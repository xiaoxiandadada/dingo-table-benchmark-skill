"""Render a selected unrotated PDF rectangle; page numbers are one-based."""
import argparse,hashlib,json
from pathlib import Path
import pymupdf as fitz

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('page',type=int);p.add_argument('box',nargs=4,type=float);p.add_argument('output');p.add_argument('--dpi',type=int,default=300);p.add_argument('--padding',type=float,default=2);a=p.parse_args()
 assert a.dpi>0 and a.padding>=0
 out=Path(a.output);assert not out.exists(),'Output exists; choose a new version'
 doc=fitz.open(a.pdf);assert 1<=a.page<=len(doc);page=doc[a.page-1];rotation=page.rotation;page.set_rotation(0)
 x0,y0,x1,y1=a.box;assert x1>x0 and y1>y0
 box=fitz.Rect(x0-a.padding,y0-a.padding,x1+a.padding,y1+a.padding)&page.rect;assert not box.is_empty
 out.parent.mkdir(parents=True,exist_ok=True);pix=page.get_pixmap(dpi=a.dpi,clip=box,colorspace=fitz.csRGB,alpha=False);pix.save(out)
 meta={'source_sha256':sha(a.pdf),'page_1based':a.page,'page_rotation':rotation,'coordinate_space':'PyMuPDF unrotated page points','bbox_pdf_points':list(box),'dpi':a.dpi,'image_size':[pix.width,pix.height],'image_sha256':sha(out)}
 out.with_suffix('.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta))
if __name__=='__main__':main()
