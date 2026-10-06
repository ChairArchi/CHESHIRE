"""Task-21 actual fixed views, coherent patch evidence and result tables."""
import argparse
import csv
import gzip
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from subdivision_capability_study import read,write

STUDY=ROOT/'output/task21/study'
ROLES={'FRAME_SIDE':1,'INNER_CAP':2,'EXTRUSION_SIDE':3,'EXTRUSION_CAP':4,
    'DIRECTIONAL_EXTRUSION_SIDE':5,'DIRECTIONAL_EXTRUSION_CAP':6,'RIDGE_SIDE':7,'RIDGE_END':8}

def gz_read(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream: return __import__('json').load(stream)

def cases(phase):
    result=[]
    for root in sorted((STUDY/phase).glob('*')):
        attempts=sorted(p for p in root.glob('attempt_*') if (p/'summary.json').exists() and read(p/'summary.json')['status']!='RUNNING' and read(p/'summary.json').get('process'))
        good=[p for p in attempts if read(p/'summary.json').get('technically_valid')]
        if good or attempts: result.append((good or attempts)[-1])
    return result

def views(phase,details=True):
    camera=read(ROOT/'studies/task19/camera.json')['bounds']; folder=STUDY/'views'/phase
    folder.mkdir(parents=True,exist_ok=True); frames=[]; tables=[]
    for case in cases(phase):
        s=read(case/'summary.json'); name=case.parent.name
        if not (case/'terminal.json').exists() or not s.get('stages'): continue
        last=s['stages'][-1]; stats=s['terminal_statistics']; diagnostics=last['diagnostics']
        branches=read(case/'branch_signatures.json'); crossing=read(case/'terminal_crossings.json')
        routing=gz_read(case/'branch_tables.json.gz')
        patches=[p for t in routing.values() for r in t['rules'] for p in r.get('patches',[])]
        verified=read(case/'verification.json') if (case/'verification.json').exists() else {}
        row=dict(id=name,family=s['recipe']['family'],reference=s['recipe']['reference_id'],status=s['status'],technically_valid=s['technically_valid'],
            completed_stage=last['stage']['id'],stop_reason=s['reason'],vertices=stats['vertex_count'],edges=stats['edge_count'],faces=stats['face_count'],
            manifold=stats['is_manifold'],closed=stats['is_closed'],boundary_edges=stats['boundary_edge_count'],components=diagnostics['components'],
            degenerate_faces=len(diagnostics['degenerate_fan_faces']),fan_warnings=len(diagnostics['opposed_fan_normals']),bilinear_warnings=len(diagnostics['bilinear_admissibility_warning_faces']),
            sampled_crossings=crossing['sampled_transverse_crossings'],contact_state='UNSTABLE' if crossing['sample_limit_reached'] else 'LOW_CONTACT' if crossing['sampled_transverse_crossings'] else 'CLEAN_SAMPLE',
            known_backbone_contacts_retained=verified.get('known_backbone_contact_pairs_retained_unchanged'),ornament_depth=branches['maximum_branch_depth'],
            signatures=branches['unique_branch_signatures'],signature_dominance=branches['dominant_signature_fraction'],nested_components=branches['independent_nested_event_components'],
            routing_patches=len(patches),multi_face_patches=sum(p['face_count']>1 for p in patches),largest_patch=max((p['face_count'] for p in patches),default=0),
            patches_spanning_parent_cells=sum(p['matching_parent_cell_count']>1 for p in patches) if all('matching_parent_cell_count' in p for p in patches) else None,
            patches_spanning_roots=sum(p['root_event_count']>1 for p in patches) if all('root_event_count' in p for p in patches) else None,
            runtime_seconds=s['runtime_seconds'],peak_resident_bytes=s['process']['peak_process_tree_plus_driver_bytes'])
        tables.append(row)
        modes=['front','oblique']+(['detail'] if details else [])
        if phase not in ('A','B','C'): modes+=['wire','roles','signatures','patches','depth']
        for view in modes:
            frame=dict(mesh=str(case.relative_to(STUDY)/'terminal.json'),file=f'views/{phase}/{name}_{view}.png',
                label=f'{name} / {row["status"]} / F={row["faces"]} / {row["contact_state"]}',
                camera='front' if view=='front' else 'oblique',bounds=camera[view if view in camera else 'detail'],width=900,height=900,wireframe=view=='wire')
            if view in ('roles','signatures','patches','depth'):
                signatures=gz_read(case/'terminal_signatures.json.gz'); paths=signatures['paths']; lineage=gz_read(case/'terminal_lineage.json.gz')
                if view=='depth': colors={f:r['depth'] for f,r in lineage['history'].items()}; legend='CONSTRUCTIVE EVENT DEPTH; subdivision adds no depth'
                elif view=='roles':
                    colors={}
                    for f,rows in signatures['faces'].items():
                        roles={paths[i][-1].split(':')[1] if paths[i] else 'SOURCE' for i,w in rows if w>0}
                        colors[f]=ROLES.get(next(iter(roles)),0) if len(roles)==1 else -1
                    legend='ROLE: frame blue / inner orange / taper purple-green / directional cyan-red / ridge gold-violet / mixed dark'
                elif view=='signatures':
                    colors={f:(rows[0][0]+12 if len(rows)==1 and paths[rows[0][0]] else 0 if len(rows)==1 else -1) for f,rows in signatures['faces'].items()}
                    legend='POSITIVE BRANCH PATH: stable index color / gray source / dark mixed; not a visual score'
                else:
                    events={e['id']:e for e in lineage['events']}; all_ids=sorted({e['stage']+':'+e['routing_patch']['id'] for e in events.values() if e.get('routing_patch',{}).get('id')})
                    ids={p:i+12 for i,p in enumerate(all_ids)}; colors={}
                    for f,r in lineage['history'].items():
                        related=[events[e] for e in r['events'] if events[e].get('routing_patch',{}).get('id')]
                        maxdepth=max((e['ornament_depth'] for e in related),default=0)
                        patches={e['stage']+':'+e['routing_patch']['id'] for e in related if e['ornament_depth']==maxdepth}
                        colors[f]=ids[next(iter(patches))] if len(patches)==1 else -1 if patches else 0
                    legend='LATEST NEW-EVENT ROUTING PATCH: stable ID color / gray uncoordinated / dark mixed'
                    write(folder/(name+'_patch_ids.json'),ids)
                path=folder/(name+'_'+view+'.json'); write(path,colors); frame['depthfile']=str(path.relative_to(STUDY)); frame['legend']=legend
            frames.append(frame)
    sheets=[]
    for view in ('oblique','detail'):
        for family in sorted({r['family'] for r in tables}):
            names={r['id'] for r in tables if r['family']==family}
            images=[f['file'] for f in frames if Path(f['file']).stem.removesuffix('_'+view) in names and f['file'].endswith('_'+view+'.png')]
            if images: sheets.append(dict(file=f'views/{phase}/{family}_{view}_sheet.png',title=f'Task21 {phase} {family}; fixed actual polygon comparisons',images=images,columns=3,width=900,height=900))
    write(STUDY/(phase+'_projection_plan.json'),dict(frames=frames,sheets=sheets)); write(STUDY/(phase+'_table.json'),tables)
    if tables:
        with (STUDY/(phase+'_table.csv')).open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(tables[0])); writer.writeheader(); writer.writerows(tables)
    print(phase,len(tables),'cases',len(frames),'views',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('phase'); parser.add_argument('--whole-only',action='store_true')
    args=parser.parse_args(); views(args.phase,not args.whole_only)
