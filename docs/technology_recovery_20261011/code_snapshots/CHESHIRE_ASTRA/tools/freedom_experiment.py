"""Exploration continues after transverse intersections; numerical failure is explicit."""
import sys,json,argparse,shutil,subprocess,hashlib
from pathlib import Path
from time import perf_counter
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'examples'),str(R/'tools')]
from task29_search import load_mesh,save_mesh
from astra_recipe import operate,physical
from cheshire.reference_subdivision import ArrayMesh,metrics
from cheshire.freedom_growth import step
from cheshire.astra_validation import embedding_failures
from task32_validation import embedding
from task36_contacts import contacts
from hero_design_sprint import guarded,windows_memory
ROOT=Path('E:/CHESHIRE_DATA/astra_freedom')
def write(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify_sources(root):
    identity=json.loads((root/'source_identity.json').read_text())
    if any(sha(R/rel)!=value for rel,value in identity.items()):raise RuntimeError('Launch source changed during experiment')
def run(spec,root):
    verify_sources(root)
    prior=Path(spec.get('start','E:/CHESHIRE_DATA/astra_research/recipes/B00_RECOVERED/G3'))
    path=prior/('operator_mesh.npz' if spec['kind']=='legacy' else 'mesh.npz');m=load_mesh(path)
    memory=None;roles=None;history=[]
    if spec.get('resume_memory',False):
        with np.load(prior/'operator_state.npz') as z:memory=dict(seed_xyz=z['seed_xyz'].copy(),ancestor_scale=float(z['ancestor_scale']))
    if spec['kind']=='legacy':
        with np.load(path) as z:
            if 'surface' in z.files:m.surface=str(z['surface'])
            if 'roles' in z.files and len(z['roles']):roles=z['roles'].copy()
    save_mesh(root/f'G{m.generation}',physical(m),{'copied_from':str(path),'source_sha256':sha(path)},None,prior)
    for row in spec['steps']:
        start=perf_counter();g=m.generation+1
        try:
            if spec['kind']=='field':m,meta,state,memory=step(m,memory=memory,**row)
            elif spec['kind']=='domain':
                from cheshire.freedom_domains import step as domain_step
                m,meta,state=domain_step(m,**row)
            elif spec['kind']=='patch':
                from cheshire.freedom_patch import connected_step
                m,meta,state=connected_step(m,**row)
            else:m,roles,meta,state=operate(m,roles,row)
            tri=physical(m);dest=root/f'G{g}'
            if 'base_xyz' in state:
                pre=ArrayMesh(state['base_xyz'],tri.faces,tri.classes,tri.rest,tri.anchors,tri.generation)
                save_mesh(root/f'G{g}_PRE',pre,{'operation':'Exact surface refinement before displacement'},None,root/f'G{g-1}')
            save_mesh(dest,tri,meta,state,root/f'G{g-1}')
            np.savez_compressed(dest/'operator_mesh.npz',xyz=m.xyz,faces=m.faces,classes=m.classes,rest=m.rest,anchors=m.anchors,generation=m.generation,surface=getattr(m,'surface','mean'),roles=np.array([]) if roles is None else roles)
            # Validation never rejects a finite experimental self-intersection.
            emb=embedding(tri);check=contacts(tri,cap=128,interval=True,include_shared=True)
            status='EXPERIMENTAL_INVALID' if check['transverse_contacts'] or embedding_failures(emb,spec.get('expected_euler',2)) else 'TRANSVERSE_AND_EMBEDDING_CHECKS_PASSED'
            record=dict(generation=g,stage=str(dest),metadata=meta,embedding=emb,contacts=check,status=status,seconds=perf_counter()-start,native_sha256=sha(dest/'mesh.npz'))
            write(dest/'validation.json',record);history.append(record);write(root/'history.json',history)
            print(root.name,g,len(tri.faces),status,round(record['seconds'],2),flush=True)
        except Exception as err:
            write(root/'numerical_failure.json',dict(generation=g,type=type(err).__name__,reason=str(err)));raise
    verify_sources(root)
    write(root/'completed.json',dict(complete=True,aesthetic_success='NOT_AUTOMATIC',invalid_retained=any(x['status']=='EXPERIMENTAL_INVALID' for x in history)))
def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if not a.tag.replace('_','').isalnum():raise ValueError('Safe new tag required')
    root=ROOT/'experiments'/a.tag;spec=json.loads(a.spec.read_text(encoding='utf8'))
    if a.worker:run(spec,root);return
    source=Path(spec.get('start','E:/CHESHIRE_DATA/astra_research/recipes/B00_RECOVERED/G3'))/'mesh.npz'
    with np.load(source) as z:n=len(z['faces'])
    forecast=512*1024**2+n*4**len(spec['steps'])*2400
    mem=windows_memory()
    if forecast>min(12*1024**3,.55*mem['available_bytes']):raise MemoryError('Forecast exceeds measured RAM reserve')
    root.mkdir(parents=True,exist_ok=False);write(root/'spec.json',spec);write(root/'preflight.json',dict(forecast_bytes=forecast,memory=mem))
    sourcefiles=list((R/'src/cheshire').glob('freedom_*.py'))+[Path(__file__)]+list((R/'src/cheshire').glob('astra_*.py'))+[R/'tools/astra_recipe.py',R/'src/cheshire/reference_subdivision.py',R/'src/cheshire/task36_growth.py']
    identity={}
    for f in sourcefiles:
        rel=f.relative_to(R);d=root/'source'/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,d);identity[rel.as_posix()]=sha(d)
    write(root/'source_identity.json',identity);write(root/'revision.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
    result=guarded(['--spec',str(root/'spec.json'),'--tag',a.tag,'--worker'],root/'logs/run',worker_script=Path(__file__))
    write(root/'execution.json',result)
    if result['exit_code']:raise SystemExit(result['exit_code'])
if __name__=='__main__':main()
