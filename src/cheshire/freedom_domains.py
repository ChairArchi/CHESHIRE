"""Geometrically selected coherent fold domains; no geometry repair.

Greedy graph-geodesic suppression separates competing hinge centres. Weighted
rotation proposals are combined with configurable concentration, not XYZ blur.
Equal scores use deterministic edge order; symmetry is not imposed.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from .reference_subdivision import ArrayMesh,topology
from .astra_rotating import features
from .freedom_patch import step as refine

def step(mesh,*,radius=400.,angle=1.2,spacing=.7,power=4.,polarity=-1.,source='current',direction='parallel',seed_quantile=.7):
    if not np.isfinite([radius,angle,spacing,power,polarity,seed_quantile]).all() or radius<=0 or not 0<=angle<=3.1 or not 0<=spacing<=2 or not 1<=power<=16 or polarity not in (-1.,1.) or not 0<=seed_quantile<=1:raise ValueError('Invalid explicit domain controls')
    if source not in ('current','rest') or direction not in ('parallel','transverse'):raise ValueError('Unknown observation or direction')
    t,actual,af=features(mesh)
    observed=mesh if source=='current' else ArrayMesh(mesh.rest,mesh.faces,mesh.classes,mesh.rest,mesh.anchors,mesh.generation)
    _,obs,feat=features(observed)
    out,_,state=refine(mesh,angle=0);base=state['base_xyz'];e=t['edges'];nv=len(mesh.xyz)
    bend=np.abs(feat['edge_angle']);length=obs['lengths'];threshold=max(float(np.quantile(bend,seed_quantile)),1e-8)
    candidates=np.flatnonzero((bend>=threshold-1e-12)&(length>=radius*.12))
    score=bend*np.sqrt(length)
    order=candidates[np.argsort(-score[candidates],kind='stable')]
    rt=topology(out);re=rt['edges'];le=np.linalg.norm(base[re[:,1]]-base[re[:,0]],axis=1)
    graph=coo_matrix((np.repeat(le,2),(re.ravel(),re[:,::-1].ravel())),shape=(len(base),len(base))).tocsr()
    blocked=np.zeros(len(e),bool);accum=np.zeros_like(base);total=np.zeros(len(base));weighted_norm=np.zeros(len(base));coverage=np.zeros(len(base),np.int32)
    winner=np.full(len(base),-1,np.int64);best=np.zeros(len(base));seeds=[];allids=[];alldist=[];allmoves=[];allweights=[];allseed=[];axes=[];origins=[];suppression=np.full(len(e),-1,np.int64)
    for seed in order:
        if blocked[seed]:continue
        axis=mesh.xyz[e[seed,1]]-mesh.xyz[e[seed,0]];axis/=np.linalg.norm(axis)
        normal=actual['nf'][t['ef'][seed]].sum(0);nn=np.linalg.norm(normal)
        if nn<=1e-12:continue
        normal/=nn
        if direction=='transverse':axis=np.cross(normal,axis);axis/=np.linalg.norm(axis)
        side=np.cross(normal,axis);origin=base[nv+seed]
        dist=dijkstra(graph,directed=True,indices=int(nv+seed),limit=max(radius,spacing*radius))
        suppress=dist[nv:nv+len(e)]<spacing*radius
        suppression[suppress&~blocked]=seed;blocked|=suppress
        ids=np.flatnonzero(dist<radius);delta=base[ids]-origin
        taper=(1-(dist[ids]/radius)**2)**2
        theta=polarity*angle*np.tanh(2*bend[seed])*np.tanh(5*(delta@side)/radius)*taper
        co=np.cos(theta)[:,None];si=np.sin(theta)[:,None]
        move=delta*co+np.cross(axis,delta)*si+axis*(delta@axis)[:,None]*(1-co)-delta
        # Dimensionless comparable weight prevents units from affecting domains.
        weight=(taper*bend[seed]/np.pi)**power
        accum[ids]+=move*weight[:,None];total[ids]+=weight;weighted_norm[ids]+=np.linalg.norm(move,axis=1)*weight;coverage[ids]+=1
        take=weight>best[ids];winner[ids[take]]=seed;best[ids[take]]=weight[take]
        seeds.append(seed);allids.append(ids);alldist.append(dist[ids]);allmoves.append(move);allweights.append(weight);allseed.append(np.full(len(ids),seed));axes.append(axis);origins.append(origin)
    disp=np.divide(accum,total[:,None],out=np.zeros_like(accum),where=total[:,None]>0)
    mean_norm=np.divide(weighted_norm,total,out=np.zeros_like(total),where=total>0)
    attenuation=np.divide(np.linalg.norm(disp,axis=1),mean_norm,out=np.ones_like(total),where=mean_norm>1e-12)
    out.xyz=base+disp
    if not np.isfinite(out.xyz).all():raise ValueError('Nonfinite domain output')
    tri=out.xyz[out.faces[:,:3]];area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2
    state.update(resolved_displacement=disp,selected_seed_edges=np.array(seeds,np.int64),candidate_seed_edges=candidates,seed_score=score,seed_observed_bend=bend,seed_observed_lengths=length,suppressed_by_seed=suppression,winning_seed=winner,proposal_attenuation=attenuation,patch_coverage=coverage,domain_vertex_ids=np.concatenate(allids) if allids else np.array([],np.int64),domain_seed_edges=np.concatenate(allseed) if allseed else np.array([],np.int64),domain_distances=np.concatenate(alldist) if alldist else np.array([]),domain_moves=np.concatenate(allmoves) if allmoves else np.empty((0,3)),domain_weights=np.concatenate(allweights) if allweights else np.array([]),domain_axes=np.array(axes),domain_origins=np.array(origins))
    meta=dict(operator='GEODESIC_DOMINANT_FOLD_DOMAINS',parameters=dict(radius=radius,angle=angle,spacing=spacing,power=power,polarity=polarity,source=source,direction=direction,seed_quantile=seed_quantile),candidate_seeds=len(candidates),selected_seeds=len(seeds),covered_vertices=int((total>0).sum()),attenuation_quantiles=np.quantile(attenuation[total>0],[0,.1,.5,.9,1]).tolist() if (total>0).any() else [],distance_quantiles=np.quantile(np.linalg.norm(disp,axis=1),[0,.5,.9,1]).tolist(),degenerate_triangles=int((area<=1e-12).sum()),symmetry='Not constrained; deterministic edge-order ties can break exact reflection.',limitations='Own finite rotation hypothesis; approximate graph geodesics; source=rest freezes only seed observation, current axes and distances remain active. Does not change genus or repair crossings.')
    return out,meta,state
