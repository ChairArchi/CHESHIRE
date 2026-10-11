"""Repeated quad midpoint/face-centre refinement and finite outside attraction.

The actual input is free to change, including its old vertices and endpoints.
No crease, valley, pleat or previous-field memory attenuates these passes.
This reuses CHESHIRE's existing finite Mandelbulb reconstruction of the public
IAAC process; it does not claim IAAC disclosed these exact equations or recipe.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

import numpy as np
import trimesh
from scipy.spatial import cKDTree

import field_follow as helpers
from cheshire.reference_subdivision import ArrayMesh
from cheshire import task33_folds, task36_growth

base = helpers.base
variation = helpers.variation
ALGORITHM = 'IAAC_REPEATED_MIDPOINT_NEAREST_OUTSIDE_V1'
VARIANTS = {
    'base': {},
    'n4': dict(powers=[4, 4]),
    'n8': dict(powers=[8, 8]),
    'three': dict(powers=[4, 6, 8], centres=[5 / 3, 5., 25 / 3], axial=2.),
    'five': dict(powers=[4, 6, 7, 8, 8], centres=[1., 3., 5., 7., 9.], axial=1.25),
    'radial_io': dict(response='radial_inside_outside'),
    'cc': dict(refinement='CC'),
}


def field_recipe(variant):
    cfg = variation.recipe('IAAC_REPEAT', fraction=.55, powers=[5, 6],
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default=helpers.DEFAULT_ROOT + '/IAAC_INPUT/G00',
                        help='Low-resolution actual input folder or checkpoint.npz.')
    parser.add_argument('--output-root', default=helpers.DEFAULT_ROOT)
    parser.add_argument('--name', default='IAAC_REPEAT', help='Relative output family, including optional subfolder.')
    parser.add_argument('--variant', choices=tuple(VARIANTS), default='base',
                        help='Bounded field/domain/refinement catalogue; radial_io is the separate radial process.')
    parser.add_argument('--quad-source', nargs='?', const='auto', default='auto',
                        help='Auto-detect sibling control_quad.npz or checkpoint quads; optionally specify a control file.')
    parser.add_argument('--stages', type=int, choices=(1, 2, 3), default=2,
                        help='Run through this stage; use 3 after reviewing G2. Matching saved stages are reused.')
    parser.add_argument('--budgets', nargs=3, type=float, default=[.35, .28, .22],
                        metavar=('G1', 'G2', 'G3'), help='Generous physical maximum steps in input units.')
    args = parser.parse_args()
    if not np.isfinite(args.budgets).all() or min(args.budgets) <= 0:
        raise ValueError('Three positive finite physical step budgets are required.')
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
    if args.variant == 'cc' and not quad_mode:
        raise ValueError('The CC comparison requires the authoritative quad control input.')
    xyz, tri, chart = load_quads(control_path) if quad_mode else load_checkpoint(source_path)
    input_vertices, input_triangles = len(xyz), len(tri)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    control_hash = hashlib.sha256(control_path.read_bytes()).hexdigest() if quad_mode else None
    _, source_reflection, _ = reflection_state(xyz, tri, chart)
    cfg = field_recipe(args.variant)
    radial = args.variant == 'radial_io'; cc = args.variant == 'cc'
    trees = None; fieldpath = None
    for gen in range(1, args.stages + 1):
        folder = root / family / f'G{gen:02}'
        signature = dict(algorithm=ALGORITHM, source_sha256=source_hash, stage=gen,
                         fraction=.55, maximum_step=args.budgets[gen - 1], field_recipe=cfg)
        if quad_mode:
            signature.update(algorithm=ALGORITHM + '_QUAD_V1', control_sha256=control_hash)
        # Keep base signatures byte-for-byte equivalent in meaning so existing
        # generated base stages can be reused without any replay or overwrite.
        if args.variant != 'base':
            signature.update(variant=args.variant, field_response='radial_inside_outside' if radial else 'nearest_outside',
                             refinement='neutral_CC' if cc else 'linear', fraction=.22 if radial else .55)
        if folder.exists() and any(folder.iterdir()):
            meta_path = folder / 'generation.json'
            if not meta_path.exists() or json.loads(meta_path.read_text(encoding='utf8')).get('signature') != signature:
                raise FileExistsError('Stage is incomplete or uses different input/controls: ' + str(folder))
            xyz, tri, chart = load_quads(folder / 'control_quad.npz') if quad_mode else load_checkpoint(folder / 'checkpoint.npz')
            if not (folder / 'operation_fields.npz').exists() or not (folder / 'gate.ply').exists():
                raise FileExistsError('Saved stage lacks output artifacts: ' + str(folder))
            print('REUSED', str(family), gen, flush=True)
            continue
        if trees is None and not radial:
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
        move = np.zeros_like(p); target = p.copy()
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
                _, where = tree.query(p[ids]); target[ids] = subset[where]
                if variation.classify(target[ids], cfg).any():
                    raise ValueError('Nearest target fails the actual finite outside classifier.')
                move[ids] = .55 * (target[ids] - p[ids])
        requested_length = np.linalg.norm(move, axis=1)
        factor = np.minimum(1, args.budgets[gen - 1] / np.maximum(requested_length, 1e-15))
        move *= factor[:, None]
        move[:, :2] *= physical_sign
        displacement = move[slots].copy()
        displacement[:, :2] *= np.where(chart[:, 1:] < 0, -1, 1)
        helpers.existing.reflect(displacement, chart, pairs)
        xyz = refined + displacement
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
                            finite_inside=inside[slots], active=active[slots],
                            canonical_query_xyz=p[slots],
                            **({'canonical_radial_target': target[slots]} if radial else {'canonical_nearest_outside_target': target[slots]}),
                            requested_step_length=requested_length[slots], step_budget_factor=factor[slots],
                            displacement=displacement, canonical_vertex=canonical_ids,
                            **({'input_edges': refinement['input_edges'], 'parent_face': refinement['parent_face']} if quad_mode else {}))
        mesh.export(folder / 'gate.ply')
        shutil.copy2(__file__, folder / 'iaac_repeat_recipe.py')
        old_motion = np.linalg.norm(xyz[:nv] - incoming, axis=1)
        base.dump(folder / 'generation.json', dict(signature=signature, candidate=str(family), stage=f'G{gen:02}',
            source=str(source_path), parent=str(source_path) if gen == 1 else str(folder.parent / f'G{gen-1:02}' / 'checkpoint.npz'),
            operation='Quad midpoint/face-centre refinement, then separate finite-inside outward / finite-outside inward radial process' if radial else 'Quad to four quads using existing neutral CC coordinates, then finite nearest-outside attraction' if cc else 'Quad to four quads using unchanged V, shared edge midpoints and face centres; evaluate all old/new control vertices against finite field' if quad_mode else 'Actual exact midpoint triangle subdivision every generation, then unrestricted finite nearest-outside attraction',
            variant=args.variant, field_response='Separate radial inside-away/outside-toward column-axis process' if radial else 'Nearest sampled finite-outside attraction',
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
            physical_surface='Task36 explicit arithmetic quad-centre fans; fan centres receive no separate field displacement' if quad_mode else 'Authoritative refined triangles',
            operator_state_frame='Control vertices/quads' if quad_mode else 'Physical vertices/triangles',
            fraction=.22 if radial else .55, maximum_requested_step=args.budgets[gen - 1],
            maximum_actual_step=float(np.linalg.norm(displacement, axis=1).max()),
            active_fraction=float(active[slots].mean()), finite_inside_fraction=float(inside[slots].mean()), moved_vertices=int((np.linalg.norm(displacement, axis=1) > 1e-12).sum()),
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
            limitations='Separate radial process: column-axis centre interpretation and .22 coefficient are our reconstruction; no outside-nearest grid is used. No guaranteed folds or hierarchy; contacts remain unchecked.' if radial else 'Sampled outside grid is not an exact distance field. Fixed field parameters and finite classifier are our reconstruction. No guaranteed folds or hierarchy; rocky results fail the design test. Contacts remain unchecked.',
            self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication='NOT_CHECKED'))
        print('GENERATED', str(family), gen, len(render_xyz), len(render_tri), 'step', np.linalg.norm(displacement, axis=1).max(),
              'minimum_area', mesh.area_faces.min(), flush=True)


if __name__ == '__main__':
    main()
