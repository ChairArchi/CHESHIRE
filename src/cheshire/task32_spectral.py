"""Opt-in lumped cotan eigenfields and our nonlinear harmonic displacement.

Standard generalized Laplacian eigenproblem, not Vallet/Levy's complete
out-of-core band solver or an exact ornamental formula from their paper.
"""
from dataclasses import replace
import numpy as np
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import eigsh, spsolve
from .reference_subdivision import fields
from .task32_morphology import triangles


def cotan_system(mesh):
    xyz=mesh.xyz/1000  # declared original model units, not physical millimetres
    tri=triangles(mesh); p=xyz[tri]
    cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])
    twice_area=np.linalg.norm(cross,axis=1)
    if np.any(twice_area<1e-14):raise ValueError('Degenerate triangles in spectral domain.')
    rows=[];cols=[];data=[]
    for corner in range(3):
        j=(corner+1)%3;k=(corner+2)%3
        cot=((p[:,j]-p[:,corner])*(p[:,k]-p[:,corner])).sum(1)/twice_area
        a,b=tri[:,j],tri[:,k];w=cot/2
        rows.extend([a,b]);cols.extend([b,a]);data.extend([w,w])
    adjacency=coo_matrix((np.concatenate(data),(np.concatenate(rows),np.concatenate(cols))),
                         shape=(len(xyz),len(xyz))).tocsr()
    lap=diags(np.asarray(adjacency.sum(1)).ravel())-adjacency
    area=np.bincount(tri.ravel(),weights=np.repeat(twice_area/6,3),minlength=len(xyz))
    if np.any(area<=0):raise ValueError('Positive lumped vertex areas required.')
    return lap,area


def spectral_field(mesh,spec):
    lap,area=cotan_system(mesh); mass=diags(area)
    modes=[int(i) for i in spec.get('modes',[3,8])]
    if min(modes)<1 or max(modes)>=len(mesh.xyz)-2:raise ValueError('Nonconstant in-range modes required.')
    count=max(modes)+2
    vals,vectors=eigsh(lap,k=count,M=mass,sigma=-1e-8,which='LM',
                       v0=np.sin(np.arange(len(mesh.xyz))*.61803398875)+.2,tol=1e-10)
    order=np.argsort(vals);vals=vals[order];vectors=vectors[:,order]
    for j in range(count):
        if vectors[np.argmax(np.abs(vectors[:,j])),j]<0:vectors[:,j]*=-1
    residual=lap@vectors-(area[:,None]*vectors)*vals
    relative=np.linalg.norm(residual,axis=0)/np.maximum(np.linalg.norm((area[:,None]*vectors)*vals,axis=0),1e-12)
    selected=vectors[:,modes]
    selected=selected/np.maximum(np.max(np.abs(selected),axis=0),1e-12)
    return selected,dict(eigenvalues=vals.tolist(),modes=modes,
                        nonconstant_relative_residual_max=float(relative[1:].max()),
                        mass_orthogonality_max=float(np.abs(vectors.T@(area[:,None]*vectors)-np.eye(count)).max())), \
        dict(eigenvalues=vals,eigenvectors=vectors,vertex_lumped_areas=area,
             selected_modes=selected,domain_xyz=mesh.xyz)


def spectral_displace(mesh,spec,previous=None):
    if previous is None or spec.get('remeasure'):
        coordinates,meta,state=spectral_field(mesh,spec)
    else:
        coordinates=previous['coordinates'];meta=dict(transport='positive CC interpolation of original spectral coordinates')
        state={}
    parent=coordinates[:,0]
    second=coordinates[:,1] if coordinates.shape[1]>1 else parent
    level=int(spec.get('level',0))
    if level==0:
        scalar=parent+float(spec.get('secondary_mix',.4))*second
    else:
        frequency=float(spec.get('frequency',4))*(2**(level-1))
        phase=frequency*np.pi*parent
        scalar=np.sin(phase+float(spec.get('coupling',1))*second*np.pi)
        scalar*=np.clip(np.abs(parent),0,1)**float(spec.get('envelope_power',.5))
    scalar*=np.clip(mesh.rest[:,2]/250,0,1)
    amplitude=float(spec.get('amplitude',250))
    requested=amplitude*scalar
    normals=fields(mesh)['nv'];applied=requested
    if spec.get('curvature_limit'):
        limit,kappa=curvature_limit(mesh,float(spec['curvature_limit']))
        smooth_length=float(spec.get('limit_smoothing_length',0))
        if smooth_length:
            log_limit,residual=diffuse_field(mesh,np.log(limit),smooth_length)
            limit=np.exp(log_limit)
            meta['limit_diffusion']=dict(model_unit_length=smooth_length,residual=residual,
                caveat='Diffusing log bounds can relax individual local limits; not a collision certificate.')
        applied=limit*np.tanh(requested/limit)
        state.update(curvature_bound=limit,estimated_max_abs_curvature=kappa,requested_displacement=requested)
        meta['limiter']=dict(fraction=float(spec['curvature_limit']),
            requested_max=float(np.abs(requested).max()),applied_max=float(np.abs(applied).max()),
            changed_vertices=int((np.abs(applied-requested)>1e-5).sum()),
            caveat='Own local curvature heuristic, not a global collision or variable-offset regularity guarantee.')
    xyz=mesh.xyz+applied[:,None]*normals
    state.update(coordinates=coordinates,field=scalar,normals=normals,displacement=xyz-mesh.xyz)
    meta.update(mechanism='cotan eigenfield / transported nonlinear phase displacement',spec=spec,
        amplitude=amplitude,level=level,topology_changed=False,
        caveat='Own normal displacement application; not physical folds, emergent topology, or unique canonical eigenbasis.')
    return replace(mesh,xyz=xyz),meta,state


def curvature_limit(mesh,fraction):
    if not 0<fraction<1:raise ValueError('Curvature fraction must lie strictly inside (0,1).')
    lap,area=cotan_system(mesh)
    p=mesh.xyz/1000
    mean=.5*np.linalg.norm(lap@p,axis=1)/area
    tri=triangles(mesh);points=p[tri];angles=[]
    for j in range(3):
        a=points[:,(j+1)%3]-points[:,j];b=points[:,(j+2)%3]-points[:,j]
        cosine=(a*b).sum(1)/(np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1))
        angles.append(np.arccos(np.clip(cosine,-1,1)))
    angle_sum=np.bincount(tri.ravel(),weights=np.column_stack(angles).ravel(),minlength=len(p))
    gauss=(2*np.pi-angle_sum)/area
    maximum=(mean+np.sqrt(np.maximum(mean**2-gauss,0)))/1000
    # Lumped barycentric areas, not Meyer's complete mixed-Voronoi estimator.
    # A model-unit regularizer limits huge offsets on perfectly flat regions.
    bound=fraction/np.sqrt(maximum**2+(1/1000)**2)
    return bound,maximum


def diffuse_field(mesh,values,length):
    """One backward-Euler scalar diffusion step, not smoothing delivered xyz."""
    if not np.isfinite(length) or length<=0:raise ValueError('Positive finite diffusion length required.')
    lap,area=cotan_system(mesh)
    system=diags(area)+(length/1000)**2*lap
    rhs=area[:,None]*values if values.ndim==2 else area*values
    out=spsolve(system.tocsc(),rhs)
    residual=float(np.linalg.norm(system@out-rhs)/max(np.linalg.norm(rhs),1e-15))
    if not np.isfinite(out).all():raise ValueError('Nonfinite diffusion field; no fallback.')
    return out,residual


def transport_coordinates(coordinates,state,mesh,method='material'):
    if method=='coupled_cc':
        # Apply the unchanged zero-weight operator to scalar coordinates too.
        # It moves old samples with the same vertex stencil as delivered xyz,
        # whereas the original material interpolation deliberately retains them.
        # Geometry-derived normals/scales are multiplied by zero in this call.
        if coordinates.shape[1]>3:raise ValueError('At most three coordinate channels admitted.')
        from .reference_subdivision import subdivide
        padded=np.zeros_like(mesh.xyz);padded[:,:coordinates.shape[1]]=coordinates
        out,_,_=subdivide(replace(mesh,xyz=padded),{})
        return out.xyz[:,:coordinates.shape[1]]
    if method!='material':raise ValueError('Unknown coordinate transport method.')
    edges=state['input_edges'];mask=mesh.faces>=0
    face=np.zeros((len(mesh.faces),coordinates.shape[1]))
    for j in range(coordinates.shape[1]):
        face[:,j]=(coordinates[np.maximum(mesh.faces,0),j]*mask).sum(1)/mask.sum(1)
    return np.concatenate([coordinates,coordinates[edges].mean(1),face])
