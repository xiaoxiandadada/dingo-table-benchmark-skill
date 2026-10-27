"""Gold is {sample_id: html}; predictions is {sample_id: {html, status}}."""
import argparse,json,re,hashlib,importlib.util
from pathlib import Path
from lxml import html,etree

def normalize(text):
 tables=re.findall(r'<table\b[^>]*>.*?</table\s*>',text,re.I|re.S)
 if not tables:return ''
 root=etree.Element('table')
 for table in tables:
  doc=html.fromstring(table)
  for row in doc.xpath('.//tr'):
   for c in row.xpath('./td|./th'):
    c.tag='td'
    for k in list(c.attrib):
     if k not in ('rowspan','colspan'):del c.attrib[k]
    for n in c.iter():
     if n.text:n.text=re.sub(r'\s+',' ',n.text)
     if n.tail:n.tail=re.sub(r'\s+',' ',n.tail)
    for n in c.xpath('.//br'):n.tail=' '+(n.tail or '')
    etree.strip_tags(c,'b','strong','i','em','span','font','br')
    if c.text:c.text=c.text.lstrip()
   root.append(row)
 return '<html><body>'+etree.tostring(root,encoding='unicode',method='html')+'</body></html>'

def main():
 p=argparse.ArgumentParser();p.add_argument('--gold',required=True);p.add_argument('--predictions',required=True);p.add_argument('--teds-module',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 spec=importlib.util.spec_from_file_location('official_teds',a.teds_module);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);metrics=[mod.TEDS(),mod.TEDS(structure_only=True)]
 gold=json.loads(Path(a.gold).read_text());pred=json.loads(Path(a.predictions).read_text());assert gold
 rows=[]
 for sid,value in gold.items():
  truth=normalize(value);assert truth,f'Invalid gold {sid}'
  o=pred.get(sid,{});status=o.get('status','missing');score=[0,0]
  if status=='ok':
   try:
    text=normalize(o.get('html',''))
    if not text:status='no_complete_table'
    else:score=[100*m.evaluate(text,truth) for m in metrics]
   except Exception as e:status='invalid:'+type(e).__name__
  rows.append(dict(sample_id=sid,status=status,TEDS=score[0],S_TEDS=score[1]))
 result={'gold_sha256':hashlib.sha256(Path(a.gold).read_bytes()).hexdigest(),'metric_code_sha256':hashlib.sha256(Path(a.teds_module).read_bytes()).hexdigest(),'samples':rows,'summary':{k:sum(x[k] for x in rows)/len(rows) for k in ['TEDS','S_TEDS']},'denominator':len(rows),'non_ok':sum(x['status']!='ok' for x in rows)}
 Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['summary']))
if __name__=='__main__':main()
