"""Measure saved G7 native fan facets and select one symmetric fine-facet mask.

No coordinates, native centres, topology, normals or source files are changed.
This script records one deterministic mask, not a parameter search.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import time

import numpy as np


HERE = Path(__file__).resolve().parent
SOURCE_ROOT = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01')
SOURCE = SOURCE_ROOT/'REVISED/control_quad.npz'
SOURCE_SHA = '0915ac8f56509768c6329a7d848793c6936b903d4d9316e01b1076a76aba8e27'
ORIGINAL = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07')
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/diagonal_facet_finish_20261014/trial01')
HEIGHT = 9.735842284057451
RECIPE = {
    'schema': 'CHESHIRE_EXISTING_FINE_DIAGONAL_FACET_MASK_V1',
    'normalized_height_support': [.08, .94], 'height_feather': .03,
    'maximum_quad_edge_height_fraction': .003,
    'minimum_quad_edge_height_fraction': .00002,
    'minimum_native_fan_altitude_height_fraction': .00001,
    'native_fan_projection_safety': 'All four native triangle signed areas projected onto the summed source-quad normal must be strictly positive.',
    'aspect_gain_interval': [1.5, 3.0],
    'diagonal_long_axis_abs_Z_interval': [.15, .95],
    'diagonal_lower_feather': .15, 'diagonal_upper_feather': .10,
    'fan_pair_normal_spread_gain_degrees': [1., 8.],
    'flat_weight_threshold': .35,
    'equation': 'quad_weight=height_support*binary_geometric_safety*aspect_gain*diagonal_gain*existing_warpage_gain; flat_quads=geometric_safety and quad_weight>=.35',
    'interpolation': 'C2 quintic smoothstep for all nonbinary gains',
    'symmetry': 'Minimum-ID source X/Y face-orbit representative copied to all actual paired faces.',
    'intent': 'Prefer existing small anisotropic diagonal nonplanar cells; exclude large coarse plates and nearly degenerate native fan triangles. No new noise or geometric pattern is generated.',
}
QUANTILES = [0., .01, .1, .5, .9, .99, 1.]
METRIC_KEYS = ('max_edge_H', 'min_edge_H', 'edge_max_min_ratio',
               'opposite_edge_aspect', 'min_fan_altitude_H',
               'min_fan_projected_signed_area_H2',
               'fan_pair_normal_spread_degrees', 'long_axis_abs_Z',
               'material_t_vector_norm_H', 'material_theta_vector_norm_H',
               'material_t_theta_abs_cosine')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def ah(array):
    return hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast('B')).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def smoothstep(value):
    x = np.clip(value, 0., 1.)
    return x*x*x*(10. + x*(-15. + 6.*x))


def summarize(values):
    result = {}
    for name in METRIC_KEYS:
        a = np.asarray(values[name], np.float64)
        finite = a[np.isfinite(a)]
        result[name] = dict(finite_samples=len(finite), quantiles=QUANTILES,
                           values=np.quantile(finite, QUANTILES).tolist() if len(finite) else None)
    return result


def material_vectors(quad_xyz, quad_chart):
    """Local least-squares dXYZ/dt and dXYZ/dtheta; rank failure is explicit."""
    t = quad_chart[:, :, 0]
    angle = np.arctan2(quad_chart[:, :, 2], quad_chart[:, :, 1])
    da = np.arctan2(np.sin(angle-angle[:, :1]), np.cos(angle-angle[:, :1]))
    dt = t-t.mean(axis=1)[:, None]
    da -= da.mean(axis=1)[:, None]
    dx = quad_xyz-quad_xyz.mean(axis=1)[:, None, :]
    stt, saa, sta = (dt*dt).sum(1), (da*da).sum(1), (dt*da).sum(1)
    determinant = stt*saa-sta*sta
    valid = determinant > 1e-10*np.maximum(stt*saa, 1e-40)
    vt, va = np.full((len(t), 3), np.nan), np.full((len(t), 3), np.nan)
    bt, ba = np.einsum('ij,ijk->ik', dt, dx), np.einsum('ij,ijk->ik', da, dx)
    vt[valid] = ((saa[:, None]*bt-sta[:, None]*ba)[valid]/determinant[valid, None])
    va[valid] = ((stt[:, None]*ba-sta[:, None]*bt)[valid]/determinant[valid, None])
    return vt, va, valid


def chunk_metrics(q, chart):
    centres = q.mean(axis=1)
    edge = np.roll(q, -1, axis=1)-q
    length = np.linalg.norm(edge, axis=2)
    cross = np.cross(edge, centres[:, None, :]-q)
    double_area = np.linalg.norm(cross, axis=2)
    altitude = np.divide(double_area, length, out=np.zeros_like(length), where=length > 0)
    normal = np.divide(cross, double_area[:, :, None], out=np.zeros_like(cross), where=double_area[:, :, None] > 0)
    normal_dot = np.einsum('nik,njk->nij', normal, normal)
    spread = np.rad2deg(np.arccos(np.clip(normal_dot.min(axis=(1, 2)), -1., 1.)))
    pair_a, pair_b = (length[:, 0]+length[:, 2])*.5, (length[:, 1]+length[:, 3])*.5
    pair_short, pair_long = np.minimum(pair_a, pair_b), np.maximum(pair_a, pair_b)
    axis_a = (edge[:, 0]-edge[:, 2])*.5
    axis_b = (edge[:, 1]-edge[:, 3])*.5
    long_axis = np.where((pair_a >= pair_b)[:, None], axis_a, axis_b)
    axis_length = np.linalg.norm(long_axis, axis=1)
    direction_z = np.divide(abs(long_axis[:, 2]), axis_length, out=np.zeros(len(q)), where=axis_length > 0)
    vt, va, material_valid = material_vectors(q, chart)
    tn, an = np.linalg.norm(vt, axis=1), np.linalg.norm(va, axis=1)
    cosine = np.divide(abs(np.einsum('ij,ij->i', vt, va)), tn*an,
                       out=np.full(len(q), np.nan), where=(tn*an) > 0)
    metrics = dict(max_edge_H=length.max(1)/HEIGHT, min_edge_H=length.min(1)/HEIGHT,
        edge_max_min_ratio=np.divide(length.max(1), length.min(1), out=np.full(len(q), np.inf), where=length.min(1) > 0),
        opposite_edge_aspect=np.divide(pair_long, pair_short, out=np.full(len(q), np.inf), where=pair_short > 0),
        min_fan_altitude_H=altitude.min(1)/HEIGHT, fan_pair_normal_spread_degrees=spread,
        long_axis_abs_Z=direction_z, material_t_vector_norm_H=tn/HEIGHT,
        material_theta_vector_norm_H=an/HEIGHT, material_t_theta_abs_cosine=cosine)
    aggregate = cross.sum(axis=1)
    normal_size = np.linalg.norm(aggregate, axis=1)
    quad_normal = np.divide(aggregate, normal_size[:, None], out=np.zeros_like(aggregate), where=normal_size[:, None] > 0)
    projected_area = .5*np.einsum('nik,nk->ni', cross, quad_normal)
    metrics['min_fan_projected_signed_area_H2'] = projected_area.min(axis=1)/(HEIGHT*HEIGHT)
    safe = (np.isfinite(q).all(axis=(1, 2)) & (length.min(1) >= HEIGHT*RECIPE['minimum_quad_edge_height_fraction']) &
            (length.max(1) <= HEIGHT*RECIPE['maximum_quad_edge_height_fraction']) &
            (altitude.min(1) >= HEIGHT*RECIPE['minimum_native_fan_altitude_height_fraction']) &
            (double_area.min(1) > 0) & (projected_area.min(1) > 0) &
            (axis_length > 1e-15) & (normal_size > 1e-15))
    return metrics, safe, centres, quad_normal, vt, va, material_valid


def face_pairs():
    info = read(ORIGINAL/'generation.json')
    path = ORIGINAL/'evidence.npz'
    observed = sha(path)
    if observed != info['evidence_file_sha256']:
        raise ValueError('Original source face-pair evidence changed.')
    with np.load(path, allow_pickle=False) as data:
        px, py = data['mirror_x_face_pairs'], data['mirror_y_face_pairs']
    return px, py, dict(path=str(path), sha256=observed,
                       original_generation_receipt=str(ORIGINAL/'generation.json'),
                       original_generation_receipt_sha256=sha(ORIGINAL/'generation.json'))


def measure(root):
    started = time.perf_counter()
    if (root/'MEASUREMENT.json').exists() or (root/'MASK.npz').exists():
        raise FileExistsError('Measurement checkpoint is immutable; use a new root.')
    receipt = read(SOURCE_ROOT/'RECEIPT.json')
    variant = receipt['variants']['REVISED']
    if variant['control_sha256'] != SOURCE_SHA or sha(SOURCE) != SOURCE_SHA:
        raise ValueError('Actual revised visual-study source changed.')
    render_path = SOURCE_ROOT/'REVISED_FLAT/views/receipt.json'
    render = read(render_path)
    camera = render['actual_views']['macro']
    position, target = np.asarray(camera['position']), np.asarray(camera['target'])
    forward = target-position; forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0., 0., 1.]); right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    scale = float(camera['scale'])
    snapshot = root/'source_snapshot'/HERE.name/'measure_v2.py'
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if snapshot.exists():
        raise FileExistsError('Executed measurement source snapshot already exists.')
    shutil.copyfile(Path(__file__).resolve(), snapshot)
    code_sha = sha(snapshot)
    with np.load(SOURCE, allow_pickle=False) as data:
        xyz, faces, chart = data['xyz'], data['faces'], data['chart']
    if faces.shape != (7002112, 4) or xyz.shape != (7002114, 3) or chart.shape != xyz.shape:
        raise ValueError('Actual same-topology G7 control state required.')
    zmin, zmax = float(xyz[:, 2].min()), float(xyz[:, 2].max())
    actual_height = zmax-zmin
    if not np.isfinite(actual_height) or actual_height <= 0:
        raise ValueError('Actual final source height is not positive and finite.')
    weights = np.zeros(len(faces), np.float64)
    safe_all = np.zeros(len(faces), bool)
    global_samples = {key: [] for key in METRIC_KEYS}
    macro_samples = {key: [] for key in METRIC_KEYS}
    macro_ids, macro_depth, macro_pixels = [], [], []
    representative_vectors = []
    material_valid_count = 0
    for start in range(0, len(faces), 65536):
        ids = np.arange(start, min(start+65536, len(faces)))
        q, qchart = xyz[faces[ids]], chart[faces[ids]]
        metrics, safe, centres, quad_normal, vt, va, material_valid = chunk_metrics(q, qchart)
        normalized_z = (centres[:, 2]-zmin)/actual_height
        zlo, zhi = RECIPE['normalized_height_support']
        z_gain = smoothstep((normalized_z-zlo)/RECIPE['height_feather'])*smoothstep((zhi-normalized_z)/RECIPE['height_feather'])
        alo, ahi = RECIPE['aspect_gain_interval']
        aspect_gain = smoothstep((metrics['opposite_edge_aspect']-alo)/(ahi-alo))
        dlo, dhi = RECIPE['diagonal_long_axis_abs_Z_interval']
        diagonal_gain = smoothstep((metrics['long_axis_abs_Z']-dlo)/RECIPE['diagonal_lower_feather'])*smoothstep((dhi-metrics['long_axis_abs_Z'])/RECIPE['diagonal_upper_feather'])
        wlo, whi = RECIPE['fan_pair_normal_spread_gain_degrees']
        warpage_gain = smoothstep((metrics['fan_pair_normal_spread_degrees']-wlo)/(whi-wlo))
        weights[ids] = z_gain*safe*aspect_gain*diagonal_gain*warpage_gain
        safe_all[ids] = safe
        sample = (ids % 32) == 0
        for key in METRIC_KEYS:
            global_samples[key].append(metrics[key][sample])
        material_valid_count += int(material_valid.sum())
        relative = centres-target
        u, v = relative@right, relative@up
        facing = quad_normal@(-forward)
        macro = (abs(u) <= scale*.5) & (abs(v) <= scale*.5) & (facing > .05)
        mid = np.flatnonzero(macro)
        macro_ids.append(ids[mid]); macro_depth.append((centres[mid]-position)@forward)
        macro_pixels.append(np.clip(np.column_stack([450+u[mid]*900/scale, 450-v[mid]*900/scale]).astype(np.int32), 0, 899))
        for key in METRIC_KEYS:
            macro_samples[key].append(metrics[key][mid])
        if len(representative_vectors) < 12:
            candidates = mid[material_valid[mid] & (weights[ids[mid]] > 0)]
            for index in candidates[:12-len(representative_vectors)]:
                representative_vectors.append(dict(face_id=int(ids[index]), source_control_ids=faces[ids[index]].tolist(),
                    dXYZ_dt=vt[index].tolist(), dXYZ_dtheta=va[index].tolist(),
                    quad_normal=quad_normal[index].tolist(), quad_weight_before_symmetry=float(weights[ids[index]])))
    px, py, pair_binding = face_pairs()
    if px.shape != weights.shape or py.shape != weights.shape:
        raise ValueError('Actual original face-pair dimensions differ.')
    ids = np.arange(len(faces))
    if not np.array_equal(px[px], ids) or not np.array_equal(py[py], ids) or not np.array_equal(px[py], py[px]):
        raise ValueError('Source face correspondences are not commuting involutions.')
    representative = np.minimum(np.minimum(ids, px), np.minimum(py, px[py]))
    max_pre_transport_difference = float(np.maximum(abs(weights-weights[px]), abs(weights-weights[py])).max())
    weights = weights[representative]
    safe_all = safe_all[representative]
    flat = safe_all & (weights >= RECIPE['flat_weight_threshold'])
    if not np.isfinite(weights).all() or weights.min() < 0 or weights.max() > 1:
        raise ValueError('Invalid measured fine-facet weights.')
    if not np.array_equal(weights, weights[px]) or not np.array_equal(weights, weights[py]) or not np.array_equal(flat, flat[px]) or not np.array_equal(flat, flat[py]):
        raise ValueError('Measured facet masks are not exactly source-ID symmetric.')
    all_macro_ids, depths = np.concatenate(macro_ids), np.concatenate(macro_depth)
    pixels = np.concatenate(macro_pixels)
    depth_image = np.full(900*900, np.inf)
    slots = pixels[:, 1]*900+pixels[:, 0]
    np.minimum.at(depth_image, slots, depths)
    approximate_visible = depths <= depth_image[slots] + HEIGHT*.001
    visible_macro_ids = all_macro_ids[approximate_visible]
    global_samples = {key: np.concatenate(value) for key, value in global_samples.items()}
    macro_samples = {key: np.concatenate(value)[approximate_visible] for key, value in macro_samples.items()}
    mask_path = root/'MASK.npz'
    np.savez_compressed(mask_path, quad_weight=weights, flat_quads=flat)
    if sha(SOURCE) != SOURCE_SHA or sha(Path(__file__).resolve()) != code_sha or sha(snapshot) != code_sha:
        raise ValueError('Actual source or executed measurement code changed.')
    result = dict(date='2026-10-14', recipe=RECIPE, physical_height=HEIGHT,
        source_control=str(SOURCE), source_control_sha256=SOURCE_SHA,
        source_candidate_receipt=str(SOURCE_ROOT/'RECEIPT.json'), source_candidate_receipt_sha256=sha(SOURCE_ROOT/'RECEIPT.json'),
        source_native=str(variant['geometry']), source_native_geometry_sha256=variant['geometry_sha256'],
        source_native_faces_sha256=variant['faces_sha256'],
        original_face_pairs=pair_binding,
        source_flat_render_receipt=str(render_path), source_flat_render_receipt_sha256=sha(render_path),
        source_macro_camera=camera, source_actual_z_bounds=[zmin, zmax],
        actual_source_z_span=actual_height,
        height_scope='Inherited H scales physical size thresholds; normalized body-height support uses actual final source zmin/zspan. The final CC finish makes the two spans differ slightly.',
        previous_attempt='The first source snapshot measure.py is preserved. That attempt stopped on an overly strict inherited-H/final-height equality guard before computing a mask. Threshold values were not changed.',
        control_vertices=len(xyz), control_quads=len(faces),
        native_fan_definition='Four cyclic control-edge-to-arithmetic-quad-centre triangles per source quad, established by the actual revised native receipt; the full native mesh was not reloaded by this measurement.',
        global_metrics=summarize(global_samples),
        global_quantile_scope='Deterministic every-32nd actual quad; representative quantiles, not exact full-population quantiles.',
        global_metric_samples=len(global_samples['max_edge_H']),
        macro_metrics=summarize(macro_samples), macro_metric_samples=len(visible_macro_ids),
        macro_scope='Actual quad centroids in the saved user macro camera, facing>.05, with per900-square-pixel minimum-centroid-depth tolerance .001H. Approximate visibility; not exact ray-traced triangle occlusion.',
        material_rank_valid_quads=material_valid_count,
        material_vector_scope='Local least-squares inherited chart partial vectors. Rank-deficient copied Task32 charts are explicitly excluded from vector statistics, without pretending a global inverse chart exists.',
        representative_macro_material_vectors=representative_vectors,
        counts=dict(geometrically_safe_quads=int(safe_all.sum()),
            nonzero_weight_quads=int(np.count_nonzero(weights)), flat_quads=int(flat.sum()),
            nonzero_weight_fraction=float(np.count_nonzero(weights)/len(faces)), flat_fraction=float(flat.mean()),
            macro_nonzero_weight_quads=int(np.count_nonzero(weights[visible_macro_ids])),
            macro_flat_quads=int(flat[visible_macro_ids].sum()),
            maximum_weight=float(weights.max())),
        actual_XY_face_mask_symmetry_exact=True,
        max_weight_reflection_difference_before_canonical_transport=max_pre_transport_difference,
        mask=dict(path=str(mask_path), sha256=sha(mask_path), quad_weight_sha256=ah(weights), flat_quads_sha256=ah(flat)),
        source_snapshot=dict(source=str(Path(__file__).resolve()), snapshot=str(snapshot), sha256=code_sha),
        source_geometry_changed=False, renderer_changed=False, candidate_geometry_generated=False,
        scope='One fixed measurement and fine-facet mask on REVISED as a visual-study input. This does not adopt the whole end revision as a new design baseline or establish aesthetic success.',
        seconds=time.perf_counter()-started)
    (root/'MEASUREMENT.json').write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(dict(saved=str(root/'MEASUREMENT.json'), counts=result['counts'], macro_samples=len(visible_macro_ids)), indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    root = parser.parse_args().root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    measure(root)


if __name__ == '__main__':
    main()
