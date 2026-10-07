"""Task27 adapter to the existing depth-correct neutral OpenGL capture route."""
import argparse
from pathlib import Path
import sys
from PIL import Image,ImageDraw
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
import progressive_gate_views as renderer
from dynamic_section_gates import directory
from cross_cell_crease_study import read,write,file_hash


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--names',nargs='+',required=True)
    p.add_argument('--tag',required=True);p.add_argument('--views',nargs='+',default=['front','oblique','detail']);p.add_argument('--resolution',type=int,default=1400)
    a=p.parse_args();out=a.output_root/'renders'/a.tag
    if out.exists():raise ValueError('Preserve previous captured states; use a new tag.')
    renderer.parent_directory=directory
    renderer.CAMERAS.update(detail=(0,-8,[-1750.036865234375,-18.533447265625,2450],1700),
        detail_angle=(32,-22,[-1750.036865234375,-18.533447265625,2450],1700),
        body=(0,0,[-1750.036865234375,-18.533447265625,1350],2800),
        mantle=(0,-15,[-400.036865234375,-18.533447265625,3050],2300))
    renderer.capture(a.output_root,a.names,a.tag,a.views,a.resolution)
    manifest=read(out/'camera_manifest.json');manifest['adapter_sha256']=file_hash(Path(__file__))
    write(out/'camera_manifest.json',manifest)
    if len(a.names)==4:
        for view in a.views:
            sheet=Image.new('RGB',(1000,1060),(242,242,240));draw=ImageDraw.Draw(sheet)
            for i,name in enumerate(a.names):
                im=Image.open(out/(name+'_'+view+'.png')).convert('RGB');im.thumbnail((500,500))
                x=i%2*500;y=i//2*530;sheet.paste(im,(x,y));draw.text((x+12,y+504),name,fill=(25,25,25))
            sheet.save(out/(view+'_four_path_comparison.png'))
