"""Published weighted CC with explicit transported ancestor displacement scale.

This experiment allows invalid finite geometry and never repairs intersections.
The incoming actual normals and stencils are recomputed every generation.
Only the normal distance scale is transported through exact parent faces.
"""
import numpy as np
from .reference_subdivision import ArrayMesh,topology,fields,mean_incident,subdivide


def step(mesh,weights,*,ancestor_scale=None,memory=.5):
    if not np.isfinite(memory) or not 0<=memory<=1:raise ValueError('Memory must be in [0,1].')
    t=topology(mesh);f=fields(mesh,t)
    inherited=f['sf'].copy() if ancestor_scale is None else np.asarray(ancestor_scale,float)
    if inherited.shape!=(len(mesh.faces),) or np.any(inherited<=0) or not np.isfinite(inherited).all():
        raise ValueError('Positive finite exact-parent face scales required.')
    scale=f['sf']**(1-memory)*inherited**memory
    edge_scale=scale[t['ef']].mean(1)
    vertex_scale=mean_incident(np.repeat(scale,t['n']),t['a'],len(mesh.xyz))
    controls={key:float(weights.get(key,0))*desired/f[base] for key,desired,base in
        [('wf',scale,'sf'),('we',edge_scale,'se'),('wp',vertex_scale,'sv')]}
    out,meta,state=subdivide(mesh,weights,resolved_controls=controls)
    child_scale=np.repeat(inherited,t['n'])
    state.update(ancestor_face_scale=inherited,effective_face_scale=scale,actual_face_scale=f['sf'],
        effective_edge_scale=edge_scale,effective_vertex_scale=vertex_scale,child_ancestor_scale=child_scale,
        source_parent_face=t['fi'],incoming_actual_face_normals=f['nf'])
    meta.update(scale_memory=memory,scale_rule='current_scale**(1-memory) * transported_ancestor_scale**memory',
        validity_policy='No clamp, repair or intersection stop; finite invalid geometry is diagnostic.',weights=weights)
    return out,meta,state,child_scale


def pocket(mesh,*,ratio=.55,depth=.5,selection=0.,signed=False,ancestor_scale=None):
    """Actual cap/rim construction, selected from current geometric width.

    Interior quads inset affinely around actual face centres and move along
    current normals. Rim quads retain shared original boundary edges. This is
    our explicit polygon construction, not a claim of using MOLA's code.
    """
    if not np.isfinite([ratio,depth,selection]).all() or not 0<ratio<1 or not 0<=selection<1:
        raise ValueError('Finite declared inset and selection required.')
    if mesh.faces.shape[1]!=4 or np.any(mesh.faces<0):raise ValueError('All-quad input required.')
    t=topology(mesh);f=fields(mesh,t);q=mesh.faces;nv=len(mesh.xyz)
    p=mesh.xyz[q];edge=np.roll(p,-1,axis=1)-p
    support=(np.linalg.norm(np.cross(p-f['c'][:,None],edge),axis=2)/np.maximum(np.linalg.norm(edge,axis=2),1e-12)).min(1)
    threshold=float(np.quantile(support,selection));chosen=support>=threshold*(1-1e-12);ids=np.flatnonzero(chosen)
    ef=t['ef'][t['fe']];other=np.where(ef[:,:,0]==np.arange(len(q))[:,None],ef[:,:,1],ef[:,:,0])
    contrast=np.sum((f['c']-f['c'][other].mean(1))*f['nf'],axis=1)/np.maximum(support,1e-12)
    direction=np.tanh(3*contrast) if signed else np.ones(len(q))
    distance=-depth*support*direction
    cap=f['c'][ids,None]+ratio*(p[ids]-f['c'][ids,None])+distance[ids,None,None]*f['nf'][ids,None]
    restcentre=mesh.rest[q].mean(1);caprest=restcentre[ids,None]+ratio*(mesh.rest[q[ids]]-restcentre[ids,None])
    capid=nv+np.arange(len(ids)*4).reshape(-1,4)
    rim=np.stack([q[ids],np.roll(q[ids],-1,axis=1),np.roll(capid,-1,axis=1),capid],axis=-1).reshape(-1,4)
    face=np.concatenate([q[~chosen],capid,rim])
    parent=np.r_[np.flatnonzero(~chosen),ids,np.repeat(ids,4)]
    out=ArrayMesh(np.concatenate([mesh.xyz,cap.reshape(-1,3)]),face,np.full(nv+len(ids)*4,-1,np.int8),
        np.concatenate([mesh.rest,caprest.reshape(-1,3)]),mesh.anchors[parent],mesh.generation+1)
    inherited=f['sf'] if ancestor_scale is None else np.asarray(ancestor_scale)
    if inherited.shape!=(len(q),):raise ValueError('Parent scale correspondence required.')
    role=np.r_[np.full((~chosen).sum(),-1),np.zeros(len(ids)),np.ones(len(ids)*4)].astype(np.int8)
    state=dict(parent_face=parent,selected_input_faces=ids,current_support=support,selection_threshold=np.array(threshold),
        current_signed_contrast=contrast,requested_normal_distance=distance,output_cap_rim_role=role,input_face_vertices=q,
        inserted_corner_parent=np.repeat(ids,4),child_ancestor_scale=inherited[parent])
    meta=dict(operation='Actual affine inset cap and four connected rims',ratio=ratio,depth=depth,selection_quantile=selection,signed=signed,
        selected_faces=len(ids),parent_class_policy='Reset to unknown; next CC correctly uses ordinary face-point fallback.',
        input_vertices_untouched=True,validity_policy='No intersection/clamp repair or validity stop.')
    return out,meta,state,inherited[parent]
