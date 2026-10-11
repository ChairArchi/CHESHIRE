"""Two physical curve-distance controls for the same finite V/F offset study.

Public IAAC boards motivate circle versus height-spanning curve attractors.
Curve equations, distance mapping and coefficients here are declared tests,
not recovered original constants. Same input, V/E/F roles, absolute depth,
decay, budgets and exact bilinear refinement; only the attractor curves change.
Curves control displacement amplitude; they are not rendered geometry.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('curve_role_adapter', HERE / 'role_growth.py')
roles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(roles)
prior = roles.prior
ALGORITHM = 'FINITE_PHYSICAL_CURVE_ATTRACTOR_ROLE_OFFSET_V1'


def attractor_curves(mode):
    """65 points per curve, with disconnected X/Y-mirrored sweep copies."""
    if mode == 'circle':
        theta = np.linspace(0., 2. * np.pi, 65)
        curves = np.array([np.column_stack([1.05 * np.cos(theta), 1.05 * np.sin(theta),
                                          np.full(65, z)]) for z in (1.8, 5., 8.)])
        definition = dict(mode=mode, heights=[1.8, 5., 8.], radius=1.05, samples_per_curve=65)
    elif mode == 'sweep':
        z = np.linspace(.3, 9.7, 65)
        theta = np.pi / 4 + .55 * np.sin(2 * np.pi * z / 10)
        radius = 1.05 + .12 * np.cos(2 * np.pi * z / 10)
        quarter = np.column_stack([radius * np.cos(theta), radius * np.sin(theta), z])
        curves = np.array([quarter * [sx, sy, 1.] for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1))])
        definition = dict(mode=mode, z_range=[.3, 9.7], samples_per_curve=65,
            theta='pi/4 + .55*sin(2*pi*z/10)', radius='1.05 + .12*cos(2*pi*z/10)',
            copies='Four disconnected X/Y reflected curves')
    else:
        raise ValueError('Circle or sweep curve control required.')
    vertices = curves.reshape(-1, 3)
    start = np.arange(len(curves))[:, None] * 65 + np.arange(64)[None, :]
    segments = np.column_stack([start.ravel(), start.ravel() + 1])
    return curves, vertices, segments, definition


def closest_segment_distance(points, vertices, segments, chunk=2048):
    """Exact closest point on each declared straight polyline segment."""
    a = vertices[segments[:, 0]]
    edge = vertices[segments[:, 1]] - a
    denominator = np.einsum('ij,ij->i', edge, edge)
    if np.any(denominator <= 0.) or chunk < 1:
        raise ValueError('Nonzero polyline segments and positive chunk required.')
    result = np.empty(len(points))
    for begin in range(0, len(points), chunk):
        relative = points[begin:begin + chunk, None, :] - a[None, :, :]
        t = np.clip(np.einsum('nsi,si->ns', relative, edge) / denominator, 0., 1.)
        relative -= t[:, :, None] * edge[None, :, :]
        result[begin:begin + chunk] = np.sqrt(np.einsum('nsi,nsi->ns', relative, relative).min(axis=1))
    return result


def curve_activation(xyz, vertices, segments, attractor_range):
    """Canonical absolute-XY query, compact C1 falloff, positive .08 floor."""
    query = xyz.copy(); query[:, :2] = np.abs(query[:, :2])
    distance = closest_segment_distance(query, vertices, segments)
    t = np.clip(1. - distance / attractor_range, 0., 1.)
    activation = .08 + .92 * t * t * (3. - 2. * t)
    return activation, distance


def self_test():
    line = np.array([[0., 0., 0.], [2., 0., 0.]])
    distance = closest_segment_distance(np.array([[1., 3., 0.], [-1., 0., 0.], [3., 0., 0.]]), line, np.array([[0, 1]]))
    assert np.allclose(distance, [3., 1., 1.])
    initial, chart = prior.variation.carrier(dict(rings=9, sectors=16, radius=.78))
    untouched = initial.xyz.copy(); results = {}; activations = []
    for mode in ('circle', 'sweep'):
        _, vertices, segments, _ = attractor_curves(mode)
        def activate(xyz, _, generation):
            return curve_activation(xyz, vertices, segments, 1.)[0]
        xyz, quads, outchart, payload, log = roles.role_step(initial.xyz, initial.faces, chart, 1,
            'vertex_face', .22, .3, activation_fn=activate)
        px, pt, pc = prior.physical_quads(xyz, quads, outchart, 1)
        mesh = trimesh.Trimesh(px, pt, process=False)
        _, errors, matches = prior.reflection_state(px, pt, pc)
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.area_faces.min() > 1e-12
        assert np.isfinite(px).all() and max(errors) < 1e-9 and all(matches)
        assert log['maximum_actual_step'] <= .22 + 1e-12 and log['cap_points_moved'] > 0
        testpoint = np.array([[.9, .7, 3.], [-.9, .7, 3.], [.9, -.7, 3.]])
        weight, _ = curve_activation(testpoint, vertices, segments, 1.)
        assert np.array_equal(weight, np.full(3, weight[0]))
        activations.append(payload['guide_activation'])
        results[mode] = dict(physical_triangles=len(pt), maximum_step=log['maximum_actual_step'],
            minimum_area=float(mesh.area_faces.min()), reflection_errors=errors,
            activation_range=log['activation_range'])
    assert not np.allclose(activations[0], activations[1]) and np.array_equal(initial.xyz, untouched)
    print('SELF_TEST_PASS', json.dumps(results), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='E:/CHESHIRE_DATA/fold_band_growth_20261011/inputs/SPAN_SPARSE/G00')
    parser.add_argument('--output-root', default='E:/CHESHIRE_DATA/fold_band_growth_20261011')
    parser.add_argument('--name', default='CURVE_CIRCLE')
    parser.add_argument('--curve-mode', choices=('circle', 'sweep'), default='circle')
    parser.add_argument('--stages', type=int, choices=(1, 2, 3), default=1)
    parser.add_argument('--absolute-depth', type=float, default=.3)
    parser.add_argument('--attractor-range', type=float, default=1.)
    parser.add_argument('--budgets', nargs=3, type=float, default=[.22, .15, .10])
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test(); return
    if not np.isfinite([args.absolute_depth, args.attractor_range, *args.budgets]).all() or min(args.absolute_depth, args.attractor_range, *args.budgets) <= 0.:
        raise ValueError('Positive finite depth, attractor range and three budgets required.')
    source = prior.helpers.checkpoint_path(args.source); control = source.parent / 'control_quad.npz'
    xyz, quads, chart = prior.load_quads(control)
    source_vertices, source_quads = len(xyz), len(quads)
    _, source_errors, _ = prior.reflection_state(xyz, quads, chart)
    source_meta_path = source.parent / 'generation.json'
    source_meta = json.loads(source_meta_path.read_text(encoding='utf8')) if source_meta_path.exists() else {}
    inherited_field = int(source_meta.get('field_passes_total', 0))
    inherited_subdivision = int(source_meta.get('subdivision_passes_total', 0))
    inherited_role = int(source_meta.get('role_offset_passes_total', 0))
    inherited_growth = int(source_meta.get('growth_passes_total', inherited_field + inherited_role))
    curves, vertices, segments, definition = attractor_curves(args.curve_mode)
    root = Path(args.output_root).resolve(); family = Path(args.name)
    if family.is_absolute() or '..' in family.parts:
        raise ValueError('--name must remain beneath --output-root.')
    hashes = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  control_sha256=hashlib.sha256(control.read_bytes()).hexdigest())
    for gen in range(1, args.stages + 1):
        folder = root / family / f'G{gen:02}'
        signature = dict(algorithm=ALGORITHM, **hashes, stage=gen, curves=definition,
            variant='vertex_face', role_coefficients=roles.VARIANTS['vertex_face'], decay=roles.DECAY,
            absolute_depth=args.absolute_depth, attractor_range=args.attractor_range,
            activation_floor=.08, maximum_step=args.budgets[gen - 1])
        signature = json.loads(json.dumps(signature))
        if folder.exists() and any(folder.iterdir()):
            saved = folder / 'generation.json'
            if not saved.exists() or json.loads(saved.read_text(encoding='utf8')).get('signature') != signature:
                raise FileExistsError('Different settings or incomplete stage: ' + str(folder))
            xyz, quads, chart = prior.load_quads(folder / 'control_quad.npz')
            if not all((folder / filename).exists() for filename in ('operation_fields.npz', 'attractor_curves.npz', 'gate.ply')):
                raise FileExistsError('Stage lacks actual output artifacts: ' + str(folder))
            print('REUSED', str(family), gen, flush=True); continue
        measured = {}
        def activate(current_xyz, _, generation):
            activation, distance = curve_activation(current_xyz, vertices, segments, args.attractor_range)
            measured['distance'] = distance
            return activation
        old_count, old_faces = len(xyz), len(quads)
        xyz, quads, chart, payload, log = roles.role_step(xyz, quads, chart, gen, 'vertex_face',
            args.budgets[gen - 1], args.absolute_depth, activation_fn=activate)
        px, pt, pc = prior.physical_quads(xyz, quads, chart, gen)
        mesh = trimesh.Trimesh(px, pt, process=False)
        if not np.isfinite(px).all() or not mesh.is_watertight or not mesh.is_winding_consistent:
            raise ValueError('Invalid actual output; no repair performed.')
        _, errors, matches = prior.reflection_state(px, pt, pc)
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder / 'geometry.npz', xyz=px, faces=pt)
        np.savez_compressed(folder / 'checkpoint.npz', xyz=px, faces=pt, chart=pc)
        np.savez_compressed(folder / 'control_quad.npz', xyz=xyz, faces=quads, chart=chart)
        np.savez_compressed(folder / 'operation_fields.npz', curve_distance=measured['distance'],
            actual_activation=payload['guide_activation'], **payload)
        np.savez_compressed(folder / 'attractor_curves.npz', curves=curves, vertices=vertices, segments=segments)
        mesh.export(folder / 'gate.ply')
        shutil.copy2(__file__, folder / 'curve_growth_recipe.py')
        prior.base.dump(folder / 'generation.json', dict(signature=signature, candidate=str(family), stage=f'G{gen:02}',
            source=str(source), parent=str(source) if gen == 1 else str(folder.parent / f'G{gen - 1:02}' / 'checkpoint.npz'),
            operation='Existing bilinear quad split and V/F signed normal offsets controlled by exact closest polyline-segment distance',
            role_variant='vertex_face', role_offset=log, curve_definition=definition,
            activation_equation='.08+.92*smoothstep(clamp(1-distance/range,0,1))',
            activation_coordinates='Current refined XYZ, absolute XY canonical query against reflected physical curves',
            curve_distance_range=[float(measured['distance'].min()), float(measured['distance'].max())],
            scale_scope=log['scale_scope'], support_shrinkage=False, absolute_depth=args.absolute_depth,
            source_control_vertices=source_vertices, source_control_quads=source_quads,
            source_vertices=source_vertices + source_quads, source_triangles=4 * source_quads,
            previous_control_vertices=old_count, previous_faces=old_faces,
            control_vertices=len(xyz), control_quads=len(quads), physical_vertices=len(px), physical_triangles=len(pt),
            curve_generation=gen, source_growth_passes=inherited_growth,
            subdivision_passes_total=inherited_subdivision + gen, subdivision_passes_this_study=gen,
            inherited_field_passes=inherited_field, field_passes_total=inherited_field, field_passes_this_study=0,
            role_offset_passes_total=inherited_role + gen, role_offset_passes_this_study=gen,
            growth_passes_total=inherited_growth + gen,
            previous_control_vertex_max_movement=log['old_vertex_maximum_step'],
            previous_control_vertices_moved=log['moved_by_birth'][0], maximum_actual_step=log['maximum_actual_step'],
            moved_vertices=sum(log['moved_by_birth']), minimum_triangle_area=float(mesh.area_faces.min()),
            minimum_area_threshold=1e-12, minimum_area_pass=bool(mesh.area_faces.min() > 1e-12),
            source_reflection_error=source_errors, geometric_reflection_error=errors,
            reflected_triangle_sets_identical=matches, watertight=bool(mesh.is_watertight), winding_consistent=bool(mesh.is_winding_consistent),
            subdivision_operator='Existing task33_folds.refine, carrier_smoothing=False, smooth_geometry=False',
            physical_surface='Existing Task36 arithmetic quad-centre triangle fans; fan centres have no independent offset',
            endpoint_lock=False, separate_geometric_smoothing=False, CC_coordinate_averaging=False,
            random_noise=False, field_used=False, curves_rendered=False,
            provenance='IAAC public catalogue motivates circle versus height-spanning attractors and normal offsets; these curve equations, range mapping and coefficients are declared CHESHIRE comparisons, not original recovered code',
            limitations='No physical folding, thickness, structural or fabrication claim. Closest distance is exact for sampled piecewise-linear curves, not an exact smooth-curve distance. Repeated point-role offsets may still produce repeated geometric texture.',
            self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication='NOT_CHECKED'))
        print('GENERATED', str(family), gen, len(px), len(pt), 'role_max', log['maximum_actual_step'],
              'activation', log['activation_range'], 'minimum_area', mesh.area_faces.min(), flush=True)


if __name__ == '__main__':
    main()
