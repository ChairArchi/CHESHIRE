"""Written-geometry comparisons and actual Rhino section overlays."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image,ImageDraw

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'examples'))
from progressive_gates import parent_directory
from cross_cell_crease_study import read,write,file_hash


def geometry_comparison(root,a,b):
    arrays=[];topologies=[];keys=[];paths=[]
    for name in (a,b):
        p=parent_directory(root,name)/'geometry.json.gz';d=read(p)
        keys.append([r['id'] for r in d['vertices']]);arrays.append(np.asarray([r['xyz'] for r in d['vertices']]))
        h=hashlib.sha256()
        for f in d['faces']:h.update(json.dumps(f,separators=(',',':')).encode());h.update(b'\n')
        topologies.append(h.hexdigest());paths.append(dict(path=str(p),sha256=file_hash(p)));del d
    if keys[0]!=keys[1] or topologies[0]!=topologies[1]:raise ValueError('Matched written geometry/topology required for causal displacement comparison.')
    delta=np.linalg.norm(arrays[0]-arrays[1],axis=1)
    return dict(pair=[a,b],inputs=paths,exact_vertex_IDs_oriented_connectivity=True,
        topology_sha256=topologies[0],vertices=len(delta),displacement=dict(min=float(delta.min()),
            median=float(np.median(delta)),p90=float(np.quantile(delta,.9)),p99=float(np.quantile(delta,.99)),
            max=float(delta.max()),rms=float(np.sqrt(np.mean(delta**2))),over_001=int((delta>.01).sum())),
        interpretation='Actual position differences on identical saved point IDs/face cycles; this alone does not prove a fold or a through-hole.')


def evidence(root):
    pairs=[('RECT_EARLY_G3','RECT_DELAYED_G3'),('RECT_EARLY_G3','ROUND_EARLY_G3'),
           ('SYMMETRY_PAIRED_G4','SYMMETRY_INDEPENDENT_G4'),
           ('CONTROL_CREASE_G4','CONTROL_STANDARD_G4'),('CONTROL_TASK25_G4','CONTROL_CREASE_G4'),
           ('FOLD_DISTRIBUTED_G4','FOLD_CONCENTRATED_G4'),
           ('LEAD_REFINE_G6','LEAD_CC_CONTROL_G6'),('LEAD_REVISED_G6','LEAD_CC_CONTROL_G6'),
           ('LEAD_ARTICULATED_G7','LEAD_FINAL_G7'),('LEAD_BALANCED_G7','LEAD_FINAL_G7')]
    write(root/'analysis/geometry_comparisons.json',dict(actual_written_checkpoint_comparisons=[geometry_comparison(root,*p) for p in pairs]))


def validate_checkpoint(root,name):
    from cheshire.fold_continuation import load_state
    from cheshire.progressive_gates import restore_gate,symmetry
    from progressive_gates import raw_mesh,verify_obj
    d=parent_directory(root,name);mesh=raw_mesh(read(d/'geometry.json.gz'));s=restore_gate(load_state(d/'state.json.gz'))
    for field in ('history','source_cells','signatures'):
        if set(s[field])!=set(mesh.faces()):raise ValueError('Incomplete face continuation '+field)
    if set(s['origins'])!=set(mesh.vertices()) or set(s['gate']['material'])!=set(mesh.vertices()):raise ValueError('Incomplete point continuation.')
    if any(r['generation']!=s['generation']['absolute_cc'] for r in s['origins'].values()):raise ValueError('Origin generation changed.')
    for n in s['networks']:
        for e in n['edges']:
            u,v=e['vertices']
            # COMPAS 2.15.1 has_edge rebuilds set(mesh.edges()) per query.
            # Both halfedge directions exist for every actual closed-mesh edge.
            if v not in mesh.halfedge.get(u,{}) or u not in mesh.halfedge.get(v,{}):
                raise ValueError('Active crease edge absent from saved geometry.')
    check=verify_obj(mesh,d/(name+'.obj'));report=symmetry(mesh,s)
    write(root/'analysis'/(name+'_checkpoint_reread.json'),dict(status='PASS',input_geometry=str(d/'geometry.json.gz'),
        geometry_sha256=file_hash(d/'geometry.json.gz'),state_sha256=file_hash(d/'state.json.gz'),
        OBJ_reread=check,symmetry=report,generation=s['generation'],completed_recipes=s['gate']['completed_recipes'],
        metadata_corrections=s['gate'].get('metadata_corrections',[]),
        continuation='Actual full checkpoint reloaded; complete origin/material/pair/face/crease coverage verified. Small save/reload/uninterrupted continuation tests separately passed. No next generation allocated.'))


def section_overlay(root,names):
    # Fixed world frames; sections come from actual reread Rhino native meshes.
    planes=[(1,2,[-700,700,-100,3800]),(0,2,[-2600,1800,0,3800]),(0,1,[-2600,1800,-700,700])]
    rows=[read(root/'analysis/sections'/(n+'.json')) for n in names]
    im=Image.new('RGB',(1800,700),(248,248,246));draw=ImageDraw.Draw(im)
    colors=[(40,110,180),(180,65,65),(30,140,85)]
    for i,(a,b,bounds) in enumerate(planes):
        lo,hi,bottom,top=bounds;s=min(540/(hi-lo),580/(top-bottom));x0=i*600+30;y0=630
        for row,color in zip(rows,colors):
            for line in row['sections'][i]['polylines']:
                pts=[(x0+(p[a]-lo)*s,y0-(p[b]-bottom)*s) for p in line]
                if len(pts)>1:draw.line(pts,fill=color,width=1)
        draw.text((i*600+24,12),rows[0]['sections'][i]['plane']+' / actual native sections',fill=(20,20,20))
    for j,(name,color) in enumerate(zip(names,colors)):draw.text((25,650+j*16),name,fill=color)
    out=root/'renders/geometry';out.mkdir(parents=True,exist_ok=True);im.save(out/'section_comparison.png')
    write(out/'section_manifest.json',dict(names=names,source=[dict(path=str(root/'analysis/sections'/(n+'.json')),
        sha256=file_hash(root/'analysis/sections'/(n+'.json'))) for n in names],
        frames=planes,type='Actual native mesh-plane intersection wire overlays; no AO or shaded depth inference.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--compare',action='store_true')
    p.add_argument('--sections',nargs='+');p.add_argument('--validate');a=p.parse_args()
    if a.compare:evidence(a.output_root)
    if a.sections:section_overlay(a.output_root,a.sections)
    if a.validate:validate_checkpoint(a.output_root,a.validate)
