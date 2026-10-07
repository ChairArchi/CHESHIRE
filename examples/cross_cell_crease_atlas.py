"""Small review contact sheets from existing registered evidence only."""
import argparse
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from cross_cell_crease_study import read,write,bounded_worker
from cross_cell_crease_views import best_attempt


def prepare(root,phase,names,view='front',suffix=''):
    output=root/'renders'/phase; output.mkdir(parents=True,exist_ok=True)
    images=[]
    for name in names:
        directory=best_attempt(root,phase,name);summary=read(directory/'summary.json')
        stage=summary['stages'][-1]['stage'];file=output/(name+'_'+stage+'_'+view+'.png')
        if not file.exists():raise ValueError('Actual view missing: '+file.name)
        images.append(file.name)
    sheets=[dict(file=f'ATLAS_{view}_{suffix}_{i//6+1:02d}.png',title=phase+' / '+view+' / '+suffix+' / actual registered output',
        images=images[i:i+6],width=600,height=600,columns=3) for i in range(0,len(images),6)]
    plan=output/('atlas_plan_'+view+'_'+suffix+'.json');write(plan,dict(frames=[],sheets=sheets));return plan


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--phase',required=True)
    p.add_argument('--run',nargs='+',required=True);p.add_argument('--view',default='front');p.add_argument('--suffix',default='')
    a=p.parse_args();plan=prepare(a.output_root,a.phase,a.run,a.view,a.suffix)
    # Pure six-image contact sheets; geometry has already been rendered under guard.
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'tools/crease_projection.ps1'),'-PlanPath',str(plan)],check=True)
