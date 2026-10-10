import argparse,json
from pathlib import Path
from gateflow.pipeline import run
p=argparse.ArgumentParser()
p.add_argument('--input',type=Path,required=True)
p.add_argument('--config',type=Path,default=Path(__file__).parent/'configs/default.json')
p.add_argument('--output',type=Path,required=True)
p.add_argument('--seed',type=int)
p.add_argument('--component',type=Path,help='Replace the porous input for every Tissue projection stage')
p.add_argument('--no-render',action='store_true')
p.add_argument('--resume-stage',type=Path,help='Reuse a completed, identical recipe prefix checkpoint')
a=p.parse_args();config=json.loads(a.config.read_text())
if a.component:
 for stage in config['stages']:
  if stage['op']=='tessellate':stage['component']=str(a.component.resolve())
r=run(a.input,config,a.output,a.seed,a.no_render,a.resume_stage)
print(json.dumps({'status':r['status'],'final':r['final']}))
