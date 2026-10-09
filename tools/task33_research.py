"""Independent immutable Task33 workers and matched native mesh evidence."""
import argparse
import json
import shutil
import sys
from pathlib import Path
from time import perf_counter
import numpy as np

REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
from task33_preserve import ROOT, sha, write_new
from task31_study import basic_gate
from task29_search import save_mesh,load_mesh
from hero_design_sprint import guarded,windows_memory
from cheshire.task33_folds import initial_chart,refine,refine_section,evaluate,reflection_error
from task32_validation import embedding,section_segments
from task32_full_contacts import full_contacts

SOURCES=['src/cheshire/task33_folds.py','tools/task33_research.py','tools/task33_preserve.py',
         'src/cheshire/reference_subdivision.py','src/cheshire/progressive_gates.py',
         'tools/task31_study.py','examples/task29_search.py','examples/hero_design_sprint.py',
         'tools/task32_validation.py','tools/task32_full_contacts.py','tools/task33_contacts.py','src/cheshire/task32_morphology.py']


def preflight(request):
    g=request.get('final_generation',5)
    if not isinstance(g,int) or g<1:raise ValueError('Positive generation required.')
    faces=80*4**g
    ram=windows_memory()
    estimated=512*1024**2+faces*3000
    if ram['status']!='MEASURED' or estimated>min(12*1024**3,ram['available_bytes']*.55):
        raise MemoryError('Measured RAM cannot accommodate predicted sampling and validation.')
    free=shutil.disk_usage(ROOT.parent).free
    if free<4*1024**3+faces*1000:raise OSError('Insufficient reserved disk space.')
    return dict(forecast_faces_upper=faces,estimated_working_bytes=estimated,available=ram,disk_free=free)


def checkpoint(dest,m,state,meta,op,parent,fields=None):
    summary=save_mesh(dest,m,meta,op,parent)
    np.savez_compressed(dest/'material_state.npz',**state)
    if fields is not None:np.savez_compressed(dest/'fold_state.npz',**fields)
    write_new(dest/'identity.json',dict(files={p.name:sha(p) for p in dest.iterdir() if p.is_file()},
        parent_mesh_sha256=sha(parent/'mesh.npz') if parent else None))
    return summary


def run(request,tag):
    job=ROOT/'candidates'/tag
    job.mkdir(parents=True,exist_ok=False)
    write_new(job/'request.json',request)
    write_new(job/'preflight.json',preflight(request))
    snap=job/'source';snap.mkdir()
    for relative in SOURCES:
        p=snap/relative;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/relative,p)
    write_new(job/'source_identity.json',{p:sha(REPO/p) for p in SOURCES})
    m=basic_gate();state=initial_chart(m);parent=None;history=[]
    initial=job/'S00_CARRIER';checkpoint(initial,m,state,dict(level=0),None,None);parent=initial
    params=request.get('parameters',{})
    onset=request.get('macro_generation',3); child=request.get('child_generation',4);micro=request.get('micro_generation',5)
    maximum=request.get('levels',3)
    old_level=0
    for g in range(1,request.get('final_generation',5)+1):
        start=perf_counter()
        if g>=request.get('section_refine_start',999):
            m,state,meta,op=refine_section(m,state)
        else:
            m,state,meta,op=refine(m,state,carrier_smoothing=g<=request.get('carrier_smoothing_end',0),
                                smooth_geometry=request.get('smooth_after_macro',False) and g>onset)
        before=job/f'G{g}_PRE'
        checkpoint(before,m,state,meta,op,parent)
        level=min(maximum,int(g>=onset)+int(g>=child)+int(g>=micro))
        if level:
            folded,ff=evaluate(m,state,params,level)
            if request.get('incremental',False) and old_level:
                previous,_=evaluate(m,state,params,old_level)
                folded.xyz=m.xyz+folded.xyz-previous.xyz
            m=folded
            after=job/f'G{g}_FOLD'
            meta=dict(operation='Incremental child differences on interpolated geometry' if request.get('incremental',False) else 'Re-evaluate finite physical-scale folds on same material carrier',generation=g,levels=level,
                      requested=params,actual_depth_range=[float(ff['depth'].min()),float(ff['depth'].max())],
                      actual_fan_range=[float(ff['fan'].min()),float(ff['fan'].max())],
                      actual_twist_angle_range=[float(ff['twist_angle'].min()),float(ff['twist_angle'].max())],
                      actual_width_range=[float(ff['width'].min()),float(ff['width'].max())],
                      actual_depth_envelope_range=[float(ff['depth_envelope'].min()),float(ff['depth_envelope'].max())],
                      symmetry_constructive_chart_max=reflection_error(state,m.xyz),
                      no_geometric_smoothing=not(request.get('smooth_after_macro',False) and g>onset),scale='Original unresolved project units; not edge-length scaling.')
            checkpoint(after,m,state,meta,None,before,ff)
            parent=after
        else:parent=before
        old_level=level
        history.append(dict(generation=g,level=level,stage=str(parent),seconds=perf_counter()-start,vertices=len(m.xyz),faces=len(m.faces)))
        print(tag,g,level,len(m.faces),round(history[-1]['seconds'],2),flush=True)
    write_new(job/'completed.json',dict(final_stage=str(parent),history=history,source=sha(job/'source_identity.json'),request_sha256=sha(job/'request.json')))


def audit(request,tag):
    dest=ROOT/'validation'/tag;dest.mkdir(parents=True,exist_ok=False);records=[]
    write_new(dest/'request.json',request)
    write_new(dest/'source_identity.json',{p:sha(REPO/p) for p in SOURCES})
    for item in request['items']:
        stage=Path(item['stage']);m=load_mesh(stage);start=perf_counter()
        contact_check=full_contacts
        if request.get('radius_bins',False):
            from task33_contacts import contacts
            contact_check=contacts
        forecast=512*1024**2+len(m.faces)*3000
        ram=windows_memory()
        if ram['status']!='MEASURED' or forecast>min(12*1024**3,ram['available_bytes']*.55):raise MemoryError('Audit forecast exceeds measured safety reserve.')
        result=dict(**item,mesh_sha256=sha(stage/'mesh.npz'),forecast_working_bytes=forecast,embedding=embedding(m),contacts=contact_check(m))
        section_info,segments=section_segments(m)
        np.savez_compressed(dest/(item['id']+'_sections.npz'),**segments)
        result.update(sections=section_info,section_sha256=sha(dest/(item['id']+'_sections.npz')),seconds=perf_counter()-start)
        write_new(dest/(item['id']+'.json'),result);records.append(result)
        print(item['id'],'contacts',result['contacts']['transverse_contacts'],'opposed',result['embedding']['opposed_quad_fan_normals'],round(result['seconds'],2),flush=True)
    write_new(dest/'summary.json',records)


def render(request,tag):
    import task31_views
    task31_views.ROOT=ROOT
    task31_views.render(request,tag)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--action',choices=['run','audit','render','raking','measure','evidence','planar','progression','export','tracks','deliver'],required=True)
    p.add_argument('--request',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');args=p.parse_args()
    if not args.tag.replace('_','').isalnum():raise ValueError('Safe tag required.')
    if args.worker:
        if args.action=='render':render(args.request,args.tag)
        elif args.action=='raking':
            from task33_views import raking
            raking(args.request,args.tag)
        elif args.action in ('measure','evidence','planar','progression','export','tracks','deliver'):
            module=__import__('task33_'+args.action)
            function=getattr(module,'audit' if args.action=='planar' else args.action)
            function(json.loads(args.request.read_text(encoding='utf-8'))['candidate'],args.tag)
        else:globals()[args.action](json.loads(args.request.read_text(encoding='utf-8')),args.tag)
    else:
        definition=json.loads(args.request.read_text(encoding='utf-8'))
        if args.action=='run':preflight(definition)
        if args.action in ('measure','evidence','planar','progression','export','tracks','deliver'):
            preflight(json.loads((ROOT/'candidates'/definition['candidate']/'request.json').read_text()))
        logs=ROOT/'logs'/(args.action+'_'+args.tag)
        if logs.exists():raise FileExistsError('Existing Task33 logs are immutable: '+str(logs))
        result=guarded(['--action',args.action,'--request',str(args.request),'--tag',args.tag,'--worker'],logs,worker_script=Path(__file__))
        write_new(ROOT/'resources'/(args.action+'_'+args.tag+'.json'),result)
        print(json.dumps(result),flush=True)
        if result['exit_code']:raise SystemExit(result['exit_code'])
