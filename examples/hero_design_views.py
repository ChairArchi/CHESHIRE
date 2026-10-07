"""Task24 camera plans for the existing polygon projection route.

Evidence is read from actual on-disk OBJ exports, never from invented geometry.
Rotations are display-only orthonormal camera coordinates; model exports retain
their original origin, coordinates, scale, connectivity and orientation.
"""
import argparse
from math import sin, cos, radians
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from cross_cell_crease_study import read,write,mesh_to_data,file_hash
from cheshire import load_mesh


def latest(root,name):
    rows=sorted((root/'designs'/name).glob('attempt_*'))
    good=[p for p in rows if (p/(name+'.obj')).exists()]
    if not good:raise ValueError('No exported real mesh: '+name)
    return good[-1]


def matrix(azimuth,elevation=0):
    t=radians(azimuth);p=radians(elevation)
    return [[cos(t),sin(t),0.],[-sin(t)*cos(p),cos(t)*cos(p),-sin(p)],
        [-sin(t)*sin(p),cos(t)*sin(p),cos(p)]]


def rotated(geometry,m):
    return dict(vertices=[dict(id=v['id'],xyz=[sum(a*b for a,b in zip(row,v['xyz'])) for row in m])
        for v in geometry['vertices']],faces=geometry['faces'])


def bounds(geometry):
    xx=[v['xyz'][0] for v in geometry['vertices']];zz=[v['xyz'][2] for v in geometry['vertices']]
    return [min(xx),max(xx),min(zz),max(zz)]


def square(b,padding=.10):
    x=(b[0]+b[1])/2;z=(b[2]+b[3])/2
    half=max(b[1]-b[0],b[3]-b[2])*(.5+padding)
    return [x-half,x+half,z-half,z+half]


def subtree_detail(directory,geometry,m):
    """Fit one real nested frame subtree, using its saved construction history."""
    original=read(directory/'terminal.json.gz')
    lineage=read(directory/'terminal_lineage.json.gz')
    event_rows=[e for e in lineage['events'] if e['stage'].endswith('_frame')
        and not e['stage'].endswith('_fine_frame') and e['stage']!='event_2']
    completed_ancestors={ancestor for e in lineage['events'] if e['stage'].endswith('_fine_cap')
        for ancestor in e['parent_event_ids']}
    completed=[e for e in event_rows if e['id'] in completed_ancestors]
    if completed:event_rows=completed
    vertex_map={v['id']:v for v in geometry['vertices']}
    choices=[]
    # OBJ and Rhino reorder keys, but preserve ordered vertex/face arrays.
    for e in event_rows:
        selected=[geometry['faces'][i] for i,f in enumerate(original['faces'])
            if e['id'] in lineage['history'][str(f['id'])]['events']]
        ids={v for f in selected for v in f['vertices']}
        if not ids:continue
        subset=dict(vertices=[vertex_map[v] for v in sorted(ids)],faces=selected)
        projected=rotated(subset,m);b=bounds(projected)
        size=max(b[1]-b[0],b[3]-b[2])
        depth=sum(v['xyz'][1] for v in projected['vertices'])/len(ids)
        choices.append((size,-depth,e['id'],b,projected))
    if not choices:return None
    # Largest actual nested subtree: technical framing, not a beauty score.
    _,_,event_id,b,projected=max(choices,key=lambda r:r[:3])
    return square(b,.35),event_id,projected


def prepare(root,names,tag='final',rhino=False):
    out=root/'renders'/tag;out.mkdir(parents=True,exist_ok=True)
    cameras=dict(front=matrix(0),oblique=matrix(32,16),side=matrix(90),rear=matrix(180))
    limits={v:[] for v in cameras};details={};records=[]
    for name in names:
        d=latest(root,name);obj=d/(name+'.obj')
        geometry=mesh_to_data(load_mesh(obj))
        if rhino:geometry=read(root/'dcc'/(name+'_reimport.json'))
        for view,m in cameras.items():
            g=rotated(geometry,m);path=out/(name+'_'+view+'.json');write(path,g)
            b=bounds(g);limits[view].append((name,b))
            if view=='oblique':
                # Deliberate architectural shoulder crop at a declared relative
                # position. Same fraction of fitted whole extent for each Hero.
                w=b[1]-b[0];h=b[3]-b[2];size=max(w,h)*.32
                cx=b[0]+w*.27;cz=b[2]+h*.79
                details[name]=[cx-size/2,cx+size/2,cz-size/2,cz+size/2]
                nested=subtree_detail(d,geometry,m)
                if nested:
                    details[name]=nested[0]
                    write(out/(name+'_subtree.json'),nested[2])
                    records.append(dict(id=name,view='detail',construction_event=nested[1],
                        bounds=nested[0],camera_matrix=m,
                        framing='Fitted saved frame subtree with a completed fine-cap chain when available; largest actual projected child extent.',
                        isolated_diagram=dict(file=name+'_subtree.json',faces=[f['id'] for f in nested[2]['faces']],
                            processing='Display-only isolation of actual tagged descendant faces; no XYZ changes. Full-context detail is supplied separately.')))
            records.append(dict(id=name,view=view,input=str(obj),input_sha256=file_hash(obj),
                camera_matrix=m,projection='Orthographic onto transformed XZ; depth=-transformed Y.',
                processing='Camera coordinate rotation only; no displacement, smoothing, clipping, decimation or per-Hero material.',
                evidence='Actual RhinoCommon .3dm reimport' if rhino else 'Actual OBJ reimport'))
    frames=[];sheets=[]
    for view,rows in limits.items():
        merged=[min(b[0] for _,b in rows),max(b[1] for _,b in rows),min(b[2] for _,b in rows),max(b[3] for _,b in rows)]
        common=square(merged)
        for name,b in rows:
            for framing,bound in [('common',common),('fit',square(b))]:
                frames.append(dict(mesh=name+'_'+view+'.json',file=name+'_'+view+'_'+framing+'.png',
                    label=name+' / '+view+' / '+framing+(' / System.Drawing 3DM preview' if rhino else ''),
                    camera='front',width=700,height=700,bounds=bound))
        sheets.append(dict(file='comparison_'+view+'.png',title='Task24 / '+view+' / COMMON MODEL SCALE',
            images=[n+'_'+view+'_common.png' for n in names],width=700,height=700,columns=len(names)))
    for name in names:
        frames.append(dict(mesh=name+'_oblique.json',file=name+'_detail.png',label=name+' / actual nested subtree / fitted detail',
            camera='front',width=700,height=700,bounds=details[name]))
        if (out/(name+'_subtree.json')).exists():
            frames.append(dict(mesh=name+'_subtree.json',file=name+'_subtree_detail.png',
                label=name+' / ISOLATED actual descendants / context hidden',camera='front',
                width=700,height=700,bounds=details[name]))
        sheets.append(dict(file=name+'_multiview.png',title='Task24 / '+name+' / fitted views + detail',
            images=[name+'_'+v+'_fit.png' for v in cameras]+[name+'_detail.png']+
                ([name+'_subtree_detail.png'] if (out/(name+'_subtree.json')).exists() else []),
            width=700,height=700,columns=3))
    sheets.append(dict(file='comparison_fitted.png',title='Task24 / FITTED oblique views / scales differ, use common comparison for size',
        images=[n+'_oblique_fit.png' for n in names],width=700,height=700,columns=len(names)))
    write(out/'projection_plan.json',dict(frames=frames,sheets=sheets))
    write(out/'camera_manifest.json',dict(records=records,frames=frames,
        lighting='Existing tools/crease_projection.ps1 neutral gray first-triangle normal shading; camera-coordinate light (.3,-.8,.5), identical across Heroes.',
        limitation='Existing headless painter projection, no ray tracing or pixel z-buffer. Interpenetrating polygon occlusion is approximate. These are clay previews, not Rhino viewport captures or beauty renders.',
        renderer_sha256=file_hash(ROOT/'tools/crease_projection.ps1')))
    return out/'projection_plan.json'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--names',nargs='+',default=['H1','H2','H3']);p.add_argument('--tag',default='final')
    p.add_argument('--rhino',action='store_true');a=p.parse_args()
    plan=prepare(a.output_root,a.names,a.tag,a.rhino)
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'tools/crease_projection.ps1'),'-PlanPath',str(plan)],check=True)
