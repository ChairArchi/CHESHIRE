"""Finite V/E/F normal-offset comparison on existing folded quad inputs.

Reuses Task33 bilinear refinement, reference normals and Task36 support radius.
IAAC-related DragonSkin diagrams motivate separate old-vertex and face-centre
offsets; these coefficients and guide bands are CHESHIRE test declarations,
not recovered IAAC constants or evidence of its MeshSubdivision source code.
No Mandelbulb field, coordinate averaging, cap lock or physical fold solver.
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
spec = importlib.util.spec_from_file_location(
    'role_target_repeat', HERE.parent / 'column_development_20261011' / 'target_repeat.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
from cheshire.reference_subdivision import fields, topology, mean_incident, unit

ALGORITHM = 'FINITE_BIRTH_ROLE_NORMAL_OFFSET_V1'
VARIANTS = {
    'vertex_face': dict(V=.32, E=0., F=-.55),
    'edge_face': dict(V=0., E=.22, F=-.52),
}
DECAY = (1., .72, .55)
GUIDES = (
    dict(height=.24, direction=0., sweep=.16, axial_width=.22, angular_width=.78),
    dict(height=.52, direction=.65, sweep=-.18, axial_width=.23, angular_width=.85),
    dict(height=.80, direction=np.pi / 2, sweep=.16, axial_width=.22, angular_width=.78),
)


def guide_activation(chart, generation):
    """Broad deterministic distance-to-guide scalar, including the endpoints.

    A positive .08 floor permits cap response. Gaussian guide distances change
    NEW displacement amplitude only; no existing XYZ are filtered or rebuilt.
    The guide is expressed in the column's material (height, quarter-angle).
    """
    guide = GUIDES[generation - 1]
    s = chart[:, 0]
    theta = np.arctan2(np.abs(chart[:, 2]), np.abs(chart[:, 1]))
    centre = guide['direction'] + guide['sweep'] * np.sin(np.pi * (s - guide['height']) / .40)
    distance2 = ((s - guide['height']) / guide['axial_width']) ** 2
    distance2 += ((theta - centre) / guide['angular_width']) ** 2
    return .08 + .92 * np.exp(-.5 * distance2)


def role_step(xyz, quads, chart, generation, variant, budget, absolute_depth=None, activation_fn=None):
    """One actual quad split, then independent normal offsets for V/E/F."""
    if generation not in (1, 2, 3) or variant not in VARIANTS:
        raise ValueError('Declared finite generation and V/E/F variant required.')
    if not np.isfinite(budget) or budget <= 0:
        raise ValueError('Positive finite normal-offset budget required.')
    if absolute_depth is not None and (not np.isfinite(absolute_depth) or absolute_depth <= 0):
        raise ValueError('Absolute depth must be positive finite model units.')
    mesh = prior.quad_mesh(xyz, quads, generation - 1)
    t = topology(mesh); f = fields(mesh, t)
    if quads.shape[1] != 4:
        raise ValueError('Closed all-quad control surface required.')
    nv, ne, nf = len(xyz), len(t['edges']), len(quads)
    p = xyz[quads]
    a = p - f['c'][:, None]
    b = np.roll(p, -1, axis=1) - p
    support = np.min(np.linalg.norm(np.cross(a, b), axis=2) /
                     np.maximum(np.linalg.norm(b, axis=2), 1e-12), axis=1)
    vertex_support = mean_incident(np.repeat(support, 4), quads.ravel(), nv)
    edge_support = support[t['ef']].min(axis=1)
    scales = np.r_[vertex_support, edge_support, support]
    placement_scale = scales if absolute_depth is None else np.full(len(scales), absolute_depth)
    normals = np.vstack([f['nv'], unit(f['nf'][t['ef']].sum(axis=1)), f['nf']])
    refined, state, _, refinement = prior.task33_folds.refine(
        mesh, dict(carrier=xyz, chart=chart), carrier_smoothing=False, smooth_geometry=False)
    if not np.array_equal(refined.xyz[:nv], xyz):
        raise ValueError('Linear refinement unexpectedly moved old vertices.')
    if len(refined.xyz) != nv + ne + nf:
        raise ValueError('Unexpected birth ordering; expected old V / new E / new F.')
    birth = np.r_[np.zeros(nv, np.int8), np.ones(ne, np.int8), np.full(nf, 2, np.int8)]
    if not np.array_equal(refined.classes, birth):
        raise ValueError('Existing operator birth classes differ from V/E/F ordering.')
    chart_out = state['chart']
    pairs, _, _ = prior.reflection_state(refined.xyz, refined.faces, chart_out)
    weights = VARIANTS[variant]
    coefficients = np.array([weights['V'], weights['E'], weights['F']])
    activation = guide_activation(chart_out, generation) if activation_fn is None else np.asarray(
        activation_fn(refined.xyz, chart_out, generation), dtype=float)
    if activation.shape != (len(refined.xyz),) or not np.isfinite(activation).all() or np.any((activation < 0.) | (activation > 1.)):
        raise ValueError('Activation must be one finite scalar in [0,1] per refined control point.')
    requested = DECAY[generation - 1] * placement_scale * activation * coefficients[birth]
    distances = np.clip(requested, -budget, budget)
    displacement = normals * distances[:, None]
    # Copy canonical-quarter vectors to their mirrors; never average XYZ.
    prior.helpers.existing.reflect(displacement, chart_out, pairs)
    result = refined.xyz + displacement
    if variant == 'edge_face' and not np.array_equal(result[:nv], xyz):
        raise ValueError('Held-old-V variant unexpectedly moved an inherited vertex.')
    cap_points = (np.abs(chart_out[:, 0]) < 1e-12) | (np.abs(chart_out[:, 0] - 1.) < 1e-12)
    length = np.linalg.norm(displacement, axis=1)
    payload = dict(pre_role_xyz=refined.xyz, birth_class=birth, input_edges=t['edges'],
        parent_face=refinement['parent_face'], normal=normals, support_radius=scales,
        placement_scale=placement_scale,
        guide_activation=activation, requested_signed_normal_distance=requested,
        applied_signed_normal_distance=distances, displacement=displacement,
        cap_points=cap_points)
    log = dict(role_coefficients=weights, decay=DECAY[generation - 1], guide=GUIDES[generation - 1] if activation_fn is None else None,
        scale_scope='Input face support radius and incident support' if absolute_depth is None else 'Constant model-unit depth before coefficient, guide and generation decay',
        support_shrinkage=absolute_depth is None, absolute_depth=absolute_depth,
        guide_floor=.08, maximum_requested_step=float(np.abs(requested).max()),
        maximum_actual_step=float(length.max()), budget_clamped_points=int((np.abs(requested) > budget).sum()),
        birth_counts=[nv, ne, nf], moved_by_birth=[int((length[birth == k] > 1e-12).sum()) for k in range(3)],
        activation_range=[float(activation.min()), float(activation.max())],
        cap_points=int(cap_points.sum()), cap_points_moved=int((length[cap_points] > 1e-12).sum()),
        cap_maximum_step=float(length[cap_points].max()) if cap_points.any() else 0.,
        old_vertex_maximum_step=float(length[:nv].max()))
    return result, refined.faces, chart_out, payload, log


def self_test():
    """Small two-variant sanity only; not a collision or folding-mechanics test."""
    initial, chart0 = prior.variation.carrier(dict(rings=9, sectors=16, radius=.78))
    untouched = initial.xyz.copy()
    summary = {}
    for variant in VARIANTS:
        xyz, quads, chart = initial.xyz.copy(), initial.faces.copy(), chart0.copy()
        logs = []
        for gen in (1, 2, 3):
            xyz, quads, chart, payload, log = role_step(xyz, quads, chart, gen, variant, .22)
            px, pt, pc = prior.physical_quads(xyz, quads, chart, gen)
            output = trimesh.Trimesh(px, pt, process=False)
            _, error, matches = prior.reflection_state(px, pt, pc)
            assert np.isfinite(px).all() and output.is_watertight and output.is_winding_consistent
            assert output.area_faces.min() > 1e-12 and max(error) < 1e-9 and all(matches)
            assert log['maximum_actual_step'] <= .22 + 1e-12
            assert log['cap_points_moved'] > 0
            assert (log['moved_by_birth'][0] == 0) == (variant == 'edge_face')
            logs.append(dict(generation=gen, physical_triangles=len(pt), minimum_area=float(output.area_faces.min()),
                             maximum_step=log['maximum_actual_step'], cap_points_moved=log['cap_points_moved']))
        summary[variant] = logs
    assert np.array_equal(initial.xyz, untouched)
    print('SELF_TEST_PASS', json.dumps(summary), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='E:/CHESHIRE_DATA/column_development_20261011/inputs/SPAN_COARSE/G00')
    parser.add_argument('--output-root', default='E:/CHESHIRE_DATA/fold_band_growth_20261011')
    parser.add_argument('--name', default='ROLE_VERTEX_FACE')
    parser.add_argument('--variant', choices=tuple(VARIANTS), default='vertex_face')
    parser.add_argument('--stages', type=int, choices=(1, 2, 3), default=3)
    parser.add_argument('--budgets', nargs=3, type=float, default=[.22, .15, .10])
    parser.add_argument('--absolute-depth', type=float,
        help='Optional positive constant model-unit placement scale instead of shrinking support radii. Coefficients, guide, decay and budgets still apply; not a recovered IAAC constant.')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test(); return
    if not np.isfinite(args.budgets).all() or min(args.budgets) <= 0:
        raise ValueError('Three positive finite offset budgets required.')
    if args.absolute_depth is not None and (not np.isfinite(args.absolute_depth) or args.absolute_depth <= 0):
        raise ValueError('--absolute-depth must be positive finite model units.')
    source = prior.helpers.checkpoint_path(args.source)
    control = source.parent / 'control_quad.npz'
    xyz, quads, chart = prior.load_quads(control)
    source_vertices, source_quads = len(xyz), len(quads)
    _, source_error, _ = prior.reflection_state(xyz, quads, chart)
    root = Path(args.output_root).resolve(); family = Path(args.name)
    if family.is_absolute() or '..' in family.parts:
        raise ValueError('--name must remain beneath --output-root.')
    hashes = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  control_sha256=hashlib.sha256(control.read_bytes()).hexdigest())
    for gen in range(1, args.stages + 1):
        folder = root / family / f'G{gen:02}'
        signature = dict(algorithm=ALGORITHM, **hashes, stage=gen, variant=args.variant,
            role_coefficients=VARIANTS[args.variant], decay=DECAY, guides=GUIDES,
            maximum_step=args.budgets[gen - 1], guide_floor=.08)
        # Default support-mode signatures remain compatible with saved outputs.
        if args.absolute_depth is not None:
            signature.update(absolute_depth=args.absolute_depth, placement_scale='constant_model_units')
        signature = json.loads(json.dumps(signature))
        if folder.exists() and any(folder.iterdir()):
            saved = folder / 'generation.json'
            if not saved.exists() or json.loads(saved.read_text(encoding='utf8')).get('signature') != signature:
                raise FileExistsError('Different settings or incomplete stage: ' + str(folder))
            xyz, quads, chart = prior.load_quads(folder / 'control_quad.npz')
            if not (folder / 'operation_fields.npz').exists() or not (folder / 'gate.ply').exists():
                raise FileExistsError('Stage lacks actual output artifacts: ' + str(folder))
            print('REUSED', str(family), gen, flush=True); continue
        old_count, old_faces = len(xyz), len(quads)
        xyz, quads, chart, payload, log = role_step(xyz, quads, chart, gen, args.variant, args.budgets[gen - 1], args.absolute_depth)
        render_xyz, triangles, render_chart = prior.physical_quads(xyz, quads, chart, gen)
        mesh = trimesh.Trimesh(render_xyz, triangles, process=False)
        if not np.isfinite(xyz).all() or not mesh.is_watertight or not mesh.is_winding_consistent:
            raise ValueError('Invalid actual output; no repair performed.')
        _, errors, matches = prior.reflection_state(render_xyz, triangles, render_chart)
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder / 'geometry.npz', xyz=render_xyz, faces=triangles)
        np.savez_compressed(folder / 'checkpoint.npz', xyz=render_xyz, faces=triangles, chart=render_chart)
        np.savez_compressed(folder / 'control_quad.npz', xyz=xyz, faces=quads, chart=chart)
        np.savez_compressed(folder / 'operation_fields.npz', **payload)
        mesh.export(folder / 'gate.ply')
        shutil.copy2(__file__, folder / 'role_growth_recipe.py')
        prior.base.dump(folder / 'generation.json', dict(signature=signature, candidate=str(family), stage=f'G{gen:02}',
            source=str(source), parent=str(source) if gen == 1 else str(folder.parent / f'G{gen - 1:02}' / 'checkpoint.npz'),
            operation='Existing bilinear quad split; separate V/E/F normal offsets with broad material-guide activation',
            role_variant=args.variant, role_offset=log,
            scale_scope=log['scale_scope'], support_shrinkage=log['support_shrinkage'], absolute_depth=args.absolute_depth,
            source_control_vertices=source_vertices, source_control_quads=source_quads,
            source_vertices=source_vertices + source_quads, source_triangles=4 * source_quads,
            previous_control_vertices=old_count, previous_faces=old_faces,
            control_vertices=len(xyz), control_quads=len(quads), physical_vertices=len(render_xyz), physical_triangles=len(triangles),
            subdivision_passes_total=gen, field_passes_total=0, role_offset_passes_total=gen,
            previous_control_vertex_max_movement=log['old_vertex_maximum_step'],
            previous_control_vertices_moved=log['moved_by_birth'][0], maximum_actual_step=log['maximum_actual_step'],
            moved_vertices=sum(log['moved_by_birth']), minimum_triangle_area=float(mesh.area_faces.min()),
            minimum_area_threshold=1e-12, minimum_area_pass=bool(mesh.area_faces.min() > 1e-12),
            source_reflection_error=source_error, geometric_reflection_error=errors, reflected_triangle_sets_identical=matches,
            watertight=bool(mesh.is_watertight), winding_consistent=bool(mesh.is_winding_consistent),
            subdivision_operator='Existing task33_folds.refine, carrier_smoothing=False, smooth_geometry=False',
            normal_and_scale='Input reference.fields unit face/vertex normals; unit summed adjacent face edge normals; Task36 centre-to-supporting-edge minimum radius',
            physical_surface='Existing Task36 explicit arithmetic quad-centre fans; render fan centres receive no independent offset',
            endpoint_lock=False, separate_geometric_smoothing=False, CC_coordinate_averaging=False, random_noise=False,
            feature_memory=False, field_used=False, symmetry='Canonical-quarter vector copy, without XYZ averaging',
            provenance='DragonSkin-related two-offset diagram motivates V/F distinction; exact constants and guide bands are CHESHIRE declarations; original MeshSubdivision code equivalence unestablished',
            limitations='This tests point-placement roles, not physical origami or guaranteed hierarchy. Repeated births may create spikes. Support mode shrinks with cell size; absolute mode removes that factor but keeps declared generation decay and budgets. Neither scale policy is established as the original IAAC depth formula. Thickness, structure and fabrication unverified.',
            self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication='NOT_CHECKED'))
        print('GENERATED', str(family), gen, len(render_xyz), len(triangles),
              'role_max', log['maximum_actual_step'], 'minimum_area', mesh.area_faces.min(), flush=True)


if __name__ == '__main__':
    main()
