"""Finite same-UV diagnostics for both sides of actual measured parent valleys.

These are measurements of saved geometry, not an aesthetic success score.
The parent-depth chord joins the lower and upper shoulders. It differs from
the earlier one-sided valley-to-upper chord used to inspect shoulder relief.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import sys

import numpy as np
from scipy.signal import find_peaks, peak_widths


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guidance


CASES = ('SPAN', 'COUNTER')
MODES = ('BASELINE', 'VALLEY_PRIORITY', 'FLOW_CHAIN')
BASIN_RECIPE = dict(minimum_prominence=.01, minimum_physical_width=.01,
    owned_arc_interval=[.25, .90], maximum_slices=7, matching_arc_tolerance=.08)


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _array_hash(array):
    return hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast('B')).hexdigest()


def _stats(values):
    values = np.asarray(values, float)
    if not values.size:
        return dict(count=0, minimum=None, median=None, maximum=None)
    return dict(count=int(values.size), minimum=float(values.min()),
                median=float(np.median(values)), maximum=float(values.max()))


def _basins(profile, reference_arc, recipe):
    """Read inward local relief after subtracting the declared shoulder chord.

    The reference physical-arc fractions and slice normal remain fixed between
    reference/result. Widths are measured in reference surface-arc units.
    """
    length = reference_arc[-1]
    if length <= 1e-12:
        return dict(found=False, candidates=[], reason='No positive reference shoulder arc.'), np.zeros_like(profile)
    u = reference_arc/length
    detrended = profile-(profile[0]+u*(profile[-1]-profile[0]))
    peaks, properties = find_peaks(-detrended, prominence=recipe['minimum_prominence'])
    if not len(peaks):
        return dict(found=False, candidates=[], reason='No inward local minimum above the declared prominence.'), detrended
    _, _, left, right = peak_widths(-detrended, peaks, rel_height=.5)
    ids = np.arange(len(profile))
    widths = np.interp(right, ids, reference_arc)-np.interp(left, ids, reference_arc)
    lower, upper = recipe['owned_arc_interval']
    candidates = []
    for i, peak in enumerate(peaks):
        if lower <= u[peak] <= upper and widths[i] >= recipe['minimum_physical_width']:
            candidates.append(dict(sample_index=int(peak), arc_fraction=float(u[peak]),
                reference_arc_distance=float(reference_arc[peak]),
                prominence=float(properties['prominences'][i]), physical_half_prominence_width=float(widths[i]),
                detrended_normal_height=float(detrended[peak])))
    return dict(found=bool(candidates), candidates=candidates,
        reason='Detected finite shoulder-profile minima.' if candidates else
               'Minima failed the declared ownership or physical-width threshold.'), detrended


def compare_parent(reference_xyz, result_xyz, parent, basin_recipe=None):
    """Compare matching actual-native samples; return JSON metrics and arrays.

    Projection fractions are computed once from reference lower/valley/upper
    XYZ and then fixed. Signed deficits are retained, including negative ones.
    No depth increase or basin count is converted to a visual PASS.
    """
    recipe = dict(BASIN_RECIPE if basin_recipe is None else basin_recipe)
    reference, result = np.asarray(reference_xyz, float), np.asarray(result_xyz, float)
    uv = np.asarray(parent['parent_surface_uv'])
    normal = np.asarray(parent['parent_normal'], float)
    parameter = np.asarray(parent['parameter'], float)
    if (reference.shape != result.shape or reference.shape != (*uv.shape[:2], 3) or
        normal.shape != (len(parameter), 3) or len(reference) != len(parameter) or
        not np.isfinite(reference).all() or not np.isfinite(result).all()):
        raise ValueError('Matching finite actual-native parent-surface samples are required.')
    if reference.shape[1] != 257:
        raise ValueError('Expected the saved 257 lower→valley→upper samples, with valley index 128.')
    if not np.allclose(np.linalg.norm(normal, axis=1), 1., rtol=0., atol=1e-9):
        raise ValueError('Fixed measured unit parent normals required.')
    valley = 128
    chord = reference[:, -1]-reference[:, 0]
    length_squared = np.sum(chord*chord, axis=1)
    if np.any(length_squared <= 1e-20):
        raise ValueError('Reference two-sided shoulder chord has zero length.')
    fraction = np.clip(np.sum((reference[:, valley]-reference[:, 0])*chord, axis=1)/length_squared, 0., 1.)
    ref_chord = reference[:, 0]+fraction[:, None]*chord
    out_chord = result[:, 0]+fraction[:, None]*(result[:, -1]-result[:, 0])
    ref_depth = np.sum((ref_chord-reference[:, valley])*normal, axis=1)
    out_depth = np.sum((out_chord-result[:, valley])*normal, axis=1)
    shift = result-reference
    distance = np.linalg.norm(shift, axis=2)
    normal_shift = np.einsum('nkj,nj->nk', shift, normal)
    chart = np.column_stack([uv[..., 0].ravel(), np.cos(uv[..., 1]).ravel(), np.sin(uv[..., 1]).ravel()])
    coordinates = guidance.patch_coordinates(chart, parent)
    core_weight = coordinates['core_weight'].reshape(uv.shape[:2])
    q = 2.*(parameter-parameter[0])/(parameter[-1]-parameter[0])-1.
    central = np.abs(q) <= .6+1e-12
    direct = np.asarray(parent['parent_valley_measured_mask'], bool)
    if direct.shape != parameter.shape:
        raise ValueError('Direct-measurement mask must match parent parameters.')
    candidates = np.flatnonzero(central)
    chosen = (candidates[np.unique(np.rint(np.linspace(0, len(candidates)-1,
        min(recipe['maximum_slices'], len(candidates)))).astype(int))] if len(candidates) else np.array([], int))
    ref_profile = np.einsum('nkj,nj->nk', reference, normal)
    out_profile = np.einsum('nkj,nj->nk', result, normal)
    basins, ref_detrended, out_detrended = [], [], []
    for index in chosen:
        arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(reference[index, valley:], axis=0), axis=1))]
        before, ref_relief = _basins(ref_profile[index, valley:], arc, recipe)
        after, out_relief = _basins(out_profile[index, valley:], arc, recipe)
        unmatched, strengthened = 0, 0
        for candidate in after['candidates']:
            matches = [old for old in before['candidates']
                       if abs(old['arc_fraction']-candidate['arc_fraction']) <= recipe['matching_arc_tolerance']]
            unmatched += not bool(matches)
            strengthened += bool(matches) and candidate['prominence'] >= max(old['prominence'] for old in matches)+recipe['minimum_prominence']
        basins.append(dict(parameter_index=int(index), material_parameter=float(parameter[index]),
            directly_measured_parent_valley=bool(direct[index]), reference=before, result=after,
            unmatched_result_minima=int(unmatched), strengthened_matched_minima=int(strengthened)))
        ref_detrended.append(ref_relief); out_detrended.append(out_relief)
    core = core_weight > 0.
    metrics = dict(parent_index=int(parent['parent_index']), station_count=len(parameter),
        directly_measured_valley_stations=int(direct.sum()),
        two_sided_signed_valley_deficit=dict(reference=_stats(ref_depth), result=_stats(out_depth),
            change=_stats(out_depth-ref_depth), central_change=_stats((out_depth-ref_depth)[central]),
            increased_station_count=int(np.count_nonzero(out_depth > ref_depth+1e-10))),
        valley_displacement=dict(magnitude=_stats(distance[:, valley]),
            central_magnitude=_stats(distance[central, valley]),
            directly_measured_magnitude=_stats(distance[direct, valley]),
            signed_normal_component=_stats(normal_shift[:, valley])),
        sampled_core_displacement=dict(point_count=int(core.sum()), magnitude=_stats(distance[core]),
            signed_normal_component=_stats(normal_shift[core])),
        intermediate_basin_diagnostic=dict(recipe=recipe, fixed_slice_count=len(chosen),
            reference_slices_with_minima=sum(item['reference']['found'] for item in basins),
            result_slices_with_minima=sum(item['result']['found'] for item in basins),
            result_found=any(item['result']['found'] for item in basins),
            slices_with_unmatched_result_minima=sum(item['unmatched_result_minima'] > 0 for item in basins),
            slices=basins),
        scope='Finite same affine-material-UV samples on actual native triangles; fixed parent normals and reference two-sided chord fractions. Not planar world sections, full valley invariance, topology branching, or visual success.')
    arrays = dict(source_uv=uv, reference_xyz=reference, result_xyz=result, fixed_parent_normal=normal,
        fixed_reference_chord_projection_fraction=fraction, reference_chord_xyz=ref_chord,
        result_chord_xyz=out_chord, reference_signed_valley_deficit=ref_depth,
        result_signed_valley_deficit=out_depth, valley_displacement=shift[:, valley],
        sampled_displacement=shift, sampled_core_weight=core_weight,
        reference_normal_profile=ref_profile, result_normal_profile=out_profile,
        basin_slice_indices=chosen, reference_shoulder_detrended_profile=np.asarray(ref_detrended),
        result_shoulder_detrended_profile=np.asarray(out_detrended))
    return metrics, arrays


def _sample_parents(mesh, chart, parents):
    sampler = guidance.bulb.study.native_sampler(mesh, chart)
    samples = [sampler.sample(parent['parent_surface_uv'], records=True) for parent in parents]
    del sampler
    gc.collect()
    return samples


def run(root, meso_root=None, active_root=None):
    """Read saved controls serially; create a new metrics directory, never repair."""
    root = Path(root).resolve()
    mode_roots = {mode: root for mode in MODES}
    if meso_root is not None:
        mode_roots['MESO_ONLY_PATCH'] = Path(meso_root).resolve()
    if active_root is not None:
        mode_roots['ACTIVE_FOLDS'] = Path(active_root).resolve()
    destination = root/'metrics'
    if destination.exists():
        raise FileExistsError('Earlier metrics preserved: '+str(destination))
    required = []
    for case in CASES:
        required += [root/case/f'actual_parent_{index}.npz' for index in (0, 1)]
        for mode, mode_root in mode_roots.items():
            required += [mode_root/mode/case/'G06'/name for name in
                         ('control_quad.npz', 'operation_fields.npz', 'generation.json')]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError('Both cases and every requested state are required: '+str(missing))
    destination.mkdir()
    summary = dict(cases=list(CASES), modes=list(mode_roots), basin_recipe=BASIN_RECIPE,
        reference_reconstruction='Use saved exact reference controls when present; otherwise saved result minus actual operation delta can introduce roundoff. Each state declares its reconstruction method. Exact replay belongs to the independent geometry checks.',
        parent_depth_definition='Actual lower-to-upper two-sided shoulder chord; reference 3D chord projection fraction and measured parent normal fixed for result. Distinct from one-sided valley-to-upper shoulder relief.',
        visual_success='NOT_ASSESSED; deeper valleys or more detected minima alone are not visual success.',
        states=[])
    for case in CASES:
        parents = [guidance.bulb.read_arrays(root/case/f'actual_parent_{index}.npz') for index in (0, 1)]
        for mode, mode_root in mode_roots.items():
            folder = mode_root/mode/case/'G06'
            mesh, chart, _ = guidance.t.load(folder)
            if mesh.generation != 6:
                raise ValueError('Actual saved G06 state required: '+str(folder))
            metadata = json.loads((folder/'generation.json').read_text(encoding='utf8'))
            result_samples = _sample_parents(mesh, chart, parents)
            with np.load(folder/'operation_fields.npz', allow_pickle=False) as data:
                delta = data['delta']
                saved_reference = data['reference_xyz'] if 'reference_xyz' in data else None
            result_xyz = mesh.xyz
            mesh.xyz = saved_reference if saved_reference is not None else result_xyz-delta
            if mesh.xyz.shape != result_xyz.shape or not np.allclose(result_xyz-mesh.xyz, delta, rtol=0., atol=3e-12):
                raise ValueError('Reference and saved actual delta disagree: '+str(folder))
            reference_hash = _array_hash(mesh.xyz)
            declared_hash = metadata.get('common_reference_xyz_sha256')
            reference_samples = _sample_parents(mesh, chart, parents)
            state = dict(input_case=case, candidate=mode, control_sha256=_hash(folder/'control_quad.npz'),
                reference_method='saved reference_xyz' if saved_reference is not None else 'result_xyz minus actual delta (roundoff possible)',
                operation_sha256=_hash(folder/'operation_fields.npz'),
                reconstructed_reference_xyz_sha256=reference_hash, declared_reference_xyz_sha256=declared_hash,
                exact_reference_hash_matches=reference_hash == declared_hash if declared_hash else None,
                parent_metrics=[])
            for index, (parent, before, after) in enumerate(zip(parents, reference_samples, result_samples)):
                metrics, arrays = compare_parent(before[0], after[0], parent)
                arrays.update(reference_triangle_ids=before[1], reference_barycentric=before[2],
                              result_triangle_ids=after[1], result_barycentric=after[2])
                target = destination/f'{case}_{mode}_parent_{index}.npz'
                np.savez_compressed(target, **arrays)
                metrics.update(samples_path=target.name, samples_sha256=_hash(target),
                    actual_parent_sha256=_hash(root/case/f'actual_parent_{index}.npz'))
                state['parent_metrics'].append(metrics)
            summary['states'].append(state)
            del mesh, chart, delta, result_xyz, saved_reference, reference_samples, result_samples, arrays
            gc.collect()
    path = destination/'summary.json'
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--meso-root', type=Path)
    parser.add_argument('--active-root', type=Path)
    args = parser.parse_args()
    result = run(args.root, args.meso_root, args.active_root)
    print('SAME_UV_METRICS_COMPLETE', len(result['states']), 'states; visual success not assessed.')
