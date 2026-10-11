"""Contact sheets of unchanged actual-mesh renders; captions outside images."""
from pathlib import Path
import argparse,math,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('E:/CHESHIRE_DATA/iaac_mandelbrot_20261011')
FONT='C:/Windows/Fonts/arial.ttf'

def board(entries,path,cols=6,cell=(240,440),title='Actual mesh catalogue'):
    w,h=cell;rows=math.ceil(len(entries)/cols)
    im=Image.new('RGB',(cols*w,rows*h+48),(27,31,36));d=ImageDraw.Draw(im)
    font=ImageFont.truetype(FONT,16);heading=ImageFont.truetype(FONT,23)
    d.text((12,9),title,font=heading,fill='white')
    for i,(label,p) in enumerate(entries):
        x=(i%cols)*w;y=(i//cols)*h+48;d.text((x+7,y+5),label,font=font,fill='white')
        if p.exists():
            img=Image.open(p).convert('RGB');iw,ih=img.size
            # Same centre crop for every case. No shape masking/retouching.
            img=img.crop((int(.225*iw),0,int(.775*iw),ih));img.thumbnail((w,h-30),Image.Resampling.LANCZOS)
            im.paste(img,(x+(w-img.width)//2,y+30))
        else:d.text((x+10,y+90),'No saved render',font=font,fill=(240,140,125))
    path.parent.mkdir(parents=True,exist_ok=True);im.save(path)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default=str(ROOT));args=p.parse_args();root=Path(args.root)
    cfgs=json.loads((root/'variations/catalogue.json').read_text())
    for view in ('front','oblique','side'):
        entries=[]
        for c in cfgs:
            name=c['name'];stage='FAILED_G01' if name=='V16_FULL' else 'G02'
            label=name+' *FAIL' if name=='V16_FULL' else name
            entries.append((label,root/'variations'/name/stage/'preview'/(view+'.png')))
        board(entries,root/'review'/('catalogue_'+view+'.png'),title=f'{len(cfgs)} recipes / G2 except V16 failed G1 / '+view+' / intersections mostly unchecked')
        for start in range(0,len(entries),12):
            board(entries[start:start+12],root/'review'/(f'catalogue_{view}_{start//12+1}.png'),
                title=f'Recipes {start+1}-{min(start+12,len(entries))} / '+view+' / actual meshes')

if __name__=='__main__':main()
