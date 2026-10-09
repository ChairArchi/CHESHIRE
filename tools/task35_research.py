"""Immutable, measured-RAM-guarded Task35 column experiments and evidence."""
import argparse,json,shutil,sys,subprocess
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_preserve import sha,write_new
from task29_search import save_mesh,load_mesh
from hero_design_sprint import guarded,windows_memory
from cheshire.task35_columns import carrier,native,refine,form,refold,symmetry,RejectedFormation
ROOT=Path('E:/CHESHIRE_DATA/task35')
SOURCES=['src/cheshire/task35_columns.py','src/cheshire/task34_refolding.py','src/cheshire/reference_subdivision.py',
    'tools/task35_research.py','examples/task29_search.py','examples/hero_design_sprint.py','tools/task33_preserve.py',
    'tools/task33_contacts.py','tools/task32_validation.py','tools/task33_views.py','tools/task34_research.py','tools/task33_planar.py']


def preflight(request):
    allowed={'carrier','variant','controller','criterion','final_generation','macro_generation','fold_generations','sampling','form','refold'}
    if set(request)-allowed:raise ValueError('Unknown column request fields.')
    g=request.get('final_generation',7);sampling=request.get('sampling',['both']*4+['angular']*3)
    if not isinstance(g,int) or len(sampling)!=g or g<3:raise ValueError('Complete finite sampling schedule required.')
    onset=request.get('macro_generation',3);folds=request.get('fold_generations',[4,7])
    if not 1<=onset<=g or len(set(folds))!=len(folds) or any(not onset<f<=g for f in folds):raise ValueError('Formation/fold schedule outside run.')
    nr=nt=8
    for mode in sampling:
        if mode not in ('both','angular'):raise ValueError('Unknown sampling direction.')
        if mode=='both':nr*=2
        nt*=2
    triangles=4*nr*nt+2*nt;forecast=512*1024**2+triangles*3000;memory=windows_memory()
    if memory['status']!='MEASURED' or forecast>min(12*1024**3,.55*memory['available_bytes']):raise MemoryError('Forecast exceeds measured RAM reserve.')
    free=shutil.disk_usage(ROOT.parent).free
    if free<4*1024**3+triangles*2000:raise OSError('Disk reserve insufficient.')
    return dict(predicted_triangles=triangles,predicted_grid=[nr+1,nt],forecast_working_bytes=forecast,available=memory,disk_free=free)


def checkpoint(dest,state,generation,metadata,parent=None,op=None,controls=None,features=None):
    mesh,chart,_=native(state,generation)
    save_mesh(dest,mesh,metadata,op,parent)
    np.savez_compressed(dest/'formation_state.npz',**state);np.savez_compressed(dest/'material_state.npz',chart=chart)
    if controls is not None:np.savez_compressed(dest/'control_state.npz',**controls)
    if features is not None:write_new(dest/'features.json',features)
    write_new(dest/'identity.json',dict(parent_mesh_sha256=sha(parent/'mesh.npz') if parent else None,
        files={p.name:sha(p) for p in dest.iterdir() if p.is_file()}))


def run(request,tag):
    forecast=preflight(request);mode=request.get('controller','common');criterion=request.get('criterion','current')
    if mode not in ('common','regional') or criterion not in ('current','frozen_form'):raise ValueError('Explicit controller/source criterion required.')
    job=ROOT/'candidates'/tag;job.mkdir(parents=True,exist_ok=False)
    write_new(job/'request.json',request);write_new(job/'preflight.json',forecast)
    git=['git','-c','safe.directory='+REPO.as_posix()]
    write_new(job/'source_revision.json',dict(head=subprocess.check_output(git+['rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        branch=subprocess.check_output(git+['branch','--show-current'],cwd=REPO,text=True).strip(),
        worktree=subprocess.check_output(git+['status','--porcelain'],cwd=REPO,text=True),note='Exact producer overlay, not HEAD alone, is authoritative for uncommitted research.'))
    identity={}
    for relative in SOURCES:
        dest=job/'source'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/relative,dest)
        identity[relative]=sha(REPO/relative)
        if sha(dest)!=identity[relative]:raise ValueError('Source copy SHA mismatch.')
    write_new(job/'source_identity.json',identity)
    state=carrier(request.get('carrier','uniform'),request.get('variant','standard'));parent=job/'G0_CARRIER'
    checkpoint(parent,state,0,dict(operation='Closed octagonal vertical column; axes X width/Y depth/Z height; no gate region/height reflection.'))
    history=[];frozen=None;frozen_parent=None
    for generation,sampling in enumerate(request.get('sampling',['both']*4+['angular']*3),1):
        start=perf_counter();state,op=refine(state,sampling);before=job/f'G{generation}_PRE'
        checkpoint(before,state,generation,dict(operation='Bilinear sampling',sampling=sampling,
            caveat='Existing grid positions retained. Angular-only refinement does not retain every old native cell-centre vertex; material overlap contributors are recorded.'),parent,op)
        parent=before
        if frozen is not None:frozen,_=refine(frozen,sampling)
        if generation==request.get('macro_generation',3):
            state,controls=form(state,mode,request.get('form',{}));after=job/f'G{generation}_FORM'
            checkpoint(after,state,generation,dict(operation='Initial finite formation',controller=mode,requested=request.get('form',{})),before,controls=controls)
            frozen=state;frozen_parent=after;parent=after
        elif generation in request.get('fold_generations',[4,7]):
            source=state;source_stage=before
            if criterion=='frozen_form':
                source=frozen;source_stage=job/f'G{generation}_REFERENCE'
                checkpoint(source_stage,source,generation,dict(operation='First formation resampled, no generated-feature feedback.'),frozen_parent);frozen_parent=source_stage
            try:state,controls,features=refold(state,source,mode,request.get('refold',{}))
            except RejectedFormation as error:
                rejected=job/f'G{generation}_REJECTED'
                checkpoint(rejected,error.state,generation,dict(operation='REJECTED diagnostic only',reason=str(error),
                    source_stage=str(source_stage),source_mesh_sha256=sha(source_stage/'mesh.npz'),requested=request.get('refold',{})),before,controls=error.controls,features=error.features)
                write_new(job/'failed.json',dict(reason=str(error),generation=generation,rejected_stage=str(rejected),export_allowed=False))
                raise
            after=job/f'G{generation}_FOLD'
            metadata=dict(operation='Measured incoming crest refolding',controller=mode,criterion=criterion,
                source_stage=str(source_stage),source_mesh_sha256=sha(source_stage/'mesh.npz'),requested=request.get('refold',{}),
                actual_signed_range=[float(controls['requested_signed_distance'].min()),float(controls['requested_signed_distance'].max())],
                actual_XYZ_max=float(controls['total_applied_distance'].max()),active_grid_vertices=int(np.count_nonzero(controls['total_applied_distance'])),
                geometric_smoothing=False,locks='Only declared common original-material end buffers. No gate/height copying or body locks.',
                scale='Physical project units and measured source prominence/chord/section radius; never current cell-edge length.')
            checkpoint(after,state,generation,metadata,before,controls=controls,features=dict(source_stage=str(source_stage),
                source_mesh_sha256=sha(source_stage/'mesh.npz'),samples=512,scalar_sigma=request.get('refold',{}).get('signal_sigma',.035),features=features))
            parent=after
        mesh,_,_=native(state,generation)
        history.append(dict(generation=generation,stage=str(parent),vertices=len(mesh.xyz),triangles=len(mesh.faces),grid=list(state['grid'].shape[:2]),seconds=perf_counter()-start))
        print(tag,generation,len(mesh.faces),round(history[-1]['seconds'],2),flush=True)
    write_new(job/'completed.json',dict(final_stage=str(parent),history=history,request_sha256=sha(job/'request.json'),source_identity_sha256=sha(job/'source_identity.json')))


def audit(request,tag):
    from task32_validation import embedding
    from task33_contacts import contacts
    import trimesh
    from task33_planar import inspect_segments
    dest=ROOT/'validation'/tag;dest.mkdir(parents=True,exist_ok=False);write_new(dest/'request.json',request);rows=[]
    for item in request['items']:
        start=perf_counter();stage=Path(item['stage']);mesh=load_mesh(stage);memory=windows_memory();forecast=512*1024**2+len(mesh.faces)*3000
        if forecast>min(12*1024**3,.55*memory['available_bytes']):raise MemoryError('Audit forecast exceeds reserve.')
        chart=np.load(stage/'material_state.npz')['chart'];state=dict(np.load(stage/'formation_state.npz'))
        value=dict(**item,mesh_sha256=sha(stage/'mesh.npz'),embedding=embedding(mesh),symmetry=symmetry(mesh,chart),contacts=contacts(mesh),forecast_working_bytes=forecast)
        fixed=(state['s']<=.06)|(state['s']>=.94)
        value['end_buffer_xyz_error']=float(abs(state['grid'][fixed]-state['rest'][fixed]).max())
        value['min_mean_row_Z_increment']=float(np.diff(state['grid'][:,:,2].mean(1)).min())
        value['min_corresponding_row_Z_increment']=float(np.diff(state['grid'][:,:,2],axis=0).min())
        model=trimesh.Trimesh(vertices=mesh.xyz,faces=mesh.faces[:,:3],process=False);segments={};cuts=[]
        planes=[(f'Z{z}',[0,0,z+.12345],[0,0,1],[0,1]) for z in range(400,3601,100)]
        planes += [('XZ',[0,0,0],[0,1,0],[0,2]),('YZ',[0,0,0],[1,0,0],[1,2]),('DIAGONAL',[0,0,0],[1,-1,0],None)]
        for name,origin,normal,axes in planes:
            lines=trimesh.intersections.mesh_plane(model,normal,origin);segments[name]=lines
            uv=lines[:,:,axes] if axes is not None else np.stack([(lines[:,:,0]+lines[:,:,1])/2**.5,lines[:,:,2]],axis=-1)
            cuts.append(dict(name=name,origin=origin,normal=normal,**inspect_segments(uv)))
        np.savez_compressed(dest/(item['id']+'_cuts.npz'),**segments)
        value.update(cuts=cuts,seconds=perf_counter()-start,producer_sha256=sha(Path(__file__)))
        write_new(dest/(item['id']+'.json'),value);rows.append(value)
        print(item['id'],'contacts',value['contacts']['transverse_contacts'],'sym',max(v['geometry_max'] for v in value['symmetry'].values()),'seconds',round(value['seconds'],2),flush=True)
    write_new(dest/'summary.json',rows)


def render(request,tag):
    import task33_views
    from task34_research import comparison_sheet
    definition=json.loads(Path(request).read_text())
    for item in definition['items']:
        stage=Path(item['stage'])
        if not stage.is_relative_to(ROOT/'candidates') or not item['label'].startswith(stage.parent.name+'_'+stage.name+'_'):raise ValueError('Native candidate/stage label mismatch.')
    task33_views.ROOT=ROOT;task33_views.sheet=comparison_sheet;task33_views.raking(request,tag)


def measure(request,tag):
    from task35_analyze import measure as actual_measure
    actual_measure(request['candidate'],request['validation'],tag,request.get('audit_id'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--action',choices=['run','audit','render','measure'],required=True);p.add_argument('--request',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');args=p.parse_args()
    if not args.tag.replace('_','').isalnum():raise ValueError('Safe fresh tag required.')
    if args.worker:globals()[args.action](args.request if args.action=='render' else json.loads(args.request.read_text(encoding='utf-8')),args.tag)
    else:
        if args.action=='run':preflight(json.loads(args.request.read_text(encoding='utf-8')))
        logs=ROOT/'logs'/(args.action+'_'+args.tag)
        if logs.exists():raise FileExistsError('Run logs are immutable.')
        result=guarded(['--action',args.action,'--request',str(args.request),'--tag',args.tag,'--worker'],logs,worker_script=Path(__file__))
        write_new(ROOT/'resources'/(args.action+'_'+args.tag+'.json'),result);print(json.dumps(result),flush=True)
        if result['exit_code']:raise SystemExit(result['exit_code'])
