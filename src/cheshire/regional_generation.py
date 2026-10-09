"""Task31 region memory and bounded coarse topology edits; opt-in research.

Region names express a tested intention, not a claim of visual achievement.
No random/ID-driven field, postprocessing or semantic architecture generator.
"""
import copy
import numpy as np
from .reference_subdivision import ArrayMesh,WEIGHTS,topology,fields,mean_incident,intrinsic_signal,subdivide
from .polygon_dual_subdivision import doo_sabin

MODES=('BULB','RIB','DEPTH','CHANNEL')
CC_MODES=(dict(wf=.06,w1=.25,w2=-.15,wp=.02,w3=.2,w4=.05),
          dict(wf=.10,we=-.02,wp=.02,w1=-.35,w2=-.15,w3=-.6,w4=.25),
          dict(wf=-.10,we=-.04,wp=-.02,w1=.1,w2=.1,w3=.05,w4=-.15),
          dict(wf=-.03,w1=.25))
DS_MODES=(dict(w1=-.05,wf=.07),dict(w1=.85,wf=.04),dict(w1=.35,wf=-.08),dict(w1=.2,wf=-.025))
KINDS=dict(wf='face',w3='face',w4='face',w6='face',w1='edge',we='edge',w7='edge',w2='vertex',wp='vertex')


def birth(mesh,descriptor='axis'):
    t=topology(mesh);f=fields(mesh,t)
    if descriptor=='axis':
        # Absolute environment axes: X -> depth, Y -> rib, Z -> bulb.
        ids=np.array([2,1,0])[np.argmax(np.abs(f['nf']),axis=1)];info=dict(axis_mapping='X:DEPTH,Y:RIB,Z:BULB')
    elif descriptor=='fold':
        a,b=t['ef'].T;d=f['c'][b]-f['c'][a]
        signal=np.zeros(len(mesh.faces));counts=np.zeros(len(mesh.faces))
        # Normal-relative neighbour displacement: negative around convex crests,
        # positive around concave folds. Geometric scalar, independent of IDs.
        np.add.at(signal,a,(f['nf'][a]*d).sum(1)/f['se'])
        np.add.at(signal,b,-(f['nf'][b]*d).sum(1)/f['se'])
        np.add.at(counts,a,1);np.add.at(counts,b,1);signal/=counts
        lo,hi=np.quantile(signal,[1/3,2/3]);ids=np.where(signal<lo,0,np.where(signal>hi,2,1))
        info=dict(quantile_thresholds=[float(lo),float(hi)],signal_range=[float(signal.min()),float(signal.max())])
    else:raise ValueError('Undeclared regional descriptor.')
    return np.eye(4)[ids],dict(descriptor=descriptor,born_generation=mesh.generation,counts=np.bincount(ids,minlength=4).tolist(),**info)


def inherit(members,parents):
    if np.any(parents<-1) or np.any(parents>=len(members)):raise ValueError('Invalid actual parent support.')
    if parents.ndim==1:
        if np.any(parents<0):raise ValueError('Empty actual parent support.')
        return members[parents]
    valid=parents>=0;result=np.zeros((len(parents),4),float)
    if not valid.any(1).all():raise ValueError('Empty actual parent support.')
    for j in range(parents.shape[1]):
        good=valid[:,j];result[good]+=members[parents[good,j]]
    return result/valid.sum(1)[:,None]


def regional_controls(mesh,members,spec,contrast):
    if members.shape!=(len(mesh.faces),4) or not np.isfinite(members).all() or np.any(members<0) or not np.allclose(members.sum(1),1):raise ValueError('Invalid memberships.')
    if not 0<=contrast<=1:raise ValueError('Contrast outside [0,1].')
    if spec['scheme']!='REFERENCE_COUPLED':
        return {k:(1-contrast)*spec['weights'].get(k,0)+contrast*(members@np.array([m.get(k,0) for m in DS_MODES])) for k in ('w1','wf')}
    t=topology(mesh);f=fields(mesh,t);rule=copy.deepcopy(spec.get('intrinsic'));g=mesh.generation+1
    if rule and g>spec.get('lock_end',999):rule.pop('lock_threshold',None)
    signal=intrinsic_signal(mesh,t,f,rule);signals={k:None for k in ('face','edge','vertex')}
    if signal is not None:
        signals=dict(face=mean_incident(signal[t['a']],t['fi'],len(mesh.faces)),edge=signal[t['edges']].mean(1),vertex=signal)
    controls={};w=spec['row']['weights']
    for k in WEIGHTS:
        kind=KINDS[k];desired=members@np.array([m.get(k,0) for m in CC_MODES])
        if kind=='edge':desired=desired[t['ef']].mean(1)
        elif kind=='vertex':desired=mean_incident(np.repeat(desired,t['n']),t['a'],len(mesh.xyz))
        original=float(w.get(k,0));s=signals[kind]
        if s is not None and k in rule['controls']:
            lo,hi=rule['controls'][k];original=original+lo+(hi-lo)*s
        controls[k]=(1-contrast)*original+contrast*desired
    return controls


def advance(mesh,roles,members,spec,definition):
    if spec.get('generation')!=mesh.generation+1:raise ValueError('Wrong generation for actual checkpoint.')
    if definition.get('memory') not in ('persistent','remeasured'):raise ValueError('Unknown regional memory policy.')
    if members is not None and definition.get('memory')=='remeasured':members,_=birth(mesh,definition['descriptor'])
    controls=None if members is None or mesh.generation<2 else regional_controls(mesh,members,spec,definition['contrast'])
    if spec['scheme']=='REFERENCE_COUPLED':
        rule=copy.deepcopy(spec.get('intrinsic'))
        if rule and mesh.generation+1>spec.get('lock_end',999):rule.pop('lock_threshold',None)
        out,meta,state=subdivide(mesh,spec['row'],scale_mode=spec['scale'],intrinsic=rule,resolved_controls=controls)
        parents=state['parent_face'];out_roles=roles[parents]
    elif spec['scheme']=='REFERENCE_DOO_SABIN':
        out,out_roles,meta,state=doo_sabin(mesh,spec['weights'],face_roles=roles,resolved_controls=controls);parents=state['parent_faces']
    else:raise ValueError('Unknown subdivision scheme.')
    next_members=None if members is None else inherit(members,parents)
    meta['regional_definition']=definition
    return out,out_roles,next_members,meta,state


def mouth_pair(mesh,target=None):
    t=topology(mesh);f=fields(mesh,t);c=f['c'];nf=f['nf']
    goal=np.asarray(target if target is not None else (mesh.xyz.min(0)+mesh.xyz.max(0))/2)
    front=np.flatnonzero((nf[:,1]<-.6)&(t['n']==4));rear=np.flatnonzero((nf[:,1]>.6)&(t['n']==4))
    if not len(front) or not len(rear):raise ValueError('No geometric opposing quad mouths.')
    a=int(front[np.argmin(((c[front][:,[0,2]]-goal[[0,2]])**2).sum(1))])
    rear=np.array([b for b in rear if not np.intersect1d(mesh.faces[a,:4],mesh.faces[b,:4]).size])
    if not len(rear):raise ValueError('No disjoint opposing mouths.')
    b=int(rear[np.argmin(((c[rear][:,[0,2]]-c[a,[0,2]])**2).sum(1))])
    return a,b


def coarse_edit(mesh,roles,members,edit,target=None):
    """Single G2 collar/recess or annulus bridge. Full provenance, no repair.
    Through tunnel changes Euler by -2; capped recess preserves Euler.
    """
    if mesh.generation!=2:raise ValueError('Coarse edits are explicitly at G2.')
    a,b=mouth_pair(mesh,target);f=fields(mesh);kind=edit['kind'];ratio=edit['ratio']
    if kind not in ('recess','opening') or not 0<ratio<1:raise ValueError('Invalid edit.')
    xyz=mesh.xyz.tolist();rest=mesh.rest.tolist();classes=mesh.classes.tolist()
    source=[a,b] if kind=='opening' else [a,b];removed=set(source)
    fs=[];ps=[];channel=[];ring_data=[]
    for i,q in enumerate(mesh.faces):
        if i not in removed:fs.append(q[q>=0].tolist());ps.append([i]);channel.append(False)
    maxdepth=min(f['sf'][source].min()*edit.get('depth',0),(np.linalg.norm(f['c'][a]-f['c'][b]))*.2)
    for face in source:
        outer=mesh.faces[face,:4].tolist();ring=outer;center=f['c'][face]
        levels=edit.get('levels',1) if kind=='recess' else 1
        for level in range(levels):
            new=[]
            for vertex in ring:
                p=center+ratio*(np.array(xyz[vertex])-center)
                if kind=='recess':p-=f['nf'][face]*maxdepth/levels
                new.append(len(xyz));xyz.append(p.tolist())
                rcenter=mesh.rest[outer].mean(0)
                rest.append((rcenter+ratio*(np.asarray(rest[vertex])-rcenter)).tolist())
                classes.append(-1)
            for j in range(4):fs.append([ring[j],ring[(j+1)%4],new[(j+1)%4],new[j]]);ps.append([face]);channel.append(True)
            ring=new
        ring_data.append(ring)
        if kind=='recess':fs.append(ring);ps.append([face]);channel.append(True)
    if kind=='opening':
        A=np.array(ring_data[0]);raw=np.array(ring_data[1])[::-1]
        candidates=[np.roll(raw,j) for j in range(4)]
        B=min(candidates,key=lambda r:np.sum((np.array(xyz)[A]-np.array(xyz)[r])**2))
        for j in range(4):fs.append([int(A[j]),int(A[(j+1)%4]),int(B[(j+1)%4]),int(B[j])]);ps.append([a,b]);channel.append(True)
    parents=np.full((len(fs),2),-1,np.int64)
    for i,p in enumerate(ps):parents[i,:len(p)]=p
    anchors=np.full((len(fs),3),-1,np.int64)
    for i,p in enumerate(ps):
        v=mesh.anchors[p];anchors[i]=np.where((v==v[0]).all(0),v[0],-1)
    out=ArrayMesh(np.asarray(xyz),np.asarray(fs,np.int64),np.asarray(classes,np.int8),np.asarray(rest),anchors,2)
    before=topology(mesh);after=topology(out)
    e0=len(mesh.xyz)-len(before['edges'])+len(mesh.faces);e1=len(out.xyz)-len(after['edges'])+len(out.faces)
    if e1-e0!=(-2 if kind=='opening' else 0):raise ValueError('Wrong edited Euler.')
    out_roles=roles[parents[:,0]].copy();out_roles[parents[:,1]>=0]=-1
    out_members=None if members is None else inherit(members,parents)
    if out_members is not None:out_members[np.asarray(channel)]=[0,0,0,1]
    meta=dict(edit=edit,mouth_faces=[a,b],mouth_centroids=f['c'][source].tolist(),ring_vertices=ring_data,
        actual_depth=maxdepth,Euler_before=e0,Euler_after=e1,explicit_designed_tunnel=kind=='opening',
        caveat='Combinatorial closedness is not proof of intersection-free embedding.')
    return out,out_roles,out_members,meta,dict(parent_faces=parents,channel_faces=np.asarray(channel))
