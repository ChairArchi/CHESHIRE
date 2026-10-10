"""Render saved, actually applied region masks on a topology-preserving stage."""
import argparse,json
from pathlib import Path
import numpy as np
from gateflow.engine import ArrayMesh,surface
from gateflow.render import render,sheet
p=argparse.ArgumentParser();p.add_argument('stage',type=Path);a=p.parse_args()
st=np.load(a.stage/'state.npz');op=np.load(a.stage/'operator_state.npz')
m=ArrayMesh(st['xyz'],st['faces'],st['classes'],st['rest'],st['anchors'],int(st['generation']));tm=surface(m)
labels={'region_opening':'Opening edge','region_transition':'Support-lintel transition','region_lintel':'Lintel flow','region_deformation':'Local geometry','region_primary':'Primary flow','region_mask':'Combined response'}
items=[];statistics={}
for key,label in labels.items():
 if key not in op:continue
 values=op[key]
 extra=[values[q[q>=0]].mean() for q in m.faces if (q>=0).sum()>4]
 if extra:values=np.r_[values,extra]
 if len(values)!=len(tm.vertices):raise ValueError('Choose a pleat_flow stage with unchanged topology')
 colors=np.c_[.1+.85*values,.25+.27*(1-np.abs(2*values-1)),.65*(1-values)+.08*values,np.ones(len(values))]
 colored=tm.copy();colored.visual.vertex_colors=(colors*255).astype(np.uint8)
 out=a.stage/'region_maps'/key;out.parent.mkdir(exist_ok=True)
 render(colored,out,600,use_vertex_colors=True)
 items.append((out/'front.png',label+' | blue low / orange high'))
 statistics[key]=np.quantile(values,[0,.1,.5,.9,1]).tolist()
sheet(items,a.stage/'region_maps.png',size=450,columns=3)
(a.stage/'region_statistics.json').write_text(json.dumps(statistics,indent=2))
