from pathlib import Path
import json
import numpy as np
import trimesh
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'reference_next_panel_results'
checks=[]
for stage in (1,2):
    for ext in ('obj','ply'):
        m=trimesh.load(OUT/f'stage_{stage:02d}'/f'column.{ext}',force='mesh',process=True)
        v=np.asarray(m.vertices);rot=v.copy();rot[:,0]=-v[:,1];rot[:,1]=v[:,0]
        other=trimesh.Trimesh(vertices=rot,faces=m.faces,process=False)
        err=trimesh.proximity.closest_point_naive(other,np.vstack([v,m.triangles_center]))[1].max()
        check=dict(stage=stage,format=ext,components=len(m.split(only_watertight=False)),watertight=bool(m.is_watertight),winding=bool(m.is_winding_consistent),symmetry_surface_error=float(err))
        assert check['components']==1 and check['watertight'] and check['winding'] and err<1e-6
        checks.append(check)
ref=Image.open(ROOT/'hansmeyer_reference.png').convert('RGB')
for view in ('front','oblique'):
    sheet=Image.new('RGB',(1080,650),(30,30,30));d=ImageDraw.Draw(sheet)
    for x,box,label in [(0,(746,10,808,188),'Reference 4'),(540,(145,207,194,379),'Reference 5')]:
        crop=ref.crop(box);w=round(crop.width/crop.height*600)
        sheet.paste(crop.resize((w,600)),(x,40));d.text((x+8,12),label,fill='white')
    for stage,x,label in [(1,215,'Reconstructed 4'),(2,740,'Next-panel study')]:
        im=Image.open(OUT/f'stage_{stage:02d}'/(view+'.png')).convert('RGB').resize((320,600))
        sheet.paste(im,(x,40));d.text((x+8,12),label,fill='white')
    sheet.save(OUT/(view+'_comparison.png'))
(OUT/'reload_validation.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))
