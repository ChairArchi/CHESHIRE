from . import runtime
import numpy as np,trimesh,manifold3d as md
from cheshire.reference_subdivision import ArrayMesh,topology,fields,mean_incident

def array_mesh(m):
    f=np.column_stack([m.faces,np.full(len(m.faces),-1,np.int64)])
    return ArrayMesh(np.array(m.vertices),f,np.full(len(m.vertices),-1,np.int8),np.array(m.vertices),np.full((len(f),3),-1,np.int64))
def triangles(a):
    fs=[]
    for q in a.faces:
        q=q[q>=0]
        for k in range(1,len(q)-1):fs.append([q[0],q[k],q[k+1]])
    return trimesh.Trimesh(a.xyz,np.array(fs),process=False)
def solid(m):
    s=md.Manifold(md.Mesh64(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.uint64)))
    if s.status()!=md.Error.NoError:raise ValueError('Manifold rejected surface: '+str(s.status()))
    return s
def from_solid(s):
    if s.status()!=md.Error.NoError or s.is_empty():raise ValueError('Boolean failed or empty: '+str(s.status()))
    raw=s.to_mesh64();return trimesh.Trimesh(np.array(raw.vert_properties)[:,:3],np.array(raw.tri_verts),process=False)
def components(m):
    return trimesh.graph.connected_components(m.face_adjacency,nodes=np.arange(len(m.faces)))
def check(m,max_faces):
    if len(m.faces)>max_faces:raise ValueError('Face budget exceeded')
    if not np.isfinite(m.vertices).all() or len(m.faces)==0:raise ValueError('Nonfinite/empty geometry')
    edges,counts=np.unique(np.sort(m.edges,axis=1),axis=0,return_counts=True)
    info=dict(vertices=len(m.vertices),triangles=len(m.faces),watertight=bool(m.is_watertight),consistent_winding=bool(m.is_winding_consistent),boundary_edges=int((counts==1).sum()),nonmanifold_edges=int((counts>2).sum()),zero_area_faces=int((m.area_faces==0).sum()),min_face_area=float(m.area_faces.min()),components=len(components(m)),volume=float(m.volume))
    if not info['watertight'] or not info['consistent_winding'] or info['zero_area_faces'] or info['volume']<=0:raise ValueError('Invalid mesh '+str(info))
    return info

def prepare(g,cfg):
    m=g.mesh.copy();before=len(m.vertices);m.merge_vertices(digits_vertex=cfg['weld_digits']);valid=m.nondegenerate_faces();removed=int((~valid).sum());m.update_faces(valid);m.remove_unreferenced_vertices()
    cc=components(m);areas=[m.area_faces[c].sum() for c in cc];i=int(np.argmax(areas));fraction=float(areas[i]/sum(areas))
    if fraction<cfg['minimum_component_area_fraction']:raise ValueError('No dominant connected surface; explicit input preparation needed')
    m=m.submesh([cc[i]],append=True,repair=False)
    if m.volume<0:m.invert()
    before_fill=len(m.faces);area_before=float(m.area)
    if not m.is_watertight:trimesh.repair.fill_holes(m)
    fill_count=len(m.faces)-before_fill;fill_area=float(m.area)-area_before
    if fill_area>area_before*.005:raise ValueError('Boundary patch area exceeds 0.5 percent budget')
    check(m,1500000)
    s=solid(m).simplify(cfg['simplify_tolerance']);resolved=[cfg['simplify_tolerance']]
    if s.num_tri()>cfg.get('max_prepared_faces',6000):
        s=s.simplify(cfg['simplify_tolerance']*2);resolved.append(cfg['simplify_tolerance']*2)
    if s.num_tri()>cfg.get('max_prepared_faces',6000):raise ValueError('Prepared surface exceeds input complexity budget; use an explicit larger budget or coarser input')
    out=from_solid(s)
    return out,dict(original_vertices=before,welded_vertices=before-len(np.unique(g.mesh.vertices.round(cfg['weld_digits']),axis=0)),removed_degenerate_faces=removed,source_components=len(cc),retained_surface_area_fraction=fraction,removed_other_components=len(cc)-1,simplify_tolerance=cfg['simplify_tolerance'],resolved_simplify_tolerances=resolved,before_simplify_faces=len(m.faces),after_simplify_faces=len(out.faces),repair='Explicit trimesh triangle/quad hole patches only, maximum 0.5% source surface area; no arbitrary hole closure',patched_faces=fill_count,patched_area_fraction=fill_area/area_before,correspondence='Nearest original triangle centroid, spatial only; source surface coordinates drive geometry')

def opening_solid(g,retention):
    parts=[]
    ylo,yhi=g.mesh.bounds[:,1];pad=max(1.,yhi-ylo)
    for p in g.profiles:
        a=np.array(p['samples']);a=a[np.argsort(a[:,2])];center=a[:,:2].mean(1);a[:,0]=center+(a[:,0]-center)*retention;a[:,1]=center+(a[:,1]-center)*retention
        # Use the measured profile with explicit small top setback, not an imposed arch.
        top=p['bottom']+(p['top']-p['bottom'])*retention
        zs=np.unique(np.r_[p['bottom']-.015,a[(a[:,2]>p['bottom'])&(a[:,2]<top),2],top])
        l=np.interp(zs,a[:,2],a[:,0]);r=np.interp(zs,a[:,2],a[:,1])
        poly=np.vstack([np.column_stack([l,zs]),np.column_stack([r[::-1],zs[::-1]])])
        s=md.CrossSection([poly[::-1]]).extrude((yhi-ylo)+2*pad).rotate((90,0,0)).translate((0,yhi+pad,0))
        if s.is_empty():raise ValueError('Invalid opening guard')
        parts.append(s)
    return md.Manifold.batch_boolean(parts,md.OpType.Add)

def observe(m,g,config,rng):
    a=array_mesh(m);t=topology(a);f=fields(a,t);c=f['c'];n=f['nf']
    angles=f['angles']/180
    bend=angles[t['fe'][:,:3]].mean(1)
    role,distance,source=g.roles_at(c)
    gain=np.array(config['role_gain'])[role]
    gain*=np.exp(-np.maximum(distance-.08,0)*3)
    # Actual current tangent axis = longest triangle edge, not world-axis motif.
    tri=m.triangles;edge=np.stack([tri[:,1]-tri[:,0],tri[:,2]-tri[:,1],tri[:,0]-tri[:,2]],axis=1)
    tangent=edge[np.arange(len(c)),np.argmax(np.linalg.norm(edge,axis=2),axis=1)];tangent/=np.linalg.norm(tangent,axis=1)[:,None]
    near=np.full(len(c),np.inf)
    for p in g.profiles:
        prof=np.array(p['samples']);z=c[:,2];l=np.interp(z,prof[:,2],prof[:,0]);r=np.interp(z,prof[:,2],prof[:,1])
        dx=np.maximum(np.maximum(l-c[:,0],c[:,0]-r),0);dz=np.maximum(np.maximum(p['bottom']-z,z-p['top']),0)
        near=np.minimum(near,np.sqrt(dx*dx+dz*dz))
    gain*=.25+.75*np.clip(near/.08,0,1)
    signal=(.25+np.sqrt(np.clip(bend,0,1)))*gain
    # Seed only breaks priorities among geometry-dependent scores; no predesigned feature coordinates.
    score=signal*np.sqrt(f['area'])*(0.85+0.3*rng.random(len(c)))
    return dict(center=c,normal=n,tangent=tangent,bend=bend,gain=gain,score=score,role=role,source_distance=distance,source_face=source,local_scale=f['sf'],opening_distance=near)

def select(obs,number,spacing):
    order=np.argsort(-obs['score'],kind='stable');picked=[]
    for i in order:
        if obs['gain'][i]<=.01:continue
        if not picked or np.linalg.norm(obs['center'][picked]-obs['center'][i],axis=1).min()>spacing:
            picked.append(int(i))
            if len(picked)>=number:break
    return np.array(picked,int)
