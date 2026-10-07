"""Reuse the established RAM guard for the actual RhinoCommon export process tree."""
import argparse
from pathlib import Path
import subprocess
import sys

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'examples'))
from progressive_gates import parent_directory
from hero_design_sprint import guarded


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--name',required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.worker:
        obj=parent_directory(a.output_root,a.name)/(a.name+'.obj')
        result=subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',
            str(REPO/'tools/progressive_gate_native.ps1'),'-ArtifactRoot',str(a.output_root),
            '-ObjPath',str(obj),'-Name',a.name],creationflags=subprocess.CREATE_NO_WINDOW)
        sys.exit(result.returncode)
    else:
        logs=a.output_root/'logs'/('native_'+a.name)
        if logs.exists():raise ValueError('Preserve native run log; do not overwrite.')
        result=guarded(['--output-root',str(a.output_root),'--name',a.name,'--worker'],logs,worker_script=Path(__file__))
        print(result,flush=True);sys.exit(result['exit_code'])
