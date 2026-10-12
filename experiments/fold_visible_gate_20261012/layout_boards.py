"""Compare fixed-column gate proportions from full actual-mesh renders."""
from pathlib import Path
import argparse
import importlib.util

from PIL import Image,ImageDraw,ImageOps

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('layout_review_font',HERE.parent/'fold_transfer_20261012/boards.py')
layout=importlib.util.module_from_spec(spec);spec.loader.exec_module(layout)
OPTIONS=[('A_NARROW_LOW','A | opening 1.75 m / beam 0.36 m'),
    ('B_WIDE_LOW','B | opening 2.53 m / beam 0.36 m'),
    ('C_NARROW_HIGH','C | opening 1.75 m / beam 0.66 m'),
    ('D_WIDE_HIGH','D | opening 2.53 m / beam 0.66 m')]


def board(root,output,view):
    cell=640;top=90;label=50;gap=16
    canvas=Image.new('RGB',(2*cell+3*gap,top+2*(cell+label+gap)+50),layout.BG)
    draw=ImageDraw.Draw(canvas)
    draw.text((gap,16),'Fixed existing columns | spacing and lintel proportions',font=layout.font(26),fill=layout.FG)
    draw.text((gap,53),'Every option uses the exact same two column meshes. Plain lintel; no column redesign.',font=layout.font(18),fill=layout.FG)
    for i,(name,title) in enumerate(OPTIONS):
        x=gap+(i%2)*(cell+gap);y=top+(i//2)*(cell+label+gap)
        draw.text((x,y+12),title,font=layout.font(23),fill=layout.FG)
        with Image.open(root/name/'views'/(view+'.png')) as image:
            saved=ImageOps.contain(image.convert('RGB'),(cell,cell),Image.Resampling.LANCZOS)
        canvas.paste(saved,(x+(cell-saved.width)//2,y+label+(cell-saved.height)//2))
    draw.text((gap,canvas.height-36),'Column height shown at 3 m using one uniform scale. Layout study; bearing and structure unverified.',font=layout.font(17),fill=layout.FG)
    output.mkdir(parents=True,exist_ok=True)
    path=output/('gate_proportions_'+view+'.png');canvas.save(path,optimize=True)
    print(path,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    for view in ('front','oblique'):
        board(args.root,args.output,view)
    layout.board(args.output/'gate_overhang.png','Same columns and opening | lintel overhang only',
        ['B | overhang 0.15 W each side','E | overhang 0.35 W each side'],['Front','Oblique'],
        [[args.root/name/'views'/(view+'.png') for name in ('B_WIDE_LOW','E_WIDE_LOW_OVERHANG')]
            for view in ('front','oblique')],
        'W is the actual maximum column width. Column positions, geometry and low lintel height are identical.')
