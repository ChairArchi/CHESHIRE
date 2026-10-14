"""One read-only parent-to-final comparison of actual guarded decorations.

Uses the frozen audit's angle, edge-incidence and sample rules. Does not write
geometry or decide aesthetic success.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path('E:/CHESHIRE_DATA/experiments/parent_continuity_20261014/trial01')
OLD = Path('E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial02')
AUDIT = Path('E:/CHESHIRE_DATA/experiments/parent_continuity_20261014/audit01/MEASUREMENTS.json')
AUDIT_SHA = '60573ddbf3e8dd4e2b17ad2ad00223e5a54cf6e43e6330ee2a9846646b9e3850'
HELPER = HERE/'measure_parent.py'
HELPER_SHA = '42be48cdd62a43a0bc4ad6b626fb41759d7cb35e192ee6b65cc8779ab172ef43'
spec = importlib.util.spec_from_file_location('parent_comparison_frozen_measurements', HELPER)
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)
digest, ah, read = measure.digest, measure.ah, measure.read


def _difference(old, new):
    if old['thresholds'] != new['thresholds'] or old['count'] != new['count']:
        raise ValueError('Actual old/new measurement threshold or incidence counts differ.')
    return dict(thresholds=old['thresholds'],
        previous_counts=old['all_incidence_exceed_counts'], new_counts=new['all_incidence_exceed_counts'],
        exceed_fraction_changes_new_minus_old=(np.array(new['all_incidence_exceed_fractions'])-
            np.array(old['all_incidence_exceed_fractions'])).tolist())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    root = parser.parse_args().root.resolve()
    output = root/'CHANGE_COMPARISON.json'
    if output.exists():
        raise FileExistsError('Preserved earlier comparison.')
    started = time.perf_counter()
    if digest(HELPER) != HELPER_SHA or digest(AUDIT) != AUDIT_SHA:
        raise ValueError('Frozen measurement helper or original audit changed.')
    previous = read(AUDIT)
    receipt_path = root/'RECEIPT.json'
    receipt = read(receipt_path)
    variant = receipt['variants']['PARENT_GUARDED']
    nested = receipt['nested']
    source = Path(receipt['source_control_path'])
    final_path = Path(variant['control_quad'])
    native_path = Path(variant['geometry'])
    guard_path = Path(receipt['geometry_guard_state']['path'])
    state_path = Path(receipt['nested_state']['path'])
    sources = {str(receipt_path): digest(receipt_path), str(AUDIT): AUDIT_SHA,
        str(HELPER): HELPER_SHA, str(Path(__file__).resolve()): digest(__file__)}
    for path, expected in ((source, receipt['source_control_sha256']),
            (final_path, variant['control_quad_sha256']), (native_path, variant['geometry_sha256']),
            (guard_path, receipt['geometry_guard_state']['sha256']),
            (state_path, receipt['nested_state']['sha256'])):
        if digest(path) != expected:
            raise ValueError('Actual bound source changed: '+str(path))
        sources[str(path)] = expected
    old_receipt = read(OLD/'RECEIPT.json')
    for path in (OLD/'RECEIPT.json', OLD/'PARENT_STATE.npz'):
        expected = previous['sources'][str(path)]
        if digest(path) != expected:
            raise ValueError('Previous actual parent audit source changed.')
        sources[str(path)] = expected
    parent_path = root/'PARENT_STATE.npz'
    sources[str(parent_path)] = digest(parent_path)
    with np.load(source, allow_pickle=False) as saved:
        carrier, q = saved['xyz'], saved['faces']
    with np.load(parent_path, allow_pickle=False) as saved:
        primary_delta = saved['primary_delta']
    with np.load(OLD/'PARENT_STATE.npz', allow_pickle=False) as saved:
        if not np.array_equal(primary_delta, saved['primary_delta']):
            raise ValueError('Previous exact primary weighting differs.')
    carrier += primary_delta
    del primary_delta
    if ah(carrier) != old_receipt['nested']['input_xyz_sha256'] or ah(carrier) != nested['input_xyz_sha256']:
        raise ValueError('Candidate and previous audit do not share the exact actual parent.')
    if ah(q) != nested['input_quads_sha256']:
        raise ValueError('Actual shared control quad association differs.')
    with np.load(final_path, allow_pickle=False) as saved:
        final = saved['xyz']
        if not np.array_equal(saved['faces'], q):
            raise ValueError('Candidate control faces changed.')
    with np.load(state_path, allow_pickle=False) as saved:
        dc, ds = saved['delta_child'], saved['delta_small']
    if ah(dc) != nested['child']['delta_sha256'] or ah(ds) != nested['small']['delta_sha256']:
        raise ValueError('Candidate saved CHILD or SMALL delta changed.')
    if not np.array_equal(carrier+dc+ds, final) or ah(final) != nested['output_xyz_sha256']:
        raise ValueError('Candidate saved stage deltas do not reproduce final exactly.')
    total_delta = dc+ds
    del dc, ds
    with np.load(guard_path, allow_pickle=False) as saved:
        guard, hard_faces = saved['guard7'], saved['hard_faces7']
    if ah(guard) != receipt['geometry_guard']['output_guard7_sha256'] or ah(guard) != nested['geometric_guard_sha256']:
        raise ValueError('Actual generated and applied geometric guards differ.')
    zero = guard == 0.
    protected_error = float(np.max(np.abs(final[zero]-carrier[zero]), initial=0.))
    if protected_error != 0.:
        raise ValueError('A zero-guard actual parent control moved.')
    with np.load(native_path, allow_pickle=False) as saved:
        native = saved['xyz']
    if (len(native) != len(carrier)+len(q) or not np.array_equal(native[:len(carrier)], final)):
        raise ValueError('Actual native control prefix or fan-centre count differs.')
    face_angles = measure.Summary([5., 15., 30., 60.])
    edge_changes = measure.Summary([.1, .25, .5, 1., 2.])
    hard_corner_error = hard_centre_error = 0.
    all_zero_faces = hard_measured = 0
    print('COMPARE actual guarded parent-to-FINAL in one quad traversal', flush=True)
    for start in range(0, len(q), measure.CHUNK):
        stop = min(start+measure.CHUNK, len(q))
        quad = q[start:stop]
        p0, p1 = carrier[quad], final[quad]
        face_angles.add(measure.angle(measure.normals(p0), measure.normals(p1)))
        delta = total_delta[quad]
        length = np.linalg.norm(np.roll(p0, -1, axis=1)-p0, axis=2)
        if np.any(length <= 0.):
            raise ValueError('Zero actual parent edge length.')
        edge_changes.add(np.linalg.norm(np.roll(delta, -1, axis=1)-delta, axis=2)/length)
        all_zero_faces += int(np.count_nonzero(np.all(guard[quad] == 0., axis=1)))
        selected = hard_faces[start:stop]
        if np.any(selected):
            if np.any(guard[quad[selected]] != 0.):
                raise ValueError('Hard descendant quad has an unprotected corner.')
            hard_measured += int(selected.sum())
            hard_corner_error = max(hard_corner_error, float(np.max(np.abs(p1[selected]-p0[selected]))))
            expected_centres = p0[selected].mean(axis=1)
            actual_centres = native[len(carrier)+np.arange(start, stop)[selected]]
            hard_centre_error = max(hard_centre_error,
                float(np.max(np.abs(actual_centres-expected_centres))))
    if hard_corner_error != 0. or hard_centre_error != 0. or hard_measured != int(hard_faces.sum()):
        raise ValueError('Requested hard descendant quad/native fan was not preserved exactly.')
    angles, edges = face_angles.report(), edge_changes.report()
    old_angles = previous['face_direction_change_degrees']['CARRIER_to_FINAL']
    old_edges = previous['edge_relative_delta_change']['CARRIER_to_FINAL']
    result = dict(date='2026-10-15', sources=sources,
        actual_same_parent_carrier=True, actual_candidate_deltas_reproduce_final=True,
        original_native_face_sha256_binding=variant['faces_sha256'],
        actual_native_prefix_matches_final_controls=True,
        protected_zero_guard_controls=int(zero.sum()), protected_max_coordinate_error=protected_error,
        hard_G7_descendant_faces=hard_measured, hard_G7_corner_max_coordinate_error=hard_corner_error,
        hard_G7_actual_native_fan_centre_max_coordinate_error=hard_centre_error,
        geometric_guard_footprint=dict(total_control_vertices=len(carrier), total_control_quads=len(q),
            zero_guard_controls=int(zero.sum()), all_zero_guard_faces=all_zero_faces,
            all_zero_guard_face_fraction=all_zero_faces/len(q),
            partial_guard_controls=int(np.count_nonzero((guard > 0.) & (guard < 1.))),
            full_guard_controls=int(np.count_nonzero(guard == 1.))),
        previous_parent_to_final_face_degrees=old_angles,
        guarded_parent_to_final_face_degrees=angles,
        face_exceedance_comparison=_difference(old_angles, angles),
        previous_parent_to_final_edge_relative_delta=old_edges,
        guarded_parent_to_final_edge_relative_delta=edges,
        edge_exceedance_comparison=_difference(old_edges, edges),
        measurement_rule=previous['counting'],
        scope='One actual parent-to-final traversal, same thresholds/stride/chunks as audit01. Exact selected source preservation and local geometric change only; no aesthetic success, semantic ridge recognition, inherited-defect repair or collision certificate. Geometry is never written or modified.',
        elapsed_seconds=time.perf_counter()-started)
    for path, expected in sources.items():
        if digest(path) != expected:
            raise ValueError('Immutable source changed during comparison: '+path)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print('CHANGE_COMPARISON_SAVED', str(output), result['elapsed_seconds'], flush=True)


if __name__ == '__main__':
    main()
