"""Ten large, serialized design moves under the user's Task23 override."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from cross_cell_crease_study import read,write,digest
from cross_cell_crease_recipes import recipe
from cheshire.sharp_subdivision import WEIGHTS


def fold(hops,**values):
    return dict(band_hops=hops,weights={k:values.get(k,0.) for k in WEIGHTS},
        u_map={'(3,3)':2.,'(4,4)':-1.,'(5,5)':2.5,'(6,6)':-1.5},unknown_u=.5,
        units='wf/we/wp: absolute original model units; interpolation and Eq10/11: dimensionless',
        composition='Reference crease CC plus route-local existing sharp-weighted displacement relative to standard smooth CC')


def downstream(root,roof_height,cap_height,*,placement='ADJACENT',quiet=.74,depth=3,ridge_child=False):
    prior=read(root/'study/recipes/E05.json');steps=deepcopy(prior['composition'])
    steps[0]['parameters']['height_ratio']=roof_height
    steps[2]['parameters']['height_ratio']=cap_height
    steps[2]['parameters']['fraction']=.22
    for i,s in enumerate(steps):
        s.update(placement=placement,hops=3,spacing=1 if i<2 else 0,max_events=48 if i==0 else 20)
        s['selector'].pop('role',None);s['selector'].pop('event_stage',None)
        s['selector'].update(z_min=quiet,normal_y_min=.05)
        s['stratify_by']='C0_FACE'
    if ridge_child:steps[1].update(parent_stage=steps[0]['id'],parent_role='RIDGE_SIDE')
    if depth==2:steps=steps[:3]
    if depth>=4:
        q=deepcopy(steps[2]);q.update(id='crease_micro_second_cap',parent_stage=steps[3]['id'],parent_role='INNER_CAP')
        q['parameters']['height_ratio']=cap_height*.65;steps.append(q)
    for s in steps:s['explicit_parameter_deviation_from_saved_fragment']=dict(parameters=s['parameters'],
        reason='User override permits large serialized Roof/extrusion/nesting moves; original fragment reference remains recorded.')
    return steps


def declare(root):
    n3=dict(generator='N3',sharpness=12,seed_xz=[-.40,.96],target_y_ratio=-1.05,length_ratio=1.35,
        max_steps=120,turn_cost=2.,cell_reward=.4,max_turn=.7)
    n1=dict(generator='N1',relation='support_shoulder_lintel',sharpness=12)
    fans=[dict(generator='N5',side=side,sharpness=12,seed_xz=[sign*.44,.98],target_y_ratio=-1.05,
        minimum_seed_support=.05,minimum_target_support=0.) for side,sign in [('left',-1),('right',1)]]
    x=dict(generator='N6',junction='X',junction_xz=[0,.94],sharpness=12)
    roof_trace=dict(generator='N4',sharpness=12,length_ratio=1.3,max_steps=120,turn_cost=2.)
    zero=fold(3)
    plans=[
        ('X01','C07',[n3],[fold(4,wf=250,we=100,wp=200,w1=-1.8,w2=-4,w6=1.25,w7=-.7),
            fold(3,wf=80,wp=50,w1=.8,w2=-.8,w6=-.35,w7=.4),zero],None,
            'Aggressive long terrain fold; large first displacement, contrasting second placement, persistent third crease generation.'),
        ('X02','C07',[n1],[fold(6,wf=450,we=-120,wp=350,w1=-2.2,w2=-5,w6=-1.2,w7=1.5),
            fold(4,wf=-150,wp=-120,w1=1.4,w2=2,w6=.6,w7=-.9)],None,
            'Wide shoulder-to-lintel deformation followed by reverse-signed placement; gate drift allowed.'),
        ('X03','C07',fans,[fold(5,wf=180,wp=240,w1=-2.8,w2=-6,w6=2,w7=1.2),zero],(.8,.9,'JUNCTION',.74,4,False),
            'Two crest fans, large fold generation, preserved junctions, Roof and four nested micro events.'),
        ('X04','C07',[x],[fold(7,wf=100,we=-250,w1=2.2,w2=-3,w6=-.6,w7=-1.6),
            fold(5,wf=-100,we=200,wp=120,w1=-1,w2=1.5,w6=.2,w7=1.5)],None,
            'Crossing network with alternating edge/face emphasis; overlap is a retained capability state.'),
        ('X05','TASK22_BOUNDARY',[n3],[fold(5,wf=400,we=-200,wp=300,w1=-2,w2=-6,w6=2,w7=-2),zero],None,
            'Continue an actual 75-contact Task22 input through aggressive fold and subsequent crease subdivision.'),
        ('X06','ORDERED',[roof_trace],[fold(5,wf=200,we=150,wp=120,w1=-1.2,w2=-3.2,w6=.8,w7=.9)],(.75,.8,'ADJACENT',.74,4,True),
            'Actual recorded Roof ridge transfer, large ordered folding and strict ridge-child nesting.'),
        ('X07','C07',[dict(n,sharpness=16,seed_xz=[(-1 if n['side']=='left' else 1)*.36,.87],target_y_ratio=-.65) for n in fans],
            [fold(6,wf=600,we=180,wp=500,w1=-3,w2=-7,w6=-1.5,w7=-1.5),
             fold(4,wf=-180,we=-80,wp=-160,w1=.5,w2=1,w6=.5,w7=.4)],(1.2,1.2,'ADJACENT',.70,4,False),
            'Extreme broad fan folding, partial signed return, large Roof and deep extrusion relationships.'),
        ('X08','C07',[dict(generator='N1',relation='outer_lintel',sharpness=12),dict(generator='N6',junction='T',sharpness=12)],
            [fold(8,wf=200,we=200,wp=-250,w1=.5,w2=-5,w6=-.8,w7=2),zero],(.65,.8,'ADJACENT',.84,3,False),
            'Long perimeter and central junction act together; broad fold with restricted upper ornament.'),
        ('X09','C07',[dict(n,sharpness=10.5,profile='JUNCTION_SOFT_ENDS') for n in fans],
            [fold(5,wf=150,we=30,wp=100,w1=-1.4,w2=-2.8,w6=.35,w7=.4),
             fold(3,wf=40,wp=30,w1=-.4,w2=-.8,w6=.1,w7=.1)],(.55,.6,'JUNCTION',.78,3,False),
            'Gate-readable direction: localized contrasting shoulder fold, attenuated second placement and sparse nested nodes.'),
        ('X10','C07',[dict(n3,seed_xz=[-.38,.94],direction=[1.,0.,.25]),dict(n3,seed_xz=[.38,.94],direction=[-1.,0.,.25])],
            [fold(6,wf=-260,wp=400,w1=1.5,w2=-4,w6=-1.6,w7=1.2),
             fold(4,wf=180,we=100,wp=-200,w1=-1,w6=.8,w7=-.8)],(.9,1.1,'ADJACENT',.70,4,False),
            'Opposed directional traces and signed nonstationary placement followed by deep selective articulation.')]
    result=[]
    for name,source,nets,schedule,events,intent in plans:
        r=recipe(name,'DESIGN_FIRST_CAPABILITY',source,nets,len(schedule))
        r.update(fold_schedule=deepcopy(schedule),hypothesis=intent,policy_override=True,
            contact_policy='Diagnostic cap256; contact count does not stop compatible finite evolution.',
            priority_order=['visible morphology','cross-cell organization','hierarchy','replay','gate readability','contact cleanliness'],
            operator_order='Frozen backbone -> declared network -> listed route-local folded crease generations -> listed existing Mola stages -> STOP')
        if events:
            rh,ch,placement,z,depth,ridge=events
            r['composition']=downstream(root,rh,ch,placement=placement,quiet=z,depth=depth,ridge_child=ridge)
        target=root/'study/recipes'/(name+'.json')
        if target.exists() and read(target)!=r:raise ValueError('Do not overwrite a declared capability candidate: '+name)
        write(target,r);result.append(r)
    write(root/'study/design_first_declarations.json',dict(recipes=[r['id'] for r in result],total=len(result),
        original_fragment=dict(path='study/recipes/E05.json',sha256=digest(read(root/'study/recipes/E05.json'))),
        policy='User override; ten structural/schedule/composition moves, no mechanism ablation grid.'))
    print('Declared',len(result),'design-first candidates')
    return result


def coherent_refinements(root):
    """After X02's actual shard field, match normal offsets across point classes.

    The original intersecting result is retained. This changes design logic,
    rather than repairing it or merely increasing the same cap height.
    """
    original=read(root/'study/recipes/X02.json')
    fans=read(root/'study/recipes/X03.json')['networks']
    plans=[('R19',original['networks'],10,320,.8,1.0,3),('R20',fans,9,500,1.0,1.4,4)]
    result=[]
    for name,nets,band,offset,rh,ch,depth in plans:
        r=recipe(name,'DESIGN_FIRST_REFINEMENT','C07',nets,2)
        first=fold(band,wf=offset,we=offset,wp=offset)
        second=fold(5,w1=-.35,w2=-.65) if name=='R19' else fold(4)
        r.update(fold_schedule=[first,second],policy_override=True,refinement_of='X02',
            original_recipe_sha256=digest(original),
            hypothesis='Replace competing point-class offsets and strong interpolation with a broad coherent route-local normal fold; preserve sharp paths and apply sparse terminal nesting.',
            contact_policy='Diagnostic cap256; continue compatible finite evolution.',
            composition=downstream(root,rh,ch,placement='ADJACENT' if name=='R19' else 'JUNCTION',quiet=.78,depth=depth))
        target=root/'study/recipes'/(name+'.json')
        if target.exists() and read(target)!=r:raise ValueError('Do not overwrite coherent refinement: '+name)
        write(target,r);result.append(r)
    write(root/'study/coherent_refinement_declarations.json',dict(recipes=[r['id'] for r in result],
        observation='Actual X02 whole view: large shard field suppresses panels but lacks a coherent meso fold; match all normal point classes before adding ornament.'))
    print('Declared two coherent-field refinements of observed X02')
    return result


def continue_large_taper(root):
    """Resume actual E2 checkpoints, rather than repeating completed folds."""
    from cross_cell_crease_compositions import substrate
    result=[]
    for origin,name in [('X03','Y03'),('X06','Y06'),('X07','Y07'),('R19','Y19')]:
        paths=sorted((root/'study/CAPABILITY'/origin).glob('attempt_*/summary.json'))
        if not paths:continue
        summary=read(paths[-1])
        if summary['status']!='TECHNICAL_STOP' or summary['reason']!='Conservative taper range required.':continue
        previous=summary['recipe'];stage=summary['stages'][-1]['stage']
        if not stage.startswith('E'):raise ValueError('Only actual completed event-prefix continuation expected.')
        used=int(stage[1:]);p=substrate(root,origin,stage,phase='CAPABILITY')
        r=recipe(name,'LARGE_TAPER_CONTINUATION',previous['input'],[],0)
        r.update(mode=previous['mode'],prepared_substrate=p,composition=deepcopy(previous['composition'][used:]),
            policy_override=True,composition_stage_base=previous.get('composition_stage_base',previous['generations']+12)+used,
            continuation_of=origin,hypothesis='Resume the exact real fold/Roof/frame checkpoint with Task23 explicit finite large-taper permission; no repeated prefix computation.',
            contact_policy='Contacts diagnostic only; existing next-operator geometry checks retained.')
        target=root/'study/recipes'/(name+'.json')
        if target.exists() and read(target)!=r:raise ValueError('Do not overwrite declared continuation: '+name)
        write(target,r);result.append(r)
    write(root/'study/large_taper_continuations.json',[dict(id=r['id'],origin=r['continuation_of'],prefix=r['prepared_substrate']['artifact'],stage=r['prepared_substrate']['stage']) for r in result])
    print('Declared actual-checkpoint continuations:',[r['id'] for r in result])
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--coherent-refinements',action='store_true');p.add_argument('--continue-large-taper',action='store_true');a=p.parse_args()
    if a.continue_large_taper:continue_large_taper(a.output_root)
    elif a.coherent_refinements:coherent_refinements(a.output_root)
    else:declare(a.output_root)
