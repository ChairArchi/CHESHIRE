"""Independent spatial/intrinsic modified-CC prototype; not DG production code.

The published reference operator supplies all point placement and topology.
Only the control mapping, cyclic-invariant feature aggregation, and optional
end-plane boundary are new. No subtraction of the standard CC component.
"""
import numpy as np
from .reference_subdivision import ArrayMesh, topology, fields, mean_incident, subdivide


def features(mesh):
    """Actual polygon features; invariant to cyclic indexing and orientation.

    Aspect is longest/shortest boundary edge (not principal curvature).
    Planarity takes the maximum of four corner-to-opposite-plane distances,
    each normalized by that opposite triangle's perimeter. This symmetric
    aggregation extends the paper's single-corner measure.
    """
    t=topology(mesh);f=fields(mesh,t);q=mesh.faces
    if q.shape[1]!=4 or np.any(q<0):raise ValueError('Prototype requires all quads.')
    p=mesh.xyz[q];edge=np.linalg.norm(np.roll(p,-1,axis=1)-p,axis=2)
    if np.any(edge<=1e-12):raise ValueError('Zero edge in feature observation.')
    aspect=edge.max(1)/edge.min(1);plan=[]
    for k in range(4):
        a,b,c=(p[:,(k+j)%4] for j in [1,2,3])
        n=np.cross(b-a,c-a);norm=np.linalg.norm(n,axis=1)
        per=np.linalg.norm(a-b,axis=1)+np.linalg.norm(b-c,axis=1)+np.linalg.norm(c-a,axis=1)
        if np.any(norm<=1e-12):raise ValueError('Degenerate support triangle in feature observation.')
        plan.append(np.abs(np.sum((p[:,k]-a)*n,axis=1))/norm/per)
    bend=1-np.clip(np.sum(f['nf'][t['ef'][:,0]]*f['nf'][t['ef'][:,1]],axis=1),-1,1)
    return t,f,dict(aspect=aspect,planarity=np.max(plan,axis=0),bend=bend[t['fe']].mean(1))


def step(mesh, *, intrinsic=0., spatial=0., source='current', blend=1., cap_policy='none',
         wf=-.08, we=.06, wp=.08, w1=-.1, w2=-1.2, w3=-.35, w4=.9,
         signed_stencil=False, support_normalization=False, signed_limit=1.4):
    """Full same-step coupled CC, optionally convex-blended with interpolation.

    Spatial weights are a declared linear external Z field in initial bounds;
    they do not prescribe output coordinates. Rest ablation freezes features
    and spatial observation only; placement and normals remain current.
    """
    values=[intrinsic,spatial,blend,wf,we,wp,w1,w2,w3,w4,signed_limit]
    if not np.isfinite(values).all() or not 0<=intrinsic<=2 or not 0<=spatial<=2 or not 0<=blend<=1:
        raise ValueError('Finite controls and declared gain/blend domains required.')
    if source not in ('current','rest') or cap_policy not in ('none','plane'):raise ValueError('Unknown policy.')
    if not 0<signed_limit<=2:raise ValueError('Signed stencil limit must be in (0,2].')
    observed=mesh if source=='current' else ArrayMesh(mesh.rest,mesh.faces,mesh.classes,mesh.rest,mesh.anchors,mesh.generation)
    t,f,feat=features(observed);nf=len(mesh.faces);nv=len(mesh.xyz);ne=len(t['edges'])
    zmin,zmax=mesh.rest[:,2].min(),mesh.rest[:,2].max()
    if zmax<=zmin:raise ValueError('Nonzero carrier height required.')
    external=2*(f['c'][:,2]-zmin)/(zmax-zmin)-1
    # No clipping of coordinates. Bounded control response is not a bbox lock.
    external=np.tanh(external)
    aspect=np.tanh(np.log(feat['aspect']))
    planar=np.tanh(12*feat['planarity'])
    bend=np.tanh(feat['bend'])
    shape=.5*aspect+.5*planar-.5*bend
    signal=intrinsic*shape+spatial*external
    face_w1=w1+.25*signal
    face_w2=w2+.35*signal
    controls=dict(wf=wf+.12*signal,we=we+.035*(intrinsic*bend+spatial*external)[t['ef']].mean(1),
        wp=wp+.035*mean_incident(np.repeat(signal,4),mesh.faces.ravel(),nv),
        w1=face_w1[t['ef']].mean(1),w2=mean_incident(np.repeat(face_w2,4),mesh.faces.ravel(),nv),
        w3=w3+.3*signal,w4=w4+.35*(intrinsic*(planar-bend)+spatial*external))
    direction_score=np.log(feat['aspect'])-3*feat['planarity']-.75*feat['bend']-.2
    if signed_stencil:
        # Positive w4 favors the V/F diagonal; negative favors the E/E pair.
        # This is a new deterministic geometry classification, not a face-ID
        # alternation or a claim about the author's hidden parameter mapping.
        controls['w4']=signed_limit*np.tanh(2*direction_score)
        controls['w3']=-.8*np.tanh(np.log(feat['aspect']))
    support=np.zeros(nf)
    if support_normalization:
        actual=fields(mesh,t);p=mesh.xyz[mesh.faces]
        edges=np.roll(p,-1,axis=1)-p
        support=np.min(np.linalg.norm(np.cross(p-actual['c'][:,None],edges),axis=2)/np.maximum(np.linalg.norm(edges,axis=2),1e-12),axis=1)
        controls['wf']*=support/actual['sf']
        controls['we']*=support[t['ef']].min(1)/actual['se']
        controls['wp']*=mean_incident(np.repeat(support,4),mesh.faces.ravel(),nv)/actual['sv']
    fixed=(mesh.rest[:,2]==zmin)|(mesh.rest[:,2]==zmax)
    if cap_policy=='plane':
        controls['wf'][fixed[mesh.faces].all(1)]=0
        controls['we'][fixed[t['edges']].all(1)]=0
        controls['wp'][fixed]=0
    out,meta,state=subdivide(mesh,{},resolved_controls=controls)
    interp=np.concatenate([mesh.xyz,mesh.xyz[t['edges']].mean(1),mesh.xyz[mesh.faces].mean(1)])
    if blend!=1:out.xyz=interp+blend*(out.xyz-interp)
    endmask=(out.rest[:,2]==zmin)|(out.rest[:,2]==zmax)
    if cap_policy=='plane':out.xyz[endmask,2]=out.rest[endmask,2]
    state.update(feature_aspect=feat['aspect'],feature_planarity=feat['planarity'],feature_bend=feat['bend'],
        intrinsic_signal=shape,spatial_signal=external,combined_signal=signal,interpolated_xyz=interp,
        directional_score=direction_score,current_support_radius=support,
        applied_displacement=out.xyz-interp,fixed_end_z=endmask if cap_policy=='plane' else np.zeros(len(out.xyz),bool))
    meta.update(implementation='ASTRA_PRIMAL_SPATIAL_INTRINSIC',parameters=dict(intrinsic=intrinsic,spatial=spatial,
        source=source,blend=blend,cap_policy=cap_policy,wf=wf,we=we,wp=wp,w1=w1,w2=w2,w3=w3,w4=w4,
        signed_stencil=signed_stencil,support_normalization=support_normalization,signed_limit=signed_limit),
        rule='Full published reference placement; independent feature-to-control map. No amplitude-based repair.',
        limitations='Rest freezes observations only. Aspect/planarity/bend are proxies, not principal curvature. Spatial field is externally organized.')
    return out,meta,state
