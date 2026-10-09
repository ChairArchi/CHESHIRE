"""Task36 opt-in interpolating quad folding. No existing operator is changed.

Every new edge and face point is independently placed using incoming geometry.
Retained vertices keep their positions: refinement cannot average away a parent
crease. Project units, X/Y reflection and quarter-turn symmetry, Z vertical.
This is a CHESHIRE experiment, not an implementation claim about Hansmeyer.
"""
import numpy as np
from .reference_subdivision import ArrayMesh, topology, fields, unit, mean_incident


def carrier(side=1000., height=4000., divisions=2):
    if not np.isfinite([side,height]).all() or min(side,height)<=0 or type(divisions)!=int or divisions<1:
        raise ValueError('Positive finite dimensions and integer divisions required.')
    ring=np.array([[-1,-1],[1,-1],[1,1],[-1,1]],float)*side/2
    xyz=np.array([[*xy,z] for z in np.linspace(0,height,divisions+1) for xy in ring])
    faces=[[3,2,1,0]]
    faces += [[4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j] for i in range(divisions) for j in range(4)]
    faces += [[4*divisions+j for j in range(4)]]
    return ArrayMesh(xyz,np.array(faces,np.int64),np.full(len(xyz),-1,np.int8),xyz.copy(),
                     np.tile(np.arange(len(faces))[:,None],(1,3)),0)


def step(mesh, *, face_gain=.25, edge_gain=.08, feedback=.5, inherited_bias=.4,
         direction='normal', active=True, source='current', vertex_gain=0., vertex_memory=1., mode='interpolating',
         diagonal_tension=None, edge_tension=.5, vertex_tension=-.8,
         averaging_gain=1., stencil_gain=1., normal_gain=1., decompose=False,
         cap_mode='fixed_xyz', ancestry_gain=1., surface='mean'):
    values=[face_gain,edge_gain,feedback,inherited_bias,vertex_gain,vertex_memory]
    if not np.isfinite(values).all() or not 0<=face_gain<=1 or not 0<=edge_gain<=1 or not 0<=feedback<=2 or not -1<=inherited_bias<=1:
        raise ValueError('Finite declared experimental parameter domain required.')
    if not -1<=vertex_gain<=1 or not 0<=vertex_memory<=1:raise ValueError('Declared vertex domain required.')
    if diagonal_tension is not None and (not np.isfinite(diagonal_tension) or not -1<=diagonal_tension<=2):raise ValueError('Declared diagonal tension domain required.')
    if not np.isfinite([edge_tension,vertex_tension]).all() or not -2<=edge_tension<=2 or not -3<=vertex_tension<=2:raise ValueError('Declared stencil domain required.')
    if not np.isfinite([averaging_gain,stencil_gain,normal_gain]).all() or min(averaging_gain,stencil_gain,normal_gain)<0 or max(averaging_gain,stencil_gain,normal_gain)>1:raise ValueError('Component gains must be in [0,1].')
    if cap_mode not in ('fixed_xyz','plane_only') or not np.isfinite(ancestry_gain) or not 0<=ancestry_gain<=1:raise ValueError('Declared boundary and ancestry policy required.')
    if surface not in ('mean','vf'):raise ValueError('Declared native surface required.')
    if direction not in ('normal','radial') or source not in ('current','rest'):
        raise ValueError('Explicit direction and geometric source required.')
    if mode=='coupled' and direction!='normal':raise ValueError('Coupled reference placement uses current normals; radial override is unsupported.')
    t=topology(mesh);q=mesh.faces;x=mesh.xyz;nv=len(x);ne=len(t['edges']);nf=len(q)
    if q.shape[1]!=4 or np.any(q<0):raise ValueError('Closed all-quad operator carrier required.')
    observed=mesh if source=='current' else ArrayMesh(mesh.rest,q,mesh.classes,mesh.rest,mesh.anchors,mesh.generation)
    f=fields(observed,t);p=observed.xyz[q];edges=t['edges'];ef=t['ef']
    # Distance from centre to each actual supporting edge line. Unlike mean
    # edge scale this does not amplify extrusion on an elongated narrow face.
    a=p-f['c'][:,None];b=np.roll(p,-1,axis=1)-p
    support=np.min(np.linalg.norm(np.cross(a,b),axis=2)/np.maximum(np.linalg.norm(b,axis=2),1e-12),axis=1)
    bend=1-np.clip((f['nf'][ef[:,0]]*f['nf'][ef[:,1]]).sum(1),-1,1)
    face_bend=bend[t['fe']].mean(1)
    multiplier=1+feedback*np.tanh(2*face_bend)
    face_base=x[q].mean(1);edge_base=x[edges].mean(1)
    cls=mesh.classes[q];eligible=(cls==0).sum(1)==1
    eligible&=((cls==1).sum(1)==2)&((cls==2).sum(1)==1)
    prior_face=np.argmax(cls==2,axis=1);prior_corner=np.argmax(cls==0,axis=1)
    eligible&=((prior_corner+2)%4==prior_face)
    if getattr(mesh,'surface','mean')=='vf':
        face_base[eligible]=(x[q[np.arange(nf),prior_face]]+x[q[np.arange(nf),prior_corner]])[eligible]/2
    # Convex ancestry bias, not negative interpolation or an arbitrary face ID.
    bias=inherited_bias*np.tanh(1+face_bend)
    shift=(x[q[np.arange(nf),prior_face]]-x[q[np.arange(nf),prior_corner]])*bias[:,None]/4
    shift[~eligible]=0
    endz=(float(mesh.rest[:,2].min()),float(mesh.rest[:,2].max()))
    fixed_vertex=(mesh.rest[:,2]==endz[0])|(mesh.rest[:,2]==endz[1])
    fixed_face=fixed_vertex[q].all(1);fixed_edge=fixed_vertex[edges].all(1)
    normals=f['nf'];en=unit(f['nf'][ef].sum(1))
    if direction=='radial':
        normals=unit(np.column_stack([f['c'][:,:2],np.zeros(nf)]))
        centre=observed.xyz[edges].mean(1);en=unit(np.column_stack([centre[:,:2],np.zeros(ne)]))
    face_vector=-face_gain*support[:,None]*multiplier[:,None]*normals+shift
    edge_vector=edge_gain*np.minimum(support[ef[:,0]],support[ef[:,1]])[:,None]*(1+feedback*np.tanh(bend))[:,None]*en
    face_vector[fixed_face]=0
    if cap_mode=='fixed_xyz':edge_vector[fixed_edge]=0
    else:edge_vector[fixed_edge,2]=0
    neighbours=mean_incident(observed.xyz[edges[:,::-1]].reshape(-1,3),edges.ravel(),nv)
    lap=observed.xyz-neighbours
    radius_vertex=mean_incident(np.repeat(support,4),q.ravel(),nv)
    # A signed geometric contrast response, bounded by incoming support.
    # No random seed, pre-specified lobe count, or axial ornament locations.
    contrast=np.sum(lap*f['nv'],axis=1)
    vertex_vector=vertex_gain*np.tanh(contrast/np.maximum(radius_vertex,1e-12))[:,None]*radius_vertex[:,None]*f['nv']
    vertex_vector+=(1-vertex_memory)*(neighbours-observed.xyz)
    if cap_mode=='fixed_xyz':vertex_vector[fixed_vertex]=0
    else:vertex_vector[fixed_vertex,2]=0
    components={}
    if mode=='coupled' and active:
        from .reference_subdivision import subdivide
        # Reuse the already corrected face -> edge -> vertex implementation.
        # Only opt-in absolute controls and the explicit end constraint differ.
        controls=dict(wf=-face_gain*support*multiplier/np.maximum(f['sf'],1e-12),
          we=edge_gain*np.minimum(support[ef[:,0]],support[ef[:,1]])/np.maximum(f['se'],1e-12),
          wp=vertex_gain*radius_vertex/np.maximum(f['sv'],1e-12),
          w3=ancestry_gain*inherited_bias*np.tanh(1+face_bend),w4=ancestry_gain*(-.3*np.tanh(face_bend) if diagonal_tension is None else np.full(nf,diagonal_tension)),
          w1=np.full(ne,edge_tension),w2=np.full(nv,vertex_tension))
        controls['wf'][fixed_face]=0;controls['we'][fixed_edge]=0;controls['wp'][fixed_vertex]=0
        coupled,_,_=subdivide(mesh,{},resolved_controls=controls)
        if decompose or (averaging_gain,stencil_gain,normal_gain)!=(1.,1.,1.):
            standard,_,_=subdivide(mesh,{})
            geometry_controls={k:v.copy() for k,v in controls.items()}
            for k in ['wf','we','wp']:geometry_controls[k][:]=0
            geometry,_,_=subdivide(mesh,{},resolved_controls=geometry_controls)
            interpolated=np.concatenate([x,edge_base,face_base])
            components=dict(averaging_component=standard.xyz-interpolated,
                stencil_component=geometry.xyz-standard.xyz,normal_component=coupled.xyz-geometry.xyz)
            for c in components.values():
                c[:nv]*=(1-vertex_memory)
                if cap_mode=='fixed_xyz':c[np.r_[fixed_vertex,fixed_edge,fixed_face]]=0
                else:c[np.r_[fixed_vertex,fixed_edge,fixed_face],2]=0;c[nv+ne:][fixed_face]=0
            resolved=interpolated+averaging_gain*components['averaging_component']+stencil_gain*components['stencil_component']+normal_gain*components['normal_component']
            coupled.xyz[:nv]=x+(resolved[:nv]-x)/max(1-vertex_memory,1e-15) if vertex_memory!=1 else x
            coupled.xyz[nv:]=resolved[nv:]
        vertex_vector=(1-vertex_memory)*(coupled.xyz[:nv]-x)
        edge_vector=coupled.xyz[nv:nv+ne]-edge_base
        face_vector=coupled.xyz[nv+ne:]-face_base
        if cap_mode=='fixed_xyz':vertex_vector[fixed_vertex]=0;edge_vector[fixed_edge]=0
        else:vertex_vector[fixed_vertex,2]=0;edge_vector[fixed_edge,2]=0
        face_vector[fixed_face]=0
    elif mode not in ('interpolating','coupled'):raise ValueError('Unknown opt-in operator mode.')
    if not active:face_vector[:]=0;edge_vector[:]=0;vertex_vector[:]=0
    xyz=np.concatenate([x+vertex_vector,edge_base+edge_vector,face_base+face_vector])
    previous=np.roll(t['fe'],1,axis=1)
    child=np.column_stack([previous.ravel()+nv,q.ravel(),t['fe'].ravel()+nv,np.repeat(np.arange(nf),4)+nv+ne])
    rest=np.concatenate([mesh.rest,mesh.rest[edges].mean(1),mesh.rest[q].mean(1)])
    classes=np.r_[np.zeros(nv,np.int8),np.ones(ne,np.int8),np.full(nf,2,np.int8)]
    out=ArrayMesh(xyz,child,classes,rest,np.repeat(mesh.anchors,4,axis=0),mesh.generation+1)
    out.surface=surface
    if not np.isfinite(xyz).all():raise ValueError('Nonfinite output; no repair.')
    op=dict(input_edges=edges,parent_face=np.repeat(np.arange(nf),4),parent_corner=q.ravel(),
            parent_face_vertices=q,face_vector=face_vector,edge_vector=edge_vector,
            face_base=face_base,edge_base=edge_base,support_radius=support,face_bend=face_bend,
            edge_bend=bend,ancestry_bias=bias,eligible=eligible,fixed_face=fixed_face,fixed_edge=fixed_edge,
            incoming_point_classes=mesh.classes,vertex_vector=vertex_vector,vertex_contrast=contrast,
            requested_face_gain=np.array(face_gain),requested_edge_gain=np.array(edge_gain),**components)
    return out,op


def native(mesh):
    """Explicit centre-fan triangles are the authoritative physical surface.

    The separate all-quad state drives the next generation. A nonplanar quad
    has no unique surface; never silently swap to a diagonal triangulation.
    """
    nv=len(mesh.xyz);nf=len(mesh.faces);q=mesh.faces
    centres=mesh.xyz[q].mean(1)
    if getattr(mesh,'surface','mean')=='vf':
        cls=mesh.classes[q];iv=np.argmax(cls==0,axis=1);jf=np.argmax(cls==2,axis=1)
        valid=((cls==0).sum(1)==1)&((cls==1).sum(1)==2)&((cls==2).sum(1)==1)&((iv+2)%4==jf)
        centres[valid]=(mesh.xyz[q[np.arange(nf),iv]]+mesh.xyz[q[np.arange(nf),jf]])[valid]/2
    xyz=np.concatenate([mesh.xyz,centres])
    tri=np.stack([q,np.roll(q,-1,axis=1),np.broadcast_to(np.arange(nf)[:,None]+nv,q.shape)],axis=-1).reshape(-1,3)
    faces=np.column_stack([tri,np.full(len(tri),-1,np.int64)])
    return ArrayMesh(xyz,faces,np.r_[mesh.classes,np.full(nf,2,np.int8)],
                     np.concatenate([mesh.rest,mesh.rest[q].mean(1)]),np.repeat(mesh.anchors,4,axis=0),mesh.generation)


def quick_integrity(mesh):
    """Supplement transverse checks with exact declared cap orientation."""
    m=native(mesh);tri=m.faces[:,:3];p=m.xyz[tri]
    cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);area=np.linalg.norm(cross,axis=1)/2
    bottom=(m.rest[tri,2]==mesh.rest[:,2].min()).all(1);top=(m.rest[tri,2]==mesh.rest[:,2].max()).all(1)
    return dict(degenerate_triangles=int((area<1e-10).sum()),
        reversed_or_degenerate_cap_triangles=int((cross[bottom,2]>=-2e-10).sum()+(cross[top,2]<=2e-10).sum()))
