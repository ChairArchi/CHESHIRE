"""Fresh bounded two-round connected-patch study; preserves invalid geometry."""
import argparse,sys,json,shutil,hashlib
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from cheshire.freedom_patch import step,connected_step
from cheshire.reference_subdivision import metrics
from task29_search import load_mesh,save_mesh
from task36_contacts import contacts
from hero_design_sprint import guarded,windows_memory
from astra_evaluate import render
ROOT=Path('E:/CHESHIRE_DATA/astra_freedom/patch_probe')
SEED=Path('E:/CHESHIRE_DATA/astra_research/recovered_probe/P01_RECOVERED_MACRO/K03_TASK28_TRANSFER/G3')
def write(p,x):p.write_text(json.dumps(x,indent=2),encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(root,round_id):
 import pyrender
 from PIL import Image
 cases=({'P00_ZERO':dict(angle=0),'P01_CURRENT':dict(angle=1.1),'P02_REST':dict(angle=1.1,source='rest')} if round_id==1 else {'P03_TRANSVERSE':dict(angle=1.1,direction='transverse'),'P04_STRONG':dict(angle=1.7),'P05_CONSTANT':dict(angle=1.1,feedback=False)})
 if round_id==3:cases={'P06_CONNECTED':dict(angle=1.1,radius=350.),'P07_CONNECTED_TRANSVERSE':dict(angle=1.1,radius=350.,direction='transverse'),'P08_CONNECTED_REST':dict(angle=1.1,radius=350.,source='rest')}
 if round_id==5:cases={'P09_ZERO_G7':dict(angle=0.,radius=350.,seed_length_floor=52.5),'P10_FIXED350_G7':dict(angle=1.1,radius=350.,seed_length_floor=52.5),'P11_RADIUS220_G7':dict(angle=1.1,radius=220.,seed_length_floor=52.5),'P12_RADIUS140_G7':dict(angle=1.1,radius=140.,seed_length_floor=52.5)}
 seed_path=ROOT/'R03_CONNECTED_GEODESIC/P06_CONNECTED/G6' if round_id==5 else SEED
 steps=1 if round_id==5 else 2 if round_id==1 else 3
 seed=load_mesh(seed_path);forecast=512*1024**2+len(seed.faces)*4**steps*1800;memory=windows_memory()
 if memory['status']!='MEASURED' or forecast>min(12*1024**3,.5*memory['available_bytes']):raise MemoryError('Measured reserve insufficient.')
 write(root/'preflight.json',dict(memory=memory,forecast_bytes=forecast,seed=str(seed_path),seed_sha256=sha(seed_path/'mesh.npz'),steps=steps))
 renderer=pyrender.OffscreenRenderer(480,480);all_records=[];finals=[];progress=[];manifest=[]
 dest=root/'renders';dest.mkdir()
 try:
  for name,params in cases.items():
   job=root/name;job.mkdir();write(job/'recipe.json',dict(seed=str(seed_path),parameters=params,steps=steps,invalid_policy='Continue transverse intersections; no repair or exchange claim.'))
   mesh=load_mesh(seed_path);parent=seed_path;history=[]
   for index in range(steps+1):
    start=perf_counter()
    if index:mesh,meta,state=(connected_step if round_id in (3,5) else step)(mesh,**params)
    else:meta={};state={}
    stage=job/f'G{mesh.generation}';save_mesh(stage,mesh,meta,state,parent)
    check=contacts(mesh,cap=128 if round_id in (3,5) else 32,interval=True,include_shared=True)
    record=dict(generation=mesh.generation,stage=str(stage),sha256=sha(stage/'mesh.npz'),metrics=metrics(mesh),contacts=check,system_memory=windows_memory(),seconds=perf_counter()-start)
    if index:record['applied_distance_quantiles']=np.quantile(np.linalg.norm(state['resolved_displacement'],axis=1),[0,.5,.9,1]).tolist()
    write(stage/'validation.json',record);history.append(record);parent=stage
    label=name+'_G'+str(mesh.generation)
    ims=render(mesh,dest,label,renderer,[0,0,2000],5000,' INTERSECTIONS' if check['transverse_contacts'] else '')
    progress.append(ims[1])
    if index==steps:finals.extend(ims)
    manifest.append(dict(id=label,stage=str(stage),sha256=record['sha256'],camera_target=[0,0,2000],camera_width=5000,contacts=check['transverse_contacts']))
    print(name,mesh.generation,'triangles',len(mesh.faces),'contacts',check['transverse_contacts'],flush=True)
   write(job/'history.json',history);all_records.append(dict(candidate=name,history=history))
 finally:renderer.delete()
 sheet=Image.new('RGB',(480*3,480*len(cases)),'white')
 for i,im in enumerate(finals):sheet.paste(im,((i%3)*480,(i//3)*480))
 sheet.save(dest/'final_comparison.png')
 sheet=Image.new('RGB',(480*(steps+1),480*len(cases)),'white')
 for i,im in enumerate(progress):sheet.paste(im,((i%(steps+1))*480,(i//(steps+1))*480))
 sheet.save(dest/'progression.png');write(root/'summary.json',all_records);write(dest/'manifest.json',manifest)
def main():
 p=argparse.ArgumentParser();p.add_argument('--round',type=int,choices=[1,2,3,4,5,6],required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
 if not a.tag.replace('_','').isalnum():raise ValueError('Safe tag.')
 root=ROOT/a.tag
 if a.worker:
  if a.round==6:
   from astra_hierarchy import run as analyze
   for name in ['P09_ZERO_G7','P10_FIXED350_G7','P11_RADIUS220_G7','P12_RADIUS140_G7']:
    dest=root/name;dest.mkdir();analyze(ROOT/'R05_CHILD_PATCH_SCALE'/name,dest,[6,7])
  elif a.round==4:
   from astra_hierarchy import run as analyze
   for name in ['P06_CONNECTED','P07_CONNECTED_TRANSVERSE','P08_CONNECTED_REST']:
    dest=root/name;dest.mkdir();analyze(ROOT/'R03_CONNECTED_GEODESIC'/name,dest,[3,4,5,6])
  else:run(root,a.round)
  return
 root.mkdir(parents=True,exist_ok=False)
 source={}
 for rel in ['src/cheshire/freedom_patch.py','tools/freedom_patch_probe.py']:
  dest=root/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/rel,dest);source[rel]=sha(dest)
 write(root/'source_identity.json',source)
 result=guarded(['--round',str(a.round),'--tag',a.tag,'--worker'],root/'logs/run',worker_script=Path(__file__))
 write(root/'execution.json',result);print(result)
 if result['exit_code']:raise SystemExit(result['exit_code'])
if __name__=='__main__':main()
