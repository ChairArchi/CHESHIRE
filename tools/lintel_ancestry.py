"""Inspect retained Task24 geometry; no regeneration or sculpting."""
import argparse
from collections import Counter
from pathlib import Path
import sys

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'examples'))
from cross_cell_crease_study import read,write,file_hash,raw_mesh
from hero_design_views import matrix,rotated
from cheshire import save_mesh


def prepare(root,previous):
    out=root/'analysis';out.mkdir(parents=True,exist_ok=True)
    h1=previous/'designs/H1/attempt_002'
    stages=[('C07',previous/'inputs/BACKBONE_S05.json.gz',previous/'inputs/BACKBONE_S05_lineage.json.gz')]
    stages += [('H1_'+s,h1/(s+'.json.gz'),h1/(s+'_lineage.json.gz')) for s in ['S01','S02','S03','S04','S05','S06','S07']]
    stages += [(name,previous/'designs'/name/'attempt_002'/'terminal.json.gz',previous/'designs'/name/'attempt_002'/'terminal_lineage.json.gz') for name in ['H2_R1']]
    stages += [('H3_R3',previous/'designs/H3_R3/attempt_001/terminal.json.gz',previous/'designs/H3_R3/attempt_001/terminal_lineage.json.gz')]
    older=previous.parent/'task23/inputs'
    early=[]
    for s in ['S01','S02','S03','S04']:
        name='BACKBONE_'+s;p=older/(name+'.json.gz');q=older/(name+'_lineage.json.gz')
        if p.exists() and q.exists():early.append((name,p,q))
    stages+=early
    views={'whole':(matrix(0,-12),[-400,0,2000],8600),
           'underside':(matrix(0,-30),[-400,0,2450],2200),
           'detail':(matrix(0,-12),[-400,0,2450],1800),
           'detail_angle':(matrix(18,-25),[-400,0,2450],1800)}
    records=[];frames=[]
    for name,geometry,lineage in stages:
        data=read(geometry);mesh=raw_mesh(data);history=read(lineage)['history']
        obj=out/(name+'.obj');save_mesh(mesh,obj)
        region=[f for f in mesh.faces() if abs(mesh.face_centroid(f)[0]+400)<700 and 1600<mesh.face_centroid(f)[2]<3000]
        records.append(dict(id=name,geometry=str(geometry),geometry_sha256=file_hash(geometry),
            lineage=str(lineage),lineage_sha256=file_hash(lineage),vertices=mesh.number_of_vertices(),faces=mesh.number_of_faces(),
            region_face_ids=region,C0_ancestry=dict(Counter(str(history[str(f)]['source']) for f in region)),
            region_event_ids=sorted({e for f in region for e in history[str(f)]['events']}),
            region_definition=dict(x_center=-400,x_half_width=700,z_min=1600,z_max=3000,y='all'),
            native_view_input=str(obj)))
        for view,(m,target,width) in views.items():
            transformed=rotated(data,m);t=[sum(a*b for a,b in zip(row,target)) for row in m]
            write(out/(name+'_'+view+'.json'),transformed)
            bounds=[t[0]-width/2,t[0]+width/2,t[2]-width/2,t[2]+width/2]
            frames.append(dict(mesh=name+'_'+view+'.json',file=name+'_'+view+'.png',label=name+' / '+view+' / polygon preview',
                camera='front',width=720,height=720,bounds=bounds))
    sheets=[dict(file='ancestry_'+view+'.png',title='Task25 / preserved checkpoints / fixed region and scale / painter occlusion approximate',
        images=[name+'_'+view+'.png' for name,_,_ in stages[:8]],width=720,height=720,columns=4) for view in ['detail','underside']]
    sheets += [dict(file='scouting_'+view+'.png',title='Task25 / retained alternative paths / common scale',images=[name+'_'+view+'.png' for name in ['H1_S07','H2_R1','H3_R3']],width=720,height=720,columns=3) for view in ['whole','detail']]
    if early:sheets.append(dict(file='backbone_detail.png',title='Task25 / original earlier backbone checkpoints / fixed region',
        images=[name+'_detail.png' for name,_,_ in early]+['C07_detail.png'],width=720,height=720,columns=3))
    write(out/'ancestry_map.json',dict(records=records,cameras={k:dict(matrix=m,target=t,width=w) for k,(m,t,w) in views.items()},
        source_baseline='385ec86c1f18ee1e2e0d61e2b32c524ceccfb683',units='Original unknown physical units; no scaling',
        evidence='Actual saved checkpoint XYZ/connectivity; existing System.Drawing polygon renderer.'))
    write(out/'ancestry_plan.json',dict(frames=frames,sheets=sheets))
    return out/'ancestry_plan.json'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--previous-root',type=Path,default=Path('E:/CHESHIRE_DATA/task24'))
    a=p.parse_args();print(prepare(a.output_root,a.previous_root))
