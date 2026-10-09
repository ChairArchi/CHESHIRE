"""Bounded recovered macro-generation experiment. Invalid geometry is retained.

Exact Task29 source/input replay is distinguished from transfers to a column
and from Task28's legacy isolated placement convention. No repair or export.
"""
import argparse,copy,json,sys,shutil,hashlib
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from cheshire.reference_subdivision import ArrayMesh,subdivide,fields,metrics,GLOBAL_SCALE,LOCAL_INCIDENT_SCALE
from cheshire.dual_subdivision import doo_sabin
from cheshire.task36_growth import carrier
from cheshire.astra_dual import native
from task29_search import save_mesh,load_mesh
from task36_contacts import contacts
from hero_design_sprint import guarded,windows_memory

ROOT=Path('E:/CHESHIRE_DATA/astra_research/recovered_probe')
SOURCE29=Path('E:/CHESHIRE_DATA/task30/definitions/retained_canonical_pipeline.json')
SOURCE28=REPO/'studies/task28/definitions/generation_weight_schedule.json'
def write(p,x):p.write_text(json.dumps(x,indent=2),encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def run(root):
    original=json.loads(SOURCE29.read_text())['original_definition']
    task28=json.loads(SOURCE28.read_text())['definition']['rows']
    memory=windows_memory();forecast=512*1024**2+40*4**6*1800
    if forecast>min(12*1024**3,.55*memory['available_bytes']):raise MemoryError('Insufficient measured RAM reserve.')
    write(root/'preflight.json',dict(memory=memory,forecast_bytes=forecast,maximum_depth=6))
    for source in [SOURCE29,SOURCE28]:shutil.copy2(source,root/source.name)
    sources={}
    for rel in ['tools/astra_recovered_probe.py','src/cheshire/reference_subdivision.py','src/cheshire/astra_dual.py','src/cheshire/task36_growth.py','tools/task36_contacts.py','tools/task36_triangle_interval.py','tools/native/Task36Bounds.cs','examples/hero_design_sprint.py']:
        dest=root/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/rel,dest);sources[rel]=sha(dest)
    write(root/'source_identity.json',sources);all_records=[]
    for name in ['K00_EXACT_CUBE','K01_COLUMN_LOCKED','K02_COLUMN_UNLOCKED','K03_TASK28_TRANSFER']:
        job=root/name;job.mkdir();is28=name.startswith('K03');rows=task28 if is28 else original['rows'][:6]
        intrinsic=None if is28 else copy.deepcopy(original['intrinsic'])
        if name.startswith('K02'):intrinsic.pop('lock_threshold')
        mesh=load_mesh('E:/CHESHIRE_DATA/task29/lead/G0') if name.startswith('K00') else carrier()
        write(job/'recipe.json',dict(rows=rows,intrinsic=intrinsic,scale='ABS/GLOBAL original units through coupled engine' if is28 else LOCAL_INCIDENT_SCALE,
            source29_sha256=sha(SOURCE29),source28_sha256=sha(SOURCE28),input='Original saved Task29 cube' if name.startswith('K00') else 'Neutral1000x1000x4000 square column2vertical cells',
            validity_policy='Continue invalid stages for diagnostic observation; never exchange-valid or fabricated output. No repair.'))
        history=[];parent=None;ever_invalid=False
        for g in range(len(rows)+1):
            start=perf_counter();state={};meta={}
            if g:
                row=copy.deepcopy(rows[g-1]);mode=GLOBAL_SCALE if is28 else LOCAL_INCIDENT_SCALE
                if is28 and row['offset_units']=='ABSOLUTE':
                    scale=float(fields(mesh)['lengths'].mean())
                    for key in ['wf','we','wp']:row['weights'][key]/=scale
                mesh,meta,state=subdivide(mesh,row,scale_mode=mode,intrinsic=intrinsic)
            physical=native(mesh);stage=job/f'G{g}';save_mesh(stage,physical,meta,state,parent)
            np.savez_compressed(stage/'quad_state.npz',xyz=mesh.xyz,faces=mesh.faces,classes=mesh.classes,rest=mesh.rest,anchors=mesh.anchors,generation=mesh.generation)
            check=contacts(physical,cap=1024,interval=True,include_shared=True)
            data=metrics(physical);ever_invalid|=bool(check['transverse_contacts'] or data['zero_area_faces'])
            rec=dict(generation=g,stage=str(stage),metrics=data,contacts=check,invalid_lineage=ever_invalid,seconds=perf_counter()-start,
                eq4_eligible=meta.get('eq4_eligible'),eq4_fallback=meta.get('eq4_fallback'),locked_vertex_count=meta.get('locked_vertex_count'))
            if name.startswith('K00'):
                old=load_mesh(f'E:/CHESHIRE_DATA/task29/lead/G{g}')
                rec['exact_saved_operator_arrays']={k:bool(np.array_equal(getattr(mesh,k),getattr(old,k))) for k in ['xyz','faces','classes','rest','anchors']}
                if not all(rec['exact_saved_operator_arrays'].values()):raise AssertionError('Recovered historical Task29 replay mismatch.')
            history.append(rec);write(stage/'validation.json',rec);parent=stage
            print(name,'G'+str(g),'contacts',check['transverse_contacts'],'invalid lineage',ever_invalid,'extent',data['extent'],flush=True)
        write(job/'history.json',history);all_records.append(dict(candidate=name,history=history))
    write(root/'summary.json',all_records)
    render(root,all_records[1:])


def continue_macro(root):
    seed=ROOT/'P01_RECOVERED_MACRO/K03_TASK28_TRANSFER/G3'
    with np.load(seed/'quad_state.npz') as z:
        initial=ArrayMesh(*(z[k].copy() for k in ['xyz','faces','classes','rest','anchors']),int(z['generation']))
    rows=json.loads(SOURCE28.read_text())['definition']['rows']
    ds_source=Path('E:/CHESHIRE_DATA/task30/definitions/task30_variant_definitions.json')
    variants=json.loads(ds_source.read_text());groups=variants[6]['steps'][3]['groups']
    source_dir=root/'source';source_dir.mkdir()
    for p in [Path(__file__),SOURCE28,ds_source]:shutil.copy2(p,source_dir/p.name)
    write(root/'provenance.json',dict(seed=str(seed),seed_operator_sha256=sha(seed/'quad_state.npz'),seed_native_sha256=sha(seed/'mesh.npz'),
        task28_sha256=sha(SOURCE28),task30_ds_sha256=sha(ds_source),ds_json_pointer='/6/steps/3/groups',ds_source_variant=variants[6].get('id')))
    memory=windows_memory();forecast=512*1024**2+40*4**6*1800
    if forecast>min(12*1024**3,.55*memory['available_bytes']):raise MemoryError('Insufficient measured RAM reserve.')
    write(root/'preflight.json',dict(memory=memory,forecast_bytes=forecast))
    cases={'T00_ORIGINAL_ZERO':[rows[3],rows[4],rows[4]],'T01_C11B':[rows[1]]*3,
        'T02_T28_G3':[rows[2]]*3,'T03_ORIGIN_DS':['DS']*3}
    all_records=[]
    for name,schedule in cases.items():
        mesh=copy.deepcopy(initial);roles=None;job=root/name;job.mkdir();history=[];parent=seed;invalid=False
        write(job/'recipe.json',dict(seed=str(seed),schedule=schedule,groups=groups if name=='T03_ORIGIN_DS' else None,
            ds_weights=dict(w1=.6,wf=.03),cc_scale=GLOBAL_SCALE,ds_scale=LOCAL_INCIDENT_SCALE,
            note='Task30 documented modest origin groups on new current DS faces; first DS has UNKNOWN origins and uses uniform row.'))
        for g in range(3,7):
            start=perf_counter();meta={};state={}
            if g>3:
                row=schedule[g-4]
                if row=='DS':mesh,roles,meta,state=doo_sabin(mesh,dict(w1=.6,wf=.03),face_roles=roles,groups=groups)
                else:mesh,meta,state=subdivide(mesh,row,scale_mode=GLOBAL_SCALE)
            physical=native(mesh);stage=job/f'G{g}';save_mesh(stage,physical,meta,state,parent)
            np.savez_compressed(stage/'quad_state.npz',xyz=mesh.xyz,faces=mesh.faces,classes=mesh.classes,rest=mesh.rest,anchors=mesh.anchors,generation=mesh.generation,
                roles=np.array([]) if roles is None else roles)
            check=contacts(physical,cap=1024,interval=True,include_shared=True);data=metrics(physical)
            invalid|=bool(check['transverse_contacts'] or data['zero_area_faces'])
            rec=dict(generation=g,stage=str(stage),metrics=data,contacts=check,invalid_lineage=invalid,seconds=perf_counter()-start)
            if name=='T00_ORIGINAL_ZERO' and g in [4,5]:
                with np.load(ROOT/f'P01_RECOVERED_MACRO/K03_TASK28_TRANSFER/G{g}/quad_state.npz') as z:
                    rec['same_original_operator_arrays']={k:bool(np.array_equal(getattr(mesh,k),z[k])) for k in ['xyz','faces','classes','rest','anchors']}
                    assert all(rec['same_original_operator_arrays'].values())
            write(stage/'validation.json',rec);history.append(rec);parent=stage
            print(name,'G'+str(g),'contacts',check['transverse_contacts'],'extent',data['extent'],flush=True)
        write(job/'history.json',history);all_records.append(dict(candidate=name,history=history))
    write(root/'summary.json',all_records);render(root,all_records)


def render(root,records):
    import pyrender,trimesh
    from PIL import Image,ImageDraw
    from progressive_gate_views import pose
    from cheshire.task32_morphology import triangles
    dest=root/'renders';dest.mkdir();size=600;width=6000.;target=[0,0,2000]
    renderer=pyrender.OffscreenRenderer(size,size);images=[];manifest=[]
    try:
        for case in records:
            for g in ([0,1,len(case['history'])-1] if case['history'][0]['generation']>0 else [1,3,len(case['history'])-1]):
                record=case['history'][g];stage=Path(record['stage']);mesh=load_mesh(stage)
                for view,angles in [('front',(0,0)),('oblique',(28,22))]:
                    label=case['candidate']+'_'+stage.name+'_'+view;model=trimesh.Trimesh(vertices=mesh.xyz,faces=triangles(mesh),process=False)
                    mat=pyrender.MetallicRoughnessMaterial(baseColorFactor=[.65,.65,.63,1],roughnessFactor=.9,doubleSided=True)
                    scene=pyrender.Scene(bg_color=[.96,.96,.95,1],ambient_light=[.08]*3)
                    scene.add(pyrender.Mesh.from_trimesh(model,material=mat,smooth=False))
                    cam=pose(*angles,target);scene.add(pyrender.OrthographicCamera(xmag=width/2,ymag=width/2,znear=1,zfar=30000),pose=cam)
                    for a,b,intensity in [(-65,25,2.),(65,10,.18)]:scene.add(pyrender.DirectionalLight(color=np.ones(3),intensity=intensity),pose=pose(a,b,target))
                    color,_=renderer.render(scene);image=Image.fromarray(color)
                    ImageDraw.Draw(image).text((8,8),label+(' INVALID LINEAGE' if record['invalid_lineage'] else ''),fill=(0,0,0))
                    path=dest/(label+'.png');image.save(path);images.append(image)
                    projected=(mesh.xyz-np.array(target))@cam[:3,:2]
                    manifest.append(dict(label=label,stage=str(stage),mesh_sha256=sha(stage/'mesh.npz'),image_sha256=sha(path),angles=angles,target=target,width=width,
                        invalid_lineage=record['invalid_lineage'],outside_frame=int((abs(projected)>width/2).any(1).sum())))
    finally:renderer.delete()
    sheet=Image.new('RGB',(size*6,size*len(records)),(255,255,255))
    for i,image in enumerate(images):sheet.paste(image,((i%6)*size,(i//6)*size))
    sheet.save(dest/'comparison.png');write(dest/'manifest.json',manifest)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);parser.add_argument('--worker',action='store_true')
    parser.add_argument('--continue-macro',action='store_true');args=parser.parse_args()
    root=ROOT/args.tag
    if args.worker:(continue_macro if args.continue_macro else run)(root)
    else:
        root.mkdir(parents=True,exist_ok=False)
        result=guarded(['--tag',args.tag,'--worker']+(['--continue-macro'] if args.continue_macro else []),root/'logs',worker_script=Path(__file__))
        print(json.dumps(result,indent=2))
