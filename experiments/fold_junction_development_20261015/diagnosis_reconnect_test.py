"""Read-only actual mature-prefix check of axial reconnection."""
from pathlib import Path
import json
import numpy as np
from axial_reconnect import build

HERE=Path(__file__).resolve().parent
STATES=Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states')
SOURCE=Path('E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial02/NESTED/control_quad.npz')

with np.load(STATES/'G03_SIDEWALL/evidence.npz',allow_pickle=False) as data:
    owner=data['face_event_ids']
with np.load(STATES/'G04_NEUTRAL/control_quad.npz',allow_pickle=False) as data:
    quads, chart=data['faces'],data['chart']
    count=len(data['xyz'])
with np.load(STATES/'G04_NEUTRAL/evidence.npz',allow_pickle=False) as data:
    body=owner[data['parent_face']]==0
    vp={axis:data['mirror_'+axis.lower()+'_vertex_pairs'] for axis in ('X','Y')}
with np.load(SOURCE,allow_pickle=False) as data:
    xyz=data['xyz'][:count].copy()
delta,stats=build(xyz,quads,chart,body,vp)
assert np.array_equal(xyz[:,:2],(xyz+delta)[:,:2])
assert np.array_equal(delta[vp['X'],2],delta[:,2])
assert np.array_equal(delta[vp['Y'],2],delta[:,2])
summary={key:value for key,value in stats.items() if key not in ('corrected_intervals','skipped_intervals')}
summary['corrected_interval_count']=len(stats['corrected_intervals'])
summary['skipped_interval_count']=len(stats['skipped_intervals'])
print(json.dumps(summary,indent=2),flush=True)
target=HERE/'diagnosis_reconnect_results.json'
if target.exists():raise FileExistsError(target)
target.write_text(json.dumps(stats,indent=2),encoding='utf8')
