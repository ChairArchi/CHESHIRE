"""Competing unbounded-geometry study with bounded measured resource use."""
import argparse,copy,json,sys,shutil,hashlib
from pathlib import Path
from time import perf_counter
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'tools'),str(R/'examples')]
from cheshire.reference_subdivision import ArrayMesh,metrics
from cheshire.freedom_legacy import step,pocket
from cheshire.astra_dual import native
from task29_search import save_mesh
from task36_contacts import contacts
from task32_validation import embedding
from hero_design_sprint import guarded,windows_memory
from astra_evaluate import render
ROOT=Path('E:/CHESHIRE_DATA/astra_freedom/legacy_probe')
SOURCE=Path('E:/CHESHIRE_DATA/astra_research/recovered_probe/P01_RECOVERED_MACRO/K03_TASK28_TRANSFER/G3')
def write(p,x):p.write_text(json.dumps(x,indent=2),encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def trace_lineage(source,dest):
    """Actual cap/rim ancestry, raw cuts and guarded finite radial evidence."""
    import trimesh,pyrender
    from PIL import Image
    from task29_search import load_mesh
    from task35_analyze import radial_cut,child_valleys
    dest.mkdir(parents=True,exist_ok=False);all_records=[];pictures=[]
    renderer=pyrender.OffscreenRenderer(550,550)
    try:
        for name in ['Q00_ROUND','Q02_CHILD_RESPONSE']:
            job=source/name;root_role=None;root_face=None;second_role=None;previous_profiles={};history=[]
            for g in range(2,7):
                stage=job/f'G{g}';state=dict(np.load(stage/'operator_state.npz'));m=load_mesh(stage)
                parent=state['parent_face'] if 'parent_face' in state else state['source_parent_face']
                if g==2:root_role=state['output_cap_rim_role'];root_face=parent
                else:root_role=root_role[parent];root_face=root_face[parent]
                if g==4:second_role=state['output_cap_rim_role']
                elif g>4:second_role=second_role[parent]
                model=trimesh.Trimesh(vertices=m.xyz,faces=m.faces[:,:3],process=False);raw={};cut_records=[];profiles={}
                for z in [500,1000,1500,2000,2500,3000,3500]:
                    lines,ids=trimesh.intersections.mesh_plane(model,[0,0,1],[0,0,z+.12345],return_faces=True)
                    profile,coverage=radial_cut(lines);label='Z'+str(z)
                    raw[label+'_segments']=lines;raw[label+'_triangle_ids']=ids;raw[label+'_G2_cap_rim']=root_role[ids//4]
                    if second_role is not None:raw[label+'_G4_cap_rim']=second_role[ids//4]
                    valid=not any(coverage.values());row=dict(z=z,segments=len(lines),coverage=coverage,radial_valid=valid)
                    if valid and z in previous_profiles:row['finite_world_child_valleys']=child_valleys(previous_profiles[z],profile)
                    else:row['finite_world_child_valleys']=None
                    if valid:profiles[z]=profile
                    cut_records.append(row)
                np.savez_compressed(dest/(name+f'_G{g}_lineage_cuts.npz'),**raw,operator_G2_role=root_role,operator_G1_face=root_face,
                    operator_G4_role=np.array([]) if second_role is None else second_role)
                row=dict(generation=g,stage=str(stage),native_sha256=sha(stage/'mesh.npz'),cuts=cut_records,
                    inherited_G2_role_counts={str(role):int((root_role==role).sum()) for role in np.unique(root_role)})
                if 'selected_input_faces' in state:
                    selected=state['selected_input_faces'];support=state['current_support'][selected];contrast=state['current_signed_contrast'][selected];distance=state['requested_normal_distance'][selected]
                    row['pocket']=dict(selected=len(selected),support_quantiles=np.quantile(support,[0,.25,.5,.75,1]).tolist(),signed_descriptor_quantiles=np.quantile(contrast,[0,.25,.5,.75,1]).tolist(),
                        actual_requested_distance_quantiles=np.quantile(distance,[0,.25,.5,.75,1]).tolist(),inward=int((distance<0).sum()),outward=int((distance>0).sum()),selection_threshold=float(state['selection_threshold']))
                    if g==4:
                        with np.load(dest/(name+'_G3_lineage_cuts.npz')) as prior:parentroles=prior['operator_G2_role']
                        row['pocket']['selected_parent_G2_roles']={str(role):int((parentroles[selected]==role).sum()) for role in np.unique(parentroles)}
                history.append(row);previous_profiles=profiles
                if name=='Q02_CHILD_RESPONSE' and g in [2,4,6]:
                    for role,label in [(0,'G2_CAP_DESCENDANTS'),(1,'G2_RIM_DESCENDANTS')]:
                        select=np.repeat(root_role==role,4)
                        subset=ArrayMesh(m.xyz,m.faces[select],m.classes,m.rest,m.anchors[select],g)
                        pictures.extend(render(subset,dest,name+f'_G{g}_'+label,renderer,[0,0,2000],6500,' SUBSET / INVALID WHOLE'))
            all_records.append(dict(id=name,history=history))
    finally:renderer.delete()
    sheet=Image.new('RGB',(550*6,550*3),'white')
    for i,im in enumerate(pictures):sheet.paste(im,((i%6)*550,(i//6)*550))
    sheet.save(dest/'Q02_CAP_RIM_LINEAGE.png')
    write(dest/'lineage.json',dict(records=all_records,roles={'-1':'untouched','0':'new inset cap','1':'new connecting rim'},
        interpretation='Actual material face ancestry; not proof of geometric containment. Pocket distance uses current support, not transported ancestor depth. Multi-hit radial sections are ineligible for child-valley counts; raw segments retained. Subset renders are incomplete surfaces with identical camera and coordinates.'))


def verify_selected(source,dest):
    """Exact fresh replay and raw actual sections; no costly planar graph audit."""
    import trimesh
    from scipy.spatial import cKDTree
    spec=json.loads((source/'spec.json').read_text());start_path=Path(spec.get('start',str(SOURCE)))
    with np.load(start_path/'quad_state.npz') as z:initial=ArrayMesh(*(z[k].copy() for k in ['xyz','faces','classes','rest','anchors']),int(z['generation']))
    dest.mkdir(parents=True,exist_ok=False);records=[]
    for case in spec['cases']:
        if case['id'] not in ['Q00_ROUND','Q02_CHILD_RESPONSE','Q03_MATCHED_UNSIGNED']:continue
        mesh=copy.deepcopy(initial);memory=None;comparisons=[]
        for row in case['steps']:
            if row.get('op','cc')=='pocket':mesh,meta,state,memory=pocket(mesh,ancestor_scale=memory,**{k:v for k,v in row.items() if k!='op'})
            else:mesh,meta,state,memory=step(mesh,row['weights'],ancestor_scale=memory,memory=row['memory'])
            stage=source/case['id']/f'G{mesh.generation}'
            with np.load(stage/'quad_state.npz') as z:
                exact={k:bool(np.array_equal(getattr(mesh,k),z[k])) for k in ['xyz','faces','classes','rest','anchors']}
                exact['ancestor_scale']=bool(np.array_equal(memory,z['ancestor_scale']))
            if not all(exact.values()):raise AssertionError('Exact regeneration failed.')
            comparisons.append(dict(generation=mesh.generation,exact_arrays=exact))
        tri=native(mesh);model=trimesh.Trimesh(vertices=tri.xyz,faces=tri.faces[:,:3],process=False);raw={}
        planes=[('Z'+str(z),[0,0,z+.12345],[0,0,1]) for z in [500,1000,2000,3000,3500]]+[('XZ',[0,0,0],[0,1,0]),('YZ',[0,0,0],[1,0,0])]
        for label,origin,normal in planes:
            segments,ids=trimesh.intersections.mesh_plane(model,normal,origin,return_faces=True)
            raw[label+'_segments']=segments;raw[label+'_triangle_ids']=ids
        np.savez_compressed(dest/(case['id']+'_cuts.npz'),**raw)
        tree=cKDTree(tri.xyz);sym={name:float(tree.query(tri.xyz*np.array(sign))[0].max()) for name,sign in [('X',[-1,1,1]),('Y',[1,-1,1])]}
        records.append(dict(id=case['id'],source=str(stage),native_sha256=sha(stage/'mesh.npz'),reproduction=comparisons,
            raw_planes=[dict(label=l,origin=o,normal=n) for l,o,n in planes],symmetry_nearest=sym,
            components=int(model.body_count),watertight=bool(model.is_watertight),winding_consistent=bool(model.is_winding_consistent),
            caution='Known transverse-intersecting diagnostic. Raw sections are not certified clean grooves or a continuous ridge network.'))
    write(dest/'verification.json',records)


def run(spec,root):
    import pyrender
    from PIL import Image
    start_path=Path(spec.get('start',str(SOURCE)))
    with np.load(start_path/'quad_state.npz') as z:initial=ArrayMesh(*(z[k].copy() for k in ['xyz','faces','classes','rest','anchors']),int(z['generation']))
    renderer=pyrender.OffscreenRenderer(650,650);pictures=[];summary=[]
    try:
        for case in spec['cases']:
            job=root/case['id'];job.mkdir();write(job/'recipe.json',dict(**case,parent=str(start_path),parent_sha256=sha(start_path/'quad_state.npz')))
            mesh=copy.deepcopy(initial);memory=None;history=[];previous=start_path
            for i,row in enumerate([None]+case['steps']):
                started=perf_counter();meta={};state={}
                if row:
                    if row.get('op','cc')=='pocket':mesh,meta,state,memory=pocket(mesh,ancestor_scale=memory,**{k:v for k,v in row.items() if k!='op'})
                    else:mesh,meta,state,memory=step(mesh,row['weights'],ancestor_scale=memory,memory=row['memory'])
                stage=job/f'G{mesh.generation}';tri=native(mesh)
                save_mesh(stage,tri,meta,state,previous)
                np.savez_compressed(stage/'quad_state.npz',xyz=mesh.xyz,faces=mesh.faces,classes=mesh.classes,rest=mesh.rest,anchors=mesh.anchors,generation=mesh.generation,
                    ancestor_scale=np.array([]) if memory is None else memory)
                check=contacts(tri,cap=128,interval=True,include_shared=True);emb=embedding(tri)
                invalid=check['transverse_contacts'] or emb['degenerate_triangles'] or emb['invalid_vertex_links']
                record=dict(generation=mesh.generation,stage=str(stage),contacts=check,embedding=emb,metrics=metrics(tri),seconds=perf_counter()-started,
                    status='EXPERIMENTAL_INVALID' if invalid else 'CHECKS_PASSED',native_sha256=sha(stage/'mesh.npz'))
                write(stage/'validation.json',record);history.append(record);previous=stage
                print(case['id'],mesh.generation,record['status'],record['metrics']['extent'],flush=True)
                if i in [0,1,len(case['steps'])]:
                    dest=stage/'renders';dest.mkdir();label=case['id']+'_G'+str(mesh.generation)
                    pictures.extend(render(tri,dest,label,renderer,[0,0,2000],spec.get('width',6500),' INVALID' if invalid else ''))
            write(job/'history.json',history);summary.append(dict(id=case['id'],history=history))
    finally:renderer.delete()
    sheet=Image.new('RGB',(650*9,650*len(spec['cases'])),'white')
    for i,im in enumerate(pictures):sheet.paste(im,((i%9)*650,(i//9)*650))
    sheet.save(root/'comparison.png');write(root/'summary.json',summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true')
    p.add_argument('--verify-source',type=Path);p.add_argument('--trace-source',type=Path);a=p.parse_args()
    spec=json.loads(a.spec.read_text());root=ROOT/a.tag
    if a.worker:
        if a.trace_source:trace_lineage(a.trace_source,root/'lineage_evidence')
        elif a.verify_source:verify_selected(a.verify_source,root/'selected_verification')
        else:run(spec,root)
    else:
        with np.load(Path(spec.get('start',str(SOURCE)))/'quad_state.npz') as z:n=len(z['faces'])
        factor=max(np.prod([5 if row.get('op')=='pocket' else 4 for row in c['steps']]) for c in spec['cases'])
        forecast=512*1024**2+int(n*factor*4*2000)
        memory=windows_memory()
        if forecast>min(12*1024**3,.55*memory['available_bytes']):raise MemoryError('Forecast exceeds measured RAM reserve.')
        root.mkdir(parents=True,exist_ok=False);write(root/'spec.json',spec);write(root/'preflight.json',dict(forecast_bytes=forecast,memory=memory))
        files=['tools/freedom_legacy_probe.py','src/cheshire/freedom_legacy.py','src/cheshire/reference_subdivision.py','src/cheshire/astra_dual.py','tools/astra_evaluate.py']
        identity={}
        for rel in files:
            dst=root/'source'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,dst);identity[rel]=sha(dst)
        write(root/'source_identity.json',identity)
        args=['--spec',str(root/'spec.json'),'--tag',a.tag,'--worker']+(['--verify-source',str(a.verify_source)] if a.verify_source else [])+(['--trace-source',str(a.trace_source)] if a.trace_source else [])
        result=guarded(args,root/'logs',worker_script=Path(__file__))
        write(root/'execution.json',result);print(json.dumps(result,indent=2))
        if result['exit_code']:raise SystemExit(result['exit_code'])
