"""Declare bounded downstream grammar from actual reviewed clean checkpoints."""
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from cross_cell_crease_study import read,write,digest
from cross_cell_crease_recipes import recipe


def substrate(root,name,stage=None,phase='SCREEN'):
    paths=sorted((root/'study'/phase/name).glob('attempt_*/summary.json'))
    if not paths: raise ValueError('No actual substrate: '+name)
    directory=paths[-1].parent; s=read(paths[-1])
    row=s['stages'][-1] if stage is None else next(r for r in s['stages'] if r['stage']==stage)
    if row['policy']['hard_stop']: raise ValueError('Reviewed substrate has a hard geometry/topology boundary: '+name)
    stage=row['stage']; assets={}
    for suffix in ('.json.gz','_lineage.json.gz','_signatures.json.gz','_networks.json','_operator.json.gz'):
        p=directory/(stage+suffix); assets[p.relative_to(root).as_posix()]=digest(read(p))
    return dict(source_case=name,artifact=directory.relative_to(root).as_posix(),stage=stage,assets=assets,
        reviewed_stage={k:row[k] for k in ('geometry_sha256','geometry_state','design_eligible','statistics','policy')},
        crease_prefix_recipe=deepcopy(s['recipe']),visual_review='See factual review and registered actual views; clean preference and computational usability are separate from design success.')


def fragments(root):
    r=read(root/'inputs/ORDERED_recipe.json'); result={}
    for s in r['steps']:
        if s['kind']!='branch_table': continue
        for q in s['rules']:
            if q['action']=='quiet': continue
            result[s['id']+'__'+q['id']]=dict(operator=q['action'],parameters=deepcopy(q['parameters']),
                reference=dict(recipe='inputs/ORDERED_recipe.json',sha256=digest(r),stage=s['id']+'__'+q['id']))
    return result


def event(id,fragment,placement='ADJACENT',count=32,hops=1,z=.74,spacing=1,role=None,stage=None):
    selector=dict(source_region='lintel',z_min=z,normal_y_min=.15)
    if role: selector.update(role=role,event_stage=stage)
    return dict(id=id,operator=fragment['operator'],parameters=deepcopy(fragment['parameters']),
        parameter_reference=fragment['reference'],placement=placement,max_events=count,hops=hops,spacing=spacing,selector=selector,quad_only=True)


def roof(fr,placement='ADJACENT',count=32,hops=1,z=.74,role='EXTRUSION_SIDE'):
    return event('crease_roof',fr['new__branch'],placement,count,hops,z,role=role,stage='event_1')


def micro(fr,placement='JUNCTION',count=20,hops=2,z=.74,seed_role='INNER_CAP',seed_stage='event_2',three=False):
    first=event('crease_micro_frame',fr['split__cap'],placement,count,hops,z,role=seed_role,stage=seed_stage)
    child=event('crease_micro_cap',fr['descend__cap_child'],placement,count,hops,z,spacing=0)
    child.update(parent_stage=first['id'],parent_role='INNER_CAP')
    result=[first,child]
    if three:
        last=event('crease_micro_terminal_frame',fr['descend__side_child'],placement,count,hops,z,spacing=0)
        last.update(parent_stage=child['id'],parent_role='EXTRUSION_CAP'); result.append(last)
    return result


def compose(root,name,family,base,stages,intent,stage=None,phase='SCREEN',preserve_existing=False):
    p=substrate(root,base,stage,phase)
    prefix=p['crease_prefix_recipe']
    r=recipe(name,family,prefix['input'],[],generations=0)
    r.update(mode=prefix['mode'],prepared_substrate=p,composition=stages,hypothesis=intent,
        operator_order='Exact frozen backbone -> declared networks -> verified CC prefix -> listed local event stages -> STOP')
    target=root/'study/recipes'/(name+'.json')
    if preserve_existing and target.exists():
        old=read(target); a=deepcopy(old); b=deepcopy(r)
        a.pop('hypothesis',None);b.pop('hypothesis',None)
        if a!=b:raise ValueError('Refuse to replace an existing declared design under the same ID: '+name)
        return old
    write(target,r); return r


def declare_downstream(root,only=None):
    """Finite design-logic comparisons, not a continuous height grid."""
    fr=fragments(root)
    bases=['A01','A02','A03','A08','A10','A11','A12','A13','A15','B03','B08','B10','B12','B14']
    results=[]
    for i,base in enumerate(bases,1):
        if only is not None and not {f'C{i:02d}',f'D{i:02d}'} & set(only): continue
        placement='JUNCTION' if base in ('A10','A11','A12','A13','B10') else 'ADJACENT'
        steps=[roof(fr,placement=placement,count=24 if placement=='JUNCTION' else 48,hops=2)]
        if placement=='JUNCTION' and i>5:
            steps[0]['selector'].pop('role');steps[0]['selector'].pop('event_stage')
        steps[0]['stratify_by']='C0_FACE'
        if only is None or f'C{i:02d}' in only:
            results.append(compose(root,f'C{i:02d}','C_CREASE_ROOF',base,steps,
                'Sparse existing Roof follows actual declared edge tangents; equal source-cohort opportunity, lower supports quiet.',stage='G1',preserve_existing=True))
        steps=micro(fr,placement=placement,count=16 if placement=='JUNCTION' else 32,hops=2,three=i in (3,5,9,12))
        if placement=='JUNCTION':
            steps[0]['selector'].pop('role');steps[0]['selector'].pop('event_stage')
        steps[0]['stratify_by']='C0_FACE'
        if i in (4,8,11): steps[0]['selector'].update(role='FRAME_SIDE',event_stage='event_2')
        if only is None or f'D{i:02d}' in only:
            results.append(compose(root,f'D{i:02d}','D_CREASE_NESTED',base,steps,
                'Select actual crease-band/junction source roles, then ring -> child cap; selected cases add one child ring.',stage='G1',preserve_existing=True))
    # Each tuple is a declared design logic: topology/source/placement/quietness,
    # roof relationship and nested parent role differ, rather than only height.
    designs=[
        ('A01','ADJACENT','ADJACENT',24,16,'INDEPENDENT',.78,False),
        ('A02','ADJACENT','ADJACENT',32,16,'RIDGE_CHILD',.74,False),
        ('A03','ADJACENT','JUNCTION',48,12,'INDEPENDENT',.74,False),
        ('A08','ADJACENT','ADJACENT',48,16,'RIDGE_CHILD',.78,False),
        ('A10','JUNCTION','JUNCTION',32,16,'INDEPENDENT',.74,True),
        ('A11','ADJACENT','JUNCTION',48,12,'RIDGE_CHILD',.74,False),
        ('A12','JUNCTION','JUNCTION',24,12,'RIDGE_CHILD',.80,True),
        ('A13','JUNCTION','ADJACENT',32,20,'INDEPENDENT',.78,False),
        ('A14','JUNCTION','JUNCTION',32,12,'INDEPENDENT',.74,True),
        ('A15','ADJACENT','ADJACENT',64,24,'RIDGE_CHILD',.74,False),
        ('B03','ADJACENT','JUNCTION',32,12,'INDEPENDENT',.74,False),
        ('B08','ADJACENT','ADJACENT',48,16,'RIDGE_CHILD',.78,True),
        ('B09','ADJACENT','ADJACENT',24,20,'INDEPENDENT',.80,False),
        ('B10','JUNCTION','JUNCTION',32,12,'RIDGE_CHILD',.74,False),
        ('B11','ADJACENT','JUNCTION',48,16,'INDEPENDENT',.74,True),
        ('B12','ADJACENT','ADJACENT',32,16,'RIDGE_CHILD',.78,False),
        ('B13','ADJACENT','ADJACENT',48,24,'INDEPENDENT',.80,False),
        ('B14','ADJACENT','ADJACENT',24,12,'RIDGE_CHILD',.78,True),
        ('A10','ADJACENT','JUNCTION',16,8,'INDEPENDENT',.84,False),
        ('A15','ADJACENT','ADJACENT',32,16,'INDEPENDENT',.84,True)]
    for i,(base,rp,mp,rc,mc,relation,z,three) in enumerate(designs,1):
        if only is not None and f'E{i:02d}' not in only: continue
        r=roof(fr,placement=rp,count=rc,hops=2,z=z);r['stratify_by']='C0_FACE'
        ms=micro(fr,placement=mp,count=mc,hops=2,z=z,three=three);ms[0]['stratify_by']='C0_FACE'
        if rp=='JUNCTION':
            r['selector'].pop('role');r['selector'].pop('event_stage')
        if mp=='JUNCTION':
            ms[0]['selector'].pop('role');ms[0]['selector'].pop('event_stage')
        if relation=='RIDGE_CHILD':
            ms[0]['selector'].pop('role',None);ms[0]['selector'].pop('event_stage',None)
            ms[0].update(parent_stage=r['id'],parent_role='RIDGE_SIDE')
        results.append(compose(root,f'E{i:02d}','E_FULL_SYNTHESIS',base,[r,*ms],
            f'{base}: {rp} Roof; {mp} nested nodes on {relation}; source height>{z}; sparse counts {rc}/{mc}; no finish.',stage='G1',preserve_existing=True))
    target=root/'study/downstream_declarations.json'; previous=read(target) if target.exists() else []
    declarations={r['id']:r for r in previous}
    for r in results: declarations[r['id']]=dict(id=r['id'],source=r['prepared_substrate']['source_case'],
        source_stage=r['prepared_substrate']['stage'],hypothesis=r['hypothesis'])
    write(target,list(declarations.values()))
    print('Declared',len(results),'bounded downstream recipes from actual clean prefixes; total',len(declarations))
    return results


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--names',nargs='+')
    a=p.parse_args();declare_downstream(a.output_root,a.names)
