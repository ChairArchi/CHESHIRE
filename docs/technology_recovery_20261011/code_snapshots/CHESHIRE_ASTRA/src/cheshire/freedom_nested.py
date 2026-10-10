"""Pocket-depth support transport and exact physical-fan refinement controls.

Separate experiment: historical freedom_legacy and astra_dual remain unchanged.
Every operator polygon carries the centre of its declared physical triangle fan.
Thus leaving a polygon untouched does not silently replace its VF fan by a mean.
"""
import numpy as np
from .reference_subdivision import ArrayMesh,topology,fields,subdivide
from .astra_dual import refine_fan
from .freedom_legacy import pocket as legacy_pocket


def centres(mesh):
    if hasattr(mesh,'physical_centres'):return mesh.physical_centres
    if getattr(mesh,'surface','mean')=='vf':
        q=mesh.faces;cls=mesh.classes[q];v=np.argmax(cls==0,axis=1);f=np.argmax(cls==2,axis=1)
        return (mesh.xyz[q[np.arange(len(q)),v]]+mesh.xyz[q[np.arange(len(q)),f]])/2
    return fields(mesh)['c']


def physical(mesh):
    t=topology(mesh);q=mesh.faces;n=t['n'];nv=len(mesh.xyz);c=centres(mesh)
    nxt=q[np.arange(len(q))[:,None],(np.arange(4)[None,:]+1)%n[:,None]][t['mask']]
    tri=np.column_stack([t['a'],nxt,nv+t['fi'],np.full(len(t['a']),-1)])
    rest=(mesh.rest[np.maximum(q,0)]*t['mask'][:,:,None]).sum(1)/n[:,None]
    return ArrayMesh(np.concatenate([mesh.xyz,c]),tri,np.r_[mesh.classes,np.full(len(q),-1,np.int8)],
        np.concatenate([mesh.rest,rest]),mesh.anchors[t['fi']],mesh.generation)


def exact_split(mesh,support):
    """Use existing exact-fan topology, substituting the actual saved fan centre."""
    incoming=centres(mesh);t=topology(mesh)
    view=ArrayMesh(mesh.xyz,mesh.faces,mesh.classes,mesh.rest,mesh.anchors,mesh.generation)
    out,state=refine_fan(view)
    out.xyz[len(mesh.xyz)+len(t['edges']):]=incoming
    out.physical_centres=(out.xyz[out.faces[:,0]]+out.xyz[out.faces[:,2]])/2
    parent=state['parent_face'];child=np.asarray(support)[parent]
    state.update(input_physical_centres=incoming,output_physical_centres=out.physical_centres,child_parent_support=child)
    return out,dict(operation='EXACT_PHYSICAL_FAN_REFINEMENT',smoothing=False),state,child


def cc_split(mesh,support):
    out,meta,state=subdivide(mesh,dict(w1=.35,w2=-.7))
    parent=np.repeat(np.arange(len(mesh.faces)),(mesh.faces>=0).sum(1))
    out.physical_centres=fields(out)['c'];child=np.asarray(support)[parent]
    state.update(parent_face=parent,input_physical_centres=centres(mesh),output_physical_centres=out.physical_centres,child_parent_support=child)
    meta.update(operation='MATCHED_WEIGHTED_CC',smoothing=True)
    return out,meta,state,child


def pocket(mesh,*,parent_support=None,memory=0.,ratio=.65,depth=1.3,selection=.3):
    if not np.isfinite(memory) or not 0<=memory<=1:raise ValueError('Memory must be in [0,1].')
    out,meta,state,_=legacy_pocket(mesh,ratio=ratio,depth=depth,selection=selection,signed=False)
    local=state['current_support'];parent=local.copy() if parent_support is None else np.asarray(parent_support)
    if parent.shape!=local.shape or np.any(parent<=0) or not np.isfinite(parent).all():raise ValueError('Actual positive parent support required.')
    effective=local**(1-memory)*parent**memory
    ids=state['selected_input_faces'];nv=len(mesh.xyz);normal=fields(mesh)['nf']
    correction=-depth*(effective[ids]-local[ids])[:,None]*normal[ids]
    out.xyz[nv:]+=np.repeat(correction,4,axis=0)
    # The existing pocket function orders untouched polygons, caps, then rims.
    unselected=np.setdiff1d(np.arange(len(mesh.faces)),ids,assume_unique=True)
    out.physical_centres=fields(out)['c']
    out.physical_centres[:len(unselected)]=centres(mesh)[unselected]
    mapping=state['parent_face'];child=parent[mapping]
    state.update(current_support=local,parent_support=parent,effective_support=effective,
        requested_normal_distance=-depth*effective,child_parent_support=child,
        input_physical_centres=centres(mesh),output_physical_centres=out.physical_centres)
    meta.update(operation='SUPPORT_TRANSPORT_POCKET',support_memory=memory,
        support_rule='current_support**(1-memory) * initial-pocket-support**memory',
        untouched_native_surface='Exact saved physical fan centres retained; no mean-centre reinterpretation.')
    return out,meta,state,child
