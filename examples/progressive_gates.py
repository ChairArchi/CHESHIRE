"""Task26 isolated whole-gate workers and actual saved generations."""
import argparse
import gc
import json
import re
from pathlib import Path
import shutil
import sys
from time import perf_counter

REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
from cross_cell_crease_study import read,write,file_hash,gz_write,raw_mesh,mesh_to_data,versions
from generational_folding import budget_for,verify_obj
from hero_design_sprint import guarded
from cheshire import save_mesh,inspect_mesh
from cheshire.fold_continuation import fold_state,save_state,load_state
from cheshire.progressive_gates import gate_input,restore_gate,advance_gate,symmetry,physical_support
from cheshire.crease_routing import CreaseRouter
from cheshire.creases import make_network

BASELINE='b4000cf85bc0768821976bab4b454ca35b8ccca3'


def declaration(**weights):
    return dict(weights=weights,execution='POINTWISE_EXISTING_STENCILS',u_map={},unknown_u=0.,
        units='Offsets absolute original units; dimensionless interpolation. Region size in input-material units.')


def initialize(root):
    root.mkdir(parents=True,exist_ok=True)
    rows=[]
    for section,profile in [('RECT',False),('ROUND',False),('ROUND',True)]:
        mesh,state=gate_input(section,profile);name=state['input']['name'];d=root/'inputs'/name
        if d.exists():raise ValueError('Preserve existing input; initialize only a fresh task26 inputs directory.')
        d.mkdir(parents=True);gz_write(d/'geometry.json.gz',mesh_to_data(mesh));save_state(d/'state.json.gz',state)
        save_mesh(mesh,d/(name+'.obj'));check=verify_obj(mesh,d/(name+'.obj'))
        write(d/'summary.json',dict(status='SUCCESS',input=state['input'],statistics=inspect_mesh(mesh),
            symmetry=symmetry(mesh,state),OBJ_validation=check,geometry_sha256=file_hash(d/'geometry.json.gz')))
        rows.append(dict(id=name,geometry=file_hash(d/'geometry.json.gz'),state=file_hash(d/'state.json.gz')))
    a=read(root/'inputs/INPUT_RECT/geometry.json.gz');b=read(root/'inputs/INPUT_ROUND/geometry.json.gz')
    write(root/'input_identity.json',dict(baseline=BASELINE,inputs=rows,identical_vertex_IDs=True,
        identical_oriented_faces=a['faces']==b['faces'],vertices=len(a['vertices']),faces=len(a['faces']),
        parts_identical=True,changed='Cross-section geometry only. Both share 9 height/joint stations, 8 perimeter points and 16 triangular cap faces.',
        section='RECT 8 corner/mid-edge perimeter samples; ROUND 8 ellipse samples, support width/depth 900/500.',
        profile='Separate ROUND_PROFILE: z=1300 scale .72, z=2600 scale 1.12; input waist/bulge, not new folds.',
        original_frame=True,physical_units='UNRESOLVED'))
    fold=declaration(wf=70.,we=-55.,wp=35.,w1=-2.2,w2=-3.4)
    upper=dict(kind='UPPER',quiet_below=400,transition=900)
    recipes=[]
    for name,source,blocks in [('RECT_EARLY','INPUT_RECT',[fold,{},{}]),
                               ('RECT_DELAYED','INPUT_RECT',[{},{},fold]),
                               ('ROUND_EARLY','INPUT_ROUND',[fold,{},{}]),
                               ('PROFILE_CC','INPUT_ROUND_PROFILE',[{},{}])]:
        parent=source
        for g,block in enumerate(blocks,1):
            id=name+'_G'+str(g)
            recipes.append(dict(id=id,parent=parent,declaration=block or declaration(),support=upper,
                trajectory=name,question='Matched full-gate fold timing/section comparison; same fold block and total CC depth.'))
            parent=id
    d=root/'recipes';d.mkdir(exist_ok=True)
    for r in recipes:write(d/(r['id']+'.json'),r)


def parent_directory(root,name):
    if name.startswith('INPUT_'):return root/'inputs'/name
    if name.startswith('PROBE_'):return root/'probes'/name
    for d in reversed(sorted((root/'designs'/name).glob('attempt_*'))):
        if (d/'summary.json').exists() and read(d/'summary.json')['status']=='SUCCESS':return d
    raise ValueError('No successful parent checkpoint: '+name)


def profile_probe(root):
    """Actual isolated profiled round support; ordinary CC, no new folding."""
    from compas.datastructures import Mesh
    from cheshire.creases import crease_subdivide_once
    from cheshire.execution import ExecutionBudget
    from cheshire.progressive_gates import PLANE_X,PLANE_Y
    from math import sin,cos,pi
    vertices={r*8+j:[PLANE_X-1550+450*scale*cos(j*pi/4),PLANE_Y+250*scale*sin(j*pi/4),z]
        for r,(z,scale) in enumerate([(0,1.),(1300,.72),(2600,1.12)]) for j in range(8)}
    vertices.update({24:[PLANE_X-1550,PLANE_Y,0],25:[PLANE_X-1550,PLANE_Y,2600]})
    faces={r*8+j:[r*8+j,r*8+(j+1)%8,(r+1)*8+(j+1)%8,(r+1)*8+j] for r in range(2) for j in range(8)}
    for j in range(8):
        faces[16+j]=[24,(j+1)%8,j];faces[24+j]=[25,16+j,16+(j+1)%8]
    mesh=Mesh.from_vertices_and_faces(vertices,faces)
    for g in range(4):
        name='PROBE_ROUND_COLUMN_PROFILE_G'+str(g);d=root/'probes'/name
        if d.exists():raise ValueError('Preserve existing profile probe.')
        d.mkdir(parents=True);gz_write(d/'geometry.json.gz',mesh_to_data(mesh));save_mesh(mesh,d/(name+'.obj'))
        write(d/'summary.json',dict(status='SUCCESS',statistics=inspect_mesh(mesh),generation=g,
            parent='PROBE_ROUND_COLUMN_PROFILE_G'+str(g-1) if g else None,
            operation='Crease-inactive ordinary full closed column CC' if g else '8-sided ellipse, height scales 1/.72/1.12',
            question='Input radius profile survives subdivision; waist/bulge are inherited, not newly generated folds.',
            frame=dict(center_X=PLANE_X-1550,center_Y=PLANE_Y,Z_up=True,global_gate_plane_not_used=True),
            OBJ_validation=verify_obj(mesh,d/(name+'.obj'))))
        if g<3:mesh=crease_subdivide_once(mesh,(),budget=ExecutionBudget(3000,3000,None),current_generation=g).mesh


def calibrate(root):
    """Freeze a conservative measured total-peak envelope for this task only."""
    target=root/'analysis/resource_calibration.json'
    if target.exists():raise ValueError('Preserve frozen calibration; use a fresh reproduction root.')
    groups={};records=[]
    for p in (root/'logs').glob('*/process.json'):
        process=read(p);match=re.fullmatch(r'(.+)_attempt_(\d+)',p.parent.name)
        name=match[1] if match else p.parent.name;attempt=match[2] if match else '001'
        summary=root/'designs'/name/('attempt_'+attempt)/'summary.json'
        if process['exit_code'] or not summary.exists():continue
        row=read(summary)
        if row['status']!='SUCCESS':continue
        faces=row['statistics']['face_count'];peak=process['sampled_peak_tree_plus_driver_bytes']
        groups[faces]=max(groups.get(faces,0),peak)
        records.append(dict(id=name,faces=faces,peak_bytes=peak,process_path=p.relative_to(root).as_posix(),process_sha256=file_hash(p)))
    if len(groups)<2:raise ValueError('At least two actual completed resolution levels needed.')
    a,b=sorted(groups)[-2:];slope=(groups[b]-groups[a])/(b-a)
    if slope<=0:raise ValueError('Insufficient positive measured growth evidence.')
    fixed=max(0,max(peak-slope*f for f,peak in groups.items()))
    write(target,dict(schema='TASK26_FIXED_PLUS_FACE_PEAK_ENVELOPE_V1',measurements=records,group_maxima=groups,
        slope_bytes_per_face=slope,fixed_bytes=fixed,margin=.35,largest_measured_faces=b,
        rationale='Separate fixed Python/driver overhead from growth. Envelope every measured completed level, +35% margin increasing beyond 4x extrapolation; forecast and unchanged live guard, not a guarantee.'))


def add_routes(mesh,state,policy):
    # Test the existing independent N6 junction selection on NEW input ancestry.
    source,_=gate_input(state['input']['section'],state['input']['profile'])
    router=CreaseRouter(mesh,source,state['history'],state['source_cells'])
    spec=dict(generator='N6',junction='Y',junction_xz=[-.32,.85],
        arm_targets=[[-.43,.94],[-.12,.89],[-.36,.62]],target_y_ratio=-.85,
        minimum_seed_support=.1,minimum_target_support=.1,sharpness=4.,
        turn_cost=1.4,source_cost=.8,front_cost=.8,dihedral_cost=.25,cell_reward=.15,profile='CONSTANT')
    left=router.generate(spec,'shoulder_L')
    rspec={**spec,'junction_xz':[-spec['junction_xz'][0],spec['junction_xz'][1]],
        'arm_targets':[[-x,z] for x,z in spec['arm_targets']]}
    if policy=='INDEPENDENT':
        right=router.generate(rspec,'shoulder_R')
    else:
        vp=state['gate']['vertex_pair']
        routing=left.to_data()['routing']
        routing={**routing,'paths':[[vp[v] for v in path] for path in routing.get('paths',[])],
            'semantic_seed_vertices':[vp[v] for v in routing['semantic_seed_vertices']],
            'profile_distance_origin':vp[routing['profile_distance_origin']],
            'reflection_of':'shoulder_L','plane_X':state['input']['frame']['X'],
            'direction_rule':'(dx,dy,dz)->(-dx,dy,dz); outward normal offsets retain sign.'}
        right=make_network(mesh,'shoulder_R',[tuple(vp[v] for v in e.vertices) for e in left.edges],4.,
            {**rspec,'paired_reflection':True},cells=state['source_cells'],history=state['history'],routing=routing)
    state['networks']=[left.to_data(),right.to_data()]
    state['gate']['selection_policy']=policy
    state['gate']['routes']=[n.to_data() for n in (left,right)]
    vp=state['gate']['vertex_pair']
    lhs={tuple(sorted(vp[v] for v in e.vertices)) for e in left.edges};rhs={e.vertices for e in right.edges}
    return dict(policy=policy,reflected_edge_symmetric_difference=len(lhs^rhs),
        left=left.to_data(),right=right.to_data(),first_check='Actual current route edges before folding; no historical H1 audit.')


def correct_early_route_metadata(state):
    """Preserve trials, explicitly correct aliased birth metadata on continuation.

    Early paired trial edges were correct, but its right seed metadata aliased
    the left seeds. Constant sharpness and the actual edge graph are unchanged.
    Original vertex IDs persist as CC corners, so constructive current pairing
    also reflects their birth IDs. No coordinate matching or geometry change.
    """
    lookup={n['network_id']:n for n in state['networks']}
    if not {'shoulder_L','shoulder_R'}<=set(lookup):return
    left,right=lookup['shoulder_L'],lookup['shoulder_R']
    if not right['seed_rule'].get('paired_reflection') or right['seed_rule']['junction_xz'][0]>0:return
    vp=state['gate']['vertex_pair'];lr=left['routing'];rr=right['routing']
    right['seed_rule']={**right['seed_rule'],'junction_xz':[-left['seed_rule']['junction_xz'][0],left['seed_rule']['junction_xz'][1]],
        'arm_targets':[[-x,z] for x,z in left['seed_rule']['arm_targets']]}
    rr.update(semantic_seed_vertices=[vp[v] for v in lr['semantic_seed_vertices']],
        profile_distance_origin=vp[lr['profile_distance_origin']])
    state['gate']['routes']=[n for n in state['networks']]
    state['gate']['metadata_corrections']=state['gate'].get('metadata_corrections',[])+[
        dict(kind='RIGHT_BIRTH_SEED_METADATA',generation=state['generation']['absolute_cc'],
            geometry_change=False,reason='Actual reflected edges were correct; correct right target/seed/profile-origin metadata inherited from preserved early paired trials.')]


def run_one(root,name):
    recipe=read(root/'recipes'/(name+'.json'));base=root/'designs'/name;base.mkdir(parents=True,exist_ok=True)
    d=base/('attempt_'+str(len(list(base.glob('attempt_*')))+1).zfill(3));d.mkdir()
    source=parent_directory(root,recipe['parent']);start=perf_counter();times={}
    code=versions();code['task26_sources']={n:file_hash(REPO/n) for n in
        ['examples/progressive_gates.py','src/cheshire/progressive_gates.py','src/cheshire/fold_continuation.py','src/cheshire/crease_folding.py']}
    write(d/'request.json',dict(baseline=BASELINE,recipe=recipe,code=code,
        parent=dict(path=str(source),geometry_sha256=file_hash(source/'geometry.json.gz'),state_sha256=file_hash(source/'state.json.gz'))))
    try:
        mesh=raw_mesh(read(source/'geometry.json.gz'));state=restore_gate(load_state(source/'state.json.gz'))
        correct_early_route_metadata(state)
        if recipe.get('routes'):
            routes=add_routes(mesh,state,recipe['routes']);write(d/'route_comparison.json',routes)
        if recipe.get('disable_creases'):state['networks']=[]
        support=physical_support(mesh,state,recipe['support']);active=[mesh.vertex_coordinates(v) for v,a in support.items() if a>.1]
        resolved=dict(support=recipe['support'],input_active_vertices=len(active),
            active_bbox=[max(p[i] for p in active)-min(p[i] for p in active) for i in range(3)] if active else [],
            physical_reference='Transported original cage XYZ with bilinear CC structural origins; not graph hop count or changing deformed bounding box.',
            architecture_displacement_reference=900,
            offsets_over_support_width={k:w/900 for k,w in recipe['declaration']['weights'].items() if k in ('wf','we','wp')})
        expected_faces=sum(len(mesh.face_vertices(f)) for f in mesh.faces())
        calibration=root/recipe.get('resource_calibration','analysis/resource_calibration.json');predicted=None
        rationale='Task25 measured 5700 bytes/output face conservative margin retained, +300 for Task26 material/pair maps; actual whole-process guard retained.'
        if recipe.get('use_task26_calibration'):
            model=read(calibration)
            if model.get('exact_output_faces') and expected_faces!=model['exact_output_faces']:
                raise ValueError('Exact-level memory calibration cannot forecast another resolution/topology.')
            for row in model['measurements']:
                if file_hash(root/row['process_path'])!=row['process_sha256']:raise ValueError('Measured memory identity changed.')
            margin=model['margin']*max(1.,expected_faces/(4*model['largest_measured_faces']))
            predicted=int((model['fixed_bytes']+model['slope_bytes_per_face']*expected_faces)*(1+margin))
            rationale=dict(model_path=str(calibration),sha256=file_hash(calibration),margin=margin,
                scope='Same whole-gate CC/pointwise operator and Task26 paired/material state; max envelope of measured process-tree peaks including driver, fixed overhead separated. No relaxed live guard.',
                total_prediction=predicted)
        budget,forecast=budget_for(mesh,d,{**recipe,'resource_bytes_per_face':6000,
            'resource_rationale':rationale},predicted_total_bytes=predicted)
        t=perf_counter();result,next_state=fold_state(mesh,state,recipe['declaration'],budget=budget,point_support=support)
        next_state=advance_gate(mesh,result,state,next_state);times['operation_and_pairing']=perf_counter()-t
        next_state['gate']['resolved_support']=resolved
        next_state['gate']['completed_recipes']=state['gate'].get('completed_recipes',[])+[recipe]
        next_state['input']['geometry_sha256']=state['input'].get('geometry_sha256',file_hash(root/'inputs'/state['input']['name']/'geometry.json.gz'))
        next_state['source_identity']=code
        report=symmetry(result.mesh,next_state)
        gz_write(d/'operator.json.gz',result.metadata);mesh=result.mesh
        del result,state,support;gc.collect()
        t=perf_counter();gz_write(d/'geometry.json.gz',mesh_to_data(mesh));save_state(d/'state.json.gz',next_state);times['checkpoint_write']=perf_counter()-t
        t=perf_counter();obj=d/(name+'.obj');save_mesh(mesh,obj);times['OBJ_write']=perf_counter()-t
        t=perf_counter();check=verify_obj(mesh,obj);times['OBJ_reread']=perf_counter()-t
        write(d/'summary.json',dict(status='SUCCESS',recipe=recipe,parent=str(source),statistics=inspect_mesh(mesh),
            generation=next_state['generation'],symmetry=report,resource_forecast=forecast,resolved_support=resolved,
            times=times,elapsed_seconds=perf_counter()-start,OBJ_validation=check,
            artifacts={p.name:dict(bytes=p.stat().st_size,sha256=file_hash(p)) for p in d.iterdir() if p.is_file()}))
        print(name,'SUCCESS',mesh.number_of_faces(),'faces',round(perf_counter()-start,2),'s',flush=True)
    except Exception as exc:
        write(d/'summary.json',dict(status='TECHNICAL_STOP',reason=str(exc),recipe=recipe,last_preserved_parent=str(source),elapsed_seconds=perf_counter()-start))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--profile-probe',action='store_true')
    p.add_argument('--calibrate',action='store_true')
    p.add_argument('--initialize',action='store_true');p.add_argument('--run',nargs='+');p.add_argument('--worker')
    a=p.parse_args();root=a.output_root.resolve()
    if a.initialize:initialize(root)
    if a.profile_probe:profile_probe(root)
    if a.calibrate:calibrate(root)
    if a.worker:run_one(root,a.worker)
    elif a.run:
        for name in a.run:
            attempt=len(list((root/'designs'/name).glob('attempt_*')))+1
            result=guarded(['--output-root',str(root),'--worker',name],root/'logs'/(name+'_attempt_'+str(attempt).zfill(3)),worker_script=Path(__file__))
            print(name,result,flush=True)
            if result['exit_code']:raise ValueError('Actual worker stopped; preserve checkpoint/logs.')
