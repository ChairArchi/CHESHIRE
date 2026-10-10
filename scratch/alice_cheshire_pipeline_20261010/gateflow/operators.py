"""Composable operators acting on the received surface, never on a replacement gate template."""
from .geometry import *
from . import runtime
from compas.datastructures import Mesh
from cheshire.reference_subdivision import subdivide,mean_incident
from cheshire.polygon_dual_subdivision import doo_sabin
from cheshire.mola import extrude_tapered_once
from cheshire.execution import ExecutionBudget

REGISTRY={}
def operator(name):
    def wrap(fn):REGISTRY[name]=fn;return fn
    return wrap
@operator('mola')
def mola(m,obs,spec,scale,budget):
    ids=select(obs,spec['selected'],spec['spacing'])
    # Existing HDMola adapter validates planar triangles and preserves boundaries.
    mesh=Mesh.from_vertices_and_faces(m.vertices.tolist(),m.faces.tolist())
    heights={int(i):float(np.clip(spec['height_ratio']*scale*obs['gain'][i]*(.6+obs['bend'][i]),.01,.5)) for i in ids}
    fractions={int(i):float(np.clip(spec['fraction']+.15*obs['bend'][i],.05,.85)) for i in ids}
    result=extrude_tapered_once(mesh,selected_faces=ids.tolist(),height_ratio=heights,fraction=fractions,dll_path=runtime.REPO.parent/'Libraries/HDMola/1.0.0/HDMola.dll',budget=ExecutionBudget(budget,budget),source_is_result=True)
    v,f=result.mesh.to_vertices_and_faces();a=np.full((len(f),max(map(len,f))),-1,int)
    for i,q in enumerate(f):a[i,:len(q)]=q
    output=triangles(ArrayMesh(np.array(v),a,None,None,None))
    return output,dict(selected_faces=ids.tolist(),height_ratio=[heights[int(i)] for i in ids],backend=result.backend),dict(selected_centers=obs['center'][ids],selected_normals=obs['normal'][ids])
@operator('cc')
def cc(m,obs,spec,scale,budget):
    if len(m.faces)*6>budget:raise ValueError('CC allocation exceeds triangle budget')
    a=array_mesh(m);t=topology(a);gain=obs['gain']*(.5+obs['bend']);contrast=spec.get('contrast',1.)
    facegain=(1-contrast)+contrast*gain
    controls={'wf':scale*spec['wf']*facegain,'we':scale*spec['we']*facegain[t['ef']].mean(1),'wp':scale*spec['wp']*mean_incident(np.repeat(facegain,3),a.faces[:,:3].ravel(),len(a.xyz))}
    out,meta,st=subdivide(a,{'weights':{'w1':.12,'w2':-.08}},resolved_controls=controls)
    return triangles(out),meta,dict(resolved_wf=controls['wf'],resolved_we=controls['we'],parent_face=st['parent_face'])
@operator('ds')
def ds(m,obs,spec,scale,budget):
    if len(m.faces)*9>budget:raise ValueError('DS allocation exceeds triangle budget')
    out,roles,meta,st=doo_sabin(array_mesh(m),{},resolved_controls={'w1':np.full(len(m.faces),spec.get('w1',.45)),'wf':scale*spec.get('wf',.06)*obs['gain']*(.5+obs['bend'])})
    return triangles(out),meta,dict(parent_faces=st['parent_faces'],face_roles=roles)
@operator('fold')
def fold(m,obs,spec,scale,budget):
    if len(m.faces)*4>budget:raise ValueError('Freedom allocation exceeds triangle budget')
    from cheshire.freedom_domains import step
    out,meta,state=step(array_mesh(m),radius=spec['radius'],angle=spec['angle']*scale,direction=spec['direction'],spacing=spec['spacing'],seed_quantile=.7,source='current')
    # Semantics and actual opening proximity modulate the existing domain proposal.
    base=state['base_xyz'];gain=np.clip(obs['gain'],0,1.5)
    vertex_gain=mean_incident(np.repeat(gain,3),m.faces.ravel(),len(m.vertices));edge_gain=vertex_gain[state['input_edges']].mean(1)
    resolved=np.r_[vertex_gain,edge_gain]
    out.xyz=base+state['resolved_displacement']*resolved[:,None]
    return triangles(out),meta,dict(selected_seed_edges=state['selected_seed_edges'],domain_axes=state['domain_axes'],domain_origins=state['domain_origins'],resolved_displacement=out.xyz-base,semantic_vertex_gain=resolved)
@operator('astra')
def astra(m,obs,spec,scale,budget):
    if len(m.faces)*3>budget:raise ValueError('Astra allocation exceeds budget')
    from cheshire.astra_adaptive import step
    out,meta,state=step(array_mesh(m),fold=spec.get('fold',.3)*scale,relaxation=spec.get('relaxation',.02),feedback=1.,selection='adaptive',source='current',quantile=.5)
    return triangles(out),meta,dict(selected_faces=state['selected_faces'],resolved_offset=state['resolved_offset'])
def inward_thickness(m,centers,normals):
    # Vectorized Moller-Trumbore rays on the actual CURRENT triangles.
    tri=m.triangles;a=tri[:,0];e1=tri[:,1]-a;e2=tri[:,2]-a;out=[]
    for c,n in zip(centers,normals):
        direction=-n;origin=c-n*1e-7;h=np.cross(np.broadcast_to(direction,e2.shape),e2);det=np.einsum('ij,ij->i',e1,h)
        inv=np.divide(1,det,out=np.zeros_like(det),where=np.abs(det)>1e-14);delta=origin-a;u=inv*np.einsum('ij,ij->i',delta,h);q=np.cross(delta,e1);v=inv*(q@direction);t=inv*np.einsum('ij,ij->i',e2,q)
        ok=(np.abs(det)>1e-14)&(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(t>1e-6)
        out.append(float(t[ok].min()) if ok.any() else 0.)
    return np.array(out)
@operator('carve')
def carve(m,obs,spec,scale,budget):
    ids=select(obs,spec['selected'],spec['spacing']);thickness=inward_thickness(m,obs['center'][ids],obs['normal'][ids]);cuts=[];used=[];sizes=[]
    for i,thick in zip(ids,thickness):
        if thick<.004:continue
        n=obs['normal'][i];t=obs['tangent'][i];b=np.cross(n,t)
        r=min(spec['radius']*scale*(.65+.35*np.clip(obs['gain'][i],0,1.5)),thick*.25)
        depth=min(spec['depth']*scale,thick*.30);length=min(spec['length']*scale,thick*.48)
        center=obs['center'][i]+n*(depth*.55)
        transform=np.column_stack([t*length,b*r,n*depth,center])
        cuts.append(md.Manifold.sphere(1,20).transform(transform));used.append(int(i));sizes.append([length,r,depth])
    out=from_solid(md.Manifold.batch_boolean([solid(m)]+cuts,md.OpType.Subtract).simplify(1e-7))
    return out,dict(selected_faces=used,cutters=len(cuts),thickness_limits=True),dict(selected_centers=obs['center'][used],selected_normals=obs['normal'][used],selected_tangents=obs['tangent'][used],candidate_thickness=thickness,resolved_ellipsoid_radii=np.array(sizes))
