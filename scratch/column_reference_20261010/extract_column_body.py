"""Keep dominant connected body after exact union; explicitly account for debris."""
import json,sys
from pathlib import Path
import numpy as np
import trimesh
source=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=True)
d=json.loads((source/'mesh.json').read_text());m=trimesh.Trimesh(d['vertices'],d['faces'],process=False)
parts=m.split(only_watertight=False);body=max(parts,key=lambda p:abs(p.volume))
report=dict(source=str(source),operation='retain largest absolute-volume connected component',input_components=len(parts),components=1,retained_volume_fraction=float(abs(body.volume)/sum(abs(p.volume) for p in parts)),discarded_components=len(parts)-1,vertices=len(body.vertices),triangles=len(body.faces),watertight=bool(body.is_watertight),winding=bool(body.is_winding_consistent),min_triangle_area=float(body.area_faces.min()),volume=float(body.volume),smoothing=False,self_intersections='independent CGAL detection pending')
report.update(component_selection_note='Other components may be detached solids OR inner cavity shells; retaining only the main shell can fill small enclosed cavities.',input_signed_volume=float(m.volume),signed_volume_change=float(body.volume-m.volume),negative_volume_components=int(sum(p.volume<0 for p in parts)))
body.export(out/'column.obj',digits=17)
# CGAL creates very small cut triangles: do not round intersections to float32.
with (out/'column.ply').open('w',encoding='ascii') as stream:
    stream.write('ply\nformat ascii 1.0\nelement vertex %d\nproperty double x\nproperty double y\nproperty double z\nelement face %d\nproperty list uchar int vertex_indices\nend_header\n'%(len(body.vertices),len(body.faces)))
    stream.writelines('%.17g %.17g %.17g\n'%tuple(v) for v in body.vertices)
    stream.writelines('3 %d %d %d\n'%tuple(f) for f in body.faces)
(out/'mesh.json').write_text(json.dumps(dict(vertices=body.vertices.tolist(),faces=body.faces.tolist())))
(out/'validation.json').write_text(json.dumps(report,indent=2));print(report)
