"""One physical-size audit of saved integral comb roofs; no new geometry."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import time

import numpy as np


HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/comb_scale_refinement_20261014/trial01')
SOURCE_ROOT = Path('E:/CHESHIRE_DATA/experiments/comb_relief_20261014/trial01')
ORIGINAL = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07')
SOURCE_CONTROL = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/REVISED/control_quad.npz')
SOURCE_CONTROL_SHA = '0915ac8f56509768c6329a7d848793c6936b903d4d9316e01b1076a76aba8e27'
RIDGE_STATE_SHA = '8ee43315100ec89ff9048515ee636863442f2dceb5c12202e2e4954da10bc2d6'
HEIGHT = 9.735842284057451
CUTOFF = HEIGHT*.0012
ROIS = {'upper_central_plate': [300, 25, 530, 250],
        'preferred_fine_lower_right_strip': [475, 700, 740, 899]}
QUANTILES = [0., .01, .1, .5, .9, .99, 1.]
METRIC_KEYS = ('max_edge', 'projected_footprint_area', 'sqrt_projected_footprint_area',
               'source_fourfan_area', 'actual_ridge_span', 'actual_max_wing_span', 'roof_height')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def ah(array):
    return hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast('B')).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def summary(values, subset=None):
    return {key: dict(samples=len(values[key] if subset is None else values[key][subset]),
                      quantiles=QUANTILES,
                      values=np.quantile(values[key] if subset is None else values[key][subset], QUANTILES).tolist())
            for key in METRIC_KEYS}


def measure(root):
    started = time.perf_counter()
    if any((root/name).exists() for name in ('MEASUREMENT.json', 'COARSE_QUADS.npz', 'SIZE_METRICS.npz')):
        raise FileExistsError('One saved size-audit checkpoint is immutable.')
    candidate_path = SOURCE_ROOT/'RECEIPT.json'
    candidate = read(candidate_path)
    variant = candidate['variants']['RELIEF']
    ridge_path = Path(variant['ridge_state'])
    if candidate['source_control_sha256'] != SOURCE_CONTROL_SHA or sha(SOURCE_CONTROL) != SOURCE_CONTROL_SHA:
        raise ValueError('Actual source control changed.')
    if variant['ridge_state_sha256'] != RIDGE_STATE_SHA or sha(ridge_path) != RIDGE_STATE_SHA:
        raise ValueError('Actual saved comb-roof state changed.')
    snapshot = root/'source_snapshot'/HERE.name/'measure.py'
    if snapshot.exists():
        raise FileExistsError('Measurement source snapshot already exists.')
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__).resolve(), snapshot)
    code_sha = sha(snapshot)
    with np.load(SOURCE_CONTROL, allow_pickle=False) as data:
        xyz, faces = data['xyz'], data['faces']
    with np.load(ridge_path, allow_pickle=False) as data:
        roof_ids, ridge0, ridge1 = data['quad_ids'], data['ridge0'], data['ridge1']
        height, weight = data['height'], data['weight']
    if len(roof_ids) != 3130576 or len(faces) != 7002112 or len(xyz) != 7002114:
        raise ValueError('Actual saved roof/source dimensions differ.')
    values = {key: np.empty(len(roof_ids), np.float64) for key in METRIC_KEYS}
    values['roof_height'][:] = height
    for start in range(0, len(roof_ids), 65536):
        end = min(start+65536, len(roof_ids))
        q = xyz[faces[roof_ids[start:end]]]
        c = q.mean(axis=1)
        edge = np.roll(q, -1, axis=1)-q
        cross = np.cross(edge, c[:, None, :]-q)
        normal = cross.sum(axis=1)
        normal /= np.linalg.norm(normal, axis=1)[:, None]
        source_area = .5*np.linalg.norm(cross, axis=2).sum(axis=1)
        projected_area = .5*np.einsum('nki,ni->nk', cross, normal).sum(axis=1)
        r0, r1 = ridge0[start:end], ridge1[start:end]
        ridge_vector = r1-r0
        ridge_length = np.linalg.norm(ridge_vector, axis=1)
        # Actual physical distance of every original corner from the saved ridge
        # line: maximum is the wider actual roof wing span, without an axis gate.
        wing = np.linalg.norm(np.cross(ridge_vector[:, None, :], q-r0[:, None, :]), axis=2)/ridge_length[:, None]
        values['max_edge'][start:end] = np.linalg.norm(edge, axis=2).max(axis=1)
        values['projected_footprint_area'][start:end] = projected_area
        values['sqrt_projected_footprint_area'][start:end] = np.sqrt(projected_area)
        values['source_fourfan_area'][start:end] = source_area
        values['actual_ridge_span'][start:end] = ridge_length
        values['actual_max_wing_span'][start:end] = wing.max(axis=1)
    if any(not np.isfinite(value).all() for value in values.values()):
        raise ValueError('Nonfinite physical size metric.')
    if (values['projected_footprint_area'] <= 0).any() or (values['actual_ridge_span'] <= 0).any():
        raise ValueError('Saved roof has invalid positive physical footprint/ridge span.')
    evidence_path = ORIGINAL/'evidence.npz'
    info = read(ORIGINAL/'generation.json')
    evidence_sha = sha(evidence_path)
    if evidence_sha != info['evidence_file_sha256']:
        raise ValueError('Original actual face-pair evidence changed.')
    with np.load(evidence_path, allow_pickle=False) as data:
        px, py = data['mirror_x_face_pairs'], data['mirror_y_face_pairs']
    ids = np.arange(len(faces))
    if not np.array_equal(px[px], ids) or not np.array_equal(py[py], ids) or not np.array_equal(px[py], py[px]):
        raise ValueError('Original source face correspondences are not commuting involutions.')
    lookup = np.full(len(faces), -1, np.int32)
    lookup[roof_ids] = np.arange(len(roof_ids))
    orbit = np.minimum(np.minimum(roof_ids, px[roof_ids]), np.minimum(py[roof_ids], px[py[roof_ids]]))
    representative_index = lookup[orbit]
    if (representative_index < 0).any():
        raise ValueError('Saved roof face orbit is incomplete.')
    coarse = values['max_edge'][representative_index] > CUTOFF
    fixed = (px[roof_ids] == roof_ids) | (py[roof_ids] == roof_ids) | (px[py[roof_ids]] == roof_ids)
    coarse &= ~fixed
    coarse_ids = roof_ids[coarse]
    coarse_mask = np.zeros(len(faces), bool)
    coarse_mask[coarse_ids] = True
    if not np.array_equal(coarse_mask, coarse_mask[px]) or not np.array_equal(coarse_mask, coarse_mask[py]):
        raise ValueError('Physical-size selection is not exactly source-face symmetric.')
    render_path = SOURCE_ROOT/'RELIEF_FLAT/views/receipt.json'
    render = read(render_path)
    camera = render['actual_views']['macro']
    position, target = np.asarray(camera['position']), np.asarray(camera['target'])
    forward = target-position; forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0., 0., 1.]); right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    scale = float(camera['scale'])
    macro_faces, macro_xy, macro_depth = [], [], []
    for start in range(0, len(faces), 65536):
        stop = min(start+65536, len(faces)); local_ids = ids[start:stop]
        q = xyz[faces[start:stop]]; c = q.mean(axis=1)
        cross = np.cross(np.roll(q, -1, axis=1)-q, c[:, None, :]-q)
        normal = cross.sum(axis=1); normal /= np.linalg.norm(normal, axis=1)[:, None]
        rank = lookup[local_ids]; roof = rank >= 0
        # Use the actual six saved roof-vertex mean for selected cells; source
        # quad means for unselected cells provide approximate body occlusion.
        c[roof] = (q[roof].sum(axis=1)+ridge0[rank[roof]]+ridge1[rank[roof]])/6.
        relative = c-target
        u, v = relative@right, relative@up
        visible_candidate = (abs(u) <= scale*.5) & (abs(v) <= scale*.5) & (normal@(-forward) > .05)
        mi = np.flatnonzero(visible_candidate)
        macro_faces.append(local_ids[mi])
        macro_xy.append(np.column_stack([450+u[mi]*900/scale, 450-v[mi]*900/scale]))
        macro_depth.append((c[mi]-position)@forward)
    all_macro_faces = np.concatenate(macro_faces)
    macro_xy = np.concatenate(macro_xy); depth = np.concatenate(macro_depth)
    pixels = np.clip(macro_xy.astype(np.int32), 0, 899)
    slots = pixels[:, 1]*900+pixels[:, 0]
    min_depth = np.full(900*900, np.inf)
    np.minimum.at(min_depth, slots, depth)
    visible = (depth <= min_depth[slots]+HEIGHT*.001) & (lookup[all_macro_faces] >= 0)
    macro_roof_ids, macro_xy = all_macro_faces[visible], macro_xy[visible]
    macro_indices = lookup[macro_roof_ids]
    roi_results = {}
    for name, (x0, y0, x1, y1) in ROIS.items():
        inside = ((macro_xy[:, 0] >= x0) & (macro_xy[:, 0] <= x1) &
                  (macro_xy[:, 1] >= y0) & (macro_xy[:, 1] <= y1))
        selected = macro_indices[inside]
        if not len(selected):
            raise ValueError('No actual saved roofs in requested image ROI: '+name)
        roi_results[name] = dict(pixel_ROI=ROIS[name], actual_roof_samples=len(selected),
            coarse_roofs=int(coarse[selected].sum()), coarse_fraction=float(coarse[selected].mean()),
            size_metrics=summary(values, selected),
            max_edge_height_fraction_quantiles=(np.quantile(values['max_edge'][selected], QUANTILES)/HEIGHT).tolist(),
            representative_quad_ids=roof_ids[selected[np.linspace(0, len(selected)-1, min(12, len(selected))).astype(int)]].tolist())
    coarse_path = root/'COARSE_QUADS.npz'
    np.savez_compressed(coarse_path, coarse_quad_ids=coarse_ids)
    metrics_path = root/'SIZE_METRICS.npz'
    np.savez_compressed(metrics_path, quad_ids=roof_ids,
        **{key: value.astype(np.float32) for key, value in values.items()},
        original_roof_weight=weight.astype(np.float32))
    if sha(SOURCE_CONTROL) != SOURCE_CONTROL_SHA or sha(ridge_path) != RIDGE_STATE_SHA or sha(Path(__file__).resolve()) != code_sha or sha(snapshot) != code_sha:
        raise ValueError('Source data or executed measurement code changed.')
    result = dict(date='2026-10-14', source_native=str(variant['geometry']), source_native_geometry_sha256=variant['geometry_sha256'],
        source_candidate_receipt=str(candidate_path), source_candidate_receipt_sha256=sha(candidate_path),
        source_control=str(SOURCE_CONTROL), source_control_sha256=SOURCE_CONTROL_SHA,
        source_ridge_state=str(ridge_path), source_ridge_state_sha256=RIDGE_STATE_SHA,
        source_render_receipt=str(render_path), source_render_receipt_sha256=sha(render_path),
        original_face_pairs=dict(path=str(evidence_path), sha256=evidence_sha),
        physical_height=HEIGHT, cutoff=dict(metric='maximum actual original quad edge length',
            height_fraction=.0012, physical_length=CUTOFF, strict_comparison='>',
            aspect_gate=False, world_axis_gate=False,
            selection_scope='Existing saved roof cells only; exact actual face-orbit representative, fixed-face orbits excluded.'),
        global_roof_metrics=summary(values), global_roof_count=len(roof_ids),
        coarse_roof_count=len(coarse_ids), coarse_roof_fraction=float(coarse.mean()),
        unchanged_other_roof_count=int((~coarse).sum()), fixed_roofs_excluded=int(fixed.sum()),
        approximate_visible_macro_roof_count=len(macro_indices),
        approximate_visible_macro_coarse_count=int(coarse[macro_indices].sum()),
        image_ROIs=roi_results, macro_camera=camera,
        visibility_scope='Saved macro .30 orthobox; actual six-vertex roof means and source unselected quad means, facing>.05, per-pixel nearest-centroid-depth tolerance .001H. Approximate visibility only.',
        metric_scope='Physical source-bound footprint, source fourfan area, saved ridge span and maximum 3D corner-to-ridge-line wing span. No image-direction/aspect proxy is used to select cells.',
        one_level_refinement_scale='A regular midpoint 2x2 subdivision halves each straight boundary edge; physical projected cell areas are approximately quartered. Curved/nonplanar interiors require actual generator validation.',
        count_estimate=dict(parent_roofs_to_replace=len(coarse_ids), child_roofs_if_four_per_parent=4*len(coarse_ids),
            net_additional_roofs=3*len(coarse_ids),
            caveat='Shared edge midpoints and conformity triangles on adjacent unrefined roof disks add generator-dependent vertices/faces; this audit does not claim final mesh counts or execution time.'),
        outputs=dict(coarse_quad_ids=dict(path=str(coarse_path), sha256=sha(coarse_path), array_sha256=ah(coarse_ids)),
                     size_metrics=dict(path=str(metrics_path), sha256=sha(metrics_path), dtype='float32 metrics; cutoff selection used original float64 values')),
        source_snapshot=dict(source=str(Path(__file__).resolve()), snapshot=str(snapshot), sha256=code_sha),
        actual_XY_coarse_face_selection_exact=True, original_mask_or_roof_heights_changed=False,
        source_geometry_changed=False, candidate_geometry_generated=False, shading_changed=False,
        threshold_sweep_performed=False, seconds=time.perf_counter()-started,
        scope='One preapproved physical-size cutoff measured once. This is selection evidence for one local native refinement, not G8 or a control subdivision.')
    target_result = root/'MEASUREMENT.json'
    target_result.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(dict(saved=str(target_result), coarse_roof_count=len(coarse_ids),
                         coarse_roof_fraction=result['coarse_roof_fraction'],
                         image_ROIs={name: {key: value for key, value in item.items() if key in ('actual_roof_samples', 'coarse_roofs', 'coarse_fraction', 'max_edge_height_fraction_quantiles')} for name, item in roi_results.items()}), indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    root = parser.parse_args().root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    measure(root)


if __name__ == '__main__':
    main()
