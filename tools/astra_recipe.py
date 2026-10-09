"""Replayable independent multi-operator engine; no historical output paths.

Recipe: {carrier:{kind:column|cube,side:1000,height:4000,divisions:2},
steps:[{operator:reference|primal|dual|rotating|fan,parameters:{...}}]}.
Every complete operator state and physical triangle surface is retained.
"""
import argparse,json,sys,shutil,hashlib,subprocess
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from cheshire.reference_subdivision import ArrayMesh,cube,subdivide,metrics,fields,GLOBAL_SCALE,LOCAL_INCIDENT_SCALE
from cheshire.task36_growth import carrier
from cheshire.astra_dual import native
from task29_search import save_mesh
from task36_contacts import contacts
from task32_validation import embedding
from cheshire.astra_validation import embedding_failures
from hero_design_sprint import guarded,windows_memory

def write(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def physical(m):return m if np.all((m.faces>=0).sum(1)==3) else native(m)

def operate(mesh,roles,row):
    kind=row['operator'];params=row.get('parameters',{})
    if kind=='reference':
        row=dict(params);mode=row.pop('scale_mode',LOCAL_INCIDENT_SCALE)
        if row.get('offset_units')=='ABSOLUTE':
            if mode!=GLOBAL_SCALE:raise ValueError('Absolute offsets require explicit global conversion.')
            row['weights']=dict(row['weights']);scale=float(fields(mesh)['lengths'].mean())
            for key in ['wf','we','wp']:row['weights'][key]=row['weights'].get(key,0)/scale
        out,meta,state=subdivide(mesh,row,scale_mode=mode);meta['requested_row']=params;roles=None
    elif kind=='primal':
        from cheshire.astra_primal import step
        out,meta,state=step(mesh,**params);roles=None
    elif kind=='dual':
        from cheshire.astra_dual import step
        out,roles,meta,state=step(mesh,roles,**params)
    elif kind=='task36':
        from cheshire.task36_growth import step
        out,state=step(mesh,**params);roles=None;meta={'implementation':'Task36 growth on independently generated input','parameters':params}
    elif kind=='curvature':
        from cheshire.astra_curvature_response import step
        out,meta,state=step(physical(mesh),**params);roles=None
    elif kind=='adaptive':
        from cheshire.astra_adaptive import step
        out,meta,state=step(physical(mesh),**params);roles=None
    elif kind=='rotating':
        from cheshire.astra_rotating import step
        out,meta,state=step(physical(mesh),**params);roles=None
        meta['input_conversion']='Explicit authoritative centroid/VF fan if incoming operator polygons are not triangles.'
    elif kind=='fan':
        from cheshire.astra_dual import refine_fan
        if params:raise ValueError('Fan sampling has no deformation parameters.')
        out,state=refine_fan(mesh);roles=None;meta={'operation':'Physical fan-preserving sampling only'}
    else:raise ValueError('Unknown explicit operator.')
    if not np.isfinite(out.xyz).all():raise ValueError('Nonfinite output; no export.')
    return out,roles,meta,state

def verify_sources(root):
    identities=json.loads((root/'source_identity.json').read_text())
    changed=[rel for rel,value in identities.items() if sha(REPO/rel)!=value]
    if changed:raise RuntimeError('Launch source changed: '+str(changed))
    return identities

def run(recipe,root):
    verify_sources(root)
    spec=dict(recipe.get('carrier',{}));kind=spec.pop('kind','column')
    if kind=='column':mesh=carrier(**spec)
    elif kind=='cube':mesh=cube(**spec)
    else:raise ValueError('Unknown carrier.')
    roles=None;history=[];parent=None;ever_invalid=False
    for g,row in enumerate([None]+recipe['steps']):
        start=perf_counter()
        if row:
            mesh,roles,meta,state=operate(mesh,roles,row)
        else:meta={'operation':'Unsculpted primitive'};state={}
        stage=root/f'G{g}';tri=physical(mesh)
        if 'base_xyz' in state:
            baseline=ArrayMesh(state['base_xyz'],mesh.faces,mesh.classes,mesh.rest,mesh.anchors,mesh.generation)
            before=root/f'G{g}_PRE';save_mesh(before,physical(baseline),{'operation':'Exact midpoint surface before coherent displacement'},None,parent)
            parent=before
        save_mesh(stage,tri,meta,state,parent)
        np.savez_compressed(stage/'operator_mesh.npz',xyz=mesh.xyz,faces=mesh.faces,classes=mesh.classes,rest=mesh.rest,anchors=mesh.anchors,generation=mesh.generation,surface=getattr(mesh,'surface','mean'),roles=np.array([]) if roles is None else roles)
        check=contacts(tri,cap=1024,interval=True,include_shared=True);basic=metrics(tri)
        emb=embedding(tri);policy_failures=embedding_failures(emb,recipe.get('expected_euler',2))
        invalid=bool(check['transverse_contacts'] or policy_failures);ever_invalid|=invalid
        record=dict(generation=g,stage=str(stage),native_sha256=sha(stage/'mesh.npz'),operator=row,metrics=basic,embedding=emb,embedding_failures=policy_failures,contacts=check,invalid=invalid,seconds=perf_counter()-start)
        write(stage/'validation.json',record);history.append(record);write(root/'history.json',history)
        print(root.name,g,basic['faces'],check['transverse_contacts'],flush=True)
        parent=stage
        if invalid and not recipe.get('continue_invalid_diagnostic',False):
            write(root/'failed.json',dict(reason='Invalid native mesh; preserved failure, no export.',generation=g));return
    verify_sources(root)
    write(root/'source_verified_after.json',{'all_launch_sources_unchanged':True})
    verdict='INVALID_DIAGNOSTIC' if ever_invalid else 'GEOMETRY_CHECKS_PASSED'
    write(root/'completed.json',dict(final_stage=str(parent),status=verdict,aesthetic_success='NOT_AUTOMATICALLY_ASSESSED',exclusions='Coplanar overlaps, tangency and boundary-only contacts excluded. No continuous-ridge or solid certification.'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--recipe',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if not a.tag.replace('_','').isalnum():raise ValueError('Safe fresh tag required.')
    root=Path('E:/CHESHIRE_DATA/astra_research/recipes')/a.tag
    recipe=json.loads(a.recipe.read_text(encoding='utf8'))
    n=len(recipe['steps'])
    if not 1<=n<=16:raise ValueError('Explicit bounded schedule required.')
    estimate=(4*recipe.get('carrier',{}).get('divisions',2)+2)*4
    for row in recipe['steps']:estimate*=3 if row['operator'] in ('rotating','adaptive') else 4
    memory=windows_memory();forecast=512*1024**2+estimate*1800
    if memory['status']!='MEASURED' or forecast>min(12*1024**3,.55*memory['available_bytes']):raise MemoryError('Predicted memory exceeds measured reserve.')
    if a.worker:run(recipe,root);return
    root.mkdir(parents=True,exist_ok=False);write(root/'recipe.json',recipe);write(root/'preflight.json',dict(forecast_bytes=forecast,forecast_native_triangles=estimate,available=memory))
    write(root/'revision.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),note='Exact source overlay authoritative for uncommitted implementations.'))
    sources=list((REPO/'src/cheshire').glob('astra_*.py'))+[REPO/p for p in ['src/cheshire/reference_subdivision.py','src/cheshire/dual_subdivision.py','src/cheshire/task36_growth.py','tools/astra_recipe.py','tools/task36_contacts.py','tools/task36_triangle_interval.py','tools/native/Task36Bounds.cs','tools/task33_contacts.py','tools/task32_validation.py','examples/task29_search.py','examples/hero_design_sprint.py']]
    identities={}
    for source in sources:
        rel=source.relative_to(REPO);dest=root/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);identities[rel.as_posix()]=sha(dest)
    write(root/'source_identity.json',identities)
    result=guarded(['--recipe',str(root/'recipe.json'),'--tag',a.tag,'--worker'],root/'logs/run',worker_script=Path(__file__))
    write(root/'execution.json',result);print(a.tag,result,flush=True)
    if result['exit_code']:raise SystemExit(result['exit_code'])
if __name__=='__main__':main()
