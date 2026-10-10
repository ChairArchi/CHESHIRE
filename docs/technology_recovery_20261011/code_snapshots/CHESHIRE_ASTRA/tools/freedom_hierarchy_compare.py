"""Unchanged finite chart metrics for intentionally self-intersecting exploration.

This measures native-triangle points, not solid validity or continuous ridges.
"""
import argparse,json,sys,shutil
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks
R=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(R/'tools'),str(R/'examples')]
import astra_hierarchy as h
from hero_design_sprint import guarded,windows_memory
from cheshire.astra_validation import embedding_failures
BASE=Path('E:/CHESHIRE_DATA/astra_freedom')
CANDIDATES=['F04_COHERENT','F05_COHERENT_STEER','F06_SEED','F07_LOCAL','F08_OSCILLATE','F09_BROAD_SPLIT','F11_LOW_SPLIT']
LIMIT='Finite construction-chart samples on actual triangle surfaces, including self-intersecting surfaces. Neither solid/no-overlap evidence nor continuous ridge certification. Radial excess is not intrinsic fold depth.'

def read(p):return json.loads(p.read_text(encoding='utf8'))
def interval(a,b):return set((np.arange(a,b+h.SAMPLES*(b<=a)+1)%h.SAMPLES).tolist())
def contrast(profile,b):return float(min(profile[b['left_crest']],profile[b['right_crest']])-profile[b['valley']])
def conservative_novelty(parent,child,event,threshold=15.):
    """Finite novelty inside the child's flanking-crest interval only.

    Interval endpoints are excluded by find_peaks; prominence is limited by
    those endpoints. This rejects resolved previous/shifted interior valleys,
    not subthreshold precursors or a valley migrating across the endpoints.
    """
    n=len(parent);a=event['left_crest'];b=event['right_crest']
    ids=np.arange(a,b+n*(b<=a)+1)%n
    previous,_=find_peaks(-parent[ids],prominence=threshold)
    crossing=bool(contrast(parent,event)<threshold<=contrast(child,event))
    old=[int(ids[i]) for i in previous]
    label='EXISTING_OR_SHIFTED' if old else 'NOVEL_WITHIN_INTERVAL' if crossing else 'NO_THRESHOLD_CROSSING'
    return dict(same_coordinate_threshold_crossing=crossing,parent_interval_valleys=old,novelty_label=label,conservative_new=bool(crossing and not old))

def verify(root):
    for rel,value in read(root/'source_identity.json').items():
        if h.sha(R/rel)!=value:raise RuntimeError('Measurement source changed: '+rel)

def pocket_lineage(candidate,stages):
    labels={};current={}
    for g in stages:
        stage=candidate/f'G{g}';p=stage/'operator_state.npz'
        if not p.exists():continue
        with np.load(p) as z:
            parent=z['parent_face'] if 'parent_face' in z.files else z['source_parent_face'] if 'source_parent_face' in z.files else None
            if parent is None:continue
            current={k:v[parent] for k,v in current.items()}
            if 'output_cap_rim_role' in z.files:
                current[f'G{g}_role']=z['output_cap_rim_role'].copy()
                current[f'G{g}_region']=np.arange(len(parent))
                current[f'G{g}_source_parent']=parent.copy()
        if not current:continue
        with np.load(stage/'quad_state.npz') as q,np.load(stage/'mesh.npz') as m:
            if len(m['faces'])!=4*len(q['faces']):raise ValueError('Pocket native/quad 4:1 mismatch')
            pairs=np.stack([q['faces'],np.roll(q['faces'],-1,axis=1)],axis=-1).reshape(-1,2)
            if not np.array_equal(m['faces'][:,:2],pairs):raise ValueError('Native triangle/quad ancestry mismatch')
        labels[g]={k:v.copy() for k,v in current.items()}
    return labels

def interval_lineage(stage,ids,labels):
    result={}
    if stage not in labels:return result
    with np.load(ids['path']) as z:quads=z['sample_triangle_ids']//4
    for born in sorted({k.split('_')[0] for k in labels[stage]}):
        roles=labels[stage][born+'_role'][quads[ids['indices']]]
        regions=labels[stage][born+'_region'][quads[ids['indices']]]
        unique=np.unique(regions);role=np.unique(roles)
        result[born]=dict(region_count=len(unique),roles=[int(x) for x in role],single_region=int(unique[0]) if len(unique)==1 else None,contained_in_cap=bool(len(unique)==1 and np.all(roles==0)),contained_in_rim=bool(len(unique)==1 and np.all(roles==1)))
    return result

def analyze(candidate,dest,stages):
    h.run(candidate,dest,stages)
    summary=read(dest/'summary.json');states=[];profiles={};section_paths={};lineage=pocket_lineage(candidate,stages)
    for stage in summary['stages']:
        g=stage['generation'];p=candidate/f'G{g}'/'validation.json'
        if p.exists():
            v=read(p)
            if v['native_sha256']!=stage['mesh_sha256']:raise ValueError('Validation/native SHA mismatch')
            contacts=v['contacts'];fail=embedding_failures(v['embedding'],2)
            states.append(dict(generation=g,validation_path=str(p),sha256=h.sha(p),recorded_status=v['status'],embedding_failures=fail,transverse_contacts=contacts['transverse_contacts'],self_intersection_invalid=bool(contacts['transverse_contacts']),limitation=LIMIT))
        else:states.append(dict(generation=g,status='COPIED_BASELINE_NOT_REVALIDATED',limitation=LIMIT))
        for section in stage['sections']:
            if section['valid']:
                with np.load(section['path']) as z:profiles[g,section['z']]=z['radial_excess'].copy()
                section_paths[g,section['z']]=section['path']
    rows=[];events={}
    for comparison in summary['comparisons']:
        g=comparison['parent_generation'];gen_rows=[]
        for section in comparison['sections']:
            z=section['z']
            if not section['valid']:continue
            before=profiles[g,z];after=profiles[g+1,z];records=[]
            for event in section['child_basins']:
                old=contrast(before,event);new=contrast(after,event)
                record=dict(event,previous_same_coordinate_contrast=old,following_same_coordinate_contrast=new,threshold_crossing=bool(old<15<=new),**conservative_novelty(before,after,event))
                indices=sorted(interval(event['left_crest'],event['right_crest']))
                parent_labels=interval_lineage(g,dict(path=section_paths[g,z],indices=indices),lineage)
                child_labels=interval_lineage(g+1,dict(path=section_paths[g+1,z],indices=indices),lineage)
                shared={}
                for born,a in parent_labels.items():
                    b=child_labels[born]
                    shared[born]=dict(same_single_cap=bool(a['contained_in_cap'] and b['contained_in_cap'] and a['single_region']==b['single_region']),same_single_rim=bool(a['contained_in_rim'] and b['contained_in_rim'] and a['single_region']==b['single_region']))
                record.update(parent_interval_lineage=parent_labels,child_interval_lineage=child_labels,same_lineage_region=shared)
                records.append(record)
            events[g,z]=records
            ratios=[x['ratio'] for x in section['parent_envelope']]
            gen_rows.append(dict(z=z,basin_records=records,parent_envelope=section['parent_envelope'],threshold_crossings=sum(x['threshold_crossing'] for x in records),conservative_new=sum(x['conservative_new'] for x in records)))
        ratios=[p['ratio'] for row in gen_rows for p in row['parent_envelope']]
        depths=[b['depth'] for row in gen_rows for b in row['basin_records']]
        rows.append(dict(parent_generation=g,child_generation=g+1,valid_sections=len(gen_rows),sections_with_basins=sum(bool(row['basin_records']) for row in gen_rows),basin_records=sum(len(row['basin_records']) for row in gen_rows),threshold_crossings=sum(row['threshold_crossings'] for row in gen_rows),sections_with_threshold_crossings=sum(bool(row['threshold_crossings']) for row in gen_rows),conservative_new=sum(row['conservative_new'] for row in gen_rows),sections_with_conservative_new=sum(bool(row['conservative_new']) for row in gen_rows),depth_min_median_max=None if not depths else [float(x) for x in np.quantile(depths,[0,.5,1])],parent_envelope_ratio_min_median_max=None if not ratios else [float(x) for x in np.quantile(ratios,[0,.5,1])],sections=gen_rows))
    chains=[]
    for g in stages[:-2]:
        if g+1 not in stages or g+2 not in stages:continue
        for z in h.Z_LEVELS.tolist():
            for first in events.get((g,z),[]):
                if not first['threshold_crossing']:continue
                outer=interval(first['parent_left'],first['parent_right'])
                retained=contrast(profiles[g+2,z],first)
                for second in events.get((g+1,z),[]):
                    if not second['threshold_crossing']:continue
                    if second['parent_peak'] not in (first['left_crest'],first['right_crest']):continue
                    if not interval(second['parent_left'],second['parent_right'])<=outer:continue
                    chains.append(dict(generations=[g,g+1,g+2],z=z,first=first,second=second,first_valley_final_same_coordinate_contrast=retained,first_valley_retained_at_threshold=bool(retained>=15),both_conservatively_new=bool(first['conservative_new'] and second['conservative_new'])))
    result=dict(candidate=str(candidate),source_summary=str(dest/'summary.json'),source_summary_sha256=h.sha(dest/'summary.json'),stages=states,comparisons=rows,finite_child_grandchild_chains=chains,chains_with_first_valley_retained=sum(c['first_valley_retained_at_threshold'] for c in chains),conservative_new_chains=sum(c['both_conservatively_new'] for c in chains),conservative_new_chains_retained=sum(c['both_conservatively_new'] and c['first_valley_retained_at_threshold'] for c in chains),conservative_novelty_definition='Threshold crossing plus no prior prominence15 minimum strictly inside child flanking-crest interval. Interval-local prominence and endpoints limit this test; not proof of unprecedented surface topology.',newness_definition='Depth crosses 15 at identical left-crest/valley/right-crest angular samples; no claim of new critical point identity.',chain_definition='Two threshold-crossing events; second parent peak equals a first flanking crest; second basin lies within initial parent interval. Count retained first-valley depth separately. Finite chart correspondence only.',limitation=LIMIT)
    h.write(dest/'freedom_measurement.json',result)
    print(candidate.name,[(x['parent_generation'],x['basin_records'],x['threshold_crossings']) for x in rows],'chains',len(chains),'retained',result['chains_with_first_valley_retained'],flush=True)
    return result

def worker(root):
    verify(root);all_results=[]
    for case in read(root/'request.json')['cases']:
        name=case['candidate'];stages=case['stages']
        candidate=Path(case.get('path',str(BASE/'experiments'/name)))
        if not case.get('external_legacy') and not (candidate/'completed.json').exists():raise ValueError('Experiment incomplete: '+name)
        for g in stages[1:]:
            if not (candidate/f'G{g}'/'validation.json').exists():raise ValueError('Missing stage validation')
        dest=root/name;dest.mkdir(exist_ok=False)
        all_results.append(analyze(candidate,dest,stages))
    verify(root)
    h.write(root/'comparison.json',dict(candidates=all_results,limitation=LIMIT))

def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--candidates',nargs='+',default=CANDIDATES);p.add_argument('--paths',nargs='+',type=Path);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if not a.tag.replace('_','').isalnum():raise ValueError('Fresh safe tag required')
    root=BASE/'hierarchy'/a.tag
    if a.worker:worker(root);return
    mem=windows_memory()
    if mem['status']!='MEASURED' or mem['available_bytes']<2*1024**3:raise MemoryError('Measured reserve required')
    cases=[]
    for item in (a.paths if a.paths else a.candidates):
        name=item.name if a.paths else item
        if not name.replace('_','').isalnum():raise ValueError('Safe candidate name required')
        candidate=item if a.paths else BASE/'experiments'/name
        if not a.paths and not (candidate/'completed.json').exists():raise ValueError('Experiment incomplete: '+name)
        stages=sorted(int(d.name[1:]) for d in candidate.iterdir() if d.is_dir() and d.name.startswith('G') and d.name[1:].isdigit() and (d/'mesh.npz').exists())
        if len(stages)<2 or any(b!=a+1 for a,b in zip(stages,stages[1:])):raise ValueError('Consecutive completed stages required')
        cases.append(dict(candidate=name,stages=stages,path=str(candidate.resolve()),external_legacy=bool(a.paths)))
    root.mkdir(parents=True,exist_ok=False)
    h.write(root/'request.json',dict(cases=cases,z_levels=h.Z_LEVELS.tolist(),samples=h.SAMPLES,prominence=15.,memory=mem,limitation=LIMIT))
    sources=['tools/freedom_hierarchy_compare.py','tools/astra_hierarchy.py','tools/task35_analyze.py','examples/task29_search.py','examples/hero_design_sprint.py','src/cheshire/astra_validation.py','src/cheshire/reference_subdivision.py']
    for rel in sources:
        d=root/'source'/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,d)
    h.write(root/'source_identity.json',{rel:h.sha(root/'source'/rel) for rel in sources})
    result=guarded(['--tag',a.tag,'--worker'],root/'logs/run',worker_script=Path(__file__))
    h.write(root/'execution.json',result)
    if result['exit_code']:raise SystemExit(result['exit_code'])

if __name__=='__main__':main()
