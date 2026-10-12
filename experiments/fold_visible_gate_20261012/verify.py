"""Replay saved G3 wall experiments and the separated three-member assemblies.

This is finite operation/native-geometry verification, not aesthetic evaluation,
self-intersection detection, structural analysis, or physical clearance proof.
CHILD/G04 and other continuation experiments are deliberately outside this API.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

import numpy as np
from scipy.spatial import cKDTree
import trimesh

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location('verified_visible_wall_study', HERE/'study.py')
study = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(study)
import gate_members

CASES = ('SPAN', 'COUNTER', 'GATE_COLUMN', 'GATE_LINTEL')
MODES = ('CONTROL', 'PREVIOUS', 'DEPTH', 'WALL')
TOLERANCE = 1e-12


def arrays(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key].copy() for key in data.files}


def max_error(left, right):
    left, right = np.asarray(left), np.asarray(right)
    if left.shape != right.shape:
        raise ValueError('Array shapes differ: '+str(left.shape)+' versus '+str(right.shape))
    return float(np.max(np.abs(left-right), initial=0.))


def canonical_cycles(triangles):
    """Keep orientation but remove arbitrary first-corner choice and row order."""
    triangles = np.asarray(triangles)
    start = np.argmin(triangles, axis=1)
    rows = np.arange(len(triangles))[:, None]
    cycles = triangles[rows, (start[:, None]+np.arange(3)[None]) % 3]
    return cycles[np.lexsort((cycles[:, 2], cycles[:, 1], cycles[:, 0]))]


def global_lr(xyz, triangles):
    """Actual XYZ pairing plus oriented triangle reflection, not bbox symmetry."""
    target = np.asarray(xyz)*[-1., 1., 1.]
    distance, ids = cKDTree(xyz).query(target)
    involution = bool(np.array_equal(ids[ids], np.arange(len(ids))))
    reflected = ids[triangles][:, [0, 2, 1]]
    triangles_equal = bool(np.array_equal(canonical_cycles(triangles), canonical_cycles(reflected)))
    return dict(maximum_xyz_pair_error=float(distance.max()), pair_map_involutive=involution,
        reflected_oriented_triangle_sets_identical=triangles_equal,
        passed=bool(distance.max() < TOLERANCE and involution and triangles_equal))


def recipe_without_candidate(metadata):
    return {key: value for key, value in metadata['recipe'].items() if key != 'candidate'}


def verify_parent(root, case, mode):
    folder = root/mode/case/'G03'
    metadata = json.loads((folder/'generation.json').read_text(encoding='utf8'))
    operation = arrays(folder/'operation_fields.npz')
    control = arrays(folder/'control_quad.npz')
    geometry = arrays(folder/'geometry.npz')
    guides = [arrays(path) for path in sorted(folder.glob('guide_*.npz'))]
    rails = [arrays(path) for path in sorted(folder.glob('rails_*.npz'))]
    reference, chart = operation['reference_xyz'], operation['chart']
    if metadata['input_case'] != case or metadata['candidate'] != mode:
        raise ValueError('Saved case/candidate identity differs from its directory.')
    if int(control['generation']) != 3 or len(guides) != 2 or len(rails) != 2:
        raise ValueError('Expected G3 controls and two saved parent guide/rail pairs.')
    if metadata['recipe'] != dict(study.RECIPE, candidate=mode):
        raise ValueError('Saved recipe differs from the declared common runner recipe.')
    rail_coefficient_errors = []
    for rail in rails:
        rail_coefficient_errors.extend([
            abs(float(rail['angle_degrees'])-40.),
            abs(float(rail['axial_plateau_fraction'])-.6),
            abs(float(rail['transverse_plateau_fraction'])-.65)])
        expected_depth = np.minimum(np.minimum(rail['left_width'], rail['right_width'])*
            np.tan(np.deg2rad(40.)), rail['depth_cap'])
        rail_coefficient_errors.append(max_error(expected_depth, rail['depth']))
    rail_coefficient_error = max(rail_coefficient_errors)
    if mode == 'CONTROL':
        replay = np.zeros_like(reference); fields = {}
    elif mode == 'PREVIOUS':
        replay, weights = study.proposal(reference, chart, guides, mode='GROOVE', depth_ratio=.28)
        fields = dict(region_weights=weights)
    else:
        replay, fields = study.wall_fold.apply_wall(reference, chart, rails, mode=mode)
    existing = study.previous.anchor.t.prior.helpers.existing
    existing.reflect(replay, chart, existing.symmetry(chart))
    if case == 'GATE_LINTEL':
        gate_members.reflect_axial_delta(replay, chart)
    field_errors = {}
    for key, value in fields.items():
        if key not in operation:
            raise ValueError('Saved operation lacks replay field '+key)
        if np.asarray(value).dtype.kind in 'OUS':
            if not np.array_equal(value, operation[key]):
                raise ValueError('Saved categorical field differs: '+key)
        else:
            field_errors[key] = max_error(value, operation[key])
    delta_error = max_error(replay, operation['delta'])
    control_error = max_error(reference+replay, control['xyz'])
    chart_error = max_error(chart, control['chart'])
    mesh, native_chart, _ = study.previous.anchor.t.load(folder)
    native = study.previous.anchor.t.growth.native(mesh)
    native_error = max_error(native.xyz, geometry['xyz'])
    native_faces_equal = bool(np.array_equal(native.faces[:, :3], geometry['faces']))
    physical = trimesh.Trimesh(geometry['xyz'], geometry['faces'], process=False)
    integrity = dict(finite=bool(np.isfinite(geometry['xyz']).all()),
        closed=bool(physical.is_watertight), winding_consistent=bool(physical.is_winding_consistent),
        components=int(physical.body_count), minimum_triangle_area=float(physical.area_faces.min()))
    endpoint = None
    if case.startswith('GATE_'):
        kind = case.removeprefix('GATE_')
        length = gate_members.DIMENSIONS[kind]['length']
        bottom, top = np.abs(native_chart[:, 0]) < TOLERANCE, np.abs(native_chart[:, 0]-1) < TOLERANCE
        endpoint = dict(bottom_local_z_error=max_error(mesh.xyz[bottom, 2], np.zeros(bottom.sum())),
            top_local_z_error=max_error(mesh.xyz[top, 2], np.full(top.sum(), length)),
            cap_displacement_error=max_error(replay[bottom | top], np.zeros_like(replay[bottom | top])),
            interpretation='Member endpoint planes only; no global surface-clearance claim')
    errors = [delta_error, control_error, chart_error, native_error, rail_coefficient_error, *field_errors.values()]
    if endpoint:
        errors += [endpoint[key] for key in ('bottom_local_z_error', 'top_local_z_error', 'cap_displacement_error')]
    passed = bool(max(errors) < TOLERANCE and native_faces_equal and
        integrity['finite'] and integrity['closed'] and integrity['winding_consistent'] and
        integrity['components'] == 1 and integrity['minimum_triangle_area'] > TOLERANCE)
    return dict(path=str(folder.relative_to(root)), input_case=case, candidate=mode, passed=passed,
        replay_delta_max_error=delta_error, replay_control_max_error=control_error,
        chart_max_error=chart_error, native_xyz_max_error=native_error,
        native_triangle_arrays_identical=native_faces_equal,
        saved_rail_coefficient_and_depth_formula_max_error=rail_coefficient_error,
        replay_field_max_errors=field_errors, integrity=integrity, endpoints=endpoint,
        role_constraint=metadata['axial_role_constraint'],
        maximum_applied_displacement=float(np.linalg.norm(operation['delta'], axis=1).max())), metadata


def verify_assembly(root, mode):
    folder = root/'assemblies'/mode
    saved = arrays(folder/'geometry.npz')
    metadata = json.loads((folder/'assembly.json').read_text(encoding='utf8'))
    parts = {}
    for kind in ('COLUMN', 'LINTEL'):
        source = arrays(root/mode/('GATE_'+kind)/'G03/geometry.npz')
        parts[kind] = source['xyz'], source['faces']
    rebuilt = gate_members.assemble(parts)
    xyz_error = max_error(rebuilt['xyz'], saved['xyz'])
    faces_equal = bool(np.array_equal(rebuilt['faces'], saved['faces']))
    labels_equal = bool(np.array_equal(rebuilt['face_parts'], saved['face_member']))
    transforms = gate_members.member_transforms()
    transform_error = max(max_error(value, metadata['transforms'][key]) for key, value in transforms.items())
    determinants = {key: float(np.linalg.det(value[:3, :3])) for key, value in transforms.items()}
    proper = all(abs(value-1.) < TOLERANCE for value in determinants.values())
    physical = trimesh.Trimesh(saved['xyz'], saved['faces'], process=False)
    integrity = dict(components=int(physical.body_count), closed=bool(physical.is_watertight),
        winding_consistent=bool(physical.is_winding_consistent), finite=bool(np.isfinite(saved['xyz']).all()),
        minimum_triangle_area=float(physical.area_faces.min()))
    reflection = global_lr(saved['xyz'], saved['faces'])
    nominal_beam_bottom = float((transforms['LINTEL'] @ np.array([-.45, 0., 0., 1.]))[2])
    nominal_gap = nominal_beam_bottom-gate_members.DIMENSIONS['COLUMN']['length']
    gap_error = abs(nominal_gap-metadata['nominal_seat_gap'])
    passed = bool(max(xyz_error, transform_error, gap_error) < TOLERANCE and faces_equal and labels_equal and
        proper and reflection['passed'] and integrity['components'] == 3 and integrity['closed'] and
        integrity['winding_consistent'] and integrity['finite'] and integrity['minimum_triangle_area'] > TOLERANCE)
    return dict(path=str(folder.relative_to(root)), candidate=mode, passed=passed,
        reassembly_xyz_max_error=xyz_error, reassembly_triangle_arrays_identical=faces_equal,
        face_member_labels_identical=labels_equal, transform_max_error=transform_error,
        transform_determinants=determinants, all_transforms_proper=proper,
        integrity=integrity, global_left_right=reflection,
        nominal_seat_gap=nominal_gap, nominal_gap_max_error=gap_error,
        gap_scope='Nominal carrier seats only; deformed closest distances, intersections, bearing and load path NOT_CHECKED')


def verify_sources(root):
    result = []
    for kind in ('COLUMN', 'LINTEL'):
        for stage in (0, 2):
            folder = root/'sources'/kind/f'G{stage:02}'
            saved = arrays(folder/'control_quad.npz')
            if stage == 0:
                mesh, chart = gate_members.build_carrier(kind)
                tags = np.zeros(len(chart))
            else:
                mesh, chart, tags, _ = gate_members.build_source(kind)
            errors = {key: max_error(saved[key], value) for key, value in
                dict(xyz=mesh.xyz, chart=chart, rest=mesh.rest, memory=tags).items()}
            discrete_equal = all(np.array_equal(saved[key], value) for key, value in
                dict(faces=mesh.faces, classes=mesh.classes, anchors=mesh.anchors).items())
            generation_equal = int(saved['generation']) == stage == mesh.generation
            result.append(dict(path=str(folder.relative_to(root)), kind=kind, stage=stage,
                maximum_errors=errors, discrete_arrays_identical=bool(discrete_equal),
                generation_identical=bool(generation_equal),
                passed=bool(max(errors.values()) < TOLERANCE and discrete_equal and generation_equal)))
    return result


def verify(root, *, source_replay=True):
    root = Path(root).resolve()
    parents, assemblies, metadata, issues = [], [], [], []
    for mode in MODES:
        for case in CASES:
            try:
                record, receipt = verify_parent(root, case, mode)
                parents.append(record); metadata.append(receipt)
            except Exception as error:
                issues.append(dict(path=f'{mode}/{case}/G03', error=str(error)))
        try:
            assemblies.append(verify_assembly(root, mode))
        except Exception as error:
            issues.append(dict(path=f'assemblies/{mode}', error=str(error)))
    source_records = []
    if source_replay:
        try:
            source_records = verify_sources(root)
        except Exception as error:
            issues.append(dict(path='sources', error=str(error)))
    recipes_equal = bool(metadata and all(recipe_without_candidate(item) == recipe_without_candidate(metadata[0]) for item in metadata))
    seeds_equal = bool(metadata and all(item['parent_region_seeds'] == metadata[0]['parent_region_seeds'] for item in metadata))
    common = dict(recipe_identical_across_four_inputs=recipes_equal,
        parent_seed_coefficients_identical=seeds_equal,
        member_role_exception='GATE_LINTEL alone adds explicit constructive s->1-s reflection after the same wall operator',
        replay_constants=dict(previous_depth_ratio=.28, wall_strength=1., wall_angle_degrees=40.,
            shoulder_fraction=.55, axial_plateau_fraction=.6, transverse_plateau_fraction=.65))
    skipped = [str(path.relative_to(root)) for path in sorted(root.rglob('G04')) if path.is_dir()]
    complete = len(parents) == len(CASES)*len(MODES) and len(assemblies) == len(MODES)
    passed = bool(complete and not issues and recipes_equal and seeds_equal and
        all(record['passed'] for record in parents+assemblies+source_records))
    return dict(passed=passed, tolerance=TOLERANCE,
        scope='Saved parent G3 operation replay, native reconstruction, new source determinism, and actual three-part gate geometry/reflection',
        excluded_scope=['G04/CHILD continuation', 'self-intersection', 'global deformed clearance',
            'fabrication', 'structural connections', 'aesthetic success'],
        expected_parent_states=16, verified_parent_states=len(parents),
        verified_assemblies=len(assemblies), common_coefficients=common,
        maximum_operation_replay_error=max((item['replay_delta_max_error'] for item in parents), default=None),
        maximum_control_replay_error=max((item['replay_control_max_error'] for item in parents), default=None),
        maximum_native_reconstruction_error=max((item['native_xyz_max_error'] for item in parents), default=None),
        parent_states=parents, assemblies=assemblies, source_replay=source_records,
        skipped_g04_directories=skipped, issues=issues)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--skip-source-replay', action='store_true')
    args = parser.parse_args()
    receipt = verify(args.root, source_replay=not args.skip_source_replay)
    destination = args.output or args.root/'verification.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(receipt, indent=2), encoding='utf8')
    print(json.dumps({key: receipt[key] for key in ('passed', 'verified_parent_states', 'verified_assemblies',
        'maximum_operation_replay_error', 'maximum_control_replay_error', 'maximum_native_reconstruction_error', 'issues')}, indent=2))
    raise SystemExit(0 if receipt['passed'] else 1)
