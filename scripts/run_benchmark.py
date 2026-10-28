"""Model-agnostic resumable runner. Configured adapters are trusted executable code."""
import argparse,base64,hashlib,html,json,mimetypes,os,re,subprocess,sys,time,urllib.request,fcntl
from pathlib import Path

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2));tmp.replace(path)
def safe(value):
 if not re.fullmatch(r'[A-Za-z0-9_-]+',value):raise ValueError('IDs must use letters, numbers, hyphens or underscores')
 return value

def complete_table(text):
 return bool(re.search(r'<table\b',text,re.I)) and len(re.findall(r'<table\b',text,re.I))==len(re.findall(r'</table\s*>',text,re.I))

def invoke(model,request):
 if model['adapter']=='command':
  # No shell expansion. Adapter implements submit/poll and owns provider-specific conversion.
  proc=subprocess.run(model['argv'],input=json.dumps(request),text=True,capture_output=True,timeout=model.get('timeout_seconds',900))
  if proc.returncode:raise RuntimeError('Adapter process failed; inspect its local log')
  return json.loads(proc.stdout)
 if model['adapter']!='openai-chat':raise ValueError('Unknown adapter')
 if request['action']!='submit':raise ValueError('Synchronous chat has no poll')
 endpoint=os.environ[model['endpoint_env']].rstrip('/')+'/chat/completions';key=os.environ[model['api_key_env']]
 image=Path(request['image_path']);mime=mimetypes.guess_type(image.name)[0] or 'image/png'
 payload=dict(model.get('parameters',{}));payload.update(model=model['model'],stream=False,messages=[{'role':'user','content':[{'type':'text','text':request['prompt']},{'type':'image_url','image_url':{'url':'data:'+mime+';base64,'+base64.b64encode(image.read_bytes()).decode()}}]}])
 req=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=model.get('timeout_seconds',900)) as f:raw=json.load(f)
 choice=raw['choices'][0];finish=choice.get('finish_reason');text=choice['message'].get('content') or ''
 return {'status':'ok' if finish=='stop' else ('truncated' if finish=='length' else 'failed'),'html':text,'finish_reason':finish,'raw_response':raw,'usage':raw.get('usage'),'backend_model':raw.get('model')}

def run_one(model,sample,image,path,prompt):
 fingerprint=digest({'model':model,'sample':sample,'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'prompt':prompt,'endpoint':os.environ.get(model.get('endpoint_env',''),'command-adapter')})
 old=json.loads(path.read_text()) if path.exists() else None
 if old and old['fingerprint']!=fingerprint:raise ValueError('Configuration/input changed: use a new run directory')
 if old and old['status']!='pending':return old  # unknown submissions are never retried automatically
 action='poll' if old else 'submit';receipt=(old or {}).get('receipt')
 if action=='poll' and not receipt:raise ValueError('Pending task has no receipt')
 state=old or {'fingerprint':fingerprint,'sample_id':sample['sample_id'],'model_id':model['id'],'submitted_at':time.time(),'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest()}
 state.update(status='submission_unknown',last_action=action);save(path,state) # before network side effects
 started=time.monotonic()
 request={'action':action,'receipt':receipt,'request_id':fingerprint,'image_path':str(image),'sample':sample,'prompt':prompt,'parameters':model.get('parameters',{})}
 try:
  out=invoke(model,request);status=out['status']
  if status not in ['ok','pending','failed','truncated']:raise ValueError('Invalid adapter status')
  if status=='pending' and not out.get('receipt'):raise ValueError('Pending adapter must return receipt')
  if status=='ok' and not complete_table(out.get('html','')):out['status']='invalid_output'
  state.update(out);state['request_seconds']=time.monotonic()-started;state['observed_at']=time.time()
 except Exception as exc:
  # Request may have reached provider. Keep receipt and require explicit reconciliation.
  state['error_type']=type(exc).__name__;state['request_seconds']=time.monotonic()-started
 save(path,state);return state

def load_project(config):
 c=json.loads(config.read_text());base=config.parent
 manifest=base/c['manifest'];samples=json.loads(manifest.read_text());assert samples
 ids=[safe(s['sample_id']) for s in samples];assert len(ids)==len(set(ids))
 mids=[safe(m['id']) for m in c['models']];assert len(mids)==len(set(mids))
 return c,base,samples,manifest.parent

def execute(config,limit):
 c,base,samples,imagebase=load_project(config);root=base/c['output']
 for model in c['models']:
  target=root/model['id'];target.mkdir(parents=True,exist_ok=True)
  frozen={'config':model,'prompt':model.get('prompt',c['prompt'])};fp=target/'config.json'
  if fp.exists() and json.loads(fp.read_text())!=frozen:raise ValueError('Use a new output directory for changed configuration')
  save(fp,frozen)
  for s in samples[:limit] if limit else samples:
   image=(imagebase/s['image_path']).resolve();actual=hashlib.sha256(image.read_bytes()).hexdigest()
   if s.get('image_sha256') and actual!=s['image_sha256']:raise ValueError('Image hash mismatch')
   state=run_one(model,s,image,target/(s['sample_id']+'.json'),frozen['prompt']);print(model['id'],s['sample_id'],state['status'],flush=True)
  predictions={s['sample_id']:json.loads((target/(s['sample_id']+'.json')).read_text()) for s in samples if (target/(s['sample_id']+'.json')).exists()}
  save(target/'predictions.json',predictions)

def report(config,metric):
 from render_table import render
 c,base,samples,imagebase=load_project(config);root=base/c['output'];root.mkdir(parents=True,exist_ok=True)
 gold=None
 if c.get('gold'):
  goldpath=base/c['gold'];gold=json.loads(goldpath.read_text());review=json.loads((base/c['gold_review']).read_text())
  assert review['gold_sha256']==hashlib.sha256(goldpath.read_bytes()).hexdigest(),'Gold changed after review'
  assert set(gold)=={s['sample_id'] for s in samples},'Gold/manifest sample sets differ'
  assert all(review['samples'].get(s)=='reviewed' for s in gold),'Unreviewed gold: render candidates, do not score'
 overview=[];parts=['<meta charset="utf-8"><h1>Table benchmark comparison</h1>']
 for model in c['models']:
  target=root/model['id'];pred={}
  for s in samples:
   p=target/(s['sample_id']+'.json');pred[s['sample_id']]=json.loads(p.read_text()) if p.exists() else {'status':'not_run','html':''}
  save(target/'predictions.json',pred)
  final=all(x['status'] not in ['not_run','pending','submission_unknown'] for x in pred.values())
  if gold and metric and final:
   subprocess.run([sys.executable,str(Path(__file__).with_name('evaluate.py')),'--gold',str(goldpath),'--predictions',str(target/'predictions.json'),'--teds-module',metric,'--output',str(target/'scores.json')],check=True)
  overview.append({'model':model['id'],'final':final,'counts':{k:sum(x['status']==k for x in pred.values()) for k in sorted({x['status'] for x in pred.values()})}})
 for s in samples:
  sid=s['sample_id'];parts.append('<h2>'+html.escape(sid)+'</h2>');parts.append('<h3>Original image</h3><img style="max-width:100%" src="'+html.escape((imagebase/s['image_path']).resolve().as_uri())+'">')
  entries=([('gold',gold[sid],'reviewed')] if gold else [])
  for m in c['models']:
   p=root/m['id']/(sid+'.json');o=json.loads(p.read_text()) if p.exists() else {};entries.append((m['id'],o.get('html',''),o.get('status','not_run')))
  for name,text,status in entries:
   parts.append('<h3>'+html.escape(name+' | '+status)+'</h3>')
   if not text:continue
   out=root/'rendered'/(sid+'__'+name+'.png')
   try:
    render(text,out,label=name+' | '+sid+' | '+status);parts.append('<img style="max-width:100%" src="'+html.escape(out.relative_to(root).as_posix())+'">')
   except Exception as exc:parts.append('<p>Render failed: '+html.escape(type(exc).__name__)+'</p>')
 (root/'comparison.html').write_text('\n'.join(parts));save(root/'coverage.json',overview)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['run','report']);p.add_argument('--config',type=Path,required=True);p.add_argument('--limit',type=int,default=3);p.add_argument('--all',action='store_true');p.add_argument('--teds-module');a=p.parse_args()
 c,base,_,_=load_project(a.config.resolve());root=base/c['output'];root.mkdir(parents=True,exist_ok=True)
 with (root/'.runner.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  if a.stage=='run':execute(a.config.resolve(),None if a.all else a.limit)
  else:report(a.config.resolve(),a.teds_module)
