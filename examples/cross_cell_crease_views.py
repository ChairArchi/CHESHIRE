"""Registered evidence from actual Task23 polygons and declared graph edges."""
import argparse
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'examples'))
from cross_cell_crease_study import read, write, raw_mesh, digest, file_hash, bounded_worker
from cross_cell_crease_diagnostics import annotated_views


def best_attempt(root, phase, name):
    attempts = sorted((root/'study'/phase/name).glob('attempt_*'))
    valid = [p for p in attempts if (p/'summary.json').exists() and read(p/'summary.json')['stages']
        and ((p/'terminal.json').exists() or read(p/'summary.json')['status']=='CANCELLED_POLICY_OVERRIDE')]
    if not valid: raise ValueError('No retained real checkpoint: '+name)
    return valid[-1]


def prepare(root, phase, names, expanded=False, ends_only=False):
    cameras = read(ROOT/'studies/task21/camera.json')['bounds']
    source=read(root/'inputs/C0.json')['vertices']
    xmin=min(v['xyz'][0] for v in source);xmax=max(v['xyz'][0] for v in source)
    zmin=min(v['xyz'][2] for v in source);zmax=max(v['xyz'][2] for v in source)
    width=xmax-xmin;height=zmax-zmin;center=(xmin+xmax)/2
    node=[center-.51*width,center-.21*width,zmin+.80*height,zmin+1.15*height]
    write(root/'study/task23_camera.json',dict(whole_and_legacy_detail=cameras,left_shoulder_node=node,
        contract='One additional crop derived only from original C0 dimensions; identical across all gate candidates, no per-case fitting. Whole-gate assessment remains mandatory.'))
    output = root/'renders'/phase; output.mkdir(parents=True, exist_ok=True)
    frames = []; sheets = []; records = []
    for name in names:
        directory = best_attempt(root, phase, name); summary = read(directory/'summary.json')
        terminal = summary['stages'][-1]['stage']
        initial=summary['stages'][0]['stage']
        stages = [initial, terminal] if terminal != initial else [initial]
        if expanded and not ends_only: stages = [r['stage'] for r in summary['stages']]
        for stage in stages:
            key = name+'_'+stage
            geometry = read(directory/(stage+'.json.gz')); networks = read(directory/(stage+'_networks.json'))
            mesh_path = output/(key+'.json'); write(mesh_path, geometry)
            edges = []; junctions = set(); directions = []
            for i, n in enumerate(networks, 1):
                edges.extend(dict(vertices=e['vertices'], sharpness=e['sharpness'], code=i) for e in n['edges'])
                junctions.update(n['junction_vertices'])
                if stage == 'G0':
                    for path in n['routing']['paths']:
                        directions.extend([path[j:j+2] for j in range(0, len(path)-1, max(1, len(path)//5))])
            overlay = dict(edges=edges, junctions=sorted(junctions), directions=directions,
                legend='DECLARED graph overlay incl. hidden edges; dots junctions / arrows seed direction')
            write(output/(key+'_edges.json'), overlay)
            if expanded:
                annotated_views(directory, geometry, networks, output, key, stage == 'G0')
            control = name.startswith('CTRL_') and 'U_gate' not in name
            bounds = {c: [-2.2, 2.2, -3.8, 3.8] for c in ('front', 'oblique', 'detail','node')} if control else dict(cameras,node=node)
            views = ['front', 'oblique'] + (['detail', 'node','wire'] if expanded else [])
            for view in views:
                camera = 'oblique' if view == 'oblique' else 'front'; bound = bounds[view if view in ('detail','node') else camera]
                frame = dict(mesh=mesh_path.name, file=key+'_'+view+'.png', label=key+' / '+view,
                    camera=camera, width=600, height=600, bounds=bound, wireframe=view == 'wire')
                frames.append(frame)
                if view in ('front', 'oblique'):
                    frames.append(dict(frame, file=key+'_'+view+'_network.png', edgefile=key+'_edges.json', label=key+' / declared route'))
            if expanded:
                common=dict(mesh=mesh_path.name,camera='front',width=600,height=600,bounds=bounds['front'])
                for kind in ('sharpness','high'):
                    frames.append(dict(common,file=key+'_'+kind+'.png',edgefile=key+'_'+kind+'.json',label=key+' / '+kind))
                for kind in ('ancestry','depth'):
                    frames.append(dict(common,file=key+'_'+kind+'.png',depthfile=key+'_'+kind+'.json',label=key+' / '+kind,
                        legend='Actual positive C0 face ancestry' if kind == 'ancestry' else 'Actual constructive nested ornament depth'))
                if stage == 'G0':
                    frames.append(dict(common,file=key+'_cell_boundaries.png',edgefile=key+'_cell_boundaries.json',label=key+' / frozen parent cells'))
            records.append(dict(case=name, stage=stage, input=directory.relative_to(root).as_posix(),
                geometry_sha256=digest(geometry), camera_identity='Task21 frozen cameras; per-fixture constant control framing'))
        sheets.append(dict(file=name+'_comparison.png', title=name+' / actual geometry before -> after, gray and declared path',
            images=[name+'_'+s+'_'+v+'.png' for s in stages for v in ('front','front_network','oblique','oblique_network')],
            width=600, height=600, columns=4))
    old=read(output/'view_records.json') if (output/'view_records.json').exists() else []
    latest={(r['case'],r['stage']):r for r in old}
    for r in records:
        r['projection_source_sha256']=file_hash(ROOT/'tools/crease_projection.ps1')
        latest[(r['case'],r['stage'])]=r
    write(output/'projection_plan.json', dict(frames=frames, sheets=sheets)); write(output/'view_records.json', list(latest.values()))
    return output/'projection_plan.json'


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output-root', type=Path, required=True)
    p.add_argument('--phase', required=True); p.add_argument('--run', nargs='+', required=True); p.add_argument('--expanded', action='store_true')
    p.add_argument('--worker',action='store_true')
    p.add_argument('--ends-only',action='store_true')
    a = p.parse_args()
    if a.worker:
        plan = prepare(a.output_root, a.phase, a.run, a.expanded,a.ends_only)
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'tools/crease_projection.ps1'),'-PlanPath',str(plan)], check=True)
    else:
        for i in range(0,len(a.run),3):
            names=a.run[i:i+3]
            command=[Path(__file__).resolve(),'--worker','--output-root',a.output_root,'--phase',a.phase,'--run',*names]
            if a.expanded: command+=['--expanded']
            if a.ends_only: command+=['--ends-only']
            logs=a.output_root/'logs'/'views'/a.phase/('_'.join(names)+('_expanded' if a.expanded else ''))
            process=bounded_worker(command,logs,900);write(logs/'process.json',process)
            print('VIEWS',names,process['exit_code'],round(process['seconds'],2),flush=True)
            if process['exit_code']:raise ValueError('Guarded evidence generation failed; see retained logs.')
