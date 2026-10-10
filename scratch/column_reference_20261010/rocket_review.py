from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent/'rocket_results'
checks=[]
for stage in range(1,4):
    for ext in ('obj','ply'):
        m=trimesh.load(ROOT/f'stage_{stage:02d}'/f'column.{ext}',force='mesh',process=True)
        v=np.asarray(m.vertices);r=v.copy();r[:,0]=-v[:,1];r[:,1]=v[:,0]
        # Boolean triangulations need not have symmetric vertex positions;
        # surface rotation is checked by nearest triangle rather than vertex pairing.
        rotated=trimesh.Trimesh(vertices=r,faces=m.faces,process=False)
        pts=np.vstack([v,np.asarray(m.triangles_center)])
        distance=trimesh.proximity.closest_point_naive(rotated,pts)[1]
        report=dict(stage=stage,format=ext,components=len(m.split(only_watertight=False)),watertight=bool(m.is_watertight),winding_consistent=bool(m.is_winding_consistent),finite=bool(np.isfinite(v).all()),rotation_surface_error=float(distance.max()))
        assert report['components']==1 and report['watertight'] and report['winding_consistent'] and report['finite'] and report['rotation_surface_error']<1e-6
        checks.append(report)
(ROOT/'reload_validation.json').write_text(json.dumps(checks,indent=2))
for view in ('front','oblique'):
    sheet=Image.new('RGB',(960,650),(30,30,30));draw=ImageDraw.Draw(sheet)
    for stage,label in enumerate(('01 / Body only','02 / Four fins','03 / Four + four interleaved fins'),1):
        im=Image.open(ROOT/f'stage_{stage:02d}'/(view+'.png')).convert('RGB').resize((320,600))
        sheet.paste(im,((stage-1)*320,40));draw.text(((stage-1)*320+10,12),label,fill=(235,235,235))
    sheet.save(ROOT/(view+'_comparison.png'))
print(json.dumps(checks,indent=2))
