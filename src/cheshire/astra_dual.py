"""Independent, intrinsic face-corner dual experiment; not recovered DG code.

Exact published Doo--Sabin connectivity is reused. Current polygon width
relative to adjacent widths controls inset and extrusion. Corner differences
in actual adjacent-normal bend modulate extrusion within each polygon.
There is no axial profile, oscillator, random field, or face-ID ornament map.
"""
import numpy as np
from .reference_subdivision import ArrayMesh, topology, fields
from .dual_subdivision import doo_sabin, _corners, FACE, EDGE, VERTEX


def features(mesh):
    t=topology(mesh);f=fields(mesh,t);q=mesh.faces;n=t['n'];mask=t['mask']
    p=mesh.xyz[np.maximum(q,0)];slots=np.arange(4)[None,:]
    following=p[np.arange(len(q))[:,None],(slots+1)%n[:,None]]
    edge=following-p
    distance=np.linalg.norm(np.cross(p-f['c'][:,None],edge),axis=2)/np.maximum(np.linalg.norm(edge,axis=2),1e-12)
    support=np.where(mask,distance,np.inf).min(1)
    if np.any(support<=1e-12):raise ValueError('Degenerate polygon support.')
    ef=t['ef'][np.maximum(t['fe'],0)]
    other=np.where(ef[:,:,0]==np.arange(len(q))[:,None],ef[:,:,1],ef[:,:,0])
    adjacent=(support[other]*mask).sum(1)/n
    width_contrast=np.log(support/adjacent)
    bends=1-np.clip(np.sum(f['nf'][t['ef'][:,0]]*f['nf'][t['ef'][:,1]],axis=1),-1,1)
    b=bends[np.maximum(t['fe'],0)]
    before=b[np.arange(len(q))[:,None],(slots-1)%n[:,None]]
    corner_bend=(b+before)/2
    face_bend=(corner_bend*mask).sum(1)/n
    corner_contrast=corner_bend-face_bend[:,None]
    return t,f,dict(support=support,width_contrast=width_contrast,
        face_bend=face_bend,corner_contrast=corner_contrast)


def step(mesh, face_roles=None, *, tension=.65, fold_gain=.2, feedback=.6,
         corner_gain=.5, source='current', cap_policy='none', role_gain=0.):
    """Return mesh, exact F/E/V roles, metadata, actual operator state.

    source='rest' freezes feature observation on transported neutral DS points;
    placement and normals still use current mesh (a features-only ablation).
    Zero feedback/folding exactly reproduces the existing published DS mask.
    Cap policy 'plane' fixes Z only on neutral samples on original end planes.
    It is a declared optional boundary condition, never a shape normalization.
    """
    if not np.isfinite([tension,fold_gain,feedback,corner_gain,role_gain]).all():raise ValueError('Finite controls required.')
    if not -.5<=tension<=1 or not 0<=fold_gain<=1 or not 0<=feedback<=1 or not 0<=corner_gain<=2:
        raise ValueError('Outside declared prototype parameter domain.')
    if not 0<=role_gain<=1:raise ValueError('Role gain outside declared prototype domain.')
    if source not in ('current','rest') or cap_policy not in ('none','plane'):raise ValueError('Unknown observation or boundary policy.')
    observed=mesh if source=='current' else ArrayMesh(mesh.rest,mesh.faces,mesh.classes,mesh.rest,mesh.anchors,mesh.generation)
    t,fo,feat=features(observed);actual=fields(mesh,t)
    resolved=tension+.12*feedback*np.tanh(feat['width_contrast'])
    strength=np.tanh(2*feat['width_contrast'])[:,None]+corner_gain*np.tanh(2*feat['corner_contrast'])
    role_sign=np.zeros(len(mesh.faces))
    if face_roles is not None:
        actual_roles=np.asarray(face_roles)
        if actual_roles.shape!=(len(mesh.faces),):raise ValueError('Actual face-role array required.')
        role_sign[actual_roles==EDGE]=-1
        role_sign[actual_roles==VERTEX]=1
    offset=feat['support'][:,None]*(fold_gain*strength+role_gain*role_sign[:,None])
    out,roles,meta,state=doo_sabin(mesh,{'w1':tension,'wf':0},face_roles=face_roles)
    points=_corners(mesh.xyz,mesh.faces,t['n'],resolved)
    xyz=points+actual['nf'][:,None,:]*offset[:,:,None]
    out.xyz=xyz[t['mask']]
    fixed=np.zeros(len(out.xyz),bool)
    if cap_policy=='plane':
        ends=(mesh.rest[:,2].min(),mesh.rest[:,2].max())
        fixed=(out.rest[:,2]==ends[0])|(out.rest[:,2]==ends[1])
        out.xyz[fixed,2]=out.rest[fixed,2]
    state.update(feature_support=feat['support'],feature_width_contrast=feat['width_contrast'],
        feature_face_bend=feat['face_bend'],feature_corner_contrast=feat['corner_contrast'],
        resolved_w1=resolved,resolved_corner_offset=offset[t['mask']],
        baseline_corner_xyz=points[t['mask']],fixed_cap_z=fixed,actual_origin_role_sign=role_sign)
    meta.update(implementation='ASTRA_INTRINSIC_DUAL_PROTOTYPE',source=source,
        parameters=dict(tension=tension,fold_gain=fold_gain,feedback=feedback,corner_gain=corner_gain,cap_policy=cap_policy,role_gain=role_gain),
        feature_rule='log(current supporting-line radius / mean adjacent radius), adjacent-normal corner contrast',
        limitations='Polygon supporting-line radius is a scale proxy, not intrinsic width or principal curvature. Neutral rest ablation freezes features only. No validity repair.')
    return out,roles,meta,state


def native(mesh):
    """Explicit centroid-fan surface, retaining operator polygons separately."""
    t=topology(mesh);f=fields(mesh,t);nv=len(mesh.xyz);q=mesh.faces
    centres=f['c'].copy()
    if getattr(mesh,'surface','mean')=='vf':
        cls=mesh.classes[np.maximum(q,0)];old=np.argmax(cls==0,axis=1);face=np.argmax(cls==2,axis=1)
        valid=(t['n']==4)&((cls==0).sum(1)==1)&((cls==2).sum(1)==1)&((old+2)%4==face)
        centres[valid]=(mesh.xyz[q[np.arange(len(q)),old]]+mesh.xyz[q[np.arange(len(q)),face]])[valid]/2
    b=q[np.arange(len(q))[:,None],(np.arange(4)[None,:]+1)%t['n'][:,None]][t['mask']]
    tri=np.column_stack([t['a'],b,nv+t['fi'],np.full(len(t['a']),-1,np.int64)])
    rest=(mesh.rest[np.maximum(q,0)]*t['mask'][:,:,None]).sum(1)/t['n'][:,None]
    return ArrayMesh(np.concatenate([mesh.xyz,centres]),tri,
        np.r_[mesh.classes,np.full(len(q),-1,np.int8)],np.concatenate([mesh.rest,rest]),
        mesh.anchors[t['fi']],mesh.generation)


def refine_fan(mesh):
    """Pure sampling of the declared centroid-fan surface, without smoothing.

    This is a separate topology ablation: every polygon obtains one child quad
    per corner, exposing its interior to later dual operators. V--F midpoint
    native centres preserve the actual incoming fan triangles exactly.
    """
    if getattr(mesh,'surface','mean')!='mean':
        raise ValueError('This sampling operator requires the declared centroid-fan input surface.')
    t=topology(mesh);f=fields(mesh,t);nv=len(mesh.xyz);ne=len(t['edges']);nf=len(mesh.faces)
    q=mesh.faces;slots=np.arange(4)[None,:]
    previous=t['fe'][np.arange(nf)[:,None],(slots-1)%t['n'][:,None]]
    faces=np.column_stack([t['a'],t['fe'][t['mask']]+nv,nv+ne+t['fi'],previous[t['mask']]+nv])
    restcentres=(mesh.rest[np.maximum(q,0)]*t['mask'][:,:,None]).sum(1)/t['n'][:,None]
    out=ArrayMesh(np.concatenate([mesh.xyz,mesh.xyz[t['edges']].mean(1),f['c']]),faces,
        np.r_[np.zeros(nv,np.int8),np.ones(ne,np.int8),np.full(nf,2,np.int8)],
        np.concatenate([mesh.rest,mesh.rest[t['edges']].mean(1),restcentres]),
        mesh.anchors[t['fi']],mesh.generation+1)
    out.surface='vf'
    return out,dict(parent_face=t['fi'],parent_corner=t['a'],input_edges=t['edges'],operation='Exact centroid-fan sampling; no smoothing or displacement')
