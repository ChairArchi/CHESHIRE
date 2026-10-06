"""Task22 serial isolated study; explicit portable external root, hash resume."""
import argparse
from collections import Counter
from copy import deepcopy
import json
from math import dist,fsum
import os
from pathlib import Path
import shutil
import subprocess
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
for folder in ('rhino','examples','tools'): sys.path.insert(0,str(ROOT/folder))
from cheshire import inspect_mesh,save_mesh
from cheshire.artifact_root import ArtifactRoot
from cheshire.execution import ExecutionBudget
from cheshire.gate_integrity import GateIntegrityMonitor
from cheshire.lineage import ParentRef
from cheshire.ornament import source_history,propagate_history,select_event_faces,depth_diagnostics
from cheshire.vocabulary import VocabularyStage,vocabulary_event,VocabularyRecipe,VocabularyRouter
from cheshire.branching import BranchSignatures
from cheshire.sharp_subdivision import (sharp_subdivide_once,source_graph_distance,inherit_scalar,intrinsic_overrides,
    normal_variation_values,motif_values,topology_motifs)
from cheshire_worker import mesh_from_data,mesh_to_data,RUNTIME_IDENTITY
from branching_process import bounded_worker
from ornament_study import digest,file_hash,verified_resume,gz_write
from beyond_smoothness_verify import read,write,BASELINE
from beyond_smoothness_recipes import controls,lock_sanity
from beyond_smoothness_diagnostics import observe,geometry_state

def versions():
    import compas
    names=[p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'src/cheshire').glob('*.py'))]
    names+=['rhino/'+n for n in ('cheshire_worker.py','exchange.py','worker_process.py')]
    names+=['examples/'+n for n in ('beyond_smoothness_study.py','beyond_smoothness_diagnostics.py',
        'beyond_smoothness_verify.py','beyond_smoothness_recipes.py','ornament_study.py','carrier_scale_study.py')]
    names+=['tools/'+n for n in ('branching_process.py','morphology_crossings.py','morphology.py')]
    return dict(COMPAS=compas.__version__,Python=sys.version,source_files={n:file_hash(ROOT/n) for n in names},
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())

def input_reference(name):
    return 'inputs/'+({'C07':'BACKBONE_S05.json.gz','ORDERED_CORE':'ORDERED_CORE.json.gz'}.get(name,name+'.json'))

def make_request(root,recipe,phase='CONTROL',dll=None):
    input_path=root.resolve(input_reference(recipe['input']))
    gate=recipe['input'] in ('C07','ORDERED_CORE')
    backend=None
    if recipe['finish']:
        if dll is None: raise ValueError('Explicit official DLL required for existing finish.')
        backend=dict(HDMola_sha256=file_hash(dll),runtime='Existing CoreCLR/.NET8; external DLL, never copied into project.')
    dependencies={}
    if gate:
        refs=['inputs/C0.json','inputs/CC3_origins.json.gz','inputs/backbone.json',
            'inputs/'+('C07_anchors.json' if recipe['input']=='C07' else 'ORDERED_CORE_anchors.json'),
            'inputs/'+('BACKBONE_S05_lineage.json.gz' if recipe['input']=='C07' else 'ORDERED_CORE_lineage.json.gz'),
            'inputs/'+('BACKBONE_S05_signatures.json.gz' if recipe['input']=='C07' else 'ORDERED_CORE_signatures.json.gz')]
        if recipe['finish']: refs.append('inputs/ORDERED_recipe.json')
        if recipe['input']=='ORDERED_CORE': refs+=['inputs/BACKBONE_S05.json.gz']+[f'inputs/ORDERED_S{i:02d}_lineage.json.gz' for i in range(6,11)]
        dependencies={ref:digest(read(root.resolve(ref))) for ref in refs}
    return dict(recipe=recipe,input=root.reference(input_path),source_sha256=digest(read(input_path)),external_backend=backend,
        reference_dependencies=dependencies,
        baseline=BASELINE,code=versions(),max_faces=(150000 if phase=='GATE' else 300000) if gate else 50000,
        max_generation=48,retention='Every sharp checkpoint; terminal exact JSON/OBJ; immediate positive construction association separately recorded.',
        crossing_sample_faces=4096,crossing_cap=30,equation_mode='LITERAL_EQ10_EQ11_UNNORMALIZED')

def initialize(root):
    if read(root.resolve('study/verification.json'))['status']!='PASS': raise ValueError('Strict regression gate required.')
    recipes=controls()+lock_sanity()
    for r in recipes: write(root.resolve('study/recipes/'+r['id']+'.json'),r)
    write(root.resolve('study/plan.json'),dict(baseline=BASELINE,control_cases=48,lock_sanity_cases=4,
        external_root_required=True,free_space_floor_bytes=12*1024**3,storage_ceiling_bytes=80*1024**3,
        process_guard='Existing creation-time-verified Task20 worker guard; 4GiB process tree; 900 seconds/case.',
        normal_scaling='wf/we/wp are ratios of current global mean edge length, as in existing grammar.',
        geometry_state='UNSTABLE: existing degenerate fan test, topology failure or 30 sampled transverse contacts. BOUNDARY_SHARP: nonzero contacts/opposed fans/bilinear warnings. Sharp dihedral alone never rejects.',
        reference_cameras='Frozen Task21 bounds; controls use fixed fixture cameras, no per-case fitting.'))
    print('Initialized 48 controls and 4 literal lock comparisons.')

def crossing(root,directory,geometry,label,source):
    directory.mkdir(parents=True,exist_ok=True)
    faces=geometry['faces']; sample=faces if len(faces)<=4096 else [faces[i*len(faces)//4096] for i in range(4096)]
    used={v for f in sample for v in f['vertices']}
    write(directory/'request.json',dict(mesh=source))
    write(directory/'response.json',dict(variants=[dict(id=label,mesh=dict(vertices=[v for v in geometry['vertices'] if v['id'] in used],faces=sample))]))
    process=bounded_worker([ROOT/'tools/morphology_crossings.py',directory],directory/'logs',90)
    write(directory/'process.json',process)
    if process['exit_code']: raise ValueError('Crossing diagnostic failed; geometry retained, no further growth.')
    result=read(directory/'crossing_audit.json')['candidates'][0]
    result['sampling']=dict(actual_faces=len(sample),total_faces=len(faces),method='Deterministic evenly spaced ordered face subset; adjacent/coplanar excluded; no collision certificate.')
    return result

def restore_history(data):
    return {int(f):{**r,'source':{int(k):w for k,w in r['source'].items()},'roles':tuple(tuple(t) for t in r['roles']),
        'events':tuple(r['events'])} for f,r in data.items()}

def support_values(mesh,history,scope):
    if scope=='ALL': return None
    if not isinstance(scope,dict): raise ValueError('Explicit source/role support required.')
    if set(scope)=={'source_face_ids'}:
        allowed=set(scope['source_face_ids'])
        fractions={f:fsum(w for source,w in r['source'].items() if source in allowed) for f,r in history.items()}
    elif set(scope)=={'event_stage','role'}:
        fractions={f:float((scope['event_stage'],scope['role']) in r['roles']) for f,r in history.items()}
    else: raise ValueError('Unsupported source support declaration.')
    return {v:fsum(fractions[f] for f in mesh.vertex_faces(v))/len(mesh.vertex_faces(v)) for v in mesh.vertices()}

def can_resume(directory,request):
    try:
        candidate=deepcopy(request)
        # A commit of identical source bytes changes provenance, not the computation.
        saved=read(Path(directory)/'request.json') if (Path(directory)/'request.json').exists() else {}
        if 'code' in candidate and 'code' in saved and candidate['code'].get('source_files')==saved['code'].get('source_files'):
            candidate['code']['commit']=saved['code']['commit']
        return verified_resume(directory,candidate)
    except (OSError,json.JSONDecodeError,KeyError,TypeError):
        # Retain interrupted attempts; they cannot prevent later independent cases.
        return False

def one(root,case_reference,request,dll):
    directory=root.resolve(case_reference); directory.mkdir(parents=True,exist_ok=False)
    write(directory/'request.json',request); write(directory/'worker_identity.json',dict(pid=os.getpid(),runtime=RUNTIME_IDENTITY))
    recipe=request['recipe']; source_data=read(root.resolve(request['input'])); mesh=mesh_from_data(source_data)
    if digest(source_data)!=request['source_sha256']: raise ValueError('Source hash changed before worker start.')
    for name,sha in request['code']['source_files'].items():
        if file_hash(ROOT/name)!=sha: raise ValueError('First-party source changed before worker start: '+name)
    for ref,sha in request.get('reference_dependencies',{}).items():
        if digest(read(root.resolve(ref)))!=sha: raise ValueError('Frozen reference dependency changed: '+ref)
    if request.get('external_backend') and (dll is None or file_hash(dll)!=request['external_backend']['HDMola_sha256']): raise ValueError('External backend hash mismatch.')
    source_mesh=mesh
    original=deepcopy(mesh.__data__); origin=None; records=[]; started=perf_counter(); failure=None; state='VALID_SHARP'
    gate=recipe['input'] in ('C07','ORDERED_CORE'); c0=mesh_from_data(read(root.resolve('inputs/C0.json')))
    if gate:
        name='BACKBONE_S05_lineage.json.gz' if recipe['input']=='C07' else 'ORDERED_CORE_lineage.json.gz'
        lineage=read(root.resolve('inputs/'+name)); history=restore_history(lineage['history']); events=lineage['events']
        monitor=GateIntegrityMonitor(c0)
        origin={int(v):r for v,r in read(root.resolve('inputs/CC3_origins.json.gz')).items() if mesh.has_vertex(int(v))}
    else: history=source_history(mesh); events=[]; monitor=None
    tracker=BranchSignatures(mesh)
    if gate:
        data=read(root.resolve('inputs/'+('BACKBONE_S05_signatures.json.gz' if recipe['input']=='C07' else 'ORDERED_CORE_signatures.json.gz')))
        paths=[tuple(p) for p in data['paths']]
        tracker.faces={int(f):{paths[p]:w for p,w in refs} for f,refs in data['faces'].items()}
        assert set(tracker.faces)==set(mesh.faces())
        for event in events:
            parent_paths=event.get('parent_branch_signatures',[])
            tracker.event_counts.update({(*tuple(p['path']),event['operator']+':'+c['role']) for p in parent_paths for c in event['children']})
    # CC retains the old corner keys. Newly generated points have no invented C0 anchor.
    anchors={int(v):p for v,p in read(root.resolve('inputs/'+('C07_anchors.json' if recipe['input']=='C07' else 'ORDERED_CORE_anchors.json'))).items()} if gate else {}
    cells={f:[f] for f in mesh.faces()}
    if gate and recipe['input']=='ORDERED_CORE':
        # Recover actual immediate old face ancestry to frozen S05 cells.
        cells={f:[f] for f in mesh_from_data(read(root.resolve('inputs/BACKBONE_S05.json.gz'))).faces()}
        for i in range(6,11):
            parents=read(root.resolve(f'inputs/ORDERED_S{i:02d}_lineage.json.gz'))['face_parents']
            cells={int(f):sorted({c for p in refs for c in cells[p['id']]}) for f,refs in parents.items()}
    seed_edge=next(mesh.edges())
    if gate:
        # A fixed source-graph edge, selected by original C0 lintel location, not generated geometry.
        seed_edge=next((e for e in c0.edges() if all(c0.vertex_coordinates(v)[2]>=monitor.ground+2600 for v in e)),next(c0.edges()))
    groups={'SOURCE_EDGE_ENDPOINT_CORNERS':dict(vertices=list(seed_edge),iterations=recipe['locks']['iterations'])}
    mode=recipe['locks']['mode']
    if mode=='INPUT_MOTIF_CORNERS':
        signatures=topology_motifs(mesh); support=support_values(mesh,history,recipe.get('scope','ALL'))
        vertices=[v for v,s in signatures.items() if s.key() in recipe['locks']['motifs'] and (support is None or support[v]>=.5)]
        if not vertices: raise ValueError('Empty declared input lock group.')
        groups={'INPUT_MOTIF_CORNERS':dict(vertices=vertices,iterations=recipe['locks']['iterations'])}
    elif mode!='SOURCE_EDGE_ENDPOINT_CORNERS': raise ValueError('Unknown literal vertex-group lock declaration.')
    distances=source_graph_distance(mesh,list(seed_edge)); scalar=distances['normalized']
    write(directory/'source_graph.json',dict(**distances,locking_group=groups))
    gz_write(directory/'G0.json.gz',source_data)
    def retain(label,metadata,parents=None,vertex_parents=None):
        nonlocal state
        geometry=mesh_to_data(mesh); write(directory/'terminal.json',geometry)
        gz_write(directory/(label+'.json.gz'),geometry)
        gz_write(directory/(label+'_lineage.json.gz'),dict(history=history,events=events,source_cells=cells,
            face_parents=parents,vertex_parents=vertex_parents,origin_lineage=origin,
            positive_sampling_association='Immediate constructive sampling; signed attraction is not semantic inheritance.'))
        gz_write(directory/(label+'_signatures.json.gz'),tracker.to_data())
        diagnostics=observe(mesh,cells,source_history=history); audit=crossing(root,directory/('audit_'+label),geometry,label,source_data)
        state=geometry_state(diagnostics,audit)
        row=dict(stage=label,operator_index=(10 if recipe['input']=='ORDERED_CORE' else 5 if gate else 0)+len(records)+1,
            statistics=inspect_mesh(mesh),geometry_sha256=digest(geometry),diagnostics=diagnostics,
            crossings=audit,geometry_state=state,elapsed_seconds=perf_counter()-started,
            metadata={k:v for k,v in metadata.items() if k not in ('points','motif_applications','face_sources','later_generation','origin_lineage','source_support_scale','events','selection','backend','later_generation_face_stencil')})
        if 'later_generation_face_stencil' in metadata:
            row['eq4_classification']={k:v for k,v in metadata['later_generation_face_stencil'].items() if k not in ('applications','fallbacks')}
        if monitor: row['monitor']=monitor.evaluate(mesh,anchors,generation=len(records)+1)
        records.append(row); gz_write(directory/(label+'_operator.json.gz'),metadata)
        write(directory/'summary.json',dict(status='RUNNING',request_sha256=digest(request),recipe=recipe,stages=records))
        print(recipe['id'],label,mesh.number_of_faces(),state,round(perf_counter()-started,2),flush=True)
        if state=='UNSTABLE': raise ValueError('Retained unstable checkpoint: degeneracy, topology failure or sampled crossing explosion. No repair.')
    try:
        for iteration,row in enumerate(recipe['schedule']['rows'],1):
            scale=fsum(dist(mesh.vertex_coordinates(a),mesh.vertex_coordinates(b)) for a,b in mesh.edges())/mesh.number_of_edges()
            weights={k:v*scale if k in ('wf','we','wp') else v for k,v in row.items()}
            modulation=deepcopy(recipe.get('modulation'))
            if modulation:
                if modulation['mode']=='NORMAL_VARIATION': scalar=normal_variation_values(mesh)
                modulation['controls']={k:[v*scale if k in ('wf','we','wp') else v for v in pair] for k,pair in modulation['controls'].items()}
            local,later,mod_info=intrinsic_overrides(mesh,modulation,scalar)
            # Regional u masks use existing original-source ancestry, not coordinate motif classification.
            u_map=recipe['u_map']; scope=recipe.get('scope','ALL'); support=support_values(mesh,history,scope)
            step=sharp_subdivide_once(mesh,weights,u_map=u_map,unknown_u=recipe['unknown_u'],lock_groups=groups,
                lock_iteration=iteration,origin_lineage=origin,point_weights=local or None,face_weights=later or None,
                budget=ExecutionBudget(request['max_faces'],request['max_faces']*2,request['max_generation']),current_generation=(3 if gate else 0)+iteration-1,
                vertex_u_scale=support)
            parents={r['id']:[ParentRef(r['source_face'],1.)] for r in step.metadata['face_sources']}
            cells={f:sorted({c for p in refs for c in cells[p.key]}) for f,refs in parents.items()}
            history=propagate_history(history,parents); scalar=inherit_scalar(scalar,step.sampling_parents)
            tracker.advance(parents,dict(stage=dict(operator='CC')))
            mesh=step.mesh; origin=step.origin_lineage; groups=step.lock_groups
            anchors={v:anchors.get(v) for v in mesh.vertices()} if monitor else {}
            step.metadata.update(global_mean_edge_length=scale,requested_ratio_row=row,intrinsic_modulation=mod_info)
            retain(f'G{iteration}',step.metadata,{f:[dict(id=p.key,weight=p.weight) for p in refs] for f,refs in parents.items()},step.sampling_parents)
        event_number=0
        for stage_data in recipe['finish']:
            router=None
            if stage_data.get('kind')=='branch_table':
                data=read(root.resolve('inputs/ORDERED_recipe.json')); data['steps']=[stage_data]
                fragment=VocabularyRecipe.from_data(data); router=VocabularyRouter(fragment)
                stages=fragment.compile().stages[fragment.backbone_stages:]
            else: stages=[VocabularyStage(**stage_data)]
            for stage in stages:
                event_number+=1
                selection=router.select(mesh,history,stage,c0,None,events) if router else select_event_faces(mesh,history,stage.selector,c0)
                if not selection['selected_ids'] and not selection.get('quiet_if_empty'): raise ValueError('Empty finish selection; no invented geometry.')
                if dll is None: raise ValueError('Official external DLL required for the existing finish.')
                step=vocabulary_event(mesh,history,stage,selected_faces=selection['selected_ids'],dll_path=str(dll),
                    routes=router.face_routes if router else None,
                    budget=ExecutionBudget(request['max_faces'],request['max_faces']*2,request['max_generation']),stage_index=(10 if recipe['input']=='ORDERED_CORE' else 5)+recipe['schedule']['generations']+event_number)
                parents=step['lineage'].face_parents
                cells={f:sorted({c for p in refs for c in cells[p.key]}) for f,refs in parents.items()}
                anchors={v:anchors.get(p) for v,p in step['corner_parents'].items()}
                tracker.advance(parents,dict(events=step['events']))
                mesh=step['mesh']; history=step['history']; events.extend(step['events'])
                origin={v:r for v,r in (origin or {}).items() if mesh.has_vertex(v)}
                retain(f'E{event_number}',dict(stage=stage.to_data() if hasattr(stage,'to_data') else stage_data,
                    selection=selection,events=step['events'],backend=step['backend'],quiet=not selection['selected_ids']),
                    {f:[dict(id=p.key,weight=p.weight) for p in refs] for f,refs in parents.items()},
                    {v:[[p.key,p.weight] for p in refs] for v,refs in step['lineage'].vertex_parents.items()})
    except (ValueError,ArithmeticError) as error:
        failure=str(error)
    geometry=mesh_to_data(mesh); write(directory/'terminal.json',geometry); save_mesh(mesh,directory/'terminal.obj')
    gz_write(directory/'terminal_lineage.json.gz',dict(history=history,events=events,source_cells=cells))
    gz_write(directory/'terminal_signatures.json.gz',tracker.to_data())
    write(directory/'branch_signatures.json',tracker.diagnostics(history,events))
    assert source_data==read(root.resolve(request['input']))
    artifacts={p.name:file_hash(p) for p in directory.iterdir() if p.is_file() and p.name!='summary.json'}
    summary=dict(status='TECHNICAL_STOP' if failure else 'SUCCESS',reason=failure or 'Requested finite schedule completed',
        geometry_state=state,recipe=recipe,request_sha256=digest(request),source_sha256=request['source_sha256'],
        code_commit=request['code']['commit'],stages=records,terminal_statistics=inspect_mesh(mesh),
        output_sha256=digest(geometry),artifacts=artifacts,runtime_seconds=perf_counter()-started,
        source_immutable=original==source_mesh.__data__,ornament=depth_diagnostics(history,events))
    write(directory/'summary.json',summary)

def execute(root,ids,phase,dll):
    for name in ids:
        if shutil.disk_usage(root.path).free<12*1024**3: raise ValueError('External disk below 12GiB safety floor; no fallback.')
        recipe=read(root.resolve('study/recipes/'+name+'.json')); request=make_request(root,recipe,phase,dll)
        base=root.resolve('study/'+phase+'/'+name); attempts=sorted(base.glob('attempt_*')) if base.exists() else []
        if any(can_resume(p,request) for p in attempts): print(name,'RESUME verified',flush=True); continue
        directory=base/f'attempt_{len(attempts)+1:03d}'; ref=root.reference(directory)
        req=root.resolve('study/requests/'+phase+'/'+name+'.json'); write(req,request)
        args=[Path(__file__).resolve(),'--worker',ref,'--request',root.reference(req),'--output-root',root.path]
        if dll is not None: args+=['--dll',dll]
        process=bounded_worker(args,root.resolve('logs/'+phase+'/'+name+'_'+directory.name),900)
        if not (directory/'summary.json').exists(): write(directory/'summary.json',dict(status='PROCESS_STOP',reason='See worker stderr',stages=[]))
        summary=read(directory/'summary.json'); summary['process']=process
        if process['exit_code']:
            measured=summary.get('stages',[])
            summary.update(status='PROCESS_STOP',reason=process['stop'] or 'Worker exception; see stderr',
                geometry_state=measured[-1]['geometry_state'] if measured else None)
        write(directory/'summary.json',summary)
        print(name,summary['status'],summary.get('geometry_state'),round(process['seconds'],2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output-root',required=True,type=Path)
    parser.add_argument('--init',action='store_true'); parser.add_argument('--run',nargs='+'); parser.add_argument('--phase',default='CONTROL')
    parser.add_argument('--worker'); parser.add_argument('--request'); parser.add_argument('--dll',type=Path)
    args=parser.parse_args(); root=ArtifactRoot(args.output_root)
    if args.worker: one(root,args.worker,read(root.resolve(args.request)),args.dll)
    elif args.init: initialize(root)
    elif args.run: execute(root,args.run,args.phase,args.dll)
    else: parser.error('Choose --init, --run or --worker.')
