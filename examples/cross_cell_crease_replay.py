"""Rebuild the retained gate grammar independently and compare actual outputs."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from cross_cell_crease_study import read,write,digest
from cross_cell_crease_views import best_attempt


def declare(root,phase,name):
    directory=best_attempt(root,phase,name);s=read(directory/'summary.json')
    if s['status']!='SUCCESS' or s['stages'][-1]['policy']['hard_stop']:
        raise ValueError('Retain only a completed computationally usable grammar; contacts are diagnostic.')
    benchmark=deepcopy(s['recipe']);benchmark.update(id='RETAINED_GATE_GRAMMAR',
        family='RETAINED_BENCHMARK',selected_from=dict(phase=phase,id=name),
        assessment='Strongest retained ordinary grammar; this label does not certify a Grotesque Hero.')
    benchmark['composition_stage_base']=benchmark.get('composition_stage_base',benchmark['generations']+12)
    replay=deepcopy(benchmark);replay['id']='RETAINED_GATE_REPLAY'
    if 'prepared_substrate' in replay:
        p=replay.pop('prepared_substrate');prefix=p['crease_prefix_recipe']
        if not p['stage'].startswith('G') or not p['stage'][1:].isdigit():
            raise ValueError('Independent replay needs an explicit CC prefix generation.')
        replay.update(input=prefix['input'],networks=deepcopy(prefix['networks']),
            mode=prefix['mode'],generations=int(p['stage'][1:]))
        if 'fold_schedule' in prefix:replay['fold_schedule']=deepcopy(prefix['fold_schedule'][:replay['generations']])
        def asset(suffix):return p['assets'][p['artifact']+'/'+p['stage']+suffix]
        replay['expected_substrate']=dict(geometry_sha256=asset('.json.gz'),
            networks_sha256=asset('_networks.json'),signatures_sha256=asset('_signatures.json.gz'))
    replay['assessment']='Independent original-backbone replay; matching bytes are required before declaring reproducibility.'
    for r in (benchmark,replay):
        path=root/'study/recipes'/(r['id']+'.json')
        if path.exists() and read(path)!=r:raise ValueError('Retained grammar ID already declared differently.')
        write(path,r)
    write(root/'study/retained_selection.json',dict(source=directory.relative_to(root).as_posix(),
        selected_recipe_sha256=digest(s['recipe']),benchmark=benchmark['id'],replay=replay['id'],
        contract='Rebuild routing and all CC generations from the original frozen backbone; same composition stage indices and exact local parameters.'))
    print('Declared retained grammar and independent replay')


def compare(root):
    a=best_attempt(root,'HERO','RETAINED_GATE_GRAMMAR');b=best_attempt(root,'REPLAY','RETAINED_GATE_REPLAY')
    original=root/read(root/'study/retained_selection.json')['source']
    summaries=[read(p/'summary.json') for p in (original,a,b)]
    suffixes=['terminal.json','terminal_networks.json','terminal_lineage.json.gz',
        'terminal_signatures.json.gz','branch_signatures.json']
    rows=[dict(artifact=n,selected_sha256=digest(read(original/n)),reference_sha256=digest(read(a/n)),replay_sha256=digest(read(b/n)),
        exact=digest(read(original/n))==digest(read(a/n))==digest(read(b/n))) for n in suffixes]
    good=all(s['status']=='SUCCESS' and s['source_immutable'] for s in summaries) and all(r['exact'] for r in rows)
    result=dict(status='PASS' if good else 'FAIL',comparison=rows,
        benchmark=a.relative_to(root).as_posix(),replay=b.relative_to(root).as_posix(),
        scope='Canonical JSON equality of coordinates/oriented topology, crease graph, complete terminal histories/events/anchors, positive branch paths and branch diagnostics; runtime/timings excluded.')
    write(root/'study/retained_reproduction.json',result);print(result['status'],[(r['artifact'],r['exact']) for r in rows])
    if not good:raise ValueError('Actual independent replay failed; see retained comparison.')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--phase');p.add_argument('--select');p.add_argument('--compare',action='store_true');a=p.parse_args()
    if a.compare:compare(a.output_root)
    elif a.select and a.phase:declare(a.output_root,a.phase,a.select)
    else:p.error('Choose --phase / --select or --compare')
