import sys,json
from pathlib import Path
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'generative_gate_20261010/deps'))
import igl
from igl.copyleft import cgal
p=Path(sys.argv[1]);d=json.loads((p/'mesh.json').read_text());v=np.asarray(d['vertices'],dtype=np.float64);f=np.asarray([[face[0],face[i],face[i+1]] for face in d['faces'] for i in range(1,len(face)-1)],dtype=np.int64)
print('CGAL independent detection',len(f),flush=True)
result=cgal.remesh_self_intersections(v,f,detect_only=True,first_only=True)
report=json.loads((p/'validation.json').read_text());report['cgal_first_intersection_pairs']=len(result[2]);report['self_intersections']='CGAL detect_only first_only: zero means no intersection detected over complete search; nonzero stops at first detection'
if len(sys.argv)>2:
    raw=trimesh.load(Path(sys.argv[2])/'column.obj',force='mesh',process=False)
    sq,_,_=igl.point_mesh_squared_distance(v,np.asarray(raw.vertices),np.asarray(raw.faces,dtype=np.int64))
    report['resolved_vertex_distance_to_raw_surface_max']=float(np.sqrt(sq.max()))
    report['resolved_vertex_distance_to_raw_surface_p99']=float(np.sqrt(np.quantile(sq,.99)))
    report['distance_limit']='one-way vertex-to-triangle distance; not a bidirectional Hausdorff bound'
(p/'validation.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
