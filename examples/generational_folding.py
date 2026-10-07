"""Task25: actual whole-gate continuation, resource observations and checkpoints."""
import argparse
import gc
from pathlib import Path
import shutil
import subprocess
import sys
from time import perf_counter

REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/p) for p in ('examples','tools')]
from cross_cell_crease_study import read,write,file_hash,digest,gz_write,raw_mesh,mesh_to_data,versions
from beyond_smoothness_study import restore_history
from cross_cell_crease_capability import fold
from hero_design_sprint import guarded,verify_frozen_inputs
from cheshire import save_mesh,inspect_mesh
from cheshire.fold_continuation import fold_state,save_state,load_state
from cheshire.artifact_root import ArtifactRoot
from cheshire.execution import ExecutionBudget
from branching_process import windows_memory

BASELINE='385ec86c1f18ee1e2e0d61e2b32c524ceccfb683'


def initialize(root,previous):
    if subprocess.run(['git','merge-base','--is-ancestor',BASELINE,'HEAD'],cwd=REPO).returncode:
        raise ValueError('Task24 baseline ancestry required; no reset.')
    verify_frozen_inputs(ArtifactRoot(previous))
    root.mkdir(parents=True,exist_ok=True);sources=[]
    c0=root/'inputs/C0.json';c0.parent.mkdir(parents=True,exist_ok=True)
    if not c0.exists():shutil.copyfile(previous/'inputs/C0.json',c0)
    if file_hash(c0)!=file_hash(previous/'inputs/C0.json'):raise ValueError('C0 routing basis changed.')
    for name,attempt,folds in [('H1','002',2),('H2_R1','002',2),('H3_R3','001',2)]:
        d=previous/'designs'/name/('attempt_'+attempt);summary=read(d/'summary.json')
        if summary['status']!='SUCCESS' or not all(file_hash(d/n)==h for n,h in summary['exports'].items()):
            raise ValueError('Task24 actual export identity changed: '+name)
        target=root/'inputs'/name;target.mkdir(parents=True,exist_ok=True)
        for filename in ['terminal.json.gz','terminal_lineage.json.gz','terminal_signatures.json.gz','terminal_networks.json',name+'.obj']:
            dst=target/filename
            if dst.exists() and file_hash(dst)!=file_hash(d/filename):raise ValueError('Frozen input differs; refuse overwrite.')
            if not dst.exists():shutil.copyfile(d/filename,dst)
        data=read(target/'terminal_lineage.json.gz');sigs=read(target/'terminal_signatures.json.gz');paths=[tuple(p) for p in sigs['paths']]
        state=dict(history=restore_history(data['history']),source_cells={int(f):c for f,c in data['source_cells'].items()},
            events=data['events'],anchors={int(v):p for v,p in data['anchors'].items()},
            signatures={int(f):{paths[p]:w for p,w in rows} for f,rows in sigs['faces'].items()},
            origins={},networks=read(target/'terminal_networks.json'),seed=None,
            generation=dict(absolute_cc=3+folds,backbone_cc=3,task24_relative_cc=folds,continuation_depth=0,
                note='Absolute counts CC only. Network generations count splits since route birth. Task24 did not retain generic point origins after Mola; first continuation bootstraps actual immediate CC origins.'),
            input=dict(name=name,Task24_source=str(d),geometry_sha256=digest(read(target/'terminal.json.gz')),units='None / original model units'),
            completed_step='Task24 terminal',next_step=None)
        state_file=target/'state.json.gz'
        if state_file.exists():
            if load_state(state_file)!=state:raise ValueError('Existing frozen continuation state changed.')
        else:save_state(state_file,state)
        sources.append(dict(id=name,source=str(d),summary_sha256=file_hash(d/'summary.json'),
            geometry=summary['terminal_canonical_sha256'],files={p.name:file_hash(p) for p in target.iterdir() if p.is_file()}))
    write(root/'input_identity.json',dict(baseline=BASELINE,inputs=sources,routing_C0_sha256=file_hash(c0),original_coordinates=True,physical_units='UNRESOLVED'))
    recipes=[
        dict(id='H1_CONTROL_G1',input='H1',question='Standard CC geometry with inherited integer creases still active; additional placement terms inactive.',declaration=fold(12)),
        dict(id='H1_FLOW_G1',input='H1',question='Continue inherited routes with inward edge and outward face/corner articulation, broader support than H1 late fold.',declaration=fold(18,wf=24,we=-12,wp=18,w1=-.6,w2=-1.1)),
        dict(id='H1_REVISED_G1',input='H1',question='Compare stronger contrasting interpolation and softened ridge retention at equal depth.',declaration=fold(28,wf=36,we=-18,wp=24,w1=-1.1,w2=-1.7),sharpness=2),
    ]
    for r in recipes:
        r.update(mode='INTEGER_COMPAS',seed=None,baseline=BASELINE,depth=1)
        path=root/'recipes'/(r['id']+'.json');path.parent.mkdir(exist_ok=True)
        if not path.exists():write(path,r)
    print('Frozen actual H1/H2/H3 state retained; cumulative CC=5.',flush=True)


def verify_obj(mesh,path):
    """Read the actual file sequentially; exact coordinates and oriented cycles.

    Avoid allocating a second million-face mesh merely for export validation.
    The parser accepts the written polygon subset and never welds or repairs.
    """
    keys=list(mesh.vertices());indices={v:i for i,v in enumerate(keys)};faces=iter(mesh.faces());i=0;j=0
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            tokens=line.split()
            if not tokens:continue
            if tokens[0]=='v':
                if i>=len(keys) or list(map(float,tokens[1:]))!=list(mesh.vertex_coordinates(keys[i])):
                    raise ValueError('Written OBJ coordinates changed.')
                i+=1
            if tokens[0]=='f':
                face=next(faces,None)
                if face is None or [int(t)-1 for t in tokens[1:]]!=[indices[v] for v in mesh.face_vertices(face)]:
                    raise ValueError('Written OBJ oriented connectivity changed.')
                j+=1
    if i!=len(keys) or j!=mesh.number_of_faces():raise ValueError('Written OBJ count changed.')
    return dict(actual_file_read=True,exact_XYZ_oriented_faces=True,vertices=i,faces=j,
        parser='Sequential written polygon records; no welding, triangulation, repairs or extra mesh allocation.')


def budget_for(mesh,directory,recipe):
    faces=sum(len(mesh.face_vertices(f)) for f in mesh.faces());vertices=mesh.number_of_vertices()+mesh.number_of_edges()+mesh.number_of_faces()
    memory=windows_memory();available=memory['available_bytes'];per_face=recipe.get('resource_bytes_per_face',16000)
    predicted=faces*per_face
    # Calibration measures TOTAL process-tree peak, including the input already
    # loaded here. Compare only predicted additional allocation with remaining
    # available RAM; subtracting the worker only leaves driver memory conservative.
    resident=memory['combined_resident_bytes'];additional=max(0,predicted-resident)
    record=dict(output_faces=faces,output_vertices=vertices,bytes_per_output_face=per_face,
        predicted_working_bytes=predicted,predicted_additional_bytes=additional,resident_worker_before_bytes=resident,
        available_bytes=available,fraction_of_available=.55,
        accounting='Measured total-peak calibration includes already loaded input. Compare additional=predicted_total-current_worker_resident to remaining available; driver remains in forecast.',
        reason=recipe.get('resource_rationale','Inherited Task24 conservative estimate, pending completed-run calibration.'))
    record['status']='SAFE_FORECAST' if additional<=available*.55 else 'PREDICTION_STOP'
    write(directory/'resource_preflight.json',record)
    if additional>available*.55:raise MemoryError('PREDICTION_STOP: '+str(record))
    return ExecutionBudget(faces,vertices,None),record


def run_one(root,name):
    identity=read(root/'input_identity.json')
    for row in identity['inputs']:
        for filename,sha in row['files'].items():
            if file_hash(root/'inputs'/row['id']/filename)!=sha:raise ValueError('Frozen Task25 input bytes changed.')
    if file_hash(root/'inputs/C0.json')!=identity['routing_C0_sha256']:raise ValueError('C0 routing coordinates changed.')
    recipe=read(root/'recipes'/(name+'.json'));base=root/'designs'/name;base.mkdir(parents=True,exist_ok=True)
    directory=base/('attempt_'+str(len(list(base.glob('attempt_*')))+1).zfill(3));directory.mkdir()
    if recipe.get('checkpoint'):
        input_dir=root/recipe['checkpoint'];geometry=input_dir/'geometry.json.gz';state_path=input_dir/'state.json.gz'
    else:
        input_dir=root/'inputs'/recipe['input'];geometry=input_dir/'terminal.json.gz';state_path=input_dir/'state.json.gz'
    code=versions();code['source_files'].update({p.relative_to(REPO).as_posix():file_hash(p) for p in [Path(__file__),REPO/'src/cheshire/fold_continuation.py']})
    for n,h in code['source_files'].items():
        dst=root/'source_snapshots'/h/n
        if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REPO/n,dst)
    write(directory/'request.json',dict(recipe=recipe,code=code,baseline=BASELINE,
        input_geometry_sha256=file_hash(geometry),input_state_sha256=file_hash(state_path),input_geometry=str(geometry),input_state=str(state_path),
        frozen_input_identity=identity,routing_C0_sha256=file_hash(root/'inputs/C0.json')))
    mesh=raw_mesh(read(geometry));state=load_state(state_path)
    if set(state['history'])!=set(mesh.faces()):raise ValueError('Continuation state coverage mismatch.')
    if 'sharpness' in recipe:
        from dataclasses import replace
        from cheshire.creases import CreaseNetwork
        state['networks']=[replace(n,edges=tuple(replace(e,sharpness=float(recipe['sharpness'])) for e in n.edges)).to_data()
            for n in [CreaseNetwork.from_data(row) for row in state['networks']]]
    if recipe.get('support_route'):
        from cheshire.crease_routing import CreaseRouter
        source=raw_mesh(read(root/'inputs/C0.json'))
        router=CreaseRouter(mesh,source,state['history'],state['source_cells'],state['events'])
        net=router.generate(recipe['support_route'],'lintel_convergence_support')
        state['networks']=[*state['networks'],net.to_data()]
        write(directory/'new_support_route.json',net.to_data())
        del router,source;gc.collect()
    start=perf_counter();times={}
    try:
        budget,forecast=budget_for(mesh,directory,recipe)
        print(name,'fold input',mesh.number_of_faces(),'CC',state['generation']['absolute_cc'],flush=True)
        t=perf_counter();result,next_state=fold_state(mesh,state,recipe['declaration'],budget=budget,mode=recipe['mode']);times['operation']=perf_counter()-t
        del mesh,state;mesh=result.mesh;metadata=result.metadata;del result;gc.collect()
        write(directory/'operator_summary.json',dict(name=metadata['name'],declaration=recipe['declaration'],
            generation=next_state['generation'],origin_state_count=len(next_state['origins']),
            operator_scope='Existing reference crease + sharp weighted CC composition; no new geometry engine.'))
        print(name,'checkpoint',mesh.number_of_faces(),round(times['operation'],2),flush=True)
        t=perf_counter();gz_write(directory/'operator.json.gz',metadata);del metadata;gc.collect();times['operator_save']=perf_counter()-t
        t=perf_counter();gz_write(directory/'geometry.json.gz',mesh_to_data(mesh));save_state(directory/'state.json.gz',next_state);times['state_save']=perf_counter()-t
        t=perf_counter();obj=directory/(name+'.obj');save_mesh(mesh,obj);times['OBJ_write']=perf_counter()-t
        t=perf_counter();check=verify_obj(mesh,obj);times['OBJ_read_check']=perf_counter()-t
        write(directory/'summary.json',dict(status='SUCCESS',recipe=recipe,code=code,input_geometry=str(geometry),input_state=str(state_path),
            statistics=inspect_mesh(mesh),generation=next_state['generation'],resource_forecast=forecast,
            elapsed_seconds=perf_counter()-start,times=times,OBJ_validation=check,
            artifacts={p.name:dict(bytes=p.stat().st_size,sha256=file_hash(p)) for p in directory.iterdir() if p.is_file()},
            units='None / original coordinate units; Z up; no scaling, no repair.'))
        print(name,'SUCCESS',flush=True)
    except (ValueError,MemoryError,ArithmeticError) as exc:
        write(directory/'summary.json',dict(status='TECHNICAL_STOP',reason=str(exc),recipe=recipe,
            last_preserved_input=str(geometry),elapsed_seconds=perf_counter()-start,times=times,code=code))
        print(name,'STOP',str(exc),flush=True)
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--previous-root',type=Path,default=Path('E:/CHESHIRE_DATA/task24'))
    p.add_argument('--initialize',action='store_true');p.add_argument('--run',nargs='+');p.add_argument('--worker')
    a=p.parse_args();root=a.output_root.resolve()
    if a.initialize:initialize(root,a.previous_root)
    if a.worker:run_one(root,a.worker)
    elif a.run:
        for name in a.run:
            result=guarded(['--output-root',str(root),'--worker',name],root/'logs'/name,worker_script=Path(__file__))
            print(name,result,flush=True)
            if result['exit_code']:raise ValueError('Worker stopped; input and completed checkpoints retained.')
