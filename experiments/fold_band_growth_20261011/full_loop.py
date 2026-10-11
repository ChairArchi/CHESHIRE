"""Three finite paired subdivision/role/field cycles on an actual quad input.

Each cycle performs exactly ONE existing bilinear quad split with V/E/F normal
placement, then evaluates the resulting control XYZ against the finite
Mandelbulb field. This is not a field pass followed by unrelated role-only
generations. Physical render fans are created only after both operations.
Equations, coefficients and curve controls are CHESHIRE reconstructions, not
recovered IAAC source. No PCHIP return, XYZ smoothing, cap lock or fold solver.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil

import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('full_loop_curve_adapter', HERE / 'curve_growth.py')
curves = importlib.util.module_from_spec(spec)
spec.loader.exec_module(curves)
roles = curves.roles
prior = curves.prior
ALGORITHM = 'FINITE_PAIRED_QUAD_ROLE_MANDELBULB_FULL_LOOP_V1'


def apply_field(xyz, quads, chart, cfg, trees, fraction, budget, target_factor):
    """Field on existing controls; deliberately performs NO subdivision."""
    pairs, _, _ = prior.reflection_state(xyz, quads, chart)
    canonical = chart.copy(); canonical[:, 1:] = np.abs(canonical[:, 1:])
    distance, canonical_ids = cKDTree(chart).query(canonical)
    if distance.max() > 1e-9:
        raise ValueError('Missing canonical material-quarter correspondence.')
    quarter = np.unique(canonical_ids)
    slots = np.searchsorted(quarter, canonical_ids)
    qchart = chart[quarter]
    query = xyz[quarter].copy()
    physical_sign = np.where(query[:, :2] < 0, -1, 1)
    query[:, :2] = np.abs(query[:, :2])
    inside = prior.variation.classify(query, cfg)
    xp = np.abs(qchart[:, 1]) < 1e-12
    yp = np.abs(qchart[:, 2]) < 1e-12
    move = np.zeros_like(query)
    coarse = query.copy(); target = query.copy(); target_logs = []
    target_confirmed = np.zeros(len(query), bool)
    for px, py, tree, subset in trees:
        ids = np.flatnonzero(inside & (xp == px) & (yp == py))
        if not len(ids):
            continue
        _, where = tree.query(query[ids])
        coarse[ids] = subset[where]; target[ids] = coarse[ids]
        if target_factor > 1:
            target[ids], log = prior.local_fine_targets(query[ids], coarse[ids], cfg, target_factor, px, py)
            target_logs.append(dict(symmetry_plane=[px, py], **log))
        if prior.variation.classify(target[ids], cfg).any():
            raise ValueError('Raw nearest target fails this finite-outside classifier.')
        target_confirmed[ids] = True
        move[ids] = fraction * (target[ids] - query[ids])
    if not target_confirmed[inside].all():
        raise ValueError('An inside query has no confirmed finite-outside target.')
    requested_length = np.linalg.norm(move, axis=1)
    factors = np.minimum(1., budget / np.maximum(requested_length, 1e-15))
    move *= factors[:, None]
    move[:, :2] *= physical_sign
    displacement = move[slots].copy()
    displacement[:, :2] *= np.where(chart[:, 1:] < 0, -1, 1)
    prior.helpers.existing.reflect(displacement, chart, pairs)
    result = xyz + displacement
    payload = dict(field_displacement=displacement, raw_field_displacement=displacement.copy(),
        applied_field_displacement=displacement.copy(), finite_inside=inside[slots],
        field_active=inside[slots], confirmed_raw_outside_target=target_confirmed[slots],
        canonical_query_xyz=query[slots], canonical_vertex=canonical_ids,
        canonical_coarse_outside_target=coarse[slots], canonical_nearest_outside_target=target[slots],
        coarse_target_distance=np.linalg.norm(coarse - query, axis=1)[slots],
        resolved_target_distance=np.linalg.norm(target - query, axis=1)[slots],
        field_requested_step_length=requested_length[slots], field_step_budget_factor=factors[slots])
    log = dict(field_iterations=cfg['iterations'], fraction=fraction, budget=budget,
        local_target_factor=target_factor, local_target_logs=target_logs,
        finite_inside_fraction=float(inside[slots].mean()),
        field_moved_vertices=int((np.linalg.norm(displacement, axis=1) > 1e-12).sum()),
        maximum_requested_field_step=float(requested_length.max()),
        maximum_field_step=float(np.linalg.norm(displacement, axis=1).max()),
        raw_targets_checked='Every initially inside query has a confirmed sampled finite-outside target before fraction/budget application',
        final_outside_guarantee=False,
        final_outside_explanation='A fractional and budget-limited move can remain inside; no final outside or exact distance-field claim',
        extra_subdivision_performed=False)
    return result, payload, log


def full_cycle(xyz, quads, chart, generation, cfg, trees, fraction, field_budget,
               role_depth, role_budget, target_factor, curve_vertices, curve_segments, attractor_range):
    """One quad split/role placement, followed by one field pass on same mesh."""
    old_quads = len(quads)
    measured = {}
    def activate(current_xyz, current_chart, stage):
        activation, distance = curves.curve_activation(current_xyz, curve_vertices, curve_segments, attractor_range)
        measured['distance'] = distance
        measured['curve_activation'] = activation
        return activation if role_depth > 0. else np.zeros_like(activation)
    # Existing role_step rejects depth=0. A positive scale with zero activation
    # gives the exact bilinear zero-role ablation without a second code path.
    api_depth = role_depth if role_depth > 0. else 1.
    role_xyz, out_quads, out_chart, role_payload, role_log = roles.role_step(
        xyz, quads, chart, generation, 'vertex_face', role_budget, api_depth, activation_fn=activate)
    if len(out_quads) != 4 * old_quads:
        raise ValueError('Full cycle must split each input quad exactly once.')
    if role_depth == 0.:
        role_payload['placement_scale'][:] = 0.
        role_log['absolute_depth'] = 0.
    role_log.update(role_disabled=role_depth == 0., requested_absolute_depth=role_depth,
                    activation_source='Physical circle closest polyline distance, zeroed only for explicit role-depth=0 ablation')
    output, field_payload, field_log = apply_field(role_xyz, out_quads, out_chart,
        cfg, trees, fraction, field_budget, target_factor)
    payload = {key: value for key, value in role_payload.items() if key != 'displacement'}
    payload.update(post_role_xyz=role_xyz, post_field_xyz=output,
        role_displacement=role_payload['displacement'], curve_distance=measured['distance'],
        curve_activation_before_ablation=measured['curve_activation'],
        displacement=output - role_payload['pre_role_xyz'], **field_payload)
    return output, out_quads, out_chart, payload, role_log, field_log


def self_test():
    """One small paired cycle with a tiny declared outside bank, no disk output."""
    initial, chart = prior.variation.carrier(dict(rings=9, sectors=16, radius=.78))
    untouched = initial.xyz.copy()
    cfg = prior.field_recipe('n4', .55)
    lattice = np.stack(np.meshgrid(np.linspace(0., 2.4, 5), np.linspace(0., 2.4, 5),
                                  np.linspace(0., 10., 21), indexing='ij'), axis=-1).reshape(-1, 3)
    outside = lattice[~prior.variation.classify(lattice, cfg)]
    trees = []
    for px, py in ((False, False), (True, False), (False, True), (True, True)):
        use = np.ones(len(outside), bool)
        if px:
            use &= outside[:, 0] == 0.
        if py:
            use &= outside[:, 1] == 0.
        subset = outside[use]
        assert len(subset), 'Tiny test bank needs every symmetry-plane subset.'
        trees.append((px, py, cKDTree(subset), subset))
    _, cv, cs, _ = curves.attractor_curves('circle')
    summaries = []
    for depth in (.20, 0.):
        xyz, quads, outchart, payload, rolelog, fieldlog = full_cycle(initial.xyz,
            initial.faces, chart, 1, cfg, trees, .55, .35, depth, .22, 1, cv, cs, 1.)
        assert len(quads) == 4 * len(initial.faces)
        assert np.array_equal(xyz, payload['pre_role_xyz'] + payload['role_displacement'] + payload['field_displacement'])
        assert np.array_equal(payload['post_role_xyz'], payload['pre_role_xyz'] + payload['role_displacement'])
        assert fieldlog['field_moved_vertices'] > 0 and fieldlog['maximum_field_step'] <= .35 + 1e-12
        if depth == 0.:
            assert not np.any(payload['role_displacement'])
        else:
            assert np.linalg.norm(payload['role_displacement'], axis=1).max() > 0.
        px, pt, pc = prior.physical_quads(xyz, quads, outchart, 1)
        mesh = trimesh.Trimesh(px, pt, process=False)
        _, errors, matches = prior.reflection_state(px, pt, pc)
        assert mesh.is_watertight and mesh.is_winding_consistent
        assert max(errors) < 1e-9 and all(matches) and np.isfinite(px).all()
        summaries.append(dict(role_depth=depth, input_quads=len(initial.faces), output_quads=len(quads),
            field_moved_vertices=fieldlog['field_moved_vertices'], maximum_field_step=fieldlog['maximum_field_step'],
            maximum_role_step=rolelog['maximum_actual_step'], minimum_triangle_area=float(mesh.area_faces.min()),
            reflection_errors=errors, self_intersection='NOT_CHECKED'))
    assert np.array_equal(initial.xyz, untouched)
    print('SELF_TEST_PASS', json.dumps(summaries), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='E:/CHESHIRE_DATA/fold_band_growth_20261011/inputs/SPAN_SPARSE/G00')
    parser.add_argument('--output-root', default='E:/CHESHIRE_DATA/fold_band_growth_20261011')
    parser.add_argument('--name', default='FULL_LOOP')
    parser.add_argument('--stages', type=int, choices=(1, 2, 3), default=3)
    parser.add_argument('--variant', choices=('n4', 'base', 'bridge4', 'n8', 'three', 'five'), default='n4')
    parser.add_argument('--fraction', type=float, default=.55)
    parser.add_argument('--field-budgets', nargs=3, type=float, default=[.35, .28, .22])
    parser.add_argument('--role-budgets', nargs=3, type=float, default=[.22, .15, .10])
    parser.add_argument('--role-depth', type=float, default=.20,
                        help='Absolute model-unit scale before V/E/F coefficients, circle activation and existing decay; zero is exact role-offset ablation.')
    parser.add_argument('--attractor-range', type=float, default=1.)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test(); return
    if not np.isfinite([args.fraction, args.role_depth, args.attractor_range, *args.field_budgets, *args.role_budgets]).all():
        raise ValueError('All parameters must be finite.')
    if args.fraction < 0. or args.role_depth < 0. or min(args.attractor_range, *args.field_budgets, *args.role_budgets) <= 0.:
        raise ValueError('Nonnegative fraction/depth and positive range/budgets required.')
    source = prior.helpers.checkpoint_path(args.source)
    control = source.parent / 'control_quad.npz'
    xyz, quads, chart = prior.load_quads(control)
    source_vertices, source_quads = len(xyz), len(quads)
    _, source_errors, _ = prior.reflection_state(xyz, quads, chart)
    root = Path(args.output_root).resolve(); family = Path(args.name)
    if family.is_absolute() or '..' in family.parts:
        raise ValueError('--name must remain beneath --output-root.')
    cfg = prior.field_recipe(args.variant, args.fraction)
    if cfg['iterations'] != 18:
        raise ValueError('This comparison fixes the finite classifier at 18 iterations.')
    curve_geometry, curve_vertices, curve_segments, curve_definition = curves.attractor_curves('circle')
    hashes = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  control_sha256=hashlib.sha256(control.read_bytes()).hexdigest())
    trees = None; fieldpath = None
    for gen in range(1, args.stages + 1):
        folder = root / family / f'G{gen:02}'
        signature = dict(algorithm=ALGORITHM, **hashes, stage=gen, field_recipe=cfg,
            field_fraction=args.fraction, field_maximum_step=args.field_budgets[gen - 1],
            field_target_mode='refined', local_target_factor=gen,
            role_variant='vertex_face', role_coefficients=roles.VARIANTS['vertex_face'],
            role_decay=roles.DECAY, role_depth=args.role_depth, role_maximum_step=args.role_budgets[gen - 1],
            curves=curve_definition, attractor_range=args.attractor_range, curve_activation_floor=.08,
            cycle_order=['one_bilinear_quad_split_and_role_offset', 'finite_nearest_outside_field'],
            quad_splits_per_cycle=1)
        signature = json.loads(json.dumps(signature))
        if folder.exists() and any(folder.iterdir()):
            saved = folder / 'generation.json'
            if not saved.exists() or json.loads(saved.read_text(encoding='utf8')).get('signature') != signature:
                raise FileExistsError('Different settings or incomplete stage: ' + str(folder))
            xyz, quads, chart = prior.load_quads(folder / 'control_quad.npz')
            if not all((folder / filename).exists() for filename in ('operation_fields.npz', 'attractor_curves.npz', 'gate.ply')):
                raise FileExistsError('Stage lacks actual output artifacts: ' + str(folder))
            print('REUSED', str(family), gen, flush=True); continue
        if trees is None:
            trees, fieldpath = prior.helpers.outside_trees(cfg, root)
        incoming = xyz.copy(); old_count, old_quads = len(xyz), len(quads)
        xyz, quads, chart, payload, rolelog, fieldlog = full_cycle(xyz, quads, chart, gen,
            cfg, trees, args.fraction, args.field_budgets[gen - 1], args.role_depth,
            args.role_budgets[gen - 1], gen, curve_vertices, curve_segments, args.attractor_range)
        px, pt, pc = prior.physical_quads(xyz, quads, chart, gen)
        mesh = trimesh.Trimesh(px, pt, process=False)
        if not np.isfinite(px).all() or not mesh.is_watertight or not mesh.is_winding_consistent:
            raise ValueError('Invalid actual output; no repair performed.')
        _, errors, matches = prior.reflection_state(px, pt, pc)
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder / 'geometry.npz', xyz=px, faces=pt)
        np.savez_compressed(folder / 'checkpoint.npz', xyz=px, faces=pt, chart=pc)
        np.savez_compressed(folder / 'control_quad.npz', xyz=xyz, faces=quads, chart=chart)
        np.savez_compressed(folder / 'operation_fields.npz', **payload)
        np.savez_compressed(folder / 'attractor_curves.npz', curves=curve_geometry,
                            vertices=curve_vertices, segments=curve_segments)
        mesh.export(folder / 'gate.ply')
        shutil.copy2(__file__, folder / 'full_loop_recipe.py')
        old_movement = np.linalg.norm(xyz[:old_count] - incoming, axis=1)
        total_displacement = np.linalg.norm(payload['displacement'], axis=1)
        prior.base.dump(folder / 'generation.json', dict(signature=signature, candidate=str(family), stage=f'G{gen:02}',
            source=str(source), parent=str(source) if gen == 1 else str(folder.parent / f'G{gen-1:02}' / 'checkpoint.npz'),
            operation='Every cycle: exactly one existing bilinear quad split with circle-activated V/E/F normal placement, then a finite nearest-outside field pass on those same control points',
            cycle_order=signature['cycle_order'], quad_splits_per_cycle=1,
            role_variant='vertex_face', role_offset=rolelog, field_step=fieldlog,
            curve_definition=curve_definition, absolute_depth=args.role_depth,
            activation_equation='.08+.92*smoothstep(clamp(1-distance_to_physical_circle_polyline/range,0,1))',
            field_recipe=cfg, field_cache=fieldpath, field_iterations=cfg['iterations'],
            fraction=args.fraction, target_mode='refined', local_target_factor=gen,
            local_target_logs=fieldlog['local_target_logs'],
            source_control_vertices=source_vertices, source_control_quads=source_quads,
            source_vertices=source_vertices + source_quads, source_triangles=4 * source_quads,
            previous_control_vertices=old_count, previous_faces=old_quads,
            control_vertices=len(xyz), control_quads=len(quads), physical_vertices=len(px), physical_triangles=len(pt),
            subdivision_passes_total=gen, field_passes_total=gen, role_offset_passes_total=gen,
            growth_passes_total=gen, growth_cycles_total=gen,
            counting_rule='Role and field are paired operations within one growth cycle, not two sequential generations; totals describe this finite study from the declared input',
            maximum_field_step=fieldlog['maximum_field_step'], maximum_role_step=rolelog['maximum_actual_step'],
            maximum_actual_step=float(total_displacement.max()),
            step_budget_scope='Separate role and field budgets; their summed movement may exceed either individual budget',
            previous_control_vertex_max_movement=float(old_movement.max()),
            previous_control_vertices_moved=int((old_movement > 1e-12).sum()),
            field_moved_vertices=fieldlog['field_moved_vertices'], role_moved_vertices=sum(rolelog['moved_by_birth']),
            moved_vertices=int((total_displacement > 1e-12).sum()),
            finite_inside_fraction=fieldlog['finite_inside_fraction'], active_fraction=fieldlog['finite_inside_fraction'],
            minimum_triangle_area=float(mesh.area_faces.min()), minimum_area_threshold=1e-12,
            minimum_area_pass=bool(mesh.area_faces.min() > 1e-12),
            source_reflection_error=source_errors, geometric_reflection_error=errors,
            reflected_triangle_sets_identical=matches, watertight=bool(mesh.is_watertight),
            winding_consistent=bool(mesh.is_winding_consistent),
            subdivision_operator='Existing task33_folds.refine exactly once per paired cycle; carrier_smoothing=False, smooth_geometry=False',
            physical_surface='Existing Task36 arithmetic quad-centre fans, created after both role and field operations; fans receive no independent displacement',
            endpoint_lock=False, separate_geometric_smoothing=False, CC_coordinate_averaging=False,
            feature_memory=False, random_noise=False, field_used=True, curves_rendered=False,
            PCHIP_return_used=False, final_outside_guarantee=False,
            provenance='IAAC public quad subdivision and finite field flow plus separate curve/normal-role diagrams motivate this CHESHIRE paired-loop reconstruction; formula, ordering and coefficients are declared hypotheses, not recovered IAAC executable code',
            limitations='Only the chosen raw targets are verified finite-outside. Fractional budget-limited final points may remain inside. Normal offsets can create repeated cells or spikes; the field can erase or roughen them. Exact smooth-curve distance, physical folding, thickness, structure and fabrication are unverified.',
            self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication='NOT_CHECKED'))
        print('GENERATED', str(family), gen, len(px), len(pt), 'quads', len(quads),
            'role_max', rolelog['maximum_actual_step'], 'field_max', fieldlog['maximum_field_step'],
            'minimum_area', mesh.area_faces.min(), flush=True)


if __name__ == '__main__':
    main()
