"""Read only saved trial13 arrays; audit actual protected-interface motion.

No subdivision, field evaluation, geometry generation or rendering is run.
The small result JSON is written beside this new diagnostic in the workspace.
"""
from pathlib import Path
import hashlib
import json
import time

import numpy as np


HERE = Path(__file__).resolve().parent
TRIAL = Path('E:/CHESHIRE_DATA/experiments/fold_junction_development_20261015/trial13_causal_parent_generation')
STATES = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states')
RESULT = HERE/'diagnosis_trial13_interfaces_results.json'
TOLERANCE = 1e-12


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def summary(delta, mask):
    d = delta[mask]
    magnitude = np.linalg.norm(d, axis=1)
    return dict(controls=int(np.count_nonzero(mask)),
                moved_above_tolerance=int(np.count_nonzero(magnitude > TOLERANCE)),
                maximum_delta_norm=float(magnitude.max(initial=0.)),
                maximum_absolute_delta_XYZ=np.abs(d).max(axis=0).tolist() if len(d) else [0., 0., 0.],
                norm_quantiles=np.quantile(magnitude, [0., .5, .9, .99, 1.]).tolist() if len(d) else [])


def tree_arrays(path, keys):
    metadata = read(path)
    filename = Path(metadata['array_file'])
    if digest(filename) != metadata['array_file_sha256']:
        raise ValueError('Saved stage-evidence file changed.')
    result = {}
    with np.load(filename, allow_pickle=False) as saved:
        for key in keys:
            record = metadata['tree'][key]
            value = saved[record['npz_key']]
            actual = hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()
            if actual != record['sha256']:
                raise ValueError('Saved stage-evidence array changed: '+key)
            result[key] = value
    return result, dict(path=str(path), sha256=digest(path), array_file=str(filename),
                        array_file_sha256=metadata['array_file_sha256'])


def main():
    started = time.perf_counter()
    receipt_path = TRIAL/'RECEIPT.json'
    receipt = read(receipt_path)
    source = Path(receipt['source_control'])
    neutral = Path(receipt['neutral_control'])
    formed = Path(receipt['variants']['FORMED']['control_quad'])
    owners = STATES/'G03_SIDEWALL/evidence.npz'
    source3 = STATES/'G03_SIDEWALL/control_quad.npz'
    expected = {source: receipt['source_control_sha256'],
                neutral: receipt['neutral_control_sha256'],
                formed: receipt['variants']['FORMED']['control_quad_sha256'],
                owners: receipt['sources'][str(owners)],
                source3: receipt['sources'][str(source3)]}
    bindings = {}
    for path, required in expected.items():
        actual = digest(path)
        if actual != required:
            raise ValueError('Saved immutable array binding changed: '+str(path))
        bindings[str(path)] = dict(sha256=actual, bytes=path.stat().st_size)
    bindings[str(receipt_path)] = dict(sha256=digest(receipt_path), bytes=receipt_path.stat().st_size)
    print('READ actual G6 topology/material terminals and G3 ownership', flush=True)
    with np.load(source, allow_pickle=False) as saved:
        q6 = saved['faces']
        t6 = saved['chart'][:, 0].copy()
    with np.load(owners, allow_pickle=False) as saved:
        owner3 = saved['face_event_ids']
    with np.load(source3, allow_pickle=False) as saved:
        q3 = saved['faces']
    recovered = q6
    for _ in range(3):
        recovered = recovered.reshape(-1, 4, 4)[:, :, 1]
    if not np.array_equal(recovered, q3):
        raise ValueError('Actual G6 to G3 source ancestry differs.')
    body = np.repeat(owner3 == 0, 64)
    if len(body) != len(q6):
        raise ValueError('Actual ownership length differs.')
    nv, nf = len(t6), len(q6)
    ne = 2*nf
    degree = np.bincount(q6.ravel(), minlength=nv)
    body_degree = np.bincount(q6[body].ravel(), minlength=nv)
    owned_degree = degree-body_degree
    print('READ actual G7 child topology once', flush=True)
    with np.load(neutral, allow_pickle=False) as saved:
        q7 = saved['faces']
    layout = q7.reshape(nf, 4, 4)
    if not np.array_equal(layout[:, :, 1], q6):
        raise ValueError('Actual G7 to G6 old-corner ancestry differs.')
    following = (layout[:, :, 2]-nv).copy()
    if following.min() < 0 or following.max() >= ne:
        raise ValueError('Actual following edge IDs out of range.')
    if not np.array_equal(layout[:, :, 0]-nv, np.roll(following, 1, axis=1)):
        raise ValueError('Actual preceding edge IDs differ.')
    for first in range(0, nf, 131072):
        last = min(first+131072, nf)
        if not np.all(layout[first:last, :, 3] == (nv+ne+np.arange(first, last))[:, None]):
            raise ValueError('Actual face-centre birth IDs differ.')
    del layout, q7, recovered, q3
    edge_count = np.bincount(following.ravel(), minlength=ne)
    if not np.all(edge_count == 2):
        raise ValueError('Actual closed two-face edge incidence differs.')
    edge_body = np.bincount(following.ravel(), weights=np.repeat(body.astype(int), 4), minlength=ne)
    print('READ formed and same-input neutral G7 coordinates sequentially', flush=True)
    with np.load(neutral, allow_pickle=False) as saved:
        neutral_xyz = saved['xyz']
    with np.load(formed, allow_pickle=False) as saved:
        formed_xyz = saved['xyz']
    if formed_xyz.shape != neutral_xyz.shape or len(neutral_xyz) != nv+ne+nf:
        raise ValueError('Actual G7 output/control counts differ.')
    delta = formed_xyz-neutral_xyz
    del neutral_xyz, formed_xyz
    dv, de, df = delta[:nv], delta[nv:nv+ne], delta[nv+ne:]
    report = dict(
        schema='TRIAL13_SAVED_ACTUAL_PROTECTED_INTERFACE_DELTA_AUDIT_V1',
        trial=str(TRIAL), exact_source_bindings=bindings,
        audit_code=dict(path=str(Path(__file__).resolve()), sha256=digest(__file__)),
        compared='Actual saved FORMED G7 controls minus exact same-G6 saved neutral G07_SURFACE controls.',
        tolerance=TOLERANCE,
        counts=dict(G3_quads=len(owner3), G6_vertices=nv, G6_edges=ne, G6_quads=nf,
                    G7_vertices=len(delta), source_G6_quads=int(body.sum()), owned_G6_quads=int((~body).sum())),
        ancestry=dict(G6_to_G3_old_corners_exact=True, G7_to_G6_old_corners_exact=True,
                      following_and_preceding_edge_birth_ids_exact=True, face_centre_birth_ids_exact=True,
                      every_G6_edge_has_two_face_incidents=True),
        actual_delta={
            'all_controls': summary(delta, np.ones(len(delta), bool)),
            'old_V_callback_ineligible_owned_incident': summary(dv, owned_degree > 0),
            'old_V_SOURCE_attachment_shared_interface': summary(dv, (body_degree > 0)&(owned_degree > 0)),
            'old_V_owned_interior_only': summary(dv, body_degree == 0),
            'new_E_callback_ineligible_not_two_SOURCE_faces': summary(de, edge_body < 2),
            'new_E_SOURCE_attachment_shared_interface': summary(de, edge_body == 1),
            'new_E_owned_interior_only': summary(de, edge_body == 0),
            'new_F_callback_ineligible_owned_face': summary(df, ~body)},
        limitation='Topological SOURCE/attachment interfaces and caller field eligibility only. This does not certify preservation of every semantic macro crest/valley, volume, silhouette, continuous self-intersection or beauty.')
    # Evaluate terminal guards from existing material associations only.
    edge_t = np.empty(ne)
    face_t = np.empty(nf)
    for first in range(0, nf, 131072):
        last = min(first+131072, nf)
        values = t6[q6[first:last]]
        edge_t[following[first:last].ravel()] = ((values+np.roll(values, -1, axis=1))*.5).ravel()
        face_t[first:last] = values.mean(axis=1)
    terminal = lambda t: (np.abs(t) <= 1e-12)|(np.abs(t-1.) <= 1e-12)
    report['actual_delta']['material_t0_or_t1_terminals'] = summary(
        delta, np.concatenate([terminal(t6), terminal(edge_t), terminal(face_t)]))
    del edge_t, face_t
    print('READ compact saved field arrays; distinguish zero-request coupling halo', flush=True)
    saved, evidence_binding = tree_arrays(TRIAL/'CAUSAL_STAGE_EVIDENCE.json',
        ['edge_active_ids', 'edge_desired_field', 'vertex_active_ids', 'vertex_desired_field'])
    report['saved_field_evidence_binding'] = evidence_binding
    for name, d, count, owned_mask in (
            ('edge', de, ne, edge_body < 2), ('vertex', dv, nv, owned_degree > 0)):
        active = np.zeros(count, bool)
        active[saved[name+'_active_ids']] = np.linalg.norm(saved[name+'_desired_field'], axis=1) > TOLERANCE
        halo = (~active)&(np.linalg.norm(d, axis=1) > TOLERANCE)
        report['actual_delta'][name+'_zero_own_request_nonzero_coupled_halo'] = summary(d, halo)
        report['actual_delta'][name+'_zero_own_request_halo_on_protected_owned_incident'] = summary(d, halo&owned_mask)
    report['elapsed_seconds'] = time.perf_counter()-started
    report['no_model_generation_or_render'] = True
    report['source_files_modified'] = False
    RESULT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(dict(result=str(RESULT), elapsed_seconds=report['elapsed_seconds'],
                          actual_delta=report['actual_delta']), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
