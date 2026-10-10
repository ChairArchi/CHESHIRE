import argparse,json
from pathlib import Path
from gateflow.engine import *
from gateflow.input import write
from gateflow.render import render
from cheshire.reference_subdivision import cube
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--thickness',type=float,default=.12);p.add_argument('--kind',choices=['cell','fiber'],default='cell');a=p.parse_args()
if a.output.exists():raise FileExistsError(a.output)
a.output.mkdir(parents=True)
m=cube(1.);cfg=dict(field_radius=.12,feedback=.3,region_gain=[1,1,1,1]);obs=observe(m,np.zeros(len(m.xyz)),np.zeros(len(m.faces),int),cfg)
out,meta,state=tissue(m,obs,dict(thickness=a.thickness),1.,30000)
if a.kind=='fiber':
 obs=observe(out,np.zeros(len(out.xyz)),np.zeros(len(out.faces),int),cfg)
 out,_,_=cc(out,obs,dict(weights=dict(wf=.02,we=-.015,w1=.1,w2=0),contrast=0),1.,30000)
checks=validate(out,30000)
write(a.output/'component.json',dict(schema='cheshire-component/1',source='Tissue porous-cell input, refined by weighted CC for fiber mode; not a final gate template',mapping=dict(xy_scale=[.3,1.15] if a.kind=='fiber' else [1.,1.],z_factor=.35 if a.kind=='fiber' else 1.),mesh=dict(vertices=out.xyz.tolist(),faces=[q[q>=0].tolist() for q in out.faces]),operator=meta,checks=checks))
surface(out).export(a.output/'component.obj');surface(out).export(a.output/'component.ply');render(surface(out),a.output/'views',650);print(checks)
