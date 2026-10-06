"""Audit independent Hero workers and prepare the fixed delivery comparisons."""
from collections import Counter
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from subdivision_capability_study import read,write
from ornament_study import digest
from vocabulary_review import STUDY,cases,gz_read
from vocabulary_reference_audit import oriented_polygons

PHASES=('A','B','C','F','R','HERO','REPLAY')


def reproduction():
    rows=[]
    for original in cases('HERO'):
        name=original.parent.name
        replay=next(p for p in cases('REPLAY') if p.parent.name==name)
        a=read(original/'summary.json'); b=read(replay/'summary.json')
        checks={}
        for filename in ('terminal.json','terminal_lineage.json.gz','terminal_signatures.json.gz','branch_tables.json.gz'):
            loader=gz_read if filename.endswith('.gz') else read
            x=loader(original/filename); y=loader(replay/filename)
            assert x==y, (name,filename)
            checks[filename]=dict(exact_decoded_payload=True,sha256=digest(x))
        checkpoints=[]
        for path in sorted(original.glob('S[0-9][0-9].json.gz')):
            other=replay/path.name
            assert gz_read(path)==gz_read(other)
            checkpoints.append(dict(file=path.name,exact_ordered_geometry=True,sha256=digest(gz_read(path))))
        assert a['recipe']==b['recipe'] and a['status']==b['status']
        rows.append(dict(id=name,status=a['status'],two_independent_external_workers=True,
            exact_recipe=True,terminal=checks,checkpoints=checkpoints,
            output_sha256=a['output_sha256'],runtime_seconds=[a['runtime_seconds'],b['runtime_seconds']]))
    # A rejected attempt is intentionally not eligible for the valid-case cache.
    failed=sorted((STUDY/'HERO/HERO_BRANCHING_PLATES').glob('attempt_*'))
    assert len(failed)==2 and read(failed[0]/'terminal.json')==read(failed[1]/'terminal.json')
    result=dict(heroes=rows,valid_resume='HERO_ORDERED_RIDGES: request/source/artifact-verified skip',
        invalid_resume='HERO_BRANCHING_PLATES: intentionally reran the rejected recipe; same output and crossing-cap stop',
        repeated_failed_attempt_exact_geometry=True,
        distinction='Exact reproduction is a technical property, not evidence of successful ornament design.')
    write(STUDY/'hero_reproduction.json',result)
    return result


def totals():
    rows=[]; attempts=[]
    for phase in PHASES:
        selected=cases(phase)
        for c in (STUDY/phase).glob('*/attempt_*'):
            if (c/'summary.json').exists() and read(c/'summary.json').get('process'):
                attempts.append((phase,c,read(c/'summary.json')))
        rows.append(dict(phase=phase,selected_cases=len(selected),technically_valid=sum(read(c/'summary.json')['technically_valid'] for c in selected),
            attempts=sum(p==phase for p,_,_ in attempts)))
    primary=[c for p in ('A','B','C') for c in cases(p)]
    # Coordinate/cycle multisets disregard arbitrary mesh key allocation only.
    exact=[]
    for c in primary:
        data=read(c/'terminal.json')
        key=(frozenset(Counter(tuple(v['xyz']) for v in data['vertices']).items()),frozenset(oriented_polygons(data).items()))
        found=next((r for k,r in exact if k==key),None)
        if found is None: exact.append((key,[c.parent.name]))
        else: found.append(c.parent.name)
    result=dict(phases=rows,whole_gate_external_worker_attempts=len(attempts),
        selected_phase_cases=sum(r['selected_cases'] for r in rows),
        technically_valid_selected=sum(r['technically_valid'] for r in rows),
        technically_valid_attempts=sum(s['technically_valid'] for _,_,s in attempts),
        primary_cases=len(primary),primary_valid=sum(read(c/'summary.json')['technically_valid'] for c in primary),
        B_C_meaningful_compositions=64,finalists=14,refinements=22,exact_DS_handoff_replays=2,
        deliberate_Hero_recipes=2,independent_Hero_replays=2,valid_resume_skips=1,failed_resume_reruns=1,
        primary_exact_geometry_classes=len(exact),primary_identical_geometry_groups=[r for _,r in exact if len(r)>1],
        maximum_terminal_faces=max(s['terminal_statistics']['face_count'] for _,_,s in attempts),
        summed_worker_runtime_seconds=sum(s['runtime_seconds'] for _,_,s in attempts),
        largest_observed_process_tree_bytes=max(s['process']['peak_process_tree_plus_driver_bytes'] for _,_,s in attempts),
        counts_scope='One selected attempt per ID per phase; promotions and replays are explicitly included, not presented as new designs. Raw operator/fixture calls are excluded.',
        technically_valid_definition='All declared stages completed with finite valid/manifold/closed geometry and no 30-contact sample cap. CLEAN_SAMPLE is not a collision certificate.')
    write(STUDY/'delivery_totals.json',result)
    return result


def views():
    folder=STUDY/'views/FINAL'; folder.mkdir(parents=True,exist_ok=True)
    camera=read(ROOT/'studies/task19/camera.json')['bounds']; frames=[]; sheets=[]
    groups=dict(
        references=[('C0','references/C0.json'),('C07_FULL','references/C07.json'),('TASK20_HERO','references/HERO.json')],
        principal=[('TASK20_HERO','references/HERO.json'),
            ('HERO_ORDERED_RIDGES',str(next(p for p in cases('HERO') if p.parent.name=='HERO_ORDERED_RIDGES').relative_to(STUDY)/'terminal.json')),
            ('R_B5_03_4',str(next(p for p in cases('R') if p.parent.name=='R_B5_03_4').relative_to(STUDY)/'terminal.json'))],
        directional=[('TASK20_HERO','references/HERO.json'),
            ('R_B5_02_2',str(next(p for p in cases('R') if p.parent.name=='R_B5_02_2').relative_to(STUDY)/'terminal.json')),
            ('FAILED_HERO_BRANCHING_PLATES',str(next(p for p in cases('HERO') if p.parent.name=='HERO_BRANCHING_PLATES').relative_to(STUDY)/'terminal.json'))],
        gate_order=[('A03_FROZEN','references/A03.json'),('D02_FROZEN','references/D02.json'),
            ('F_B5_01',str(next(p for p in cases('F') if p.parent.name=='F_B5_01').relative_to(STUDY)/'terminal.json'))])
    for group,items in groups.items():
        for view in ('front','oblique','detail'):
            images=[]
            for name,path in items:
                output=f'views/FINAL/{group}_{name}_{view}.png'; images.append(output)
                data=read(STUDY/path)
                frames.append(dict(mesh=path,file=output,label=f'{name} / actual F={len(data["faces"])}',
                    camera='front' if view=='front' else 'oblique',bounds=camera[view],width=900,height=900))
            sheets.append(dict(file=f'views/FINAL/{group}_{view}_sheet.png',
                title=f'Task21 {group}; actual coordinates / same camera and scale / failures retained',
                images=images,columns=3,width=900,height=900))
    write(STUDY/'FINAL_projection_plan.json',dict(frames=frames,sheets=sheets))


if __name__=='__main__':
    reproduction(); result=totals(); views()
    print('Exact Hero reproduction verified; fixed delivery plans ready.')
    print(result['whole_gate_external_worker_attempts'],'real worker attempts;',result['technically_valid_attempts'],'technically valid')
