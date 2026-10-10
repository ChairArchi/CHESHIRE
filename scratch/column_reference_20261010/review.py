"""Reload exported meshes, check topology and compose actual render contact sheets."""
from pathlib import Path
import json
import numpy as np
import trimesh
from PIL import Image, ImageDraw
root=Path(__file__).resolve().parent/'results_v2'
checks=[]
for stage in range(1,5):
    for ext in ('obj','ply'):
        m=trimesh.load(root/f'stage_{stage:02d}'/f'column.{ext}',force='mesh',process=True)
        v=np.asarray(m.vertices)
        # Exact fourfold rotational symmetry, including axial offsets.
        rotated=v.copy();rotated[:,0]=-v[:,1];rotated[:,1]=v[:,0]
        from scipy.spatial import cKDTree
        error=float(cKDTree(v).query(rotated)[0].max())
        item=dict(stage=stage,format=ext,components=len(m.split(only_watertight=False)),watertight=bool(m.is_watertight),winding_consistent=bool(m.is_winding_consistent),finite=bool(np.isfinite(v).all()),rotational_symmetry_error=error)
        assert item['components']==1 and item['watertight'] and item['winding_consistent'] and item['finite'] and error<1e-6
        checks.append(item)
(root/'reload_validation.json').write_text(json.dumps(checks,indent=2))
for view in ('front','oblique'):
    sheet=Image.new('RGB',(1280,650),(30,30,30));draw=ImageDraw.Draw(sheet)
    for stage,label in enumerate(('01 / 4 sides','02 / 8 sides','03 / 16 sides + parent wings','04 / interleaved child wings'),1):
        im=Image.open(root/f'stage_{stage:02d}'/(view+'.png')).convert('RGB').resize((320,600))
        sheet.paste(im,((stage-1)*320,40));draw.text(((stage-1)*320+10,12),label,fill=(235,235,235))
    sheet.save(root/(view+'_comparison.png'))
print(json.dumps(checks,indent=2))
