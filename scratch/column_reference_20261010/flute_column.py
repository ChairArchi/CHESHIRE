"""Input-derived faceted axial fluting via Manifold Boolean difference.
For straight, centered Z-axis polygonal columns. No smoothing/subdivision.
"""
import sys,json,math,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'grotesque_gate_20261010'/'deps'))
import numpy as np
import trimesh
import manifold3d as mf

def solid(mesh):
    mesh.fix_normals()
    result=mf.Manifold(mf.Mesh64(vert_properties=np.asarray(mesh.vertices,dtype=np.float64),tri_verts=np.asarray(mesh.faces,dtype=np.uint64)))
    assert result.status()==mf.Error.NoError
    return result

def cutter(sections):
    n=len(sections[0]);vs=np.array(sections).reshape((-1,3));fs=[]
    for j in range(len(sections)-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;c=(j+1)*n+(i+1)%n;d=(j+1)*n+i
            fs.extend([(a,b,c),(a,c,d)])
    for i in range(1,n-1):fs.extend([(0,i+1,i),((len(sections)-1)*n,(len(sections)-1)*n+i,(len(sections)-1)*n+i+1)])
    return solid(trimesh.Trimesh(vs,np.array(fs),process=True))

def flute(mesh,count=8,depth=.18,width=.15):
    v=np.asarray(mesh.vertices);lo,hi=mesh.bounds;axis=(lo[:2]+hi[:2])/2;h=hi[2]-lo[2]
    levels=np.unique(np.round(v[:,2],6))
    radii=np.array([np.linalg.norm(v[np.isclose(v[:,2],z,atol=h*1e-7),:2]-axis,axis=1).max() for z in levels])
    zpath=np.r_[levels[0]-.01*h,levels,levels[-1]+.01*h]
    rpath=np.r_[radii[0],radii,radii[-1]]
    result=solid(mesh)
    for k in range(count):
        angle=2*math.pi*k/count;sections=[]
        for z,r in zip(zpath,rpath):
            # Elliptic polygon cutters follow the input's changing cross-section.
            center=r*(1.02-depth/2);radial=r*(depth/2+.08);tangent=r*width
            sections.append([(axis[0]+(center+radial*math.cos(2*math.pi*j/8))*math.cos(angle)-tangent*math.sin(2*math.pi*j/8)*math.sin(angle),axis[1]+(center+radial*math.cos(2*math.pi*j/8))*math.sin(angle)+tangent*math.sin(2*math.pi*j/8)*math.cos(angle),float(z)) for j in range(8)])
        result=result-cutter(sections)
    data=result.to_mesh64();out=trimesh.Trimesh(np.asarray(data.vert_properties)[:,:3],np.asarray(data.tri_verts),process=True)
    assert out.is_watertight and out.is_winding_consistent and len(out.split())==1
    assert out.euler_number==2
    return out,dict(engine='manifold3d 3.5.4',operation='input-section-following flute cutters / Boolean difference',input_levels=levels.tolist(),input_radii=radii.tolist(),flutes=count,depth_ratio=depth,width_ratio=width,watertight=bool(out.is_watertight),components=len(out.split()),genus=0,vertices=len(out.vertices),triangles=len(out.faces),smoothing=False,subdivision=False,limitations=['straight Z-axis columns','section envelope assumes star-shaped cross-sections','not a recovered historical algorithm'])

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);ap.add_argument('--count',type=int,default=8);ap.add_argument('--depth',type=float,default=.18);ap.add_argument('--width',type=float,default=.15);args=ap.parse_args()
    mesh=trimesh.load(args.input,force='mesh',process=True);out,report=flute(mesh,args.count,args.depth,args.width)
    p=Path(args.output);p.mkdir(exist_ok=True,parents=True)
    for ext in ('obj','ply'):out.export(p/('column.'+ext))
    (p/'mesh.json').write_text(json.dumps(dict(vertices=out.vertices.tolist(),faces=out.faces.tolist())))
    report['input']=str(Path(args.input).resolve());(p/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
