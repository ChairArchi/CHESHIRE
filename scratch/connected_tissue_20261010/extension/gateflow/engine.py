"""Small composable mesh-growth engine using existing CHESHIRE operators."""
from . import runtime
import numpy as np,trimesh
from scipy.sparse import coo_matrix,diags
from scipy.sparse.linalg import spsolve
from scipy.spatial import cKDTree
from cheshire.reference_subdivision import ArrayMesh,topology,fields,subdivide,mean_incident
from cheshire.polygon_dual_subdivision import doo_sabin
from cheshire.mola import extrude_tapered_once
from cheshire.execution import ExecutionBudget
from compas.datastructures import Mesh
import manifold3d as md
import igl
from .symmetry import symmetric_displacement

def surface(m):
    verts=m.xyz.tolist();faces=[]
    for q in m.faces:
      q=q[q>=0]
      if len(q)==3:faces.append(q.tolist())
      elif len(q)==4:
        a,b,c,d=q;ac=np.linalg.norm(m.xyz[a]-m.xyz[c]);bd=np.linalg.norm(m.xyz[b]-m.xyz[d])
        def key(i,j):
            v=m.xyz[[i,j]].copy();v[:,0]=np.abs(v[:,0]);return tuple(sorted(map(tuple,np.round(v,10))))
        diag_ac=ac<bd-1e-10 or (abs(ac-bd)<=1e-10 and key(a,c)<=key(b,d))
        faces.extend([[a,b,c],[a,c,d]] if diag_ac else [[a,b,d],[b,c,d]])
      else:
        v=len(verts);verts.append(m.xyz[q].mean(0).tolist())
        faces.extend([[int(a),int(b),v] for a,b in zip(q,np.roll(q,-1))])
    return trimesh.Trimesh(np.array(verts),np.array(faces),process=False)
def from_tri(mesh,generation=0):
    x=np.array(mesh.vertices);q=np.column_stack([mesh.faces,np.full(len(mesh.faces),-1,int)])
    return ArrayMesh(x,q,np.full(len(x),-1,np.int8),x.copy(),np.full((len(q),3),-1,int),generation)
def validate(m,budget):
    if len(m.faces)>budget:raise ValueError('Polygon budget exceeded')
    topology(m);tm=surface(m)
    if not np.isfinite(m.xyz).all() or np.any(tm.area_faces==0) or not tm.is_watertight or not tm.is_winding_consistent or tm.volume<=0:raise ValueError('Invalid basic mesh geometry')
    return dict(vertices=len(m.xyz),polygons=len(m.faces),triangles=len(tm.faces),watertight=bool(tm.is_watertight),winding_consistent=bool(tm.is_winding_consistent),zero_area_faces=int((tm.area_faces==0).sum()),min_triangle_area=float(tm.area_faces.min()),volume=float(tm.volume),components=int(len(trimesh.graph.connected_components(tm.face_adjacency,nodes=np.arange(len(tm.faces))))))

def smooth_graph(values,m,radius):
    t=topology(m);e=t['edges'];length=np.linalg.norm(m.xyz[e[:,0]]-m.xyz[e[:,1]],axis=1)
    # Screened graph diffusion groups current neighboring geometry at a spatial scale.
    w=1/np.maximum(length,1e-4)**2
    A=coo_matrix((np.r_[w,w],(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),shape=(len(m.xyz),)*2).tocsr()
    L=diags(np.asarray(A.sum(1)).ravel())-A
    # cg avoids a dense factorization on later generations.
    from scipy.sparse.linalg import cg
    y,code=cg(diags(np.ones(len(m.xyz)))+(radius**2)*L,values,rtol=1e-5,maxiter=120)
    if code<0:raise ValueError('Graph field solver failed')
    return y

def observe(m,field,roles,cfg):
    t=topology(m);f=fields(m,t);q=m.faces;mask=q>=0;n=t['n']
    e=t['edges'];delta=m.xyz[e[:,1]]-m.xyz[e[:,0]]
    lap=mean_incident(m.xyz[e[:,::-1].ravel()],e.ravel(),len(m.xyz))-m.xyz
    signed=np.einsum('ij,ij->i',lap,f['nv'])/np.maximum(f['sv'],1e-10)
    smooth=smooth_graph(signed,m,cfg['field_radius'])
    centered=smooth-np.median(smooth);den=max(np.quantile(np.abs(centered),.9),1e-4)
    feedback=np.tanh(centered/den)
    tri=surface(m)
    if len(m.xyz)<=25000:
        pd1,pd2,k1,k2,bad=igl.principal_curvature(np.asarray(tri.vertices),np.asarray(tri.faces,dtype=np.int64),radius=3,useKring=True)
        curvature=np.nan_to_num((k1[:len(m.xyz)]+k2[:len(m.xyz)])*.5,nan=0.,posinf=0.,neginf=0.)
        curvature_backend='libigl principal_curvature radius=3'
    else:
        # Dense generations use linear-size cotangent mean-curvature evaluation.
        # Principal directions are intentionally unavailable here, not fabricated.
        v=np.asarray(tri.vertices);faces=np.asarray(tri.faces,dtype=np.int64)
        mass=igl.massmatrix(v,faces,igl.MASSMATRIX_TYPE_BARYCENTRIC).diagonal()
        hn=-(igl.cotmatrix(v,faces)@v)/(2*np.maximum(mass[:,None],1e-14))
        curvature=np.einsum('ij,ij->i',hn[:len(m.xyz)],f['nv']);curvature=np.nan_to_num(curvature)
        pd1=np.zeros_like(m.xyz);bad=[]
        curvature_backend='libigl cotmatrix + barycentric massmatrix; no principal directions on dense mesh'
    denom=max(float(np.quantile(np.abs(curvature),.9)),1e-8)
    libigl_signal=np.tanh(curvature/denom)
    feedback=.65*feedback+.35*libigl_signal
    active=(1-cfg['feedback'])*field+cfg['feedback']*feedback
    canonical=m.xyz.copy();canonical[:,0]=np.abs(canonical[:,0])
    positive=np.flatnonzero(m.xyz[:,0]>=-1e-10)
    # One canonical sample also resolves duplicated coincident cell vertices.
    active=active[positive[cKDTree(m.xyz[positive]).query(canonical)[1]]]
    face=(active[np.maximum(q,0)]*mask).sum(1)/n
    rg=np.array(cfg['region_gain'])[roles]
    fv=f['variation'];anisotropy=mean_incident(np.repeat(face,n),t['a'],len(m.xyz))
    return dict(t=t,f=f,field=active,face_field=face,role_gain=rg,signed_curvature=signed,feedback_signal=feedback,normal_variation=fv,libigl_curvature=curvature,libigl_bad_vertices=np.array(bad),principal_direction=pd1[:len(m.xyz)],curvature_backend=curvature_backend)

def transport(old,new,field):
    # Spatial correspondence only; no historical lineage claim.
    dist,idx=cKDTree(old.xyz).query(new.xyz,k=min(4,len(old.xyz)))
    if idx.ndim==1:return field[idx]
    w=1/np.maximum(dist,1e-9)**2;return (field[idx]*w).sum(1)/w.sum(1)
def role_transport(old,new,roles):
    oldf=fields(old)['c'];newf=fields(new)['c'];return roles[cKDTree(oldf).query(newf)[1]]

def regional_response(m,obs,spec):
    """Strength from declared opening, transported role boundaries and current geometry."""
    distance=np.full(len(m.xyz),np.inf)
    for profile in obs['openings']:
        for a,b in zip(profile,np.roll(profile,-1,axis=0)):
            edge=b-a;t=np.clip(((m.xyz[:,[0,2]]-a)@edge)/max(edge@edge,1e-12),0,1)
            distance=np.minimum(distance,np.linalg.norm(m.xyz[:,[0,2]]-(a+t[:,None]*edge),axis=1))
    opening=np.exp(-(distance/spec.get('opening_band',.07))**2)
    roles=obs['structural_roles'];ef=obs['t']['ef'];touched=np.zeros(len(m.faces))
    boundary=(roles[ef[:,0]]==2)!=(roles[ef[:,1]]==2)
    touched[ef[boundary].ravel()]=1
    transition=mean_incident(np.repeat(touched,obs['t']['n']),obs['t']['a'],len(m.xyz))
    transition=smooth_graph(transition,m,spec.get('transition_band',.065))
    transition=np.clip(transition/max(float(transition.max()),1e-8),0,1)
    feature=smooth_graph(np.abs(obs['signed_curvature'])+obs['normal_variation'],m,spec.get('feature_band',.035))
    low,high=np.quantile(feature,[.25,.9]);feature=np.clip((feature-low)/max(high-low,1e-8),0,1)
    upper=mean_incident(np.repeat((roles==2).astype(float),obs['t']['n']),obs['t']['a'],len(m.xyz))
    upper=smooth_graph(upper,m,spec.get('transition_band',.065))
    lintel=upper*np.exp(-(distance/spec.get('lintel_band',.20))**2)
    primary=1-(1-.85*opening)*(1-.9*transition)*(1-spec.get('lintel_weight',0.)*lintel)
    mask=primary+(1-primary)*spec.get('secondary_weight',.7)*feature
    gain=spec.get('quiet_gain',.25)+spec.get('active_gain',1.35)*mask
    return gain,dict(region_opening=opening,region_transition=transition,region_deformation=feature,region_mask=mask,region_gain=gain,region_primary=primary,region_lintel=lintel,region_upper=upper)

OPS={}
def op(n):
    def dec(f):OPS[n]=f;return f
    return dec
@op('cc')
def cc(m,obs,spec,attenuation,budget):
    t=obs['t'];f=obs['f'];signal=np.tanh(2*obs['face_field']);gain=obs['role_gain']
    if int((m.faces>=0).sum())>budget:raise ValueError('CC budget exceeded before allocation')
    base=spec.get('weights',{})
    wf=attenuation*gain*(base.get('wf',.15)+spec.get('contrast',.3)*signal)
    we=attenuation*(base.get('we',-.06)-spec.get('edge_contrast',.10)*np.abs(signal[t['ef']].mean(1)))
    wp=np.full(len(m.xyz),base.get('wp',.0))*attenuation
    region={}
    if spec.get('region_response',False):
        regional,region=regional_response(m,obs,spec);q=m.faces;mask=q>=0
        face_gain=(regional[np.maximum(q,0)]*mask).sum(1)/mask.sum(1)
        wf*=face_gain;we*=regional[t['edges']].mean(1);wp*=regional
    row={'weights':base}
    intrinsic=dict(field='NORMAL_VARIATION',controls={},lock_threshold=spec['fold_lock'],start=0) if 'fold_lock' in spec else None
    out,meta,state=subdivide(m,row,intrinsic=intrinsic,resolved_controls={'wf':wf,'we':we,'wp':wp})
    locks=state.get('vertex_lock_mask',np.zeros(len(m.xyz),bool))
    meta['locked_old_vertex_max_motion']=float(np.linalg.norm(out.xyz[:len(m.xyz)][locks]-m.xyz[locks],axis=1).max()) if locks.any() else None
    return out,meta,dict(resolved_wf=wf,resolved_we=we,parent_face=state['parent_face'],vertex_lock_mask=locks,**region)
def separate_vertex_fans(m):
    """Separate disconnected incident face cycles sharing only a vertex.
    Coordinates are unchanged. This is explicit topology normalization, not
    self-intersection repair or an unpublished porosity rule.
    """
    t=topology(m);q=m.faces;n=t['n'];hs=np.arange(len(t['a']));starts=np.r_[0,np.cumsum(n)[:-1]]
    slots=np.arange(q.shape[1])[None,:];prev=(starts[:,None]+(slots-1)%n[:,None])[t['mask']]
    pair=np.argsort(t['fe'][t['mask']],kind='stable').reshape(-1,2)
    opposite=np.empty(len(hs),int);opposite[pair[:,0]]=pair[:,1];opposite[pair[:,1]]=pair[:,0]
    successor=opposite[prev];visited=np.zeros(len(hs),bool);first=np.zeros(len(m.xyz),bool)
    assigned=np.empty(len(hs),int);extra=[]
    for h in hs:
        if visited[h]:continue
        v=int(t['a'][h]);new=v
        if first[v]:new=len(m.xyz)+len(extra);extra.append(v)
        first[v]=True;k=int(h)
        while not visited[k]:visited[k]=True;assigned[k]=new;k=int(successor[k])
        if k!=h:raise ValueError('Invalid vertex permutation')
    if not extra:return m,0
    ids=np.r_[np.arange(len(m.xyz)),extra];faces=q.copy();faces[t['mask']]=assigned
    return ArrayMesh(m.xyz[ids],faces,m.classes[ids],m.rest[ids],m.anchors.copy(),m.generation),len(extra)

@op('ds')
def ds(m,obs,spec,attenuation,budget):
    m,fan_splits=separate_vertex_fans(m)
    if len(obs['t']['edges'])+len(m.faces)+len(m.xyz)>budget:raise ValueError('DS budget exceeded before allocation')
    f=obs['face_field'];gain=obs['role_gain']
    w1=spec.get('w1',.4)+spec.get('contrast',.25)*np.tanh(2*f)
    wf=attenuation*gain*(spec.get('wf',.10)+spec.get('normal_contrast',.15)*np.tanh(2*f))
    out,roles,meta,state=doo_sabin(m,{},resolved_controls={'w1':w1,'wf':wf})
    meta['disconnected_vertex_fans_separated']=fan_splits
    return out,meta,dict(parent_faces=state['parent_faces'],resolved_w1=w1,resolved_wf=wf)
@op('mola')
def mola(m,obs,spec,attenuation,budget):
    # Reuse adapter on planar eligible faces only; it never silently flattens a face.
    from cheshire.mola import eligible_planar_faces
    mesh=Mesh.from_vertices_and_faces(m.xyz.tolist(),[q[q>=0].tolist() for q in m.faces])
    eligible,excluded=eligible_planar_faces(mesh)
    score=obs['f']['area']*obs['role_gain']*(.25+np.abs(obs['face_field']))
    order=np.array(eligible)[np.argsort(-score[eligible],kind='stable')];picked=[]
    for i in order:
      if not picked or np.linalg.norm(obs['f']['c'][picked]-obs['f']['c'][i],axis=1).min()>spec.get('spacing',.065):
        picked.append(int(i))
        if len(picked)>=spec.get('count',80):break
    hr={i:float(np.clip(attenuation*spec.get('height_ratio',.5)*(.7+.3*obs['face_field'][i]),.005,.5)) for i in picked}
    fraction={i:float(np.clip(spec.get('fraction',.35)+.2*obs['face_field'][i],.05,.8)) for i in picked}
    result=extrude_tapered_once(mesh,selected_faces=picked,height_ratio=hr,fraction=fraction,dll_path=runtime.REPO.parent/'Libraries/HDMola/1.0.0/HDMola.dll',budget=ExecutionBudget(budget,budget),source_is_result=True)
    v,fs=result.mesh.to_vertices_and_faces();q=np.full((len(fs),max(4,max(map(len,fs)))),-1,int)
    for i,f in enumerate(fs):q[i,:len(f)]=f
    out=ArrayMesh(np.array(v),q,np.full(len(v),-1,np.int8),np.array(v),np.full((len(q),3),-1,int),m.generation+1)
    return out,dict(backend=result.backend,selected=len(picked),excluded_nonplanar=len(excluded)),dict(selected_faces=np.array(picked),height_ratio=np.array(list(hr.values())),fraction=np.array(list(fraction.values())))
@op('domains')
def domains(m,obs,spec,attenuation,budget):
    from cheshire.freedom_domains import step
    tri=surface(m)
    if len(tri.faces)*4>budget:raise ValueError('Domain refinement budget exceeded')
    out,meta,state=step(from_tri(tri,m.generation),radius=spec.get('radius',.22),angle=spec.get('angle',1.1)*attenuation,spacing=spec.get('spacing',.9),direction=spec.get('direction','transverse'),source='current',seed_quantile=.75,power=4)
    return out,meta,dict(selected_edges=state['selected_seed_edges'],axes=state['domain_axes'],origins=state['domain_origins'],displacement=state['resolved_displacement'])
@op('relax')
def relax(m,obs,spec,attenuation,budget):
    # Existing trimesh Taubin smoothing: geometry cleanup, not a claim of validity repair.
    tri=surface(m);trimesh.smoothing.filter_taubin(tri,lamb=.35,nu=.36,iterations=spec.get('iterations',4))
    return from_tri(tri,m.generation+1),dict(operator='trimesh.filter_taubin'),{}
@op('fuse')
def fuse(m,obs,spec,attenuation,budget):
    # Optional explicit mesh -> voxel occupancy -> isosurface conversion.
    from scipy.ndimage import gaussian_filter,binary_fill_holes,label
    from skimage.measure import marching_cubes
    tri=surface(m);pitch=spec.get('pitch',.006)
    if np.prod(np.ceil(tri.extents/pitch)+6)>100000000:raise ValueError('Voxel memory budget exceeded')
    if spec.get('bounded_voxelization',False):
        # Same upstream subdivide surface sampler, in bounded triangle batches.
        # Shared global voxel origin permits exact union of the sampled indices.
        from scipy.ndimage import binary_fill_holes
        from trimesh.voxel import VoxelGrid
        from trimesh.voxel.encoding import DenseEncoding
        lower=np.floor(tri.bounds[0]/pitch).astype(int)-3;upper=np.ceil(tri.bounds[1]/pitch).astype(int)+3
        occupancy=np.zeros(tuple(upper-lower+1),bool)
        for start in range(0,len(tri.faces),1024):
            ff=tri.faces[start:start+1024];verts=tri.vertices[ff].reshape(-1,3)
            chunk=trimesh.Trimesh(verts,np.arange(len(verts)).reshape(-1,3),process=False)
            sparse=chunk.voxelized(pitch,method='subdivide')
            index=np.rint(sparse.points/pitch).astype(int)-lower;occupancy[tuple(index.T)]=True
        occupancy=binary_fill_holes(occupancy)
        transform=np.eye(4);transform[:3,:3]*=pitch;transform[:3,3]=lower*pitch
        vox=VoxelGrid(DenseEncoding(occupancy),transform=transform)
    else:vox=tri.voxelized(pitch,method='subdivide').fill()
    occ=np.pad(vox.matrix,3)
    core_count=0
    if spec.get('retain_core',0)>0:
        from scipy.ndimage import distance_transform_edt
        src=surface(obs['input_mesh']).voxelized(pitch,method='subdivide').fill()
        keep=distance_transform_edt(src.matrix)*pitch>=spec['retain_core']
        pts=src.indices_to_points(np.argwhere(keep))
        ii=np.rint((pts-vox.transform[:3,3])/pitch).astype(int)+3
        valid=((ii>=0)&(ii<np.array(occ.shape))).all(1);ii=ii[valid];occ[tuple(ii.T)]=True;core_count=len(ii)
    field=gaussian_filter(occ.astype(np.float32),spec.get('sigma',.7))
    v,f,_,_=marching_cubes(field,.5,spacing=(pitch,)*3,allow_degenerate=False)
    v+=vox.transform[:3,3]-3*pitch
    tm=trimesh.Trimesh(v,f,process=False)
    if tm.volume<0:tm.invert()
    before_simplify=len(tm.faces)
    sm=md.Manifold(md.Mesh64(np.asarray(tm.vertices),np.asarray(tm.faces,dtype=np.uint64))).simplify(pitch*.18)
    if sm.status()!=md.Error.NoError:raise ValueError('Volumetric surface rejected by Manifold')
    simplify_tolerance=pitch*.18
    while sm.num_tri()>budget*.85 and simplify_tolerance<pitch*.65:
        simplify_tolerance*=1.4;sm=sm.simplify(simplify_tolerance)
    raw=sm.to_mesh64();tm=trimesh.Trimesh(np.array(raw.vert_properties)[:,:3],np.array(raw.tri_verts),process=False)
    return from_tri(tm,m.generation+1),dict(operator='trimesh.voxelized.fill + scipy.gaussian_filter + skimage.marching_cubes',pitch=pitch,extracted_triangles=before_simplify,simplify_tolerance=simplify_tolerance,retained_input_core_voxels=core_count,lineage='Explicit representation reset; cavities below pitch may disappear'),{}

@op('flow')
def flow(m,obs,spec,attenuation,budget):
    # Coherent displacement, directed by current surface normals and a graph field.
    # No world-coordinate ornament functions or preconstructed curves.
    field=smooth_graph(obs['field'],m,spec.get('radius',.18))
    field=np.tanh(field/max(float(np.std(field)),.08))
    n=obs['f']['nv'];normal=np.column_stack([smooth_graph(n[:,k],m,.045) for k in range(3)])
    normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-8)
    delta=attenuation*spec.get('amplitude',.10)*field[:,None]*normal
    # Bound each proposal relative to local material thickness scale, not a final motif.
    out=ArrayMesh(m.xyz+delta,m.faces.copy(),m.classes.copy(),m.rest.copy(),m.anchors.copy(),m.generation+1)
    return out,dict(operator='screened current graph-field normal flow',amplitude=spec.get('amplitude',.10)),dict(field=field,displacement=delta)
@op('astra')
def astra(m,obs,spec,attenuation,budget):
    from cheshire.astra_adaptive import step
    tri=surface(m)
    if len(tri.faces)*3>budget:raise ValueError('Astra allocation exceeds budget')
    out,meta,state=step(from_tri(tri,m.generation),fold=spec.get('fold',.4)*attenuation,relaxation=spec.get('relaxation',.015),feedback=1.6,bias=.05,selection='adaptive',hinge='dominant',source='current',quantile=.45)
    return out,meta,dict(selected_faces=state['selected_faces'],flipped_edges=state['flipped_edges'],offset=state['resolved_offset'])

@op('extrusion_growth')
def extrusion_growth(m,obs,spec,attenuation,budget):
    """Repeated real MOLA child-cap growth, with steering from current neighboring geometry."""
    from cheshire.mola import eligible_planar_faces
    tri=surface(m)
    mesh=Mesh.from_vertices_and_faces(tri.vertices.tolist(),tri.faces.tolist())
    eligible,_=eligible_planar_faces(mesh)
    start_centers=np.array([mesh.face_centroid(i) for i in mesh.faces()])
    mapped=cKDTree(obs['f']['c']).query(start_centers)[1]
    score=tri.area_faces*obs['role_gain'][mapped]*(.5+.5*obs['face_field'][mapped])
    if spec.get('frontier_only',False):eligible=[i for i in eligible if obs['frontier'][mapped[i]]]
    order=np.array(eligible)[np.argsort(-score[eligible],kind='stable')];caps=[]
    for i in order:
      if not caps or np.linalg.norm(start_centers[caps]-start_centers[i],axis=1).min()>spec.get('spacing',.12):
        caps.append(int(i))
        if len(caps)>=spec.get('count',24):break
    initial_caps=list(caps);growth_records=[];generated=set()
    if not caps:raise ValueError('No eligible growth faces for selected frontier')
    original_centers=obs['f']['c'];source_tree=cKDTree(original_centers)
    for generation in range(spec.get('rounds',7)):
      if not caps:break
      centers=np.array([mesh.face_centroid(i) for i in caps]);normals=np.array([mesh.face_normal(i) for i in caps])
      distances,idx=source_tree.query(centers);values=obs['face_field'][idx]
      heights={i:float(np.clip(attenuation*.5*(.8+.2*values[j]),.05,.5)) for j,i in enumerate(caps)}
      fractions={i:float(np.clip(spec.get('fraction',.10)+.035*values[j],.025,.2)) for j,i in enumerate(caps)}
      result=extrude_tapered_once(mesh,selected_faces=caps,height_ratio=heights,fraction=fractions,dll_path=runtime.REPO.parent/'Libraries/HDMola/1.0.0/HDMola.dll',budget=ExecutionBudget(budget,budget),source_is_result=True)
      nextmesh=result.mesh;children=[k for k,v in result.face_roles.items() if v=='cap']
      generated.intersection_update(set(nextmesh.faces()));generated.update(k for k,v in result.face_roles.items() if v in ('cap','side'))
      turns=[]
      # Cap and emitted side identities come from the actual MOLA result.
      for j,(parent,child) in enumerate(zip(caps,children)):
        n=normals[j];c=centers[j];keys=nextmesh.face_vertices(child);pts=np.array([nextmesh.vertex_coordinates(v) for v in keys]);pivot=pts.mean(0)
        others=centers-c;d=np.linalg.norm(others,axis=1);valid=(d>1e-5)&(d<spec.get('interaction_radius',.3))
        repulse=-(others[valid]/np.maximum(d[valid,None],.025)**3).sum(0) if valid.any() else np.zeros(3)
        # Current neighbor interaction and inherited scalar jointly change the direction.
        tangent=repulse-n*(repulse@n)
        # Libigl's direction is an unoriented line; align it with the local edge
        # before blending so its arbitrary sign cannot flip a growth trajectory.
        face=m.faces[idx[j]];face=face[face>=0]
        pd=obs['principal_direction'][face].mean(0);pd-=n*(pd@n)
        edge=m.xyz[face[1]]-m.xyz[face[0]]
        if pd@edge<0:pd=-pd
        tangent+=spec.get('principal_steering',.35)*pd/max(np.linalg.norm(pd),1e-8)
        if np.linalg.norm(tangent)<1e-8:
          verts=np.array([mesh.vertex_coordinates(v) for v in mesh.face_vertices(parent)]);tangent=verts[1]-verts[0]
        tangent/=max(np.linalg.norm(tangent),1e-8)
        axis=np.cross(n,tangent);axis/=max(np.linalg.norm(axis),1e-8)
        theta=spec.get('turn',.32)*attenuation*(.45+.55*values[j])
        rel=pts-pivot;new=pivot+rel*np.cos(theta)+np.cross(axis,rel)*np.sin(theta)+axis*(rel@axis)[:,None]*(1-np.cos(theta))
        for key,xyz in zip(keys,new):nextmesh.vertex_attributes(key,'xyz',xyz.tolist())
        turns.append(theta)
      mesh=nextmesh;caps=children;growth_records.append(dict(round=generation,children=len(caps),turn_min=float(min(turns)),turn_max=float(max(turns))))
    v,fs=mesh.to_vertices_and_faces();q=np.full((len(fs),max(4,max(map(len,fs)))),-1,int)
    for i,f in enumerate(fs):q[i,:len(f)]=f
    out=ArrayMesh(np.array(v),q,np.full(len(v),-1,np.int8),np.array(v),np.full((len(q),3),-1,int),m.generation+1)
    return out,dict(operator='Existing HDMola ExtrudeTapered, actual child cap iteration, current cap repulsion steering',rounds=growth_records,initial_cap_count=len(initial_caps)),dict(initial_cap_faces=np.array(initial_caps),generated_faces=np.array([i for i,k in enumerate(mesh.faces()) if k in generated],int))

@op('tissue')
def tissue(m,obs,spec,attenuation,budget):
    import subprocess,tempfile,json,os
    from pathlib import Path
    external=runtime.PROJECT/'external'
    blender=Path(os.environ.get('CHESHIRE_BLENDER',external/'blender-4.5.4-windows-x64/blender.exe'))
    if not blender.is_file():raise ValueError('Headless Blender missing: '+str(blender))
    if len(m.faces)>15000:raise ValueError('Tissue input budget is 15000 polygons; place before dense subdivision')
    temp_root=runtime.PROJECT/'worker_temp';temp_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temp_root) as folder:
        source=Path(folder)/'input.json';target=Path(folder)/'result.json'
        weights=np.clip(.7+.3*obs['field'],.05,1.)
        source.write_text(json.dumps(dict(external_root=str(external),vertices=m.xyz.tolist(),faces=[q[q>=0].tolist() for q in m.faces],weights=weights.tolist(),selection=np.clip(.5+.5*obs['field'],0,1).tolist(),thickness=spec.get('thickness',.01)*attenuation,selective=spec.get('selective','NONE'))))
        r=subprocess.run([str(blender),'--background','--factory-startup','--python-exit-code','1','--python',str(runtime.PROJECT/'gateflow/tissue_worker.py'),'--',str(source),str(target)],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=240,creationflags=0x08000000)
        if r.returncode or not target.is_file():raise RuntimeError('Tissue failed: '+r.stdout[-1800:]+r.stderr[-1200:])
        j=json.loads(target.read_text());v=np.array(j.pop('vertices'));fs=j.pop('faces');q=np.full((len(fs),max(4,max(map(len,fs)))),-1,int)
        for i,f in enumerate(fs):q[i,:len(f)]=f
        out=ArrayMesh(v,q,np.full(len(v),-1,np.int8),v.copy(),np.full((len(q),3),-1,int),m.generation+1)
        # Orientation of the upstream result is normalized as one whole surface.
        if surface(out).volume<0:out.faces=np.array([np.r_[r[r>=0][::-1],np.full((r<0).sum(),-1)] for r in out.faces])
        j.update(thickness=spec.get('thickness',.01)*attenuation,weights_min=float(weights.min()),weights_max=float(weights.max()),upstream_log=r.stdout)
        return out,j,dict(thickness_weights=weights)

@op('tessellate')
def tessellate(m,obs,spec,attenuation,budget):
    import subprocess,tempfile,json,os,hashlib
    from pathlib import Path
    external=runtime.PROJECT/'external';blender=Path(os.environ.get('CHESHIRE_BLENDER',external/'blender-4.5.4-windows-x64/blender.exe'))
    compath=Path(spec['component']);compath=compath if compath.is_absolute() else runtime.PROJECT/compath
    data=json.loads(compath.read_text());component=data['mesh']
    if data['schema']!='cheshire-component/1':raise ValueError('Invalid component contract')
    if np.any((m.faces>=0).sum(1)!=4):raise ValueError('Tissue component mapping currently requires a QUAD target; place CC before it')
    selected=np.ones(len(m.faces),bool)
    if 'projection_selection' in obs:
        selected=np.asarray(obs['projection_selection'],dtype=bool)
        if selected.shape!=(len(m.faces),) or not selected.any():raise ValueError('Invalid saved Tissue face selection')
    elif spec.get('selective',False):
        q=m.faces;mask=q>=0;curv=(np.abs(obs['libigl_curvature'])[np.maximum(q,0)]*mask).sum(1)/mask.sum(1)
        curv=np.clip(curv/max(float(np.quantile(curv,.95)),1e-8),0,1)
        centers=obs['f']['c'];distance=np.full(len(centers),np.inf)
        for profile in obs['openings']:
            for start,end in zip(profile,np.roll(profile,-1,axis=0)):
                edge=end-start;alpha=np.clip(((centers[:,[0,2]]-start)@edge)/max(edge@edge,1e-12),0,1)
                distance=np.minimum(distance,np.linalg.norm(centers[:,[0,2]]-(start+alpha[:,None]*edge),axis=1))
        opening=np.exp(-(distance/spec.get('opening_band',.10))**2)
        roles=obs['structural_roles'];ef=obs['t']['ef'];transition=np.zeros(len(m.faces));transition[ef[roles[ef[:,0]]!=roles[ef[:,1]]].ravel()]=1
        scores=.4*opening+.4*curv+.2*transition
        if spec.get('hierarchy_selection',False):
            _,region=regional_response(m,obs,spec);primary=region['region_primary'][q].mean(1)
            scores=(.75*primary+.25*curv)*np.clip(np.sqrt(obs['f']['area']/max(float(np.median(obs['f']['area'])),1e-12)),.5,1.5)
            scores[primary<.45]=0
        positive=np.flatnonzero(centers[:,0]>=-1e-10);canonical=centers.copy();canonical[:,0]=np.abs(canonical[:,0]);scores=scores[positive[cKDTree(centers[positive]).query(canonical)[1]]]
        fraction=min(spec.get('fraction',.18),spec.get('max_cells',5000)/len(scores));threshold=np.quantile(scores,1-fraction);selected=scores>=threshold
    if len(component['faces'])*int(selected.sum())+len(m.faces)>budget:raise ValueError('Component x selected target-face budget exceeded')
    temp_root=runtime.PROJECT/'worker_temp';temp_root.mkdir(exist_ok=True)
    weights=np.clip(.65+.35*obs['field'],0.,1.);rotation_weights=weights.copy()
    if spec.get('orientation')=='opening_flow':
        distances=np.full(len(m.xyz),np.inf);rotation_weights=np.zeros(len(m.xyz))
        for profile in obs['openings']:
            perimeter=sum(np.linalg.norm(b-a) for a,b in zip(profile,np.roll(profile,-1,axis=0)));offset=0.
            for a,b in zip(profile,np.roll(profile,-1,axis=0)):
                edge=b-a;length=np.linalg.norm(edge);t=np.clip(((m.xyz[:,[0,2]]-a)@edge)/max(edge@edge,1e-12),0,1)
                d=np.linalg.norm(m.xyz[:,[0,2]]-(a+t[:,None]*edge),axis=1);use=d<distances
                rotation_weights[use]=(offset+t[use]*length)/perimeter;distances=np.minimum(distances,d);offset+=length
        weights=.65+.35*np.clip(np.abs(obs['field']),0,1)
    with tempfile.TemporaryDirectory(dir=temp_root) as folder:
        source=Path(folder)/'input.json';target=Path(folder)/'result.json'
        source.write_text(json.dumps(dict(external_root=str(external),vertices=m.xyz.tolist(),faces=[q[q>=0].tolist() for q in m.faces],component=component,mapping=data.get('mapping',{}),selected=selected.tolist(),keep_target=spec.get('keep_target',False),combine_mode=spec.get('combine_mode','LAST'),weights=weights.tolist(),rotation_weights=rotation_weights.tolist(),rotation_shift=spec.get('rotation_shift',0),offset=spec.get('offset',0.),overlap=spec.get('overlap',1.15),depth=spec.get('depth',1.)*attenuation)))
        r=subprocess.run([str(blender),'--background','--factory-startup','--python-exit-code','1','--python',str(runtime.PROJECT/'gateflow/tessellate_worker.py'),'--',str(source),str(target)],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=240,creationflags=0x08000000)
        if r.returncode or not target.is_file():raise RuntimeError('Tissue tessellation failed: '+r.stdout[-1800:]+r.stderr[-1200:])
        j=json.loads(target.read_text());v=np.array(j.pop('vertices'));fs=j.pop('faces');q=np.full((len(fs),max(4,max(map(len,fs)))),-1,int)
        for i,f in enumerate(fs):q[i,:len(f)]=f
        out=ArrayMesh(v,q,np.full(len(v),-1,np.int8),v.copy(),np.full((len(q),3),-1,int),m.generation+1)
        if spec.get('keep_target',False):
            offset=j['retained_target_vertex_offset']
            error=float(np.max(np.abs(v[offset:]-m.xyz)))
            same_faces=np.array_equal(q[-len(m.faces):,:m.faces.shape[1]]-offset,m.faces)
            if error!=0 or not same_faces:raise ValueError('Tissue changed retained target geometry')
            j.update(retained_target_max_coordinate_error=error,retained_target_topology_identical=bool(same_faces),target_preservation_scope='Before symmetry enforcement and final opening Boolean')
        j.update(selected_target_faces=int(selected.sum()),selection_rule='current curvature + opening proximity + structural transition' if spec.get('selective') else 'all faces',keep_target=spec.get('keep_target',False),component_sha256=hashlib.sha256(compath.read_bytes()).hexdigest(),component_input=str(compath),depth=spec.get('depth',1.)*attenuation,depth_weight_min=float(weights.min()),depth_weight_max=float(weights.max()),orientation=spec.get('orientation','current_field'),upstream_log=r.stdout)
        return out,j,dict(selected_target_faces=selected,depth_weights=weights,rotation_weights=rotation_weights,component_xyz=np.array(component['vertices']),component_faces=np.array(component['faces']))

@op('fold_field')
def fold_field(m,obs,spec,attenuation,budget):
    # Reuses the finite-rotation/taper construction of freedom_domains.step,
    # evaluated on existing vertices without its obligatory 4x refinement.
    # Euclidean neighborhoods intentionally couple adjacent projected cells.
    t=obs['t'];f=obs['f'];edges=t['edges'];centers=m.xyz[edges].mean(1)
    bend=np.radians(f['angles']);edge_field=obs['field'][edges].mean(1)
    score=(.15+bend)*np.sqrt(f['lengths'])*(.35+np.abs(edge_field))
    order=np.argsort(-score,kind='stable');radius=spec.get('radius',.08)
    chosen=[];tree=cKDTree(m.xyz);accum=np.zeros_like(m.xyz);total=np.zeros(len(m.xyz));axes=[];angles=[]
    for seed in order:
        origin=centers[seed]
        if chosen and np.linalg.norm(centers[chosen]-origin,axis=1).min()<radius*.8:continue
        axis=m.xyz[edges[seed,1]]-m.xyz[edges[seed,0]];axis/=max(np.linalg.norm(axis),1e-12)
        normal=f['nf'][t['ef'][seed]].sum(0);normal/=max(np.linalg.norm(normal),1e-12)
        transverse=np.cross(normal,axis);transverse/=max(np.linalg.norm(transverse),1e-12)
        direction=spec.get('direction_phase',0.)+1.2*edge_field[seed]
        axis=axis*np.cos(direction)+transverse*np.sin(direction);axis/=max(np.linalg.norm(axis),1e-12)
        side=np.cross(normal,axis);ids=np.array(tree.query_ball_point(origin,radius),int)
        delta=m.xyz[ids]-origin;dist=np.linalg.norm(delta,axis=1);taper=(1-(dist/radius)**2)**2
        strength=attenuation*spec.get('angle',.9)*(.25+.75*abs(edge_field[seed]))
        theta=strength*np.tanh(5*(delta@side)/radius)*taper
        co=np.cos(theta)[:,None];si=np.sin(theta)[:,None]
        move=delta*co+np.cross(axis,delta)*si+axis*(delta@axis)[:,None]*(1-co)-delta
        weight=taper**3*(.1+bend[seed]);accum[ids]+=move*weight[:,None];total[ids]+=weight
        chosen.append(int(seed));axes.append(axis);angles.append(strength)
        if len(chosen)>=spec.get('domains',100):break
    displacement=np.divide(accum,total[:,None],out=np.zeros_like(accum),where=total[:,None]>0)
    displacement=symmetric_displacement(m,displacement)
    out=ArrayMesh(m.xyz+displacement,m.faces.copy(),m.classes.copy(),m.rest.copy(),m.anchors.copy(),m.generation+1)
    return out,dict(operator='Current-geometry weighted local finite rotations, adapted from CHESHIRE Freedom',neighborhood='Euclidean, couples adjacent cells; no claim of graph geodesic equivalence',selected_domains=len(chosen),angle_min=float(min(angles)),angle_max=float(max(angles))),dict(seed_edges=np.array(chosen),axes=np.array(axes),angles=np.array(angles),displacement=displacement)

@op('section_articulate')
def section_articulate(m,obs,spec,attenuation,budget):
    """Coarse support-section compression/expansion before detail generation."""
    knots=np.asarray(spec['knots'],float);scales=np.asarray(spec['scales'],float)
    if len(knots)!=len(scales) or np.any(np.diff(knots)<=0) or np.min(scales)<=0:raise ValueError('Invalid section profile')
    move=np.zeros_like(m.xyz);resolved=np.ones(len(m.xyz));records=[]
    for role in (0,1):
        weights=mean_incident(np.repeat((obs['structural_roles']==role).astype(float),obs['t']['n']),obs['t']['a'],len(m.xyz))
        ids=np.flatnonzero(weights>(0 if spec.get('axis_from_all_role_vertices',False) else .95))
        if not len(ids):continue
        points=m.xyz[ids];lo=points.min(0);hi=points.max(0);center=(lo+hi)*.5
        h=np.clip((m.xyz[:,2]-lo[2])/max(hi[2]-lo[2],1e-9),0,1)
        profile=1+attenuation*(np.interp(h,knots,scales)-1)
        weight=weights*np.clip(h/.04,0,1)*np.clip((1-h)/.04,0,1)
        radial=m.xyz[:,:2]-center[:2]
        move[:,:2]+=radial*((profile-1)*weight)[:,None]
        if spec.get('axial_lift',0) or spec.get('wing_strength',0):
            theta=np.arctan2(radial[:,1],radial[:,0])
            angular=1-4*np.abs(np.mod(spec.get('lobes',4)*theta/(2*np.pi)+spec.get('angular_phase',.125)+spec.get('axial_phase_slope',0)*h,1)-.5)
            radius=np.linalg.norm(radial,axis=1);radial_weight=np.clip(radius/max(float(np.quantile(radius[ids],.9)),1e-9),0,1)
            expansion=np.clip((profile-1)/max(float(scales.max()-1),1e-9),0,1)
            move[:,2]+=attenuation*spec.get('axial_lift',0)*(hi[2]-lo[2])*weight*radial_weight*expansion*angular
            move[:,:2]+=radial*(attenuation*spec.get('wing_strength',0)*weight*expansion*np.maximum(angular,0))[:,None]
        resolved+=(profile-1)*weight
        records.append(dict(role=role,axis_xy=center[:2].tolist(),height_bounds=[float(lo[2]),float(hi[2])]))
    move=symmetric_displacement(m,move)
    out=ArrayMesh(m.xyz+move,m.faces.copy(),m.classes.copy(),m.rest.copy(),m.anchors.copy(),m.generation+1)
    return out,dict(operator='Piecewise-linear cross-section profile on current support axes; optional angular axial lift; topology unchanged',axes=records,scale_min=float(resolved.min()),scale_max=float(resolved.max()),axial_lift=spec.get('axial_lift',0)),dict(displacement=move,section_scale=resolved)

@op('normal_extrude')
def normal_extrude(m,obs,spec,attenuation,budget):
    # Hansmeyer-style vertex normal extrusion, separate from folding/smoothing.
    if spec.get('ridge_focus',False):
        convex=np.maximum(-obs['signed_curvature'],0.)
        ridge=np.clip(convex/max(float(np.quantile(convex,.9)),1e-8),0,1)**1.6
        gain=spec.get('amount',.3)*attenuation*ridge
    else:gain=spec.get('amount',.3)*attenuation*(.3+.7*obs['field'])
    region={}
    if spec.get('region_response',False):
        regional,region=regional_response(m,obs,spec);gain*=regional
    displacement=obs['f']['nv']*(obs['f']['sv']*gain)[:,None]
    displacement=symmetric_displacement(m,displacement)
    out=ArrayMesh(m.xyz+displacement,m.faces.copy(),m.classes.copy(),m.rest.copy(),m.anchors.copy(),m.generation+1)
    return out,dict(operator='Current vertex-normal extrusion scaled by current local edge scale',gain_min=float(gain.min()),gain_max=float(gain.max())),dict(displacement=displacement,resolved_gain=gain,**region)

@op('pleat_flow')
def pleat_flow(m,obs,spec,attenuation,budget):
    from scipy.sparse.linalg import spsolve
    from scipy.sparse.csgraph import dijkstra
    e=obs['t']['edges'];length=obs['f']['lengths'];nv=len(m.xyz)
    conductance=1/np.maximum(length,1e-7)
    graph=coo_matrix((np.r_[conductance,conductance],(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),shape=(nv,nv)).tocsr()
    lap=diags(np.asarray(graph.sum(1)).ravel())-graph
    z=m.xyz[:,2];low=z<=np.quantile(z,.035);high=z>=np.quantile(z,.965);fixed=low|high;free=~fixed
    u=high.astype(float);u[free]=spsolve(lap[free][:,free],-(lap[free][:,fixed]@u[fixed]))
    # A second intrinsic distance field bends the trajectories near the opening.
    distance=np.full(nv,np.inf)
    for profile in obs['openings']:
        for a,b in zip(profile,np.roll(profile,-1,axis=0)):
            edge=b-a;t=np.clip(((m.xyz[:,[0,2]]-a)@edge)/max(edge@edge,1e-12),0,1)
            distance=np.minimum(distance,np.linalg.norm(m.xyz[:,[0,2]]-(a+t[:,None]*edge),axis=1))
    seeds=np.flatnonzero(distance<=np.quantile(distance,.03))
    metric=coo_matrix((np.r_[length,length],(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),shape=(nv,nv)).tocsr()
    intrinsic=dijkstra(metric,directed=False,indices=seeds,min_only=True)
    intrinsic=smooth_graph(intrinsic,m,spec.get('flow_smoothing',0.)) if spec.get('flow_smoothing',0.)>0 else intrinsic
    across=intrinsic/max(float(np.quantile(intrinsic,.95)),1e-8)
    region={}
    if spec.get('region_response',False):spatial_gain,region=regional_response(m,obs,spec)
    angle=spec.get('flow_angle',0.)
    if region and 'lintel_angle' in spec:angle=angle*(1-region['region_upper'])+spec['lintel_angle']*region['region_upper']
    coordinate=np.cos(angle)*u+np.sin(angle)*across
    phase=spec.get('frequency',6.)*coordinate+spec.get('cross_flow',.7)*np.tanh(intrinsic/.16)+spec.get('phase',0.)
    # Sparse fan centers come from THIS surface's measured curvature, not authored coordinates.
    fan_centers=[];fan_potential=np.zeros(nv);fan_radius=spec.get('fan_radius',.16)
    salience=smooth_graph(np.abs(obs['libigl_curvature']),m,spec.get('feature_smoothing',.055))
    salience=np.clip(salience/max(float(np.quantile(salience,.9)),1e-8),0,1)
    if region and spec.get('hierarchical_flow',False):salience*=.1+.9*region['region_primary']
    if spec.get('fan_count',0):
        for idx in np.argsort(-salience,kind='stable'):
            if m.xyz[idx,0]<0:continue
            if all(np.linalg.norm(m.xyz[idx]-m.xyz[a])>fan_radius for a in fan_centers):fan_centers.append(int(idx))
            if len(fan_centers)>=spec['fan_count']:break
        positive=list(fan_centers)
        for idx in positive:
            mirror=m.xyz[idx].copy();mirror[0]*=-1;fan_centers.append(int(cKDTree(m.xyz).query(mirror)[1]))
        fan_centers=sorted(set(fan_centers))
        distances=dijkstra(metric,directed=False,indices=fan_centers)
        # Geodesic source/sink perturbations bend and bunch phase contours locally.
        strengths=np.tanh(smooth_graph(obs['signed_curvature'],m,.045)[fan_centers]*12)
        for dist,strength in zip(distances,strengths):fan_potential+=strength*np.exp(-.5*(dist/fan_radius)**2)
        phase+=spec.get('fan_strength',1.)*fan_potential
    triangle=1-4*np.abs(np.mod(phase,1.)-.5)
    normal=obs['f']['nv'];edgegrad=(u[e[:,1]]-u[e[:,0]])[:,None]*(m.xyz[e[:,1]]-m.xyz[e[:,0]])/np.maximum(length[:,None]**2,1e-12)
    gradient=mean_incident(np.repeat(edgegrad,2,axis=0),e.ravel(),nv)
    gradient-=normal*np.einsum('ij,ij->i',gradient,normal)[:,None];gradient/=np.maximum(np.linalg.norm(gradient,axis=1)[:,None],1e-12)
    regional_gain=1+spec.get('regional_contrast',0.)*(2*salience-1)
    base_scale=np.full(nv,spec['depth']) if 'depth' in spec else spec.get('amount',.6)*obs['f']['sv']
    if region:regional_gain*=spatial_gain
    scale=attenuation*base_scale*regional_gain;taper=.25+.75*np.sin(np.pi*u)**2
    delta=scale[:,None]*taper[:,None]*(normal*triangle[:,None]+spec.get('convergence',.5)*gradient*np.sin(2*np.pi*phase)[:,None])
    if region:delta-=normal*(attenuation*spec.get('quiet_recess',0.)*(1-region['region_mask'])**2)[:,None]
    delta=symmetric_displacement(m,delta)
    out=ArrayMesh(m.xyz+delta,m.faces.copy(),m.classes.copy(),m.rest.copy(),m.anchors.copy(),m.generation+1)
    return out,dict(operator='Harmonic-flow pleating with tangential convergence/divergence',flow_anchors='Current lower/upper 3.5% vertices in declared Z-up frame',opening_seeds=len(seeds),frequency=spec.get('frequency',6.),amount=spec.get('amount',.6)),dict(harmonic_flow=u,opening_geodesic=intrinsic,phase=phase,gradient=gradient,displacement=delta,fan_centers=np.array(fan_centers,int),fan_potential=fan_potential,regional_gain=regional_gain,**region)


@op('support_twist')
def support_twist(m,obs,spec,attenuation,budget):
    import subprocess,tempfile,json,os
    from pathlib import Path
    # Scope and origin derive from the current right support, then mirror displacement.
    support=mean_incident(np.repeat((obs['structural_roles']==1).astype(float),obs['t']['n']),obs['t']['a'],len(m.xyz))
    weight=np.clip(smooth_graph(support,m,spec.get('transition_width',.07)),0,1)
    ids=np.flatnonzero(support>.95)
    if not len(ids):raise ValueError('No current right-support vertices for twist')
    z=m.xyz[:,2];lo=float(z[ids].min());hi=float(z[ids].max());height=max(hi-lo,1e-8)
    h=np.clip((z-lo)/height,0,1)
    # Fade at the lintel; retain a quiet foot without erasing the support's relief.
    weight*=np.clip((1-h)/.25,0,1)**2*np.clip(h/.10,0,1)
    origin=np.average(m.xyz[ids],axis=0,weights=np.maximum(weight[ids],1e-5));origin[2]=lo
    temp_root=runtime.PROJECT/'worker_temp';temp_root.mkdir(exist_ok=True)
    blender=Path(os.environ.get('CHESHIRE_BLENDER',runtime.PROJECT/'external/blender-4.5.4-windows-x64/blender.exe'))
    with tempfile.TemporaryDirectory(dir=temp_root) as folder:
        source=Path(folder)/'input.json';target=Path(folder)/'result.json'
        source.write_text(json.dumps(dict(vertices=m.xyz.tolist(),faces=[f[f>=0].tolist() for f in m.faces],origin=origin.tolist(),weights=weight.tolist(),angle=spec.get('angle',1.5)*attenuation)))
        r=subprocess.run([str(blender),'--background','--factory-startup','--python-exit-code','1','--python',str(runtime.PROJECT/'gateflow/deform_worker.py'),'--',str(source),str(target)],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=120,creationflags=0x08000000)
        if r.returncode or not target.is_file():raise RuntimeError('Simple Deform failed: '+r.stdout[-1200:]+r.stderr[-1000:])
        data=json.loads(target.read_text());xyz=np.array(data.pop('vertices'));faces=data.pop('faces')
        if faces!=[q[q>=0].tolist() for q in m.faces] or xyz.shape!=m.xyz.shape:raise ValueError('Unexpected Simple Deform topology change')
        delta=symmetric_displacement(m,xyz-m.xyz)
        out=ArrayMesh(m.xyz+delta,m.faces.copy(),m.classes.copy(),m.rest.copy(),m.anchors.copy(),m.generation+1)
        data.update(angle=spec.get('angle',1.5)*attenuation,origin=origin.tolist(),scope='Current support role; smooth transition fade; reflected displacement',upstream_log=r.stdout)
        return out,data,dict(displacement=delta,twist_weight=weight,twist_origin=origin)


@op('crease_subdivide')
def crease_subdivide(m,obs,spec,attenuation,budget):
    import subprocess,tempfile,json,os
    from pathlib import Path
    if int((m.faces>=0).sum())>budget:raise ValueError('Crease subdivision budget exceeded')
    low=spec.get('angle_low',8.);high=spec.get('angle_high',32.)
    if not high>low:raise ValueError('Ordered crease angle thresholds required')
    creases=np.clip((obs['f']['angles']-low)/(high-low),0,1)*spec.get('crease',1.)
    if spec.get('region_response',False):
        gain,region=regional_response(m,obs,spec)
        creases*=.45+.55*region['region_mask'][obs['t']['edges']].mean(1)
    creases=np.clip(creases,0,1)
    temp_root=runtime.PROJECT/'worker_temp';temp_root.mkdir(exist_ok=True)
    blender=Path(os.environ.get('CHESHIRE_BLENDER',runtime.PROJECT/'external/blender-4.5.4-windows-x64/blender.exe'))
    with tempfile.TemporaryDirectory(dir=temp_root) as folder:
        source=Path(folder)/'input.json';target=Path(folder)/'result.json'
        source.write_text(json.dumps(dict(vertices=m.xyz.tolist(),faces=[f[f>=0].tolist() for f in m.faces],edges=obs['t']['edges'].tolist(),creases=creases.tolist(),sampling=spec.get('sampling','CATMULL_CLARK'))))
        r=subprocess.run([str(blender),'--background','--factory-startup','--python-exit-code','1','--python',str(runtime.PROJECT/'gateflow/subdivision_worker.py'),'--',str(source),str(target)],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=180,creationflags=0x08000000)
        if r.returncode or not target.is_file():raise RuntimeError('Crease subdivision failed: '+r.stdout[-1000:]+r.stderr[-1000:])
        data=json.loads(target.read_text());xyz=np.array(data.pop('vertices'));faces=data.pop('faces');q=np.full((len(faces),max(4,max(map(len,faces)))),-1,int)
        for i,f in enumerate(faces):q[i,:len(f)]=f
        out=ArrayMesh(xyz,q,np.full(len(xyz),-1,np.int8),xyz.copy(),np.full((len(q),3),-1,int),m.generation+1)
        data.update(crease_count=int((creases>0).sum()),crease_quantiles=np.quantile(creases,[0,.5,.9,1]).tolist(),crease_rule='Current edge dihedral; optional structural mask',upstream_log=r.stdout)
        return out,data,dict(input_edges=obs['t']['edges'],edge_creases=creases)

from . import cage_ops  # Register the isolated low-poly parent/child study.
