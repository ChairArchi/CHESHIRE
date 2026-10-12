"""One symmetric lintel redevelopment over the accepted fixed B gate layout.

The two actual current WALL columns are only uniformly displayed and translated.
The lintel is a new carrier derived from the earlier actual SPAN G2 control:
paired axial-reflection averaging, one fixed section/length transform, then a
fresh measurement and the existing wall operator. Pair averaging may soften
asymmetric macro features. The final displacement explicitly copies its first
half to the second; that role constraint is not automatic symmetry discovery.

PLAIN is a box baseline, CONTROL is the inactive refined symmetric carrier,
and WALL redevelops that exact carrier. No variant-specific envelope scaling,
fractal-field pass, physical joint, or fabrication validation is added.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
import sys

import numpy as np
from scipy.spatial import cKDTree
import trimesh

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location('symmetric_lintel_existing_study', HERE/'study.py')
study = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(study)
import gate_layout

DEFAULT_COLUMN = HERE.parents[1]/'output/fold_visible_gate_20261012/WALL/SPAN/G03/geometry.npz'
TOLERANCE = 1e-12
RECIPE = dict(angle_degrees=40., shoulder_fraction=.55, wall_strength=1.,
    axial_plateau_fraction=.6, transverse_plateau_fraction=.65,
    gate_opening_in_column_widths=2.6, overhang_in_column_widths=.15,
    column_display_height=3., nominal_seat_gap=.04,
    source_symmetry='Axial pair average of actual incoming G2 positions and their reflected counterparts',
    displacement_symmetry='Constructive first-half axial copy after existing XY reflection',
    envelope='One fixed source-derived transform; no WALL variant rescaling')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def arrays(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key].copy() for key in data.files}


def error(left, right):
    if np.shape(left) != np.shape(right):
        raise ValueError('Mismatched verification array shapes.')
    return float(np.max(np.abs(np.asarray(left)-np.asarray(right)), initial=0.))


def axial_pairs(chart):
    target = np.asarray(chart).copy(); target[:, 0] = 1.-target[:, 0]
    distance, ids = cKDTree(chart).query(target)
    if distance.max() > TOLERANCE or not np.array_equal(ids[ids], np.arange(len(ids))):
        raise ValueError('Exact involutive material s->1-s correspondence required.')
    return ids, float(distance.max())


def copy_axial_delta(delta, chart, ids=None):
    ids = axial_pairs(chart)[0] if ids is None else ids
    second = chart[:, 0] > .5+TOLERANCE
    delta[second] = delta[ids[second]]*[1., 1., -1.]
    delta[np.abs(chart[:, 0]-.5) <= TOLERANCE, 2] = 0.
    return delta


def _cycles(triangles):
    start = np.argmin(triangles, axis=1)
    cyclic = triangles[np.arange(len(triangles))[:, None], (start[:, None]+np.arange(3)) % 3]
    return cyclic[np.lexsort((cyclic[:, 2], cyclic[:, 1], cyclic[:, 0]))]


def reflection(xyz, triangles, axis=0, plane=0.):
    target = xyz.copy(); target[:, axis] = 2*plane-target[:, axis]
    distance, ids = cKDTree(xyz).query(target)
    involutive = bool(np.array_equal(ids[ids], np.arange(len(ids))))
    triangle_match = bool(np.array_equal(_cycles(triangles), _cycles(ids[triangles][:, [0, 2, 1]])))
    return dict(axis=axis, plane=plane, maximum_xyz_error=float(distance.max()),
        pair_map_involutive=involutive, reflected_oriented_triangle_sets_identical=triangle_match,
        passed=bool(distance.max() < TOLERANCE and involutive and triangle_match))


def geometry_checks(xyz, faces, *, components):
    actual = trimesh.Trimesh(xyz, faces, process=False)
    checks = dict(finite=bool(np.isfinite(xyz).all()), components=int(actual.body_count),
        watertight=bool(actual.is_watertight), winding_consistent=bool(actual.is_winding_consistent),
        minimum_triangle_area=float(actual.area_faces.min()), signed_volume=float(actual.volume))
    checks['passed'] = bool(checks['finite'] and checks['components'] == components and
        checks['watertight'] and checks['winding_consistent'] and
        checks['minimum_triangle_area'] > TOLERANCE and checks['signed_volume'] > 0.)
    return checks


def fixed_layout(column):
    data = arrays(column); xyz, faces = data['xyz'], data['faces']
    bbox = np.array([xyz.min(0), xyz.max(0)])
    scale = RECIPE['column_display_height']/np.ptp(xyz[:, 2])
    width, depth = np.ptp(xyz[:, :2], axis=0)*scale
    opening = RECIPE['gate_opening_in_column_widths']*width
    centre_distance = opening+width
    overhang = RECIPE['overhang_in_column_widths']*width
    length = opening+2*width+2*overhang
    transforms = {name: gate_layout.uniform_column_transform(bbox, 3., centre)
        for name, centre in [('LEFT', -centre_distance/2), ('RIGHT', centre_distance/2)]}
    # Beam local Z follows world X; local X follows world Z. This is proper.
    beam = np.eye(4); beam[:3, :3] = [[0, 0, 1], [0, -1, 0], [1, 0, 0]]
    beam[:3, 3] = [-length/2, 0., 3.+RECIPE['nominal_seat_gap']+width/2]
    return dict(source_xyz=xyz, source_faces=faces, column_transforms=transforms,
        beam_transform=beam, uniform_column_scale=float(scale), width=float(width),
        depth=float(depth), length=float(length), opening=float(opening),
        column_center_distance=float(centre_distance), overhang=float(overhang))


def plain_box(width, depth, length):
    """Symmetric quad-centre fans avoid a reflected diagonal mismatch."""
    xyz, _ = gate_layout.box(width, depth, length, 0.)
    quads = np.array([[3, 2, 1, 0], [4, 5, 6, 7], [0, 1, 5, 4],
        [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]], np.int64)
    centres = np.arange(len(quads))+len(xyz)
    triangles = np.stack([quads, np.roll(quads, -1, axis=1),
        np.broadcast_to(centres[:, None], quads.shape)], axis=2).reshape(-1, 3)
    return np.vstack([xyz, xyz[quads].mean(axis=1)]), triangles


def make_source(source, layout):
    mesh, chart, tags = study.previous.anchor.t.load(source)
    if mesh.generation != 2:
        raise ValueError('An actual saved G2 source control is required.')
    original = mesh.xyz.copy()
    ids, pair_error = axial_pairs(chart)
    if not np.array_equal(mesh.classes, mesh.classes[ids]):
        raise ValueError('Axial material pairs have different native point classes.')
    plane = float((original[:, 2].min()+original[:, 2].max())/2)
    counterpart = original[ids]*[1., 1., -1.]+[0., 0., 2*plane]
    averaged = .5*(original+counterpart)
    bbox = np.array([averaged.min(0), averaged.max(0)])
    dimensions = np.array([layout['width'], layout['depth'], layout['length']])
    factors = dimensions/np.ptp(averaged, axis=0)
    transform = np.eye(4); transform[:3, :3] = np.diag(factors)
    transform[:3, 3] = -bbox.mean(0)*factors+[0., 0., dimensions[2]/2]
    normalized = gate_layout.apply_transform(averaged, transform)
    mesh.xyz = normalized.copy()
    existing = study.previous.anchor.t.prior.helpers.existing
    existing.reflect(mesh.xyz, chart, existing.symmetry(chart))
    # This new carrier has a declared local rest association of its own.
    mesh.rest = mesh.xyz.copy()
    source_metadata = json.loads((Path(source)/'generation.json').read_text(encoding='utf8'))
    originals = source_metadata.get('event_bank', source_metadata.get('authored_return_events'))
    if len(originals) != 2:
        raise ValueError('Expected the two declared preserved macro search seeds.')
    bank = []
    for parent in originals:
        bank.append(copy.deepcopy(parent))
        mirrored = copy.deepcopy(parent)
        mirrored.update(id='AXIAL_MIRROR_'+parent['id'], mirrored_from=parent['id'],
            height=1.-parent['height'], sweep=-parent['sweep'])
        bank.append(mirrored)
    provenance = dict(source_control_sha256=digest(Path(source)/'control_quad.npz'),
        source_generation_metadata_sha256=digest(Path(source)/'generation.json'),
        source_generation=2, source_identity='Actual earlier SPAN G2; not the finished WALL G3 column',
        source_field_passes_in_history=source_metadata.get('field_passes_total'), added_field_passes=0,
        symmetry_operation='Pair averaging explicitly permitted for this new lintel carrier',
        source_axial_reflection_plane=plane, material_pair_max_error=pair_error,
        fixed_member_dimension_transform=transform.tolist(),
        target_local_extent=dimensions.tolist(),
        tradeoff='Pair averaging softens mismatched macro folds; final first-half delta copy may create a central crease and does not promise C1 continuity',
        rest_association='Reset to the explicitly reconstructed G2 carrier positions',
        parent_region_seeds=bank, original_parent_region_seeds=originals,
        search_symmetry='Mirrored authored search bands; final symmetry is additionally enforced by a declared first-half copy')
    construction = dict(original_xyz=original, reflected_counterpart_xyz=counterpart,
        pair_average_xyz=averaged, dimension_transformed_xyz=normalized,
        source_xyz=mesh.xyz.copy(), chart=chart, source_axial_pair_ids=ids,
        fixed_dimension_transform=transform, averaged_source_bbox=bbox)
    return mesh, chart, tags, provenance, construction


def save_member(folder, mesh, chart, tags, metadata, *, operation=None, guides=(), rails=()):
    folder.mkdir(parents=True)
    native = study.previous.anchor.t.growth.native(mesh)
    triangles = native.faces[:, :3]
    pchart = np.concatenate([chart, study.previous.anchor.t.face_values(mesh, chart)])
    checks = geometry_checks(native.xyz, triangles, components=1)
    checks['reflections'] = [reflection(native.xyz, triangles, axis=axis,
        plane=metadata['target_local_extent'][2]/2 if axis == 2 else 0.) for axis in (0, 1, 2)]
    checks['passed'] &= all(item['passed'] for item in checks['reflections'])
    np.savez_compressed(folder/'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces,
        chart=chart, classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors,
        generation=np.array(mesh.generation), surface=np.array(mesh.surface), memory=tags)
    np.savez_compressed(folder/'geometry.npz', xyz=native.xyz, faces=triangles)
    if operation is not None:
        np.savez_compressed(folder/'operation_fields.npz', **operation)
    for prefix, records in (('guide', guides), ('rails', rails)):
        for index, record in enumerate(records):
            np.savez_compressed(folder/f'{prefix}_{index}.npz', **record)
    metadata = dict(metadata, actual_local_bbox=[native.xyz.min(0).tolist(), native.xyz.max(0).tolist()],
        actual_local_extent=np.ptp(native.xyz, axis=0).tolist(), control_vertices=len(mesh.xyz),
        physical_vertices=len(native.xyz), triangles=len(triangles), checks=checks,
        quick_integrity='PASS' if checks['passed'] else 'FAILED_PRESERVED')
    (folder/'generation.json').write_text(json.dumps(metadata, indent=2), encoding='utf8')
    if not checks['passed']:
        raise ValueError('Member geometry failure preserved: '+str(folder))
    return native.xyz, triangles, metadata


def assemble(root, mode, layout, beam_xyz, beam_faces, source_column):
    source_xyz, source_faces = layout['source_xyz'], layout['source_faces']
    transformed = {name: gate_layout.apply_transform(source_xyz, transform)
        for name, transform in layout['column_transforms'].items()}
    beam = gate_layout.apply_transform(beam_xyz, layout['beam_transform'])
    count = len(source_xyz)
    xyz = np.vstack([transformed['LEFT'], transformed['RIGHT'], beam])
    faces = np.vstack([source_faces, source_faces+count, beam_faces+2*count])
    labels = np.r_[np.zeros(len(source_faces), np.int8), np.ones(len(source_faces), np.int8),
        np.full(len(beam_faces), 2, np.int8)]
    checks = geometry_checks(xyz, faces, components=3)
    checks['global_left_right'] = reflection(xyz, faces, axis=0)
    checks['source_column_max_error'] = max(error(transformed[name],
        gate_layout.apply_transform(source_xyz, transform)) for name, transform in layout['column_transforms'].items())
    checks['column_triangle_arrays_identical'] = bool(np.array_equal(faces[:len(source_faces)], source_faces) and
        np.array_equal(faces[len(source_faces):2*len(source_faces)]-count, source_faces))
    checks['passed'] &= checks['global_left_right']['passed'] and checks['source_column_max_error'] == 0. and checks['column_triangle_arrays_identical']
    folder = root/mode; folder.mkdir(parents=True)
    np.savez_compressed(folder/'geometry.npz', xyz=xyz, faces=faces, face_member=labels)
    metadata = dict(candidate=mode, units='metres for review only', recipe=RECIPE,
        fixed_layout='Accepted B; no new proportion comparison',
        source_column=str(source_column), source_column_sha256=digest(source_column),
        column_transforms={key: value.tolist() for key, value in layout['column_transforms'].items()},
        lintel_transform=layout['beam_transform'].tolist(),
        target_lintel_length=layout['length'], target_lintel_vertical_section=layout['width'],
        target_lintel_depth=layout['depth'], actual_lintel_world_extent=np.ptp(beam, axis=0).tolist(),
        target_cross_section_ratio=layout['width']/layout['depth'],
        actual_lintel_cross_section_ratio=float(np.ptp(beam[:, 2])/np.ptp(beam[:, 1])),
        actual_column_display_height=3., opening_width=layout['opening'],
        nominal_seat_gap=.04, actual_bbox_vertical_gap=float(beam[:, 2].min()-max(
            transformed['LEFT'][:, 2].max(), transformed['RIGHT'][:, 2].max())),
        overhang_each_side=layout['overhang'], part_names=['LEFT', 'RIGHT', 'LINTEL'],
        part_vertex_ranges=dict(LEFT=[0, count], RIGHT=[count, 2*count], LINTEL=[2*count, len(xyz)]),
        column_operation='Only the accepted common uniform display scale and translations; actual geometry and triangles unchanged',
        lintel_operation=('Plain corrected-section box baseline' if mode == 'PLAIN' else
            'New symmetric source, inactive refinement' if mode == 'CONTROL' else 'New symmetric source, same measured wall operator'),
        envelope='One source/control transform only; WALL is not rescaled to hide resulting depth change',
        self_intersection='NOT_CHECKED_EXPLORATION', structural_connections='NOT_IMPLEMENTED',
        seating='BBox gap only; source column endpoints are not certified planar bearing faces',
        fabrication='NOT_CHECKED', checks=checks, quick_integrity='PASS' if checks['passed'] else 'FAILED_PRESERVED')
    (folder/'assembly.json').write_text(json.dumps(metadata, indent=2), encoding='utf8')
    if not checks['passed']:
        raise ValueError('Assembly geometry failure preserved: '+str(folder))
    print('FIXED_GATE', mode, metadata['quick_integrity'], 'column_error', checks['source_column_max_error'],
        'LR', checks['global_left_right']['maximum_xyz_error'], 'lintel extent', metadata['actual_lintel_world_extent'], flush=True)
    return metadata


def replay_member(folder):
    operation = arrays(folder/'operation_fields.npz')
    metadata = json.loads((folder/'generation.json').read_text(encoding='utf8'))
    mode = metadata['candidate']
    rails = [arrays(path) for path in sorted(folder.glob('rails_*.npz'))]
    if mode == 'CONTROL':
        raw = np.zeros_like(operation['reference_xyz'])
    else:
        raw, _ = study.wall_fold.apply_wall(operation['reference_xyz'], operation['chart'], rails, mode='WALL', strength=1.)
    raw_error = error(raw, operation['raw_delta'])
    existing = study.previous.anchor.t.prior.helpers.existing
    existing.reflect(raw, operation['chart'], existing.symmetry(operation['chart']))
    xy_error = error(raw, operation['pre_axial_delta'])
    copy_axial_delta(raw, operation['chart'], operation['axial_pair_ids'])
    delta_error = error(raw, operation['delta'])
    mesh, chart, _ = study.previous.anchor.t.load(folder)
    control_error = error(mesh.xyz, operation['reference_xyz']+raw)
    native = study.previous.anchor.t.growth.native(mesh)
    geometry = arrays(folder/'geometry.npz')
    native_error = error(native.xyz, geometry['xyz'])
    triangles_equal = bool(np.array_equal(native.faces[:, :3], geometry['faces']))
    passed = max(raw_error, xy_error, delta_error, control_error, native_error) < TOLERANCE and triangles_equal
    return dict(candidate=mode, passed=bool(passed), raw_delta_max_error=raw_error,
        pre_axial_delta_max_error=xy_error, final_delta_max_error=delta_error,
        control_max_error=control_error, native_xyz_max_error=native_error,
        native_triangle_arrays_identical=triangles_equal)


def generate(root, *, column=DEFAULT_COLUMN, source_g2=None):
    root, column = Path(root).resolve(), Path(column).resolve()
    source = Path(source_g2).resolve() if source_g2 is not None else study.previous.SOURCES['SPAN']
    if root.exists():
        raise FileExistsError('Existing fixed-gate result preserved: '+str(root))
    layout = fixed_layout(column)
    mesh, chart, tags, provenance, construction = make_source(source, layout)
    root.mkdir(parents=True)
    original_folder = root/'lintel/ORIGINAL_G02'; original_folder.mkdir(parents=True)
    for name in ('control_quad.npz', 'generation.json'):
        shutil.copy2(source/name, original_folder/name)
    if digest(original_folder/'control_quad.npz') != provenance['source_control_sha256']:
        raise ValueError('Exact preserved source control copy differs.')
    source_folder = root/'lintel/SOURCE/G02'
    save_member(source_folder, mesh, chart, tags, dict(provenance, candidate='SOURCE', recipe=RECIPE))
    np.savez_compressed(source_folder/'construction.npz', **construction)
    sampler = study.native_sampler(mesh, chart)
    guides = [study.measure_longitudinal(sampler, parent, shoulder_fraction=.55, frame_mode='region')
        for parent in provenance['parent_region_seeds']]
    rails = [study.wall_fold.measure_rails(sampler, guide, angle_degrees=40.) for guide in guides]
    out, outchart, outtags, operator = study.previous.anchor.t.memory.refine(mesh, chart, tags)
    reference = out.xyz.copy()
    out_pairs, correspondence_error = axial_pairs(outchart)
    beam_records, assembly_records = [], []
    plain_xyz, plain_faces = plain_box(layout['width'], layout['depth'], layout['length'])
    plain_folder = root/'lintel/PLAIN'; plain_folder.mkdir(parents=True)
    np.savez_compressed(plain_folder/'geometry.npz', xyz=plain_xyz, faces=plain_faces)
    (plain_folder/'generation.json').write_text(json.dumps(dict(candidate='PLAIN', operation='Plain corrected-section box baseline',
        target_local_extent=[layout['width'], layout['depth'], layout['length']],
        added_field_passes=0, new_column_geometry=False), indent=2), encoding='utf8')
    assembly_records.append(assemble(root, 'PLAIN', layout, plain_xyz, plain_faces, column))
    for mode in ('CONTROL', 'WALL'):
        if mode == 'CONTROL':
            raw = np.zeros_like(reference); fields = {}
        else:
            raw, fields = study.wall_fold.apply_wall(reference, outchart, rails, mode='WALL', strength=1.)
        raw_delta = raw.copy()
        existing = study.previous.anchor.t.prior.helpers.existing
        existing.reflect(raw, outchart, existing.symmetry(outchart))
        pre_axial = raw.copy()
        copy_axial_delta(raw, outchart, out_pairs)
        out.xyz = reference+raw
        metadata = dict(provenance, candidate=mode, recipe=RECIPE, source_folder=str(source_folder),
            material_axial_pair_error=correspondence_error,
            maximum_displacement=float(np.linalg.norm(raw, axis=1).max()),
            source_refinement='Existing inactive surface-preserving Task36 split from new symmetric SOURCE G2',
            final_axial_constraint='Copy s<=0.5 displacement to s>0.5 and reverse its local Z component; centre-plane Z displacement zero',
            final_envelope_policy='Same fixed source/control transform; no WALL variant rescaling')
        operation = dict(reference_xyz=reference, raw_delta=raw_delta, pre_axial_delta=pre_axial,
            delta=raw, chart=outchart, axial_pair_ids=out_pairs,
            input_edges=operator['input_edges'], parent_face=operator['parent_face'], **fields)
        folder = root/'lintel'/mode/'G03'
        xyz, faces, receipt = save_member(folder, out, outchart, outtags, metadata,
            operation=operation, guides=guides, rails=rails)
        beam_records.append(receipt)
        assembly_records.append(assemble(root, mode, layout, xyz, faces, column))
    replay = [replay_member(root/'lintel'/mode/'G03') for mode in ('CONTROL', 'WALL')]
    receipt = dict(passed=bool(all(item['passed'] for item in replay)),
        scope='Saved lintel operation replay plus native reconstruction, source correspondence, exact fixed-column transforms, and actual oriented gate reflection',
        source_preserved_byte_identical=True, source_control_sha256=provenance['source_control_sha256'],
        fixed_column_geometry_sha256=digest(column), replay=replay,
        assemblies=[dict(candidate=item['candidate'], checks=item['checks']) for item in assembly_records],
        excluded=['self-intersection', 'joint bearing', 'fabrication', 'C1 central-seam continuity', 'aesthetic success'])
    (root/'verification.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
    summary = dict(recipe=RECIPE, source=provenance, fixed_column=str(column),
        fixed_column_geometry_sha256=digest(column), fixed_column_uniform_display_scale=layout['uniform_column_scale'],
        opening_width=layout['opening'], lintel_length=layout['length'],
        requested_lintel_vertical_section=layout['width'], requested_lintel_depth=layout['depth'],
        lintel_results=[dict(candidate=item['candidate'], actual_local_extent=item['actual_local_extent'],
            maximum_displacement=item['maximum_displacement']) for item in beam_records],
        assemblies=[dict(candidate=item['candidate'], path=str(root/item['candidate']),
            actual_lintel_world_extent=item['actual_lintel_world_extent'],
            actual_cross_section_ratio=item['actual_lintel_cross_section_ratio']) for item in assembly_records],
        tradeoff=provenance['tradeoff'], verification_passed=receipt['passed'])
    (root/'SUMMARY.json').write_text(json.dumps(summary, indent=2), encoding='utf8')
    shutil.copy2(__file__, root/'symmetric_lintel.py')
    print('LINTEL_REPLAY', json.dumps(replay), flush=True)
    if not receipt['passed']:
        raise ValueError('Saved lintel replay failure preserved.')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--column', type=Path, default=DEFAULT_COLUMN)
    parser.add_argument('--source-g2', type=Path)
    args = parser.parse_args()
    generate(args.root, column=args.column, source_g2=args.source_g2)
