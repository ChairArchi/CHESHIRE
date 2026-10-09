"""Streaming all-triangle transverse contact check; same narrow-phase exclusions.

Vectorized AABB/shared-vertex filtering reduces Python overhead. This still
does not detect coplanar, tangent or adjacent-face embedding failures.
"""
import argparse
from pathlib import Path
from time import perf_counter
import numpy as np
from scipy.spatial import cKDTree
from task32_research import ROOT,read,write_new,sha,guarded
from task29_search import load_mesh
from task32_validation import segment_triangle_hit
from cheshire.task32_morphology import triangles


def full_contacts(mesh,cap=256):
    tri=triangles(mesh);span=float(np.ptp(mesh.xyz,axis=0).max())
    if span<=0:raise ValueError('Nonzero domain extent required.')
    p=(mesh.xyz[tri]-mesh.xyz.min(0))/span
    centres=p.mean(1);radius=np.linalg.norm(p-centres[:,None],axis=2).max(1)
    tree=cKDTree(centres);maximum=float(radius.max());lo=p.min(1);hi=p.max(1)
    contacts=[];checked=0
    for a in range(len(p)):
        neighbours=np.array(tree.query_ball_point(centres[a],radius[a]+maximum),dtype=np.int64)
        neighbours=neighbours[neighbours>a]
        if not len(neighbours):continue
        eligible=(np.minimum(hi[a],hi[neighbours])+1e-10>=np.maximum(lo[a],lo[neighbours])).all(1)
        eligible&=~(tri[neighbours][:,:,None]==tri[a][None,None,:]).any((1,2))
        for b in neighbours[eligible]:
            checked+=1;hit=False
            for one,two in ((p[a],p[b]),(p[b],p[a])):
                if any(segment_triangle_hit(one[k],one[(k+1)%3],two) for k in range(3)):
                    hit=True;break
            if hit:
                contacts.append([a,int(b)])
                if len(contacts)==cap:break
        if len(contacts)==cap:break
    return dict(transverse_contacts=len(contacts),pairs=contacts,sample_triangles=len(tri),total_triangles=len(tri),
        all_triangles_sampled=True,cap_reached=len(contacts)==cap,cap=cap,checked_nonadjacent_AABB_pairs=checked,
        exclusions='Shared vertices, coplanar, boundary/tangent contacts excluded; diagnostic polygon fan only. Zero does not certify solid geometry.')


def audit(request,tag):
    output=ROOT/'validation'/tag;output.mkdir(parents=True,exist_ok=False);rows=[]
    for item in read(request)['items']:
        path=Path(item['stage']).resolve()
        if not path.is_relative_to((ROOT/'candidates').resolve()):raise ValueError('Only Task32 checkpoint reads allowed.')
        start=perf_counter();m=load_mesh(path)
        row=dict(**item,mesh_sha256=sha(path/'mesh.npz'),contacts=full_contacts(m),seconds=perf_counter()-start)
        write_new(output/(item['id']+'.json'),row);rows.append(row)
        print(item['id'],row['contacts']['transverse_contacts'],round(row['seconds'],2),flush=True)
    write_new(output/'summary.json',rows)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--tag',required=True)
    p.add_argument('--worker',action='store_true');a=p.parse_args()
    if any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-' for c in a.tag):raise ValueError('Safe tag required.')
    if a.worker:audit(a.request,a.tag)
    else:
        result=guarded(['--request',str(a.request),'--tag',a.tag,'--worker'],ROOT/'logs'/('full_contacts_'+a.tag),worker_script=Path(__file__))
        print(result)
        if result['exit_code']:raise SystemExit(result['exit_code'])
