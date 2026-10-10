"""Actual reference crop and mesh-render comparison; exported mesh reload checks."""
from pathlib import Path
import json
import numpy as np
import trimesh
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent/'reference_proportion_results'
checks=[]
for stage in range(1,4):
    for ext in ('obj','ply'):
        m=trimesh.load(ROOT/f'stage_{stage:02d}'/f'column.{ext}',force='mesh',process=True)
        v=np.asarray(m.vertices);rot=v.copy();rot[:,0]=-v[:,1];rot[:,1]=v[:,0]
        rotated=trimesh.Trimesh(vertices=rot,faces=m.faces,process=False)
        pts=np.vstack([v,np.asarray(m.triangles_center)])
        err=trimesh.proximity.closest_point_naive(rotated,pts)[1].max()
        item=dict(stage=stage,format=ext,components=len(m.split(only_watertight=False)),watertight=bool(m.is_watertight),winding=bool(m.is_winding_consistent),finite=bool(np.isfinite(v).all()),symmetry_surface_error=float(err))
        assert item['components']==1 and item['watertight'] and item['winding'] and item['finite'] and err<1e-6
        checks.append(item)
(ROOT/'reload_validation.json').write_text(json.dumps(checks,indent=2))
ref=Image.open(r'C:/Users/USER/Downloads/User attachment.png').convert('RGB').crop((746,10,808,188))
ref.save(ROOT/'reference_crop.png')
for view in ('front','oblique'):
    sheet=Image.new('RGB',(1289,645),(30,30,30));draw=ImageDraw.Draw(sheet)
    sheet.paste(ref.resize((209,600)),(0,35));draw.text((8,10),'Reference: top row / panel 4',fill='white')
    for stage,label in enumerate(('Previous mass','Wider body / lower mass','Short neck collar / planar corners'),1):
        im=Image.open(ROOT/f'stage_{stage:02d}'/(view+'.png')).convert('RGB')
        if view=='front':im=im.crop((0,67,640,1134))
        im=im.resize((360,600));sheet.paste(im,(209+(stage-1)*360,35));draw.text((219+(stage-1)*360,10),label,fill='white')
    sheet.save(ROOT/(view+'_reference_comparison.png'))
print(json.dumps(checks,indent=2))
