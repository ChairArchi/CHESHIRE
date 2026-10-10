"""Triangle edge-rotating growth, inspired by sqrt(3) connectivity.

Kobbelt 2000 supplies the insert-centres/flip-old-edges topology idea.
The bounded signed normal response and retention are our experimental rules;
no claim of the paper's smooth limit or Hansmeyer's private implementation.
"""
import numpy as np
from .reference_subdivision import ArrayMesh,topology,fields,mean_incident

def features(mesh):
    if not np.isfinite(mesh.xyz).all():raise ValueError('Nonfinite input.')
    t=topology(mesh);f=fields(mesh,t)
    if np.any(t['n']!=3):raise ValueError('Closed triangles required.')
    q=mesh.faces[:,:3];p=mesh.xyz[q]
    lengths=np.linalg.norm(np.roll(p,-1,axis=1)-p,axis=2)
    if np.any(lengths<=1e-12) or np.any(f['area']<=1e-12):raise ValueError('Degenerate input triangle.')
    support=2*f['area']/lengths.sum(1) # exact triangle inradius
    # Orient each edge as it appears in first adjacent face.
    ef=t['ef'];edges=t['edges'];left=q[ef[:,0]]
    sign=np.where(np.any((left==edges[:,0,None])&(np.roll(left,-1,axis=1)==edges[:,1,None]),axis=1),1.,-1.)
    direction=(mesh.xyz[edges[:,1]]-mesh.xyz[edges[:,0]])*sign[:,None]
    direction/=np.linalg.norm(direction,axis=1)[:,None]
    n0=f['nf'][ef[:,0]];n1=f['nf'][ef[:,1]]
    angle=np.arctan2(np.sum(direction*np.cross(n0,n1),axis=1),np.clip(np.sum(n0*n1,axis=1),-1,1))
    bend=angle[t['fe'][:,:3]].mean(1)
    return t,f,dict(inradius=support,signed_bend=bend,edge_angle=angle,edge_orientation=sign)

def step(mesh,*,fold=.35,relaxation=.18,feedback=1.,bias=0.,source='current',flip=True,polarity=-1.):
    if not np.isfinite([fold,relaxation,feedback,bias]).all() or not 0<=relaxation<=1 or not 0<=fold<=2 or not 0<=feedback<=3:
        raise ValueError('Invalid declared parameter range.')
    if source not in ['current','rest']:raise ValueError('Unknown source.')
    if polarity not in (-1.,1.):raise ValueError('Polarity must be -1 or +1.')
    observed=mesh if source=='current' else ArrayMesh(mesh.rest,mesh.faces,mesh.classes,mesh.rest,mesh.anchors,mesh.generation)
    t,obs,feat=features(observed);actual=fields(mesh,t);x=mesh.xyz;q=mesh.faces[:,:3];nv=len(x);nf=len(q);e=t['edges'];ef=t['ef']
    # Negative and positive folds respond to actual signed geometry.
    response=np.tanh(bias+feedback*3*feat['signed_bend'])
    offset=polarity*fold*feat['inradius']*response
    centre=actual['c']+actual['nf']*offset[:,None]
    neighbor=mean_incident(x[e[:,::-1].ravel()],e.ravel(),nv)
    old=x+relaxation*(neighbor-x)
    xyz=np.concatenate([old,centre])
    rest=np.concatenate([mesh.rest,mesh.rest[q].mean(1)])
    if flip:
        sign=feat['edge_orientation'];a=np.where(sign>0,e[:,0],e[:,1]);b=np.where(sign>0,e[:,1],e[:,0]);l=ef[:,0]+nv;r=ef[:,1]+nv
        faces=np.stack([np.column_stack([a,r,l]),np.column_stack([b,l,r])],axis=1).reshape(-1,3)
        parents=np.repeat(ef,2,axis=0);corners=np.column_stack([a,b]).ravel()
    else:
        faces=np.stack([q,np.roll(q,-1,axis=1),np.broadcast_to(np.arange(nf)[:,None]+nv,q.shape)],axis=-1).reshape(-1,3)
        parents=np.repeat(np.column_stack([np.arange(nf),np.full(nf,-1)]),3,axis=0);corners=q.ravel()
    anchors=mesh.anchors[parents[:,0]].copy()
    if flip:anchors=np.where(anchors==mesh.anchors[parents[:,1]],anchors,-1)
    out=ArrayMesh(xyz,np.column_stack([faces,np.full(len(faces),-1,np.int64)]),np.r_[np.zeros(nv,np.int8),np.full(nf,2,np.int8)],rest,anchors,mesh.generation+1)
    if not np.isfinite(out.xyz).all():raise ValueError('Nonfinite output.')
    topology(out)
    state=dict(input_edges=e,parent_faces=parents,parent_corner=corners,feature_inradius=feat['inradius'],feature_signed_bend=feat['signed_bend'],feature_edge_angle=feat['edge_angle'],resolved_offset=offset,response=response,old_vertex_displacement=old-x,new_face_displacement=centre-actual['c'])
    meta=dict(implementation='ASTRA_ROTATING_TRIANGLE',parameters=dict(fold=fold,relaxation=relaxation,feedback=feedback,bias=bias,source=source,flip=flip,polarity=polarity),topology='Insert triangle centroids then flip every old edge; 3x faces' if flip else 'Insert centroids only; 3x faces',limitations='Own nonlinear normal-offset rule; fixed genus; not original sqrt3 smoothing coefficients. Reference observation uses the evolving undeformed rest embedding, not fixed initial feature arrays; placement/normals remain current.')
    return out,meta,state
