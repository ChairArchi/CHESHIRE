"""Trace finite planar warnings to authoritative native triangle IDs.

No mesh edits or filtered profiles. Recomputed cut order must match saved XYZ.
Classification is diagnostic: excluded contacts are not certified harmless.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np
import trimesh
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task29_search import load_mesh
from task33_contacts import batch_hits
from task36_triangle_interval import interval_hits
from task33_preserve import sha,write_new
ROOT=Path('E:/CHESHIRE_DATA/task36')


def trace(audit,tag):
    certificate=json.loads(audit.read_text());stage=Path(certificate['stage']);mesh=load_mesh(stage)
    if sha(stage/'mesh.npz')!=certificate['mesh_sha256']:raise ValueError('Audit identity mismatch.')
    model=trimesh.Trimesh(mesh.xyz,mesh.faces[:,:3],process=False)
    stored=np.load(audit.with_name(audit.stem+'_cuts.npz'));span=np.ptp(mesh.xyz,axis=0).max();rows=[]
    for cut in certificate['cuts']:
        lines,face_ids=trimesh.intersections.mesh_plane(model,cut['normal'],cut['origin'],return_faces=True)
        if not np.array_equal(lines,stored[cut['name']]):raise ValueError('Cut/triangle order mismatch.')
        pairs=np.asarray(cut['crossings_touches_overlaps'],int).reshape(-1,2)
        if not len(pairs):rows.append(dict(name=cut['name'],warnings=0,classes={},pairs=[]));continue
        ids=face_ids[pairs];vertices=mesh.faces[ids,:3];tri=mesh.xyz[vertices]/span
        old=batch_hits(tri[:,0],tri[:,1]);new=interval_hits(tri[:,0],tri[:,1])
        shared=(vertices[:,0,:,None]==vertices[:,1,None,:]).any((1,2))
        normals=np.cross(tri[:,:,1]-tri[:,:,0],tri[:,:,2]-tri[:,:,0]);normals/=np.maximum(np.linalg.norm(normals,axis=2,keepdims=True),1e-30)
        parallel=np.linalg.norm(np.cross(normals[:,0],normals[:,1]),axis=1)<=1e-10
        uv=lines[:,:,[0,1]] if cut['name'].startswith('Z') else lines[:,:,[0,2]] if cut['name']=='XZ' else lines[:,:,[1,2]] if cut['name']=='YZ' else np.stack([(lines[:,:,0]+lines[:,:,1])/2**.5,lines[:,:,2]],axis=-1)
        p,q=uv[pairs[:,0],0],uv[pairs[:,0],1];r,s=uv[pairs[:,1],0],uv[pairs[:,1],1]
        cross=lambda a,b:a[:,0]*b[:,1]-a[:,1]*b[:,0]
        proper=(cross(q-p,r-p)*cross(q-p,s-p)<0)&(cross(s-r,p-r)*cross(s-r,q-r)<0)
        labels=np.where(old,'original_strict_hit',np.where(new,'positive_noncoplanar_interval',np.where(parallel,'coplanar_or_parallel','excluded_boundary_or_tangent')))
        records=[dict(triangles=pair.tolist(),classification=str(label),shared_vertex=bool(sh),proper_planar_cross=bool(pr)) for pair,label,sh,pr in zip(ids,labels,shared,proper)]
        rows.append(dict(name=cut['name'],warnings=len(pairs),proper_planar_crossings=int(proper.sum()),classes={str(k):int((labels==k).sum()) for k in np.unique(labels)},pairs=records))
        print(cut['name'],rows[-1]['classes'],flush=True)
    dest=ROOT/'validation'/tag;dest.mkdir(parents=True,exist_ok=False)
    write_new(dest/'section_trace.json',dict(audit=str(audit),audit_sha256=sha(audit),native_sha256=certificate['mesh_sha256'],rows=rows,
        caveat='Finite section warnings traced to native IDs. Coplanar/parallel, shared-vertex and boundary-only/tangent cases remain limitations, not solid-validity certificates.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--audit',type=Path,required=True);p.add_argument('--tag',required=True);a=p.parse_args();trace(a.audit,a.tag)
