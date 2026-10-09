"""Explicit hypothesis batches; further batches depend on reviewed actual geometry."""
import argparse
from copy import deepcopy
from pathlib import Path
from task32_research import ROOT, write_new, read,sha


def cc():
    return dict(kind='cc', row={})


def pilot():
    definitions = [dict(id='P01_NEUTRAL', hypothesis='Matched unchanged CC carrier control',
                        steps=[cc() for _ in range(4)])]
    for index, (growth, anisotropy, field) in enumerate([
            (.25, 0, 'bands'), (.55, 0, 'bands'), (.9, 0, 'bands'),
            (.55, .85, 'bands'), (.55, .85, 'nested'), (.9, .85, 'nested')], 2):
        spec = dict(growth=growth, anisotropy=anisotropy, field=field, lobes=5,
                    angular=3, twist=1.5, bending=.02, anchor=.002, seed=.001, maxiter=2000)
        definitions.append(dict(id=f'P{index:02}_GROWTH',
            hypothesis='Spatial rest-length incompatibility may create meso buckling; isotropic/anisotropic ablation',
            steps=[cc(), cc(), dict(kind='growth', spec=spec), cc(), cc()]))
    for index, (amplitude, coupling, twist) in enumerate([
            (140, 1, 1.5), (280, 1, 1.5), (280, 0, 1.5), (280, 1, 0)], 8):
        spec = dict(amplitude=amplitude, coupling=coupling, twist=twist, angular=3,
                    lobes=5, decay=.42, envelope_power=1.5, phase=0)
        steps = [cc(), cc(), dict(kind='hierarchy', spec=spec, level=0), cc(),
                 dict(kind='hierarchy', spec=spec, level=1), cc(),
                 dict(kind='hierarchy', spec=spec, level=2)]
        definitions.append(dict(id=f'P{index:02}_HIERARCHY',
            hypothesis='Parent-gated directional child fields may create connected scales without per-cell point-class forcing',
            steps=steps))
    folder = ROOT/'definitions/pilot'
    for d in definitions:
        write_new(folder/(d['id']+'.json'), d)
    write_new(folder/'batch.json', dict(ids=[d['id'] for d in definitions],
        allocation='Small G2 deformations first; G4 views before deeper allocation.',
        not_final_search_limit=True))
    return folder


def request(folder, tag, extra=None):
    paths = sorted(p for p in Path(folder).glob('*.json') if p.name!='batch.json')
    items = []
    for p in paths:
        d = read(p)
        dest = ROOT/'candidates'/d['id']
        if not (dest/'completed.json').exists():
            continue
        stage = read(dest/'completed.json')['final_stage']
        for label, angles, width, target in [
                ('front', [0, 0], 5400, [-400.036865234375, -18.533447265625, 1750]),
                ('oblique', [28, 22], 5400, [-400.036865234375, -18.533447265625, 1750]),
                ('lintel', [0, 0], 2200, [-400.036865234375, -18.533447265625, 2950])]:
            items.append(dict(label=d['id']+' '+label, stage=stage, angles=angles, width=width, target=target))
    if extra:
        items.extend(extra)
    path = ROOT/'definitions/renders'/(tag+'.json')
    write_new(path, dict(items=items, resolution=900, cols=3, size=550, pages=99,
                         sheet_name=tag+'.png'))
    return path


def patches():
    root=dict(locations=[.14,.3,.44,.56,.7,.86],radius_arc=400,radius_angle=1.1,
              heights=[.25,.7,1.25],scales=[.6,1.05,.75],bend=.45,twist=0,direction=[0,0,1])
    child=dict(heights=[.25,.7,1.2],scales=[.65,1,.5],bend=.5,twist=0,
               child_radius=.27,child_offset=.30)
    base=[cc(),cc(),dict(kind='patches',spec=root),cc(),
          dict(kind='patches',spec=child,children=True),cc(),cc()]
    definitions=[]
    for name,steps,reason in [
        ('R01_ROOT_ONLY',base[:4]+[cc(),cc()], 'Ablate child events; same root grammar and CC5'),
        ('R02_NESTED',base,'Connected multi-face roots, then two inherited cap children'),
        ('R03_NO_NECK',deepcopy(base),'Ablate neck constriction with same cumulative heights'),
        ('R04_TWIST',deepcopy(base),'Change patch orientation through actual ring rotation'),
        ('R05_LONG_THIN',deepcopy(base),'Test legibility and collision risk of longer narrow branches'),
        ('R06_WIDE_CHILD',deepcopy(base),'Increase child scope size; expose overlap rejection'),
        ('R07_THIRD_LEVEL',base[:-1]+[dict(kind='patches',spec=child,children=True),cc()],
            'Third grammar level; test extra hierarchy before late smoothing'),
        ('R08_GROWTH_PATCH',base[:2]+[dict(kind='growth',spec=dict(growth=.55,field='bands',anisotropy=0,
            lobes=5,bending=.02,anchor=.002))]+base[2:], 'Combine observed growth meso and constructive patch hierarchy')]:
        d=dict(id=name,hypothesis=reason,steps=deepcopy(steps));definitions.append(d)
    for step in definitions[2]['steps']:
        if step['kind']=='patches':step['spec']['scales']=[1,1,1]
    for step in definitions[3]['steps']:
        if step['kind']=='patches':step['spec']['twist']=.8
    for step in definitions[4]['steps']:
        if step['kind']=='patches':step['spec'].update(heights=[.4,1.3,2.2],scales=[.45,.65,.25])
    definitions[5]['steps'][4]['spec']['child_radius']=.34
    folder=ROOT/'definitions/patches'
    for d in definitions:write_new(folder/(d['id']+'.json'),d)
    write_new(folder/'batch.json',dict(ids=[d['id'] for d in definitions],
        reason='Pilot metric growth yielded broad necks/bulbs, field hierarchy yielded repeated rough bands. Test a different constructive relationship.',
        changed_from_Task23='Simple Task26 carrier; connected multi-face disks, curved neck rings, inherited multi-face child caps; no crease/Mola/per-cell terminal events.',
        not_final_search_limit=True))
    return folder


def intrinsic():
    definitions=[]
    for k,(growth,volume,bending,anisotropy) in enumerate([
            (.55,2,.02,0),(.55,20,.02,0),(.9,20,.02,0),
            (.9,20,.002,0),(.9,20,.02,.85),(.9,20,.002,.85)],1):
        spec=dict(growth=growth,volume_strength=volume,bending=bending,anisotropy=anisotropy,
                  field='nested',lobes=5,anchor=.002,seed=.001,maxiter=4000)
        definitions.append(dict(id=f'V{k:02}_VOLUME',
            hypothesis='Global signed volume penalty may convert free inflation into constrained buckling; algebraic volume not certified solid volume',
            steps=[cc(),cc(),dict(kind='growth',spec=spec),cc(),cc()]))
    for k,(modes,amplitude,coupling,remeasure) in enumerate([
            ([2,7],240,1,False),([5,14],320,1,False),([8,18],320,1,False),
            ([5,14],320,0,False),([5,14],320,1,True),([5,14],500,1,False),
            ([5,14],180,1,False)],1):
        spec=dict(modes=modes,amplitude=amplitude,coupling=coupling,secondary_mix=.4,level=0)
        child=dict(spec,level=1,amplitude=amplitude*.32,frequency=4,remeasure=remeasure)
        micro=dict(spec,level=2,amplitude=amplitude*.10,frequency=4)
        steps=[cc(),cc(),dict(kind='spectral',spec=spec),cc(),dict(kind='spectral',spec=child),
               cc(),dict(kind='spectral',spec=micro)]
        definitions.append(dict(id=f'S{k:02}_SPECTRAL',
            hypothesis='Intrinsic eigenfield organization avoids closest-carrier chart seams; shared parent phase couples scales',steps=steps))
    folder=ROOT/'definitions/intrinsic'
    for d in definitions:write_new(folder/(d['id']+'.json'),d)
    write_new(folder/'batch.json',dict(ids=[d['id'] for d in definitions],
        reason='Patch attachment remains local and child depth does not improve whole view. Test intrinsic geometry organization and constrain free inflation.',
        not_final_search_limit=True))
    return folder


def corrective():
    definitions=[]
    choices=[([5,14],320,.35,3,1),([5,14],320,0,3,1),([5,14],320,.35,2,1),
             ([2,19],300,.35,3,1),([6,20],300,.35,3,1),([8,18],240,.35,3,1),
             ([5,14],320,.35,3,0),([5,14],180,.20,3,1)]
    for k,(modes,amplitude,limit,birth,coupling) in enumerate(choices,1):
        spec=dict(modes=modes,amplitude=amplitude,coupling=coupling,secondary_mix=.4,level=0,curvature_limit=limit)
        child=dict(spec,level=1,amplitude=amplitude*.3,frequency=4)
        micro=dict(spec,level=2,amplitude=amplitude*.10,frequency=4)
        steps=[cc() for _ in range(birth)]+[dict(kind='spectral',spec=spec),cc(),
            dict(kind='spectral',spec=child),cc(),dict(kind='spectral',spec=micro)]
        definitions.append(dict(id=f'C{k:02}_LIMITED',
            hypothesis='Observed transverse crossings require local curvature-aware amplitude and adequate birth sampling; matched uncapped/coupling ablations',steps=steps))
    source=Path('E:/CHESHIRE_DATA/task31/lead/gate/G2')
    for k,modes in enumerate(([2,19],[8,18]),9):
        spec=dict(modes=modes,amplitude=200,coupling=1,secondary_mix=.4,level=0,curvature_limit=.2)
        definitions.append(dict(id=f'C{k:02}_TASK31_PREFIX',
            hypothesis='Retain actual Task31 simple-gate early macro prefix, replace late cell forcing with intrinsic hierarchy; not replay of full Task31 schedule',
            source_checkpoint=dict(path=str(source),mesh_sha256=sha(source/'mesh.npz'),
                producer_baseline='663be3b4e030322b38af743d0d40631e8cafc1d6',
                note='Actual G0->G2 unchanged simple gate prefix, original state preserved at source'),
            steps=[cc(),dict(kind='spectral',spec=spec),cc(),dict(kind='spectral',spec=dict(spec,level=1,amplitude=55)),
                   cc(),dict(kind='spectral',spec=dict(spec,level=2,amplitude=18))]))
    folder=ROOT/'definitions/corrective'
    for d in definitions:write_new(folder/(d['id']+'.json'),d)
    write_new(folder/'batch.json',dict(ids=[d['id'] for d in definitions],
        reason='Every S-series field result had transverse contacts and opposed quad fans. Test an explicit geometric risk correction; no repair of those retained outputs.',
        not_final_search_limit=True))
    return folder


def transmission():
    definitions=[]
    choices=[('D01_SMOOTH','C01_LIMITED','material',80,None,None),
        ('D02_CC_FIELD','C01_LIMITED','coupled_cc',0,None,None),
        ('D03_BOTH','C01_LIMITED','coupled_cc',80,None,None),
        ('D04_LONG_SMOOTH','C01_LIMITED','coupled_cc',150,None,None),
        ('D05_OTHER_MODES','C06_LIMITED','coupled_cc',80,None,None),
        ('D06_MACRO_ONLY','C01_LIMITED','coupled_cc',80,None,0),
        ('D07_MACRO_MESO','C01_LIMITED','coupled_cc',80,None,1),
        ('D08_TIGHT_BOUND','C01_LIMITED','coupled_cc',80,.15,None),
        ('D09_UNCAPPED_CC','C02_LIMITED','coupled_cc',0,None,None),
        ('D10_TASK31_PREFIX','C09_TASK31_PREFIX','coupled_cc',80,None,None)]
    for name,parent,transport,length,fraction,last_level in choices:
        d=deepcopy(read(ROOT/'definitions/corrective'/(parent+'.json')))
        d.update(id=name,coordinate_transport=transport,
            hypothesis='C-series showed many opposed quad fans even after local caps. Separate bound-field discontinuity, material-vs-geometry stencil, and contributions of each scale.',
            comparison_parent=parent)
        for step in d['steps']:
            if step['kind']=='spectral':
                step['spec']['limit_smoothing_length']=length
                if fraction is not None:step['spec']['curvature_limit']=fraction
                if last_level is not None and step['spec']['level']>last_level:step['spec']['amplitude']=0
        definitions.append(d)
    folder=ROOT/'definitions/transmission'
    for d in definitions:write_new(folder/(d['id']+'.json'),d)
    write_new(folder/'batch.json',dict(ids=[d['id'] for d in definitions],
        reason='Corrective C01 had 1,315 opposed quad fans despite only two sampled contacts. Investigate field transmission instead of increasing detail depth.',
        not_final_search_limit=True))
    return folder


def combination():
    root=dict(locations=[.14,.3,.44,.56,.7,.86],radius_arc=400,radius_angle=1.1,
        heights=[.25,.65,1.1],scales=[.72,.6,.42],bend=.45,direction=[1,0,1])
    child=dict(root,heights=[.4,1.3,2.2],scales=[.45,.65,.25],child_radius=.24,child_offset=.27)
    definitions=[]
    for k,(parent,modes,bound,twist) in enumerate([
        (None,None,None,0),('D06_MACRO_ONLY',None,None,0),('D06_MACRO_ONLY',None,None,.8),
        ('D08_TIGHT_BOUND',None,None,0),('D08_TIGHT_BOUND',[2,19],.15,0),
        ('D10_TASK31_PREFIX',None,None,0)],1):
        if parent:
            d=deepcopy(read(ROOT/'definitions/transmission'/(parent+'.json')))
            # Only the first macro deformation; do not carry rejected fine folds.
            end=next(i for i,s in enumerate(d['steps']) if s['kind']=='spectral')+1
            d['steps']=d['steps'][:end]
            if modes:d['steps'][-1]['spec']['modes']=modes
            if bound:d['steps'][-1]['spec']['curvature_limit']=bound
        else:d=dict(steps=[cc(),cc(),cc()])
        root_spec=dict(root);child_spec=dict(child,twist=twist)
        if k==5:root_spec.update(heights=[.4,1.3,2.2],scales=[.45,.65,.25])
        d.update(id=f'E{k:02}_COMBINATION',comparison_parent=parent or 'R02_NESTED',
            hypothesis='Previous isolated patches attach to a mostly blank carrier. Test whether an actual macro input changes multi-face branch organization, keeping real scope lineage and rejected selections.')
        d['steps'] += [dict(kind='patches',spec=root_spec),cc(),dict(kind='patches',children=True,spec=child_spec),cc()]
        definitions.append(d)
    folder=ROOT/'definitions/combination'
    for d in definitions:write_new(folder/(d['id']+'.json'),d)
    write_new(folder/'batch.json',dict(ids=[d['id'] for d in definitions],
        reason='D06 macro-only had zero sampled transverse contacts and zero opposed quad fans. D08 tight bound also passed these limited screens; actual fine hierarchy is still weak. Test constructed branches on those macro prefixes.',
        not_final_search_limit=True))
    return folder


def conservative():
    parent=read(ROOT/'definitions/combination/E02_COMBINATION.json')
    definitions=[]
    for k,(scales,heights,bend,children) in enumerate([
        ([1,1,1],[.4,.8,1.2],0,False),([1,1,1],[.4,.8,1.2],.2,True),
        ([1,.85,.75],[.7,1.4,2.1],.2,True),([1,1,1],[.4,.8,1.2],0,True)],1):
        d=deepcopy(parent);d.update(id=f'F{k:02}_SCREENED',comparison_parent='E02_COMBINATION',
            hypothesis='E02 root stage had 87 fully sampled transverse crossings despite final sample zero. Preserve first ring footprint and increase outward clearance; require explicit pre-subdivision screen.')
        d['steps']=d['steps'][:4]
        root=deepcopy(parent['steps'][4]['spec']);root.update(scales=scales,heights=heights,bend=bend)
        d['steps'] += [dict(kind='patches',spec=root),dict(kind='audit'),cc()]
        if children:
            child=deepcopy(parent['steps'][6]['spec']);child.update(scales=[1,.85,.65] if k==3 else [1,1,1],
                heights=[.6,1.2,1.8],bend=bend)
            d['steps'] += [dict(kind='patches',children=True,spec=child),dict(kind='audit'),cc()]
        else:d['steps'] += [cc()]
        definitions.append(d)
    folder=ROOT/'definitions/conservative'
    for d in definitions:write_new(folder/(d['id']+'.json'),d)
    write_new(folder/'batch.json',dict(ids=[d['id'] for d in definitions],
        reason='Root-stage full contact check exposed contacts missed by a final coarse sample. Stop flagged topology edits before smoothing; no old output repaired.',
        not_final_search_limit=True))
    return folder


def projected():
    definitions=[]
    for k in range(1,4):
        d=deepcopy(read(ROOT/'definitions/conservative'/f'F{k:02}_SCREENED.json'))
        d.update(id=f'G{k:02}_PROJECTED',comparison_parent=f'F{k:02}_SCREENED',
            hypothesis='F-series contact pairs localize to one right-shoulder disk; its projected boundary crosses once. Admit a simple projected boundary and oriented cap before each sweep, retain the independent post-edit contact screen.')
        for step in d['steps']:
            if step['kind']=='patches':step['spec']['projection_guard']=True
        definitions.append(d)
    folder=ROOT/'definitions/projected'
    for d in definitions:write_new(folder/(d['id']+'.json'),d)
    write_new(folder/'batch.json',dict(ids=[d['id'] for d in definitions],
        reason='Diagnosed self-crossing projected boundary in scope5; outward clearance alone did not fix all four F candidates.',
        not_final_search_limit=True))
    return folder


def straight_children():
    definitions=[]
    for k,radius in enumerate([.24,.18],1):
        d=deepcopy(read(ROOT/'definitions/projected/G02_PROJECTED.json'))
        d.update(id=f'I{k:02}_STRAIGHT_CHILD',comparison_parent='G02_PROJECTED',
            hypothesis='Full G02 child audit found 13 contacts, concentrated in child scope6 with near-tangential cap normals. Isolate curved sweep bend=0 first; then reduce child footprint. Require all-triangle screens before CC and at the final stage.')
        for step in d['steps']:
            if step['kind']=='audit':step['full']=True
            if step['kind']=='patches' and step.get('children'):
                step['spec'].update(bend=0,child_radius=radius)
        d['steps'].append(dict(kind='audit',full=True))
        definitions.append(d)
    folder=ROOT/'definitions/straight_children'
    for d in definitions:write_new(folder/(d['id']+'.json'),d)
    write_new(folder/'batch.json',dict(ids=[d['id'] for d in definitions],
        reason='Projection over an initial normal does not certify a curved sweep path. Full contact checks replace limited sampling for these candidates.',
        not_final_search_limit=True))
    return folder


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['pilot','patches','intrinsic','corrective','transmission','combination','conservative','projected','straight_children','request'])
    p.add_argument('--folder', type=Path); p.add_argument('--tag')
    a = p.parse_args()
    actions=dict(pilot=pilot,patches=patches,intrinsic=intrinsic,corrective=corrective,
                 transmission=transmission,combination=combination,conservative=conservative,
                 projected=projected,straight_children=straight_children)
    print(request(a.folder,a.tag) if a.action=='request' else actions[a.action]())
