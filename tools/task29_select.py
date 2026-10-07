"""Recorded visual decisions, not autonomous metric-based success claims."""
import argparse,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
from task29_search import ROOT,row,mix,scaled
from cross_cell_crease_study import read,write
from task29_views import sheet


def select_b():
    selected=[0,4,8,12,16,20,24,28,1,13,96,100,128,140,144,156,
              192,196,200,204,208,212,216,220,224,225,228,232,236,240,244,248]
    s=read(ROOT/'definitions/recovered_numeric_seeds.json');late=[
        [s['CURVE'],s['T28_G3']],
        [s['T28_G3'],s['C11B']],
        [mix(s['C26'],s['GENTLE'],.5,'C26/GENTLE .5'),mix(s['C11B'],s['C26'],.35,'C11B/C26 .35')],
        [row({**s['C11B']['weights'],'wf':-.16,'we':.05,'wp':-.045},source='Offset sign reversal'),
         row(dict(wf=.04,we=-.02,wp=.01,w1=-.3,w2=-.65,w3=-1.25,w4=.65),source='Bounded continued Eq4 fold')]]
    definitions=[]
    for n in selected:
        d=read(ROOT/'definitions/round_A'/f'A{n:03}.json')
        for i,rows in enumerate(late):definitions.append(dict(**{k:v for k,v in d.items() if k not in ('id','rows')},id=f'B{n:03}_{i}',parent=str(ROOT/f'candidates/round_A/A{n:03}/G3'),rows=d['rows']+rows))
    write(ROOT/'definitions/round_B_selection.json',dict(definitions=definitions,selected_A=selected,late_families=late,
        visual_review='All sixteen A contact pages (256 G3) inspected. C11A/B/H1B macro starts mostly inflated capsules; AMP nested row frequently causes thin spikes. Prefer H1-ablation lobes with internal G3 ridges; keep four full-H1 petal cases, two C26, and mixed-prefix cases as distinct mechanisms.',
        counts=dict(A_selected=32,late_per_A=4,B=128),early_success=False))
    manifest=read(ROOT/'renders/round_A/manifest.json')['records'];records=[manifest[n] for n in selected]
    sheet(records,ROOT/'renders/broad_search_contact_sheet.png',4,540)
    write(ROOT/'analysis/round_A_visual_review.json',dict(pages_inspected=list(range(16)),selected=selected,
        lead_scale='A previews are explicitly individually framed for shape inspection; physical extent is recorded. Matrix and final progression use fixed physical scale.',
        judgment='Macro/meso potential, no convincing non-repeating small hierarchy yet. Continue B/C.'))


def select_c(names):
    s=read(ROOT/'definitions/recovered_numeric_seeds.json');defs=[]
    for i,name in enumerate(names):
        b=read(ROOT/'definitions/round_B'/f'{name}.json')
        # Continue the genuinely modified late regime; alternate with exact recovered
        # G3 / CURVE / attraction mix instead of approaching zero.
        tail=[b['rows'][-1],s['T28_G3'],b['rows'][-1]] if name.endswith('_0') else [s['T28_G3'],b['rows'][-1],s['CURVE']]
        if name.endswith('_2'):tail=[b['rows'][-2],b['rows'][-1],b['rows'][-2]]
        defs.append(dict(id=f'C{i:02}_{name}',rows=b['rows']+tail,mode=b['mode'],scale=b['scale'],parent=str(ROOT/f'candidates/round_B/{name}/G5')))
    write(ROOT/'definitions/round_C_selection.json',dict(definitions=defs,visual_selection=names,requested=8,actual=len(defs),reason='Actual G5 comparison reviewed; selected existing macro lobes/internal folds, rather than spikes or inflated capsules. All G6–8 controls remain nonzero, no relaxation trend.'))


def intrinsic(names):
    s=read(ROOT/'definitions/recovered_numeric_seeds.json');defs=[]
    rules=[]
    for field in ['NORMAL_VARIATION','ORIGINAL_EDGE_DISTANCE','PLANARITY','LOCAL_SCALE']:
        for strength in [.6,1.2]:
            rules.append(dict(field=field,start=3,gain=3 if field=='NORMAL_VARIATION' else 12,
                controls={'wf':[-.06*strength,.12*strength],'we':[.035*strength,-.04*strength],
                          'w3':[-.55*strength,.35*strength],'w4':[.18*strength,-.22*strength]}))
    for j,name in enumerate(names):
        c=read(ROOT/'definitions/round_C'/f'{name}.json')
        # Reuse actual unchanged G2 of this schedule, then apply intrinsic at G3.
        parent=Path(read(ROOT/'candidates/round_A'/name.split('_')[1].replace('B','A')/'G3/summary.json')['parent'])
        for i,r in enumerate(rules):defs.append(dict(id=f'D{j:02}_{i}',rows=c['rows'][:5],mode=c['mode'],scale=c['scale'],parent=str(parent),intrinsic=r,base_C=name))
    write(ROOT/'definitions/intrinsic_rules.json',dict(rules=rules,base_schedules=names,variants=len(defs),meaning='Current scalar field linearly adds bounded offsets to declared controls. Other controls remain identical. Field re-evaluated from actual geometry every generation; no IDs/no randomness.',equivalent_cell_goal='Original edge distances or nonlinear geometric feedback differentiate neighbouring descendants.'))
    write(ROOT/'definitions/intrinsic_selection.json',dict(definitions=defs))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--b',action='store_true');p.add_argument('--c',nargs='+');p.add_argument('--intrinsic',nargs='+');a=p.parse_args()
    if a.b:select_b()
    if a.c:select_c(a.c)
    if a.intrinsic:intrinsic(a.intrinsic)
