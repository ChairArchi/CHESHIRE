"""One-factor post-pocket CC versus exact-fan and pocket-support-memory study."""
import argparse,copy,gc,hashlib,json,shutil,sys
from pathlib import Path
from time import perf_counter
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'tools'),str(R/'examples')]
from cheshire.reference_subdivision import ArrayMesh,metrics
from cheshire.freedom_nested import pocket,exact_split,cc_split,physical,centres
from task29_search import save_mesh
from task36_contacts import contacts
from task32_validation import embedding
from task35_analyze import radial_cut,child_valleys,envelope_retention
from hero_design_sprint import guarded,windows_memory
from astra_evaluate import render,cut_picture
ROOT=Path('E:/CHESHIRE_DATA/astra_freedom/nested_probe')
START=Path('E:/CHESHIRE_DATA/astra_research/recovered_probe/P01_RECOVERED_MACRO/K03_TASK28_TRANSFER/G1')
def write(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def run(spec,root):
    import pyrender,trimesh
    from PIL import Image
    with np.load(START/'quad_state.npz') as z:initial=ArrayMesh(*(z[k].copy() for k in ['xyz','faces','classes','rest','anchors']),int(z['generation']))
    renderer=pyrender.OffscreenRenderer(600,600);finalpics=[];cases=[]
    try:
        for case in spec['cases']:
            job=root/case['id'];job.mkdir();write(job/'recipe.json',dict(**case,source=str(START),parent_sha256=sha(START/'quad_state.npz')))
            m=copy.deepcopy(initial);support=None;role_history={};history=[];previous=START;previous_profiles={};pictures=[]
            for g in range(1,8):
                started=perf_counter();state={};meta={};preflight={}
                if g>1:
                    factor=5 if g%2==0 else 4;forecast=512*1024**2+len(m.faces)*factor*4*2000;memory=windows_memory()
                    preflight=dict(forecast_bytes=forecast,memory=memory)
                    if forecast>min(12*1024**3,.55*memory['available_bytes']):raise MemoryError('Next native forecast exceeds measured reserve.')
                    if g%2==0:
                        params=dict(ratio=.48,depth=.7,selection=0) if g==2 else dict(ratio=.65,depth=1.3,selection=.3)
                        m,meta,state,support=pocket(m,parent_support=support,memory=case['memory'],**params)
                    else:m,meta,state,support=(cc_split if case['refine']=='cc' else exact_split)(m,support)
                    parent=state['parent_face']
                    for ancestor in role_history:role_history[ancestor]=role_history[ancestor][parent]
                    if g%2==0:role_history[g]=state['output_cap_rim_role'].copy()
                native=physical(m);stage=job/f'G{g}';save_mesh(stage,native,meta,state,previous)
                np.savez_compressed(stage/'quad_state.npz',xyz=m.xyz,faces=m.faces,classes=m.classes,rest=m.rest,anchors=m.anchors,generation=m.generation,
                    physical_centres=centres(m),parent_support=np.array([]) if support is None else support,
                    **{'G'+str(k)+'_cap_rim_role':v for k,v in role_history.items()})
                check=contacts(native,cap=128,interval=True,include_shared=True);emb=embedding(native);data=metrics(native)
                invalid=check['transverse_contacts'] or emb['degenerate_triangles'] or emb['invalid_vertex_links']
                model=trimesh.Trimesh(vertices=native.xyz,faces=native.faces[:,:3],process=False);raw={};cuts=[];profiles={}
                for z in [500,1000,1500,2000,2500,3000,3500]:
                    lines,ids=trimesh.intersections.mesh_plane(model,[0,0,1],[0,0,z+.12345],return_faces=True)
                    profile,coverage=radial_cut(lines);valid=not any(coverage.values());label='Z'+str(z)
                    raw[label]=lines;raw[label+'_triangle_ids']=ids
                    row=dict(z=z,coverage=coverage,radial_valid=valid)
                    if valid and z in previous_profiles:
                        row['child_valleys']=child_valleys(previous_profiles[z],profile);row['parent_envelope_retention']=envelope_retention(previous_profiles[z],profile)
                        row['profile_max_change']=float(np.max(abs(profile-previous_profiles[z])))
                    if valid:profiles[z]=profile
                    cuts.append(row)
                for label,normal in [('XZ',[0,1,0]),('YZ',[1,0,0])]:
                    lines,ids=trimesh.intersections.mesh_plane(model,normal,[0,0,0],return_faces=True);raw[label]=lines;raw[label+'_triangle_ids']=ids
                np.savez_compressed(stage/'cuts.npz',**raw);cut_picture(raw,case['id']+'_G'+str(g),stage)
                record=dict(generation=g,stage=str(stage),metadata=meta,preflight=preflight,contacts=check,embedding=emb,metrics=data,cuts=cuts,
                    seconds=perf_counter()-started,status='EXPERIMENTAL_INVALID' if invalid else 'CHECKS_PASSED',native_sha256=sha(stage/'mesh.npz'))
                if 'effective_support' in state:
                    ids=state['selected_input_faces'];record['pocket_scales']=dict(selected=len(ids),current=np.quantile(state['current_support'][ids],[0,.5,1]).tolist(),
                        parent=np.quantile(state['parent_support'][ids],[0,.5,1]).tolist(),effective=np.quantile(state['effective_support'][ids],[0,.5,1]).tolist(),
                        displacement=np.quantile(state['requested_normal_distance'][ids],[0,.5,1]).tolist())
                write(stage/'validation.json',record);history.append(record);previous=stage;previous_profiles=profiles
                dest=stage/'renders';dest.mkdir();pics=render(native,dest,case['id']+'_G'+str(g),renderer,[0,0,2000],6500,' INVALID' if invalid else '')
                pictures.extend(pics)
                if g==7:finalpics.extend(pics)
                print(case['id'],g,len(native.faces),record['status'],'eligibleCuts',sum(c['radial_valid'] for c in cuts),flush=True)
            sheet=Image.new('RGB',(1800,600*7),'white')
            for i,pic in enumerate(pictures):sheet.paste(pic,((i%3)*600,(i//3)*600))
            sheet.save(job/'progression.png');write(job/'history.json',history);cases.append(dict(id=case['id'],history=history));gc.collect()
    finally:renderer.delete()
    sheet=Image.new('RGB',(1800,600*len(cases)),'white')
    for i,pic in enumerate(finalpics):sheet.paste(pic,((i%3)*600,(i//3)*600))
    sheet.save(root/'comparison.png');write(root/'summary.json',cases)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
    spec=json.loads(a.spec.read_text());root=ROOT/a.tag
    if a.worker:run(spec,root)
    else:
        root.mkdir(parents=True,exist_ok=False);write(root/'spec.json',spec);identity={}
        for rel in ['src/cheshire/freedom_nested.py','tools/freedom_nested_probe.py','src/cheshire/freedom_legacy.py','src/cheshire/astra_dual.py','src/cheshire/reference_subdivision.py','tools/astra_evaluate.py']:
            d=root/'source'/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,d);identity[rel]=sha(d)
        write(root/'source_identity.json',identity)
        result=guarded(['--spec',str(root/'spec.json'),'--tag',a.tag,'--worker'],root/'logs',worker_script=Path(__file__))
        write(root/'execution.json',result);print(json.dumps(result,indent=2))
        if result['exit_code']:raise SystemExit(result['exit_code'])
