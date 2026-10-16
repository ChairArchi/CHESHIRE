"""Build a new macro grammar, actual closed solid union and descendant meshes."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import time
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import grammar_kernel as k


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()


def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')


def quality(x,t):
    edges=np.concatenate([t[:,[0,1]],t[:,[1,2]],t[:,[2,0]]])
    key=np.sort(edges,axis=1)
    _,inv,count=np.unique(key,axis=0,return_inverse=True,return_counts=True)
    orient=np.bincount(inv,weights=np.sign(edges[:,1]-edges[:,0]))
    p=x[t];areas=np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)/2
    chi=int(len(x)-len(count)+len(t))
    passed=bool(np.isfinite(x).all() and np.all(count==2) and np.all(orient==0) and chi==2 and areas.min()>0)
    result=dict(passed=passed,vertices=len(x),triangles=len(t),Euler=chi,closed_two_face_edges=bool(np.all(count==2)),
        consistent_orientation=bool(np.all(orient==0)),minimum_triangle_area=float(areas.min()),
        apparent_holes='Topological genus zero required; closed backing on each folded sheet.',
        self_intersections_certified=False,fabrication_certified=False)
    if not passed:raise ValueError('Actual macro geometry integrity failed: '+repr(result))
    return result


def save_surface(folder,x,t,extra=None):
    folder.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(folder/'geometry.npz',xyz=x,faces=t)
    write(folder/'GEOMETRY_QA.json',quality(x,t))
    if extra:
        for name,value in extra.items():np.save(folder/(name+'.npy'),value)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--module',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cc-passes',type=int,default=2)
    p.add_argument('--id',required=True)
    p.add_argument('--dependency',type=Path,action='append',default=[])
    a=p.parse_args()
    if a.cc_passes!=2:raise ValueError('This bounded study uses exactly two actual CC descendants.')
    source=HERE/(a.module+'.py')
    if a.output.exists():raise FileExistsError('Preserve earlier prototype.')
    source_paths=[source,HERE/'grammar_kernel.py',Path(__file__),HERE.parents[1]/'src/cheshire/reference_subdivision.py']+a.dependency
    bindings={str(f):sha(f) for f in source_paths}
    mod=importlib.util.spec_from_file_location('actual_grammar',source)
    g=importlib.util.module_from_spec(mod);sys.modules[mod.name]=g;mod.loader.exec_module(g)
    started=time.perf_counter()
    parts,meta=g.build_components()
    meta=dict(meta,id=a.id)
    a.output.mkdir(parents=True)
    snaps=a.output/'source_snapshot';snaps.mkdir()
    for f in source_paths:shutil.copyfile(f,snaps/f.name)
    component_rows=[]
    for i,part in enumerate(parts):
        dest=a.output/'components'/f'{i:03d}'
        dest.mkdir(parents=True)
        np.savez_compressed(dest/'geometry.npz',xyz=part['xyz'],faces=part['faces'])
        component_rows.append(dict(index=i,name=part['name'],role=part.get('role','macro'),level=part.get('level',0),
            geometry=str(dest/'geometry.npz'),sha256=sha(dest/'geometry.npz'),triangles=len(part['faces'])))
    write(a.output/'DESIGN.json',dict(metadata=meta,components=component_rows))
    x,t,tags,csg=k.union_components(parts)
    q0=quality(x,t)
    save_surface(a.output/'G00_CSG',x,t,dict(triangle_parts=tags))
    write(a.output/'G00_CSG/CSG_RECEIPT.json',csg)
    mesh,nx,nt,parent,stages=k.real_subdivide(x,t,2)
    dest=a.output/'G02_CC'
    native_parts=np.repeat(tags[parent],4)
    save_surface(dest,nx,nt,dict(parent_CSG_face=parent,native_part_ids=native_parts))
    np.savez_compressed(dest/'control_quad.npz',xyz=mesh.xyz,faces=mesh.faces,
        classes=mesh.classes,rest=mesh.rest,anchors=mesh.anchors,generation=np.array(mesh.generation),surface=np.array('mean'))
    for s in stages:
        pf=s.pop('actual_parent_face')
        np.save(a.output/(f'G{s["generation"]:02d}_actual_parent_face.npy'),pf)
    palette=[dict(name=row['name'],rgb=list((.04,.43,.75) if row['level']==0 else
        (.91,.35,.055) if row['level']==1 else (.01,.63,.48) if row['level']==2 else (.59,.17,.46))) for row in component_rows]
    write(a.output/'COLOR_LEGEND.json',dict(palette=palette,
        meaning='Actual source components of the solid Boolean union, inherited through both recorded Catmull-Clark parent-face arrays. Color does not estimate curvature or deformation strength.'))
    for f,digest in bindings.items():
        if sha(f)!=digest:raise ValueError('Executed source changed during prototype build.')
    receipt=dict(schema='CHESHIRE_NEW_STRUCTURAL_GRAMMAR_V1',status='PASS',id=meta['id'],design=meta,
        source_bindings=bindings,components=component_rows,actual_CSG=csg,actual_G00_QA=q0,
        subdivision_stages=stages,final_geometry=str(dest/'geometry.npz'),final_geometry_sha256=sha(dest/'geometry.npz'),
        final_controls=str(dest/'control_quad.npz'),final_controls_sha256=sha(dest/'control_quad.npz'),
        final_QA=quality(nx,nt),actual_native_color_tags=str(dest/'native_part_ids.npy'),
        color_tags_sha256=sha(dest/'native_part_ids.npy'),old_column_geometry_read=False,
        late_ornament_added=False,visual_success='NOT_ASSESSED',user_adopted=False,
        fabrication_certified=False,elapsed_seconds=time.perf_counter()-started)
    write(a.output/'RECEIPT.json',receipt)
    print('NEW_STRUCTURAL_GRAMMAR_READY',meta['id'],len(nx),len(nt),receipt['elapsed_seconds'],flush=True)


if __name__=='__main__':main()
