"""Closed coarse geometry, actual solid CSG and real descendant subdivision.

No historic column, relief texture or final geometry pullback is read here.
"""
from pathlib import Path
import os
import sys
import numpy as np

_DLL_HANDLES=[]
_MANIFOLD=None


def manifold_module():
    global _MANIFOLD
    if _MANIFOLD is None:
        deps=Path(r'C:/Users/USER/CHESHIRE/scratch/grotesque_gate_20261010/deps')
        if os.name=='nt':_DLL_HANDLES.append(os.add_dll_directory(str(deps)))
        sys.path.insert(0,str(deps))
        import manifold3d
        _MANIFOLD=manifold3d
    return _MANIFOLD


def unit(a):
    a=np.asarray(a,float)
    n=np.linalg.norm(a,axis=-1,keepdims=True)
    if np.any(n<1e-12):raise ValueError('A geometric frame direction vanished.')
    return a/n


def _profile(a,n,name):
    a=np.broadcast_to(np.asarray(a,float),(n,)).copy()
    if not np.isfinite(a).all():raise ValueError('Nonfinite '+name)
    return a


def orient(x,t):
    x=np.asarray(x,np.float64);t=np.asarray(t,np.int64)
    p=x[t]
    areas=np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)
    if not np.isfinite(x).all() or np.any(areas<1e-14):
        raise ValueError('Invalid or degenerate closed input surface.')
    volume=np.einsum('ij,ij->',p[:,0],np.cross(p[:,1],p[:,2]))/6
    if volume<0:t=t[:,::-1].copy()
    if abs(volume)<1e-12:raise ValueError('A coarse solid has no positive volume.')
    return x,t


def loft_closed_ribbon(centerline,width,thickness,lateral,
                       across_curvature=0.,samples_across=12):
    c=np.asarray(centerline,float);n=len(c)
    if c.shape!=(n,3) or n<3:raise ValueError('A ribbon needs at least three centres.')
    tangent=unit(np.gradient(c,axis=0))
    lat=np.broadcast_to(np.asarray(lateral,float),(n,3)).copy()
    lat-=np.sum(lat*tangent,axis=1)[:,None]*tangent
    lat=unit(lat);normal=unit(np.cross(tangent,lat))
    w=_profile(width,n,'width');h=_profile(thickness,n,'thickness')
    bend=_profile(across_curvature,n,'cross curvature')
    if min(w.min(),h.min())<=0:raise ValueError('Positive ribbon width and thickness required.')
    u=np.linspace(-1,1,int(samples_across));m=len(u)
    if m<3:raise ValueError('A folded sheet needs three transverse samples.')
    middle=c[:,None]+u[None,:,None]*w[:,None,None]*lat[:,None]
    middle+=(u*u)[None,:,None]*bend[:,None,None]*normal[:,None]
    top=middle+h[:,None,None]*normal[:,None]/2
    bottom=middle-h[:,None,None]*normal[:,None]/2
    x=np.concatenate([top.reshape(-1,3),bottom.reshape(-1,3)])
    grid=np.arange(n*m).reshape(n,m)
    a,b,d,e=grid[:-1,:-1].ravel(),grid[1:,:-1].ravel(),grid[1:,1:].ravel(),grid[:-1,1:].ravel()
    surf=np.concatenate([np.column_stack([a,b,d]),np.column_stack([a,d,e])])
    # Each oriented boundary edge is used oppositely by the side wall.
    edges=np.concatenate([surf[:,[0,1]],surf[:,[1,2]],surf[:,[2,0]]])
    keys=np.sort(edges,axis=1)
    _,inv,count=np.unique(keys,axis=0,return_inverse=True,return_counts=True)
    edge=edges[count[inv]==1];a,b=edge.T;K=n*m
    walls=np.concatenate([np.column_stack([b,a,a+K]),np.column_stack([b,a+K,b+K])])
    t=np.concatenate([surf,(surf+K)[:,::-1],walls])
    return orient(x,t)


def loft_closed_tube(centerline,radius,sides=16):
    c=np.asarray(centerline,float);n=len(c);r=_profile(radius,n,'tube radius')
    if n<3 or r.min()<=0:raise ValueError('Positive tube radii and a path required.')
    tangent=unit(np.gradient(c,axis=0))
    frames=[]
    previous=np.array([1.,0.,0.])
    for d in tangent:
        q=previous-d*np.dot(previous,d)
        if np.linalg.norm(q)<.1:
            trial=np.array([0.,1.,0.]);q=trial-d*np.dot(trial,d)
        q=unit(q);frames.append(q);previous=q
    lat=np.asarray(frames);up=np.cross(tangent,lat)
    angles=np.arange(sides)*2*np.pi/sides
    rings=c[:,None]+r[:,None,None]*(np.cos(angles)[None,:,None]*lat[:,None]+
        np.sin(angles)[None,:,None]*up[:,None])
    x=np.concatenate([rings.reshape(-1,3),c[[0,-1]]])
    ids=np.arange(n*sides).reshape(n,sides)
    a=ids[:-1].ravel();b=ids[1:].ravel();d=np.roll(ids[1:],-1,axis=1).ravel();e=np.roll(ids[:-1],-1,axis=1).ravel()
    t=np.concatenate([np.column_stack([a,d,b]),np.column_stack([a,e,d]),
        np.column_stack([np.full(sides,n*sides),np.roll(ids[0],-1),ids[0]]),
        np.column_stack([np.full(sides,n*sides+1),ids[-1],np.roll(ids[-1],-1)])])
    return orient(x,t)


def closed_sheet(middle,thickness):
    """Thicken an actual two-parameter macro sheet and close all four rims."""
    p=np.asarray(middle,float)
    if p.ndim!=3 or p.shape[2]!=3 or min(p.shape[:2])<3:
        raise ValueError('A finite N by M macro sheet is required.')
    n,m=p.shape[:2]
    normal=unit(np.cross(np.gradient(p,axis=0),np.gradient(p,axis=1)))
    h=np.broadcast_to(np.asarray(thickness,float),(n,m))
    if not np.isfinite(h).all() or h.min()<=0:raise ValueError('Positive sheet thickness required.')
    x=np.concatenate([(p+h[:,:,None]*normal/2).reshape(-1,3),
                      (p-h[:,:,None]*normal/2).reshape(-1,3)])
    grid=np.arange(n*m).reshape(n,m)
    a,b,d,e=grid[:-1,:-1].ravel(),grid[1:,:-1].ravel(),grid[1:,1:].ravel(),grid[:-1,1:].ravel()
    surf=np.concatenate([np.column_stack([a,b,d]),np.column_stack([a,d,e])])
    edge=np.concatenate([surf[:,[0,1]],surf[:,[1,2]],surf[:,[2,0]]])
    _,inv,count=np.unique(np.sort(edge,axis=1),axis=0,return_inverse=True,return_counts=True)
    a,b=edge[count[inv]==1].T;K=n*m
    walls=np.concatenate([np.column_stack([b,a,a+K]),np.column_stack([b,a+K,b+K])])
    return orient(x,np.concatenate([surf,(surf+K)[:,::-1],walls]))


def to_manifold(x,t):
    m=manifold_module();x,t=orient(x,t)
    solid=m.Manifold(m.Mesh64(np.ascontiguousarray(x,np.float64),np.ascontiguousarray(t,np.uint64)))
    if solid.status()!=m.Error.NoError or solid.is_empty():
        raise ValueError('Native coarse input is not a valid nonempty solid: '+str(solid.status()))
    return solid


def from_manifold(solid):
    m=manifold_module()
    if solid.status()!=m.Error.NoError or solid.is_empty():
        raise ValueError('Solid CSG failed: '+str(solid.status()))
    mesh=solid.to_mesh64()
    return np.asarray(mesh.vert_properties[:,:3],np.float64).copy(),np.asarray(mesh.tri_verts,np.int64).copy()


def union_meshes(meshes):
    m=manifold_module()
    solids=[to_manifold(*p) for p in meshes]
    return from_manifold(m.Manifold.batch_boolean(solids,m.OpType.Add))


def union_components(parts):
    """Return geometry plus actual CSG source-part ID for every triangle."""
    m=manifold_module();solids=[];original={}
    for i,p in enumerate(parts):
        s=to_manifold(p['xyz'],p['faces']).as_original()
        original[s.original_id()]=i;solids.append(s)
    result=m.Manifold.batch_boolean(solids,m.OpType.Add)
    x,t=from_manifold(result)
    cleanup=[]
    for tolerance in (1e-8,1e-7):
        p=x[t]
        minimum=float(np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1).min()/2)
        if minimum>=1e-14:break
        before_count=len(t);before_volume=float(result.volume())
        result=result.simplify(tolerance)
        x,t=from_manifold(result)
        cleanup.append(dict(tolerance=tolerance,before_triangles=before_count,after_triangles=len(t),
            absolute_volume_change=abs(float(result.volume())-before_volume),
            reason='Remove numerical coplanar CSG slivers before descendant subdivision.'))
    mesh=result.to_mesh64()
    tags=np.full(len(t),-1,np.int32)
    run=np.asarray(mesh.run_index,dtype=np.int64)//3
    ids=np.asarray(mesh.run_original_id,dtype=np.int64)
    for a,b,oid in zip(run[:-1],run[1:],ids):tags[a:b]=original[int(oid)]
    if np.any(tags<0):raise ValueError('Every CSG triangle must retain its actual source part.')
    return x,t,tags,dict(status=str(result.status()),volume=float(result.volume()),
        source_parts=len(parts),actual_output_triangles=len(t),
        numerical_CSG_cleanup=cleanup,
        source_relation='Actual Manifold original-ID triangle run provenance; no nearest-surface inference.')


def reflect_mesh(x,t,normal,point=(0.,0.,0.)):
    n=unit(np.asarray(normal,float));p=np.asarray(point,float)
    x=np.asarray(x,float)
    return x-2*((x-p)@n)[:,None]*n,np.asarray(t,np.int64)[:,::-1].copy()


def cut_reflect_union(mesh,normal,point=(0.,0.,0.)):
    n=unit(np.asarray(normal,float));p=np.asarray(point,float)
    solid=to_manifold(*mesh)
    half=solid.trim_by_plane(tuple(n),float(n@p))
    original=from_manifold(half)
    reflected=reflect_mesh(*original,n,p)
    return union_meshes([original,reflected])


def real_subdivide(x,t,passes=2):
    """Actual neutral Catmull-Clark; triangle parent -> quads -> child quads."""
    repo=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(repo/'src'))
    from cheshire.reference_subdivision import ArrayMesh,subdivide,topology
    q=np.column_stack([np.asarray(t,np.int64),-np.ones(len(t),np.int64)])
    mesh=ArrayMesh(np.asarray(x,float),q,np.full(len(x),-1,np.int8),
        np.asarray(x,float).copy(),np.full((len(q),3),-1,np.int64),0)
    ancestry=np.arange(len(t));records=[]
    for g in range(int(passes)):
        out,meta,state=subdivide(mesh,{'weights':{}})
        ancestry=ancestry[state['parent_face']]
        topology(out)
        records.append(dict(generation=g+1,vertices=len(out.xyz),quads=len(out.faces),
            operator=meta,actual_parent_face=state['parent_face']))
        mesh=out
    q=mesh.faces
    centres=mesh.xyz[q].mean(1)
    native_x=np.concatenate([mesh.xyz,centres])
    native_t=np.column_stack([q.ravel(),np.roll(q,-1,axis=1).ravel(),
        np.repeat(len(mesh.xyz)+np.arange(len(q)),4)])
    return mesh,native_x,native_t,ancestry,records
