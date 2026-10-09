"""Geometry-driven multiscale crest inversion; an experimental hypothesis.

Heat-filtered coordinates are FEATURES ONLY. They never replace the surface.
Positive FEM stiffness with lumped mass gives a physical-length observation.
Nonlinear response and tangential steering are our own geometric rules.
"""
import numpy as np
from scipy.sparse import coo_matrix,diags
from scipy.sparse.linalg import spsolve
from .reference_subdivision import ArrayMesh,topology

def normals(x,q):
    p=x[q];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])
    length=np.linalg.norm(cross,axis=1)
    if np.any(length<=1e-12):raise ValueError('Degenerate observation triangle')
    normal=np.column_stack([np.bincount(q.ravel(),weights=np.repeat(cross[:,k],3),minlength=len(x)) for k in range(3)])
    den=np.linalg.norm(normal,axis=1)
    if np.any(den<=1e-12):raise ValueError('Undefined vertex normal')
    return normal/den[:,None],length/2

def observe(x,q,radius):
    n,area=normals(x,q);nv=len(x);p=x[q]
    mass=np.bincount(q.ravel(),weights=np.repeat(area/3,3),minlength=nv)
    rows=[];cols=[];vals=[]
    for k in range(3):
        a=(k+1)%3;b=(k+2)%3
        cot=np.sum((p[:,a]-p[:,k])*(p[:,b]-p[:,k]),axis=1)/(2*area)
        w=cot/2;i=q[:,a];j=q[:,b]
        rows.extend([i,j,i,j]);cols.extend([j,i,i,j]);vals.extend([-w,-w,w,w])
    L=coo_matrix((np.concatenate(vals),(np.concatenate(rows),np.concatenate(cols))),shape=(nv,nv)).tocsc()
    A=diags(mass)+radius**2*L
    smooth=spsolve(A,mass[:,None]*x)
    ns,_=normals(smooth,q)
    detail=np.sum((x-smooth)*ns,axis=1)
    # Piecewise linear scalar gradient, area-averaged at vertices.
    cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);unit=cross/(2*area[:,None])
    grad=np.zeros((len(q),3))
    for k in range(3):
        grad+=detail[q[:,k],None]*np.cross(unit,p[:,(k+2)%3]-p[:,(k+1)%3])/(2*area[:,None])
    gv=np.column_stack([np.bincount(q.ravel(),weights=np.repeat(grad[:,k]*area,3),minlength=nv) for k in range(3)])/(3*mass[:,None])
    residual=float(np.linalg.norm(A@smooth-mass[:,None]*x)/max(np.linalg.norm(mass[:,None]*x),1e-30))
    return detail,gv,ns,smooth,mass,residual

def step(mesh,*,radius=300.,gain=2.,q0=1.,tangent=0.,rotation=0.,response='split',scale='parent',source='current',memory=None,refine=True,frame='current'):
    if not np.isfinite([radius,gain,q0,tangent,rotation]).all() or min(radius,q0)<=0:raise ValueError('Finite physical parameters required')
    if frame not in ('current','coherent'):raise ValueError('Unknown normal frame')
    if response not in ('split','amplify','zero','oscillate') or scale not in ('parent','local') or source not in ('current','seed'):raise ValueError('Unknown experiment condition')
    if not np.isfinite(mesh.xyz).all():raise ValueError('Nonfinite input')
    t=topology(mesh);q=mesh.faces[:,:3]
    if np.any(t['n']!=3):raise ValueError('Native triangles required')
    x=mesh.xyz;e=t['edges'];nv=len(x);memory={} if memory is None else memory
    seed=np.asarray(memory.get('seed_xyz',x))
    observed=x if source=='current' else seed
    d,grad,nobs,smoothed,mass,residual=observe(observed,q,radius)
    depth=max(float(np.quantile(np.abs(d),.8)),1e-9)
    ancestor=float(memory.get('ancestor_scale',depth))
    mean_edge=float(np.linalg.norm(x[e[:,1]]-x[e[:,0]],axis=1).mean())
    amplitude=gain*(ancestor if scale=='parent' else mean_edge)
    if refine:
        base=np.r_[x,x[e].mean(1)];rest=np.r_[mesh.rest,mesh.rest[e].mean(1)];seedout=np.r_[seed,seed[e].mean(1)]
        a,b,c=q.T;ab,bc,ca=(t['fe'][:,:3]+nv).T
        faces=np.stack([np.c_[a,ab,ca],np.c_[ab,b,bc],np.c_[ca,bc,c],np.c_[ab,bc,ca]],axis=1).reshape(-1,3)
        parents=np.repeat(np.arange(len(q)),4)
        scalar=np.r_[d,d[e].mean(1)]/depth
        gradient=np.r_[grad,grad[e].mean(1)]
    else:
        base=x.copy();rest=mesh.rest.copy();seedout=seed.copy();faces=q.copy();parents=np.arange(len(q));scalar=d/depth;gradient=grad.copy()
    n,_=normals(base,faces)
    if frame=='coherent':
        n=np.r_[nobs,nobs[e].mean(1)] if refine else nobs.copy()
        n/=np.maximum(np.linalg.norm(n,axis=1),1e-15)[:,None]
    gradient-=np.sum(gradient*n,axis=1)[:,None]*n
    gnorm=np.linalg.norm(gradient,axis=1)
    across=np.divide(gradient,gnorm[:,None],out=np.zeros_like(gradient),where=gnorm[:,None]>1e-12)
    along=np.cross(n,across)
    direction=np.cos(rotation)*across+np.sin(rotation)*along
    if response=='split':
        small=np.abs(scalar)<=q0;phi=np.empty_like(scalar)
        u=scalar[small]/q0;phi[small]=scalar[small]*(1-u*u)/(1+u**4)
        v=q0/scalar[~small];phi[~small]=scalar[~small]*v*v*(v*v-1)/(1+v**4)
    elif response=='oscillate':
        if q0<1e-6:raise ValueError('Oscillation scale below numerical experiment domain')
        phi=np.sin(np.pi*scalar/q0)/np.pi
    elif response=='amplify':phi=scalar/(1+np.abs(scalar))
    else:phi=np.zeros_like(scalar)
    # Signed crest inversion; all terms depend on measured geometry, no texture.
    tangential=tangent*(scalar/np.hypot(1.,scalar))/np.hypot(1.,scalar)
    disp=amplitude*(phi[:,None]*n+tangential[:,None]*direction)
    xyz=base+disp
    if not np.isfinite(xyz).all():raise ValueError('Nonfinite output')
    out=ArrayMesh(xyz,np.c_[faces,np.full(len(faces),-1,dtype=np.int64)],np.r_[np.zeros(nv,np.int8),np.ones(len(base)-nv,np.int8)],rest,mesh.anchors[parents],mesh.generation+1)
    state=dict(base_xyz=base,parent_faces=parents,input_edges=e,observed_xyz=observed,observed_detail=d,observed_gradient=grad,observed_normals=nobs,heat_feature_xyz=smoothed,observed_mass=mass,transferred_scalar=scalar,current_normal=n,tangent_direction=direction,resolved_displacement=disp,seed_xyz=seedout,ancestor_scale=np.array(ancestor))
    meta=dict(operator='MULTICELL_CREST_INVERSION',parameters=dict(radius=radius,gain=gain,q0=q0,tangent=tangent,rotation=rotation,response=response,scale=scale,source=source,refine=refine,frame=frame),measured_detail_scale=depth,inherited_feature_scale=ancestor,requested_amplitude=amplitude,mean_input_edge=mean_edge,actual_max_displacement=float(np.linalg.norm(disp,axis=1).max()),heat_solve_relative_residual=residual,geometry_smoothing=False,applied_normal_frame=frame,applied_frame_min_norm=float(np.linalg.norm(n,axis=1).min()),applied_frame_near_zero=int((np.linalg.norm(n,axis=1)<1e-6).sum()),validity='EXPLORATORY_UNCHECKED')
    return out,meta,state,dict(seed_xyz=seedout,ancestor_scale=ancestor)
