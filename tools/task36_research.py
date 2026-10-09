"""Immutable Task36 experiments. Measured process-family RAM guard is reused."""
import argparse,json,sys,shutil,subprocess
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_preserve import sha,write_new
from task29_search import save_mesh,load_mesh
from hero_design_sprint import guarded,windows_memory
from cheshire.task36_growth import carrier,step,native,quick_integrity
from cheshire.reference_subdivision import ArrayMesh
ROOT=Path('E:/CHESHIRE_DATA/task36')
SOURCES=['src/cheshire/task36_growth.py','src/cheshire/reference_subdivision.py','tools/task36_research.py',
 'examples/task29_search.py','examples/hero_design_sprint.py','tools/task33_preserve.py','tools/task33_contacts.py',
 'tools/task32_validation.py','tools/task33_views.py','tools/task34_research.py','tools/task33_planar.py']
SOURCES += ['tools/task36_contacts.py','tools/native/Task36Bounds.cs','tools/task36_triangle_interval.py']


def preflight(request):
    g=request['generations'];div=request.get('divisions',2)
    if type(g)!=int or not 1<=g<=10:raise ValueError('Declared bounded integer depth required.')
    faces=(4*div+2)*4**g;tri=faces*4;memory=windows_memory();forecast=512*1024**2+tri*1800
    if memory['status']!='MEASURED' or forecast>min(12*1024**3,.55*memory['available_bytes']):raise MemoryError('Forecast exceeds measured RAM reserve.')
    if shutil.disk_usage(ROOT.parent).free<4*1024**3+tri*2000:raise OSError('Insufficient disk reserve.')
    return dict(quads=faces,triangles=tri,forecast_bytes=forecast,available=memory,
      estimator='512 MiB + 1800 bytes/native triangle; empirical Task36 G6 and H01 G7 margin. Actual process-family RAM guard and 2 GiB free floor unchanged.')


def checkpoint(dest,mesh,parent=None,op=None,meta=None):
    save_mesh(dest,native(mesh),meta,op,parent)
    np.savez_compressed(dest/'quad_state.npz',xyz=mesh.xyz,faces=mesh.faces,rest=mesh.rest,classes=mesh.classes,anchors=mesh.anchors,generation=mesh.generation,surface=getattr(mesh,'surface','mean'))
    write_new(dest/'identity.json',{p.name:sha(p) for p in dest.iterdir() if p.is_file()})


def run(request,tag):
    forecast=preflight(request);job=ROOT/'candidates'/tag;job.mkdir(parents=True,exist_ok=False)
    write_new(job/'request.json',request);write_new(job/'preflight.json',forecast)
    git=['git','-c','safe.directory='+REPO.as_posix()]
    write_new(job/'revision.json',dict(head=subprocess.check_output(git+['rev-parse','HEAD'],text=True).strip(),
       status=subprocess.check_output(git+['status','--porcelain'],text=True),note='Exact source overlay authoritative.'))
    ids={}
    for relative in SOURCES:
        dest=job/'source'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/relative,dest)
        ids[relative]=sha(dest);assert ids[relative]==sha(REPO/relative)
    write_new(job/'source_identity.json',ids)
    mesh=carrier(divisions=request.get('divisions',2));parent=job/'G0_CARRIER';checkpoint(parent,mesh)
    history=[]
    for g in range(1,request['generations']+1):
        start=perf_counter();params=request['parameters'].copy();params.update(request.get('schedule',{}).get(str(g),{}))
        active=g in request.get('active_generations',list(range(1,request['generations']+1)))
        pre,preop=step(mesh,**params,active=False);before=job/f'G{g}_PRE';checkpoint(before,pre,parent,preop,dict(operation='Interpolating split only; centre-fan surface changes possible.'))
        if request.get('contact_engine','original')=='bvh_interval':
            from task36_contacts import contacts as accelerated
            from functools import partial
            contacts=partial(accelerated,interval=True)
        elif request.get('contact_engine','original')=='bvh':from task36_contacts import contacts
        elif request.get('contact_engine','original')=='original':from task33_contacts import contacts
        else:raise ValueError('Explicit supported contact engine required.')
        out,op=step(mesh,**params,active=active)
        trials=[];check=contacts(native(out)) if request.get('check_each',True) else None
        factor=1.;integrity=quick_integrity(out)
        local_trials=[]
        if check and check['transverse_contacts'] and request.get('local_backtrack',False):
            from scipy.spatial import cKDTree
            proposed=out.xyz.copy();delta=proposed-pre.xyz;weights=np.ones(len(out.xyz));tree=cKDTree(out.rest)
            local_cap=request.get('local_contact_cap',256)
            if type(local_cap)!=int or not 256<=local_cap<=16384:raise ValueError('Bounded diagnostic contact batch required.')
            local_iterations=request.get('local_iterations',24)
            if type(local_iterations)!=int or not 1<=local_iterations<=64:raise ValueError('Bounded diagnostic repair budget required.')
            if local_cap>256:check=contacts(native(out),cap=local_cap)
            transforms=[np.diag([-1,1,1]),np.diag([1,-1,1]),np.array([[0,-1,0],[1,0,0],[0,0,1]])]
            maps=[]
            for matrix in transforms:
                distance,index=tree.query(out.rest@matrix.T)
                if distance.max()>1e-8 or len(np.unique(index))!=len(index):raise ValueError('Material symmetry correspondence failed.')
                maps.append(index)
            for iteration in range(local_iterations):
                pairs=np.asarray(check['pairs'],np.int64);quad_ids=np.unique(pairs.ravel()//4)
                affected=np.unique(out.faces[quad_ids].ravel())
                for _ in range(3):affected=np.unique(np.r_[affected,*[m[affected] for m in maps]])
                weights[affected]*=.5;weights[weights<1/4096]=0
                out.xyz=pre.xyz+weights[:,None]*delta;check=contacts(native(out),cap=local_cap);integrity=quick_integrity(out)
                local_trials.append(dict(iteration=iteration+1,changed_points=len(affected),limited_points=int((weights<1).sum()),zero_points=int((weights==0).sum()),contacts=check,integrity=integrity))
                print(tag,'G'+str(g),'local',iteration+1,'contacts',check['transverse_contacts'],'limited',int((weights<1).sum()),flush=True)
                if not check['transverse_contacts'] or any(integrity.values()):break
            op.update(local_requested_xyz=proposed,local_point_factor=weights)
        if ((check and check['transverse_contacts']) or any(integrity.values())) and request.get('backtrack',False) and not request.get('local_backtrack',False):
            requested_xyz=out.xyz.copy();trials.append(dict(factor=1.,contacts=check,integrity=integrity))
            for factor in [.5,.25,.125,.0625,.03125]:
                out.xyz=pre.xyz+factor*(requested_xyz-pre.xyz);check=contacts(native(out));integrity=quick_integrity(out);trials.append(dict(factor=factor,contacts=check,integrity=integrity))
                if not check['transverse_contacts'] and not any(integrity.values()):break
            op['requested_xyz']=requested_xyz;op['applied_factor']=np.array(factor)
        dest=job/f'G{g}_FOLD';checkpoint(dest,out,before,op,dict(operation='Independent current face/edge placement',active=active,parameters=params,applied_factor=factor,backtrack_trials=trials,local_trials=local_trials))
        row=dict(generation=g,vertices=len(out.xyz),quads=len(out.faces),triangles=4*len(out.faces),seconds=perf_counter()-start,
          new_face_participants=int((np.linalg.norm(op['face_vector'],axis=1)>1e-9).sum()),
          new_edge_participants=int((np.linalg.norm(op['edge_vector'],axis=1)>1e-9).sum()),
          prior_edge_points_reused_as_corners=int((mesh.classes==1).sum()),prior_face_points_reused_as_corners=int((mesh.classes==2).sum()),
          applied_factor=factor,backtrack_trials=trials,
          integrity=integrity,
          actual_displacement_quantiles=np.quantile(np.linalg.norm(out.xyz-pre.xyz,axis=1),[0,.5,.95,1]).tolist(),
          actual_new_point_participants=int((np.linalg.norm((out.xyz-pre.xyz)[len(mesh.xyz):],axis=1)>1e-9).sum()),
          face_distance_quantiles=np.quantile(np.linalg.norm(op['face_vector'],axis=1),[0,.5,.95,1]).tolist(),contacts=check)
        write_new(dest/'growth.json',row);history.append(row);print(tag,g,len(out.faces),row['new_face_participants'],None if check is None else check['transverse_contacts'],round(row['seconds'],2),flush=True)
        if (check and check['transverse_contacts']) or any(integrity.values()):
            write_new(job/'failed.json',dict(reason='Actual transverse contact; no export.',generation=g,history=history));return
        mesh=out;parent=dest
    write_new(job/'completed.json',dict(final_stage=str(parent),history=history))


def render(request,tag):
    import task33_views
    from task34_research import comparison_sheet
    for item in request['items']:
        stage=Path(item['stage'])
        if not item['label'].startswith(stage.parent.name+'_'+stage.name+'_'):raise ValueError('Label/native mismatch.')
    p=ROOT/'definitions'/(tag+'_render.json');write_new(p,request)
    task33_views.ROOT=ROOT;task33_views.sheet=comparison_sheet;task33_views.raking(p,tag)


def audit(request,tag):
    from task36_evidence import audit as actual_audit
    actual_audit(request,tag)


def hierarchy(request,tag):
    from task36_evidence import hierarchy as actual_hierarchy
    actual_hierarchy(request,tag)


def probe(request,tag):
    from task33_contacts import contacts
    job=ROOT/'candidates'/request['candidate'];g=request['generation'];previous=job/f'G{g-1}_FOLD'
    z=np.load(previous/'quad_state.npz');mesh=ArrayMesh(*(z[k].copy() for k in ['xyz','faces','classes','rest','anchors']),int(z['generation']))
    mesh.surface=str(z['surface']) if 'surface' in z else 'mean'
    recipe=json.loads((job/'request.json').read_text());params=recipe['parameters'].copy();params.update(recipe.get('schedule',{}).get(str(g),{}))
    alpha=json.loads((job/f'G{g}_FOLD/growth.json').read_text())['applied_factor']
    pre,_=step(mesh,**params,active=False);full,op=step(mesh,**params)
    original_op=np.load(job/f'G{g}_FOLD/operator_state.npz')
    common_point_factor=original_op['local_point_factor'] if 'local_point_factor' in original_op else np.ones(len(full.xyz))
    dest=ROOT/'diagnostics'/tag;dest.mkdir(parents=True,exist_ok=False);rows=[]
    for name in ['REPLAY','FEATURES_REST','NO_NEW_POINTS','NO_RETAINED_MOVE','SUBDIVISION_ONLY']:
        out=step(mesh,**dict(params,source='rest'))[0] if name=='FEATURES_REST' else ArrayMesh(full.xyz.copy(),full.faces,full.classes,full.rest,full.anchors,full.generation)
        out.surface=getattr(full,'surface','mean')
        delta=out.xyz-pre.xyz;nv=len(mesh.xyz)
        if name=='NO_NEW_POINTS':delta[nv:]=0
        if name=='NO_RETAINED_MOVE':delta[:nv]=0
        if name=='SUBDIVISION_ONLY':delta[:]=0
        out.xyz=pre.xyz+alpha*common_point_factor[:,None]*delta;stage=dest/name/f'G{g}_FOLD'
        checkpoint(stage,out,previous,dict(actual_delta=out.xyz-pre.xyz),dict(probe=name,common_applied_factor=alpha,source_native_sha256=sha(previous/'mesh.npz')))
        diff=out.xyz-(pre.xyz+alpha*common_point_factor[:,None]*(full.xyz-pre.xyz));check=contacts(native(out))
        row=dict(id=name,stage=str(stage),contacts=check,integrity=quick_integrity(out),max_difference=float(abs(diff).max()),rms_difference=float(np.sqrt(np.mean(diff**2))))
        if name=='REPLAY':row['matches_authoritative_native_arrays']=bool(np.array_equal(native(out).xyz,load_mesh(job/f'G{g}_FOLD').xyz))
        rows.append(row);print(name,check['transverse_contacts'],row['max_difference'],flush=True)
    write_new(dest/'summary.json',dict(source=request,common_factor=alpha,common_local_mask_sha256=sha(job/f'G{g}_FOLD/operator_state.npz'),rows=rows,note='Identical incoming geometry and frozen common actual point factors; alternative masks are not re-solved. Invalid counterfactual surfaces retained, never exported. FEATURES_REST freezes feature controls, not placement geometry/normals.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--action',choices=['run','render','audit','hierarchy','probe'],required=True);p.add_argument('--request',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if not a.tag.replace('_','').isalnum():raise ValueError('Safe fresh tag required.')
    request=json.loads(a.request.read_text(encoding='utf8'))
    if a.worker:globals()[a.action](request,a.tag)
    else:
        if a.action=='run':preflight(request)
        logs=ROOT/'logs'/(a.action+'_'+a.tag)
        if logs.exists():raise FileExistsError(logs)
        result=guarded(['--action',a.action,'--request',str(a.request.resolve()),'--tag',a.tag,'--worker'],logs,worker_script=Path(__file__))
        write_new(ROOT/'resources'/(a.action+'_'+a.tag+'.json'),result);print(json.dumps(result),flush=True)
        if result['exit_code']:raise SystemExit(result['exit_code'])
