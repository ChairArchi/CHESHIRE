"""Coarse versus bounded local fine targets in the existing quad progression.

The actual input is free to change, including its old vertices and endpoints.
No crease, valley, pleat or previous-field memory attenuates these passes.
This reuses CHESHIRE's existing finite Mandelbulb reconstruction of the public
IAAC process; it does not claim IAAC disclosed these exact equations or recipe.
Optional authored PCHIP returns and escape-iteration staging compose existing
operators; lower iterations expand finite occupancy, not guaranteed filtering.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'terminal_fold_20261011'))
import field_follow as helpers
import smooth_deep
from cheshire.reference_subdivision import ArrayMesh
from cheshire import task33_folds, task36_growth

base = helpers.base
variation = helpers.variation
ALGORITHM = 'COLUMN_DEVELOPMENT_LOCAL_TARGET_COMPARE_V1'
VARIANTS = {
    'base': {},
    'n4': dict(powers=[4, 4]),
    'bridge4': dict(powers=[4, 4, 4], centres=[1.8, 5., 8.1], axial=2.5),
    'n8': dict(powers=[8, 8]),
    'three': dict(powers=[4, 6, 8], centres=[5 / 3, 5., 25 / 3], axial=2.),
    'five': dict(powers=[4, 6, 7, 8, 8], centres=[1., 3., 5., 7., 9.], axial=1.25),
    'radial_io': dict(response='radial_inside_outside'),
    'cc': dict(refinement='CC'),
}
FOLD_EVENTS = [
    dict(id='LOWER_Y_RETURN', direction=np.pi / 2, height=.38, span=.075,
         expansion=.40, constriction=.18, reexpansion=.32, return_depth=.38,
         overlap_width=.95, sweep=-.16, mirror=False),
    dict(id='MIDDLE_DIAGONAL_RETURN', direction=.65, height=.60, span=.06,
         expansion=.30, constriction=.14, reexpansion=.26, return_depth=.30,
         overlap_width=.80, sweep=.18, mirror=False),
    dict(id='UPPER_X_RETURN', direction=0., height=.82, span=.045,
         expansion=.22, constriction=.10, reexpansion=.19, return_depth=.22,
         overlap_width=.85, sweep=-.16, mirror=False),
]
FIELD_ITERATIONS = (4, 8, 18)


def field_recipe(variant, fraction=.55):
    cfg = variation.recipe('IAAC_REPEAT', fraction=fraction, powers=[5, 6],
                           centres=[2.5, 7.5], axial=2.8, scales=[1.6, 1.6])
    cfg.update(VARIANTS[variant])
    return cfg


def load_checkpoint(path):
    with np.load(path, allow_pickle=False) as saved:
        xyz, tri, chart = (saved[key].copy() for key in ('xyz', 'faces', 'chart'))
    if xyz.ndim != 2 or xyz.shape[1] != 3 or chart.shape != xyz.shape:
        raise ValueError('Expected matching N x 3 xyz and chart arrays.')
    if tri.ndim != 2 or tri.shape[1] != 3 or tri.dtype.kind not in 'iu':
        raise ValueError('Expected authoritative integer triangle faces.')
    if not np.isfinite(xyz).all() or not np.isfinite(chart).all() or tri.min() < 0 or tri.max() >= len(xyz):
        raise ValueError('Invalid checkpoint coordinates or face indices.')
    return xyz, tri, chart


def load_quads(path):
    with np.load(path, allow_pickle=False) as saved:
        faces = saved['quads'].copy() if 'quads' in saved.files else saved['faces'].copy()
        # Physical checkpoints may append render-only fan centres after V.
        count = int(faces.max()) + 1
        xyz, chart = saved['xyz'][:count].copy(), saved['chart'][:count].copy()
    if faces.ndim != 2 or faces.shape[1] != 4 or faces.dtype.kind not in 'iu' or faces.min() < 0:
        raise ValueError('Quad control must contain closed all-quad integer faces.')
    if xyz.shape != (count, 3) or chart.shape != xyz.shape or not np.isfinite(xyz).all() or not np.isfinite(chart).all():
        raise ValueError('Invalid quad control XYZ or chart.')
    return xyz, faces, chart


def quad_mesh(xyz, faces, generation):
    return ArrayMesh(xyz, faces, np.full(len(xyz), -1, np.int8), xyz.copy(),
                     np.full((len(faces), 3), -1, np.int64), generation)


def physical_quads(xyz, faces, chart, generation):
    native = task36_growth.native(quad_mesh(xyz, faces, generation))
    physical_chart = np.vstack([chart, chart[faces].mean(1)])
    return native.xyz, native.faces[:, :3], physical_chart


def reflection_state(xyz, tri, chart):
    pairs = helpers.existing.symmetry(chart)
    sortrows = lambda a: a[np.lexsort(tuple(a[:, j] for j in range(a.shape[1] - 1, -1, -1)))]
    triangles = sortrows(np.sort(tri, axis=1))
    errors = []; matched = []
    for axis, ids in enumerate(pairs):
        sign = np.ones(3); sign[axis] = -1
        errors.append(float(np.linalg.norm(xyz - xyz[ids] * sign, axis=1).max()))
        matched.append(bool(np.array_equal(triangles, sortrows(np.sort(ids[tri], axis=1)))))
    if max(errors) > 1e-9 or not all(matched):
        raise ValueError('Actual mesh lacks mandatory geometric X/Y reflection.')
    return pairs, errors, matched



COARSE_SPACING = np.array([.06, .06, .0625])


def local_fine_targets(query, coarse, cfg, factor, plane_x=False, plane_y=False):
    """Bounded finite lattice samples near used coarse targets, with fallback.

    A shared bank avoids repeating classifier work for vertices with the same
    coarse target. Search half extent is exactly one coarse spacing on each
    free axis. The original coarse targets remain eligible, so distance cannot
    worsen. This is local finite sampling, not a global continuous boundary solve.
    """
    if factor not in (2, 3):
        raise ValueError('Use the declared half/third coarse-spacing comparison.')
    spacing = COARSE_SPACING / factor
    anchors = np.unique(np.rint(coarse / spacing).astype(np.int64), axis=0)
    offsets = [np.arange(-factor, factor + 1, dtype=np.int64) for _ in range(3)]
    if plane_x:
        offsets[0] = np.array([0], np.int64)
    if plane_y:
        offsets[1] = np.array([0], np.int64)
    stencil = np.stack(np.meshgrid(*offsets, indexing='ij'), axis=-1).reshape(-1, 3)
    indices = (anchors[:, None, :] + stencil[None, :, :]).reshape(-1, 3)
    bounds = np.rint(np.array([2.4, 2.4, 10.]) / spacing).astype(np.int64)
    indices = indices[((indices >= 0) & (indices <= bounds)).all(1)]
    indices = np.unique(indices, axis=0)
    candidates = indices * spacing
    outside = np.empty(len(candidates), bool)
    for start in range(0, len(candidates), 65536):
        outside[start:start + 65536] = ~variation.classify(candidates[start:start + 65536], cfg)
    # Keep the exact cached float coordinates as well as the fine lattice.
    # Finite fractal classification near a boundary can depend on rounding.
    fallback = np.unique(coarse, axis=0)
    bank = np.vstack([candidates[outside], fallback])
    distance, ids = cKDTree(bank).query(query)
    resolved = bank[ids]
    coarse_distance = np.linalg.norm(coarse - query, axis=1)
    if np.any(distance > coarse_distance + 1e-10):
        raise ValueError('Fine target search worsened a coarse nearest distance.')
    improvement = coarse_distance - distance
    log = dict(spacing=spacing.tolist(), search_half_extent=COARSE_SPACING.tolist(),
               unique_coarse_anchors=len(anchors), candidates_classified=len(candidates),
               fine_outside_candidates=int(outside.sum()), exact_coarse_fallbacks=len(fallback),
               improved_queries=int((improvement > 1e-12).sum()),
               maximum_distance_improvement=float(improvement.max()),
               median_distance_improvement=float(np.median(improvement)),
               classifier_batch_limit=65536, global_fine_grid=False)
    return resolved, log


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True,
                        help='Low-resolution actual input folder or checkpoint.npz.')
    parser.add_argument('--output-root', default='E:/CHESHIRE_DATA/column_development_20261011')
    parser.add_argument('--target-mode', choices=('coarse', 'refined'), default='coarse',
                        help='Coarse existing outside grid, or G2/G3 bounded local half/third-step target refinement.')
    parser.add_argument('--name', default='TARGET_COMPARE', help='Relative output family, including optional subfolder.')
    parser.add_argument('--variant', choices=tuple(VARIANTS), default='base',
                        help='Bounded field/domain/refinement catalogue; radial_io is the separate radial process.')
    parser.add_argument('--quad-source', nargs='?', const='auto', default='auto',
                        help='Auto-detect sibling control_quad.npz or checkpoint quads; optionally specify a control file.')
    parser.add_argument('--stages', type=int, choices=(1, 2, 3), default=3,
                        help='Run through this stage; matching completed stages are reused without overwriting.')
    parser.add_argument('--budgets', nargs=3, type=float, default=[.35, .28, .22],
                        metavar=('G1', 'G2', 'G3'), help='Generous physical maximum steps in input units.')
    parser.add_argument('--fraction', type=float, default=.55,
                        help='Nearest-outside attraction fraction; the separate radial_io coefficient remains .22.')
    parser.add_argument('--fold-schedule', action='store_true',
                        help='After each field pass, add its fixed existing PCHIP return event on the material chart.')
    parser.add_argument('--staged-field', action='store_true',
                        help='Use finite escape iterations 4, 8, 18 in G1, G2, G3; a reconstructed staging hypothesis.')
    args = parser.parse_args()
    if not np.isfinite(args.budgets).all() or min(args.budgets) <= 0:
        raise ValueError('Three positive finite physical step budgets are required.')
    if not np.isfinite(args.fraction) or args.fraction < 0:
        raise ValueError('The attraction fraction must be finite and nonnegative.')
    source_path = helpers.checkpoint_path(args.source)
    root = Path(args.output_root).resolve()
    family = Path(args.name)
    if family.is_absolute() or '..' in family.parts:
        raise ValueError('--name must be a relative output family beneath --output-root.')
    control_path = None
    if args.quad_source == 'auto':
        if (source_path.parent / 'control_quad.npz').exists():
            control_path = source_path.parent / 'control_quad.npz'
        else:
            with np.load(source_path, allow_pickle=False) as saved:
                if 'quads' in saved.files or saved['faces'].shape[1] == 4:
                    control_path = source_path
    else:
        control_path = Path(args.quad_source).resolve()
    quad_mode = control_path is not None
    if not quad_mode:
        raise ValueError('This comparison requires authoritative control_quad.npz or checkpoint quads.')
    if args.variant == 'cc' and not quad_mode:
        raise ValueError('The CC comparison requires the authoritative quad control input.')
    xyz, tri, chart = load_quads(control_path) if quad_mode else load_checkpoint(source_path)
    input_vertices, input_triangles = len(xyz), len(tri)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    control_hash = hashlib.sha256(control_path.read_bytes()).hexdigest() if quad_mode else None
    _, source_reflection, _ = reflection_state(xyz, tri, chart)
    initial_cfg = field_recipe(args.variant, args.fraction)
    radial = args.variant == 'radial_io'; cc = args.variant == 'cc'
    if radial and args.target_mode == 'refined':
        raise ValueError('Refined outside targets apply to nearest-outside variants, not the separate radial process.')
    trees = None; fieldpath = None
    for gen in range(1, args.stages + 1):
        folder = root / family / f'G{gen:02}'
        cfg = initial_cfg.copy()
        if args.staged_field:
            cfg['iterations'] = FIELD_ITERATIONS[gen - 1]
        fold_event = FOLD_EVENTS[gen - 1] if args.fold_schedule else None
        signature = dict(algorithm=ALGORITHM, source_sha256=source_hash, stage=gen,
                         fraction=args.fraction, maximum_step=args.budgets[gen - 1], field_recipe=cfg,
                         target_mode=args.target_mode, local_target_factor=(1, 2, 3)[gen - 1] if args.target_mode == 'refined' else 1)
        if quad_mode:
            signature.update(algorithm=ALGORITHM + '_QUAD_V1', control_sha256=control_hash)
        if args.variant != 'base':
            signature.update(variant=args.variant, field_response='radial_inside_outside' if radial else 'nearest_outside',
                             refinement='neutral_CC' if cc else 'linear', fraction=.22 if radial else args.fraction)
        # Default controls retain the existing saved signatures exactly.
        if args.fold_schedule:
            signature.update(fold_schedule=FOLD_EVENTS)
        if args.staged_field:
            signature.update(staged_field=True, field_iterations=cfg['iterations'])
        if folder.exists() and any(folder.iterdir()):
            meta_path = folder / 'generation.json'
            if not meta_path.exists() or json.loads(meta_path.read_text(encoding='utf8')).get('signature') != signature:
                raise FileExistsError('Stage is incomplete or uses different input/controls: ' + str(folder))
            xyz, tri, chart = load_quads(folder / 'control_quad.npz') if quad_mode else load_checkpoint(folder / 'checkpoint.npz')
            if not (folder / 'operation_fields.npz').exists() or not (folder / 'gate.ply').exists():
                raise FileExistsError('Saved stage lacks output artifacts: ' + str(folder))
            print('REUSED', str(family), gen, flush=True)
            continue
        if not radial and (trees is None or args.staged_field):
            # The existing cache key includes iterations; each staged field
            # must classify and query targets from that same generation's cfg.
            trees, fieldpath = helpers.outside_trees(cfg, root)
        incoming = xyz
        nv = len(incoming); previous_triangles = len(tri)
        # Main public-flow path: shared four edge midpoints + face centre,
        # four child quads. Existing operator overwrites all CC coordinates.
        if quad_mode:
            refined_mesh, state, _, refinement = task33_folds.refine(
                quad_mesh(incoming, tri, gen - 1), dict(carrier=incoming, chart=chart),
                carrier_smoothing=False, smooth_geometry=cc)
            refined, tri, chart = refined_mesh.xyz, refined_mesh.faces, state['chart']
        else:
            refined, tri, attributes = trimesh.remesh.subdivide(incoming, tri, vertex_attributes={'chart': chart})
            chart = attributes['chart']; refinement = {}
        refinement_old_motion = np.linalg.norm(refined[:nv] - incoming, axis=1)
        if not cc and not np.array_equal(refined[:nv], incoming):
            raise ValueError('Midpoint operator unexpectedly changed previous vertices before field movement.')
        pairs, _, triangle_sets = reflection_state(refined, tri, chart)
        canonical = chart.copy(); canonical[:, 1:] = np.abs(canonical[:, 1:])
        distance, canonical_ids = cKDTree(chart).query(canonical)
        if distance.max() > 1e-9:
            raise ValueError('Missing exact canonical-quarter correspondence after subdivision.')
        quarter = np.unique(canonical_ids); slots = np.searchsorted(quarter, canonical_ids)
        qchart = chart[quarter]
        p = refined[quarter].copy(); physical_sign = np.where(p[:, :2] < 0, -1, 1)
        p[:, :2] = np.abs(p[:, :2])
        inside = variation.classify(p, cfg)
        xp = np.abs(qchart[:, 1]) < 1e-12; yp = np.abs(qchart[:, 2]) < 1e-12
        move = np.zeros_like(p); target = p.copy(); coarse_target = p.copy()
        target_factor = (1, 2, 3)[gen - 1] if args.target_mode == 'refined' else 1
        target_logs = []
        if radial:
            # Separate public process 4: our explicit interpretation of centre
            # is the column's XY axis. Coefficient .22 is reconstructed, not
            # disclosed IAAC code. Zero radial axis motion follows the formula.
            move[:, :2] = .22 * np.where(inside, 1., -1.)[:, None] * p[:, :2]
            target = p + move
            active = np.ones(len(p), bool)
        else:
            # Every inside sample is eligible, including old points and caps.
            # Plane restrictions enforce only the required reflections.
            active = inside
            for px, py, tree, subset in trees:
                ids = np.flatnonzero(inside & (xp == px) & (yp == py))
                if not len(ids):
                    continue
                _, where = tree.query(p[ids]); coarse_target[ids] = subset[where]
                target[ids] = coarse_target[ids]
                if target_factor > 1:
                    target[ids], log = local_fine_targets(p[ids], coarse_target[ids], cfg, target_factor, px, py)
                    target_logs.append(dict(symmetry_plane=[px, py], **log))
                if variation.classify(target[ids], cfg).any():
                    raise ValueError('Nearest target fails the actual finite outside classifier.')
                move[ids] = args.fraction * (target[ids] - p[ids])
        requested_length = np.linalg.norm(move, axis=1)
        factor = np.minimum(1, args.budgets[gen - 1] / np.maximum(requested_length, 1e-15))
        move *= factor[:, None]
        move[:, :2] *= physical_sign
        field_displacement = move[slots].copy()
        field_displacement[:, :2] *= np.where(chart[:, 1:] < 0, -1, 1)
        helpers.existing.reflect(field_displacement, chart, pairs)
        post_field = refined + field_displacement
        return_displacement = np.zeros_like(refined)
        if fold_event is not None:
            # Existing authored PCHIP radial/axial event; no XYZ smoothing,
            # memory attenuation, or physical-sign reinterpretation.
            return_displacement = smooth_deep.smooth_event(canonical, fold_event)
            return_displacement[:, :2] *= np.where(chart[:, 1:] < 0, -1, 1)
            helpers.existing.reflect(return_displacement, chart, pairs)
        displacement = field_displacement + return_displacement
        xyz = post_field + return_displacement
        render_xyz, render_tri, render_chart = physical_quads(xyz, tri, chart, gen) if quad_mode else (xyz, tri, chart)
        mesh = trimesh.Trimesh(render_xyz, render_tri, process=False)
        if not np.isfinite(xyz).all() or not mesh.is_watertight or not mesh.is_winding_consistent:
            raise ValueError('Nonfinite or topologically invalid output; no repair.')
        reflection_errors = []
        for axis, ids in enumerate(pairs):
            sign = np.ones(3); sign[axis] = -1
            reflection_errors.append(float(np.linalg.norm(xyz - xyz[ids] * sign, axis=1).max()))
        if max(reflection_errors) > 1e-9:
            raise ValueError('Actual field output lost X/Y reflection.')
        if quad_mode:
            _, physical_errors, triangle_sets = reflection_state(render_xyz, render_tri, render_chart)
            reflection_errors = physical_errors
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder / 'geometry.npz', xyz=render_xyz, faces=render_tri)
        np.savez_compressed(folder / 'checkpoint.npz', xyz=render_xyz, faces=render_tri, chart=render_chart)
        if quad_mode:
            np.savez_compressed(folder / 'control_quad.npz', xyz=xyz, faces=tri, chart=chart)
        np.savez_compressed(folder / 'operation_fields.npz', pre_field_xyz=refined,
                            post_field_xyz=post_field, field_displacement=field_displacement,
                            return_displacement=return_displacement,
                            finite_inside=inside[slots], active=active[slots],
                            canonical_query_xyz=p[slots], canonical_coarse_outside_target=coarse_target[slots],
                            coarse_target_distance=np.linalg.norm(coarse_target - p, axis=1)[slots],
                            resolved_target_distance=np.linalg.norm(target - p, axis=1)[slots],
                            **({'canonical_radial_target': target[slots]} if radial else {'canonical_nearest_outside_target': target[slots]}),
                            requested_step_length=requested_length[slots], step_budget_factor=factor[slots],
                            displacement=displacement, canonical_vertex=canonical_ids,
                            **({'input_edges': refinement['input_edges'], 'parent_face': refinement['parent_face']} if quad_mode else {}))
        mesh.export(folder / 'gate.ply')
        shutil.copy2(__file__, folder / 'target_repeat_recipe.py')
        old_motion = np.linalg.norm(xyz[:nv] - incoming, axis=1)
        base.dump(folder / 'generation.json', dict(signature=signature, candidate=str(family), stage=f'G{gen:02}',
            source=str(source_path), parent=str(source_path) if gen == 1 else str(folder.parent / f'G{gen-1:02}' / 'checkpoint.npz'),
            operation=('Quad midpoint/face-centre refinement, then separate finite-inside outward / finite-outside inward radial process' if radial else 'Quad to four quads using existing neutral CC coordinates, then finite nearest-outside attraction' if cc else 'Quad to four quads using unchanged V, shared edge midpoints and face centres; evaluate all old/new control vertices against finite field' if quad_mode else 'Actual exact midpoint triangle subdivision every generation, then unrestricted finite nearest-outside attraction') + ('; then add one authored smooth_deep PCHIP return event' if args.fold_schedule else ''),
            variant=args.variant, target_mode=args.target_mode, local_target_factor=target_factor,
            local_target_logs=target_logs,
            target_equation='delta=.22*(inside?+1:-1)*(x,y,0), then the declared physical step budget' if radial else f't=argmin ||q-p|| over sampled finite-outside candidates; delta={args.fraction}*(t-p)*min(1,budget/||{args.fraction}*(t-p)||)',
            field_equation=f'z0=0; z_next=spherical_power(z,n)+c; finite inside iff radius never exceeds 4 during {cfg["iterations"]} iterations; union of configured transformed domains',
            staged_field=args.staged_field, field_iterations=cfg['iterations'],
            staged_field_interpretation='Finite escape iteration schedule [4,8,18] is our hypothesis, not an exact IAAC equation. Lower iterations may expand finite occupancy, not guaranteed frequency filtering. Inside-only response may retain outside vertices from earlier passes, producing history dependence. Iteration 2 was excluded because the existing z=0..10 grid has no finite-outside samples on the mandatory X=Y=0 subset; target bounds remain unchanged.' if args.staged_field else None,
            fold_schedule=args.fold_schedule, fold_event=fold_event,
            fold_events_total=gen if args.fold_schedule else 0,
            fold_operator='Existing smooth_deep.smooth_event on abs material quarter, then material-sign reflection; one event after each field pass' if args.fold_schedule else None,
            fold_equation='XYZ_out=XYZ_after_field+reflected(smooth_deep.smooth_event(abs_material_chart,event)); existing PCHIP section amplitudes in physical units' if args.fold_schedule else None,
            fold_provenance='CHESHIRE authored PCHIP return composition, not an IAAC original formula; existing event endpoint taper and material-axis suppression remain, with no added holdout' if args.fold_schedule else None,
            target_refinement='Existing coarse candidates plus classified finer lattice points within one coarse spacing of used coarse targets; no global fine 3D grid',
            field_response='Separate radial inside-away/outside-toward column-axis process' if radial else 'Nearest sampled finite-outside attraction',
            radial_process_interpretation=dict(centre='Column XY axis, with Z unchanged', coefficient=.22,
                disclosure='Centre interpretation and numeric coefficient are reconstructed; not disclosed executable IAAC parameters') if radial else None,
            field_recipe=cfg, field_cache=fieldpath, field_passes_total=gen, subdivision_passes_total=gen,
            source_vertices=input_vertices + input_triangles if quad_mode else input_vertices,
            source_triangles=4 * input_triangles if quad_mode else input_triangles,
            source_control_vertices=input_vertices if quad_mode else None,
            source_control_quads=input_triangles if quad_mode else None,
            previous_faces=previous_triangles, physical_vertices=len(render_xyz), physical_triangles=len(render_tri),
            control_vertices=len(xyz), control_quads=len(tri) if quad_mode else None,
            control_input=str(control_path) if quad_mode else None,
            subdivision_operator=f'Existing task33_folds.refine with carrier_smoothing=False, smooth_geometry={cc}' if quad_mode else 'Existing trimesh.remesh.subdivide',
            physical_surface='Task36 explicit arithmetic quad-centre fans; fan centres receive no separate field or scheduled return displacement' if quad_mode else 'Authoritative refined triangles',
            operator_state_frame='Control vertices/quads' if quad_mode else 'Physical vertices/triangles',
            fraction=.22 if radial else args.fraction, maximum_requested_step=args.budgets[gen - 1],
            maximum_actual_step=float(np.linalg.norm(displacement, axis=1).max()),
            maximum_field_step=float(np.linalg.norm(field_displacement, axis=1).max()),
            maximum_return_step=float(np.linalg.norm(return_displacement, axis=1).max()),
            step_budget_scope='Finite field displacement only; scheduled returns use the declared authored event amplitudes',
            active_fraction=float(active[slots].mean()), finite_inside_fraction=float(inside[slots].mean()), moved_vertices=int((np.linalg.norm(displacement, axis=1) > 1e-12).sum()),
            field_moved_vertices=int((np.linalg.norm(field_displacement, axis=1) > 1e-12).sum()),
            return_moved_vertices=int((np.linalg.norm(return_displacement, axis=1) > 1e-12).sum()),
            return_active_fraction=float((np.linalg.norm(return_displacement, axis=1) > 1e-12).mean()),
            refinement_previous_vertex_max_movement=float(refinement_old_motion.max()),
            previous_vertex_max_movement=float(old_motion.max()), previous_vertices_moved=int((old_motion > 1e-12).sum()),
            previous_control_vertex_max_movement=float(old_motion.max()) if quad_mode else None,
            previous_control_vertices_moved=int((old_motion > 1e-12).sum()) if quad_mode else None,
            minimum_triangle_area=float(mesh.area_faces.min()), minimum_area_threshold=1e-12,
            minimum_area_pass=bool(mesh.area_faces.min() > 1e-12),
            source_reflection_error=source_reflection, geometric_reflection_error=reflection_errors,
            reflected_triangle_sets_identical=triangle_sets,
            feature_memory=False, previous_field_footprint_holdout=False, endpoint_lock=False,
            separate_geometric_smoothing=False, CC_coordinate_averaging=cc, random_noise=False,
            symmetry='Canonical quarter field queries and reflected displacement only; no coordinate normalization',
            source_status='CHESHIRE finite Mandelbulb reconstruction following the public IAAC subdivision/field progression; not IAAC original code',
            limitations='Separate radial process: column-axis centre interpretation and .22 coefficient are our reconstruction; no outside-nearest grid is used. No guaranteed folds or hierarchy; contacts remain unchecked.' if radial else 'Local fine targets reduce sampled-grid quantization but are not an exact global nearest boundary or a distance field. Finite lattice spacing remains and may still produce a rocky skin. Fixed field parameters and finite classifier are our reconstruction. No guaranteed folds or hierarchy; rocky results fail the design test. Contacts remain unchecked.',
            self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication='NOT_CHECKED'))
        print('GENERATED', str(family), gen, len(render_xyz), len(render_tri), 'step', np.linalg.norm(displacement, axis=1).max(),
              'minimum_area', mesh.area_faces.min(), flush=True)


if __name__ == '__main__':
    main()
