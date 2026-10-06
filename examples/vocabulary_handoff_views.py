"""Retain/compare actual pre-DS, post-DS and post-inset checkpoints."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from subdivision_capability_study import read,write
from ornament_study import digest
from vocabulary_review import STUDY,cases,gz_read

def main():
    folder=STUDY/'views/HANDOFFS'; folder.mkdir(parents=True,exist_ok=True)
    bounds=read(ROOT/'studies/task19/camera.json')['bounds']; frames=[]; records=[]
    for name in ('B4_05','B4_10'):
        case=next(p for p in cases('R') if p.parent.name=='HANDOFF_'+name)
        original=read(STUDY/'B'/name/'attempt_001/summary.json'); summary=read(case/'summary.json')
        labels={10:'PRE_DS',11:'POST_DS',12:'POST_NESTED_INSET'}; checkpoints=[]
        for index,label in labels.items():
            path=case/f'S{index:02d}.json.gz'
            if not path.exists(): continue
            geometry=gz_read(path); expected=original['stages'][index-1]['geometry_sha256']
            assert digest(geometry)==expected, 'Handoff diagnostic must replay actual primary coordinates/cycles.'
            checkpoints.append(dict(stage=index,label=label,exact_primary_geometry=True,sha256=expected,faces=len(geometry['faces'])))
            cache=folder/f'{name}_{label}_checkpoint_cache.json'; write(cache,geometry)
            for view in ('front','oblique','detail'):
                frames.append(dict(mesh=str(cache.relative_to(STUDY)),file=f'views/HANDOFFS/{name}_{label}_{view}.png',
                    label=f'{name} {label} / actual F={len(geometry["faces"])} / no new parameter',camera='front' if view=='front' else 'oblique',
                    bounds=bounds[view],width=900,height=900))
        records.append(dict(id=name,status=summary['status'],checkpoints=checkpoints,
            assessment='Compare sharp pre-DS features to actual structural DS, then additional inset. Face count alone does not establish a new ornament scale.'))
    sheets=[]
    for view in ('oblique','detail'):
        sheets.append(dict(file=f'views/HANDOFFS/handoff_{view}_sheet.png',title='Exact replay of two primary DS handoffs: pre-DS / post-DS / nested inset; fixed camera',
            images=[f['file'] for f in frames if f['file'].endswith('_'+view+'.png')],columns=3,width=900,height=900))
    write(STUDY/'handoff_identity.json',records); write(STUDY/'HANDOFFS_projection_plan.json',dict(frames=frames,sheets=sheets))
    print('handoff checkpoints',sum(len(r['checkpoints']) for r in records))

if __name__=='__main__': main()
