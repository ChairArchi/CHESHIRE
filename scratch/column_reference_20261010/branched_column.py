"""Reuse installed Manifold to loft and reunite thick angular ribs around a core."""
import sys,json,math,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'grotesque_gate_20261010'/'deps'))
import numpy as np
import trimesh
import manifold3d as mf
ap=argparse.ArgumentParser();ap.add_argument('--core-radius',type=float,default=.40);ap.add_argument('--output',default=str(ROOT/'branched_column_results'));args=ap.parse_args()
OUT=Path(args.output);OUT.mkdir(exist_ok=True)

def loft(sections):
    n=len(sections[0]);vs=np.array(sections).reshape((-1,3));fs=[]
    for j in range(len(sections)-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;c=(j+1)*n+(i+1)%n;d=(j+1)*n+i
            fs.extend([(a,b,c),(a,c,d)])
    for i in range(1,n-1):fs.extend([(0,i+1,i),((len(sections)-1)*n,(len(sections)-1)*n+i,(len(sections)-1)*n+i+1)])
    m=trimesh.Trimesh(vs,np.array(fs),process=True);m.fix_normals()
    assert m.is_watertight and m.is_winding_consistent
    solid=mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices,dtype=np.float32),tri_verts=np.asarray(m.faces,dtype=np.uint32)))
    assert solid.status()==mf.Error.NoError,str(solid.status())
    return solid

profile=[(0,.95),(.90,.95),(1.20,args.core_radius),(2.60,args.core_radius),(2.72,1.40),(3.38,.30),(3.52,.25),(4.04,.25),(4.24,.48),(4.88,1.40),(7.5,1.40),(8,1.07)]
core=loft([[(r*math.cos(2*math.pi*i/16),r*math.sin(2*math.pi*i/16),z) for i in range(16)] for z,r in profile])
knots=[(.78,.70,.18,.13),(1.15,1.03,.24,.20),(1.70,1.16,.26,.25),(2.14,1.08,.23,.23),(2.50,.65,.20,.17),(2.74,.36,.14,.12)]
result=core
for i in range(4):
    angle=i*math.pi/2
    sections=[]
    for z,r,d,w in knots:
        sections.append([((r+dr)*math.cos(angle)-dt*math.sin(angle),(r+dr)*math.sin(angle)+dt*math.cos(angle),z) for dr,dt in [(d,0),(0,w),(-d,0),(0,-w)]])
    result=result+loft(sections)
assert result.status()==mf.Error.NoError
output=result.to_mesh()
m=trimesh.Trimesh(np.asarray(output.vert_properties)[:,:3],np.asarray(output.tri_verts),process=True)
assert m.is_watertight and m.is_winding_consistent and len(m.split())==1
for ext in ('obj','ply'):m.export(OUT/('column.'+ext))
(OUT/'mesh.json').write_text(json.dumps(dict(vertices=m.vertices.tolist(),faces=m.faces.tolist())))
report=dict(engine='manifold3d 3.5.4',source='https://github.com/elalish/manifold',operations=['polygon-section loft','fourfold radial repetition','Boolean union'],components=len(m.split()),watertight=bool(m.is_watertight),winding=bool(m.is_winding_consistent),vertices=len(m.vertices),triangles=len(m.faces),euler_number=int(m.euler_number),genus=int((2-m.euler_number)/2),subdivision=False,smoothing=False,profile=profile,rib_knots=knots,limitations=['configured column landmarks','image-inferred hidden surfaces','not original Hansmeyer algorithm'])
(OUT/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
