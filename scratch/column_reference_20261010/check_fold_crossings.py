"""Proper, non-adjacent triangle crossings. Excludes coplanar overlap/contact."""
import sys,json
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree

def segment_hits(a,b,t):
    e1=t[:,1]-t[:,0];e2=t[:,2]-t[:,0];d=b-a
    p=np.cross(d,e2);det=np.einsum('ij,ij->i',e1,p)
    safe=np.where(abs(det)>1e-10,det,1.)
    s=a-t[:,0];u=np.einsum('ij,ij->i',s,p)/safe;q=np.cross(s,e1)
    v=np.sum(d*q,axis=-1)/safe;w=np.einsum('ij,ij->i',e2,q)/safe
    return (abs(det)>1e-10)&(u>1e-7)&(v>1e-7)&(u+v<1-1e-7)&(w>1e-7)&(w<1-1e-7)

def count(m):
    t=m.triangles;f=m.faces;centers=t.mean(1);radii=np.linalg.norm(t-centers[:,None,:],axis=2).max(1);tree=cKDTree(centers);total=0
    for i in range(len(t)):
        ids=np.array(tree.query_ball_point(centers[i],radii[i]+radii.max()),dtype=int)
        ids=ids[ids>i]
        if not len(ids):continue
        ids=ids[np.all(t[ids].max(1)>=t[i].min(0),axis=1)&np.all(t[ids].min(1)<=t[i].max(0),axis=1)]
        if not len(ids):continue
        ids=ids[~np.any(f[ids,:,None]==f[i][None,None,:],axis=(1,2))]
        if not len(ids):continue
        other=t[ids];hits=np.zeros(len(ids),dtype=bool)
        for k in range(3):
            hits|=segment_hits(t[i,k],t[i,(k+1)%3],other)
            hits|=segment_hits(other[:,k],other[:,(k+1)%3],np.broadcast_to(t[i],other.shape))
        total+=int(hits.sum())
    return total

if __name__=='__main__':
    for folder in sys.argv[1:]:
        p=Path(folder);m=trimesh.load(p/'column.obj',force='mesh',process=False)
        n=count(m);report=json.loads((p/'validation.json').read_text())
        report['proper_nonadjacent_crossing_pairs']=n
        report['self_intersections']='proper crossing check only; excludes coplanar overlaps and adjacent-face intersections'
        (p/'validation.json').write_text(json.dumps(report,indent=2))
        print(str(p),n,flush=True)
