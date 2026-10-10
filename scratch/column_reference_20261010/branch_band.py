"""Reusable column-band branching from an actual input mesh.
Scope: straight axial column, Z axis, centered XY. No general gate claim.
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
    if result.status()!=mf.Error.NoError:raise ValueError(str(result.status()))
    return result

def loft(sections):
    n=len(sections[0]);vs=np.array(sections).reshape((-1,3));fs=[]
    for j in range(len(sections)-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;c=(j+1)*n+(i+1)%n;d=(j+1)*n+i
            fs.extend([(a,b,c),(a,c,d)])
    for i in range(1,n-1):fs.extend([(0,i+1,i),((len(sections)-1)*n,(len(sections)-1)*n+i,(len(sections)-1)*n+i+1)])
    return solid(trimesh.Trimesh(vs,np.array(fs),process=True))

def branch_band(mesh,lower=.09,upper=.34,count=4,core_ratio=.30):
    lo,hi=mesh.bounds;height=hi[2]-lo[2];axis=(lo[:2]+hi[:2])/2
    a=lo[2]+lower*height;b=lo[2]+upper*height;length=b-a
    v=np.asarray(mesh.vertices);zvalues=np.unique(np.round(v[:,2],6))
    envelope=np.array([np.linalg.norm(v[np.isclose(v[:,2],z,atol=1e-5),:2]-axis,axis=1).max() for z in zvalues])
    radius=lambda z:float(np.interp(z,zvalues,envelope))
    sample_z=np.linspace(a,b,7);rmax=max(radius(z) for z in sample_z)
    core=rmax*core_ratio;depth=rmax*.13;width=rmax*.18;overlap=height*.003
    def circular(z,r):return [(axis[0]+r*math.cos(2*math.pi*i/16),axis[1]+r*math.sin(2*math.pi*i/16),z) for i in range(16)]
    sections=[circular(a-overlap,radius(a-overlap)),circular(a+.17*length,core),circular(b-.17*length,core),circular(b+overlap,radius(b+overlap))]
    tool=mf.Manifold.cube((float((hi[0]-lo[0])*3),float((hi[1]-lo[1])*3),float(length)),True).translate((float(axis[0]),float(axis[1]),float((a+b)/2)))
    result=(solid(mesh)-tool)+loft(sections)
    paths=[]
    for k in range(count):
        angle=2*math.pi*k/count;sections=[];path=[]
        for j,z in enumerate(sample_z):
            # Root sections connect to retained masses; middle follows input envelope.
            rr=radius(z)-depth*.5
            if j in (0,6):rr*=.65
            path.append((float(z),rr))
            sections.append([(axis[0]+(rr+dr)*math.cos(angle)-dt*math.sin(angle),axis[1]+(rr+dr)*math.sin(angle)+dt*math.cos(angle),float(z)) for dr,dt in [(depth,0),(0,width),(-depth,0),(0,-width)]])
        result=result+loft(sections);paths.append(path)
    result=result.simplify(height*1e-7)
    output=result.to_mesh64();out=trimesh.Trimesh(np.asarray(output.vert_properties)[:,:3],np.asarray(output.tri_verts),process=True)
    if not out.is_watertight or len(out.split())!=1:raise ValueError(str(dict(status=str(result.status()),closed=out.is_watertight,components=[dict(faces=len(c.faces),volume=c.volume,bounds=c.bounds.tolist()) for c in out.split(only_watertight=False)])))
    # Check source geometry outside the overlap zone against actual output triangles.
    points=np.vstack([v,np.asarray(mesh.triangles_center)])
    points=points[(points[:,2]<a-2*overlap)|(points[:,2]>b+2*overlap)]
    error=float(trimesh.proximity.closest_point_naive(out,points)[1].max())
    return out,dict(selected_z=[a,b],axis=axis.tolist(),input_envelope=list(zip(zvalues.tolist(),envelope.tolist())),rib_paths=paths,core_radius=core,thickness=2*depth,components=len(out.split()),watertight=bool(out.is_watertight),genus=int((2-out.euler_number)/2),outside_band_surface_error=error,scope='straight Z-axis column; manually selected normalized band',engine='manifold3d 3.5.4')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);ap.add_argument('--lower',type=float,default=.09);ap.add_argument('--upper',type=float,default=.34);ap.add_argument('--count',type=int,default=4);args=ap.parse_args()
    source=trimesh.load(args.input,force='mesh',process=True);out,report=branch_band(source,args.lower,args.upper,args.count)
    folder=Path(args.output);folder.mkdir(parents=True,exist_ok=True)
    for ext in ('obj','ply'):out.export(folder/('column.'+ext))
    (folder/'mesh.json').write_text(json.dumps(dict(vertices=out.vertices.tolist(),faces=out.faces.tolist())))
    report['input']=str(Path(args.input).resolve());(folder/'validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('input_envelope','rib_paths')},indent=2))
