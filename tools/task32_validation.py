"""Actual Task32 topology/embedding evidence; no geometry repair or pass inflation."""
import argparse
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from time import perf_counter
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from task32_research import ROOT,REPO,read,write_new,sha,load_mesh,guarded
from cheshire.reference_subdivision import topology,metrics
from cheshire.task32_morphology import triangles,signed_volume_gradient


def manifold_links(mesh):
    q=mesh.faces;mask=q>=0;n=mask.sum(1)
    vertices=q[mask]
    slot=np.arange(q.shape[1])[None,:]
    previous=q[np.arange(len(q))[:,None],(slot-1)%n[:,None]][mask]
    following=q[np.arange(len(q))[:,None],(slot+1)%n[:,None]][mask]
    order=np.argsort(vertices,kind='stable');vertices=vertices[order]
    previous=previous[order];following=following[order]
    ids,start,count=np.unique(vertices,return_index=True,return_counts=True)
    invalid=[]
    for vertex,begin,size in zip(ids,start,count):
        links=defaultdict(list)
        for a,b in zip(previous[begin:begin+size],following[begin:begin+size]):
            links[int(a)].append(int(b));links[int(b)].append(int(a))
        if any(len(ns)!=2 for ns in links.values()):invalid.append(int(vertex));continue
        pending=[next(iter(links))];seen=set()
        while pending:
            v=pending.pop()
            if v not in seen:seen.add(v);pending.extend(links[v])
        if len(seen)!=len(links):invalid.append(int(vertex))
    return dict(checked_vertices=len(ids),invalid_vertex_links=invalid,
                orphan_vertices=int(len(mesh.xyz)-len(ids)))


def segment_triangle_hit(a,b,tri):
    direction=b-a;e1=tri[1]-tri[0];e2=tri[2]-tri[0]
    p=np.cross(direction,e2);det=float(np.dot(e1,p))
    if abs(det)<1e-13:return False
    t=a-tri[0];u=float(np.dot(t,p)/det)
    v=float(np.dot(direction,np.cross(t,e1))/det)
    along=float(np.dot(e2,np.cross(t,e1))/det)
    return bool(1e-8<u<1-1e-8 and 1e-8<v and u+v<1-1e-8 and 1e-8<along<1-1e-8)


def transverse_contacts(mesh,maximum_sample=4096,cap=256):
    tri=triangles(mesh)
    if len(tri)<=12000:indices=np.arange(len(tri))
    else:indices=np.unique(np.linspace(0,len(tri)-1,maximum_sample).astype(int))
    selected=tri[indices]
    span=float(np.ptp(mesh.xyz,axis=0).max())
    p=(mesh.xyz[selected]-mesh.xyz.min(0))/span
    centres=p.mean(1);radius=np.linalg.norm(p-centres[:,None],axis=2).max(1)
    tree=cKDTree(centres);maximum=float(radius.max());lo=p.min(1);hi=p.max(1)
    contacts=[];checked=0
    for a in range(len(p)):
        neighbours=tree.query_ball_point(centres[a],radius[a]+maximum)
        for b in neighbours:
            if b<=a or np.intersect1d(selected[a],selected[b]).size:continue
            if np.any(lo[a]>hi[b]+1e-10) or np.any(lo[b]>hi[a]+1e-10):continue
            checked+=1;hit=False
            for one,two in ((p[a],p[b]),(p[b],p[a])):
                if any(segment_triangle_hit(one[k],one[(k+1)%3],two) for k in range(3)):
                    hit=True;break
            if hit:
                contacts.append([int(indices[a]),int(indices[b])])
                if len(contacts)==cap:break
        if len(contacts)==cap:break
    return dict(transverse_contacts=len(contacts),pairs=contacts,sample_triangles=len(indices),
        total_triangles=len(tri),all_triangles_sampled=len(indices)==len(tri),checked_nonadjacent_AABB_pairs=checked,
        cap_reached=len(contacts)==cap,cap=cap,
        exclusions='Shared vertices, coplanar, boundary/tangent contacts excluded; fan diagnostic; zero never certifies solid validity.')


def embedding(mesh):
    t=topology(mesh);tri=triangles(mesh);p=mesh.xyz[tri]
    cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);area=np.linalg.norm(cross,axis=1)/2
    q=mesh.faces
    opposed=0
    if q.shape[1]>=4:
        quad=q[(q>=0).sum(1)==4]
        pts=mesh.xyz[quad[:,:4]]
        one=np.cross(pts[:,1]-pts[:,0],pts[:,2]-pts[:,0])
        two=np.cross(pts[:,2]-pts[:,0],pts[:,3]-pts[:,0])
        opposed=int(((one*two).sum(1)<0).sum())
    edges=t['edges'];adj=coo_matrix((np.ones(2*len(edges)),(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(len(mesh.xyz),)*2)
    components,_=connected_components(adj,directed=False)
    volume,_=signed_volume_gradient(mesh.xyz-mesh.xyz.mean(0),tri)
    return dict(**metrics(mesh),**manifold_links(mesh),connected_components=int(components),
        diagnostic_fan_triangles=len(tri),min_triangle_area=float(area.min()),
        degenerate_triangles=int((area<1e-10).sum()),opposed_quad_fan_normals=opposed,
        signed_algebraic_volume=volume,
        warning='Finite/closed/manifold graph and algebraic volume do not establish intersection-free solid geometry.')


def section_segments(mesh):
    import trimesh
    obj=trimesh.Trimesh(vertices=mesh.xyz,faces=triangles(mesh),process=False)
    records=[];saved={}
    for name,normal,origin in [('mid_depth',[0,1,0],[-400.036865234375,-18.533447265625,1750])]+[
            (f'z{z}',[0,0,1],[0,0,z]) for z in (650,1300,2200,3050)]:
        segments=trimesh.intersections.mesh_plane(obj,normal,origin)
        saved[name]=segments
        records.append(dict(name=name,plane_normal=normal,plane_origin=origin,
            segment_count=len(segments),bounds_min=segments.reshape(-1,3).min(0).tolist() if len(segments) else None,
            bounds_max=segments.reshape(-1,3).max(0).tolist() if len(segments) else None))
    return records,saved


def audit(tag,ids):
    out=ROOT/'validation'/tag;out.mkdir(parents=True,exist_ok=False)
    rows=[]
    for name in ids:
        dest=ROOT/'candidates'/name
        completed=read(dest/'completed.json');stage=Path(completed['final_stage']);m=load_mesh(stage)
        start=perf_counter();row=dict(id=name,stage=str(stage),mesh_sha256=sha(stage/'mesh.npz'),embedding=embedding(m),
                                  contacts=transverse_contacts(m))
        sections,segments=section_segments(m);np.savez_compressed(out/(name+'_sections.npz'),**segments)
        row.update(sections=sections,section_sha256=sha(out/(name+'_sections.npz')),seconds=perf_counter()-start)
        write_new(out/(name+'.json'),row);rows.append(row)
        print(name,'links',len(row['embedding']['invalid_vertex_links']),'crossings',row['contacts']['transverse_contacts'],
              'opposed quads',row['embedding']['opposed_quad_fan_normals'],round(row['seconds'],2),'s',flush=True)
    write_new(out/'summary.json',rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);parser.add_argument('--ids',nargs='+',required=True)
    parser.add_argument('--worker',action='store_true');a=parser.parse_args()
    if any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-' for c in a.tag):raise ValueError('Safe audit tag required.')
    if a.worker:audit(a.tag,a.ids)
    else:
        result=guarded(['--worker','--tag',a.tag,'--ids',*a.ids],ROOT/'logs'/('validation_'+a.tag),worker_script=Path(__file__))
        print(result)
        if result['exit_code']:raise SystemExit(result['exit_code'])
