"""Render HTML tables without changing cell text/spans; optional CSS highlights."""
import argparse,html,os
from pathlib import Path
os.environ.setdefault('DYLD_FALLBACK_LIBRARY_PATH','/opt/homebrew/lib')
from lxml import html as lh,etree
from weasyprint import HTML
import pymupdf as fitz

def render(source,output,marks=(),label='Table rendering'):
 root=lh.fromstring(source);tables=root.xpath('descendant-or-self::table');assert tables,'No table found'
 holder=etree.Element('div')
 for table in tables:
  if not any(a.tag=='table' for a in table.iterancestors()):holder.append(table)
 for n in holder.xpath('.//script|.//style|.//iframe|.//link|.//object|.//img'):n.getparent().remove(n)
 # Empty header groups can suppress the entire table in some renderers.
 for n in holder.xpath('.//thead|.//tbody|.//tfoot'):
  if not n.xpath('.//tr'):n.getparent().remove(n)
 for n in holder.iter():
  for k in list(n.attrib):
   if k not in ('rowspan','colspan'):del n.attrib[k]
 cells=holder.xpath('.//td|.//th');assert cells,'No table cells'
 for i in marks:
  assert 0<=i<len(cells),f'Cell index out of range: {i}'
  cells[i].set('class','error')
 css='@page{size:1400px 30000px;margin:24px}body{font:18px Arial,"Hiragino Sans",sans-serif}table{border-collapse:collapse;width:100%;table-layout:fixed;margin:12px 0}td,th{border:1px solid #888;padding:7px;overflow-wrap:anywhere}.error{outline:3px solid red;outline-offset:-3px}'
 content=etree.tostring(holder,encoding='unicode',method='html')
 doc=HTML(string='<meta charset="utf-8"><style>'+css+'</style><h3>'+html.escape(label)+'</h3>'+content,url_fetcher=lambda u:(_ for _ in ()).throw(ValueError('External resources disabled'))).render()
 assert len(doc.pages)==1,'Table exceeds canvas; explicitly split or increase canvas'
 boxes=list(doc.pages[0]._page_box.descendants());rendered={id(b.element) for b in boxes if getattr(b,'element_tag',None) in ('td','th')}
 assert len(rendered)>=len(cells),'Rendered cells missing; do not publish'
 bottom=max(b.position_y+b.height for b in boxes if getattr(b,'element_tag',None));assert bottom>100
 pdf=fitz.open(stream=doc.write_pdf(),filetype='pdf');page=pdf[0];pix=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),clip=fitz.Rect(0,0,page.rect.width,min(page.rect.height,(bottom+25)*.75)))
 Path(output).parent.mkdir(parents=True,exist_ok=True);pix.save(output);return {'cells':len(cells),'width':pix.width,'height':pix.height}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('output');p.add_argument('--mark',default='');p.add_argument('--label',default='Table rendering');a=p.parse_args();print(render(Path(a.input).read_text(),a.output,[int(x) for x in a.mark.split(',') if x],a.label))
