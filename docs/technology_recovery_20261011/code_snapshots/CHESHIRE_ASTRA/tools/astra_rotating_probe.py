"""Bounded edge-rotation comparisons, immutable failure checkpoints."""
import argparse,json,sys,shutil,hashlib
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from cheshire.astra_rotating import step
from cheshire.reference_subdivision import cube,metrics
from cheshire.task36_growth import carrier,native
from task29_search import save_mesh
from task36_contacts import contacts
from hero_design_sprint import guarded,windows_memory

CASES={'R00_SMOOTH':dict(fold=0),'R01_CURRENT':dict(),'R02_REST':dict(source='rest'),
       'R03_NO_FLIP':dict(flip=False),'R04_RETENTION':dict(relaxation=.04),'R05_STRONG':dict(fold=.65),'R06_REVERSE':dict(fold=.35,bias=-.75),'R07_OUTWARD':dict(polarity=1.),'R08_OUTWARD_WEAK':dict(polarity=1.,fold=.18),'R09_OUTWARD_REST':dict(polarity=1.,fold=.18,source='rest')}
def write(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf8')
def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--generations',type=int,default=6);p.add_argument('--case',choices=list(CASES),required=True);p.add_argument('--shape',choices=['column','cube'],default='column');p.add_argument('--worker',action='store_true');a=p.parse_args()
    if not a.tag.replace('_','').isalnum() or not 1<=a.generations<=12:raise ValueError('Explicit bounded run required.')
    root=Path('E:/CHESHIRE_DATA/astra_research/rotating_probe')/a.tag
    params=dict(CASES[a.case]);tri0=40 if a.shape=='column' else 24
    mem=windows_memory();forecast=512*1024**2+tri0*3**a.generations*1800
    if mem['status']!='MEASURED' or forecast>min(12*1024**3,.55*mem['available_bytes']):raise MemoryError('Measured reserve exceeded.')
    if not a.worker:
        root.mkdir(parents=True,exist_ok=False);write(root/'request.json',dict(case=a.case,shape=a.shape,generations=a.generations,parameters=params,forecast_bytes=forecast,available=mem))
        for rel in ['src/cheshire/astra_rotating.py','src/cheshire/reference_subdivision.py','src/cheshire/task36_growth.py','tools/astra_rotating_probe.py','tools/task36_contacts.py','tools/task36_triangle_interval.py','tools/native/Task36Bounds.cs']:
            dest=root/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/rel,dest)
        write(root/'source_identity.json',{str(f.relative_to(root/'source')):hashlib.sha256(f.read_bytes()).hexdigest() for f in (root/'source').rglob('*') if f.is_file()})
        result=guarded(['--tag',a.tag,'--case',a.case,'--shape',a.shape,'--generations',str(a.generations),'--worker'],root/'logs/run',worker_script=Path(__file__))
        write(root/'execution.json',result);print(a.tag,result,flush=True)
        if result['exit_code']:raise SystemExit(result['exit_code'])
        return
    mesh=native(carrier() if a.shape=='column' else cube());history=[];parent=None
    for g in range(a.generations+1):
        start=perf_counter()
        if g:mesh,meta,state=step(mesh,**params)
        else:meta={};state={}
        stage=root/f'G{g}';save_mesh(stage,mesh,meta,state,parent)
        check=contacts(mesh,cap=512,interval=True,include_shared=True)
        row=dict(generation=g,stage=str(stage),metrics=metrics(mesh),contacts=check,seconds=perf_counter()-start)
        if g:row['displacements']={k:np.quantile(np.linalg.norm(state[k],axis=1),[0,.5,.95,1]).tolist() for k in ['old_vertex_displacement','new_face_displacement']}
        write(stage/'validation.json',row);history.append(row);print(g,row['metrics']['extent'],'contact',check['transverse_contacts'],flush=True)
        if check['transverse_contacts'] or row['metrics']['zero_area_faces'] or not row['metrics']['finite']:write(root/'failed.json',row);break
        parent=stage
    else:write(root/'completed.json',dict(final_stage=str(parent)))
    write(root/'history.json',history)
if __name__=='__main__':main()
