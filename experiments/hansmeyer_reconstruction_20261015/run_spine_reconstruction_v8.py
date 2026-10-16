"""ONE bold absolute sculpted chain, reusing all four certified source domains."""
from pathlib import Path
import argparse
import gc
import json
import shutil
import time
import numpy as np
import run_spine_reconstruction_v7 as core
import recursive_spine_operator_v3 as sculpt


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--foundation', type=Path, required=True)
    args = p.parse_args()
    root = args.root.resolve(); foundation = args.foundation.resolve()
    if root.exists(): raise FileExistsError('Select a fresh immutable output root.')
    started = time.perf_counter()
    old_receipt_path = foundation/'RECEIPT.json'
    old_receipt = json.loads(old_receipt_path.read_text(encoding='utf8'))
    old_preflight_path = foundation/'PREFLIGHT.json'
    old_preflight = json.loads(old_preflight_path.read_text(encoding='utf8'))
    if not old_preflight['passed'] or {i['component'] for i in old_preflight['selected']} != {2, 12, 25, 40}:
        raise ValueError('The four existing certified source domains are required.')
    sources = {str(old_receipt_path):core.sha(old_receipt_path), str(old_preflight_path):core.sha(old_preflight_path)}
    root.mkdir(parents=True)
    paths = [Path(__file__).resolve(), Path(sculpt.__file__).resolve()]
    for record in old_receipt['source_snapshots'].values():
        source, snapshot = Path(record['source']), Path(record['snapshot'])
        if core.sha(source) != record['sha256'] or core.sha(snapshot) != record['sha256']:
            raise ValueError('Frozen source-domain dependency changed: '+str(source))
        paths.append(source)
    snapshots = {}
    for path in dict.fromkeys(paths):
        target = root/'source_snapshot_run'/path.relative_to(core.REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        snapshots[path.relative_to(core.REPO).as_posix()] = dict(source=str(path), snapshot=str(target), sha256=core.sha(path))
    accepted_receipt_path = core.ACCEPTED/'RECEIPT.json'
    if core.sha(accepted_receipt_path) != core.helper.BASE_RECEIPT_SHA:
        raise ValueError('Accepted cloth receipt changed.')
    accepted_receipt = json.loads(accepted_receipt_path.read_text(encoding='utf8'))
    baseline = accepted_receipt['variants']['NESTED']
    source_control = Path(baseline['control_quad'])
    if core.sha(source_control) != baseline['control_quad_sha256']:
        raise ValueError('Accepted cloth controls changed.')
    sources[str(accepted_receipt_path)] = core.sha(accepted_receipt_path)
    sources[str(source_control)] = baseline['control_quad_sha256']
    prepared = []; foundations = []
    for old_info in old_preflight['selected']:
        state = core.load_tree(old_info['evidence']['description'], sources)
        old = state['formation']
        strip = sculpt.reconstruct_strip(old, state['foundation'])
        print('SCULPT_ABSOLUTE_PARENT', old_info['component'], flush=True)
        _, q, chart, meta, formed = sculpt.form(strip, periodic=old_info['periodic'],
            cell_count=old_info['node_count'], phase_origin=old_info['phase_origin'], total_length=old_info['total_length'])
        if not np.array_equal(q, old['quads_refined']) or not np.array_equal(chart, old['source_chart_refined']):
            raise ValueError('Certified source birth correspondence changed.')
        formed['source_uv_refined'] = old['source_uv_refined']
        formed['source_chart_transfer'] = old['source_chart_transfer']
        atlas = core.BucketAtlas(formed['source_chart_transfer'], q, formed['formed_refined'], formed['logical_refined'], verify_global=False)
        atlas.metadata['source_domain_proof'] = old_info['atlas']['global_injectivity']
        info = {key:value for key, value in old_info.items() if key not in ('formation', 'local_section_gate', 'evidence', 'atlas')}
        info.update(formation=meta, atlas=atlas.metadata, transfer_mode='ABSOLUTE_FORMED_TARGET_WITH_C2_SOURCE_BOUNDARY',
            source_domain_reused_exact=True, predecessor_evidence=old_info['evidence'],
            transfer_endpoint_pitch=(1.5*formed['requested_base_width'][[0, -1]]).tolist())
        info['evidence'] = core.receipt_helper.save_tree(root, f'PARENT_{len(prepared):02}', dict(foundation=state['foundation'], formation=formed))
        foundations.append(info); prepared.append((atlas, info))
    core.write(root/'PREFLIGHT.json', dict(passed=True, kind='FOUR_EXISTING_SOURCE_DOMAINS_REUSED', selected=foundations,
        rejected=[], new_measurements=0, new_domain_solves=0,
        meaning='All four source atlases were already certified. This records correspondence reuse, not a visual-success gate.'))
    print('TRANSFER_ABSOLUTE_SCULPTED_SURFACES_TO_G7', flush=True)
    with np.load(source_control, allow_pickle=False) as z:
        control = {key:z[key] for key in z.files}
    carrier, q7, chart7 = control['xyz'], control['faces'], control['chart']
    with np.load(core.STATES/'G03_SIDEWALL/control_quad.npz', allow_pickle=False) as z:
        q3, chart3 = z['faces'], z['chart']
    with np.load(core.STATES/'G03_SIDEWALL/evidence.npz', allow_pickle=False) as z:
        owners3 = z['face_event_ids']
    ancestor = q7
    for _ in range(4): ancestor = ancestor.reshape(-1, 4, 4)[:, :, 1]
    if not np.array_equal(ancestor, q3): raise ValueError('Exact source-domain ancestry changed.')
    cap3 = np.all(chart3[q3, 0] == 0., axis=1)|np.all(chart3[q3, 0] == 1., axis=1)
    body7 = np.repeat((owners3 == 0)&~cap3, 256)
    pair_path = core.STATES/'G07_SURFACE/evidence.npz'
    pair_generation = json.loads((pair_path.parent/'generation.json').read_text(encoding='utf8'))
    if core.sha(pair_path) != pair_generation['evidence_file_sha256']:
        raise ValueError('Inherited mirror source IDs changed.')
    sources[str(pair_path)] = pair_generation['evidence_file_sha256']
    with np.load(pair_path, allow_pickle=False) as z:
        px, py = z['mirror_x_vertex_pairs'], z['mirror_y_vertex_pairs']
    degree = np.bincount(q7.ravel(), minlength=len(carrier))
    body_degree = np.bincount(q7[body7].ravel(), minlength=len(carrier))
    eligible = body_degree == degree
    ids = np.arange(len(carrier)); representative = np.minimum.reduce((ids, px, py, px[py]))
    free = np.flatnonzero(eligible&(ids == representative))
    raw = np.zeros_like(carrier); support = np.zeros(len(carrier))
    ownership = np.full(len(carrier), -1, np.int8)
    for parent_index, (atlas, info) in enumerate(prepared):
        for sx, sy in ((1., 1.), (-1., 1.), (1., -1.), (-1., -1.)):
            for start in range(0, len(free), 65536):
                take = free[start:start+65536]
                query = chart7[take].copy(); query[:, 1] *= sx; query[:, 2] *= sy
                target, logical, valid = atlas.evaluate(query)
                taper = sculpt.quintic((1.-np.abs(logical[:, 2]))/.35)*valid
                if not info['periodic']:
                    arc = logical[:, 0]*info['total_length']
                    pitch = info['transfer_endpoint_pitch']
                    taper *= sculpt.quintic(arc/(1.5*pitch[0]))*sculpt.quintic((info['total_length']-arc)/(1.5*pitch[1]))
                conflict = (taper > 1e-6)&(support[take] > 1e-6)&(ownership[take] != parent_index)
                if np.any(conflict): raise ValueError('Distinct certified sculpt footprints overlap; no forced seam.')
                active = taper > support[take]
                target[:, 0] *= sx; target[:, 1] *= sy
                raw[take[active]] = (target[active]-carrier[take[active]])*taper[active, None]
                support[take[active]] = taper[active]
                ownership[take[active]] = parent_index
    delta = core.helper.reflect_delta(raw, px, py); delta[~eligible] = 0.
    output = carrier+delta
    if not np.isfinite(output).all(): raise ValueError('Nonfinite absolute sculpt result.')
    outside = support[representative] == 0.
    if np.any(output[outside] != carrier[outside]): raise ValueError('Exact outside-source geometry changed.')
    norm = np.linalg.norm(delta, axis=1); moved = np.flatnonzero(norm > 1e-12)
    if not len(moved): raise ValueError('Empty absolute sculpt output.')
    symmetry = 0.
    for axis, pair in enumerate((px, py)):
        for start in range(0, len(output), 65536):
            sl = slice(start, min(start+65536, len(output)))
            reflected = output[pair[sl]].copy(); reflected[:, axis] *= -1
            symmetry = max(symmetry, float(np.abs(output[sl]-reflected).max()))
    if symmetry > 2e-12: raise ValueError('Inherited reflection integrity changed.')
    validation = dict(generation=7, original_topology_unchanged=True, added_original_CC_passes=0,
        local_scaffold_CC_passes=2, moved_controls=len(moved), output_XY_symmetry_error=symmetry,
        displacement_quantiles=np.quantile(norm[moved], [0., .1, .5, .9, .99, 1.]).tolist(),
        exact_untouched_controls=int(outside.sum()),
        maximum_bounds_change=(np.ptp(output, axis=0)-np.ptp(carrier, axis=0)).tolist(),
        absolute_design='The compact interior owns actual formed rib/coffer geometry. No neutral differential or inherited carrier residual is added inside its full-support region.',
        boundary='C2 blend to exact accepted source at outer cross-margin and actual path ends.',
        self_intersection_checked=False, visual_success='Pending actual matched full-native views; no numerical beauty claim.')
    np.savez_compressed(root/'SPARSE_DELTA.npz', ids=moved, delta=delta[moved], carrier_xyz_sha256=np.array(core.ah(carrier)))
    del raw, delta, norm, body7, degree, body_degree, representative, ids, support
    gc.collect()
    print('EXPORT_BOLD_ABSOLUTE_NATIVE', flush=True)
    record = core.helper.save(root, 'SPINE', output, q7, validation)
    control['xyz'] = output
    cp = root/'SPINE/control_quad.npz'; np.savez_compressed(cp, **control)
    record.update(control_quad=str(cp), control_quad_sha256=core.sha(cp))
    for item in snapshots.values():
        if core.sha(item['source']) != item['sha256'] or core.sha(item['snapshot']) != item['sha256']:
            raise ValueError('Executed sculpt source changed.')
    for path, digest in sources.items():
        if core.sha(path) != digest: raise ValueError('Immutable sculpt input changed.')
    core.write(root/'RECEIPT.json', dict(kind='BOLD_ABSOLUTE_SCULPTED_COFFER_CHAIN', date='2026-10-15',
        comparison_source_native_path=str(core.ACCEPTED/'NESTED/geometry.npz'),
        comparison_source_native_geometry_sha256=core.helper.BASE_NATIVE_SHA,
        source_snapshots=snapshots, sources=sources, variants=dict(SPINE=record, REFERENCE_NESTED=baseline),
        foundation=foundations, validation=validation, elapsed_seconds=time.perf_counter()-started,
        scope='One bold absolute sculpted rib/coffer design on four existing registered parent-flow domains. All source stations/UV reused; no new measurement, domain solve, decorative variant or baseline recreation. Cloth outside the compact source boundary is exact.'))
    print('BOLD_ABSOLUTE_SCULPT_COMPLETE', time.perf_counter()-started, flush=True)


if __name__ == '__main__': main()
