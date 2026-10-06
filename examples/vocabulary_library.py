"""Serialize useful, construction-proven fragments with explicit input context."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from subdivision_capability_study import read,write
from ornament_study import digest
from vocabulary_review import STUDY,gz_read,cases
from vocabulary_recipes import references
from cheshire.vocabulary import VocabularyRecipe,validate_morphology_library

def main(ridge_case):
    refs=references(); entries=[]; prefix=read(STUDY/'backbone.json')
    contract='Existing positive C0 ancestry and complete constructive event paths; signed geometric stencils remain separate. Exact serialized source context, not a verified arbitrary transplant.'
    def add(id,source,stages,steps,input,geometry,intent,failures):
        entries.append(dict(id=id,source_recipe=source,source_stage_ids=stages,required_input=input,
            operator_sequence=deepcopy(steps),successful_geometry_sha256=digest(geometry),visual_intent=intent,
            known_failure_boundaries=failures,lineage_contract=contract))
    for id,count,intent in [('C11_MACRO_MASS',2,'Frozen larger support/lintel fold form'),('C07_GATE_BACKBONE',5,'Frozen first cap plus rim, before subsequent grammar')]:
        steps=[dict(kind='subdivision' if s['operator'] in ('CC','DS') else 'event',**s) for s in refs['C07']['stages'][:count]]
        add(id,refs['C07']['id'],[s['id'] for s in steps],steps,dict(exact_C0_sha256=digest(read(STUDY/'C0.json'))),
            gz_read(STUDY/'references'/f'BACKBONE_S{count:02d}.json.gz'),intent,['Already has read-only gate drift. Stage 5 has 12 known full-audit contacts; never a collision-free seed.'])
    for label,id,intent in [('A03','A03_ANGULAR_CAP','Angular nested cap/rim benchmark'),('D02','D02_ORDERED_FRAME','Existing DS/frame order benchmark')]:
        r=VocabularyRecipe.from_data(refs[label])
        add(id,r.id,[s.id for s in r.compile().stages[5:]],refs[label]['steps'],dict(exact_prefix_sha256=prefix['geometry_sha256']['5']),
            read(STUDY/'references'/(label+'.json')),intent,['Only proven in the exact saved context; DS can round terminal detail.'])
    hero=refs['HERO']
    for id,routes,intent in [('HERO_CAP_RING',{'cap','cap_child'},'Inset ring then smaller raised cap'),('HERO_SIDE_FIN',{'side','side_child'},'Side taper then inner frame')]:
        steps=[]; stages=[]
        for s in hero['steps']:
            if s['kind']!='branch_table': continue
            selected=[r for r in s['rules'] if r['id'] in routes]
            if selected:
                steps.append({**deepcopy(s),'rules':deepcopy(selected)}); stages.extend(s['id']+'__'+r['id'] for r in selected)
        add(id,hero['id'],stages,steps,dict(exact_prefix_sha256=prefix['geometry_sha256']['5'],source_context_recipe=hero['id']),
            read(STUDY/'references/HERO.json'),intent,['Supported as a fragment of the saved Hero, not independently transplanted. Broader side growth can reach the contact cap.'])
    case=next(p for phase in ('F','R','HERO') for p in cases(phase) if p.parent.name==ridge_case)
    summary=read(case/'summary.json'); assert summary['technically_valid']
    r=summary['recipe']; steps=r['steps'][len(refs[r['reference_id']]['steps']):] if r['reference_id']!='C07' else r['steps']
    assert all(s['kind']=='branch_table' for s in steps)
    add('NEW_FLANK_RIDGE',r['id'],[s['id']+'__'+q['id'] for s in steps for q in s['rules'] if q['action']!='quiet'],steps,
        dict(source_context_recipe=refs[r['reference_id']]['id'],role='EXTRUSION_SIDE',event_stage='event_1',eligible='Convex projected, bilinear-admissible quad; all actual selector gates remain in the fragment'),
        read(case/'terminal.json'),'Sharp crests on larger flank plates; partial local ridge organization, not a demonstrated gate-wide assembly',
        ['Preferred axis can select only two quad directions. Shared axes do not join ridges. Low contacts remain; do not widen indiscriminately.'])
    data=dict(version=1,entries=entries,excluded=dict(NEW_DIRECTIONAL_FIN='Stable directional cases mostly offset existing cells/plates; no convincing shared lateral-fin assembly.',
        NEW_STRIP_FIELD='Official split calls change outer boundary segmentation; variable-width call also failed exact repeat.',
        CAP_CENTERED_ROOF='Only repeats the panel scaffold; pure roof-on-cap is retained as study evidence, not a library entry.'),
        scope='Seven construction-proven, context-bound fragments; parameters are explicit. No generic operator library, GUI, or automatic composition search.')
    value=validate_morphology_library(data); write(STUDY/'morphology_library.json',data); write(STUDY/'morphology_library_validation.json',dict(sha256=value,entries=len(entries)))
    print('library',len(entries),value)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--ridge-case',required=True); args=p.parse_args(); main(args.ridge_case)
