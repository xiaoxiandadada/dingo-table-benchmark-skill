import importlib.util,json,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import run_benchmark as b
class RunnerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name);self.img=self.r/'image.png';self.img.write_bytes(b'image-bytes');self.path=self.r/'sample.json';self.m={'id':'model','adapter':'command','argv':['unused']};self.s={'sample_id':'s'}
 def tearDown(self):self.tmp.cleanup()
 def runone(self):return b.run_one(self.m,self.s,self.img,self.path,'prompt')
 def test_resume_does_not_submit_twice(self):
  with patch.object(b,'invoke',return_value={'status':'ok','html':'<table><tr><td>A</td></tr></table>'}) as f:
   self.runone();self.runone();self.assertEqual(f.call_count,1)
 def test_async_polls_receipt(self):
  with patch.object(b,'invoke',side_effect=[{'status':'pending','receipt':{'id':'abc'}},{'status':'ok','html':'<table><tr><td>A</td></tr></table>'}]) as f:
   self.runone();self.runone();self.assertEqual(f.call_args.args[1]['action'],'poll');self.assertEqual(f.call_args.args[1]['receipt'],{'id':'abc'})
 def test_uncertain_submission_is_not_repeated(self):
  with patch.object(b,'invoke',side_effect=TimeoutError) as f:
   self.assertEqual(self.runone()['status'],'submission_unknown');self.runone();self.assertEqual(f.call_count,1)
 def test_changed_image_rejected(self):
  with patch.object(b,'invoke',return_value={'status':'failed'}):self.runone()
  self.img.write_bytes(b'changed')
  with self.assertRaises(ValueError):self.runone()
 def test_incomplete_table_not_ok(self):
  with patch.object(b,'invoke',return_value={'status':'ok','html':'<table><tr><td>partial'}):self.assertEqual(self.runone()['status'],'invalid_output')
 def test_command_contract(self):
  self.m['argv']=[sys.executable,'-c','import sys,json; r=json.load(sys.stdin); print(json.dumps({"status":"pending","receipt":{"id":r["request_id"]}}))']
  x=self.runone();self.assertEqual(x['status'],'pending');self.assertTrue(x['receipt']['id'])
 def test_chat_image_and_truncation(self):
  import io
  m={'id':'chat','adapter':'openai-chat','model':'any-vision','endpoint_env':'TEST_TABLE_ENDPOINT','api_key_env':'TEST_TABLE_KEY','parameters':{'max_tokens':5}}
  response={'choices':[{'finish_reason':'length','message':{'content':'<table>partial'}}]}
  with patch.dict(b.os.environ,{'TEST_TABLE_ENDPOINT':'https://example.invalid/v1','TEST_TABLE_KEY':'test-only'}), patch.object(b.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as f:
   out=b.invoke(m,{'action':'submit','image_path':str(self.img),'prompt':'read'})
   self.assertEqual(out['status'],'truncated');payload=json.loads(f.call_args.args[0].data)
   self.assertEqual(payload['model'],'any-vision');self.assertTrue(payload['messages'][0]['content'][1]['image_url']['url'].startswith('data:image/png;base64,'))
 def test_non_unique_samples_rejected(self):
  (self.r/'manifest.json').write_text(json.dumps([self.s,self.s]));p=self.r/'project.json';p.write_text(json.dumps({'manifest':'manifest.json','models':[]}))
  with self.assertRaises(AssertionError):b.load_project(p)
if __name__=='__main__':unittest.main()
