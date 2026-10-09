from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).parent/'src'))
import numpy as np
from projection import frame,target,project,save_obj,check_frame
from render import render,sheet

root=Path(__file__).parent; out=root/'output'; out.mkdir(exist_ok=True)
iv,inf=frame(); tv,tf=target(); ov,receipts=project(iv,tv,tf)
assert np.allclose(ov[:,[0,2]],iv[:,[0,2]])
assert np.ptp(ov[:,1])>.1
stats=check_frame(ov,inf)
# One causal check, no search: hold INPUT fixed and change only target depth.
cv,cf=target(depth=1.35); control,_=project(iv,cv,cf)
delta=np.linalg.norm(control-ov,axis=1)
assert np.max(delta)>.3 and np.all(delta>0)
row=[]
for name,v,f,color in [('INPUT',iv,inf,(139,187,224)),('TARGET',tv,tf,(202,190,166)),('OUTPUT',ov,inf,(139,187,224))]:
    save_obj(v,f,out/f'{name}.obj')
    center=(v.min(axis=0)+v.max(axis=0))/2
    row.append(render(v-center,f,out/f'{name}.png',f'{name} | actual mesh',scale=130,color=color))
sheet([row],out/'checkpoint_B.png','B | Separate INPUT + TARGET -> ray-mapped OUTPUT')
report=dict(input=check_frame(iv,inf),output=stats,target_vertices=len(tv),target_faces=len(tf),
            ray_direction=[0,1,0],missed_rays=0,output_y_range=[float(ov[:,1].min()),float(ov[:,1].max())],
            target_only_control=dict(depth_before=.9,depth_after=1.35,
            maximum_output_displacement=float(delta.max()),minimum_output_displacement=float(delta.min())),
            triangle_hits=receipts,limits='Mapped frame is an open surface patch, not a Boolean cut or printable solid. Mesh faces approximate the sampled target surface; every vertex is exactly on a target triangle.')
(out/'checkpoint.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='triangle_hits'}))
