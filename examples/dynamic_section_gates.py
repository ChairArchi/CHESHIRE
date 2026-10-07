"""Task27 actual saved-geometry feedback, four controlled paths and checkpoints."""
import argparse
from pathlib import Path
import sys,json,gc
from time import perf_counter
import numpy as np

REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
from cross_cell_crease_study import read,write,gz_write,file_hash,mesh_to_data,raw_mesh,versions
from generational_folding import budget_for,verify_obj
from hero_design_sprint import guarded
from cheshire import save_mesh,inspect_mesh
from cheshire.fold_continuation import save_state,load_state
from cheshire.dynamic_sections import definition,gate,restore,measure,map_rules,step
from cheshire.progressive_gates import symmetry

BASELINE='53bea0fda2779cb63a6ef31f5b7eb9c5eeff7392'
CONFIGS=dict(R1=dict(offset_ratio=.08,face_gain=1.,edge_gain=1.))
PATHS=['CONTROL_CC','PROFILE_CC','PROFILE_STATIC','PROFILE_DYNAMIC']
SOURCES=['src/cheshire/dynamic_sections.py','examples/dynamic_section_gates.py',
         'src/cheshire/generational_subdivision.py','src/cheshire/weighted_subdivision.py',
         'src/cheshire/progressive_gates.py','src/cheshire/fold_continuation.py']


def directory(root,name):
    d=root/'stages'/name
    if not (d/'summary.json').exists() or read(d/'summary.json')['status']!='SUCCESS':
        raise ValueError('Actual successful checkpoint required: '+name)
    return d


def persist(mesh,state,d,name):
    gz_write(d/'geometry.json.gz',mesh_to_data(mesh));save_state(d/'state.json.gz',state)
    save_mesh(mesh,d/(name+'.obj'));return verify_obj(mesh,d/(name+'.obj'))


def initialize(root):
    if root.exists():raise ValueError('Initialize a fresh Task27 root; preserve existing artifacts.')
    root.mkdir(parents=True);write(root/'configuration.json',dict(baseline=BASELINE,configs=CONFIGS,
        paths=PATHS,scope='New connected port gate, current-geometry feedback. No Task26 recipe continuation.'))
    for profile in (False,True):
        defn=definition(profile);mesh,state=gate(defn);name=state['input']['name'];d=root/'stages'/name;d.mkdir(parents=True)
        write(root/'definitions'/(name+'.json'),defn)
        check=persist(mesh,state,d,name);descriptors=measure(mesh,state);gz_write(d/'descriptors.json.gz',descriptors)
        write(d/'summary.json',dict(status='SUCCESS',name=name,parent=None,path=name,generation=0,
            statistics=inspect_mesh(mesh),symmetry=symmetry(mesh,state),OBJ_validation=check,
            sections=descriptors['sections'],geometry_sha256=file_hash(d/'geometry.json.gz')))
    print('Created two actual connected coarse section/port gates.',flush=True)


def statistics(rows):
    if not rows:return {}
    return {k:dict(min=min(r[k] for r in rows),median=float(np.median([r[k] for r in rows])),
        max=max(r[k] for r in rows)) for k in ('wf','w1','w2','w3','w4')}


def run_one(root,name):
    recipe=read(root/'recipes'/(name+'.json'));d=root/'stages'/name
    if d.exists():raise ValueError('Preserve actual saved stage; use a new revision ID.')
    d.mkdir(parents=True);parent=directory(root,recipe['parent']);times={};start=perf_counter()
    code={n:file_hash(REPO/n) for n in SOURCES}
    write(d/'request.json',dict(recipe=recipe,baseline=BASELINE,source_hashes=code,
        parent=dict(path=str(parent),geometry_sha256=file_hash(parent/'geometry.json.gz'),state_sha256=file_hash(parent/'state.json.gz'))))
    try:
        t=perf_counter();mesh=raw_mesh(read(parent/'geometry.json.gz'));state=restore(load_state(parent/'state.json.gz'));times['parent_file_read']=perf_counter()-t
        # More conservative than Task26: measured descriptor/parameter tables
        # coexist with the full native CC working mesh. No historical face cap.
        expected_faces=sum(len(mesh.face_vertices(f)) for f in mesh.faces())
        budget,forecast=budget_for(mesh,d,dict(resource_bytes_per_face=10000,
            resource_rationale='200 MiB fixed Python/driver overhead plus 10,000 bytes/output face; conservative allowance for current slice/face descriptors, local overrides and complete operator audit. Unchanged live RAM guard.'),
            predicted_total_bytes=200*1024**2+expected_faces*10000)
        t=perf_counter();result,new_state,descriptors,rules,method=step(mesh,state,recipe['path'],recipe['config'],budget);times['measure_map_subdivide_state']=perf_counter()-t
        if descriptors is not None:gz_write(d/'descriptors.json.gz',descriptors)
        gz_write(d/'rules.json.gz',dict(input_generation=state['generation']['absolute_cc'],method=method,faces=rules))
        gz_write(d/'operator.json.gz',result.metadata)
        metrics=statistics(list(rules.values()));region_metrics={}
        for part in sorted(set(state['gate']['parts'].values())):
            fs=[f for f in mesh.faces() if state['gate']['parts'][f]==part]
            region_metrics[part]=statistics([rules[f] for f in fs]) if rules else {}
        # Full actual output remeasurement is saved as observation for ALL paths.
        # STATIC never consumes this observation when choosing its next rules.
        t=perf_counter();output_measure=measure(result.mesh,new_state);times['output_section_observation']=perf_counter()-t
        gz_write(d/'observations.json.gz',output_measure)
        report=symmetry(result.mesh,new_state);mesh=result.mesh
        del result,state,rules,descriptors;gc.collect()
        t=perf_counter();check=persist(mesh,new_state,d,name);times['checkpoint_export_reread']=perf_counter()-t
        write(d/'summary.json',dict(status='SUCCESS',name=name,parent=recipe['parent'],path=recipe['path'],revision=recipe['revision'],
            generation=new_state['generation']['absolute_cc'],statistics=inspect_mesh(mesh),symmetry=report,rule_method=method,
            rule_statistics=metrics,part_rule_statistics=region_metrics,sections=output_measure['sections'],
            OBJ_validation=check,resource_forecast=forecast,times=times,total_seconds=perf_counter()-start,
            geometry_sha256=file_hash(d/'geometry.json.gz'),rules_sha256=file_hash(d/'rules.json.gz')))
        print(name,'SUCCESS',mesh.number_of_vertices(),mesh.number_of_faces(),round(perf_counter()-start,3),'s',flush=True)
    except Exception as exc:
        write(d/'summary.json',dict(status='TECHNICAL_STOP',name=name,parent=recipe['parent'],reason=str(exc),times=times,total_seconds=perf_counter()-start));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--initialize',action='store_true')
    p.add_argument('--run',nargs='+',choices=PATHS);p.add_argument('--to-generation',type=int,default=3)
    p.add_argument('--revision',default='R1');p.add_argument('--worker');a=p.parse_args();root=a.output_root.resolve()
    if a.initialize:initialize(root)
    if a.worker:run_one(root,a.worker)
    if a.run:
        config=read(root/'configuration.json')['configs'][a.revision]
        for path in a.run:
            for g in range(1,a.to_generation+1):
                name=f'{a.revision}_{path}_G{g}'
                if (root/'stages'/name/'summary.json').exists():
                    directory(root,name);continue
                parent=('G0_CONTROL' if path=='CONTROL_CC' else 'G0_PROFILE') if g==1 else f'{a.revision}_{path}_G{g-1}'
                write(root/'recipes'/(name+'.json'),dict(name=name,path=path,parent=parent,revision=a.revision,config=config))
                process=guarded(['--output-root',str(root),'--worker',name],root/'logs'/name,worker_script=Path(__file__))
                print(name,process,flush=True)
                if process['exit_code']:raise ValueError('Actual worker failed; retained checkpoint/log records.')
