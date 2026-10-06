"""Two deliberate, bounded Hero compositions from visually reviewed cases."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from subdivision_capability_study import read,write
from ornament_study import digest
from vocabulary_review import STUDY,cases
from vocabulary_recipes import table,rule,roof
from cheshire.vocabulary import VocabularyRecipe

def prepare(ordered,branching):
    recipes=[]; sources=[]
    for source,id,strategy,new in [(ordered,'HERO_ORDERED_RIDGES','Large flank crests plus small crests nested in existing side frames',
            table('hero_micro',rule('ridge','INNER_CAP','Roof','descend__side_child',4,roof(.12,'vertical',.22)))),
        (branching,'HERO_BRANCHING_PLATES','Existing cap/side branches plus offset flank plates carrying restrained ridges',
            table('hero_crest',rule('plate','DIRECTIONAL_EXTRUSION_CAP','Roof','new__branch',2,roof(.10,'vertical',.26),z_min=.90)))]:
        case=next(p for phase in ('F','R') for p in cases(phase) if p.parent.name==source)
        summary=read(case/'summary.json'); assert summary['technically_valid'] and summary['recipe']['reference_id']=='HERO'
        data=deepcopy(summary['recipe']); data.update(id=id,family='HERO',mechanism=strategy+'; no terminal finish; existing macro frozen.')
        data['steps'].append(dict(kind='branch_table',**new.to_data()))
        data=VocabularyRecipe.from_data(data).to_data(); write(STUDY/'recipes'/(id+'.json'),data)
        recipes.append(id); sources.append(dict(hero=id,source_case=source,source_output_sha256=summary['output_sha256'],source_recipe_sha256=digest(summary['recipe']),
            appended_table=new.to_data(),strategy=strategy))
    write(STUDY/'hero_plan.json',dict(heroes=recipes,sources=sources,third_hero='Omitted: a third distinct strategy is not supported by the actual screen.',
        status='Proposed actual runs, not a design-success claim; milestone assessed after fixed views.'))
    print(*recipes)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--ordered',required=True); parser.add_argument('--branching',required=True)
    args=parser.parse_args(); prepare(args.ordered,args.branching)
