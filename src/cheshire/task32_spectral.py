"""Opt-in lumped cotan eigenfields and our nonlinear harmonic displacement.

Standard generalized Laplacian eigenproblem, not Vallet/Levy's complete
out-of-core band solver or an exact ornamental formula from their paper.
"""
from dataclasses import replace
import numpy as np
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import eigsh
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
    normals=fields(mesh)['nv'];xyz=mesh.xyz+amplitude*scalar[:,None]*normals
    state.update(coordinates=coordinates,field=scalar,normals=normals,displacement=xyz-mesh.xyz)
    meta.update(mechanism='cotan eigenfield / transported nonlinear phase displacement',spec=spec,
        amplitude=amplitude,level=level,topology_changed=False,
        caveat='Own normal displacement application; not physical folds, emergent topology, or unique canonical eigenbasis.')
    return replace(mesh,xyz=xyz),meta,state


def transport_coordinates(coordinates,state,mesh):
    edges=state['input_edges'];mask=mesh.faces>=0
    face=np.zeros((len(mesh.faces),coordinates.shape[1]))
    for j in range(coordinates.shape[1]):
        face[:,j]=(coordinates[np.maximum(mesh.faces,0),j]*mask).sum(1)/mask.sum(1)
    return np.concatenate([coordinates,coordinates[edges].mean(1),face])
