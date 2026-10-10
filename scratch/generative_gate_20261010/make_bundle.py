"""Build a reusable porous bundle INPUT from the existing Tissue cell geometry."""
import argparse,json
from pathlib import Path
import numpy as np
from gateflow.engine import ArrayMesh,validate,surface
from gateflow.input import write,sha
from gateflow.render import render
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=Path('components/fiber14/component.json'));p.add_argument('--output',type=Path,required=True);p.add_argument('--count',type=int,default=3);a=p.parse_args()
if not 1<=a.count<=5:raise ValueError('Use 1 to 5 input strands')
if a.output.exists():raise FileExistsError(a.output)
a.output.mkdir(parents=True)
j=json.loads(a.source.read_text());v=np.array(j['mesh']['vertices']);q=np.array(j['mesh']['faces']);lo=v.min(0);extent=np.ptp(v,axis=0);unit=(v-lo)/extent-.5
xyz=[];faces=[]
for k in range(a.count):
 t=unit[:,1]+.5;taper=.55+.45*np.sin(np.pi*t)
 points=unit.copy();points[:,0]=.14*unit[:,0]*taper+(k-(a.count-1)/2)*.23*(.4+.6*np.sin(np.pi*t))
 points[:,2]=.12*unit[:,2]*taper+.10*np.sin(np.pi*t)
 xyz.append(points);faces.append(q+k*len(v))
xyz=np.concatenate(xyz);faces=np.concatenate(faces)
m=ArrayMesh(xyz,faces,np.full(len(xyz),-1,np.int8),xyz.copy(),np.full((len(faces),3),-1,int))
checks=validate(m,10000)
write(a.output/'component.json',dict(schema='cheshire-component/1',source='Curved bundle of existing Tissue porous cells; independent INPUT, not a gate template',source_sha256=sha(a.source),strand_count=a.count,mapping=dict(xy_scale=[.65,6.],z_factor=.7),mesh=dict(vertices=xyz.tolist(),faces=faces.tolist()),checks=checks,limitations='Separate closed porous strands; not fused at converging ends'))
surface(m).export(a.output/'component.obj');surface(m).export(a.output/'component.ply');render(surface(m),a.output/'views',800)
print(json.dumps(checks))
