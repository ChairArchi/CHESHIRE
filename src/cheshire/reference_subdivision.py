"""Task29 opt-in closed tri/quad experiment; original operators are untouched.

Eq3 uses original endpoint midpoints (Figure 2's weight-6 neighbours),
but completed new face points. Eq10 finishes faces before Eq2/3. No claim
of reproducing the unpublished Digital Grotesque implementation.
"""
from dataclasses import dataclass
import numpy as np

WEIGHTS = ('wf','w1','we','w2','wp','w3','w4','w6','w7')
LEGACY_ISOLATED = 'LEGACY_ISOLATED'
REFERENCE_COUPLED = 'REFERENCE_COUPLED'
GLOBAL_SCALE = 'GLOBAL_SCALE'
LOCAL_INCIDENT_SCALE = 'LOCAL_INCIDENT_SCALE'


@dataclass
class ArrayMesh:
    xyz: np.ndarray
    faces: np.ndarray                 # -1 fourth slot for triangles
    classes: np.ndarray               # 0 previous vertex, 1 edge, 2 face
    rest: np.ndarray                  # positive cage association, not geometry
    anchors: np.ndarray               # actual ancestor face IDs at G1/G2/G3
    generation: int = 0


def cube(side=1000.):
    xyz=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],
                  [-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]],float)*side/2
    faces=np.array([[3,2,1,0],[4,5,6,7],[0,1,5,4],[1,2,6,5],
                    [2,3,7,6],[3,0,4,7]],np.int64)
    return ArrayMesh(xyz,faces,np.full(8,-1,np.int8),xyz.copy(),
                     np.full((6,3),-1,np.int64))


def topology(mesh):
    q=mesh.faces;mask=q>=0;n=mask.sum(1);fi=np.repeat(np.arange(len(q)),n)
    a=q[mask];nextq=q[np.arange(len(q))[:,None],(np.arange(4)[None,:]+1)%n[:,None]]
    b=nextq[mask];pairs=np.sort(np.column_stack((a,b)),axis=1)
    edges,inv,counts=np.unique(pairs,axis=0,return_inverse=True,return_counts=True)
    if np.any(counts!=2): raise ValueError('Closed two-face edges required; no repair.')
    order=np.argsort(inv,kind='stable');ef=fi[order].reshape(-1,2)
    directed=np.sign(b-a)[order].reshape(-1,2)
    if np.any(directed.sum(1)!=0): raise ValueError('Inconsistent orientation.')
    fe=np.full(q.shape,-1,np.int64);fe[mask]=inv
    degree=np.bincount(edges.ravel(),minlength=len(mesh.xyz))
    return dict(mask=mask,n=n,fi=fi,a=a,edges=edges,ef=ef,fe=fe,degree=degree)


def mean_incident(values,ids,size):
    counts=np.bincount(ids,minlength=size)
    v=np.asarray(values)
    if v.ndim==1: return np.bincount(ids,weights=v,minlength=size)/counts
    return np.column_stack([np.bincount(ids,weights=v[:,j],minlength=size)/counts for j in range(v.shape[1])])


def unit(v):
    norms=np.linalg.norm(v,axis=1)
    return np.divide(v,norms[:,None],out=np.zeros_like(v),where=norms[:,None]>0)


def fields(mesh,t=None):
    t=t or topology(mesh);q=mesh.faces;p=mesh.xyz[np.maximum(q,0)]
    c=(p*t['mask'][:,:,None]).sum(1)/t['n'][:,None]
    following=p[np.arange(len(q))[:,None],(np.arange(4)[None,:]+1)%t['n'][:,None]]
    cross=np.cross(p-c[:,None],following-c[:,None])*t['mask'][:,:,None]
    normals=unit(cross.sum(1));area=np.linalg.norm(cross,axis=2).sum(1)/2
    lengths=np.linalg.norm(mesh.xyz[t['edges'][:,0]]-mesh.xyz[t['edges'][:,1]],axis=1)
    sf=(lengths[np.maximum(t['fe'],0)]*t['mask']).sum(1)/t['n']
    se=sf[t['ef']].mean(1)
    sv=mean_incident(np.repeat(sf,t['n']),t['a'],len(mesh.xyz))
    nv=unit(mean_incident(np.repeat(normals,t['n'],axis=0),t['a'],len(mesh.xyz)))
    ne=normals[t['ef']].mean(1)  # paper: mean, not unit-normalized
    angles=np.degrees(np.arccos(np.clip((normals[t['ef'][:,0]]*normals[t['ef'][:,1]]).sum(1),-1,1)))
    variation=1-np.linalg.norm(mean_incident(np.repeat(normals,t['n'],axis=0),t['a'],len(mesh.xyz)),axis=1)
    # Distance of fourth quad point to plane through first three / perimeter.
    plane=unit(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]))
    planarity=np.abs(((p[:,3]-p[:,0])*plane).sum(1))/(sf*t['n'])
    planarity[t['n']==3]=0
    return dict(c=c,nf=normals,ne=ne,nv=nv,sf=sf,se=se,sv=sv,
                lengths=lengths,angles=angles,area=area,variation=variation,planarity=planarity)


def intrinsic_signal(mesh,t,f,rule):
    if not rule or mesh.generation+1<rule.get('start',2): return None
    kind=rule['field']
    if kind=='NORMAL_VARIATION': s=np.clip(f['variation']*rule.get('gain',3.),0,1)
    elif kind=='ORIGINAL_EDGE_DISTANCE':
        # Positive rest samples stay on/in cube; second largest absolute
        # coordinate measures proximity to original cube edges, all axes equal.
        s=np.clip(1-np.sort(np.abs(mesh.rest),axis=1)[:,1]/500.,0,1)
    elif kind=='PLANARITY':
        s=mean_incident(np.repeat(np.clip(f['planarity']*rule.get('gain',12.),0,1),t['n']),t['a'],len(mesh.xyz))
    elif kind=='LOCAL_SCALE':
        s=np.clip(np.log2(np.maximum(f['sv'],1e-15)/np.median(f['sv']))/2+.5,0,1)
    else: raise ValueError('Undeclared intrinsic field.')
    return s


def subdivide(mesh,row,*,scale_mode=LOCAL_INCIDENT_SCALE,intrinsic=None):
    """Complete face -> edge, complete face + original midpoint -> vertex.

    Compact previous-point classes are verified against the real quad pattern;
    descendants after topology edits with invalid classes use Eq1 explicitly.
    """
    w={k:float(row.get('weights',row).get(k,0)) for k in WEIGHTS}
    if not all(np.isfinite(list(w.values()))): raise ValueError('Finite weights required.')
    t=topology(mesh);f=fields(mesh,t);q=mesh.faces;x=mesh.xyz
    nv=len(x);ne=len(t['edges']);nf=len(q);n=t['n'];edges=t['edges'];ef=t['ef']
    scales=dict(face=f['sf'],edge=f['se'],vertex=f['sv'])
    if scale_mode==GLOBAL_SCALE: scales={k:np.full(len(v),f['lengths'].mean()) for k,v in scales.items()}
    elif scale_mode!=LOCAL_INCIDENT_SCALE: raise ValueError('Unknown scale mode.')
    signal=intrinsic_signal(mesh,t,f,intrinsic)
    sf=se=sv=None
    if signal is not None:
        sf=mean_incident(signal[t['a']],t['fi'],nf);se=signal[edges].mean(1);sv=signal
    def control(k,kind):
        s={'face':sf,'edge':se,'vertex':sv}[kind]
        if s is None or k not in intrinsic['controls']: return w[k]
        lo,hi=intrinsic['controls'][k]
        return w[k]+lo+(hi-lo)*s
    def col(v):return np.asarray(v)[...,None] if np.ndim(v) else v
    base=f['c'].copy();classes=mesh.classes[np.maximum(q,0)]
    eligible=(n==4)&((classes==0).sum(1)==1)&((classes==1).sum(1)==2)&((classes==2).sum(1)==1)
    iv=np.argmax(classes==0,axis=1);jf=np.argmax(classes==2,axis=1)
    eligible&=((iv+2)%4==jf)
    if mesh.generation:
        V=x[q[np.arange(nf),iv]];F=x[q[np.arange(nf),jf]]
        E=(x[np.maximum(q,0)]*(classes==1)[:,:,None]).sum(1)
        w3=col(control('w3','face'));w4=col(control('w4','face'))
        later=((V*(1+w3)+F*(1-w3))*(1+w4)+E*(1-w4))/4
        base[eligible]=later[eligible]
    face=base+f['nf']*col(control('wf','face'))*scales['face'][:,None]
    um=row.get('u_map',{});u=np.array([um.get(f'({d},{d})',row.get('unknown_u',0.)) for d in t['degree']])
    uface=u[np.maximum(q,0)]*t['mask']
    face+=col(control('w6','face'))*((x[np.maximum(q,0)]-face[:,None])*uface[:,:,None]).sum(1)
    w1=col(control('w1','edge'))
    ep=((face[ef].sum(1))*(1+w1)+x[edges].sum(1)*(1-w1))/4+f['ne']*col(control('we','edge'))*scales['edge'][:,None]
    ep+=col(control('w7','edge'))*((x[edges]-ep[:,None])*u[edges][:,:,None]).sum(1)
    Fbar=mean_incident(np.repeat(face,n,axis=0),t['a'],nv)
    mid=x[edges].mean(1);Rbar=mean_incident(np.repeat(mid,2,axis=0),edges.ravel(),nv)
    w2=col(control('w2','vertex'));degree=t['degree'][:,None]
    vp=(Fbar*(1+w2)+Rbar*(2-w2)+x*(degree-3))/degree+f['nv']*col(control('wp','vertex'))*scales['vertex'][:,None]
    locks=None
    if signal is not None and 'lock_threshold' in intrinsic:
        # Paper-motivated facet retention extension: geometric fold tags, not IDs.
        # Lock previous vertex positions in already folded regions; still generate
        # modified new face/edge points. Re-evaluate from actual input each call.
        threshold=float(intrinsic['lock_threshold'])
        if not 0<threshold<1:raise ValueError('Fold-lock threshold must be in (0,1).')
        locks=f['variation']>=threshold;vp[locks]=x[locks]
    xyz=np.concatenate([vp,ep,face]);outclasses=np.concatenate([np.zeros(nv,np.int8),np.ones(ne,np.int8),np.full(nf,2,np.int8)])
    prev=t['fe'][np.arange(nf)[:,None],(np.arange(4)[None,:]-1)%n[:,None]]
    child=np.column_stack([prev[t['mask']]+nv,t['a'],t['fe'][t['mask']]+nv,t['fi']+nv+ne])
    restface=mean_incident(mesh.rest[t['a']],t['fi'],nf)
    rest=np.concatenate([mesh.rest,mesh.rest[edges].mean(1),restface])
    anchors=np.repeat(mesh.anchors,n,axis=0)
    if mesh.generation<3: anchors[:,mesh.generation]=np.arange(len(child))
    out=ArrayMesh(xyz,child,outclasses,rest,anchors,mesh.generation+1)
    if not np.isfinite(xyz).all():raise ValueError('Nonfinite output; no fallback.')
    metadata=dict(generation=out.generation,implementation=REFERENCE_COUPLED,scale=scale_mode,
        weights=w,u_map=um,unknown_u=row.get('unknown_u',0),eq4_eligible=int(eligible.sum()) if mesh.generation else 0,
        eq4_fallback=int(nf-eligible.sum()) if mesh.generation else nf,
        intrinsic=intrinsic,scale_ranges={k:[float(v.min()),float(v.max())] for k,v in scales.items()},
        locked_vertex_count=0 if locks is None else int(locks.sum()),
        intrinsic_range=None if signal is None else [float(signal.min()),float(signal.max())],
        dependency='Eq1/4 -> Eq10 -> Eq2 -> Eq11; completed faces + ORIGINAL edge midpoints -> Eq3',
        normals='unit input face; edge arithmetic mean; vertex normalized incident face mean')
    state=dict(input_edges=edges,parent_face=t['fi'],parent_corner=t['a'],
               face_scale=scales['face'],edge_scale=scales['edge'],vertex_scale=scales['vertex'])
    if signal is not None:state['intrinsic_signal']=signal
    if locks is not None:state['vertex_lock_mask']=locks
    return out,metadata,state


def metrics(mesh):
    t=topology(mesh);f=fields(mesh,t);xyz=mesh.xyz
    return dict(vertices=len(xyz),faces=len(mesh.faces),edges=len(t['edges']),generation=mesh.generation,
        bounds_min=xyz.min(0).tolist(),bounds_max=xyz.max(0).tolist(),extent=np.ptp(xyz,axis=0).tolist(),
        finite=bool(np.isfinite(xyz).all()),min_unsigned_area=float(f['area'].min()),
        zero_area_faces=int((f['area']<1e-12).sum()),mean_edge=float(f['lengths'].mean()),
        dihedral_median=float(np.median(f['angles'])),dihedral_p90=float(np.quantile(f['angles'],.9)),
        dihedral_over45=float((f['angles']>45).mean()),normal_variation_mean=float(f['variation'].mean()),
        local_scale_CV=float(f['sf'].std()/f['sf'].mean()),
        Euler=int(len(xyz)-len(t['edges'])+len(mesh.faces)))
