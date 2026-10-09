"""Independent Task34 runs, native geometry, controls and guarded evidence."""
import argparse,json,shutil,sys
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_preserve import sha,write_new
from task29_search import save_mesh,load_mesh
from task31_study import basic_gate
from hero_design_sprint import guarded,windows_memory
from cheshire.task34_refolding import carrier,native,refine,macro,refold,symmetry
ROOT=Path('E:/CHESHIRE_DATA/task34')
SOURCES=['src/cheshire/task34_refolding.py','tools/task34_research.py',
         'src/cheshire/reference_subdivision.py','src/cheshire/progressive_gates.py',
         'tools/task31_study.py','examples/task29_search.py','examples/hero_design_sprint.py',
         'tools/task33_preserve.py','tools/task33_contacts.py','tools/task32_validation.py',
         'tools/task33_views.py','tools/task33_planar.py','tools/task33_deliver.py']


def preflight(request):
    g=request.get('final_generation',5)
    if not isinstance(g,int) or not 3<=g<=8:raise ValueError('Declared sampling generations 3..8 required.')
    predicted=256*4**g+16*2**g;ram=windows_memory();forecast=512*1024**2+predicted*3000
    if ram['status']!='MEASURED' or forecast>min(12*1024**3,.55*ram['available_bytes']):raise MemoryError('Forecast exceeds measured reserve.')
    free=shutil.disk_usage(ROOT.parent).free
    if free<4*1024**3+predicted*1000:raise OSError('Disk reserve insufficient.')
    return dict(predicted_triangles=predicted,forecast_working_bytes=forecast,available=ram,disk_free=free)


def checkpoint(dest,state,generation,metadata,parent=None,operator=None,controls=None):
    mesh,chart,_=native(state,generation)
    summary=save_mesh(dest,mesh,dict(**metadata,symmetry=symmetry(mesh,chart)),operator,parent)
    np.savez_compressed(dest/'formation_state.npz',**state)
    np.savez_compressed(dest/'material_state.npz',chart=chart)
    if controls:np.savez_compressed(dest/'control_state.npz',**controls)
    write_new(dest/'identity.json',dict(files={p.name:sha(p) for p in dest.iterdir() if p.is_file()},parent_mesh_sha256=sha(parent/'mesh.npz') if parent else None))
    return summary


def run(request,tag):
    allowed={'carrier','macro','refold','criterion','final_generation','macro_generation','fold_generations'}
    if set(request)-allowed:raise ValueError('Unknown run request.')
    criterion=request.get('criterion','current')
    if criterion not in ('current','frozen_macro'):raise ValueError('Explicit geometry criterion required.')
    job=ROOT/'candidates'/tag;job.mkdir(parents=True,exist_ok=False)
    write_new(job/'request.json',request);write_new(job/'preflight.json',preflight(request))
    for rel in SOURCES:
        dest=job/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/rel,dest)
    write_new(job/'source_identity.json',{rel:sha(REPO/rel) for rel in SOURCES})
    state=carrier(basic_gate(),request.get('carrier','uniform'));parent=job/'G0_CARRIER'
    checkpoint(parent,state,0,dict(operation='Elliptical coarse role carrier; common centreline and overall coarse bounds. No Task33 state overwritten.'))
    history=[];frozen=None;frozen_parent=None;onset=request.get('macro_generation',3);folds=request.get('fold_generations',[4,5])
    if len(folds)!=len(set(folds)) or any(g<=onset for g in folds):raise ValueError('Distinct later folding stages required.')
    for generation in range(1,request.get('final_generation',5)+1):
        start=perf_counter();state,op=refine(state);before=job/f'G{generation}_PRE'
        checkpoint(before,state,generation,dict(operation='Bilinear grid refinement. Existing grid and quad-centre vertices unchanged. New centre fans define the sampled surface.'),parent,op)
        parent=before
        if frozen is not None:
            frozen,_=refine(frozen)
        if generation==onset:
            state,controls=macro(state,request.get('macro',{}));after=job/f'G{generation}_FORM'
            checkpoint(after,state,generation,dict(operation='Finite radial protrusions, physical distance and convergence envelope.',requested=request.get('macro',{})),before,controls=controls)
            frozen=state;frozen_parent=after;parent=after
        elif generation in folds:
            source=state;source_stage=before
            if criterion=='frozen_macro':
                source=frozen;source_stage=job/f'G{generation}_REFERENCE'
                checkpoint(source_stage,source,generation,dict(operation='Frozen first-formation geometry, resampled without refolding.'),frozen_parent);frozen_parent=source_stage
            state,controls,features=refold(state,source,request.get('refold',{}));after=job/f'G{generation}_FOLD'
            flat=[f for row in features for f in row]
            summary=dict(operation='Read actual source edge polylines, crest width/prominence/curvature and longitudinal shape, then apply the explicitly requested crest operation.',
                criterion=criterion,source_stage=str(source_stage),source_mesh_sha256=sha(source_stage/'mesh.npz'),requested=request.get('refold',{}),
                actual_requested_range=[float(controls['requested_radial'].min()),float(controls['requested_radial'].max())],
                actual_applied_range=[float(controls['applied_radial'].min()),float(controls['applied_radial'].max())],
                active_grid_vertices=int(np.count_nonzero(controls['applied_radial'])),measured_features=len(flat),
                geometry_smoothing=False,vertex_locks=False,scale='Absolute original project units and measured parent prominence/arc width, independent of cell length.',
                feature_limit='Projected ring-polyline curvature, fixed angular signal filter; not general principal curvature or certified continuous ridges.',
                distance_meaning='Requested/applied signed fold component along the selected unit direction. Total actual XYZ displacement is separately stored; it also includes the longitudinal component.',
                axial_feature_columns=['material_s','actual_centre_arc','peak_excess','prominence','left_half_width','right_half_width'],
                ownership='Canonical left/front source features copied before displacement; vector parity reflected, no XYZ averaging.')
            checkpoint(after,state,generation,summary,before,controls=controls)
            write_new(after/'features.json',dict(source=str(source_stage),source_mesh_sha256=sha(source_stage/'mesh.npz'),features=flat,
                measurement_samples=512,scalar_sigma_angle=.035,geometry_smoothing=False))
            # Include the feature log in the checkpoint identity without rewriting it.
            write_new(after/'feature_identity.json',dict(features_sha256=sha(after/'features.json')))
            parent=after
        mesh,_,_=native(state,generation)
        history.append(dict(generation=generation,stage=str(parent),vertices=len(mesh.xyz),triangles=len(mesh.faces),seconds=perf_counter()-start))
        print(tag,generation,len(mesh.faces),round(history[-1]['seconds'],2),flush=True)
    write_new(job/'completed.json',dict(final_stage=str(parent),history=history,request_sha256=sha(job/'request.json'),source_identity_sha256=sha(job/'source_identity.json')))


def audit(request,tag):
    from task32_validation import embedding,section_segments
    from task33_contacts import contacts
    dest=ROOT/'validation'/tag;dest.mkdir(parents=True,exist_ok=False);write_new(dest/'request.json',request);rows=[]
    for item in request['items']:
        start=perf_counter();stage=Path(item['stage']);mesh=load_mesh(stage);ram=windows_memory();forecast=512*1024**2+len(mesh.faces)*3000
        if ram['status']!='MEASURED' or forecast>min(12*1024**3,.55*ram['available_bytes']):raise MemoryError('Audit forecast exceeds measured reserve.')
        value=dict(**item,mesh_sha256=sha(stage/'mesh.npz'),embedding=embedding(mesh),contacts=contacts(mesh),forecast_working_bytes=forecast)
        if (stage/'material_state.npz').exists():value['symmetry']=symmetry(mesh,np.load(stage/'material_state.npz')['chart'],check_faces=bool(np.all(mesh.faces[:,3]==-1)))
        info,segments=section_segments(mesh);np.savez_compressed(dest/(item['id']+'_sections.npz'),**segments)
        value.update(sections=info,seconds=perf_counter()-start,source_sha256={p:sha(REPO/p) for p in ['tools/task34_research.py','tools/task33_contacts.py','tools/task32_validation.py']})
        write_new(dest/(item['id']+'.json'),value);rows.append(value)
        print(item['id'],'contacts',value['contacts']['transverse_contacts'],'seconds',round(value['seconds'],2),flush=True)
    write_new(dest/'summary.json',rows)


def render(request,tag):
    import task33_views
    task33_views.ROOT=ROOT
    task33_views.sheet=comparison_sheet
    definition=json.loads(Path(request).read_text())
    for item in definition['items']:
        stage=Path(item['stage'])
        if stage.is_relative_to(ROOT/'candidates'):
            if not item['label'].startswith(stage.parent.name+'_'+stage.name+'_'):raise ValueError('Render ID/generation must match native checkpoint.')
        elif stage!=Path('E:/CHESHIRE_DATA/task33/exports/V01_MIRRORED_TRIANGLES'):
            raise ValueError('Only explicit Task33 V01 baseline allowed for these comparisons.')
        elif not item['label'].startswith('TASK33_V01_'):raise ValueError('Baseline label must identify V01.')
    task33_views.raking(request,tag)


def comparison_sheet(records,path,cols=4,size=500):
    """Fixed image cells with readable exact IDs; no change to raw renders."""
    import re,textwrap
    from PIL import Image,ImageDraw,ImageFont
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    rowheight=size+80;out=Image.new('RGB',(cols*size,((len(records)+cols-1)//cols)*rowheight),'#f5f5f2');draw=ImageDraw.Draw(out)
    for i,record in enumerate(records):
        x=(i%cols)*size;y=(i//cols)*rowheight
        with Image.open(record['image']) as raw:out.paste(raw.resize((size,size)),(x,y))
        label=record['label'];match=re.match(r'(.*)_(G\d+_(?:CARRIER|PRE|FORM|FOLD|REFERENCE))_(.*)',label)
        lines=[match[1],match[2]+' | '+match[3]] if match else label.rsplit('_',1)
        lines=[part for line in lines for part in textwrap.wrap(line,width=45)]
        draw.multiline_text((x+8,y+size+5),'\n'.join(lines),font=font,fill='#222222',spacing=3)
    if Path(path).exists():raise FileExistsError(path)
    out.save(path)


def planar(request,tag):
    import task33_planar
    task33_planar.ROOT=ROOT;task33_planar.audit(request['candidate'],tag)


def deliver(request,tag):
    import task34_exchange
    task34_exchange.deliver(request['candidate'],tag)


def baseline(request,tag):
    import task33_research
    task33_research.ROOT=ROOT
    task33_research.run(request,tag)
    job=ROOT/'candidates'/tag
    shutil.copy2(Path(__file__),job/'source/tools/task34_research.py')
    write_new(job/'baseline_driver.json',dict(driver_sha256=sha(Path(__file__)),
        description='Unmodified Task33 algorithm, independent Task34 output root; only explicitly declared recipe controls differ.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--action',choices=['run','baseline','audit','render','planar','deliver'],required=True);p.add_argument('--request',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');args=p.parse_args()
    if not args.tag.replace('_','').isalnum():raise ValueError('Safe immutable tag required.')
    if args.worker:
        request=json.loads(args.request.read_text(encoding='utf-8'))
        globals()[args.action](args.request if args.action=='render' else request,args.tag)
    else:
        if args.action=='run':preflight(json.loads(args.request.read_text(encoding='utf-8')))
        if args.action=='baseline':
            import task33_research
            task33_research.ROOT=ROOT;task33_research.preflight(json.loads(args.request.read_text(encoding='utf-8')))
        logs=ROOT/'logs'/(args.action+'_'+args.tag)
        if logs.exists():raise FileExistsError('Task34 run logs are immutable.')
        result=guarded(['--action',args.action,'--request',str(args.request),'--tag',args.tag,'--worker'],logs,worker_script=Path(__file__))
        write_new(ROOT/'resources'/(args.action+'_'+args.tag+'.json'),result);print(json.dumps(result),flush=True)
        if result['exit_code']:raise SystemExit(result['exit_code'])
