"""Bounded finite-Mandelbulb height relief on actual current WALL columns.

The atlas is the upper occupied envelope of a finite spherical-power-8 escape
test. Surface-local colonies project this envelope as actual XYZ relief. This
is a height-mapped interpretation, not a full embedded Mandelbulb volume, an
exact infinite-set boundary, random noise, or the old nearest-outside operator.
Deterministic irregular centres and two physical scales cover broad body panels.
Each colony pools directions from the actual incoming native surface; source
XYZ is never smoothed. No ownership/core corridor or intersection gate is used.
"""
from pathlib import Path
import argparse
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
_spec = importlib.util.spec_from_file_location('bulb_finish_current_wall', HERE/'study.py')
study = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(study)
_field_spec = importlib.util.spec_from_file_location('bulb_finish_existing_escape',
    HERE.parent/'iaac_mandelbrot_20261011/study.py')
field = importlib.util.module_from_spec(_field_spec); _field_spec.loader.exec_module(field)

ATLAS_RECIPE = dict(power=8, iterations=10, bailout=4., xy_resolution=129,
    z_resolution=96, xy_extent=1.2, maximum_z=1.4,
    interpretation='Top finite occupied height along +Z; compact projected height relief, not a full 3D fractal volume')
VARIANTS = dict(
    COARSE_CLUSTER=dict(primary_radius=.30, primary_amplitude=.16,
        secondary_radius=.11, secondary_amplitude=.055, maximum_height=.22,
        primary_count=70, minimum_spacing_in_radii=1.35),
    BOLD_DETAIL=dict(primary_radius=.23, primary_amplitude=.20,
        secondary_radius=.10, secondary_amplitude=.08, maximum_height=.28,
        primary_count=110, minimum_spacing_in_radii=1.35))
COMMON = dict(candidate_samples=640, body_material_range=[.10, .90],
    secondary_per_primary=2, secondary_offset_in_primary_radii=.65,
    normal_pool_radius_in_colony_radii=1., normal_agreement_minimum=.10,
    normal_pool_agreement_minimum=.25, slab_support_in_radii=1.,
    primary_footprint_diameters=[.60, .46], secondary_footprint_diameters=[.22, .20],
    deep_core_exclusion=False, source_xyz_smoothing=False,
    symmetry='Constructive material X/Y reflection after relief placement')


def unit(value):
    value = np.asarray(value, float)
    length = np.linalg.norm(value, axis=-1, keepdims=True)
    return np.divide(value, length, out=np.zeros_like(value), where=length > 1e-14)


def compact(distance):
    q = np.clip(np.abs(distance), 0., 1.)
    return (1.-q*q)**2


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_arrays(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key].copy() for key in data.files}


def build_atlas(recipe=ATLAS_RECIPE):
    axis = np.linspace(-recipe['xy_extent'], recipe['xy_extent'], recipe['xy_resolution'])
    z_axis = np.linspace(0., recipe['maximum_z'], recipe['z_resolution'])
    x, y = np.meshgrid(axis, axis, indexing='ij')
    points = np.stack(np.broadcast_arrays(x[:, :, None], y[:, :, None], z_axis[None, None]), axis=-1).reshape(-1, 3)
    membership = np.empty(len(points), bool)
    for start in range(0, len(points), 180000):
        membership[start:start+180000] = field.escape_field(points[start:start+180000],
            power=recipe['power'], iterations=recipe['iterations'], bailout=recipe['bailout'])[2]
    occupied = membership.reshape(len(axis), len(axis), len(z_axis))
    if occupied[:, :, -1].any():
        raise ValueError('Atlas upper envelope reaches its declared top sampling boundary.')
    height = np.max(np.where(occupied, z_axis[None, None], 0.), axis=2)
    if height.max() <= 0:
        raise ValueError('Empty finite Mandelbulb height atlas.')
    return dict(axis=axis, z_axis=z_axis, finite_membership=occupied,
        height_raw=height, height=height/height.max())


def sample_atlas(atlas, u, v):
    axis = atlas['axis']; height = atlas['height']
    u, v = np.asarray(u), np.asarray(v)
    a = (u-axis[0])/(axis[-1]-axis[0])*(len(axis)-1)
    b = (v-axis[0])/(axis[-1]-axis[0])*(len(axis)-1)
    outside = (a < 0) | (b < 0) | (a > len(axis)-1) | (b > len(axis)-1)
    a, b = np.clip(a, 0, len(axis)-1), np.clip(b, 0, len(axis)-1)
    i, j = np.floor(a).astype(int), np.floor(b).astype(int)
    i1, j1 = np.minimum(i+1, len(axis)-1), np.minimum(j+1, len(axis)-1)
    fa, fb = a-i, b-j
    result = ((1-fa)*(1-fb)*height[i, j]+fa*(1-fb)*height[i1, j]+
        (1-fa)*fb*height[i, j1]+fa*fb*height[i1, j1])
    return np.where(outside, 0., result)


def _frame(normal):
    axis = np.array([0., 0., 1.]) if abs(normal[2]) < .90 else np.array([1., 0., 0.])
    tangent = unit(axis-normal*np.dot(axis, normal))
    return tangent, unit(np.cross(normal, tangent))


def make_colonies(mesh, chart, variant):
    """Actual-surface centres with physical spacing, without random numbers."""
    t = study.previous.anchor.t
    native = t.growth.native(mesh); triangles = native.faces[:, :3]
    physical = trimesh.Trimesh(native.xyz, triangles, process=False)
    normals = physical.vertex_normals.copy()
    pchart = np.concatenate([chart, t.face_values(mesh, chart)])
    canonical = ((pchart[:, 1] >= -1e-12) & (pchart[:, 2] >= -1e-12) &
        (pchart[:, 0] >= .08) & (pchart[:, 0] <= .92) &
        (np.linalg.norm(pchart[:, 1:], axis=1) > .2))
    surface_ids = np.flatnonzero(canonical)
    tree = cKDTree(native.xyz[surface_ids])
    sampler = study.native_sampler(mesh, chart)
    count = COMMON['candidate_samples']; index = np.arange(1, count+1)
    golden = (np.sqrt(5.)-1.)/2
    uv = np.column_stack([.10+.80*np.mod(index*golden+.17, 1.),
        .035+(np.pi/2-.070)*np.mod(index*(np.sqrt(2.)-1.)+.31, 1.)])
    points, triangle_ids, barycentric = sampler.sample(uv, records=True)
    point_normals = unit(np.einsum('ni,nij->nj', barycentric, normals[triangles[triangle_ids]]))
    chosen = []
    spacing = variant['primary_radius']*variant['minimum_spacing_in_radii']
    for candidate, point in enumerate(points):
        if not chosen or np.min(np.linalg.norm(points[chosen]-point, axis=1)) >= spacing:
            chosen.append(candidate)
        if len(chosen) == variant['primary_count']:
            break
    if len(chosen) < variant['primary_count']//2:
        raise ValueError('Too few physically separated colony centres on incoming body.')
    centres, pooled, tangents, bitangents, radii, amplitudes = [], [], [], [], [], []
    levels, parent_ids, native_ids, pool_counts = [], [], [], []

    def add(point, naive, radius, amplitude, level, parent, vertex_id):
        nearby = np.asarray(tree.query_ball_point(point, radius), int)
        global_ids = surface_ids[nearby]
        keep = (normals[global_ids]@naive) > COMMON['normal_pool_agreement_minimum']
        global_ids = global_ids[keep]
        distance = np.linalg.norm(native.xyz[global_ids]-point, axis=1)
        weights = compact(distance/radius)
        normal = unit(np.sum(weights[:, None]*normals[global_ids], axis=0)) if weights.sum() else naive
        if np.linalg.norm(normal) < .5:
            normal = naive
        tangent, bitangent = _frame(normal)
        centres.append(point); pooled.append(normal); tangents.append(tangent); bitangents.append(bitangent)
        radii.append(radius); amplitudes.append(amplitude); levels.append(level)
        parent_ids.append(parent); native_ids.append(vertex_id); pool_counts.append(len(global_ids))

    for candidate in chosen:
        add(points[candidate], point_normals[candidate], variant['primary_radius'],
            variant['primary_amplitude'], 0, -1, -1)
    primary_count = len(centres)
    for parent in range(primary_count):
        for child in range(COMMON['secondary_per_primary']):
            angle = 2*np.pi*np.mod((parent+1)*golden+child*.38196601125, 1.)
            offset = COMMON['secondary_offset_in_primary_radii']*variant['primary_radius']*(
                np.cos(angle)*tangents[parent]+np.sin(angle)*bitangents[parent])
            _, local_id = tree.query(centres[parent]+offset)
            vertex_id = int(surface_ids[local_id])
            add(native.xyz[vertex_id], normals[vertex_id], variant['secondary_radius'],
                variant['secondary_amplitude'], 1, parent, vertex_id)
    return dict(centres=np.asarray(centres), normals=np.asarray(pooled), tangents=np.asarray(tangents),
        bitangents=np.asarray(bitangents), radii=np.asarray(radii), amplitudes=np.asarray(amplitudes),
        levels=np.asarray(levels), parent_ids=np.asarray(parent_ids), native_vertex_ids=np.asarray(native_ids),
        pooled_native_normal_counts=np.asarray(pool_counts), primary_sample_uv=uv[chosen],
        primary_source_xyz=points[chosen], primary_source_triangle_ids=triangle_ids[chosen],
        primary_source_barycentric=barycentric[chosen], primary_unpooled_normals=point_normals[chosen])


def apply_colonies(reference, chart, incoming_normals, colonies, atlas, maximum_height):
    """Coherent patch-normal relief; actual controls, bounded scalar amplitude."""
    reference = np.asarray(reference)
    canonical = ((chart[:, 1] >= -1e-12) & (chart[:, 2] >= -1e-12) &
        (np.linalg.norm(chart[:, 1:], axis=1) > .2))
    ids = np.flatnonzero(canonical); tree = cKDTree(reference[ids])
    numerator = np.zeros_like(reference); raw_height = np.zeros(len(reference))
    extent = float(atlas['axis'][-1])
    for centre, normal, tangent, bitangent, radius, amplitude in zip(
            colonies['centres'], colonies['normals'], colonies['tangents'], colonies['bitangents'],
            colonies['radii'], colonies['amplitudes']):
        local = np.asarray(tree.query_ball_point(centre, 1.35*radius), int)
        selected = ids[local]
        relative = reference[selected]-centre
        x, y, z = relative@tangent, relative@bitangent, relative@normal
        agreement = incoming_normals[selected]@normal
        h = amplitude*sample_atlas(atlas, extent*x/radius, extent*y/radius)
        h *= compact(np.sqrt(x*x+y*y)/radius)*compact(z/radius)
        h[agreement < COMMON['normal_agreement_minimum']] = 0.
        raw_height[selected] += h
        numerator[selected] += h[:, None]*normal
    height = np.minimum(raw_height, maximum_height)
    applied_normals = unit(numerator)
    delta = height[:, None]*applied_normals
    return delta, dict(raw_height=raw_height, height=height, pooled_direction_numerator=numerator,
        applied_normals=applied_normals)


def reflect_scalar(values, chart, pairs):
    for coordinate, ids in ((1, pairs[0]), (2, pairs[1])):
        negative = chart[:, coordinate] < -1e-12
        values[negative] = values[ids[negative]]
    return values


def save(folder, mesh, chart, tags, metadata, operation, colonies=None):
    folder.mkdir(parents=True)
    t = study.previous.anchor.t; native = t.growth.native(mesh)
    triangles = native.faces[:, :3]
    physical = trimesh.Trimesh(native.xyz, triangles, process=False)
    pchart = np.concatenate([chart, t.face_values(mesh, chart)])
    _, symmetry_error, triangle_matches = t.prior.reflection_state(native.xyz, triangles, pchart)
    actual_displacement = np.linalg.norm(operation['delta'], axis=1)
    outward_dot = np.sum(operation['delta']*operation['incoming_normals'], axis=1)
    checks = dict(finite=bool(np.isfinite(native.xyz).all()), components=int(physical.body_count),
        watertight=bool(physical.is_watertight), winding_consistent=bool(physical.is_winding_consistent),
        minimum_triangle_area=float(physical.area_faces.min()), symmetry_error=symmetry_error,
        reflected_triangle_sets_identical=triangle_matches,
        maximum_displacement=float(actual_displacement.max()), minimum_outward_normal_dot=float(outward_dot.min()),
        moved_controls=int((actual_displacement > 1e-12).sum()))
    passed = bool(checks['finite'] and checks['components'] == 1 and checks['watertight'] and
        checks['winding_consistent'] and checks['minimum_triangle_area'] > 1e-12 and
        max(symmetry_error) < 1e-9 and all(triangle_matches) and
        checks['maximum_displacement'] <= metadata['maximum_height']+1e-12)
    np.savez_compressed(folder/'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces, chart=chart,
        classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors, generation=np.array(mesh.generation),
        surface=np.array(mesh.surface), memory=tags)
    np.savez_compressed(folder/'geometry.npz', xyz=native.xyz, faces=triangles)
    np.savez_compressed(folder/'operation_fields.npz', **operation)
    if colonies is not None:
        np.savez_compressed(folder/'colonies.npz', **colonies)
    metadata = dict(metadata, checks=checks, control_vertices=len(mesh.xyz), physical_vertices=len(native.xyz),
        triangles=len(triangles), quick_integrity='PASS' if passed else 'FAILED_PRESERVED',
        self_intersection='IGNORED_EXPLORATION_PER_USER', fabrication='NOT_CHECKED')
    (folder/'generation.json').write_text(json.dumps(metadata, indent=2), encoding='utf8')
    print('BULB', metadata['input_case'], metadata['candidate'], metadata['quick_integrity'],
        'max', checks['maximum_displacement'], 'moved', checks['moved_controls'], flush=True)
    if not passed:
        raise ValueError('Basic geometry failure preserved: '+str(folder))
    return metadata


def replay(root, case, mode, detail_generation=4):
    folder = root/mode/case/f'G{detail_generation:02d}'
    operation = read_arrays(folder/'operation_fields.npz')
    metadata = json.loads((folder/'generation.json').read_text())
    if mode == 'CONTROL':
        delta = np.zeros_like(operation['reference_xyz'])
    else:
        atlas = read_arrays(root/'atlas/power8.npz')
        colonies = read_arrays(folder/'colonies.npz')
        delta, fields = apply_colonies(operation['reference_xyz'], operation['chart'],
            operation['incoming_normals'], colonies, atlas, metadata['maximum_height'])
    raw_error = float(np.abs(delta-operation['pre_reflection_delta']).max())
    existing = study.previous.anchor.t.prior.helpers.existing
    existing.reflect(delta, operation['chart'], existing.symmetry(operation['chart']))
    error = float(np.abs(delta-operation['delta']).max())
    mesh, _, _ = study.previous.anchor.t.load(folder)
    control_error = float(np.abs(mesh.xyz-operation['reference_xyz']-delta).max())
    native = study.previous.anchor.t.growth.native(mesh); geometry = read_arrays(folder/'geometry.npz')
    native_error = float(np.abs(native.xyz-geometry['xyz']).max())
    triangles_equal = bool(np.array_equal(native.faces[:, :3], geometry['faces']))
    return dict(input_case=case, candidate=mode, raw_delta_max_error=raw_error,
        delta_max_error=error, control_max_error=control_error, native_xyz_max_error=native_error,
        native_triangle_arrays_identical=triangles_equal,
        passed=bool(max(raw_error, error, control_error, native_error) < 1e-12 and triangles_equal))


def verify_source_references(root, detail_generation=4):
    """Rebuild the inactive reference from each actual WALL G3 checkpoint."""
    root = Path(root)
    records = []
    for case in ('SPAN', 'COUNTER'):
        folder = root/'CONTROL'/case/f'G{detail_generation:02d}'
        metadata = json.loads((folder/'generation.json').read_text())
        operation = read_arrays(folder/'operation_fields.npz')
        source = Path(metadata['source'])
        source_hash_matches = digest(source/'control_quad.npz') == metadata['source_control_sha256']
        mesh, chart, tags = study.previous.anchor.t.load(source)
        for _ in range(detail_generation-3):
            mesh, chart, tags, operator = study.previous.anchor.t.memory.refine(mesh, chart, tags)
        reference_error = float(np.abs(mesh.xyz-operation['reference_xyz']).max())
        control, saved_chart, saved_tags = study.previous.anchor.t.load(folder)
        chart_equal = bool(np.array_equal(chart, operation['chart']) and np.array_equal(chart, saved_chart))
        topology_equal = bool(np.array_equal(mesh.faces, control.faces))
        memory_equal = bool(np.array_equal(tags, saved_tags))
        correspondence_equal = bool(np.array_equal(operator['input_edges'], operation['input_edges']) and
            np.array_equal(operator['parent_face'], operation['parent_face']))
        native = study.previous.anchor.t.growth.native(mesh)
        saved_geometry = read_arrays(folder/'geometry.npz')
        native_error = float(np.abs(native.xyz-saved_geometry['xyz']).max())
        triangles_equal = bool(np.array_equal(native.faces[:, :3], saved_geometry['faces']))
        passed = bool(source_hash_matches and max(reference_error, native_error) < 1e-12 and
            chart_equal and topology_equal and memory_equal and correspondence_equal and triangles_equal)
        records.append(dict(input_case=case, source_control_hash_matches=source_hash_matches,
            source_refinement_reference_max_error=reference_error, native_reference_max_error=native_error,
            chart_arrays_identical=chart_equal, topology_arrays_identical=topology_equal,
            memory_arrays_identical=memory_equal, final_refinement_correspondence_identical=correspondence_equal,
            native_triangle_arrays_identical=triangles_equal, passed=passed))
    receipt = dict(passed=all(item['passed'] for item in records), records=records,
        scope='Re-run one/two inactive refinements from actual source WALL G3 and reconstruct CONTROL native geometry')
    path = root/'source_reference_verification.json'
    if path.exists():
        raise FileExistsError('Existing source verification preserved: '+str(path))
    path.write_text(json.dumps(receipt, indent=2), encoding='utf8')
    return receipt


def generate(root, parent_root, detail_generation=4):
    root, parent_root = Path(root).resolve(), Path(parent_root).resolve()
    if detail_generation not in (4, 5):
        raise ValueError('Only detail generations 4 and 5 are supported.')
    if root.exists():
        raise FileExistsError('Existing bulb comparison preserved: '+str(root))
    root.mkdir(parents=True)
    atlas_folder = root/'atlas'; atlas_folder.mkdir()
    atlas = build_atlas()
    np.savez_compressed(atlas_folder/'power8.npz', **atlas)
    (atlas_folder/'recipe.json').write_text(json.dumps(ATLAS_RECIPE, indent=2), encoding='utf8')
    print('BULB_ATLAS', atlas['finite_membership'].shape, 'height range',
        float(atlas['height_raw'].min()), float(atlas['height_raw'].max()), flush=True)
    receipts = []
    modes = ('CONTROL', *VARIANTS) if detail_generation == 4 else ('BOLD_DETAIL', 'CONTROL')
    for case in ('SPAN', 'COUNTER'):
        source = parent_root/'WALL'/case/'G03'
        source_metadata = json.loads((source/'generation.json').read_text(encoding='utf8'))
        mesh, chart, tags = study.previous.anchor.t.load(source)
        if mesh.generation != 3 or source_metadata['candidate'] != 'WALL':
            raise ValueError('Actual current WALL G3 parent required, not CHILD.')
        out, outchart, outtags = mesh, chart, tags
        for _ in range(detail_generation-3):
            out, outchart, outtags, operator = study.previous.anchor.t.memory.refine(out, outchart, outtags)
        reference = out.xyz.copy()
        native = study.previous.anchor.t.growth.native(out)
        incoming_normals = trimesh.Trimesh(native.xyz, native.faces[:, :3], process=False).vertex_normals[:len(reference)].copy()
        common = dict(input_case=case, source=str(source), source_control_sha256=digest(source/'control_quad.npz'),
            parent_candidate='WALL', source_generation=3, output_generation=detail_generation,
            inactive_refinement_passes=detail_generation-3,
            operation='Inactive surface-preserving split(s), then finite Mandelbulb upper-envelope local relief',
            atlas_recipe=ATLAS_RECIPE, common_recipe=COMMON, source_xyz_smoothing=False,
            original_field_passes_in_history=source_metadata['input'].get('field_passes_inherited'),
            new_nearest_outside_passes=0, projected_bulb_relief_passes=1,
            normal_rule='Weighted actual incoming native normals pooled per physical colony; source XYZ is untouched before relief',
            amplitude_scope='Bounds control displacement, not full old fold-angle retention')
        for mode in modes:
            if mode == 'CONTROL':
                delta = np.zeros_like(reference); colonies = None; fields = {}
                variant = dict(maximum_height=0.)
            else:
                variant = VARIANTS[mode]
                colonies = make_colonies(mesh, chart, variant)
                delta, fields = apply_colonies(reference, outchart, incoming_normals, colonies, atlas, variant['maximum_height'])
            pre_reflection = delta.copy()
            existing = study.previous.anchor.t.prior.helpers.existing
            pairs = existing.symmetry(outchart)
            existing.reflect(delta, outchart, pairs)
            if 'height' in fields:
                fields['final_symmetric_height'] = reflect_scalar(fields['height'].copy(), outchart, pairs)
            out.xyz = reference+delta
            metadata = dict(common, candidate=mode, variant_recipe=variant,
                maximum_height=variant['maximum_height'],
                actual_primary_colonies=0 if colonies is None else int((colonies['levels'] == 0).sum()),
                actual_secondary_colonies=0 if colonies is None else int((colonies['levels'] == 1).sum()))
            receipts.append(save(root/mode/case/f'G{detail_generation:02d}', out, outchart, outtags, metadata,
                dict(reference_xyz=reference, chart=outchart, incoming_normals=incoming_normals,
                    pre_reflection_delta=pre_reflection, delta=delta,
                    input_edges=operator['input_edges'], parent_face=operator['parent_face'], **fields), colonies))
    verification = [replay(root, case, mode, detail_generation) for case in ('SPAN', 'COUNTER') for mode in modes]
    source_verification = verify_source_references(root, detail_generation)
    passed = all(record['passed'] for record in verification) and source_verification['passed']
    (root/'verification.json').write_text(json.dumps(dict(passed=passed, records=verification,
        scope='Saved atlas + colony frames + actual incoming normals reproduce real control displacement and native geometry',
        excluded=['self-intersection', 'fabrication', 'aesthetic success', 'exact infinite Mandelbulb boundary']), indent=2), encoding='utf8')
    (root/'SUMMARY.json').write_text(json.dumps(dict(variants={mode: VARIANTS[mode] for mode in modes if mode != 'CONTROL'},
        output_generation=detail_generation, common=COMMON, atlas=ATLAS_RECIPE,
        states=[dict(input_case=r['input_case'], candidate=r['candidate'], checks=r['checks'],
            primary_colonies=r['actual_primary_colonies'], secondary_colonies=r['actual_secondary_colonies']) for r in receipts],
        verification_passed=passed), indent=2), encoding='utf8')
    shutil.copy2(__file__, root/'bulb_detail.py')
    print('BULB_REPLAY', 'PASS' if passed else 'FAILED', len(verification), flush=True)
    if not passed:
        raise ValueError('Saved bulb replay failed; evidence preserved.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--parent-root', type=Path, default=HERE.parents[1]/'output/fold_visible_gate_20261012')
    parser.add_argument('--detail-generation', type=int, choices=(4, 5), default=4,
        help='G5 resolves the same BOLD_DETAIL field with one additional inactive split; no extra relief pass.')
    args = parser.parse_args()
    generate(args.root, args.parent_root, args.detail_generation)
