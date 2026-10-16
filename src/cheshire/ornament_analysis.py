"""Reusable fixed-physical-radius shape evidence; no project IDs or feature-birth inference."""
from dataclasses import dataclass, asdict
import heapq
import numpy as np
from scipy.sparse import csr_matrix

@dataclass(frozen=True)
class EvidenceConfig:
    radius: float
    minimum_samples: int = 8
    reliable_samples: int = 16
    maximum_condition: float = 20.0
    residual_good: float = 0.15
    residual_bad: float = 0.50
    relative_residual_good: float = 0.35
    relative_residual_bad: float = 0.75
    minimum_unique_ancestors: int = 3
    reliable_unique_ancestors: int = 6
    anisotropy_direction_good: float = 0.75
    anisotropy_direction_bad: float = 0.45

def smooth01(x):
    x=np.clip(x,0.,1.)
    return x*x*x*(10.+x*(-15.+6.*x))

def unit(x):
    return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-30)

def quad_centres_normals(xyz,quads):
    """Actual quad arithmetic centres and oriented summed native-fan normals."""
    corners=np.asarray(xyz)[np.asarray(quads)]
    centres=corners.mean(1)
    normals=unit(np.cross(corners-centres[:,None,:],np.roll(corners,-1,axis=1)-centres[:,None,:]).sum(1))
    return centres,normals

def reference_dual_graph(xyz,quads):
    """Generic closed/open quad dual graph via shared edge midpoint on given input.
    For a finer reference surface, callers may instead provide measured material
    edge-route lengths. Never use Euclidean nearest-sheet neighbors.
    """
    xyz=np.asarray(xyz,dtype=float);q=np.asarray(quads,dtype=np.int64)
    if q.ndim!=2 or q.shape[1]!=4 or not np.isfinite(xyz).all():
        raise ValueError("Finite xyz and quad faces are required.")
    c=xyz[q].mean(1);nxt=np.roll(q,-1,axis=1)
    keys=np.minimum(q,nxt)*len(xyz)+np.maximum(q,nxt)
    order=np.argsort(keys.ravel());sortedkeys=keys.ravel()[order]
    starts=np.r_[0,np.flatnonzero(np.diff(sortedkeys))+1,len(order)]
    rows=[];cols=[];lengths=[]
    for a,b in zip(starts[:-1],starts[1:]):
        if b-a==1:continue
        if b-a!=2:raise ValueError("Nonmanifold edge; split sheets explicitly.")
        h0,h1=order[a:b];f0,f1=h0//4,h1//4
        midpoint=.5*(xyz[q.ravel()[h0]]+xyz[nxt.ravel()[h0]])
        length=np.linalg.norm(c[f0]-midpoint)+np.linalg.norm(c[f1]-midpoint)
        if length<=0:raise ValueError("Zero dual route length.")
        rows.extend((f0,f1));cols.extend((f1,f0));lengths.extend((length,length))
    return csr_matrix((lengths,(rows,cols)),shape=(len(q),len(q)))

def radius_neighbors(graph,seed,radius):
    distance={int(seed):0.};queue=[(0.,int(seed))]
    while queue:
        d,i=heapq.heappop(queue)
        if d!=distance[i]:continue
        a,b=graph.indptr[i:i+2]
        for j,w in zip(graph.indices[a:b],graph.data[a:b]):
            j=int(j);nd=d+float(w)
            if nd<=radius and nd<distance.get(j,float("inf")):
                distance[j]=nd;heapq.heappush(queue,(nd,j))
    ids=np.fromiter(distance.keys(),dtype=np.int64)
    return ids,np.fromiter(distance.values(),dtype=float)

def analyze_stage_anchors(centres,normals,reference_graph,reference_area,config,
                          ancestor_face_ids=None,progress=None):
    """Compare matching material anchors in a single fixed reference-radius window.

    centres,normals: (stage,anchor,3); unavailable pre-event anchors are NaN.
    ancestor_face_ids: optional (stage,anchor) IDs; -1 means no known counterpart.
    They measure independent ancestor-face coverage, not feature birth.
    All coordinates and config.radius must share declared model units.
    No history: pass one stage, or NaN/unknown lineage; shape evidence still works,
    while early-persistence confidence remains unavailable.
    """
    p=np.asarray(centres,float);normal=unit(np.asarray(normals,float))
    if p.shape!=normal.shape or p.ndim!=3 or p.shape[2]!=3:
        raise ValueError("centres/normals must share (stage,anchor,3).")
    ns,nf,_=p.shape;area=np.asarray(reference_area,float)
    if reference_graph.shape!=(nf,nf) or area.shape!=(nf,) or np.any(area<=0) or not np.isfinite(area).all():
        raise ValueError("Reference graph/positive quadrature area mismatch.")
    if not np.isfinite(reference_graph.data).all() or np.any(reference_graph.data<=0):
        raise ValueError("Reference route lengths must be finite positive.")
    if config.radius<=0:raise ValueError("Physical radius must be positive.")
    ancestors=None if ancestor_face_ids is None else np.asarray(ancestor_face_ids,np.int64)
    if ancestors is not None and ancestors.shape!=(ns,nf):raise ValueError("Ancestor shape mismatch.")
    shape=(ns,nf)
    out=dict(kappa=np.full(shape+(2,),np.nan),low_curvature_axis=np.full(shape+(3,),np.nan),
        normal_fit_residual=np.full(shape,np.nan),relative_normal_fit_residual=np.full(shape,np.nan),
        normal_variation_rms=np.full(shape,np.nan),position_plane_residual_over_radius=np.full(shape,np.nan),
        fit_condition=np.full(shape,np.nan),sample_count=np.zeros(shape,np.int32),
        unique_ancestor_faces=np.zeros(shape,np.int32),reference_neighbor_count=np.zeros(nf,np.int32))
    for face in range(nf):
        ids,dist=radius_neighbors(reference_graph,face,config.radius)
        out["reference_neighbor_count"][face]=len(ids)
        base=(1-(dist/config.radius)**2)**2*area[ids]
        for s in range(ns):
            valid=np.isfinite(p[s,ids]).all(1)&np.isfinite(normal[s,ids]).all(1)
            take=ids[valid];w=base[valid];out["sample_count"][s,face]=len(take)
            if ancestors is not None:
                aa=ancestors[s,take];out["unique_ancestor_faces"][s,face]=len(np.unique(aa[aa>=0]))
            else:out["unique_ancestor_faces"][s,face]=-1
            if len(take)<config.minimum_samples or not np.isfinite(normal[s,face]).all():continue
            n=normal[s,face];e=np.array([0.,0.,1.]);e-=n*np.dot(e,n)
            if np.linalg.norm(e)<.1:e=np.array([1.,0.,0.])-n*n[0]
            e=unit(e);v=np.cross(n,e);frame=np.column_stack((e,v))
            dp3=p[s,take]-p[s,face];dn=(normal[s,take]-n)@frame;dp=dp3@frame
            root=np.sqrt(w/max(float(w.max()),1e-30));A=dp*root[:,None];Y=-dn*root[:,None]
            if np.linalg.matrix_rank(A)<2:continue
            fit=np.linalg.lstsq(A,Y,rcond=None)[0];S=.5*(fit+fit.T);eig,V=np.linalg.eigh(S)
            residual=float(np.sqrt(np.sum(w*np.sum((dp@fit+dn)**2,axis=1))/max(w.sum(),1e-30)))
            variation=float(np.sqrt(np.sum(w*np.sum(dn*dn,axis=1))/max(w.sum(),1e-30)))
            out["kappa"][s,face]=eig
            out["low_curvature_axis"][s,face]=frame@V[:,np.argmin(np.abs(eig))]
            out["normal_fit_residual"][s,face]=residual
            out["normal_variation_rms"][s,face]=variation
            out["relative_normal_fit_residual"][s,face]=residual/max(variation,1e-12)
            out["position_plane_residual_over_radius"][s,face]=np.sqrt(np.sum(w*(dp3@n)**2)/max(w.sum(),1e-30))/config.radius
            out["fit_condition"][s,face]=float(np.linalg.cond(A))
        if progress is not None and face%5000==0:progress(face,nf)
    k=np.abs(out["kappa"])
    out["dimensionless_strength"]=config.radius*np.sqrt(np.sum(k*k,axis=-1))
    out["anisotropy"]=(k.max(-1)-k.min(-1))/np.maximum(k.sum(-1),1e-12)
    valid=np.isfinite(out["kappa"]).all(-1)&(out["sample_count"]>=config.minimum_samples)&(out["fit_condition"]<=config.maximum_condition)
    out["fit_valid"]=valid
    sample=smooth01((out["sample_count"]-config.minimum_samples+1)/max(config.reliable_samples-config.minimum_samples+1,1))
    cond=1-smooth01((out["fit_condition"]-4.)/max(config.maximum_condition-4.,1e-12))
    raw=1-smooth01((out["normal_fit_residual"]-config.residual_good)/(config.residual_bad-config.residual_good))
    relative=1-smooth01((out["relative_normal_fit_residual"]-config.relative_residual_good)/(config.relative_residual_bad-config.relative_residual_good))
    confidence=np.where(valid,sample*cond*np.minimum(raw,relative),0.)
    out["local_shape_evidence_confidence"]=np.nan_to_num(confidence)
    if ancestors is None:
        out["history_evidence_confidence"]=np.zeros(shape)
    else:
        unique=out["unique_ancestor_faces"]
        factor=smooth01((unique-config.minimum_unique_ancestors+1)/max(config.reliable_unique_ancestors-config.minimum_unique_ancestors+1,1))
        out["history_evidence_confidence"]=out["local_shape_evidence_confidence"]*factor
    axis=smooth01((out["anisotropy"]-config.anisotropy_direction_bad)/(config.anisotropy_direction_good-config.anisotropy_direction_bad))
    out["direction_evidence_confidence"]=out["local_shape_evidence_confidence"]*np.nan_to_num(axis)
    return out

def evidence_contract(config):
    return dict(config=asdict(config),input="xyz/quads or identical material anchors and actual reference dual graph",
        units="All coordinates/radius share caller-declared model units; no generation-specific bbox normalization.",
        radius_semantics="Same reference graph ball and material samples at every stage; increase radius in a separate comparison, never per stage.",
        feature_birth_claimed=False,topological_vertex_birth_is_not_feature_birth=True,
        independent_history="Unique coarse ancestor faces supplement sample count; unknown history cannot imply early absence.",
        confidence_semantics="Estimator adequacy and directional reliability, not a calibrated probability of class or age.",
        fallback="Use current-surface shape evidence and independently certified flow; do not alter existing classes where history is absent or unreliable.",
        scale_policy="Supply explicit model-unit radius or a global object-scale convention in config; never local ring count across resolutions.",
        nonmanifold_policy="Reject or explicitly split sheet topology; never cross folded sheets by Euclidean nearest neighbors.")


SHAPE_CLASS_NAMES = ("calm", "weak_fold", "strong_coherent_fold", "rounded_bulge", "multidirectional_junction_candidate")

def _normalize_weights(weights, count):
    a=np.asarray(weights,dtype=float)
    if a.shape!=(count,5) or not np.isfinite(a).all() or np.any(a<0):
        raise ValueError("Shape weights must be finite nonnegative (count,5).")
    total=a.sum(axis=1,keepdims=True)
    if np.any(total<=0):raise ValueError("Every shape-weight row needs positive support.")
    return a/total

def face_fields_to_vertices(quads,fields,vertex_count,face_area=None):
    """Incident-area scalar/vector interpolation; returns values and support mask."""
    q=np.asarray(quads,np.int64);a=np.asarray(fields,float)
    if len(a)!=len(q):raise ValueError("Face field count differs from quads.")
    area=np.ones(len(q)) if face_area is None else np.asarray(face_area,float)
    if area.shape!=(len(q),) or np.any(area<=0) or not np.isfinite(area).all():
        raise ValueError("Positive finite face areas are required.")
    values=np.zeros((vertex_count,)+a.shape[1:],float);weight=np.zeros(vertex_count,float)
    weighted=a*area.reshape((-1,)+(1,)*(a.ndim-1))
    for corner in range(4):
        np.add.at(values,q[:,corner],weighted);np.add.at(weight,q[:,corner],area)
    values/=np.maximum(weight,1e-30).reshape((-1,)+(1,)*(a.ndim-1))
    return values,weight>0

def direction_coherence(graph,axis,anisotropy,radius,valid=None):
    """Sign-free nearby principal-axis agreement, separate from shape strength."""
    axis=np.asarray(axis,float);an=np.asarray(anisotropy,float)
    valid=np.isfinite(axis).all(1) if valid is None else np.asarray(valid,bool)&np.isfinite(axis).all(1)
    result=np.zeros(len(axis),float)
    for face in np.flatnonzero(valid):
        ids,distance=radius_neighbors(graph,int(face),radius)
        take=valid[ids]&(an[ids]>.2)&(ids!=face)
        if not np.any(take):continue
        ids=ids[take];distance=distance[take]
        weight=(1-(distance/radius)**2)**2*an[ids]
        dot2=(axis[ids]@axis[face])**2
        result[face]=np.clip(2*np.sum(weight*dot2)/max(weight.sum(),1e-30)-1,0,1)
    return result

def classify_current_shape(metrics,reference_graph,config,*,stage=-1,fallback_face_weights=None,
                           calm_strength=0.15,strong_strength=0.60,
                           anisotropy_start=0.45,anisotropy_full=0.80):
    """Continuous current-surface five classes; junction is a shape candidate.

    Strength is radius*sqrt(k1^2+k2^2), so the thresholds are dimensionless.
    Gaussian sign distinguishes two-axis convex/concave caps from saddles.
    It does not prove constructive branching. History is never treated as age.
    """
    k=metrics["kappa"][stage];nf=len(k)
    fallback=np.tile([.25,.75,0.,0.,0.],(nf,1)) if fallback_face_weights is None else _normalize_weights(fallback_face_weights,nf)
    strength=metrics["dimensionless_strength"][stage]
    anisotropy=metrics["anisotropy"][stage]
    coherence=direction_coherence(reference_graph,metrics["low_curvature_axis"][stage],anisotropy,
                                  config.radius,metrics["fit_valid"][stage])
    active=smooth01((strength-calm_strength)/max(strong_strength-calm_strength,1e-12))
    strong=smooth01((strength-.5*strong_strength)/max(.5*strong_strength,1e-12))
    one_axis=smooth01((anisotropy-anisotropy_start)/max(anisotropy_full-anisotropy_start,1e-12))*coherence
    sign=k[:,0]*k[:,1]/np.maximum(np.sum(k*k,axis=1),1e-30)
    two_axis=active*(1-one_axis)
    rounded=two_axis*smooth01((sign-.02)/.18)
    saddle=two_axis*smooth01((-sign-.02)/.18)
    coherent=active*one_axis*strong
    weak=np.maximum(active-rounded-saddle-coherent,0.)
    weights=np.column_stack((1-active,weak,coherent,rounded,saddle))
    raw=1-smooth01((metrics["normal_fit_residual"][stage]-config.residual_good)/(config.residual_bad-config.residual_good))
    relative=1-smooth01((metrics["relative_normal_fit_residual"][stage]-config.relative_residual_good)/(config.relative_residual_bad-config.relative_residual_good))
    cond=1-smooth01((metrics["fit_condition"][stage]-4.)/max(config.maximum_condition-4.,1e-12))
    # Minimum sample count is a hard adequacy gate. More samples raise the
    # separate evidence confidence, not the current class probability itself.
    quality=np.where(metrics["fit_valid"][stage],np.minimum(raw,relative)*cond,0.)
    quality=np.nan_to_num(quality)
    weights=np.nan_to_num(weights)*quality[:,None]+fallback*(1-quality[:,None])
    return dict(face_shape_weights=_normalize_weights(weights,nf),direction_coherence=coherence,
                classification_fit_quality=quality,
                hierarchy_claimed=False,feature_birth_claimed=False,
                junction_semantics="Multidirectional saddle-like geometry candidate; not certified topology branching.")

def analyze_ornament_shape(xyz,quads,*,config=None,fallback_face_weights=None,
                           stage_centres=None,stage_normals=None,ancestor_face_ids=None,
                           reference_graph=None,reference_area=None):
    """Reusable analysis output directly consumable by apply_adaptive_ornament.

    Without history, current face-centre shape is analyzed. With history, callers
    provide explicitly corresponding material anchors and mark unavailable
    counterparts NaN. The last stage must equal the current face-centre anchors.
    Optional graph/area inputs allow exact finer-surface reference routes.
    No face IDs, project paths, canonical seeds, or certified curves are embedded.
    """
    x=np.asarray(xyz,float);q=np.asarray(quads,np.int64)
    if x.ndim!=2 or x.shape[1]!=3 or q.ndim!=2 or q.shape[1]!=4:
        raise ValueError("Expected xyz=(Nv,3), quads=(Nq,4).")
    if not len(x) or not len(q) or np.any(q<0) or np.any(q>=len(x)) or not np.isfinite(x).all():
        raise ValueError("Finite nonempty mesh with valid indices is required.")
    centres,normals=quad_centres_normals(x,q)
    graph=reference_dual_graph(x,q) if reference_graph is None else reference_graph
    corners=x[q];fan=np.cross(corners-centres[:,None],np.roll(corners,-1,axis=1)-centres[:,None])
    areas=.5*np.linalg.norm(fan,axis=-1).sum(1) if reference_area is None else np.asarray(reference_area,float)
    if config is None:
        # A single global object convention preserves uniform-scale behavior.
        scale=float(np.linalg.norm(np.ptp(x,axis=0)))
        if scale<=0:raise ValueError("Nonzero physical object extent is required.")
        config=EvidenceConfig(radius=.03*scale)
    if (stage_centres is None)!=(stage_normals is None):
        raise ValueError("Stage centres and normals must be provided together.")
    history=stage_centres is not None
    p=centres[None] if not history else np.asarray(stage_centres,float)
    n=normals[None] if not history else np.asarray(stage_normals,float)
    if p.shape[-2:]!=(len(q),3) or not np.allclose(p[-1],centres,rtol=1e-10,atol=1e-12):
        raise ValueError("Last-stage anchors must match the current material face centres.")
    metrics=analyze_stage_anchors(p,n,graph,areas,config,ancestor_face_ids=ancestor_face_ids)
    classes=classify_current_shape(metrics,graph,config,fallback_face_weights=fallback_face_weights)
    vertex_weights,support=face_fields_to_vertices(q,classes["face_shape_weights"],len(x),areas)
    # Isolated vertices have no local shape evidence and use the declared fallback.
    vertex_weights[~support]=[.25,.75,0.,0.,0.]
    vertex_weights=_normalize_weights(vertex_weights,len(x))
    vertex_metrics={}
    for key,field in [
        ("fold_strength",metrics["dimensionless_strength"][-1]),
        ("anisotropy",metrics["anisotropy"][-1]),
        ("direction_coherence",classes["direction_coherence"]),
        ("shape_evidence_confidence",metrics["local_shape_evidence_confidence"][-1])]:
        vertex_metrics[key]=face_fields_to_vertices(q,np.nan_to_num(field),len(x),areas)[0]
    candidate_flow=classes["face_shape_weights"][:,2]*metrics["direction_evidence_confidence"][-1]
    return dict(shape_weights=vertex_weights,face_shape_weights=classes["face_shape_weights"],
        vertex_fields=vertex_metrics,face_metrics=metrics,
        face_direction_coherence=classes["direction_coherence"],
        face_classification_fit_quality=classes["classification_fit_quality"],
        candidate_flow_confidence=candidate_flow,
        metadata=dict(evidence_contract(config),class_names=SHAPE_CLASS_NAMES,
            history_provided=history,flow_certified=False,
            class_weights_are_not_age_probabilities=True,
            isolated_vertices=int((~support).sum()),fallback_weights=[.25,.75,0.,0.,0.],
            automatic_radius_policy="0.03 * one global bbox diagonal, if no explicit physical radius is supplied.",
            junction_semantics=classes["junction_semantics"]))
