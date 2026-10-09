"""Task30 actual geometry views, preserving Task29's exact fixed renderer."""
import argparse,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from task30_study import ROOT
import task29_views
from hero_design_sprint import guarded


def sheet(records,path,cols=4,size=900):
    """Readable captions; geometry pixels retain the same renderer/framing."""
    rows=(len(records)+cols-1)//cols;caption=max(44,size//17)
    out=Image.new('RGB',(cols*size,rows*(size+caption)),(245,245,242));draw=ImageDraw.Draw(out)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',max(23,size//31))
    for i,r in enumerate(records):
        im=Image.open(r['image']).convert('RGB').resize((size,size))
        x=i%cols*size;y=i//cols*(size+caption);out.paste(im,(x,y))
        draw.text((x+10,y+size+8),r['label'],font=font,fill=(25,25,25))
    path.parent.mkdir(parents=True,exist_ok=True);out.save(path)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.worker:
        task29_views.ROOT=ROOT;task29_views.sheet=sheet;task29_views.render(a.request,a.tag)
    else:
        r=guarded(['--request',str(a.request),'--tag',a.tag,'--worker'],ROOT/'logs'/('render_'+a.tag),worker_script=Path(__file__))
        print(r,flush=True);sys.exit(r['exit_code'])
