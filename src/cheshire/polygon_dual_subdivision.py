"""Task31 opt-in closed polygon DS. Eq5/6 on tri/quads; neutral cosine mask
on other polygons (COMPAS subdivision.py). Modified Hansmeyer w1 is explicitly
inactive on those polygons. No invented generalization of unpublished weights.
"""
import numpy as np
from .reference_subdivision import ArrayMesh, topology, fields
from .dual_subdivision import _corners


def polygon_corners(values,q,n,w1):
    out=np.zeros((*q.shape,3),float)
    short=n<=4
    if short.any():out[short,:4]=_corners(values,q[short,:4],n[short],w1[short])
    for size in np.unique(n[~short]):
        ids=np.flatnonzero(n==size);i=np.arange(size)
        alpha=(3+2*np.cos(2*np.pi*(i[:,None]-i[None,:])/size))/(4*size)
        np.fill_diagonal(alpha,(size+5)/(4*size))
        out[ids,:size]=np.einsum('ij,fjk->fik',alpha,values[q[ids,:size]])
    return out


def doo_sabin(mesh,weights,*,face_roles=None,resolved_controls=None):
    t=topology(mesh);f=fields(mesh,t);q=mesh.faces;n=t['n'];nv=len(mesh.xyz);nf=len(q);ne=len(t['edges'])
    if np.any(n<3) or np.any(t['degree']<3):raise ValueError('Closed polygon degree >=3 required.')
    roles=np.full(nf,-1,np.int8) if face_roles is None else np.asarray(face_roles)
    if roles.shape!=(nf,) or not np.isin(roles,[-1,0,1,2]).all():raise ValueError('Invalid face origins.')
    controls=resolved_controls or {}
    w1=np.asarray(controls.get('w1',np.full(nf,float(weights.get('w1',0.)))),float)
    wf=np.asarray(controls.get('wf',np.full(nf,float(weights.get('wf',0.)))),float)
    if any(v.shape!=(nf,) or not np.isfinite(v).all() for v in (w1,wf)):raise ValueError('Invalid DS controls.')
    xyz=(polygon_corners(mesh.xyz,q,n,w1)+f['nf'][:,None]*wf[:,None,None]*f['sf'][:,None,None])[t['mask']]
    rest=polygon_corners(mesh.rest,q,n,np.zeros(nf))[t['mask']]
    width=max(q.shape[1],int(t['degree'].max()),4);slots=np.arange(q.shape[1])[None,:]
    start=np.r_[0,np.cumsum(n)[:-1]];corners=np.where(t['mask'],start[:,None]+slots,-1)
    hs=np.arange(len(t['a']));next_h=corners[np.arange(nf)[:,None],(slots+1)%n[:,None]][t['mask']]
    prev_h=corners[np.arange(nf)[:,None],(slots-1)%n[:,None]][t['mask']]
    pair=np.argsort(t['fe'][t['mask']],kind='stable').reshape(-1,2)
    opposite=np.empty(len(hs),np.int64);opposite[pair[:,0]]=pair[:,1];opposite[pair[:,1]]=pair[:,0]
    h,k=pair[:,0],pair[:,1];edge_faces=np.column_stack([next_h[h],h,next_h[k],k])
    first=np.full(nv,len(hs),np.int64);np.minimum.at(first,t['a'],hs)
    successor=opposite[prev_h];vfaces=np.empty((nv,width),np.int64);vfaces[:,0]=first
    for j in range(1,width):vfaces[:,j]=successor[vfaces[:,j-1]]
    degree=t['degree'];vmask=np.arange(width)[None,:]<degree[:,None]
    for j in range(1,width):
        repeated=(vfaces[:,j,None]==vfaces[:,:j]).any(1)
        if np.any((j<degree)&repeated):raise ValueError('Disconnected input vertex fan repeats before full degree.')
    if not np.array_equal(successor[vfaces[np.arange(nv),degree-1]],first):raise ValueError('Noncyclic/disconnected fan.')
    if not np.all(t['a'][vfaces]==np.arange(nv)[:,None]):raise ValueError('Fan changes vertex.')
    vfaces[~vmask]=-1
    faces=np.full((nf+ne+nv,width),-1,np.int64)
    faces[:nf,:q.shape[1]]=corners;faces[nf:nf+ne,:4]=edge_faces;faces[nf+ne:]=vfaces
    parents=np.full((len(faces),width),-1,np.int64)
    parents[:nf,0]=np.arange(nf);parents[nf:nf+ne,:2]=t['ef']
    parents[nf+ne:]=np.where(vmask,t['fi'][np.maximum(vfaces,0)],-1)
    pm=parents>=0;values=mesh.anchors[np.maximum(parents,0)]
    shared=((values==values[:,0,None,:])|~pm[:,:,None]).all(1)&(values[:,0]>=0)
    out=ArrayMesh(xyz,faces,np.full(len(xyz),-1,np.int8),rest,np.where(shared,values[:,0],-1),mesh.generation+1)
    if not np.isfinite(xyz).all():raise ValueError('Nonfinite DS output.')
    ot=topology(out)
    if np.any(ot['degree']!=4):raise ValueError('Unexpected DS output valence.')
    output_roles=np.r_[np.zeros(nf,np.int8),np.ones(ne,np.int8),np.full(nv,2,np.int8)]
    meta=dict(generation=out.generation,implementation='POLYGON_DOO_SABIN',weights=weights,
        extended_polygon_count=int((n>4).sum()),w1_inactive_polygon_ids=np.flatnonzero(n>4).tolist(),
        rule='Exact Eq5/6 for n=3/4; standard positive cosine mask for n>4 plus local wf; no w1 extension.',
        topology='Complete F/E/V polygons and cyclic fans, no welding or genus change.')
    state=dict(parent_faces=parents,input_edges=t['edges'],resolved_w1=w1,resolved_wf=wf,face_scale=f['sf'],
        input_face_roles=roles,output_face_roles=output_roles)
    return out,output_roles,meta,state
