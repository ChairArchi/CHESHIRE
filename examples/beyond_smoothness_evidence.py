"""Compact first-party evidence export; raw geometry stays outside Git."""
import argparse
from collections import Counter
import csv
import hashlib
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
for f in ('rhino','examples','tools'): sys.path.insert(0,str(ROOT/f))
from cheshire.artifact_root import ArtifactRoot
from beyond_smoothness_verify import read,write
from beyond_smoothness_study import versions
from ornament_study import file_hash,digest

def reference_worker(root,label):
    from cheshire import inspect_mesh,save_mesh
    from cheshire_worker import mesh_from_data
    from cheshire.ornament import source_history
    from cheshire.gate_integrity import GateIntegrityMonitor
    from beyond_smoothness_study import crossing,restore_history
    from beyond_smoothness_diagnostics import observe,geometry_state
    from time import perf_counter
    started=perf_counter(); name={'C0':'C0.json','C07':'BACKBONE_S05.json.gz','ORDERED':'TASK21_ORDERED.json'}[label]
    geometry=read(root.resolve('inputs/'+name)); mesh=mesh_from_data(geometry)
    directory=root.resolve('study/REFERENCE/REF_'+label+'/attempt_001'); directory.mkdir(parents=True,exist_ok=True)
    if label=='C0': history=source_history(mesh); cells={f:[f] for f in mesh.faces()}
    else:
        history=restore_history(read(root.resolve('inputs/'+('BACKBONE_S05_lineage.json.gz' if label=='C07' else 'TASK21_ORDERED_lineage.json.gz')))['history'])
        cells={f:[f] for f in mesh_from_data(read(root.resolve('inputs/BACKBONE_S05.json.gz'))).faces()}
        if label=='ORDERED':
            for i in range(6,13):
                parents=read(root.resolve(f'inputs/ORDERED_S{i:02d}_lineage.json.gz'))['face_parents']
                cells={int(f):sorted({c for p in refs for c in cells[p['id']]}) for f,refs in parents.items()}
    d=observe(mesh,cells,source_history=history)
    source=read(root.resolve('inputs/'+('C0.json' if label=='C0' else 'BACKBONE_S05.json.gz' if label=='C07' else 'ORDERED_CORE.json.gz')))
    audit=crossing(root,directory/'audit_reference',geometry,label,source)
    write(directory/'terminal.json',geometry); save_mesh(mesh,directory/'terminal.obj')
    c0=mesh_from_data(read(root.resolve('inputs/C0.json')))
    anchors={v:v for v in c0.vertices()} if label=='C0' else {int(v):p for v,p in read(root.resolve('inputs/'+('C07' if label=='C07' else 'TASK21_ORDERED')+'_anchors.json')).items()}
    monitor=GateIntegrityMonitor(c0).evaluate(mesh,anchors,generation={'C0':0,'C07':5,'ORDERED':12}[label])
    row=dict(stage='REFERENCE',statistics=inspect_mesh(mesh),diagnostics=d,crossings=audit,metadata={},
        geometry_state=geometry_state(d,audit),geometry_sha256=digest(geometry),monitor=monitor)
    write(directory/'summary.json',dict(status='SUCCESS',reason='Frozen actual reference, no transform',geometry_state=row['geometry_state'],
        recipe=dict(input='C0' if label=='C0' else 'C07' if label=='C07' else 'ORDERED_CORE',family='REFERENCE'),
        stages=[row],terminal_statistics=inspect_mesh(mesh),output_sha256=digest(geometry),runtime_seconds=perf_counter()-started))
    print(label,row['geometry_state'],audit['sampled_transverse_crossings'],flush=True)

def references(root):
    from branching_process import bounded_worker
    for label in ('C0','C07','ORDERED'):
        process=bounded_worker([Path(__file__).resolve(),'--output-root',root.path,'--reference-worker',label],root.resolve('logs/REFERENCE/'+label),900)
        write(root.resolve('logs/REFERENCE/'+label+'/process.json'),process)
        if process['exit_code']: raise ValueError('Reference diagnostic failed: '+label)

def snapshot(root):
    actual=versions()['source_files']; contents={}
    for name,sha in actual.items(): contents[(name,sha)]=(ROOT/name).read_bytes()
    driver=(ROOT/'examples/beyond_smoothness_study.py').read_text(encoding='utf-8')
    if '\ndef can_resume(' in driver:
        a=driver.index('\ndef can_resume('); b=driver.index('\ndef one(')
        previous=(driver[:a]+driver[b:]).replace('any(can_resume(p,request)','any(verified_resume(p,request)')
        raw=previous.encode(); contents[('examples/beyond_smoothness_study.py',hashlib.sha256(raw).hexdigest())]=raw
    coverage=[]
    for name,sha in sorted(contents):
        target=root.resolve('cache/source_snapshots/'+sha+'/'+Path(name).name)
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists(): target.write_bytes(contents[(name,sha)])
        assert file_hash(target)==sha
        coverage.append(dict(repository_file=name,sha256=sha,artifact=root.reference(target)))
    previous=root.resolve('study/source_snapshots.json')
    if previous.exists(): coverage=read(previous)+[r for r in coverage if r not in read(previous)]
    write(previous,coverage); print('Pinned',len(coverage),'first-party source snapshots.')

def cases(root,phases):
    result=[]
    for phase in phases:
        directory=root.resolve('study/'+phase)
        if not directory.exists(): continue
        for case in sorted(directory.iterdir()):
            attempts=sorted(case.glob('attempt_*/summary.json'))
            if not attempts: continue
            path=attempts[-1]; data=read(path); rows=[]
            for stage in data.get('stages',[]):
                d=stage['diagnostics']; metadata=stage.get('metadata',{})
                cross=d['cross_cell_sharp_components']
                rows.append(dict(stage=stage['stage'],statistics=stage['statistics'],geometry_state=stage['geometry_state'],
                    geometry_sha256=stage['geometry_sha256'],dihedral_degrees=d['dihedral_degrees'],
                    high_dihedral_edge_fraction=d['high_dihedral_edge_fraction'],normal_variation=d['local_normal_variation'],
                    distributions=d['distributions'],motif_histogram=d['motif_histogram'],components=d['components'],
                    fan_warnings=len(d['opposed_fan_normals']),bilinear_warnings=len(d['bilinear_admissibility_warning_faces']),
                    degenerate_faces=len(d['degenerate_fan_faces']),crossings=stage['crossings'],
                    cross_cell_sharp_components={k:v for k,v in cross.items() if k!='largest_components'},
                    largest_sharp_components=[{k:v for k,v in c.items() if k!='source_cells'} for c in cross['largest_components'][:6]],
                    eq4_classification=stage.get('eq4_classification'),monitor=stage.get('monitor'),
                    requested_weights=metadata.get('requested_ratio_row'),effective_weights=metadata.get('weights'),
                    u_map=metadata.get('u_map'),intrinsic_modulation=metadata.get('intrinsic_modulation'),
                    locking={k:v for k,v in metadata.get('locking',{}).items() if k!='active_vertices'}))
            result.append(dict(id=case.name,phase=phase,artifact=root.reference(path.parent),status=data['status'],
                geometry_state=data.get('geometry_state'),reason=data.get('reason'),output_sha256=data.get('output_sha256'),
                source_immutable=data.get('source_immutable'),statistics=data.get('terminal_statistics'),
                runtime_seconds=data.get('runtime_seconds'),process=data.get('process'),ornament=data.get('ornament'),
                request_sha256=data.get('request_sha256'),stages=rows))
    return result

def export(root,phases):
    target=ROOT/'studies/task22'; target.mkdir(parents=True,exist_ok=True)
    data=cases(root,phases); recipes=[read(p) for p in sorted(root.resolve('study/recipes').glob('*.json'))]
    write(target/'recipes.json',dict(version=1,artifact_references='Relative to explicitly configured output root',recipes=recipes))
    write(target/'summaries/verification.json',read(root.resolve('study/verification.json')))
    for phase in phases: write(target/('summaries/'+phase.lower()+'.json'),[r for r in data if r['phase']==phase])
    write(root.resolve('study/delivery_table.json'),data)
    report=dict(phases={p:dict(cases=sum(r['phase']==p for r in data),status=dict(Counter(r['status'] for r in data if r['phase']==p)),
        geometry_state=dict(Counter(r['geometry_state'] for r in data if r['phase']==p)),
        distinct_successful_geometry_hashes=len({r['output_sha256'] for r in data if r['phase']==p and r['status']=='SUCCESS'})) for p in phases},
        raw_dataset_bytes=sum(p.stat().st_size for p in root.path.rglob('*') if p.is_file()))
    gates=[r for r in recipes if r['family'] in ('G1','G2','G3','G4','G5')]
    report['gate_causal_declarations']=len({digest({k:v for k,v in r.items() if k not in ('id','hypothesis','family')}) for r in gates})
    report['gate_declared_ids']=len(gates)
    write(root.resolve('study/coverage.json'),report)
    path=root.resolve('study/primary_table.csv')
    with path.open('w',newline='',encoding='utf-8') as stream:
        columns=['phase','id','status','geometry_state','vertices','faces','high_dihedral_fraction','max_dihedral','degenerate_faces','crossings','cross_cell_components','C0_multi_face_components','seconds','reason']
        writer=csv.DictWriter(stream,fieldnames=columns); writer.writeheader()
        for r in data:
            last=r['stages'][-1] if r['stages'] else {}; d=last.get('cross_cell_sharp_components',{}); stats=r.get('statistics') or {}
            writer.writerow(dict(phase=r['phase'],id=r['id'],status=r['status'],geometry_state=r['geometry_state'],vertices=stats.get('vertex_count'),faces=stats.get('face_count'),
                high_dihedral_fraction=last.get('high_dihedral_edge_fraction'),max_dihedral=(last.get('dihedral_degrees') or {}).get('max'),
                degenerate_faces=last.get('degenerate_faces'),crossings=last.get('crossings',{}).get('sampled_transverse_crossings'),
                cross_cell_components=d.get('multiple_neighboring_cells'),C0_multi_face_components=d.get('multiple_C0_source_faces'),seconds=r['runtime_seconds'],reason=r['reason']))
    print(report)

def restore_recipes(root):
    """Recreate requests from committed declarations, independent of screening scripts."""
    for recipe in read(ROOT/'studies/task22/recipes.json')['recipes']:
        write(root.resolve('study/recipes/'+recipe['id']+'.json'),recipe)

def verify_replays(root):
    selection=read(root.resolve('study/selection.json')); checks=[]
    for hero in selection.get('heroes',[]):
        a=sorted(root.resolve('study/HERO/'+hero).glob('attempt_*/summary.json'))[-1].parent
        b=sorted(root.resolve('study/REPLAY/'+hero).glob('attempt_*/summary.json'))[-1].parent
        x,y=read(a/'summary.json'),read(b/'summary.json')
        assert x['status']==y['status']=='SUCCESS'
        assert x['source_sha256']==y['source_sha256'] and x['source_immutable'] and y['source_immutable']
        assert x['recipe']==y['recipe'] and x['output_sha256']==y['output_sha256']
        stages=[]
        for p,q in zip(x['stages'],y['stages'],strict=True):
            assert p['stage']==q['stage'] and p['geometry_sha256']==q['geometry_sha256']
            for suffix in ('.json.gz','_lineage.json.gz','_signatures.json.gz'):
                assert digest(read(a/(p['stage']+suffix)))==digest(read(b/(q['stage']+suffix)))
            stages.append(dict(stage=p['stage'],geometry_sha256=p['geometry_sha256'],exact_lineage=True,exact_branch_signatures=True))
        checks.append(dict(id=hero,independent_workers=True,source_immutable=True,terminal_sha256=x['output_sha256'],checkpoints=stages))
    write(root.resolve('study/replay_verification.json'),dict(status='PASS' if checks else 'NOT_RUN',checks=checks))
    print('Exact independent replays:',len(checks))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output-root',required=True,type=Path); parser.add_argument('--snapshot',action='store_true'); parser.add_argument('--export',action='store_true'); parser.add_argument('--phases',nargs='+',default=['CONTROL','DISTANCE','PLANARITY','GATE','F','R','HERO','REPLAY'])
    parser.add_argument('--references',action='store_true'); parser.add_argument('--reference-worker',choices=('C0','C07','ORDERED')); parser.add_argument('--restore-recipes',action='store_true'); parser.add_argument('--verify-replays',action='store_true')
    args=parser.parse_args(); root=ArtifactRoot(args.output_root)
    if args.snapshot: snapshot(root)
    if args.export: export(root,args.phases)
    if args.references: references(root)
    if args.reference_worker: reference_worker(root,args.reference_worker)
    if args.restore_recipes: restore_recipes(root)
    if args.verify_replays: verify_replays(root)
