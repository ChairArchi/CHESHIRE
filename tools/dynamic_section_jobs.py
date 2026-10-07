"""Task27 finite-memory wrappers for existing capture/native/evidence tools."""
import argparse
from pathlib import Path
import subprocess,sys
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
from hero_design_sprint import guarded
from dynamic_section_gates import directory


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--kind',choices=['capture','native','evidence','package'],required=True)
    p.add_argument('--name');p.add_argument('--names',nargs='+');p.add_argument('--tag')
    p.add_argument('--views',nargs='+',default=['front','oblique','detail']);p.add_argument('--resolution',type=int,default=1600)
    p.add_argument('--revision',default='R2');p.add_argument('--generation',type=int,default=4);p.add_argument('--comparison-generation',type=int)
    p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.kind=='native' and a.worker:
        obj=directory(a.output_root,a.name)/(a.name+'.obj')
        r=subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(REPO/'tools/dynamic_section_native.ps1'),
            '-ArtifactRoot',str(a.output_root),'-ObjPath',str(obj),'-Name',a.name],creationflags=subprocess.CREATE_NO_WINDOW)
        sys.exit(r.returncode)
    tag=a.tag or a.name or (a.revision+'_G'+str(a.generation))
    logs=a.output_root/'logs'/(a.kind+'_'+tag)
    if logs.exists():raise ValueError('Keep existing job log; use a new tag.')
    args=['--output-root',str(a.output_root)]
    if a.kind=='capture':
        script=REPO/'tools/dynamic_section_views.py';args+=['--names',*a.names,'--tag',a.tag,'--views',*a.views,'--resolution',str(a.resolution)]
    elif a.kind=='native':
        script=Path(__file__);args+=['--kind','native','--name',a.name,'--worker']
    else:
        script=REPO/'tools'/('dynamic_section_'+a.kind+'.py');args+=['--revision',a.revision,'--generation',str(a.generation)]
        if a.kind=='evidence' and a.comparison_generation is not None:args+=['--comparison-generation',str(a.comparison_generation)]
    r=guarded(args,logs,worker_script=script);print(r,flush=True);sys.exit(r['exit_code'])
