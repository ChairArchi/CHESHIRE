"""Freeze visually selected finalists and eighteen small local refinements.

Run after inspecting the actual primary views. Numeric macro parameters and
existing reference fragments are copied verbatim, never searched again.
"""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from subdivision_capability_study import read,write
from vocabulary_review import STUDY,gz_read,cases
from cheshire.vocabulary import VocabularyRecipe

def prepare(selected,strongest):
    assert 12<=len(selected)<=16 and len(strongest)==6 and set(strongest)<=set(selected)
    finalists=[]; refinements=[]
    z=[v['xyz'][2] for v in read(STUDY/'C0.json')['vertices']]; z0=min(z); source_height=max(z)-z0
    for name in selected:
        if name=='TASK20_HERO_CONTROL':
            finalists.append(name); continue
        data=deepcopy(read(STUDY/'recipes'/(name+'.json')))
        data.update(id='F_'+name,family='FINALIST',mechanism=data['mechanism']+' Visually selected primary; exact parameters retained.')
        data=VocabularyRecipe.from_data(data).to_data()
        write(STUDY/'recipes'/(data['id']+'.json'),data); finalists.append(data['id'])
    for name in strongest:
        original=read(STUDY/'recipes'/(name+'.json'))
        phase='A' if name.startswith('A_') else 'B' if name.startswith('B') else 'C'
        case=next(p for p in cases(phase) if p.parent.name==name)
        actual_events=gz_read(case/'terminal_lineage.json.gz')['events']
        # Three explicitly named, nearby refinements. Values are serialized
        # completely in the recipe rather than implied by a scaling factor.
        for index,mode in enumerate(('RESTRAIN_NEW','GABLE_OR_TANGENT','UPPER_OR_LEFT_ONLY'),1):
            data=deepcopy(original); changed=[]
            for step in data['steps']:
                if step['kind']!='branch_table': continue
                for r in step['rules']:
                    if r['action'] not in ('Roof','DirectionalExtrusion'): continue
                    p=r['parameters']
                    if mode=='RESTRAIN_NEW': p['height_ratio']=round(p['height_ratio']*.75,6)
                    elif mode=='GABLE_OR_TANGENT':
                        if r['action']=='Roof': p['gable_inset']=round(min(.4,p.get('gable_inset',.2)+.08),6)
                        else: p['normal_ratio']=round(min(.95,p.get('normal_ratio',.45)+.12),6)
                    else:
                        heights=sorted((e['local_frame']['center'][2]-z0)/source_height for e in actual_events if e['stage']==step['id']+'__'+r['id'])
                        if not heights: continue
                        if heights[-1]-heights[0]>1e-7:
                            r['when']['z_min']=max(r['when'].get('z_min',0),round(heights[(len(heights)-1)//2],6))
                        else: r['when']['side_class']='left'
                    changed.append(step['id']+'__'+r['id'])
            assert changed, 'Refine only recipes with a verified new operator.'
            data.update(id=f'R_{name}_{index}',family='REFINEMENT',mechanism=f'{name}: {mode}; changed routes {changed}; all other values including frozen backbone unchanged.')
            data=VocabularyRecipe.from_data(data).to_data()
            write(STUDY/'recipes'/(data['id']+'.json'),data); refinements.append(data['id'])
    write(STUDY/'finalist_plan.json',dict(finalists=finalists,strongest_six=strongest,refinements=refinements,
        method='Actual fixed views reviewed first; preserve all early values. Three local changes per strongest candidate; failures retained.',
        unsupported_strip_representative='Raw LinearSplit/Border probe evidence only; no invalid strip gate was promoted.'))
    print('finalists',*finalists); print('refinements',*refinements)

def end_refinements():
    """Four bounded tests of front-biased existing Roof-END branches.

    Hypothesis: the earlier sideways/upward end directions enter neighboring
    roof envelopes. A front tangent with a smaller normal component may make
    readable shelves without that contact growth. No new operator is added.
    """
    ids=[]
    for source in ('B2_01','B5_03'):
        original=read(STUDY/'recipes'/(source+'.json'))
        for index,ratio in ((4,.30),(5,.45)):
            data=deepcopy(original); changed=[]
            for s in data['steps']:
                if s['kind']!='branch_table': continue
                for r in s['rules']:
                    if r['action']!='DirectionalExtrusion' or r['when']['role']!='RIDGE_END': continue
                    r['parameters'].update(direction_mode='depth',normal_ratio=ratio,height_ratio=.18)
                    r['when'].update(normal_axis='y',normal_min=.2)
                    changed.append(s['id']+'__'+r['id'])
            assert changed
            data.update(id=f'R_{source}_{index}',family='REFINEMENT',mechanism=f'{source}: front-depth tangent on existing ridge ends; positive front orientation; normal_ratio={ratio}; other words and frozen C07 unchanged.')
            data=VocabularyRecipe.from_data(data).to_data(); write(STUDY/'recipes'/(data['id']+'.json'),data); ids.append(data['id'])
    plan=read(STUDY/'finalist_plan.json')
    plan['additional_end_refinements']=ids
    plan['refinement_count']=22
    plan['additional_hypothesis']='Front bias after observed side/upward END contact stops; two extra variations on each of the existing B2_01/B5_03 strongest-six sources, bringing them to five each.'
    write(STUDY/'finalist_plan.json',plan); print(*ids)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--selected',nargs='+'); p.add_argument('--strongest',nargs='+'); p.add_argument('--end-refinements',action='store_true')
    a=p.parse_args()
    if a.end_refinements: end_refinements()
    elif a.selected and a.strongest: prepare(a.selected,a.strongest)
    else: p.error('Select finalists and six sources, or --end-refinements.')
