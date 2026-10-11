"""Finite comparison of independent, guide-coupled and regional field growth.

Reuses column_development's actual quad refinement, finite Mandelbulb target
queries, and PCHIP return events. Only NEW field-displacement vectors are
interpolated. No XYZ rebuilding, geometric smoothing, legacy holdout, or new
folding solver. Coupling is our hypothesis, not an IAAC original equation.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys

import numpy as np
import trimesh
from scipy.interpolate import PchipInterpolator
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'band_target_repeat', HERE.parent / 'column_development_20261011' / 'target_repeat.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
helpers = prior.helpers
variation = prior.variation
ALGORITHM = 'FOLD_BAND_DISPLACEMENT_COUPLING_V1'
GUIDE_INTERVALS = ((4, 12), (8, 24), (16, 48))
CAP_BLEND_SPAN = .04


def c1_window(distance, inner, outer):
    """One in the inner band; zero outside; C1 at both transitions."""
    t = np.clip((np.abs(distance) - inner) / (outer - inner), 0., 1.)
    return 1. - t * t * (3. - 2. * t)


def couple_field_displacement(qchart, raw_move, generation, mode, budget, fold_event):
    """PCHIP interpolation of displacement only, on material sidewall guides.

    Refined chart points lie on polygon chords, so rho>.99 is NOT a valid
    sidewall classifier. Strict 0<s<1 identifies this input's sidewall.
    Endpoint rings and cap interiors retain independent field displacement.
    A .04-material-unit C1 vector blend joins these moving endpoints to the
    coupled sidewall. No endpoint is fixed to its previous XYZ position.
    """
    if mode == 'independent':
        return raw_move.copy(), dict(mode=mode, guide_coupling=False), dict(
            coupling_weight=np.zeros(len(qchart)), regional_weight=np.ones(len(qchart)))
    if mode not in ('coupled', 'regional') or generation not in (1, 2, 3):
        raise ValueError('Unknown mode or generation outside the finite schedule.')
    s = qchart[:, 0]
    theta = np.clip(np.arctan2(qchart[:, 2], qchart[:, 1]), 0., np.pi / 2)
    wall = (s > 1e-12) & (s < 1. - 1e-12)
    wall_ids = np.flatnonzero(wall)
    if not len(wall_ids):
        raise ValueError('Material chart has no interior sidewall samples.')
    angular_intervals, axial_intervals = GUIDE_INTERVALS[generation - 1]
    axial_guides = np.linspace(0., 1., axial_intervals + 1)
    angular_guides = np.linspace(0., np.pi / 2, angular_intervals + 1)
    ss, tt = np.meshgrid(axial_guides, angular_guides, indexing='ij')
    requested_chart = np.column_stack([ss.ravel(), tt.ravel() / (np.pi / 2)])
    actual_chart = np.column_stack([s[wall_ids], theta[wall_ids] / (np.pi / 2)])
    distances, where = cKDTree(actual_chart).query(requested_chart)
    guide_ids = wall_ids[where]
    guide_values = raw_move[guide_ids].reshape(axial_intervals + 1, angular_intervals + 1, 3).copy()
    # Vector boundary conditions, not averaging of physical XYZ coordinates.
    guide_values[:, 0, 1] = 0.
    guide_values[:, -1, 0] = 0.
    # First axial PCHIP at every angular guide, then paired angular evaluations.
    # The paired coefficient evaluation avoids an N-by-N output array.
    axial_values = PchipInterpolator(axial_guides, guide_values, axis=0)(s[wall_ids])
    angular_spline = PchipInterpolator(angular_guides, axial_values, axis=1)
    interval = np.clip(np.searchsorted(angular_guides, theta[wall_ids], side='right') - 1,
                       0, angular_intervals - 1)
    delta = theta[wall_ids] - angular_guides[interval]
    c = angular_spline.c[:, interval, np.arange(len(wall_ids)), :]
    coupled = ((c[0] * delta[:, None] + c[1]) * delta[:, None] + c[2]) * delta[:, None] + c[3]
    join = np.clip(np.minimum(s[wall_ids], 1. - s[wall_ids]) / CAP_BLEND_SPAN, 0., 1.)
    join = join * join * (3. - 2. * join)
    result = raw_move.copy()
    result[wall_ids] = raw_move[wall_ids] * (1. - join[:, None]) + coupled * join[:, None]
    coupling_weight = np.zeros(len(qchart)); coupling_weight[wall_ids] = join
    regional_weight = np.ones(len(qchart))
    if mode == 'regional':
        if fold_event is None:
            raise ValueError('Regional coupling requires the existing fold schedule.')
        centre = fold_event['direction'] + fold_event['sweep'] * np.sin(np.pi * (s - fold_event['height']) / .32)
        d = np.abs(theta - centre)
        width = fold_event['overlap_width']
        local_height = fold_event['height'] + .05 * np.clip(d / width, 0., 1.) ** 1.4
        u = (s - local_height) / fold_event['span']
        compact = c1_window(d, .35 * width, width) * c1_window(u, .9, 2.2)
        # Cap/rim points keep their raw displacement, rather than locked XYZ.
        regional_weight[wall] = compact[wall]
        result[wall] *= regional_weight[wall, None]
    # PCHIP preserves each component's range; the vector norm can still grow.
    # Reapply the SAME field budget. Authored returns remain a separate event.
    lengths = np.linalg.norm(result, axis=1)
    bound_factor = np.minimum(1., budget / np.maximum(lengths, 1e-15))
    result *= bound_factor[:, None]
    log = dict(mode=mode, guide_coupling=True, angular_intervals=angular_intervals,
        axial_intervals=axial_intervals, guide_count=len(guide_ids), sidewall_vertices=len(wall_ids),
        sidewall_rule='strict 0<s<1; refined chart chord radius is not a sidewall classifier',
        cap_rule='s=0/1 rings and cap interiors retain independent field displacement; no endpoint lock',
        cap_join_C1_span=CAP_BLEND_SPAN,
        guide_lookup='nearest actual sidewall sample in normalized material (s,theta/(pi/2))',
        maximum_guide_material_distance=float(distances.max()),
        median_guide_material_distance=float(np.median(distances)),
        interpolant='tensor axial-then-angular component PCHIP of NEW field-displacement vectors only',
        regional_mask='existing event direction+sweep, local height, angular and axial support; compact C1 field scalar' if mode == 'regional' else None,
        regional_wall_nonzero_fraction=float((regional_weight[wall] > 1e-12).mean()),
        maximum_raw_step=float(np.linalg.norm(raw_move, axis=1).max()),
        maximum_applied_step=float(np.linalg.norm(result, axis=1).max()),
        maximum_vector_change=float(np.linalg.norm(result - raw_move, axis=1).max()),
        interpolation_budget_reclamps=int((bound_factor < 1.).sum()),
        coordinate_smoothing=False, coordinate_reconstruction=False, memory_holdout=False,
        field_low_frequency_interpolation=True,
        target_classifier_after_interpolation='NOT_ENFORCED: coupled vectors need not point to finite-outside samples')
    payload = dict(coupling_weight=coupling_weight, regional_weight=regional_weight,
        guide_vertex_ids=guide_ids, guide_requested_s_theta=np.column_stack([ss.ravel(), tt.ravel()]),
        guide_sample_s_theta=np.column_stack([s[guide_ids], theta[guide_ids]]),
        guide_raw_field_displacement=raw_move[guide_ids], applied_budget_factor=bound_factor)
    return result, log, payload


def self_test():
    """Small vector-only sanity; no mesh, folding-mechanics or collision claim."""
    s, theta = np.meshgrid(np.linspace(0., 1., 97), np.linspace(0., np.pi / 2, 65), indexing='ij')
    chart = np.column_stack([s.ravel(), np.cos(theta.ravel()), np.sin(theta.ravel())])
    chart = np.vstack([chart, [0., .2, .2], [1., .3, .2], [0., 0., 0.], [1., 0., 0.]])
    raw = np.zeros_like(chart); raw[:, 2] = .08
    raw[:, 0] = .025 * chart[:, 1]; raw[:, 1] = .02 * chart[:, 2]
    baseline = raw.copy()
    independent, _, _ = couple_field_displacement(chart, raw, 1, 'independent', .2, prior.FOLD_EVENTS[0])
    assert np.array_equal(independent, raw)
    coupled, log, payload = couple_field_displacement(chart, raw, 1, 'coupled', .2, prior.FOLD_EVENTS[0])
    caps = (chart[:, 0] == 0.) | (chart[:, 0] == 1.)
    assert np.array_equal(coupled[caps], raw[caps])
    assert np.max(np.abs(coupled[:, 2] - .08)) < 1e-12
    assert np.array_equal(raw, baseline)
    assert np.max(np.linalg.norm(coupled, axis=1)) <= .2 + 1e-12
    regional, regional_log, weights = couple_field_displacement(chart, raw, 1, 'regional', .2, prior.FOLD_EVENTS[0])
    assert np.array_equal(regional[caps], raw[caps])
    assert np.any(weights['regional_weight'] == 0.) and np.any(weights['regional_weight'] > .9)
    assert np.all(regional[weights['regional_weight'] == 0.] == 0.)
    assert len(payload['guide_vertex_ids']) == 65
    print('SELF_TEST_PASS', json.dumps(dict(constant_vector_z_error=float(np.max(np.abs(coupled[:, 2] - .08))),
        cap_samples_unchanged=int(caps.sum()), guide_count=log['guide_count'],
        regional_wall_nonzero_fraction=regional_log['regional_wall_nonzero_fraction'])), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', help='Actual input folder containing authoritative control_quad.npz.')
    parser.add_argument('--output-root', default='E:/CHESHIRE_DATA/fold_band_growth_20261011')
    parser.add_argument('--name', default='BAND_COUPLED')
    parser.add_argument('--band-mode', choices=('independent', 'coupled', 'regional'), default='coupled')
    parser.add_argument('--variant', choices=tuple(prior.VARIANTS), default='n4')
    parser.add_argument('--target-mode', choices=('coarse', 'refined'), default='refined')
    parser.add_argument('--fraction', type=float, default=.18)
    parser.add_argument('--budgets', nargs=3, type=float, default=[.35, .28, .22])
    parser.add_argument('--stages', type=int, choices=(1, 2, 3), default=3)
    parser.add_argument('--fold-schedule', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test(); return
    if args.source is None:
        parser.error('--source is required unless --self-test is selected')
    if args.variant in ('radial_io', 'cc'):
        parser.error('This finite comparison holds the linear-quad nearest-outside process fixed.')
    if args.band_mode == 'regional' and not args.fold_schedule:
        parser.error('--band-mode regional requires --fold-schedule')
    if not np.isfinite(args.budgets).all() or min(args.budgets) <= 0:
        raise ValueError('Three positive finite field-step budgets required.')
    if not np.isfinite(args.fraction) or args.fraction < 0:
        raise ValueError('Finite nonnegative attraction fraction required.')
    source = helpers.checkpoint_path(args.source)
    control_source = source.parent / 'control_quad.npz'
    xyz, quads, chart = prior.load_quads(control_source)
    source_count = len(xyz); source_quads = len(quads)
    _, source_errors, _ = prior.reflection_state(xyz, quads, chart)
    root = Path(args.output_root).resolve()
    family = Path(args.name)
    if family.is_absolute() or '..' in family.parts:
        raise ValueError('--name must remain beneath --output-root.')
    cfg = prior.field_recipe(args.variant, args.fraction)
    if cfg['iterations'] != 18:
        raise ValueError('This comparison fixes the finite field at 18 iterations.')
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    control_hash = hashlib.sha256(control_source.read_bytes()).hexdigest()
    trees = None; fieldpath = None
    for gen in range(1, args.stages + 1):
        folder = root / family / f'G{gen:02}'
        event = prior.FOLD_EVENTS[gen - 1] if args.fold_schedule else None
        target_factor = (1, 2, 3)[gen - 1] if args.target_mode == 'refined' else 1
        signature = dict(algorithm=ALGORITHM, source_sha256=source_hash, control_sha256=control_hash,
            stage=gen, fraction=args.fraction, maximum_step=args.budgets[gen - 1], field_recipe=cfg,
            target_mode=args.target_mode, local_target_factor=target_factor, band_mode=args.band_mode,
            guide_intervals=GUIDE_INTERVALS, cap_blend_span=CAP_BLEND_SPAN,
            fold_schedule=prior.FOLD_EVENTS if args.fold_schedule else None)
        # Normalize tuple/list JSON representation before resume comparisons.
        signature = json.loads(json.dumps(signature))
        if folder.exists() and any(folder.iterdir()):
            saved = folder / 'generation.json'
            if not saved.exists() or json.loads(saved.read_text(encoding='utf8')).get('signature') != signature:
                raise FileExistsError('Different settings or incomplete stage: ' + str(folder))
            xyz, quads, chart = prior.load_quads(folder / 'control_quad.npz')
            if not (folder / 'operation_fields.npz').exists() or not (folder / 'gate.ply').exists():
                raise FileExistsError('Completed stage lacks actual output artifacts: ' + str(folder))
            print('REUSED', str(family), gen, flush=True)
            continue
        if trees is None:
            trees, fieldpath = helpers.outside_trees(cfg, root)
        incoming = xyz; old_count = len(xyz); previous_quads = len(quads)
        refined_mesh, state, _, refinement = prior.task33_folds.refine(
            prior.quad_mesh(incoming, quads, gen - 1), dict(carrier=incoming, chart=chart),
            carrier_smoothing=False, smooth_geometry=False)
        refined, quads, chart = refined_mesh.xyz, refined_mesh.faces, state['chart']
        if not np.array_equal(refined[:old_count], incoming):
            raise ValueError('Linear refinement unexpectedly changed old coordinates.')
        pairs, _, _ = prior.reflection_state(refined, quads, chart)
        canonical = chart.copy(); canonical[:, 1:] = np.abs(canonical[:, 1:])
        distance, canonical_ids = cKDTree(chart).query(canonical)
        if distance.max() > 1e-9:
            raise ValueError('Missing canonical-quarter correspondence.')
        quarter = np.unique(canonical_ids); slots = np.searchsorted(quarter, canonical_ids)
        qchart = chart[quarter]
        query = refined[quarter].copy()
        physical_sign = np.where(query[:, :2] < 0, -1, 1)
        query[:, :2] = np.abs(query[:, :2])
        inside = variation.classify(query, cfg)
        xp = np.abs(qchart[:, 1]) < 1e-12; yp = np.abs(qchart[:, 2]) < 1e-12
        move = np.zeros_like(query); target = query.copy(); coarse = query.copy(); target_logs = []
        for px, py, tree, subset in trees:
            ids = np.flatnonzero(inside & (xp == px) & (yp == py))
            if not len(ids):
                continue
            _, where = tree.query(query[ids]); coarse[ids] = subset[where]
            target[ids] = coarse[ids]
            if target_factor > 1:
                target[ids], log = prior.local_fine_targets(query[ids], coarse[ids], cfg, target_factor, px, py)
                target_logs.append(dict(symmetry_plane=[px, py], **log))
            if variation.classify(target[ids], cfg).any():
                raise ValueError('Sampled raw target fails finite-outside classifier.')
            move[ids] = args.fraction * (target[ids] - query[ids])
        requested = np.linalg.norm(move, axis=1)
        factors = np.minimum(1., args.budgets[gen - 1] / np.maximum(requested, 1e-15))
        move *= factors[:, None]; move[:, :2] *= physical_sign
        raw_quarter = move.copy()
        move, coupling_log, coupling_payload = couple_field_displacement(
            qchart, raw_quarter, gen, args.band_mode, args.budgets[gen - 1], event)
        def expanded(vectors):
            output = vectors[slots].copy()
            output[:, :2] *= np.where(chart[:, 1:] < 0, -1, 1)
            helpers.existing.reflect(output, chart, pairs)
            return output
        raw_displacement = expanded(raw_quarter)
        field_displacement = expanded(move)
        return_displacement = np.zeros_like(refined)
        if event is not None:
            return_displacement = prior.smooth_deep.smooth_event(canonical, event)
            return_displacement[:, :2] *= np.where(chart[:, 1:] < 0, -1, 1)
            helpers.existing.reflect(return_displacement, chart, pairs)
        post_field = refined + field_displacement
        xyz = post_field + return_displacement
        render_xyz, triangles, render_chart = prior.physical_quads(xyz, quads, chart, gen)
        mesh = trimesh.Trimesh(render_xyz, triangles, process=False)
        if not np.isfinite(xyz).all() or not mesh.is_watertight or not mesh.is_winding_consistent:
            raise ValueError('Invalid actual output; no topology repair applied.')
        _, reflection_errors, reflected_sets = prior.reflection_state(render_xyz, triangles, render_chart)
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder / 'geometry.npz', xyz=render_xyz, faces=triangles)
        np.savez_compressed(folder / 'checkpoint.npz', xyz=render_xyz, faces=triangles, chart=render_chart)
        np.savez_compressed(folder / 'control_quad.npz', xyz=xyz, faces=quads, chart=chart)
        payload = {key: (value[slots] if key in ('coupling_weight', 'regional_weight', 'applied_budget_factor') else value)
                   for key, value in coupling_payload.items()}
        np.savez_compressed(folder / 'operation_fields.npz', pre_field_xyz=refined,
            post_field_xyz=post_field, raw_field_displacement=raw_displacement,
            applied_field_displacement=field_displacement, field_displacement=field_displacement,
            return_displacement=return_displacement, displacement=xyz - refined,
            finite_inside=inside[slots], raw_field_active=inside[slots],
            canonical_query_xyz=query[slots], canonical_nearest_outside_target=target[slots],
            canonical_coarse_outside_target=coarse[slots],
            coarse_target_distance=np.linalg.norm(coarse - query, axis=1)[slots],
            resolved_target_distance=np.linalg.norm(target - query, axis=1)[slots],
            requested_step_length=requested[slots], step_budget_factor=factors[slots],
            canonical_vertex=canonical_ids, input_edges=refinement['input_edges'],
            parent_face=refinement['parent_face'], **payload)
        mesh.export(folder / 'gate.ply')
        shutil.copy2(__file__, folder / 'band_growth_recipe.py')
        old_movement = np.linalg.norm(xyz[:old_count] - incoming, axis=1)
        displacement = xyz - refined
        prior.base.dump(folder / 'generation.json', dict(signature=signature, candidate=str(family), stage=f'G{gen:02}',
            source=str(source), parent=str(source) if gen == 1 else str(folder.parent / f'G{gen-1:02}' / 'checkpoint.npz'),
            operation='Existing linear quad-to-four refinement; finite nearest-outside raw field; optional material-guide displacement coupling; separate authored return',
            band_mode=args.band_mode, band_coupling=coupling_log, variant=args.variant,
            target_mode=args.target_mode, local_target_factor=target_factor, local_target_logs=target_logs,
            field_recipe=cfg, field_cache=fieldpath, field_iterations=cfg['iterations'], staged_field=False,
            field_equation=f'finite Mandelbulb classifier, {cfg["iterations"]} iterations; raw delta={args.fraction}*(nearest sampled outside-query), bounded by declared field budget',
            field_coupling='Only new displacement vectors are interpolated; old XYZ and return displacement are not filtered',
            fold_schedule=args.fold_schedule, fold_event=event, fold_events_total=gen if args.fold_schedule else 0,
            fold_provenance='Existing CHESHIRE smooth_deep.smooth_event PCHIP sequence; not an IAAC disclosed formula',
            source_control_vertices=source_count, source_control_quads=source_quads,
            source_vertices=source_count + source_quads, source_triangles=4 * source_quads,
            previous_faces=previous_quads, control_vertices=len(xyz), control_quads=len(quads),
            physical_vertices=len(render_xyz), physical_triangles=len(triangles),
            subdivision_passes_total=gen, field_passes_total=gen,
            subdivision_operator='Existing task33_folds.refine, carrier_smoothing=False, smooth_geometry=False',
            physical_surface='Existing task36 explicit arithmetic quad-centre fans, same float64 triangles for renderer/checker',
            fraction=args.fraction, maximum_requested_step=args.budgets[gen - 1],
            maximum_raw_field_step=float(np.linalg.norm(raw_displacement, axis=1).max()),
            maximum_field_step=float(np.linalg.norm(field_displacement, axis=1).max()),
            maximum_return_step=float(np.linalg.norm(return_displacement, axis=1).max()),
            maximum_actual_step=float(np.linalg.norm(displacement, axis=1).max()),
            step_budget_scope='Field displacement only; authored return is separate and total movement may exceed field budget',
            active_fraction=float(inside[slots].mean()), finite_inside_fraction=float(inside[slots].mean()),
            field_moved_vertices=int((np.linalg.norm(field_displacement, axis=1) > 1e-12).sum()),
            raw_field_moved_vertices=int((np.linalg.norm(raw_displacement, axis=1) > 1e-12).sum()),
            return_moved_vertices=int((np.linalg.norm(return_displacement, axis=1) > 1e-12).sum()),
            moved_vertices=int((np.linalg.norm(displacement, axis=1) > 1e-12).sum()),
            previous_control_vertex_max_movement=float(old_movement.max()),
            previous_control_vertices_moved=int((old_movement > 1e-12).sum()),
            previous_vertex_max_movement=float(old_movement.max()),
            minimum_triangle_area=float(mesh.area_faces.min()), minimum_area_threshold=1e-12,
            minimum_area_pass=bool(mesh.area_faces.min() > 1e-12),
            source_reflection_error=source_errors, geometric_reflection_error=reflection_errors,
            reflected_triangle_sets_identical=reflected_sets, watertight=bool(mesh.is_watertight),
            winding_consistent=bool(mesh.is_winding_consistent),
            feature_memory=False, previous_field_footprint_holdout=False, endpoint_lock=False,
            separate_geometric_smoothing=False, CC_coordinate_averaging=False, random_noise=False,
            field_low_frequency_interpolation=args.band_mode != 'independent',
            symmetry='Canonical material quarter and reflected vectors; no coordinate normalization',
            source_status='CHESHIRE reconstruction/composition from public IAAC flow, not original executable code',
            limitations='Coupling filters NEW field displacement, not XYZ. Coupled vectors need not end at sampled outside targets. Sparse guides may miss fine features. Cap/rim response remains independent. No guarantee of folds or improved hierarchy. Physical fold, thickness, structural stability and fabrication are unverified.',
            self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication='NOT_CHECKED'))
        print('GENERATED', str(family), gen, len(render_xyz), len(triangles),
              'field_max', np.linalg.norm(field_displacement, axis=1).max(),
              'minimum_area', mesh.area_faces.min(), flush=True)


if __name__ == '__main__':
    main()
