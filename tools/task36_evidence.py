"""Actual native triangle geometry, finite cuts and oriented symmetry evidence."""
import json,sys
from pathlib import Path
from time import perf_counter
import numpy as np
from scipy.spatial import cKDTree
from scipy.signal import find_peaks
import trimesh
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_preserve import sha,write_new
from task29_search import load_mesh
from task32_validation import embedding
from task33_contacts import contacts
from task33_planar import inspect_segments
from task35_analyze import radial_cut,longitudinal_profile,peaks,child_valleys,open_valleys
ROOT=Path('E:/CHESHIRE_DATA/task36')


def cycles(tri):
    first=tri.argmin(1);v=tri[np.arange(len(tri))[:,None],(first[:,None]+np.arange(3))%3]
    return v[np.lexsort((v[:,2],v[:,1],v[:,0]))]


def symmetry(mesh):
    tree=cKDTree(mesh.xyz);tri=mesh.faces[:,:3];original=cycles(tri);result={}
    for name,matrix in [('X',np.diag([-1,1,1])),('Y',np.diag([1,-1,1])),('QUARTER_TURN',np.array([[0,-1,0],[1,0,0],[0,0,1]]))]:
        distance,ids=tree.query(mesh.xyz@matrix.T);mapped=ids[tri]
        if np.linalg.det(matrix)<0:mapped=mapped[:,[0,2,1]]
        result[name]=dict(geometry_max=float(distance.max()),bijective=len(np.unique(ids))==len(ids),oriented_face_cycle_failures=int(np.count_nonzero(np.any(cycles(mapped)!=original,axis=1))))
    return result


def audit(request,tag):
    contact_check=contacts
    if request.get('contact_engine')=='bvh':
        from task36_contacts import contacts as contact_check
    dest=ROOT/'validation'/tag;dest.mkdir(parents=True,exist_ok=False);write_new(dest/'request.json',request);rows=[]
    for item in request['items']:
        start=perf_counter();stage=Path(item['stage']);mesh=load_mesh(stage)
        value=dict(**item,mesh_sha256=sha(stage/'mesh.npz'),embedding=embedding(mesh),symmetry=symmetry(mesh),contacts=contact_check(mesh))
        fixed=(mesh.rest[:,2]==0)|(mesh.rest[:,2]==4000)
        value['end_plane_z_error']=float(np.max(np.abs(mesh.xyz[fixed,2]-mesh.rest[fixed,2])))
        value['endcap_xy_displacement']=float(np.max(np.abs(mesh.xyz[fixed,:2]-mesh.rest[fixed,:2])))
        model=trimesh.Trimesh(vertices=mesh.xyz,faces=mesh.faces[:,:3],process=False);raw={};measurements=[]
        planes=[(f'Z{z}',[0,0,z+.12345],[0,0,1],[0,1]) for z in request.get('section_z',list(range(500,3501,250)))]
        planes += [('XZ',[0,0,0],[0,1,0],[0,2]),('YZ',[0,0,0],[1,0,0],[1,2]),('DIAGONAL',[0,0,0],[1,-1,0],None)]
        for name,origin,normal,axes in planes:
            lines=trimesh.intersections.mesh_plane(model,normal,origin);raw[name]=lines
            uv=lines[:,:,axes] if axes else np.stack([(lines[:,:,0]+lines[:,:,1])/2**.5,lines[:,:,2]],axis=-1)
            row=dict(name=name,origin=origin,normal=normal,**inspect_segments(uv))
            signal,coverage=radial_cut(lines) if name.startswith('Z') else longitudinal_profile(lines,name)
            row['profile_coverage']=coverage;raw[name+'_profile']=signal
            valid=all(v==0 for v in coverage.values())
            row['profile_peaks_15']=len(peaks(signal)) if valid and name.startswith('Z') else int(len(find_peaks(signal,prominence=15)[0])) if valid else None
            row['profile_peaks_5']=int(len(find_peaks(np.tile(signal,3) if name.startswith('Z') else signal,prominence=5)[0])/(3 if name.startswith('Z') else 1)) if valid else None
            measurements.append(row)
        np.savez_compressed(dest/(item['id']+'_cuts.npz'),**raw)
        value.update(cuts=measurements,seconds=perf_counter()-start);write_new(dest/(item['id']+'.json'),value);rows.append(value)
        print(item['id'],'contacts',value['contacts']['transverse_contacts'],'degenerate',value['embedding']['degenerate_triangles'],'seconds',round(value['seconds'],2),flush=True)
    write_new(dest/'summary.json',rows)


def hierarchy(request,tag):
    dest=ROOT/'measurements'/tag;dest.mkdir(parents=True,exist_ok=False);rows=[]
    for group in request['groups']:
        loaded=[dict(np.load(p)) for p in group['cuts']]
        keys=[k for k in loaded[0] if k.endswith('_profile')]
        for key in keys:
            signals=[v[key] for v in loaded]
            # Only use single-valued profiles confirmed by their audit JSON.
            audits=[json.loads(Path(p).with_name(Path(p).name.replace('_cuts.npz','.json')).read_text()) for p in group['cuts']]
            cutname=key[:-8];status=[next(c for c in a['cuts'] if c['name']==cutname)['profile_coverage'] for a in audits]
            valid=all(all(v==0 for v in s.values()) for s in status)
            counts=[]
            if valid:
                for a,b in zip(signals,signals[1:]):counts.append(child_valleys(a,b) if cutname.startswith('Z') else open_valleys(a,b))
            rows.append(dict(group=group['id'],cut=cutname,valid=valid,coverage=status,transitions=counts,
                caveat='Finite fixed-world section basins, not material ancestry or continuous ridge certification.'))
    write_new(dest/'hierarchy.json',rows);print(tag,'finite rows',len(rows),flush=True)
