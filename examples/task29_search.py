"""Task29 deterministic staged experiment. Saved checkpoints are the geometry.

Run --prepare, --matrix, --round-a, then --continue definitions after visual
selection. Guarded workers measure RAM; no historical face-count cap.
"""
import argparse,gc,gzip,hashlib,json,shutil,sys
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
from cheshire.reference_subdivision import (ArrayMesh,cube,subdivide,metrics,topology,fields,
    WEIGHTS,GLOBAL_SCALE,LOCAL_INCIDENT_SCALE,REFERENCE_COUPLED,LEGACY_ISOLATED)
from cross_cell_crease_study import read,write,file_hash
from hero_design_sprint import guarded

ROOT=Path('E:/CHESHIRE_DATA/task29')
BASELINE='a9e456fcc7711ae5920457c49890bc28aa045f1d'


def row(weights,u_map=None,source=None):
    return dict(weights={k:float(weights.get(k,0)) for k in WEIGHTS},u_map=u_map or {},unknown_u=0.,source=source,
                units='wf/we/wp dimensionless ratios times declared current scale; all others dimensionless')


def mix(a,b,t,name):
    r=row({k:a['weights'][k]*(1-t)+b['weights'][k]*t for k in WEIGHTS},source=name)
    r['u_map']={k:a.get('u_map',{}).get(k,0)*(1-t)+b.get('u_map',{}).get(k,0)*t for k in set(a.get('u_map',{}))|set(b.get('u_map',{}))}
    return r


def scaled(a,factor,name=None):
    return row({k:v*factor for k,v in a['weights'].items()},a['u_map'],name or f'{a["source"]} x {factor}')


def save_mesh(d,m,meta=None,state=None,parent=None):
    d.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(d/'mesh.npz',xyz=m.xyz,faces=m.faces,classes=m.classes,rest=m.rest,anchors=m.anchors,generation=m.generation)
    if state:np.savez_compressed(d/'operator_state.npz',**state)
    summary=metrics(m)
    summary.update(metadata=meta or {},parent=str(parent) if parent else None,mesh_sha256=file_hash(d/'mesh.npz'))
    write(d/'summary.json',summary)
    return summary


def load_mesh(d):
    d=Path(d)
    with np.load(d if d.suffix=='.npz' else d/'mesh.npz') as z:
        return ArrayMesh(*(z[k].copy() for k in ('xyz','faces','classes','rest','anchors')),int(z['generation']))


def legacy_step(m,r,origins):
    from compas.datastructures import Mesh
    from cheshire.sharp_subdivision import sharp_subdivide_once
    from cheshire.execution import ExecutionBudget
    cage=Mesh.from_vertices_and_faces(m.xyz.tolist(),[[int(v) for v in f if v>=0] for f in m.faces])
    lengths=[cage.edge_length(e) for e in cage.edges()];scale=float(np.mean(lengths))
    w={k:v*(scale if k in ('wf','we','wp') else 1) for k,v in r['weights'].items()}
    res=sharp_subdivide_once(cage,w,u_map=r['u_map'],unknown_u=r['unknown_u'],origin_lineage=origins,
        budget=ExecutionBudget(1000000,1000000,None),current_generation=m.generation)
    ids=list(res.mesh.vertices());remap={v:j for j,v in enumerate(ids)}
    xyz=np.array([res.mesh.vertex_coordinates(v) for v in ids]);faces=np.array([[remap[v] for v in res.mesh.face_vertices(f)] for f in res.mesh.faces()])
    kinds={'VERTEX_DERIVED':0,'EDGE_DERIVED':1,'FACE_DERIVED':2}
    classes=np.array([kinds[res.origin_lineage[v]['class']] for v in ids],np.int8)
    rest=np.array([sum(m.rest[v]*a for v,a in res.sampling_parents[k]) for k in ids])
    amap={s['id']:s['source_face'] for s in res.metadata['face_sources']}
    anchors=np.array([m.anchors[amap[f]] for f in res.mesh.faces()])
    if m.generation<3:anchors[:,m.generation]=np.arange(len(faces))
    # COMPAS vertex IDs are contiguous here; face IDs are remapped for next call.
    neworig={remap[v]:dict(res.origin_lineage[v]) for v in ids}
    out=ArrayMesh(xyz,faces,classes,rest,anchors,m.generation+1)
    meta=dict(implementation=LEGACY_ISOLATED,scale=GLOBAL_SCALE,declared=r,resolved_weights=w,
              eq4_eligible=res.metadata['later_generation_face_stencil']['eligible_faces'])
    return out,meta,neworig


def prepare():
    seeds=read(REPO/'studies/task28/definitions/recovered_subdivision_seeds.json');items=read(REPO/'studies/task28/analysis/previous_success_inventory.json')['items']
    sources=ROOT/'analysis/recovered_sources';sources.mkdir(parents=True,exist_ok=True)
    for item in items:
        p=REPO/item['recipe_source'].replace('\\','/')
        actual=read(p) # actual saved recipes, not reports
        if file_hash(p)!=item['recipe_source_sha256']:raise ValueError('Historical recipe changed: '+str(p))
        shutil.copy2(p,sources/(f'T{item["task"]}_'+p.name))
        item['source_re_read_verified_sha256']=file_hash(p)
        item['implementation_path']='sharp_subdivide_once / generational_subdivide_once / weighted_subdivide_once; see source recipe composition'
        item['visual_behavior']=item.pop('assessment')
        item['known_failure']='Historical gate/profile/support or Mola topology is omitted; numerical seed transfer is not evidence of the same shape.'
    p=REPO/'studies/task28/definitions/generation_weight_schedule.json'
    if not p.exists():p=Path('E:/CHESHIRE_DATA/task28/definitions/generation_weight_schedule.json')
    actual=read(p);shutil.copy2(p,sources/'Task28_generation_weight_schedule.json')
    items.append(dict(task=28,commit=BASELINE,name='P4_C033_ZERO',generation='G1..5',exact_saved_schedule=actual,
        recipe_source=str(p),source_re_read_verified_sha256=file_hash(p),implementation_path='examples/hansmeyer_benchmark.py -> sharp_subdivide_once',
        visual_behavior='Macro G1, secondary G2, smaller pleats G3; G4 suppresses and G5 all-zero loses finer articulation.',known_failure='Late zero relaxation; cell-associated detail; PARTIAL.'))
    # Include actual Task25 flow regimes omitted from the previous inventory.
    for p in sorted((REPO/'studies/task25/recipes').glob('H1_FLOW*json')):
        d=read(p);shutil.copy2(p,sources/('Task25_'+p.name))
        items.append(dict(task=25,commit='b4000cf85bc0768821976bab4b454ca35b8ccca3',name=p.stem,generation=d.get('generation','saved recipe'),
            exact_saved_recipe=d,recipe_source=str(p),source_re_read_verified_sha256=file_hash(p),implementation_path='Task25 pointwise existing stencils',
            visual_behavior='Directional continuation scouting; retained as exact source, not assumed successful on cube.',known_failure='Spatial gate supports are not reused.'))
    write(ROOT/'analysis/seed_parameter_inventory.json',dict(items=items,seeds=seeds,verified_before_new_sampling=True))
    lines=['# Task20–28 exact seed recovery','Actual recipe bytes were re-read and SHA256 checked before sampling.','']
    for i in items:lines.extend([f'## Task{i["task"]}: {i["name"]}',f'Commit: {i["commit"]}; generation: {i["generation"]}.',f'Source: {i["recipe_source"]}',i['visual_behavior'],i['known_failure'],'```json',json.dumps(i.get('exact_subdivision_weights',i.get('exact_saved_schedule',i.get('exact_saved_recipe'))),indent=2),'```'])
    (ROOT/'analysis/seed_parameter_inventory.md').write_text('\n\n'.join(lines),encoding='utf-8')
    # Absolute H1 offsets become ratios against the explicitly declared 1000-unit seed cube.
    normalized={}
    for name,s in seeds.items():
        w=s['weights'].copy()
        if s['offset_units']=='ABSOLUTE':
            for k in ('wf','we','wp'):w[k]/=1000.
        normalized[name]=row(w,s['u_map'],name)
        normalized[name]['normalization']='Absolute historical offsets / initial cube edge 1000; later applied to current declared scale.' if s['offset_units']=='ABSOLUTE' else 'Historical dimensionless ratio unchanged.'
    h=normalized['H1'];h0=row({**h['weights'],'w6':0,'w7':0},source='Task28 H1 ablation')
    b=normalized['C11B'];g=normalized['GENTLE']
    g3=row({**{k:v*.7 for k,v in b['weights'].items()},'w3':-.6,'w4':.35},source='Exact Task28 G3 ratio row')
    normalized.update(H1_NO_ATTR=h0,T28_G3=g3)
    write(ROOT/'definitions/recovered_numeric_seeds.json',normalized)
    write(ROOT/'definitions/cube_specimen.json',dict(side=1000,vertices=cube().xyz.tolist(),faces=cube().faces.tolist(),units='Unresolved project units; no display normalization',closed=True))
    save_mesh(ROOT/'input/G0',cube())
    write(ROOT/'definitions/mechanism_modes.json',dict(M0=[LEGACY_ISOLATED,GLOBAL_SCALE],M1=[REFERENCE_COUPLED,GLOBAL_SCALE],M2=[REFERENCE_COUPLED,LOCAL_INCIDENT_SCALE],
        reference_vertex_midpoints='Original endpoint midpoints, justified by Fig2 stencil and neutral CC; new face points feed Eq2 and Eq3.',
        local_scale='Face arithmetic mean current perimeter edge length; edge mean of two incident face scales; vertex mean of incident face scales.',
        attraction_order='Eq10 completes face points before Eq2/3. Eq11 completes edges but Eq3 retains original endpoint midpoints.'))
    matrix=[h0,b,g3,normalized['CURVE'],g3]
    for mode,scale in [(LEGACY_ISOLATED,GLOBAL_SCALE),(REFERENCE_COUPLED,GLOBAL_SCALE),(REFERENCE_COUPLED,LOCAL_INCIDENT_SCALE)]:
        name=['M0','M1','M2'][[(LEGACY_ISOLATED,GLOBAL_SCALE),(REFERENCE_COUPLED,GLOBAL_SCALE),(REFERENCE_COUPLED,LOCAL_INCIDENT_SCALE)].index((mode,scale))]
        write(ROOT/'definitions/matrix'/f'{name}.json',dict(id=name,mode=mode,scale=scale,rows=matrix))
    print('Prepared seed inventory',len(items),'historical rows; simple cube',flush=True)


def stage(d,parent,r,mode,scale,intrinsic=None,topology_rule=None):
    m=load_mesh(parent);started=perf_counter()
    if mode==LEGACY_ISOLATED:
        origins=read(Path(parent)/'legacy_origins.json') if m.generation else {}
        origins={int(k):v for k,v in origins.items()}
        out,meta,origins=legacy_step(m,r,origins);state=None
    else:out,meta,state=subdivide(m,r,scale_mode=scale,intrinsic=intrinsic)
    meta['declared_row']=r
    if topology_rule and out.generation==topology_rule['generation']:
        from task29_topology import weld
        # Retain the real unmerged result even when the proposed weld is invalid.
        pre=out
        out,log=weld(out,topology_rule)
        d.mkdir(parents=True,exist_ok=False)
        np.savez_compressed(d/'pre_weld.npz',xyz=pre.xyz,faces=pre.faces,classes=pre.classes,rest=pre.rest,anchors=pre.anchors,generation=pre.generation)
        write(d/'topology_log.json',log)
        if out is None:raise ValueError('Rejected explicit topology proposal: '+log['invalid_reason'])
        # save_mesh creates the directory; preserve proposal files in a sibling
        # evidence directory instead of allowing overwrite semantics globally.
        evidence=d.parent/(d.name+'_weld_evidence');d.rename(evidence)
        meta['topology']=log;meta['implementation']='REFERENCE_COUPLED_LOCAL_TOPOLOGY'
    meta['parent_mesh_sha256']=file_hash(Path(parent)/'mesh.npz')
    summary=save_mesh(d,out,meta,state,parent)
    if mode==LEGACY_ISOLATED:write(d/'legacy_origins.json',origins)
    summary['seconds']=perf_counter()-started;write(d/'summary.json',summary)
    print(d.parent.name,'G'+str(out.generation),len(out.faces),round(summary['seconds'],3),'s',flush=True)
    return summary


def run_definition(definition,category):
    name=definition['id'];base=ROOT/'candidates'/category/name
    write(ROOT/'definitions'/category/f'{name}.json',definition)
    parent=Path(definition.get('parent',ROOT/'input/G0'))
    rows=definition['rows'];start=load_mesh(parent).generation
    summaries=[]
    for g in range(start+1,len(rows)+1):
        d=base/f'G{g}'
        if d.exists():raise ValueError('Preserve actual candidates: '+str(d))
        s=stage(d,parent,rows[g-1],definition.get('mode',REFERENCE_COUPLED),definition.get('scale',LOCAL_INCIDENT_SCALE),definition.get('intrinsic'),definition.get('topology'))
        summaries.append(s);parent=d;gc.collect()
    return dict(id=name,category=category,definition=definition,stages=summaries,final=str(parent))


def matrix():
    result=[run_definition(read(ROOT/'definitions/matrix'/f'M{i}.json'),'matrix') for i in range(3)]
    # IDs/topology differ only for legacy. New modes have the same exact compact ordering.
    comparisons=[]
    for g in range(1,6):
        m1=load_mesh(ROOT/f'candidates/matrix/M1/G{g}');m2=load_mesh(ROOT/f'candidates/matrix/M2/G{g}')
        comparisons.append(dict(generation=g,M1_vs_M2_RMS=float(np.sqrt(((m1.xyz-m2.xyz)**2).sum(1).mean()))))
    write(ROOT/'analysis/mechanism_matrix_metrics.json',dict(results=result,paired_local_scale_differences=comparisons,controlled_variables='Identical cube, full nine-weight rows, u-map, generations, normals and rendering. Legacy scalar summation order preserved.'))


def broad():
    s=read(ROOT/'definitions/recovered_numeric_seeds.json')
    macros=[s['H1_NO_ATTR'],s['C11A'],s['C11B'],s['C26'],s['H1'],s['H1B'],
            mix(s['H1_NO_ATTR'],s['C11A'],.5,'H1/C11A midpoint'),scaled(s['H1_NO_ATTR'],1.25,'H1 1.25')]
    secondary=[s['C11B'],s['CURVE'],s['GENTLE'],s['C26'],s['H1B'],
               mix(s['C11B'],s['CURVE'],.5,'C11B/CURVE midpoint'),scaled(s['C11B'],1.3),
               row({**s['C11B']['weights'],'wf':-.16,'we':.05,'wp':-.045},source='C11B offset-sign reversal')]
    nested=[s['T28_G3'],s['CURVE'],s['AMP'],mix(s['C26'],s['GENTLE'],.5,'C26/GENTLE midpoint')]
    definitions=[]
    for a,ma in enumerate(macros):
        for b,se in enumerate(secondary):
            for c,ns in enumerate(nested):definitions.append(dict(id=f'A{a*32+b*4+c:03}',mode=REFERENCE_COUPLED,scale=LOCAL_INCIDENT_SCALE,rows=[ma,se,ns]))
    write(ROOT/'definitions/broad_search_space.json',dict(macros=macros,secondary=secondary,nested=nested,count=len(definitions),sampling='Deterministic 8 x 8 x 4 seed-derived nonstationary Cartesian schedules; no vertex noise.'))
    result=[run_definition(d,'round_A') for d in definitions]
    write(ROOT/'analysis/broad_search_log.json',dict(round_A=result,requested_count=256,actual_count=len(result)))


def continuing(path,category):
    definitions=read(path)['definitions'];result=[]
    for d in definitions:
        try: result.append(run_definition(d,category))
        except ValueError as e:
            if category!='topology':raise
            result.append(dict(id=d['id'],category=category,definition=d,status='REJECTED_EXPLICITLY',reason=str(e)))
            print('Rejected topology',d['id'],str(e),flush=True)
    write(ROOT/'analysis'/f'{category}_log.json',dict(results=result,definitions=len(definitions)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--matrix',action='store_true');p.add_argument('--round-a',action='store_true');p.add_argument('--continue-file',type=Path);p.add_argument('--category');p.add_argument('--worker',action='store_true');p.add_argument('--tag',required=True)
    a=p.parse_args()
    if not a.worker:
        args=[v for v in sys.argv[1:] if v!='--worker']+['--worker']
        r=guarded(args,ROOT/'logs'/a.tag,worker_script=Path(__file__));print(r,flush=True);sys.exit(r['exit_code'])
    if a.prepare:prepare()
    if a.matrix:matrix()
    if a.round_a:broad()
    if a.continue_file:continuing(a.continue_file,a.category)
