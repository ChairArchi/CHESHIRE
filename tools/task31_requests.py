"""Explicit matched physical views of actual Task31 checkpoints."""
import sys
from task31_study import ROOT,read,write


def request(tag,items,**options):
    config=dict(resolution=1400,width=2600,cols=3,size=1000,pages=30,items=items);config.update(options)
    write(ROOT/'definitions'/('render_'+tag+'.json'),config)


def main(tag):
    v=read(ROOT/'definitions/task31_variant_definitions.json')['StageA']
    if tag in ('cube1','cube2'):
        items=([dict(label='Task30 cube G8',stage=str(ROOT/'controls/cube/G8'))] if tag=='cube1' else [])
        items += [dict(label=d['id']+' G8',stage=str(ROOT/'candidates/cube'/d['id']/'G8')) for d in (v[:6] if tag=='cube1' else v[6:])]
        request(tag,items)
    elif tag=='detail':
        roots=[('Task30',ROOT/'controls/cube')]+[(name,ROOT/'candidates/cube'/name) for name in sys.argv[2:]]
        items=[dict(label=name+' G8 '+angle,stage=str(path/'G8'),width=900,target=[0,-250,0],angles=angles) for name,path in roots for angle,angles in [('front',[0,0]),('oblique',[28,22])]]
        request(tag,items,sheet_name='TASK31_cube_detail_comparison.png')
    elif tag in ('cube_compare','cube_progression'):
        definition=read(ROOT/'definitions/task31_lead_pipeline.json')['cube'];lead=ROOT/'candidates/cube'/definition['id']
        items=([dict(label=name+' G8 '+angle,stage=str(path/'G8'),angles=angles) for name,path in [('Task30',ROOT/'controls/cube'),(definition['id'],lead)] for angle,angles in [('front',[0,0]),('oblique',[28,22])]] if tag=='cube_compare' else
            [dict(label=definition['id']+f' G{g}',stage=str(lead/f'G{g}')) for g in range(9)])
        request(tag,items,sheet_name='TASK30_vs_TASK31_cube.png' if tag=='cube_compare' else 'TASK31_cube_progression.png')
    elif tag in ('gate','gate_progression','gate_detail','gate_compare'):
        v=read(ROOT/'definitions/gate_specimen_definition.json')['variants']
        lead=read(ROOT/'definitions/task31_lead_pipeline.json').get('gate') or v[-1]
        if tag=='gate':items=[dict(label=d['id']+' G8',stage=str(ROOT/'candidates/gate'/d['id']/'G8'),width=6800,target=[-400,-18,1700]) for d in v]
        elif tag=='gate_progression':items=[dict(label=lead['id']+f' G{g}',stage=str(ROOT/'candidates/gate'/lead['id']/f'G{g}'),width=6800,target=[-400,-18,1700],angles=[0,0]) for g in range(9)]
        elif tag=='gate_compare':items=[dict(label=name+' G8 '+angle,stage=str(ROOT/'candidates/gate'/name/'G8'),width=6800,target=[-400,-18,1700],angles=angles) for name in ('TASK30_GATE',lead['id']) for angle,angles in [('front',[0,0]),('oblique',[28,22])]]
        else:items=[dict(label=d['id']+' lintel G8 '+name,stage=str(ROOT/'candidates/gate'/d['id']/'G8'),width=1800,target=[-400,-18,3050],angles=angles) for d in v for name,angles in [('front',[0,0]),('oblique',[28,22])]]
        request(tag,items,cols=2 if tag=='gate_compare' else 3,sheet_name={'gate':'TASK31_gate_variants.png','gate_progression':'TASK31_gate_progression.png','gate_detail':'TASK31_gate_detail.png','gate_compare':'TASK30_vs_TASK31_gate.png'}[tag])


if __name__=='__main__':main(sys.argv[1])
