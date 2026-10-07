"""Eighteen explicit refinements of six observed directions; no new operator."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from cross_cell_crease_study import read,write,digest
from cross_cell_crease_recipes import recipe


def get(root,name):
    return read(root/'study/recipes'/(name+'.json'))


def record(root,name,origin,r,reason):
    old=get(root,origin)
    r=deepcopy(r);r.update(id=name,family='REFINEMENT',refinement_of=origin,
        original_recipe_sha256=digest(old),hypothesis=reason)
    r['explicit_changes']={k:v for k,v in r.items() if k not in ('id','family','hypothesis','explicit_changes') and old.get(k)!=v}
    destination=root/'study/recipes'/(name+'.json')
    if destination.exists() and read(destination)!=r:
        raise ValueError('Do not overwrite a declared refinement: '+name)
    write(destination,r);return r


def declare(root,only=None):
    results=[]
    def add(i,origin,r,reason):
        name=f'R{i:02d}'
        if only is None or name in only:results.append(record(root,name,origin,r,reason))
    a=get(root,'A08')
    r=deepcopy(a);r['networks'][0]['sharpness']=6
    add(1,'A08',r,'Longer sharp lifetime, same terrain route and two CC generations.')
    r=deepcopy(a);r['networks'][0].update(seed_xz=[-.40,.96],target_y_ratio=-1.05,length_ratio=1.25,max_turn=.55,turn_cost=2.0,cell_reward=.35)
    n=deepcopy(r['networks'][0]);n.update(seed_xz=[.40,.96],direction=[-1.,0.,0.]);r['networks'].append(n)
    add(2,'A08',r,'Two architectural crest seeds and stronger directional continuity, no hand-picked edges.')
    r=deepcopy(a);r['networks'][0].update(seed_xz=[-.42,.98],target_y_ratio=-1.05,length_ratio=1.35,turn_cost=2.0,cell_reward=.5,max_steps=120)
    add(3,'A08',r,'Front crest cue and longer cross-cell walk instead of deeper valley cue.')
    a=get(root,'A10')
    crest=deepcopy(a);crest['generations']=1
    for n in crest['networks']:
        sign=-1 if n['side']=='left' else 1
        n.update(seed_xz=[sign*.44,.98],target_y_ratio=-1.05,minimum_seed_support=.05,minimum_target_support=0.,sharpness=6)
    add(4,'A10',crest,'Sparse crest-seeded shoulder fans, one generation and persistent integer state.')
    r=deepcopy(crest);r['generations']=2;r['mode']='UNIFORM_FRACTIONAL'
    for n in r['networks']:n.update(sharpness=4.5,profile='JUNCTION_SOFT_ENDS')
    add(5,'A10',r,'Same crest seeds, softer ends and two generations; not a different geometric stencil.')
    r=deepcopy(a);r['generations']=3
    for n in r['networks']:n['sharpness']=6
    add(6,'A10',r,'Original fan with six-step persistence observed for three refinements, ordinary 300k ceiling retained.')
    a=get(root,'B12')
    r=deepcopy(a);r['networks'][0].update(sharpness=6,length_ratio=1.3,turn_cost=2.,max_steps=120)
    add(7,'B12',r,'Extend an actual recorded Roof ridge through neighboring cells; one CC generation.')
    r=deepcopy(a);r['mode']='UNIFORM_FRACTIONAL';r['networks'][0].update(sharpness=4.5,profile='CENTER_SOFT_TAILS',length_ratio=1.3)
    add(8,'B12',r,'Matched long Roof-transfer trace with soft tails, finite Uniform decay.')
    r=deepcopy(a);r['networks'][0].update(sharpness=4,seed_xz=[.32,.91],length_ratio=1.1,max_turn=.55,cell_reward=.4)
    add(9,'B12',r,'Transfer a right architectural ridge seed with fewer turns, not a new Roof operator.')
    # These use reviewed original A/B prefixes. Exact old fragment parameters
    # remain in parameter_reference; every changed parameter is serialized above.
    a=get(root,'E05')
    r=deepcopy(a);r['composition'][0]['parameters']['height_ratio']=.36
    r['composition'][2]['parameters']['height_ratio']=.39
    add(10,'E05',r,'Two-fold Roof height and 1.5-fold nested cap height in the same sparse fan-junction bands.')
    r=deepcopy(a);r['composition'][0]['parameters']['height_ratio']=.28
    for s in r['composition']:s['selector']['z_min']=.80
    add(11,'E05',r,'Narrow the active upper zone; quiet lower shoulder faces stay untouched.')
    r=deepcopy(crest);r['composition']=deepcopy(a['composition']);r['composition_stage_base']=12
    add(12,'E05',r,'Rebuild crest fans then apply the identical full synthesis; clean substrate checked before each local stage.')
    a=get(root,'E04')
    r=deepcopy(a);r['composition'][0]['parameters']['height_ratio']=.09;r['composition'][2]['parameters']['height_ratio']=.13
    add(13,'E04',r,'Half-height downstream events to test the two observed sampled crossings without repair.')
    r=deepcopy(a);r['composition'][0]['parameters']['height_ratio']=.36;r['composition'][2]['parameters']['height_ratio']=.39
    for s in r['composition']:s['selector']['z_min']=.82
    add(14,'E04',r,'Larger selective ridge-child micro events confined to a quieter upper zone.')
    r=get(root,'R03') if (root/'study/recipes/R03.json').exists() else deepcopy(get(root,'A08'))
    r=deepcopy(r);r['generations']=1;r['composition']=deepcopy(a['composition']);r['composition_stage_base']=12
    add(15,'E04',r,'Longer crest-oriented terrain trace followed by the original ridge-child ornament.')
    if only is None or set(only)&{'R16','R17','R18'}:
        a=get(root,'E16')
        r=deepcopy(a);r['composition'][0]['parameters']['height_ratio']=.36
        add(16,'E16',r,'Existing ordered ridge grammar with larger selective Roof reinforcement, no smooth finish.')
        r=deepcopy(a)
        for s in r['composition']:s['selector']['z_min']=.84
        r['composition'][1]['parameters']['width_ratio']=.10;r['composition'][2]['parameters']['height_ratio']=.39
        add(17,'E16',r,'Ordered transfer with a quieter upper activity zone and explicitly rescaled nested node.')
        r=get(root,'R07') if (root/'study/recipes/R07.json').exists() else deepcopy(get(root,'B12'))
        r=deepcopy(r);r['composition']=deepcopy(a['composition']);r['composition_stage_base']=12
        add(18,'E16',r,'Longer actual Roof-transfer crease prefix with the identical downstream ordered synthesis.')
    write(root/'study/refinement_declarations.json',dict(limit=24,declared_total=18,
        origins=['A08','A10','B12','E05','E04','E16'],recipes=[r['id'] for r in results],
        policy='Observed route contrast / sparse nodes / ordered ridge directions; weak originals retained. No carrier or operator search.'))
    print('Declared',len(results),'explicit refinements')
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--names',nargs='+')
    a=p.parse_args();declare(a.output_root,a.names)
