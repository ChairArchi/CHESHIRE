"""Opt-in attached longitudinal ribs, branching curves and smaller side folds.

G4 and G5 are active actual-normal geometry stages; G6 is inactive refinement.
The branch layout is authored in a measured parent's physical-arc chart. It is
not an automatically discovered branching grammar or a full fractal volume.
No existing checkpoint is edited. The final local replacement preserves the
saved BASELINE exactly outside its patch, at ends, and in protected parent cores.
"""
from pathlib import Path
import argparse
import copy
import gc
import importlib.util
import json
import shutil
import sys

import numpy as np
from scipy.spatial import cKDTree
import trimesh


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import guidance

_spec = importlib.util.spec_from_file_location('active_fold_finish', guidance.LEGACY/'detail_finish.py')
finish = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(finish)
t, bulb = finish.t, finish.bulb
CASES = ('SPAN', 'COUNTER')
CANDIDATE = 'ACTIVE_FOLDS'
RECIPE = dict(parent_index=1, output_generation=6, active_generations=[4, 5],
    maximum_total_shift=.45, end_limits=[.10, .90],
    core_arc_halfwidth=.25, core_transverse_fade=.10, core_axial_extension=.20,
    trunk_base=.54, trunk_linear=.035, trunk_quadratic=-.020,
    branch_starts=[-.35, .10], branch_durations=[1.10, .80],
    branch_offsets=[.22, -.18], branch_gate_span=.22,
    primary_halfwidth_arc=.15, primary_height_width_ratio=1.25, primary_height_cap=.24,
    primary_branch_ratio=.85, side_groove_ratio=.52, side_groove_offset_in_halfwidths=1.35,
    side_groove_halfwidth_ratio=.65,
    secondary_offset_arc=.085, secondary_halfwidth_arc=.065,
    secondary_height_width_ratio=.38, secondary_height_cap=.075,
    secondary_start_delay=.14, curve_sample_count=61,
    scope='One measured parent shoulder per material quadrant, same recipe on SPAN/COUNTER',
    amplitude_scope='The .45 total bound is an explicit first comparison condition, not a user-mandated design limit',
    inspiration='Earlier ROLE_ABSOLUTE middle-scale walls/lips are a composition clue; this is a new continuous signed-band operator, not that algorithm',
    reference_evidence='docs/fold_band_growth_20261011/technical/role_ablation_review.md:7')


def curves(q, recipe=RECIPE):
    """Continuous trunk plus two staggered branches; no axial repeat texture."""
    q = np.asarray(q, float)
    trunk = recipe['trunk_base']+recipe['trunk_linear']*q+recipe['trunk_quadratic']*q*q
    centres, gates = [trunk], [np.ones_like(q)]
    for start, duration, offset in zip(recipe['branch_starts'], recipe['branch_durations'], recipe['branch_offsets']):
        centres.append(trunk+offset*guidance._quintic((q-start)/duration))
        gates.append(guidance._quintic((q-start)/recipe['branch_gate_span']))
    return np.asarray(centres), np.asarray(gates)


def ownership(chart, parent, parents, recipe=RECIPE):
    """Smooth replacement with an exact inner core for *every* parent valley."""
    chart = np.asarray(chart)
    selected = guidance.patch_coordinates(chart, parent)
    weight = selected['envelope'].copy()
    protected = np.zeros(len(chart), bool)
    for item in parents:
        coords = guidance.patch_coordinates(chart, item)
        transverse_pass = guidance._quintic((np.abs(coords['u'])-recipe['core_arc_halfwidth'])/
                                            recipe['core_transverse_fade'])
        axial_release = guidance._quintic((np.abs(coords['q'])-1.)/recipe['core_axial_extension'])
        weight *= 1.-(1.-transverse_pass)*(1.-axial_release)
        protected |= (np.abs(coords['u']) <= recipe['core_arc_halfwidth']) & (np.abs(coords['q']) <= 1.)
    lower, upper = recipe['end_limits']
    ends = (chart[:, 0] <= lower) | (chart[:, 0] >= upper)
    weight[protected | ends] = 0.
    return dict(weight=weight, protected=protected, ends=ends, q=selected['q'], u=selected['u'])


def signed_height(chart, parent, parents, stage, recipe=RECIPE):
    """Ribs own their connected crowns; flanking negative bands retain roots."""
    owned = ownership(chart, parent, parents, recipe)
    q, u = owned['q'], owned['u']
    centre, gate = curves(q, recipe)
    width = np.interp(chart[:, 0], parent['parameter'], parent['parent_shoulder_width'])
    if stage == 4:
        halfwidth = recipe['primary_halfwidth_arc']
        height = np.minimum(recipe['primary_height_cap'], recipe['primary_height_width_ratio']*width)
        ratios = np.array([1., recipe['primary_branch_ratio'], recipe['primary_branch_ratio']])
        positive = np.max(ratios[:, None]*gate*bulb.compact((u[None]-centre)/halfwidth), axis=0)
        sides = []
        for direction in (-1., 1.):
            offset = direction*recipe['side_groove_offset_in_halfwidths']*halfwidth
            sides.append(np.max(ratios[:, None]*gate*bulb.compact((u[None]-centre-offset)/
                (recipe['side_groove_halfwidth_ratio']*halfwidth)), axis=0))
        negative = recipe['side_groove_ratio']*np.maximum.reduce(sides)*(1.-np.clip(positive, 0., 1.))**2
    elif stage == 5:
        halfwidth = recipe['secondary_halfwidth_arc']
        height = np.minimum(recipe['secondary_height_cap'], recipe['secondary_height_width_ratio']*width)
        offsets = np.array([recipe['secondary_offset_arc'], -recipe['secondary_offset_arc']])
        side_centres = centre[1:]+offsets[:, None]
        delayed = np.array([guidance._quintic((q-start-recipe['secondary_start_delay'])/
            recipe['branch_gate_span']) for start in recipe['branch_starts']])
        positive = np.max(delayed*bulb.compact((u[None]-side_centres)/halfwidth), axis=0)
        negative = recipe['side_groove_ratio']*np.max(delayed*bulb.compact((u[None]-side_centres-
            offsets[:, None]*.75)/(halfwidth*.70)), axis=0)*(1.-np.clip(positive, 0., 1.))**2
    else:
        raise ValueError('Only G4 primary and G5 secondary active stages are defined.')
    signed = height*(positive-negative)*owned['weight']
    return signed, dict(height=signed, positive_band=positive, negative_band=negative,
        adaptive_height=height, patch_weight=owned['weight'], protected_core=owned['protected'],
        fixed_ends=owned['ends'], q=q, u=u)


def normal_delta(chart, incoming_normals, parent, parents, stage, recipe=RECIPE):
    """Displace along actual incoming native angle-weighted control normals."""
    height, fields = signed_height(chart, parent, parents, stage, recipe)
    normals = np.asarray(incoming_normals, float)
    if normals.shape != chart.shape or not np.isfinite(normals).all():
        raise ValueError('Actual finite incoming native control normals required.')
    active = height != 0.
    if np.any(np.linalg.norm(normals[active], axis=1) < .9):
        raise ValueError('Active incoming body has no stable actual native normal.')
    normals = bulb.unit(normals)
    tangent = guidance._interp(chart[:, 0], parent['parameter'], parent['parent_tangent'])
    tangent[:, :2] *= np.where(chart[:, 1:] < 0., -1., 1.)
    tangent = bulb.unit(tangent-normals*np.sum(tangent*normals, axis=1)[:, None])
    if np.any(np.linalg.norm(tangent[active], axis=1) < .9):
        raise ValueError('Actual incoming normal and inherited parent direction have a degenerate frame.')
    delta = height[:, None]*normals
    fields.update(incoming_normals=normals, projected_parent_tangent=tangent)
    return delta, fields


def reflect(delta, chart):
    existing = t.prior.helpers.existing
    existing.reflect(delta, chart, existing.symmetry(chart))
    return delta


def _curve_evidence(mesh, chart, parent, stage, recipe):
    """Actual incoming native samples for the authored branch coordinates."""
    sampler = bulb.study.native_sampler(mesh, chart)
    q = np.linspace(-.90, .90, recipe['curve_sample_count'])
    parameter = parent['parameter'][0]+(q+1.)*.5*np.ptp(parent['parameter'])
    centre, gate = curves(q, recipe)
    labels = np.array(['TRUNK', 'BRANCH_UPPER', 'BRANCH_LOWER'])
    if stage == 5:
        centre = centre[1:]+np.array([recipe['secondary_offset_arc'], -recipe['secondary_offset_arc']])[:, None]
        gate = np.array([guidance._quintic((q-start-recipe['secondary_start_delay'])/
            recipe['branch_gate_span']) for start in recipe['branch_starts']])
        labels = np.array(['SIDE_UPPER', 'SIDE_LOWER'])
    uv = np.stack([guidance._uv_at_fraction(parameter, line, parent) for line in centre])
    xyz, ids, bary = sampler.sample(uv, records=True)
    triangle_xyz = sampler.xyz  # The native chart sampler retains actual triangle positions.
    # IDs are native IDs, so lookup is explicitly through its retained ID map.
    local = np.searchsorted(sampler.ids, ids)
    tri = triangle_xyz[local]
    normal = bulb.unit(np.cross(tri[..., 1, :]-tri[..., 0, :], tri[..., 2, :]-tri[..., 0, :]))
    tangent = np.gradient(xyz, parameter, axis=1)
    tangent = bulb.unit(tangent-normal*np.sum(tangent*normal, axis=2)[..., None])
    evidence = dict(curve_labels=labels,
        q=q, physical_arc_fraction=centre, activation=gate, source_uv=uv,
        source_xyz=xyz, source_triangle_ids=ids, source_barycentric=bary,
        actual_triangle_normals=normal, actual_curve_tangent=tangent,
        incoming_generation=np.array(stage), source_control_xyz_sha256=np.array(finish.array_hash(mesh.xyz)))
    del sampler
    gc.collect()
    return evidence


def _bound(delta, maximum):
    delta = np.asarray(delta)
    length = np.linalg.norm(delta, axis=1)
    return delta*np.minimum(1., maximum/np.maximum(length, 1e-30))[:, None]


def _source(root, case, metadata):
    expected = metadata['source_control_sha256']
    candidates = [Path(metadata['source']), REPO/'docs/fold_visible_gate_20261012/review/WALL'/case/'G03']
    for candidate in candidates:
        control = candidate/'control_quad.npz'
        if control.is_file() and bulb.digest(control) == expected:
            return candidate
    raise FileNotFoundError('No exact-hash actual WALL G3 source: '+str(candidates))


def _native_axis_symmetry(mesh, chart, native, axis):
    pchart = np.concatenate([chart, t.face_values(mesh, chart)])
    sign_chart, sign_xyz = np.ones(3), np.ones(3)
    sign_chart[axis+1] = -1.; sign_xyz[axis] = -1.
    tree = cKDTree(pchart)
    distance, pairs = tree.query(pchart*sign_chart)
    material_error = float(distance.max())
    involution = bool(np.array_equal(pairs[pairs], np.arange(len(pairs))))
    del tree, distance, pchart
    gc.collect()
    error = 0.
    for start in range(0, len(pairs), 120000):
        ids = pairs[start:start+120000]
        error = max(error, float(np.linalg.norm(native.xyz[start:start+len(ids)]-
            native.xyz[ids]*sign_xyz, axis=1).max()))
    original = finish.oriented_canonical(native.faces[:, :3])
    reflected = finish.oriented_canonical(pairs[native.faces[:, 2::-1]])
    oriented = bool(np.array_equal(original, reflected))
    del pairs, original, reflected
    gc.collect()
    return dict(passed=material_error < 1e-9 and involution and error < 1e-9 and oriented,
        material_pair_max_error=material_error, actual_native_xyz_pair_max_error=error,
        pair_involution=involution, reflected_oriented_native_triangles_identical=oriented)


def _write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')


def _restore_guarded_weights(mesh, chart, parent, parents, recipe):
    """Also guard fan centres: restoring their incident controls preserves XYZ."""
    control = ownership(chart, parent, parents, recipe)
    fan = ownership(t.face_values(mesh, chart), parent, parents, recipe)
    weights = control['weight'].copy()
    outside_faces = fan['weight'] == 0.
    if outside_faces.any():
        weights[np.unique(mesh.faces[outside_faces])] = 0.
    return weights, control, fan


def run_case(root, output, case, recipe=RECIPE):
    finish.memory_guard()
    root, output = Path(root).resolve(), Path(output).resolve()
    final = output/CANDIDATE/case/'G06'
    evidence_root = output/case
    if final.exists() or evidence_root.exists():
        raise FileExistsError('Earlier case preserved: '+str(final))
    base_path = root/'BASELINE'/case/'G06'
    metadata = json.loads((base_path/'generation.json').read_text(encoding='utf8'))
    source = _source(root, case, metadata)
    mesh, chart, tags = t.load(source)
    if mesh.generation != 3:
        raise ValueError('Actual G03 source required.')
    source_native = t.growth.native(mesh)
    physical = trimesh.Trimesh(source_native.xyz, source_native.faces[:, :3], process=False)
    source_topology = dict(components=int(physical.body_count), watertight=bool(physical.is_watertight),
                           winding_consistent=bool(physical.is_winding_consistent))
    if source_topology != dict(components=1, watertight=True, winding_consistent=True):
        raise ValueError('Source must be one closed consistently oriented native body.')
    del source_native, physical
    carrier_delta = finish.relax_carrier(mesh, chart, metadata['relaxation_recipe'])
    parents = [bulb.read_arrays(root/case/f'actual_parent_{index}.npz') for index in (0, 1)]
    for parent in parents:
        if str(parent['measured_carrier_xyz_sha256']) != finish.array_hash(mesh.xyz):
            raise ValueError('Saved parent evidence belongs to another actual carrier.')
    parent = parents[recipe['parent_index']]
    common, common_chart, common_tags = copy.deepcopy(mesh), chart.copy(), tags.copy()
    for _ in range(3):
        common, common_chart, common_tags, _ = t.memory.refine(common, common_chart, common_tags)
    reference = common.xyz
    if finish.array_hash(reference) != metadata['common_reference_xyz_sha256']:
        raise ValueError('Exact relaxed/inactive reference replay failed.')
    evidence_root.mkdir(parents=True)
    for index in (0, 1):
        shutil.copy2(root/case/f'actual_parent_{index}.npz', evidence_root/f'actual_parent_{index}.npz')
    np.savez_compressed(evidence_root/'common_carrier_relaxation.npz', delta=carrier_delta)
    stages = []
    for generation in (4, 5):
        mesh, chart, tags, operator = t.memory.refine(mesh, chart, tags)
        if mesh.generation != generation:
            raise ValueError('Unexpected active stage lineage.')
        native = t.growth.native(mesh)
        normals = finish.stream_control_normals(native.xyz, native.faces[:, :3], len(mesh.xyz))
        del native
        gc.collect()
        curves_path = evidence_root/f'G{generation:02d}_incoming_curves.npz'
        np.savez_compressed(curves_path, **_curve_evidence(mesh, chart, parent, generation, recipe))
        before = finish.array_hash(mesh.xyz)
        delta, fields = normal_delta(chart, normals, parent, parents, generation, recipe)
        raw_hash = finish.array_hash(delta)
        reflect(delta, chart)
        mesh.xyz += delta
        path = evidence_root/f'G{generation:02d}_active_fields.npz'
        np.savez_compressed(path, delta=delta, input_edges=operator['input_edges'], parent_face=operator['parent_face'], **fields)
        stages.append(dict(generation=generation, incoming_xyz_sha256=before,
            raw_delta_sha256=raw_hash, applied_delta_sha256=finish.array_hash(delta),
            resulting_xyz_sha256=finish.array_hash(mesh.xyz), maximum_active_shift=float(np.linalg.norm(delta, axis=1).max()),
            positive_height_maximum=float(fields['height'].max()), negative_height_minimum=float(fields['height'].min()),
            moved_controls=int(np.count_nonzero(np.linalg.norm(delta, axis=1) > 1e-12)),
            fields_path=str(path.relative_to(output)), fields_sha256=bulb.digest(path),
            curve_path=str(curves_path.relative_to(output)), curve_sha256=bulb.digest(curves_path)))
        del normals, delta, fields, operator
        gc.collect()
    mesh, chart, tags, _ = t.memory.refine(mesh, chart, tags)
    if mesh.generation != 6 or not np.array_equal(common_chart, chart) or not np.array_equal(common.faces, mesh.faces):
        raise ValueError('Active operation changed the inherited chart or topology.')
    baseline, baseline_chart, _ = t.load(base_path)
    if not np.array_equal(baseline_chart, chart) or not np.array_equal(baseline.faces, mesh.faces):
        raise ValueError('Saved BASELINE correspondence differs.')
    if not np.array_equal(baseline.classes, mesh.classes) or baseline.surface != mesh.surface:
        raise ValueError('Saved BASELINE native surface construction differs.')
    active_delta = mesh.xyz-reference
    raw_max = float(np.linalg.norm(active_delta, axis=1).max())
    active_delta = reflect(_bound(active_delta, recipe['maximum_total_shift']), chart)
    weight, control_ownership, fan_ownership = _restore_guarded_weights(mesh, chart, parent, parents, recipe)
    mesh.xyz = baseline.xyz+weight[:, None]*(reference+active_delta-baseline.xyz)
    total = reflect(_bound(mesh.xyz-reference, recipe['maximum_total_shift']), chart)
    mesh.xyz = reference+total
    fixed = weight == 0.
    mesh.xyz[fixed] = baseline.xyz[fixed]
    total = mesh.xyz-reference  # synchronize the operation with exact restoration
    native = t.growth.native(mesh)
    baseline_native_xyz = np.concatenate([baseline.xyz, t.face_values(baseline, baseline.xyz)])
    outside_native = np.r_[control_ownership['weight'] == 0., fan_ownership['weight'] == 0.]
    ends_native = np.r_[control_ownership['ends'], fan_ownership['ends']]
    cores_native = np.r_[control_ownership['protected'], fan_ownership['protected']]
    max_error = lambda mask: float(np.linalg.norm(native.xyz[mask]-baseline_native_xyz[mask], axis=1).max()) if mask.any() else 0.
    outside_error, end_error, core_error = max_error(outside_native), max_error(ends_native), max_error(cores_native)
    outside_exact = bool(np.array_equal(native.xyz[outside_native], baseline_native_xyz[outside_native]))
    end_exact = bool(np.array_equal(native.xyz[ends_native], baseline_native_xyz[ends_native]))
    core_exact = bool(np.array_equal(native.xyz[cores_native], baseline_native_xyz[cores_native]))
    del baseline_native_xyz
    gc.collect()
    symmetry = {axis: _native_axis_symmetry(mesh, chart, native, index) for index, axis in enumerate(('X', 'Y'))}
    area = finish.minimum_area(native.xyz, native.faces[:, :3])
    maximum = float(np.linalg.norm(total, axis=1).max())
    triangles_hash = finish.array_hash(native.faces[:, :3])
    same_faces = triangles_hash == metadata['checks']['native_faces_sha256']
    checks = dict(finite=bool(np.isfinite(native.xyz).all()), minimum_triangle_area=area,
        actual_native_xy_symmetry=symmetry, source_topology=source_topology,
        inherited_native_faces_identical_to_baseline=same_faces, native_faces_sha256=triangles_hash,
        native_xyz_sha256=finish.array_hash(native.xyz), control_xyz_sha256=finish.array_hash(mesh.xyz),
        maximum_total_shift=maximum, raw_active_total_shift=raw_max,
        control_outside_restored_exact=bool(np.array_equal(mesh.xyz[fixed], baseline.xyz[fixed])),
        actual_native_outside_baseline_exact=outside_exact, actual_native_ends_baseline_exact=end_exact,
        actual_native_core_baseline_exact=core_exact, outside_error=outside_error, end_error=end_error, core_error=core_error,
        control_patch_count=int(np.count_nonzero(weight)), outside_native_count=int(outside_native.sum()),
        protected_native_core_count=int(cores_native.sum()), end_native_count=int(ends_native.sum()))
    checks['passed'] = bool(checks['finite'] and area > 1e-14 and all(item['passed'] for item in symmetry.values()) and
        same_faces and maximum <= recipe['maximum_total_shift']+3e-12 and outside_exact and end_exact and core_exact and
        max(outside_error, end_error, core_error) <= 3e-12)
    final.mkdir(parents=True)
    np.savez_compressed(final/'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces, chart=chart,
        classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors, generation=np.array(mesh.generation),
        surface=np.array(mesh.surface), memory=tags)
    np.savez_compressed(final/'geometry.npz', xyz=native.xyz, faces=native.faces[:, :3])
    np.savez_compressed(final/'operation_fields.npz', reference_xyz=reference, delta=total,
        replacement_weight=weight, protected_core=control_ownership['protected'], fixed_ends=control_ownership['ends'])
    result = dict(input_case=case, candidate=CANDIDATE, source=str(source),
        source_control_sha256=bulb.digest(source/'control_quad.npz'), baseline_source=str(base_path),
        baseline_control_sha256=bulb.digest(base_path/'control_quad.npz'), recipe=recipe,
        relaxation_recipe=metadata['relaxation_recipe'], common_reference_xyz_sha256=finish.array_hash(reference),
        stages=stages, output_generation=6, inactive_generation=6, new_field_atlas=False,
        protected_core_scope='Exact saved BASELINE core/ends/outside restoration, not a claim that the old BASELINE preserved the raw parent valley',
        topology_scope='One closed oriented inherited body; original face IDs and fan connectivity preserved; no appended components',
        visual_status='UNASSESSED: connected ribs/basins and hierarchy require matched actual renders',
        branching_scope='Authored continuous curve bifurcations in an actually measured parent chart; not automatic topology/grammar discovery',
        self_intersection='Not checked, per exploratory scope', checks=checks)
    _write(final/'generation.json', result)
    for path in (Path(__file__), HERE/'guidance.py'):
        shutil.copy2(path, evidence_root/path.name)
    _write(evidence_root/'ACTIVE_FOLDS_SUMMARY.json', result)
    print('ACTIVE_FOLDS_SAVED', case, checks['passed'], maximum, flush=True)
    del mesh, common, baseline, native, total, active_delta
    gc.collect()
    if not checks['passed']:
        raise ValueError('Failed geometry retained: '+str(final))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='Preserved trial02 with BASELINE and actual parent evidence')
    parser.add_argument('--output', type=Path, required=True, help='Fresh output root, preferably external E data volume')
    parser.add_argument('--case', nargs='+', choices=CASES, default=list(CASES))
    args = parser.parse_args()
    if len(set(args.case)) != len(args.case):
        parser.error('Each requested case must occur once.')
    if args.output.exists():
        raise FileExistsError('Fresh output root required: '+str(args.output))
    args.output.mkdir(parents=True)
    _write(args.output/'RECIPE.json', RECIPE)
    receipts = [run_case(args.root, args.output, case) for case in args.case]
    _write(args.output/'SUMMARY.json', dict(cases=args.case, required_full_comparison=list(CASES),
        both_inputs_complete=set(args.case) == set(CASES),
        geometry_checks_passed=all(item['checks']['passed'] for item in receipts),
        passed=set(args.case) == set(CASES) and all(item['checks']['passed'] for item in receipts),
        visual_success='NOT_ASSESSED', states=receipts))
