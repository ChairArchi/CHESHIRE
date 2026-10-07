"""Compact factual delivery from actual retained artifacts, no design scoring."""
import argparse
from collections import Counter
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'));sys.path.insert(0,str(ROOT/'tools'))
from cross_cell_crease_study import read,write,digest,file_hash
from cross_cell_crease_review import table
from cross_cell_crease_views import best_attempt
from morphology import windows_memory

PHASES=('CONTROL','SCREEN','DESIGN','REFINE','EXPLORATION','CAPABILITY')


def collect(root,selection,destination):
    destination.mkdir(parents=True,exist_ok=True);ledgers={p:table(root,p) for p in PHASES}
    counts={}
    for phase,rows in ledgers.items():
        counts[phase]=dict(named_requests=len(rows),latest_status_counts=dict(Counter(r['status'] for r in rows)),
            attempts=len(list((root/'study'/phase).glob('*/attempt_*'))),any_sampled_contact=sum(r['any_contact'] for r in rows),
            diagnostic_cap_ever=sum(r['cap_ever'] for r in rows))
        write(destination/('table_'+phase.lower()+'.json'),rows)
    finalists=[];monitors=[];recipes=[];images=[]
    for item in selection['finalists']:
        phase,name=item['phase'],item['id'];directory=best_attempt(root,phase,name);s=read(directory/'summary.json')
        row=next(r for r in s['stages'] if r['stage']==item['stage']) if item.get('stage') else s['stages'][-1]
        stage=row['stage'];f=dict(item);f.update(stage=stage,artifact=directory.relative_to(root).as_posix(),
            status=s['status'],geometry_sha256=row['geometry_sha256'],statistics=row['statistics'],
            sampled_contacts=row['crossings']['sampled_transverse_crossings'],sample_cap_reached=row['crossings']['sample_limit_reached'],
            recorded_geometry_state=row['geometry_state'],networks=row['networks'],process=s.get('process'),
            degenerate_fan_faces=len(row['diagnostics']['degenerate_fan_faces']),
            note='Selected checkpoint, not necessarily the requested terminal. Contact counts are diagnostic; visual judgment is separate.')
        metric=root/'renders'/phase/(name+'_'+stage+'_high_angle_metrics.json')
        if metric.exists():
            measured=read(metric)
            f['high_angle_components']={k:v for k,v in measured.items() if k!='components'}
            f['high_angle_components'].update(artifact=metric.relative_to(root).as_posix(),sha256=file_hash(metric),
                first_12_components=[dict(edge_count=c['edge_count'],length=c['length'],maximum_angle=c['maximum_angle'],
                    parent_cell_count=len(c['parent_cells']),C0_face_count=len(c['C0_faces']),cross_cell=c['cross_cell'])
                    for c in measured['components'][:12]],
                retention='Full actual component ancestry remains in the referenced external metrics file; lightweight Git table retains counts and first 12 recorded components.')
        finalists.append(f);recipes.append(dict(phase=phase,recipe=s['recipe']))
        if 'monitor' in row:monitors.append(dict(id=name,phase=phase,stage=stage,monitor=row['monitor']))
        for suffix in ('front','oblique','front_network','oblique_network','detail','node','wire','sharpness','ancestry','high','depth'):
            p=root/'renders'/phase/(name+'_'+stage+'_'+suffix+'.png')
            if p.exists():images.append(dict(case=name,stage=stage,view=suffix,path=p.relative_to(root).as_posix(),sha256=file_hash(p),geometry_sha256=row['geometry_sha256']))
    allrows=[r for rows in ledgers.values() for r in rows]
    continuation_count=sum(r['family']=='LARGE_TAPER_CONTINUATION' for r in ledgers['CAPABILITY'])
    memory=windows_memory()
    result=dict(baseline='66cb4f90d0b15834d358db5ce2569c813379b0b1',phase_counts=counts,
        named_gate_requests=len(allrows)-len(ledgers['CONTROL']),continuation_segments=continuation_count,
        distinct_gate_candidate_strategies=len(allrows)-len(ledgers['CONTROL'])-continuation_count,
        named_gate_technical_completions=sum(r['status']=='SUCCESS' for r in allrows if r['phase']!='CONTROL'),
        gate_requests_with_any_contact=sum(r['any_contact'] for r in allrows if r['phase']!='CONTROL'),
        cap_request_count=sum(r['cap_ever'] for r in allrows),
        maximum_finished_peak_bytes=max((r['peak_bytes'] or 0 for r in allrows),default=0),
        resources=dict(system_total_bytes=memory['physical_bytes'],process_tree_plus_driver_limit=4*1024**3,
            available_memory_floor=memory['available_floor_bytes'],case_seconds=900,ordinary_faces=300000),
        original_policy='Saved pre-override requests retain original contact policy',
        current_policy='Contacts and diagnostic cap do not stop compatible finite evolution; SELF_INTERSECTING_CAPABILITY',
        labels=selection['labels'],grotesque_gate_candidate=None,production='NOT_JUSTIFIED',rhino='NOT_ADDED; no real/strong near-Hero established; actual host not run',
        assessment=selection['assessment'],test_result=selection['test_result'])
    write(destination/'result_summary.json',result);write(destination/'finalists.json',finalists)
    write(destination/'recipes.json',recipes);write(destination/'principal_monitors.json',monitors);write(destination/'image_manifest.json',images)
    write(root/'study/delivery_summary.json',result)
    print('Collected',len(finalists),'finalists;',result['distinct_gate_candidate_strategies'],'gate strategies;',result['named_gate_requests'],'named gate requests')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True);a=p.parse_args();collect(a.output_root,read(a.selection),a.destination)
