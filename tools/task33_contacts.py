"""Same transverse narrow phase as Task32; radius-binned exact broad phase.

Large cap triangles must not inflate every small triangle's query radius.
Coplanar/tangent/shared-vertex exclusions remain unchanged, so zero still does
not certify a valid solid. No triangle subsampling.
"""
import numpy as np
from scipy.spatial import cKDTree
from cheshire.task32_morphology import triangles
from task32_validation import segment_triangle_hit


def batch_hits(a, b):
    """Vectorize the six unchanged strict segment/triangle predicates."""
    hit=np.zeros(len(b),dtype=bool)
    for reverse in (False,True):
        target=np.broadcast_to(a,b.shape) if reverse else b
        source=b if reverse else np.broadcast_to(a,b.shape)
        e1=target[:,1]-target[:,0];e2=target[:,2]-target[:,0]
        for k in range(3):
            direction=source[:,(k+1)%3]-source[:,k]
            p=np.cross(direction,e2);det=(e1*p).sum(1)
            valid=np.abs(det)>=1e-13
            denominator=np.where(valid,det,1.)
            t=source[:,k]-target[:,0]
            cross=np.cross(t,e1)
            u=(t*p).sum(1)/denominator
            v=(direction*cross).sum(1)/denominator
            along=(e2*cross).sum(1)/denominator
            hit|=valid&(u>1e-8)&(u<1-1e-8)&(v>1e-8)&(u+v<1-1e-8)&(along>1e-8)&(along<1-1e-8)
    return hit


def contacts(mesh,cap=256):
    tri=triangles(mesh);span=float(np.ptp(mesh.xyz,axis=0).max())
    if span<=0:raise ValueError('Nonzero extent required.')
    p=(mesh.xyz[tri]-mesh.xyz.min(0))/span
    centres=p.mean(1);radius=np.linalg.norm(p-centres[:,None],axis=2).max(1)
    lo=p.min(1);hi=p.max(1)
    bins=np.floor(np.log2(np.maximum(radius,1e-15))).astype(int)
    groups=[]
    for key in np.unique(bins):
        ids=np.flatnonzero(bins==key)
        groups.append((ids,cKDTree(centres[ids]),float(radius[ids].max())))
    pairs=[];checked=0;queries=0
    # Bound broad-phase list allocation while amortizing Python/scipy overhead.
    for begin in range(0,len(p),512):
        aa=np.arange(begin,min(begin+512,len(p)))
        candidates=[[] for _ in aa]
        for ids,tree,maximum in groups:
            lists=tree.query_ball_point(centres[aa],radius[aa]+maximum+1e-10)
            queries+=len(aa)
            for offset,local in enumerate(lists):
                a=aa[offset];near=ids[np.asarray(local,dtype=np.int64)]
                near=near[near>a]
                if len(near):
                    sphere=np.linalg.norm(centres[near]-centres[a],axis=1)<=radius[a]+radius[near]+1e-10
                    candidates[offset].extend(near[sphere])
        batch_a=[];batch_b=[]
        for a,neighbours in zip(aa,candidates):
            near=np.asarray(sorted(neighbours),dtype=np.int64)
            if not len(near):continue
            eligible=(np.minimum(hi[a],hi[near])+1e-10>=np.maximum(lo[a],lo[near])).all(1)
            eligible&=~(tri[near][:,:,None]==tri[a][None,None,:]).any((1,2))
            chosen=near[eligible]
            batch_a.extend([a]*len(chosen));batch_b.extend(chosen)
        checked+=len(batch_a)
        for start in range(0,len(batch_a),8192):
            a=np.asarray(batch_a[start:start+8192],dtype=np.int64)
            b=np.asarray(batch_b[start:start+8192],dtype=np.int64)
            hit=batch_hits(p[a],p[b])
            pairs.extend(np.column_stack([a[hit],b[hit]]).tolist())
            if len(pairs)>=cap:pairs=pairs[:cap];break
        if len(pairs)>=cap:break
    return dict(transverse_contacts=len(pairs),pairs=pairs,sample_triangles=len(tri),total_triangles=len(tri),
                all_triangles_sampled=True,cap_reached=len(pairs)==cap,cap=cap,
                checked_nonadjacent_AABB_pairs=checked,radius_bins=len(groups),queries=queries,
                broad_phase='All bounding spheres, binned by radius; exact AABB and unchanged narrow phase.',
                exclusions='Shared vertices, coplanar, boundary/tangent contacts excluded; diagnostic polygon fan only. Zero does not certify solid geometry.')
