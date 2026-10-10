"""Panel 5->6-inspired regional flutes. Reuse input-derived Boolean cutters."""
from flute_column import ROOT,solid,cutter
from pathlib import Path
import numpy as np,trimesh,math,json,hashlib
SOURCE=ROOT/'reference_proportion_results/stage_03/column.obj'
mesh=trimesh.load(SOURCE,force='mesh',process=True)
v=np.asarray(mesh.vertices);lo,hi=mesh.bounds;h=hi[2]-lo[2];axis=(lo[:2]+hi[:2])/2
zs=np.unique(np.round(v[:,2],6));rs=np.array([np.linalg.norm(v[np.isclose(v[:,2],z,atol=1e-6),:2]-axis,axis=1).max() for z in zs])
regions=[dict(name='upper_long_body',low=.56,high=.99,count=8,phase=0,depth=.20,width=.14),dict(name='lower_body',low=.115,high=.335,count=8,phase=math.pi/8,depth=.24,width=.16),dict(name='neck_collar',low=.375,high=.445,count=12,phase=math.pi/12,depth=.26,width=.10),dict(name='foot',low=.005,high=.10,count=8,phase=0,depth=.20,width=.14)]
branches=[dict(name='upper_transition_children',low=.455,high=.64,count=8,phase=math.pi/8,depth=.23,width=.10),dict(name='lower_transition_children',low=.285,high=.362,count=8,phase=0,depth=.22,width=.10)]
def apply_region(result,region):
    a=lo[2]+h*region['low'];b=lo[2]+h*region['high']
    levels=np.unique(np.r_[np.linspace(a,b,9),zs[(zs>a)&(zs<b)]])
    for k in range(region['count']):
        angle=region['phase']+2*math.pi*k/region['count'];sections=[]
        for z in levels:
            t=(z-a)/(b-a);strength=min(1,t/.16,(1-t)/.16);r=float(np.interp(z,zs,rs))
            radial=.16*r;center=r*(1.04+.16-region['depth']*strength);tangent=r*region['width']
            sections.append([(axis[0]+(center+radial*math.cos(2*math.pi*j/8))*math.cos(angle)-tangent*math.sin(2*math.pi*j/8)*math.sin(angle),axis[1]+(center+radial*math.cos(2*math.pi*j/8))*math.sin(angle)+tangent*math.sin(2*math.pi*j/8)*math.cos(angle),float(z)) for j in range(8)])
        result=result-cutter(sections)
    return result
result=solid(mesh)
for region in regions:result=apply_region(result,region)
for name,extra in [('regional',[]),('regional_children',branches)]:
    for region in extra:result=apply_region(result,region)
    data=result.to_mesh64();out=trimesh.Trimesh(np.asarray(data.vert_properties)[:,:3],np.asarray(data.tri_verts),process=True)
    assert out.is_watertight and out.is_winding_consistent and len(out.split())==1 and out.euler_number==2
    p=ROOT/(name+'_results');p.mkdir(exist_ok=True)
    for ext in ('obj','ply'):out.export(p/('column.'+ext))
    (p/'mesh.json').write_text(json.dumps(dict(vertices=out.vertices.tolist(),faces=out.faces.tolist())))
    (p/'validation.json').write_text(json.dumps(dict(input=str(SOURCE),input_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),regions=regions+extra,vertices=len(out.vertices),triangles=len(out.faces),components=1,watertight=True,genus=0,subdivision=False,smoothing=False,interpretation='image-inspired regional hierarchy, not recovered original process'),indent=2))
    print(name,len(out.vertices),len(out.faces),flush=True)
