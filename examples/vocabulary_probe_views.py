"""Project actual raw unit-quad outputs without stitching their polygons."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from subdivision_capability_study import read,write

def main():
    out=ROOT/'output/task21'; folder=out/'probe_views'; folder.mkdir(exist_ok=True)
    rows=read(out/'operator_probes.json')['probes']; frames=[]
    choices=[('normal','Extrude',[[0,0,1],.18]),('lateral','Extrude',[[.8,0,.6],.24]),
        ('strips','LinearSplitQuad',[.3,0]),('borders','LinearSplitQuadBorder',[.18,.18,1]),
        ('ridge','Roof',[.2,.2]),('long_ridge','Roof',[.2,0])]
    for label,name,params in choices:
        row=next(r for r in rows if r['fixture']=='unit_quad' and r['operator']==name and r['parameters']==params)
        data=dict(vertices=[],faces=[])
        for i,face in enumerate(row['output']):
            keys=[]
            for xyz in face:
                keys.append(len(data['vertices'])); data['vertices'].append(dict(id=keys[-1],xyz=xyz))
            data['faces'].append(dict(id=i,vertices=keys))
        write(folder/(label+'.json'),data)
        frames.append(dict(mesh='probe_views/'+label+'.json',file='probe_views/'+label+'.png',
            label=f'RAW UNIT {name} {params}; independent returned polygons; not gate topology',
            camera='oblique',bounds=[-.2,1.85,-.1,.85],width=900,height=600,wireframe=True))
    write(out/'probe_projection_plan.json',dict(frames=frames,sheets=[dict(file='probe_views/operator_sheet.png',
        title='Actual official DLL unit-quad outputs / same projection and scale / no stitching',images=[f['file'] for f in frames],columns=3,width=900,height=600)]))

if __name__=='__main__': main()
