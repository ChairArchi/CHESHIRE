"""One measured parent shoulder: valley priority and a connected meso fold.

Opt-in experiment. Existing checkpoints and the accepted gate are read-only.
BASELINE and VALLEY_PRIORITY share every incoming array and colony. FLOW_CHAIN
adds a measured shoulder fold and reattaches a few colonies to that surface;
its comparison is explicitly a combined operation, not a single-variable test.
"""
from pathlib import Path
import argparse
import copy
import gc
import importlib.util
import json
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO/'src'))
sys.path.insert(0, str(HERE))
LEGACY = HERE.parent/'fold_visible_gate_20261012'
_spec = importlib.util.spec_from_file_location('parent_detail_finish', LEGACY/'detail_finish.py')
finish = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(finish)
bulb, t = finish.bulb, finish.t
import guidance

MODES = ('BASELINE', 'VALLEY_PRIORITY', 'FLOW_CHAIN')
RECIPE = dict(parent_index=1, output_generation=6, inactive_refinements=3,
    maximum_relief=.30, middle_amplitude_cap=.14, middle_width_ratio=.70,
    middle_centre_arc=.55, middle_curve_arc=.08, middle_halfwidth_arc=.22,
    middle_positive_rim_ratio=.18, parent_core_arc=.25,
    scope='One measured shoulder per canonical quadrant; material X/Y reflection',
    lineage='Actual relaxed WALL G3 trough and shoulder, not a generation-number ornament')


def bound_delta(delta, maximum=.30):
    delta = np.asarray(delta, float)
    if delta.ndim != 2 or delta.shape[1] != 3 or not np.isfinite(delta).all() or maximum <= 0:
        raise ValueError('Finite XYZ displacement and positive maximum required.')
    length = np.linalg.norm(delta, axis=1)
    return delta*np.minimum(1., maximum/np.maximum(length, 1e-30))[:, None]


def validate_cases(cases):
    if len(cases) != 2 or set(cases) != {'SPAN', 'COUNTER'}:
        raise ValueError('The comparison requires SPAN and COUNTER exactly once.')


def priority_delta(baseline_delta, positive, unsuppressed_collar, applied_normals, core_weight, recipe):
    """Same atlas/positions: give measured parent cores priority over growth."""
    baseline_delta = np.asarray(baseline_delta)
    positive, collar, weight = map(np.asarray, (positive, unsuppressed_collar, core_weight))
    if (positive.shape != (len(baseline_delta),) or collar.shape != positive.shape or weight.shape != positive.shape or
        np.asarray(applied_normals).shape != baseline_delta.shape or
        not np.isfinite(np.r_[positive, collar, weight]).all() or
        np.any(positive < 0) or np.any(collar < 0) or np.any((weight < 0) | (weight > 1))):
        raise ValueError('Nonnegative fields and core weights in [0,1] required.')
    grown = positive*(1.-weight)
    suppression = 1.-np.clip(grown/recipe['collar_positive_suppression_height'], 0., 1.)
    height = np.minimum(grown, recipe['maximum_height'])-collar*suppression**2
    height = np.clip(height, -recipe['maximum_height'], recipe['maximum_height'])
    result = baseline_delta.copy()
    active = weight > 0
    result[active] = height[active, None]*applied_normals[active]
    return result


def signed_folds(chart, parent, other_parents=()):
    """One curved negative fold plus low shoulders, excluding every parent core."""
    chart = np.asarray(chart)
    coords = guidance.patch_coordinates(chart, parent)
    q, u = coords['q'], coords['u']
    core = coords['core_weight'].copy()
    for other in other_parents:
        core = np.maximum(core, guidance.patch_coordinates(chart, other)['core_weight'])
    centre = RECIPE['middle_centre_arc']+RECIPE['middle_curve_arc']*np.sin(np.pi*q+.31)
    width = RECIPE['middle_halfwidth_arc']
    amplitude = np.minimum(RECIPE['middle_amplitude_cap'], RECIPE['middle_width_ratio']*
        np.interp(chart[:, 0], parent['parameter'], parent['parent_shoulder_width']))
    groove = -bulb.compact((u-centre)/width)
    rims = RECIPE['middle_positive_rim_ratio']*(bulb.compact((u-centre-width)/(.55*width))+
        bulb.compact((u-centre+width)/(.55*width)))
    height = amplitude*(groove+rims)*coords['envelope']*(1.-core)
    normal = bulb.unit(np.column_stack([np.interp(chart[:, 0], parent['parameter'],
        parent['parent_normal'][:, axis]) for axis in range(3)]))
    normal[:, :2] *= np.where(chart[:, 1:] < 0, -1., 1.)
    delta = height[:, None]*normal
    delta[np.abs(chart[:, 1]) < 1e-10, 0] = 0.
    delta[np.abs(chart[:, 2]) < 1e-10, 1] = 0.
    return delta, dict(fold_height=height, core_union=core, patch_envelope=coords['envelope'])


def reflect(delta, chart):
    existing = t.prior.helpers.existing
    existing.reflect(delta, chart, existing.symmetry(chart))
    return delta


def refine(mesh, chart, tags):
    for _ in range(3):
        mesh, chart, tags, _ = t.memory.refine(mesh, chart, tags)
    return mesh, chart, tags


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def geometry_checks(mesh, chart):
    native = t.growth.native(mesh)
    symmetry = finish.native_lr_symmetry(mesh, chart, native)
    return native, dict(finite=bool(np.isfinite(native.xyz).all()),
        minimum_triangle_area=finish.minimum_area(native.xyz, native.faces[:, :3]),
        actual_native_left_right_symmetry=symmetry,
        native_xyz_sha256=finish.array_hash(native.xyz), native_faces_sha256=finish.array_hash(native.faces[:, :3]))


def save_state(folder, mesh, chart, tags, common_reference, delta, metadata, fields):
    if folder.exists():
        raise FileExistsError('Earlier result preserved: '+str(folder))
    folder.mkdir(parents=True)
    native, checks = geometry_checks(mesh, chart)
    actual_delta = mesh.xyz-common_reference
    maxshift = float(np.linalg.norm(actual_delta, axis=1).max())
    checks.update(maximum_total_detail_shift=maxshift,
        control_xyz_sha256=finish.array_hash(mesh.xyz),
        control_topology_sha256=finish.array_hash(mesh.faces),
        outside_patch_delta_sha256=finish.array_hash(delta[fields['changed_region'] == 0]))
    checks['passed'] = bool(checks['finite'] and checks['minimum_triangle_area'] > 1e-14 and
        checks['actual_native_left_right_symmetry']['passed'] and maxshift <= .30+1e-10)
    np.savez_compressed(folder/'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces, chart=chart,
        classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors, generation=np.array(mesh.generation),
        surface=np.array(mesh.surface), memory=tags)
    np.savez_compressed(folder/'geometry.npz', xyz=native.xyz, faces=native.faces[:, :3])
    np.savez_compressed(folder/'operation_fields.npz', delta=actual_delta, **fields)
    write_json(folder/'generation.json', dict(metadata, checks=checks))
    del native; gc.collect()
    print('SAVED', metadata['input_case'], metadata['candidate'], checks['passed'], maxshift, flush=True)
    if not checks['passed']:
        raise ValueError('Failed geometry preserved at '+str(folder))
    return checks


def sample_diagnostics(mesh, chart, parents):
    sampler = bulb.study.native_sampler(mesh, chart)
    output = []
    for parent in parents:
        uv = parent['parent_shoulder_uv']
        xyz = sampler.sample(uv)
        normal = parent['parent_normal']
        profile = np.einsum('nkj,nj->nk', xyz, normal)
        # Actual same-UV endpoints and valley, not the old target depth.
        chord = profile[:, :1]+(profile[:, -1:]-profile[:, :1])*np.linspace(0., 1., profile.shape[1])[None, :]
        output.append(dict(xyz=xyz, projected=profile, chord_deficit=chord-profile))
    return output


def run_case(root, parent_root, integrated_root, case, modes=MODES):
    finish.memory_guard()
    source = parent_root/'WALL'/case/'G03'
    case_root = root/case
    case_root.mkdir(parents=True)
    mesh3, chart3, tags3 = t.load(source)
    carrier_delta = finish.relax_carrier(mesh3, chart3)
    parents = [guidance.measure_parent(source, i, mesh=mesh3, chart=chart3) for i in (0, 1)]
    parent = parents[RECIPE['parent_index']]
    for i, measured in enumerate(parents):
        np.savez_compressed(case_root/f'actual_parent_{i}.npz', **measured)
    atlas_path = integrated_root/'atlas/power8.npz'
    colony_path = integrated_root/'INTEGRATED'/case/'G05/colonies.npz'
    atlas, old_colonies = bulb.read_arrays(atlas_path), bulb.read_arrays(colony_path)
    common, chart, tags = refine(copy.deepcopy(mesh3), chart3.copy(), tags3.copy())
    reference = common.xyz.copy()
    native = t.growth.native(common)
    normals = finish.stream_control_normals(native.xyz, native.faces[:, :3], len(common.xyz))
    del native; gc.collect()
    recipe = bulb.VARIANTS['INTEGRATED']
    baseline, basefields = bulb.apply_colonies(reference, chart, normals, old_colonies, atlas, .30, recipe)
    _, unsuppressed = bulb.apply_colonies(reference, chart, normals, old_colonies, atlas, .30,
        dict(recipe, collar_positive_suppression_height=1e30))
    coords = guidance.patch_coordinates(chart, parent)
    core = np.maximum.reduce([guidance.patch_coordinates(chart, p)['core_weight'] for p in parents])
    priority = priority_delta(baseline, basefields['raw_height'], unsuppressed['root_collar_height'],
        basefields['applied_normals'], core, recipe)
    baseline, priority = reflect(baseline, chart), reflect(priority, chart)
    del unsuppressed; gc.collect()
    identity = dict(input_case=case, source=str(source), source_control_sha256=bulb.digest(source/'control_quad.npz'),
        atlas_source=str(atlas_path), atlas_sha256=bulb.digest(atlas_path),
        original_colonies_source=str(colony_path), original_colonies_sha256=bulb.digest(colony_path),
        recipe=RECIPE, relief_recipe=recipe, relaxation_recipe=finish.RELAXATION,
        common_reference_xyz_sha256=finish.array_hash(reference),
        common_incoming_normals_sha256=finish.array_hash(normals),
        carrier_relaxation_maximum=float(np.linalg.norm(carrier_delta, axis=1).max()),
        output_generation=6, field_internal_iterations=10,
        topology='Unchanged inherited quad/fan connectivity; no appended component',
        self_intersection='Exploration proceeds per user preference; not certified',
        baseline_comparison='BASELINE vs VALLEY_PRIORITY changes only parent-core growth priority')
    np.savez_compressed(case_root/'common_carrier_relaxation.npz', delta=carrier_delta)
    before = sample_diagnostics(common, chart, parents)
    receipts = []
    for mode in modes:
        fields = dict(changed_region=(core > 0).astype(np.uint8), parent_core_weight=core,
            selected_patch_envelope=coords['envelope'])
        if mode == 'BASELINE':
            delta = baseline.copy()
        elif mode == 'VALLEY_PRIORITY':
            delta = priority.copy()
        elif mode == 'FLOW_CHAIN':
            middle3 = copy.deepcopy(mesh3)
            fold3, fold_fields = signed_folds(chart3, parent, parents)
            middle3.xyz = mesh3.xyz+reflect(fold3, chart3)
            colonies = guidance.make_guided_colonies(middle3, chart3, parent, recipe)
            middle6, chain_chart, _ = refine(middle3, chart3.copy(), tags3.copy())
            if not np.array_equal(chart, chain_chart) or not np.array_equal(common.faces, middle6.faces):
                raise ValueError('Middle fold changed chart or topology.')
            meso_delta = middle6.xyz-reference
            native = t.growth.native(middle6)
            middle_normals = finish.stream_control_normals(native.xyz, native.faces[:, :3], len(middle6.xyz))
            del native; gc.collect()
            # Reattach the saved material samples to the actual final G6 native
            # surface. Coarse frame/trajectory evidence remains separately saved.
            sampler = bulb.study.native_sampler(middle6, chart)
            positions, ids, bary = sampler.sample(colonies['sample_uv'], records=True)
            colonies['frame_source_xyz'] = colonies['source_xyz'].copy()
            colonies['frame_source_triangle_ids'] = colonies['source_triangle_ids'].copy()
            colonies['frame_source_barycentric'] = colonies['source_barycentric'].copy()
            colonies['frame_source_generation'] = np.array(3)
            colonies['centres'] = positions
            colonies['source_xyz'] = positions.copy()
            colonies['source_triangle_ids'], colonies['source_barycentric'] = ids, bary
            count = int((colonies['levels'] == 0).sum())
            colonies['primary_source_xyz'] = positions[:count].copy()
            colonies['primary_source_triangle_ids'] = ids[:count].copy()
            colonies['primary_source_barycentric'] = bary[:count].copy()
            colonies['source_control_generation'] = np.array(6)
            colonies['source_carrier_xyz_sha256'] = np.array(finish.array_hash(middle6.xyz))
            np.savez_compressed(case_root/'guided_colonies.npz', **colonies)
            del sampler; gc.collect()
            guided, guided_fields = bulb.apply_colonies(middle6.xyz, chart, middle_normals, colonies, atlas, .30, recipe)
            # The same measured shoulder ownership excludes all parent cores.
            envelope = coords['envelope']*(1.-core)
            delta = priority+meso_delta+envelope[:, None]*(guided-priority)
            fields.update(changed_region=((core > 0) | (envelope > 0) | (np.linalg.norm(meso_delta, axis=1) > 0)).astype(np.uint8),
                middle_delta=meso_delta, guided_positive=guided_fields['positive_height'])
            del middle6, middle_normals, guided, guided_fields; gc.collect()
        else:
            raise ValueError(mode)
        delta = reflect(bound_delta(delta), chart)
        common.xyz = reference+delta
        after = sample_diagnostics(common, chart, parents)
        for i, (a, b) in enumerate(zip(before, after)):
            np.savez_compressed(case_root/f'{mode}_parent_{i}_samples.npz',
                source_uv=parents[i]['parent_shoulder_uv'], reference_xyz=a['xyz'], result_xyz=b['xyz'],
                reference_profile=a['projected'], result_profile=b['projected'],
                reference_chord_deficit=a['chord_deficit'], result_chord_deficit=b['chord_deficit'])
        checks = save_state(root/mode/case/'G06', common, chart, tags, reference, delta,
            dict(identity, candidate=mode, combined_operation=mode == 'FLOW_CHAIN'), fields)
        receipts.append(dict(candidate=mode, checks=checks))
        common.xyz = reference.copy()
        del delta, after, fields; gc.collect()
    write_json(case_root/'SUMMARY.json', dict(input_case=case, states=receipts,
        passed=all(item['checks']['passed'] for item in receipts)))
    print('CASE_COMPLETE', case, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--parent-root', type=Path, required=True)
    parser.add_argument('--integrated-root', type=Path, required=True)
    parser.add_argument('--case', choices=('SPAN', 'COUNTER'), required=True)
    parser.add_argument('--modes', nargs='+', choices=MODES, default=list(MODES))
    args = parser.parse_args()
    root = args.root.resolve()
    if (root/args.case).exists():
        raise FileExistsError('Existing case output preserved.')
    root.mkdir(parents=True, exist_ok=True)
    write_json(root/'RECIPE.json', RECIPE)
    run_case(root, args.parent_root.resolve(), args.integrated_root.resolve(), args.case, args.modes)


if __name__ == '__main__':
    main()
