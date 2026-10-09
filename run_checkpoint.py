from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).parent/'src'))
import numpy as np
from subdivision import column,cc,ds,check,save_obj,settings,Mesh
from render import render,sheet

root=Path(__file__).parent; out=root/'output'; out.mkdir(exist_ok=True)
# Only four fixed short sequences, G0-G3. No optimizer or exploration loop.
tracks=[('standard_cc',[cc]*3,True),('modified_cc',[cc]*3,False),
        ('modified_ds',[ds]*3,False),('mixed_cc_ds_cc',[cc,ds,cc],False)]
rows=[]; report={}
for name,ops,standard in tracks:
    m=column(); report[name]=[]; row=[]
    for g in range(4):
        if g: m=ops[g-1](m,g,standard)
        report[name].append(check(m)); save_obj(m,out/f'{name}_G{g}.obj')
        row.append(render(m.v,m.f,out/f'{name}_G{g}.png',f'{name.replace("_"," ")} | G{g}'))
    rows.append(row)
sheet(rows,out/'checkpoint_A.png','A | Independent column subdivision | G0 to G3')
rows[0][0].save(out/'G0.png')
# Minimal exact mathematical sanity checks, not a regression campaign.
cube=Mesh(np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]],float),
          [[3,2,1,0],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]])
c=cc(cube,1,True); assert np.allclose(c.v[0],[-5/9]*3); check(c)
d=ds(cube,1,True); assert np.allclose(d.v[0],[-.5,.5,-1]); check(d)
for op in (cc,ds):
    shifted=Mesh(cube.v+[2,3,4],cube.f)
    assert np.allclose(op(shifted,1,True).v,op(cube,1,True).v+[2,3,4])
report['checks']=['closed oriented two-manifold and Euler 2 each mesh','finite nondegenerate faces',
                  'standard CC cube corner = (-5/9,-5/9,-5/9)',
                  'standard DS cube corner = (-1/2,1/2,-1)',
                  'standard CC/DS translation equivariance']
report['settings']={str(g):{str(z):settings(g,np.array([0,0,z])) for z in [-2,2]} for g in [1,2,3]}
(out/'checkpoint.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:[(x['vertices'],x['faces']) for x in v] for k,v in report.items() if k not in ['checks','settings']}))
