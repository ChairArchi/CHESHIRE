"""Actual planar-cut graph and crossing/touch checks, including collinear overlap.

This supplements the transverse 3D diagnostic, it does not certify the solid
between the inspected planes. Coordinate snapping and orientation tolerances
are recorded, not used to repair the mesh.
"""
import json,sys,argparse
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_preserve import ROOT,write_new,sha
from task29_search import load_mesh
from task32_validation import section_segments


def inspect_segments(segments):
    lines=np.asarray(segments,dtype=float)
    points,inverse=np.unique(np.round(lines.reshape(-1,2),7),axis=0,return_inverse=True)
    edges=inverse.reshape(-1,2)
    degree=np.bincount(edges.ravel(),minlength=len(points))
    graph=coo_matrix((np.ones(2*len(edges)),(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(len(points),)*2)
    count,_=connected_components(graph,directed=False)
    lo=lines.min(1);hi=lines.max(1);order=np.argsort(lo[:,0]);failures=[]
    tol=1e-8
    def cross(a,b):return a[0]*b[1]-a[1]*b[0]
    for slot,a in enumerate(order):
        for b in order[slot+1:]:
            if lo[b,0]>hi[a,0]+tol:break
            if np.any(np.maximum(lo[a],lo[b])>np.minimum(hi[a],hi[b])+tol):continue
            p,q=lines[a];r,s=lines[b]
            oa,ob=cross(q-p,r-p),cross(q-p,s-p)
            oc,od=cross(s-r,p-r),cross(s-r,q-r)
            shared=bool(np.intersect1d(edges[a],edges[b]).size)
            collinear=max(abs(oa),abs(ob),abs(oc),abs(od))<=tol
            hit=False
            if collinear:
                axis=int(np.argmax(np.abs(q-p)))
                hit=min(max(p[axis],q[axis]),max(r[axis],s[axis]))-max(min(p[axis],q[axis]),min(r[axis],s[axis]))>tol
            elif not shared:
                hit=(oa*ob<0 and oc*od<0)
                for point,one,two,value in [(r,p,q,oa),(s,p,q,ob),(p,r,s,oc),(q,r,s,od)]:
                    hit|=abs(value)<=tol and np.all(point>=np.minimum(one,two)-tol) and np.all(point<=np.maximum(one,two)+tol)
            if hit:failures.append([int(a),int(b)])
    return dict(segments=len(lines),nodes=len(points),components=int(count),non_cycle_nodes=int((degree!=2).sum()),
                zero_length_segments=int((np.linalg.norm(lines[:,1]-lines[:,0],axis=1)<tol).sum()),
                crossings_touches_overlaps=failures,snap_decimals=7,orientation_tolerance=tol)


def audit(candidate,tag):
    job=ROOT/'candidates'/candidate
    stage=Path(json.loads((job/'completed.json').read_text())['final_stage'])
    mesh=load_mesh(stage);info,segments=section_segments(mesh);rows=[]
    for key in ['z650','z1300','z2200','z3050']:
        seg=segments[key];row=dict(plane=key,**inspect_segments(seg[:,:,[0,1]]))
        pts=seg.reshape(-1,3);left=pts[pts[:,0]<-400.036865234375];right=pts[pts[:,0]>-400.036865234375]
        if key!='z3050' and len(left) and len(right):row['main_portal_gap_X']=float(right[:,0].min()-left[:,0].max())
        rows.append(row)
    write_new(ROOT/'validation'/(tag+'.json'),dict(candidate=candidate,stage=str(stage),mesh_sha256=sha(stage/'mesh.npz'),planes=rows,
        caveat='Finite sampled world-plane cuts; snap is solely for graph identification, raw XYZ line segments used for intersection tests. This does not certify the 3D solid between planes.'))
    print(candidate,[(r['plane'],r['components'],len(r['crossings_touches_overlaps']),r.get('main_portal_gap_X')) for r in rows])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
    if not all(v.replace('_','').isalnum() for v in (a.candidate,a.tag)):raise ValueError('Safe names required.')
    audit(a.candidate,a.tag)
