"""Read/replay latest Task31 checkpoints; separate observations from hypotheses."""
import copy
import json
import sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / 'examples'), str(REPO / 'tools')]
from task29_search import load_mesh
from task33_preserve import ROOT, sha, write_new
from cheshire.reference_subdivision import fields, subdivide, topology
from cheshire.regional_generation import advance, birth, coarse_edit
from cheshire.progressive_gates import PLANE_X


def distribution(values):
    a = np.asarray(values)
    return dict(min=float(a.min()), median=float(np.median(a)), p90=float(np.quantile(a, .9)), max=float(a.max()))


def diagnose():
    source = Path('E:/CHESHIRE_DATA/task31/lead/gate')
    spec = json.loads(Path('E:/CHESHIRE_DATA/task30/definitions/final_selected_pipeline.json').read_text())
    definition = json.loads((REPO / 'studies/task31/definitions/task31_lead_pipeline.json').read_text())['cube']
    records = []
    m = load_mesh(source / 'G0')
    roles = np.full(len(m.faces), -1, np.int8)
    members = None
    for g in range(1, 6):
        if g == 3:
            m, roles, members, _, _ = coarse_edit(m, roles, members, definition['edit'], target=[PLANE_X, -18.533447265625, 3050])
        f = fields(m)
        out, roles, members, meta, state = advance(m, roles, members, spec['steps'][g-1], definition)
        saved = load_mesh(source / ('G' + str(g)))
        if not np.array_equal(out.xyz, saved.xyz) or not np.array_equal(out.faces, saved.faces):
            raise ValueError('Current exact replay differs at G' + str(g))
        if g == definition['born']:
            members, _ = birth(out, definition['descriptor'])
        controls = state
        offsets = {}
        for k, s, n in [('wf','face','nf'), ('we','edge','ne'), ('wp','vertex','nv')]:
            w = controls.get('resolved_' + k, np.full(len(state[s+'_scale']), spec['steps'][g-1]['row']['weights'].get(k, 0)))
            offsets[k] = dict(coefficient=distribution(w), physical_requested=distribution(np.abs(w)*state[s+'_scale']),
                              normal_vector_length=distribution(np.linalg.norm(f[n],axis=1)),
                              physical_normal_term=distribution(np.linalg.norm(f[n]*w[:,None]*state[s+'_scale'][:,None],axis=1)))
        neutral, _, _ = subdivide(m, {'weights': {}}, scale_mode='LOCAL_INCIDENT_SCALE')
        reflected = saved.xyz.copy(); reflected[:,0] = 2*PLANE_X-reflected[:,0]
        nearest, _ = cKDTree(saved.xyz).query(reflected)
        records.append(dict(generation=g, input_mesh=str(source/('G'+str(g-1))), output_sha256=sha(source/('G'+str(g))/'mesh.npz'),
                            exact_replay=True, input_edge=distribution(f['lengths']), offsets=offsets,
                            actual_old_vertex_movement=distribution(np.linalg.norm(out.xyz[:len(m.xyz)]-m.xyz,axis=1)),
                            neutral_old_vertex_movement=distribution(np.linalg.norm(neutral.xyz[:len(m.xyz)]-m.xyz,axis=1)),
                            difference_from_neutral=distribution(np.linalg.norm(out.xyz-neutral.xyz,axis=1)),
                            lock_count=meta['locked_vertex_count'], regional=meta.get('regional_controls'),
                            symmetry_nearest_diagnostic=distribution(nearest),
                            symmetry_caveat='Nearest-distance diagnostic only, not constructive correspondence proof.',
                            metadata=meta))
        m = out
    write_new(ROOT/'analysis/task31_exact_diagnosis.json', dict(definition=definition, generations=records,
        confirmed=['Current G1..G5 exactly replay saved coordinates/topology.',
                   'No separate zero-weight smoothing prefix: all G1..G5 use REFERENCE_COUPLED weighted position formulas.',
                   'wf/we/wp physical normal terms multiply current incident edge scales.',
                   'Persistent CC regional membership carries mode labels, not parent ridge/valley tangent directions.',
                   'Completed face points and original edge midpoints already feed vertex positions; this is not a new correction.'],
        hypotheses=['Neutral interpolation contributes attenuation of earlier folds; requires matched causal ablation.',
                    'Scale decay limits spatial depth; measured normal terms do not isolate total coupled displacement.',
                    'Uniform regional mode vocabulary limits cross-cell directional continuity; visual causation needs separate trial.']))
    for r in records:
        print('G',r['generation'],'edge median',r['input_edge']['median'],'wf term',r['offsets']['wf']['physical_normal_term']['median'],'symmetry',r['symmetry_nearest_diagnostic']['max'],flush=True)


if __name__ == '__main__':
    diagnose()
