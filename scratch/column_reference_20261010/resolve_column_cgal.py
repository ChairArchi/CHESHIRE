"""Resolve the raw folded surface using libigl/CGAL winding-number union.

No smoothing or voxel approximation. Preserve raw input and face provenance.
Disconnected components and nonmanifold contacts are reported, not hidden.
"""
import sys,json,argparse,time
from pathlib import Path
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'generative_gate_20261010/deps'))
from igl.copyleft import cgal

def run(source,output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    m=trimesh.load(Path(source)/'column.obj',force='mesh',process=False)
    started=time.time();print('CGAL union start',len(m.faces),flush=True)
    v,f,j=cgal.mesh_boolean(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.int64),type_str='union')
    result=trimesh.Trimesh(v,f,process=False)
    report=dict(operation='libigl 2.6.3 / CGAL self-union against empty mesh, winding number solid boundary',source=str(source),vertices=len(v),triangles=len(f),watertight=bool(result.is_watertight),winding=bool(result.is_winding_consistent),components=len(result.split(only_watertight=False)),min_triangle_area=float(result.area_faces.min()),volume=float(result.volume),smoothing=False,voxelization=False,elapsed=time.time()-started,self_intersections='CGAL resolution performed; independent output check pending')
    (out/'mesh.json').write_text(json.dumps(dict(vertices=v.tolist(),faces=f.tolist())))
    np.save(out/'source_face_indices.npy',j)
    for ext in ['obj','ply']:result.export(out/f'column.{ext}')
    (out/'validation.json').write_text(json.dumps(report,indent=2));print(report,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');a=p.parse_args();run(a.source,a.output)
