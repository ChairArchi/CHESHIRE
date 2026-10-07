"""Task24: three explicit compositions of the existing Task23 machinery.

Run workers sequentially. Resource limits derive from measured available RAM;
contacts, aperture drift and elapsed time are observations, never vetoes.
"""
import argparse
from copy import deepcopy
import gc
import json
from math import dist, isfinite
from pathlib import Path
import shutil
import subprocess
import sys
from time import perf_counter, sleep

ROOT = Path(__file__).resolve().parents[1]
for folder in ('examples', 'rhino', 'tools'):
    sys.path.insert(0, str(ROOT / folder))
from cross_cell_crease_study import (read, write, digest, file_hash, gz_write,
    load, choose_faces, terminal_networks, raw_mesh, mesh_to_data, versions, prepared_substrate)
from cross_cell_crease_capability import fold
from cheshire import inspect_mesh, save_mesh, load_mesh
from cheshire.artifact_root import ArtifactRoot
from cheshire.crease_routing import CreaseRouter, unit
from cheshire.crease_folding import folded_crease_once
from cheshire.execution import ExecutionBudget
from cheshire.lineage import ParentRef
from cheshire.ornament import propagate_history, local_polygon, depth_diagnostics
from cheshire.vocabulary import VocabularyStage, vocabulary_event
from branching_process import (windows_memory, process_birth, scoped_family,
    birth_of_pid, terminate_tree)
from worker_process import worker_environment

BASELINE = '140932fb6cbcaec4a1d27665fb99bf0e0a806fc3'
INPUT_FILES = ['C0.json', 'backbone.json', 'BACKBONE_S05.json.gz',
    'BACKBONE_S05_lineage.json.gz', 'BACKBONE_S05_signatures.json.gz', 'C07_anchors.json']


def event(name, operator, parameters, *, count=32, z=.55, role=None,
          parent=None, placement='ADJACENT', hops=6, region=None):
    selector = dict(z_min=z, normal_y_min=0.)
    if region:
        selector['source_region'] = region
    if role:
        selector.update(role=role, event_stage=parent)
    return dict(kind='event', id=name, operator=operator, parameters=parameters,
        selector=selector, placement=placement, hops=hops, spacing=1,
        max_events=count, quad_only=True, stratify_by='C0_FACE',
        local_face_policy='Record incompatible local polygons; operate on usable selected faces without moving or repairing them.')


def fold_step(name, declaration):
    return dict(kind='fold', id=name, declaration=declaration)


def descendants(prefix, parent, role, *, count=48, height=1.5, z=.45):
    return [
        event(prefix+'_frame', 'InsetFrame', dict(width_ratio=.12),
            count=count, z=z, role=role, parent=parent),
        event(prefix+'_cap', 'TaperedExtrusion', dict(height_ratio=height, fraction=.25),
            count=count, z=z, role='INNER_CAP', parent=prefix+'_frame'),
        event(prefix+'_fine_frame', 'InsetFrame', dict(width_ratio=.08),
            count=count, z=z, role='EXTRUSION_CAP', parent=prefix+'_cap'),
        event(prefix+'_fine_cap', 'TaperedExtrusion', dict(height_ratio=height*.55, fraction=.3),
            count=count, z=z, role='INNER_CAP', parent=prefix+'_fine_frame')]


def declare(reference):
    old = {n: read(reference/'study/recipes'/f'{n}.json')
           for n in ('R20', 'X10', 'X01', 'X02', 'Y07', 'Y19')}
    y07 = old['Y07']['prepared_substrate']['crease_prefix_recipe']
    y19 = old['Y19']['prepared_substrate']['crease_prefix_recipe']
    # Existing N6 supports explicit architectural arm targets. Extend the
    # organization down the support; this is a routing declaration, not a field.
    legs = [dict(generator='N6', junction='Y', junction_xz=[sign*.39,.79],
        arm_targets=[[sign*.40,.20], [0,.98], [sign*.49,1.04]],
        sharpness=12, minimum_seed_support=0., minimum_target_support=0.,
        quiet_below=.12, target_y_ratio=-.85) for sign in (-1,1)]
    common = dict(input='C07', units='original model units; see input_identity.json',
        baseline=BASELINE, seed=None, mode='INTEGER_COMPAS',
        policy='Finite computation and actual operator compatibility; contacts/opening changes diagnostic.',
        no_terminal_smoothing=True)
    h1 = dict(common, id='H1', name='ANGULAR MANTLE / CLEFT',
        vocabulary=['R20','X10','Y19','X01'],
        networks=deepcopy(old['X10']['networks'])+legs,
        steps=[
            fold_step('mantle_macro', fold(10,wf=-280,we=320,wp=520,w1=.8,w2=-2.8,w6=-.9,w7=.8)),
            event('mantle_ridges','Roof',dict(height_ratio=1.2,direction_mode='vertical',gable_inset=.16),count=36,z=.48,hops=8),
            fold_step('cleft_articulation', fold(5,wf=130,we=130,wp=130,w1=-.35,w2=-.65)),
            *descendants('mantle','mantle_ridges','RIDGE_SIDE',count=72,height=2.2,z=.45)],
        intent='Opposed X10 angular placement, R20 matched normal offsets and Y19 restrained return; shoulder-to-support route continuation and nested ridge descendants.')
    h2 = dict(common, id='H2', name='BRANCHING CROWN / CANOPY',
        vocabulary=['R20','X01','Y07','X10'],
        networks=deepcopy(y07['networks'])+deepcopy(old['X01']['networks']),
        steps=[
            fold_step('crown_macro',fold(6,wf=480,we=160,wp=420,w1=-2.4,w2=-5.6,w6=-1.1,w7=-1.0)),
            event('major_branches','TaperedExtrusion',dict(height_ratio=4.,fraction=.32),count=16,z=.58,hops=5),
            fold_step('branch_articulation',fold(4,wf=-90,we=-40,wp=-80,w1=.35,w2=.6,w6=.2,w7=.2)),
            event('secondary_forks','Roof',dict(height_ratio=1.2,direction_mode='outward',gable_inset=.16),count=48,z=.5,role='EXTRUSION_SIDE',parent='major_branches',hops=8),
            *descendants('crown','secondary_forks','RIDGE_SIDE',count=80,height=1.6,z=.45)],
        intent='X01 directional branching interacts with Y07 bilateral fan displacement; early large taper branches are subdivided, then their surviving side descendants receive forks and nested tips.')
    h3 = dict(common,id='H3',name='ORDERED SHARD / CANYON',
        vocabulary=['R20','X02','Y19','X10'],
        networks=deepcopy(y19['networks'])+[dict(y19['networks'][0],target_y_ratio=1.05)],
        steps=[
            fold_step('canyon_macro',fold(10,wf=540,we=540,wp=540)),
            event('depth_assemblies','DirectionalExtrusion',dict(height_ratio=1.2,direction_mode='depth',normal_ratio=.55,tangent_sign=1),count=32,z=.57,hops=7),
            fold_step('intersecting_shards',fold(4,wf=-160,we=-65,wp=-110,w1=1.1,w2=1.6,w6=.4,w7=-.6)),
            event('canyon_ridges','Roof',dict(height_ratio=1.1,direction_mode='vertical',gable_inset=.22),count=48,z=.48,role='DIRECTIONAL_EXTRUSION_SIDE',parent='depth_assemblies',hops=9),
            *descendants('canyon','canyon_ridges','RIDGE_SIDE',count=64,height=1.8,z=.4)],
        intent='Y19 actually means matched offsets then a restrained generation and selective events; reuse that sequencing, add X02 reverse-signed shards and depth-axis assemblies on front/rear architectural routes.')
    return [h1,h2,h3]


def initialize(root, reference):
    root.path.mkdir(parents=True, exist_ok=True)
    if subprocess.run(['git','merge-base','--is-ancestor',BASELINE,'HEAD'],cwd=ROOT).returncode:
        raise ValueError('Task24 execution requires the specified baseline ancestry; no reset is performed.')
    identities=[]
    for n in INPUT_FILES:
        src=reference/'inputs'/n; dst=root.resolve('inputs/'+n)
        dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists() and file_hash(dst)!=file_hash(src):
            raise ValueError('Existing Task24 input differs; do not overwrite it.')
        if not dst.exists(): shutil.copyfile(src,dst)
        identities.append(dict(file='inputs/'+n,byte_sha256=file_hash(src),canonical_sha256=digest(read(src))))
    r20=reference/'study/CAPABILITY/R20/attempt_001'
    summary=read(r20/'summary.json')
    checked={n:file_hash(r20/n)==sha for n,sha in summary['artifacts'].items()}
    if not all(checked.values()) or read(reference/'study/retained_reproduction.json')['status']!='PASS':
        raise ValueError('Retained R20 evidence integrity failed.')
    write(root.resolve('input_identity.json'),dict(inputs=identities,
        R20_validation=dict(artifact=str(r20),status='PASS',artifacts_checked=len(checked),
            terminal_canonical_sha256=summary['output_sha256'],independent_Task23_replay='PASS'),
        provenance='Exact frozen Task23 C0 and C07 backbone; no replacement input. Upstream ALICE provenance and units must be resolved from original request metadata.',
        orientation='Original XYZ, Z up; front camera looks along +Y; original origin retained.'))
    for recipe in declare(reference):
        write(root.resolve('recipes/'+recipe['id']+'.json'),recipe)
    rows=[]
    for n in ('R20','X10','X01','X02','Y07','Y19'):
        r=read(reference/'study/recipes'/f'{n}.json')
        s=read(reference/'study/CAPABILITY'/n/'attempt_001/summary.json')
        stage=s['stages'][-1]['stage']
        write(root.resolve('references/'+n+'.json'),r)
        rows.append(dict(id=n,recipe='references/'+n+'.json',recipe_sha256=digest(r),
            definition='examples/cross_cell_crease_capability.py',
            implementation=['examples/cross_cell_crease_study.py:load/choose_faces/terminal_networks',
                'src/cheshire/crease_routing.py:CreaseRouter','src/cheshire/crease_folding.py:folded_crease_once',
                'src/cheshire/vocabulary.py:vocabulary_event'],
            input=r['input'],checkpoint=str(reference/'study/CAPABILITY'/n/'attempt_001'),
            output_stage=stage,images=[str(reference/'renders/CAPABILITY'/(n+'_'+stage+'_'+v+'.png')) for v in ('front','oblique','node')],
            semantics='Y07 resumes X07 E2; Y19 resumes R19 E2. Order in Y19 is relative editorial order, no separate sorting/spatial-field operator.' if n.startswith('Y') else 'Complete generation/event recipe, not an independent operator.'))
    write(root.resolve('source_map.json'),rows)
    print('Initialized three actual design compositions; R20 integrity verified.',flush=True)


def revise(root):
    """Two revisions motivated by the actual first three mesh views."""
    h2=deepcopy(read(root.resolve('recipes/H2.json')))
    h2.update(id='H2_R1',revision_of='H2',
        visual_observation='Initial fitted oblique: large broad rectangular cap masses dominate; fine forks are invisible at whole scale. Preserve canopy scale, taper tips and organize intermediate child branches.')
    h2['steps'][0]['declaration']=fold(6,wf=480,we=160,wp=420,w1=-1.8,w2=-4,w6=.9,w7=-.7)
    h2['steps'][1]['parameters'].update(height_ratio=3.6,fraction=.70)
    h2['steps'][1]['max_events']=12
    h2['steps'][3].update(operator='TaperedExtrusion',parameters=dict(height_ratio=1.8,fraction=.62),max_events=40)
    h2['steps'][4]['selector']['role']='EXTRUSION_SIDE'
    h2['intent']+=' Revision uses X01 interpolation and narrower primary/secondary taper caps; changes are editorial, not collision repairs.'
    h3=deepcopy(read(root.resolve('recipes/H3.json')))
    h3.update(id='H3_R1',revision_of='H3',
        visual_observation='Initial front/oblique: swollen continuous crown dominates, leaving a decorated thick lintel. Use stronger X02 point-class differences after the matched Y19 macro offset; move depth assemblies toward the opening rim.')
    h3['networks']=[dict(generator='N1',relation=relation,sharpness=12,target_y_ratio=y,
        minimum_seed_support=0.,quiet_below=.4) for relation,y in [('opening_rim',-.85),('opening_rim',.85),('support_shoulder_lintel',-.85)]]
    h3['steps'][0]['declaration']=fold(8,wf=320,we=320,wp=320)
    h3['steps'][2]['declaration']=fold(5,wf=450,we=-120,wp=350,w1=-2.2,w2=-5,w6=-1.2,w7=1.5)
    h3['steps'][1]['parameters']['direction_mode']='horizontal'
    h3['steps'][1]['parameters']['tangent_sign']=-1
    h3['intent']+=' Revision positions opening-rim assemblies before full X02 angular articulation; intersections remain permitted.'
    for recipe in (h2,h3):
        target=root.resolve('recipes/'+recipe['id']+'.json')
        if target.exists() and read(target)!=recipe:raise ValueError('Revision already declared differently.')
        write(target,recipe)
    write(root.resolve('revision_decisions.json'),[dict(id=r['id'],origin=r['revision_of'],
        observation=r['visual_observation'],source_images='renders/initial',recipe='recipes/'+r['id']+'.json') for r in (h2,h3)])
    print('Declared two targeted visual revisions.',flush=True)


def continue_canyon(root):
    directory=root.resolve('designs/H3_R1/attempt_001')
    summary=read(directory/'summary.json')
    if summary['reason']!='Mola cap reverses/collapses.' or summary['stages'][-1]['stage']!='S04':
        raise ValueError('Continuation is specific to the observed actual S04 inset failure.')
    r=deepcopy(summary['recipe']);r.update(id='H3_R2',revision_of='H3_R1',
        visual_observation='Actual revised canyon generates through S04. A selected thin RIDGE_SIDE cannot accept the requested Mola inset: cap reverses/collapses. Preflight actual local constructor compatibility and retain usable faces, without moving/repairing the folded mesh.')
    stage='S04';reference=root.reference(directory)
    assets={reference+'/'+stage+suffix:digest(read(directory/(stage+suffix))) for suffix in
        ('.json.gz','_lineage.json.gz','_signatures.json.gz','_networks.json','_operator.json.gz')}
    r['prepared_substrate']=dict(artifact=reference,stage=stage,assets=assets,
        reviewed_stage=dict(policy=dict(hard_stop=False)),source_case='H3_R1')
    r['steps']=r['steps'][4:];r['stage_index_base']=24
    write(root.resolve('recipes/H3_R2.json'),r)
    print('Declared H3_R2 from actual S04, preserving the stopped original.',flush=True)


def preflight_event(mesh,history,stage,selected,dll,routes=None):
    """Check the same existing constructor on small unchanged parent disks.

    This diagnoses a demonstrated local constructor failure. The bulk operation
    still owns all geometry/lineage; there is no remeshing or collision screen.
    """
    usable=[];failures=[]
    for f in selected:
        keys=mesh.face_vertices(f)
        disk=raw_mesh(dict(vertices=[dict(id=v,xyz=mesh.vertex_coordinates(v)) for v in keys],
            faces=[dict(id=f,vertices=keys)]))
        local_routes={(stage.id,f):routes[(stage.id,f)]} if routes else None
        try:
            vocabulary_event(disk,{f:history[f]},stage,selected_faces=[f],dll_path=str(dll),
                budget=ExecutionBudget(100,100,64),routes=local_routes,allow_large_taper=True)
            usable.append(f)
        except (ValueError,ArithmeticError) as e:
            failures.append(dict(face=f,actual_constructor_failure=str(e)))
    return usable,failures


def resource_budget(mesh, kind, count=0):
    m=windows_memory()
    if m['status']!='MEASURED': raise ValueError('Memory measurement unavailable.')
    estimated=(sum(len(mesh.face_vertices(f)) for f in mesh.faces()) if kind=='fold'
        else mesh.number_of_faces()+count*6)
    # Conservative mesh+lineage+placement metadata allowance, measured again
    # in the guarded child. It is not an inherited study face ceiling.
    reserved=estimated*16000
    available=m['available_bytes']
    if reserved>available*.55:
        raise MemoryError(f'Predicted {reserved} bytes exceeds 55% of available {available}; checkpoint retained.')
    ceiling=max(estimated+1000,int(available*.55/16000))
    return ExecutionBudget(ceiling,ceiling*2,64),dict(estimated_faces=estimated,
        estimated_working_bytes=reserved,available_bytes=available,
        allowance_bytes_per_face=16000,resource_derived_face_limit=ceiling)


def verify_frozen_inputs(root):
    identity=read(root.resolve('input_identity.json'))
    for row in identity['inputs']:
        path=root.resolve(row['file'])
        if not path.is_file() or file_hash(path)!=row['byte_sha256']:
            raise ValueError('Frozen input bytes changed: '+row['file'])
        if digest(read(path))!=row['canonical_sha256']:
            raise ValueError('Frozen input geometry/lineage changed: '+row['file'])
    return identity


def run_one(root, name, dll):
    input_identity=verify_frozen_inputs(root)
    recipe=read(root.resolve('recipes/'+name+'.json'))
    base=root.resolve('designs/'+name); attempts=sorted(base.glob('attempt_*'))
    for p in attempts:
        if (p/'summary.json').exists():
            s=read(p/'summary.json')
            unchanged=all((ROOT/n).exists() and file_hash(ROOT/n)==h for n,h in s.get('source',{}).get('source_files',{}).items())
            if s['status']=='SUCCESS' and s['recipe_sha256']==digest(recipe) and unchanged and all(file_hash(p/n)==h for n,h in s['exports'].items()):
                print(name,'verified export resume',flush=True); return
    directory=base/f'attempt_{len(attempts)+1:03d}'; directory.mkdir(parents=True,exist_ok=False)
    code=versions();code['source_files']['examples/hero_design_sprint.py']=file_hash(Path(__file__))
    for n,h in code['source_files'].items():
        snapshot=root.resolve('cache/source_snapshots/'+h+'/'+n)
        if not snapshot.exists():snapshot.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,snapshot)
    write(directory/'request.json',dict(recipe=recipe,source=code,baseline=BASELINE,
        input_identity=input_identity,HDMola_sha256=file_hash(dll)))
    mesh,source,history,events,cells,anchors,tracker=load(root,recipe['input'])
    original=digest(mesh_to_data(mesh)); router=CreaseRouter(mesh,source,history,cells,events)
    if recipe.get('prepared_substrate'):
        mesh,history,events,cells,anchors,tracker,networks=prepared_substrate(root,recipe['prepared_substrate'])
    else:
        networks=tuple(router.generate(spec,'network-'+str(i+1)) for i,spec in enumerate(recipe['networks']))
    center=router.center; del router
    records=[];start=perf_counter();failed=None;generation=0

    def retain(label,metadata,seconds=0.):
        nonlocal records
        geometry=mesh_to_data(mesh)
        if any(not isfinite(x) for v in geometry['vertices'] for x in v['xyz']):
            raise ValueError('Non-finite coordinates prevent further computation.')
        if not mesh.is_valid(): raise ValueError('Invalid connectivity prevents next operation.')
        gz_write(directory/(label+'.json.gz'),geometry)
        gz_write(directory/(label+'_lineage.json.gz'),dict(history=history,events=events,source_cells=cells,anchors=anchors))
        gz_write(directory/(label+'_signatures.json.gz'),tracker.to_data())
        write(directory/(label+'_networks.json'),[n.to_data() for n in networks])
        gz_write(directory/(label+'_operator.json.gz'),metadata)
        row=dict(stage=label,statistics=inspect_mesh(mesh),geometry_sha256=digest(geometry),
            operator_seconds=seconds,cumulative_seconds=perf_counter()-start,
            memory=windows_memory(),observation='Intersections/opening/topology flags diagnostic; no envelope clamp or repair.')
        records.append(row)
        write(directory/'summary.json',dict(status='RUNNING',recipe=recipe,recipe_sha256=digest(recipe),stages=records))
        print(name,label,mesh.number_of_faces(),round(row['cumulative_seconds'],2),flush=True)

    retain('INPUT',dict(routing=[n.to_data() for n in networks]))
    try:
        for index,step in enumerate(recipe['steps'],1):
            t=perf_counter()
            if step['kind']=='fold':
                budget,estimate=resource_budget(mesh,'fold')
                result=folded_crease_once(mesh,networks,step['declaration'],mode=recipe['mode'],budget=budget,current_generation=generation)
                parents={r['id']:[ParentRef(r['source_face'],1.)] for r in result.metadata['face_sources']}
                history=propagate_history(history,parents)
                cells={f:sorted({c for p in refs for c in cells[p.key]}) for f,refs in parents.items()}
                tracker.advance(parents,{})
                mesh=result.mesh;networks=result.networks;generation+=1
                anchors={v:anchors[v] for v in mesh.vertices() if v in anchors}
                metadata=dict(operator=result.metadata,resource_estimate=estimate)
                del result,parents
            else:
                selected,selection=choose_faces(mesh,source,history,networks,step,events)
                usable=[];unusable=[]
                for f in selected:
                    try:local_polygon(mesh,f);usable.append(f)
                    except ValueError as e:unusable.append(dict(face=f,failure=str(e)))
                selection.update(unusable_local_faces=unusable,actual_selected_ids=usable)
                if not usable:
                    raise ValueError('No computationally usable selected local polygons for '+step['id'])
                budget,estimate=resource_budget(mesh,'event',len(usable))
                stage=VocabularyStage(step['id'],step['operator'],step['parameters'],{})
                routes=None
                if stage.operator=='Roof':
                    edges=[e.vertices for n in networks for e in n.edges];routes={}
                    for f in usable:
                        mid=mesh.face_centroid(f)
                        edge=min(edges,key=lambda e:(dist(mid,[(mesh.vertex_coordinates(e[0])[a]+mesh.vertex_coordinates(e[1])[a])/2 for a in range(3)]),e))
                        tangent=unit([mesh.vertex_coordinates(edge[1])[a]-mesh.vertex_coordinates(edge[0])[a] for a in range(3)])
                        routes[(stage.id,f)]=dict(common_directional_basis=tangent,centerline=center[0],basis_policy='Closest actual declared current crease tangent, existing constructor-axis choice.')
                usable,constructor_failures=preflight_event(mesh,history,stage,usable,dll,routes)
                selection['actual_constructor_failures']=constructor_failures
                selection['actual_selected_ids']=usable
                write(directory/(f'S{index:02d}'+'_selection.json'),selection)
                if not usable:raise ValueError('All selected local polygons are unusable for the requested constructor: '+stage.id)
                result=vocabulary_event(mesh,history,stage,selected_faces=usable,dll_path=str(dll),
                    budget=budget,stage_index=index+recipe.get('stage_index_base',20),routes=routes,allow_large_taper=True)
                parents=result['lineage'].face_parents
                nets,network_report=terminal_networks(mesh,result['mesh'],networks,result['corner_parents'])
                cells={f:sorted({c for p in refs for c in cells[p.key]}) for f,refs in parents.items()}
                anchors={v:anchors[p] for v,p in result['corner_parents'].items() if p in anchors}
                tracker.advance(parents,dict(events=result['events']))
                mesh=result['mesh'];history=result['history'];events.extend(result['events']);networks=nets
                metadata=dict(declaration=step,selection=selection,events=result['events'],backend=result['backend'],
                    terminal_crease_contract=network_report,resource_estimate=estimate)
                del result,parents
            retain(f'S{index:02d}',metadata,perf_counter()-t)
            del metadata;gc.collect()
    except (ValueError,ArithmeticError,MemoryError) as error:
        failed=str(error)
    geometry=mesh_to_data(mesh);gz_write(directory/'terminal.json.gz',geometry)
    gz_write(directory/'terminal_lineage.json.gz',dict(history=history,events=events,source_cells=cells,anchors=anchors))
    gz_write(directory/'terminal_signatures.json.gz',tracker.to_data())
    write(directory/'terminal_networks.json',[n.to_data() for n in networks])
    save_mesh(mesh,directory/(name+'.obj'))
    # Validate the real on-disk export, with exact XYZ and oriented connectivity.
    imported=load_mesh(directory/(name+'.obj'))
    export_exact=mesh.to_vertices_and_faces()==imported.to_vertices_and_faces()
    if not export_exact: raise ValueError('On-disk OBJ reimport differs from actual generated mesh.')
    write(directory/'summary.json',dict(status='TECHNICAL_STOP' if failed else 'SUCCESS',reason=failed,
        recipe=recipe,recipe_sha256=digest(recipe),source=code,stages=records,
        statistics=inspect_mesh(mesh),runtime_seconds=perf_counter()-start,
        terminal_canonical_sha256=digest(geometry),input_canonical_sha256=original,
        actual_OBJ_reimport_exact=export_exact,
        exports={n:file_hash(directory/n) for n in [name+'.obj','terminal.json.gz','terminal_lineage.json.gz','terminal_signatures.json.gz','terminal_networks.json']},
        ornament=depth_diagnostics(history,events),display_processing='None; original XYZ/connectivity.',
        lineage_scope='Positive construction ancestry and branch signatures. Affected Mola derivatives do not retain crease semantics; fragments record surviving unchanged edges.'))
    print(name,'TECHNICAL_STOP' if failed else 'SUCCESS',failed or '',flush=True)


def guarded(args, logs, *, worker_script=None):
    logs.mkdir(parents=True,exist_ok=True);start=perf_counter();peak=0;reason=None;seen={}
    initial=windows_memory();limit=min(12*1024**3,int(initial['available_bytes']*.65))
    with (logs/'stdout.txt').open('w') as out,(logs/'stderr.txt').open('w') as err:
        child=subprocess.Popen([sys.executable,'-E','-s',str(worker_script or Path(__file__)),*args],cwd=ROOT,
            env=worker_environment(),stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
        birth=process_birth(int(child._handle));seen[child.pid]=birth
        try:
            while child.poll() is None:
                family,unknown=scoped_family(child.pid,birth);seen.update(family)
                m=windows_memory();total=m.get('combined_resident_bytes',0)
                for pid,b in family.items():
                    if birth_of_pid(pid)==b:
                        total+=max(0,windows_memory(pid).get('combined_resident_bytes',0)-m.get('combined_resident_bytes',0))
                peak=max(peak,total)
                if total>limit:reason='Measured process memory exceeds resource-derived guard.'
                if m.get('available_bytes',0)<2*1024**3:reason='Measured available RAM below 2 GiB.'
                if unknown:reason='Cannot measure a live descendant resource identity.'
                if reason:terminate_tree(child.pid,seen);child.wait(timeout=15);break
                sleep(.5)
        finally:
            if child.poll() is None:terminate_tree(child.pid,seen);child.wait(timeout=15)
    result=dict(exit_code=child.returncode,resource_stop=reason,seconds=perf_counter()-start,
        sampled_peak_tree_plus_driver_bytes=peak,memory_guard_bytes=limit,
        guard='Measured RAM only; no elapsed-time/contact/historical-face-cap stop.')
    write(logs/'process.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--reference-root',type=Path,default=Path('E:/CHESHIRE_DATA/task23'))
    p.add_argument('--initialize',action='store_true');p.add_argument('--revise',action='store_true');p.add_argument('--continue-canyon',action='store_true');p.add_argument('--run',nargs='+')
    p.add_argument('--worker');p.add_argument('--dll',type=Path)
    a=p.parse_args();root=ArtifactRoot(a.output_root)
    if a.initialize:initialize(root,a.reference_root)
    if a.revise:revise(root)
    if a.continue_canyon:continue_canyon(root)
    if a.worker:run_one(root,a.worker,a.dll)
    elif a.run:
        for name in a.run:
            if shutil.disk_usage(root.path).free<4*1024**3:raise ValueError('Insufficient disk for retained checkpoints.')
            result=guarded(['--output-root',str(root.path),'--worker',name,'--dll',str(a.dll)],root.resolve('logs/'+name))
            print(name,result,flush=True)
            if result['exit_code']:raise ValueError('Worker stopped; retained checkpoints and logs identify the failure.')
