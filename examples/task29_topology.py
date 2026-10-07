"""One bounded opt-in proximity-weld experiment, only introduced after A–D.

No implicit mesh repair: cycle compression, removed degenerate faces and
every merged ID are recorded. Invalid edge or vertex links reject a proposal.
"""
import numpy as np
from scipy.spatial import cKDTree
from cheshire.reference_subdivision import ArrayMesh,topology,fields,metrics


def vertex_links_valid(m,t,vertices):
    faces=m.faces
    for v in vertices:
        fs=np.flatnonzero((faces==v).any(1));links={}
        for f in fs:
            q=[int(k) for k in faces[f] if k>=0];j=q.index(int(v));a=q[j-1];b=q[(j+1)%len(q)]
            links.setdefault(a,[]).append(b);links.setdefault(b,[]).append(a)
        if not links or any(len(row)!=2 for row in links.values()):return False
        pending=[next(iter(links))];seen=set()
        while pending:
            n=pending.pop()
            if n not in seen:seen.add(n);pending.extend(links[n])
        if len(seen)!=len(links):return False
    return True


def weld(m,rule):
    t=topology(m);f=fields(m,t);scales=f['sv'];threshold=rule['threshold'];before=metrics(m)
    if not 0<threshold<1:raise ValueError('Bounded positive local ratio required.')
    if rule['scope']=='ADJACENT':pairs=t['edges'].copy()
    elif rule['scope']=='ALL_PROXIMATE':
        pairs=cKDTree(m.xyz).query_pairs(float(threshold*scales.max()),output_type='ndarray')
    else:raise ValueError('Explicit proximity scope required.')
    mask=(m.classes[pairs]>=1).all(1);pairs=pairs[mask]
    distance=np.linalg.norm(m.xyz[pairs[:,0]]-m.xyz[pairs[:,1]],axis=1)
    local=np.minimum(scales[pairs[:,0]],scales[pairs[:,1]])
    ratio=np.divide(distance,local,out=np.full(len(distance),np.inf),where=local>0)
    keep=ratio<=threshold;pairs=pairs[keep];ratio=ratio[keep];distance=distance[keep]
    order=np.lexsort((pairs[:,1],pairs[:,0],ratio)) if len(pairs) else np.array([],int)
    # One disjoint matching in this iteration. ID tie-breaks resolve exact equal
    # distances only; there is no ID field or stochastic generation parameter.
    used=set();merges=[];mapping=np.arange(len(m.xyz));xyz=m.xyz.copy();rest=m.rest.copy();classes=m.classes.copy()
    for index in order:
        a,b=map(int,pairs[index])
        if a in used or b in used:continue
        used.update([a,b]);mapping[b]=a;xyz[a]=(m.xyz[a]+m.xyz[b])/2;rest[a]=(m.rest[a]+m.rest[b])/2;classes[a]=-1
        merges.append(dict(ids=[a,b],distance=float(distance[index]),local_scale=float(min(scales[a],scales[b])),normalized_distance=float(ratio[index]),merged_xyz=xyz[a].tolist()))
    q=mapping[np.maximum(m.faces,0)];q[m.faces<0]=-1;cycles=[];anchors=[];removed=[];compressed=[];reason=None
    for index,face in enumerate(q):
        cycle=[]
        for v in face[face>=0]:
            if not cycle or cycle[-1]!=v:cycle.append(int(v))
        if len(cycle)>1 and cycle[0]==cycle[-1]:cycle.pop()
        if len(set(cycle))!=len(cycle):reason='Nonconsecutive repeated vertex creates a pinched face';break
        if len(cycle)<3:removed.append(index);continue
        if len(cycle)!=int((m.faces[index]>=0).sum()):compressed.append(dict(face=index,cycle=cycle))
        cycles.append(cycle+[-1]*(4-len(cycle)));anchors.append(m.anchors[index])
    log=dict(rule=rule,before=before,threshold_candidates=len(pairs),merged_pairs=merges,
        compressed_cycles=compressed,removed_degenerate_face_ids=removed,
        policy='Single disjoint deterministic proximity matching; averaged double-precision XYZ/rest; merged point provenance becomes unknown so Eq4 cannot invent classes. Exact cycle compression/drop recorded, no implicit cleanup.',
        status='PROPOSED',after=None,invalid_reason=reason)
    if reason:log['status']='REJECTED_INVALID';return None,log
    cycles=np.array(cycles,np.int64);active=np.unique(cycles);active=active[active>=0]
    reindex=np.full(len(xyz),-1,np.int64);reindex[active]=np.arange(len(active))
    outfaces=reindex[np.maximum(cycles,0)];outfaces[cycles<0]=-1
    out=ArrayMesh(xyz[active],outfaces,classes[active],rest[active],np.array(anchors),m.generation)
    log['old_to_new_ids']=[int(reindex[mapping[k]]) for k in range(len(mapping))]
    try:
        check=topology(out)
        if not vertex_links_valid(out,check,np.unique(reindex[[r['ids'][0] for r in merges]])):
            raise ValueError('Disconnected or non-cycle vertex links / non-manifold pinch')
        signatures=[tuple(sorted(int(v) for v in face if v>=0)) for face in out.faces]
        if len(set(signatures))!=len(signatures):raise ValueError('Duplicate faces')
        if not np.isfinite(out.xyz).all():raise ValueError('Nonfinite welded XYZ')
        log['after']=metrics(out)
        if log['after']['zero_area_faces']:raise ValueError('Zero unsigned area after weld')
    except ValueError as e:log.update(status='REJECTED_INVALID',invalid_reason=str(e));return None,log
    log['status']='ACCEPTED_CHANGED' if merges else 'ACCEPTED_NO_PROXIMATE_POINTS'
    log['new_valence_histogram']={str(v):int((check['degree']==v).sum()) for v in np.unique(check['degree'])}
    log['genus_changed']=log['before']['Euler']!=log['after']['Euler']
    return out,log
