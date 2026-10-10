"""Re-open delivered files, including double PLY, and check actual serialization."""
import json,sys
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'generative_gate_20261010/deps'))
from igl.copyleft import cgal
p=Path(sys.argv[1]);d=json.loads((p/'mesh.json').read_text());reference=np.array(d['vertices']);tree=cKDTree(reference);rows={}
for ext in ['obj','ply']:
    m=trimesh.load(p/f'column.{ext}',process=False,force='mesh')
    r=dict(vertices=len(m.vertices),triangles=len(m.faces),watertight=bool(m.is_watertight),winding=bool(m.is_winding_consistent),zero_area_triangles=int((m.area_faces<=0).sum()),max_vertex_roundtrip_distance=float(tree.query(m.vertices)[0].max()))
    r['cgal_first_intersection_pairs']=len(cgal.remesh_self_intersections(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.int64),detect_only=True,first_only=True)[2])
    rows[ext]=r
    assert r['watertight'] and r['winding'] and r['zero_area_triangles']==0 and r['cgal_first_intersection_pairs']==0,r
(p/'export_validation.json').write_text(json.dumps(rows,indent=2));print(rows,flush=True)
