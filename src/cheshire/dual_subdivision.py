"""Opt-in published Doo–Sabin masks and face-origin topology for Task30.

Hansmeyer 2010, Subdivision Beyond Smoothness, Eq5/6 and section2.2.
Scope: closed oriented triangles/quads with input valence3/4. No welding,
genus changes, implicit polygon conversion or claim of unpublished DG code.
"""
import numpy as np
from .reference_subdivision import ArrayMesh,topology,fields,GLOBAL_SCALE,LOCAL_INCIDENT_SCALE

FACE,EDGE,VERTEX,UNKNOWN=0,1,2,-1
ROLE_NAMES={FACE:'FACE',EDGE:'EDGE',VERTEX:'VERTEX',UNKNOWN:'UNKNOWN'}
REFERENCE_DOO_SABIN='REFERENCE_DOO_SABIN'


def _corners(values,q,n,w1):
    """Literal Eq5/6; masked fourth triangle slots are not output vertices."""
    p=values[np.maximum(q,0)]
    j=np.arange(4)[None,:];i=np.arange(len(q))[:,None]
    nxt=p[i,(j+1)%n[:,None]];prev=p[i,(j-1)%n[:,None]];opp=p[i,(j+2)%n[:,None]]
    w=w1[:,None,None]
    quad=(p*(2.25+2*w)+(nxt+prev)*(.75-w)+.25*opp)/4
    tri=p*(2/3)*(1+w/2)+(nxt+prev)*(1-w)/6
    return np.where((n==3)[:,None,None],tri,quad)


def doo_sabin(mesh,weights,*,face_roles=None,groups=None,scale_mode=LOCAL_INCIDENT_SCALE):
    t=topology(mesh);f=fields(mesh,t);q=mesh.faces;n=t['n'];nv=len(mesh.xyz);nf=len(q);ne=len(t['edges'])
    if np.any((n!=3)&(n!=4)) or np.any((t['degree']!=3)&(t['degree']!=4)):
        raise ValueError('Doo-Sabin experiment requires face size and vertex valence3/4; no conversion.')
    roles=np.full(nf,UNKNOWN,np.int8) if face_roles is None else np.asarray(face_roles)
    if roles.shape!=(nf,) or not np.isin(roles,[-1,0,1,2]).all():raise ValueError('Invalid actual face-origin state.')
    roles=roles.astype(np.int8,copy=False)
    groups=groups or {}
    if set(groups)-{'FACE','EDGE','VERTEX'}:raise ValueError('Unknown structural face group.')
    w1=np.full(nf,float(weights.get('w1',0.)));wf=np.full(nf,float(weights.get('wf',0.)))
    for role,name in ROLE_NAMES.items():
        if name in groups:
            mask=roles==role;w1[mask]=float(groups[name].get('w1',w1[mask][0] if mask.any() else weights.get('w1',0.)))
            wf[mask]=float(groups[name].get('wf',wf[mask][0] if mask.any() else weights.get('wf',0.)))
    if not np.isfinite(w1).all() or not np.isfinite(wf).all():raise ValueError('Finite DS controls required.')
    scale=f['sf'].copy()
    if scale_mode==GLOBAL_SCALE:scale[:]=f['lengths'].mean()
    elif scale_mode!=LOCAL_INCIDENT_SCALE:raise ValueError('Unknown DS scale mode.')
    points=_corners(mesh.xyz,q,n,w1)+f['nf'][:,None]*wf[:,None,None]*scale[:,None,None]
    xyz=points[t['mask']]
    # Positive neutral mask transports cage association; negative shape weights
    # and extrusion do not turn association into a second displacement field.
    rest=_corners(mesh.rest,q,n,np.zeros(nf))[t['mask']]
    lengths=n;start=np.r_[0,np.cumsum(n)[:-1]];slots=np.arange(4)[None,:]
    corners=np.where(t['mask'],start[:,None]+slots,-1)
    hs=np.arange(len(t['a']));next_h=corners[np.arange(nf)[:,None],(slots+1)%n[:,None]][t['mask']]
    prev_h=corners[np.arange(nf)[:,None],(slots-1)%n[:,None]][t['mask']]
    # Opposite oriented halfedges are paired by the existing actual edge IDs.
    inv=t['fe'][t['mask']];order=np.argsort(inv,kind='stable');pair=order.reshape(-1,2)
    opposite=np.empty(len(hs),np.int64);opposite[pair[:,0]]=pair[:,1];opposite[pair[:,1]]=pair[:,0]
    h,k=pair[:,0],pair[:,1]
    edge_faces=np.column_stack([next_h[h],h,next_h[k],k])
    # Reverse the edge-face traversal to make each original vertex's face.
    first=np.full(nv,len(hs),np.int64);np.minimum.at(first,t['a'],hs)
    successor=opposite[prev_h];vfaces=np.empty((nv,4),np.int64);vfaces[:,0]=first
    for j in range(1,4):vfaces[:,j]=successor[vfaces[:,j-1]]
    degree=t['degree'];last=vfaces[np.arange(nv),degree-1]
    if not np.array_equal(successor[last],first):raise ValueError('Disconnected/noncyclic input vertex fan.')
    if not np.all(t['a'][vfaces]==np.arange(nv)[:,None]):raise ValueError('Vertex fan changes original vertex.')
    vmask=np.arange(4)[None,:]<degree[:,None];vfaces[~vmask]=-1
    faces=np.concatenate([corners,edge_faces,vfaces])
    output_roles=np.r_[np.full(nf,FACE,np.int8),np.full(ne,EDGE,np.int8),np.full(nv,VERTEX,np.int8)]
    parents=np.full((len(faces),4),-1,np.int64)
    parents[:nf,0]=np.arange(nf);parents[nf:nf+ne,:2]=t['ef']
    parents[nf+ne:]=np.where(vmask,t['fi'][np.maximum(vfaces,0)],-1)
    pmask=parents>=0;values=mesh.anchors[np.maximum(parents,0)]
    shared=((values==values[:,0,None,:])|~pmask[:,:,None]).all(1)&(values[:,0]>=0)
    anchors=np.where(shared,values[:,0],-1)
    out=ArrayMesh(xyz,faces,np.full(len(xyz),-1,np.int8),rest,anchors,mesh.generation+1)
    if not np.isfinite(xyz).all():raise ValueError('Nonfinite DS coordinates.')
    ot=topology(out)
    if np.any(ot['degree']!=4):raise ValueError('Unexpected DS generated valence.')
    metadata=dict(generation=out.generation,implementation=REFERENCE_DOO_SABIN,scale=scale_mode,
        source='R1 Subdivision Beyond Smoothness (2010), Eq5/6 and section2.2',weights=weights,groups=groups,
        input_face_origin_counts={name:int((roles==role).sum()) for role,name in ROLE_NAMES.items()},
        output_face_origin_counts={name:int((output_roles==role).sum()) for role,name in ROLE_NAMES.items()},
        face_normal='Unit actual input polygon area-vector normal.',
        topology='F faces per input face, E faces per input edge, V faces per cyclic input vertex fan. No joins/genus change.',
        ancestry='Exact up-to-four source-face supports stored. Single anchors retained only if all parents agree; otherwise -1.',
        vertex_provenance='DS corners have no CC V/E/F stencil pattern; next CC step explicitly falls back to Eq1.',
        all_zero=bool(np.all(w1==0)&np.all(wf==0)))
    state=dict(input_corner_face=t['fi'],input_corner_vertex=t['a'],parent_faces=parents,
        output_face_roles=output_roles,input_face_roles=roles,resolved_w1=w1,resolved_wf=wf,face_scale=scale,
        input_edges=t['edges'])
    return out,output_roles,metadata,state
