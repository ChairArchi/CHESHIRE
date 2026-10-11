"""Selected finite-field follow-up on a retained terminal-fold triangle mesh.

Reuse the existing finite Mandelbulb classifier, outside grid and reflection
helpers. All generations keep the source topology; no triangle is subdivided.
This is a bounded IAAC-public-process-inspired reconstruction, not IAAC source
code or a claim that its exact equations or sequence have been disclosed.
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'curved_fold_side_20261011'))
import growth_follow as existing

base = existing.base
variation = existing.variation
window = existing.repair.legacy.window
DEFAULT_ROOT = 'E:/CHESHIRE_DATA/terminal_fold_20261011'
ALGORITHM = 'TERMINAL_SELECTED_FINITE_FIELD_V1'
STAGES = [
    dict(fraction=.45, budget=.08, zones=[
        dict(id='LOWER_X_FLANK', height=.18, span=.13, angle=0., width=.62),
        dict(id='UPPER_Y_ENDPOINT', height=1., span=.10, angle=np.pi / 2, width=.62)]),
    dict(fraction=.35, budget=.05, zones=[
        dict(id='UPPER_Y_FLANK', height=.84, span=.12, angle=np.pi / 2, width=.62),
        dict(id='LOWER_X_ENDPOINT', height=0., span=.10, angle=0., width=.62)]),
    dict(fraction=.25, budget=.035, zones=[
        dict(id='MIDDLE_DIAGONAL_BAND', height=.55, span=.13, angle=np.pi / 4, width=.40)]),
]
FOLD_FIRST_STAGES = [
    dict(fraction=.55, budget=.14, zones=[
        dict(id='BROAD_LOWER_X', height=.20, span=.25, angle=0., width=.90)]),
    dict(fraction=.45, budget=.12, zones=[
        dict(id='BROAD_UPPER_Y', height=.80, span=.25, angle=np.pi / 2, width=.90)]),
    dict(fraction=.35, budget=.10, zones=[
        dict(id='BROAD_MIDDLE_DIAGONAL', height=.53, span=.26, angle=np.pi / 4, width=.90)]),
]


def checkpoint_path(value):
    path = Path(value).resolve()
    return path / 'checkpoint.npz' if path.is_dir() else path


def load_source(path):
    with np.load(path, allow_pickle=False) as saved:
        missing = {'xyz', 'faces', 'chart', 'memory', 'valley_protection'} - set(saved.files)
        if missing:
            raise ValueError('Source checkpoint lacks required arrays: ' + ', '.join(sorted(missing)))
        arrays = {key: saved[key].copy() for key in ('xyz', 'faces', 'chart', 'memory', 'valley_protection')}
    xyz, tri, chart = (arrays[key] for key in ('xyz', 'faces', 'chart'))
    if xyz.ndim != 2 or xyz.shape[1] != 3 or chart.shape != xyz.shape:
        raise ValueError('Source xyz and chart must be matching N x 3 arrays.')
    if tri.ndim != 2 or tri.shape[1] != 3 or tri.dtype.kind not in 'iu':
        raise ValueError('Source must contain the authoritative N x 3 integer triangles.')
    if tri.min() < 0 or tri.max() >= len(xyz) or not np.isfinite(xyz).all() or not np.isfinite(chart).all():
        raise ValueError('Invalid source coordinates or triangle indices.')
    for key in ('memory', 'valley_protection'):
        value = arrays[key]
        if value.shape != (len(xyz),) or not np.isfinite(value).all() or np.any((value < 0) | (value > 1)):
            raise ValueError(key + ' must contain one finite [0,1] value per source vertex.')
    return arrays


def zone_field(chart, controls):
    theta = np.arctan2(np.abs(chart[:, 2]), np.abs(chart[:, 1]))
    envelope = np.zeros(len(chart))
    for zone in controls['zones']:
        axial = window((chart[:, 0] - zone['height']) / zone['span'], .50, 1.)
        angular = window((theta - zone['angle']) / zone['width'], .60, 1.)
        envelope = np.maximum(envelope, axial * angular)
    return envelope


def fold_first_protection(source_path, chart, pairs):
    """Use distinct legacy tags, never the merged GEO pleat-envelope memory."""
    fields_path = source_path.parent / 'operation_fields.npz'
    if fields_path.exists():
        with np.load(fields_path, allow_pickle=False) as fields:
            if {'macro_protection', 'valley_protection'} <= set(fields.files):
                macro, valley = (fields[key].copy() for key in ('macro_protection', 'valley_protection'))
            else:
                macro = valley = None
    else:
        macro = valley = None
    origin = str(fields_path)
    if macro is None:
        # Existing exact midpoint adapter transfers tags only; candidate faces
        # and XYZ are never replaced by this temporary sampling mesh.
        legacy_path = Path(existing.repair.ROOT) / 'W06_SYMMETRIC_SMOOTH/G01/checkpoint.npz'
        with np.load(legacy_path, allow_pickle=False) as legacy:
            _, _, tags = trimesh.remesh.subdivide(legacy['xyz'], legacy['faces'], vertex_attributes={
                'macro': legacy['memory'][:, None], 'valley': legacy['valley_protection'][:, None],
                'chart': legacy['chart']})
        distance, ids = cKDTree(tags['chart']).query(chart)
        if distance.max() > 1e-9:
            raise ValueError('Fold-first legacy tags lack exact midpoint chart correspondence.')
        macro, valley = tags['macro'][ids, 0], tags['valley'][ids, 0]
        origin = str(legacy_path) + ' through existing exact midpoint attribute adapter'
    for value in (macro, valley):
        if value.shape != (len(chart),) or not np.isfinite(value).all() or np.any((value < 0) | (value > 1)):
            raise ValueError('Invalid separate legacy protection tags for fold-first mode.')
    # Retain the deep centre, while allowing the broad cup opening to change.
    distance_to_valley = np.arctan2(np.abs(chart[:, 1]), np.abs(chart[:, 2]))
    valley *= window(distance_to_valley, .015, .075)
    valley[np.linalg.norm(chart[:, 1:], axis=1) < .99] = 0
    def narrow(value):
        t = np.clip((value - .88) / (.98 - .88), 0, 1)
        value = t * t * (3 - 2 * t)
        for ids in pairs:
            value = np.maximum(value, value[ids])
        return value
    macro, valley = narrow(macro), narrow(valley)
    policy = dict(mode='FOLD_FIRST', tag_source=origin, tag_smoothstep=[.88, .98],
                  valley_centre_angular_corridor=[.015, .075],
                  mask_symmetry='Maximum of exact reflected mask partners; no coordinate averaging',
                  pleat_envelope_protection=False, previous_field_footprint_holdout=False,
                  priority='Major folds and repeated field deformation before fine pleat retention')
    return macro, valley, policy


def outside_trees(cfg, root):
    # Use exactly the earlier field cache/classification and plane restrictions.
    _, fieldpath = variation.grid(cfg, base.ArtifactRoot(root))
    with np.load(Path(fieldpath) / 'outside_grid.npz') as saved:
        points = saved['points']
    points = points[(points[:, 0] >= 0) & (points[:, 1] >= -1e-12)].copy()
    points[np.abs(points[:, 1]) < 1e-12, 1] = 0
    trees = []
    for px, py in ((False, False), (True, False), (False, True), (True, True)):
        choose = np.ones(len(points), bool)
        if px:
            choose &= points[:, 0] == 0
        if py:
            choose &= points[:, 1] == 0
        subset = points[choose]
        if not len(subset):
            raise ValueError('Outside grid lacks a required symmetry-plane subset.')
        trees.append((px, py, cKDTree(subset), subset))
    return trees, fieldpath


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Terminal candidate checkpoint.npz or its folder.')
    parser.add_argument('--output-root', default=DEFAULT_ROOT)
    parser.add_argument('--stages', type=int, choices=(1, 2, 3), default=2,
                        help='Run through this stage; matching completed stages are reused.')
    parser.add_argument('--fold-first', action='store_true',
                        help='Broader overlapping field zones; protect only narrow macro/valley cores; write FOLD_FIRST.')
    args = parser.parse_args()
    source_path = checkpoint_path(args.source)
    root = Path(args.output_root).resolve()
    source = load_source(source_path)
    birth, tri, chart = (source[key] for key in ('xyz', 'faces', 'chart'))
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    pairs = existing.symmetry(chart)
    macro, valley = source['memory'], source['valley_protection']
    protection_policy = None
    if args.fold_first:
        macro, valley, protection_policy = fold_first_protection(source_path, chart, pairs)
    protection = np.maximum(macro, valley)
    core = protection >= 1 - 1e-12
    family = 'FOLD_FIRST' if args.fold_first else 'FIELD_FOLLOW'
    stages = FOLD_FIRST_STAGES if args.fold_first else STAGES
    source_symmetry = []
    sortrows = lambda a: a[np.lexsort((a[:, 2], a[:, 1], a[:, 0]))]
    source_triangles = sortrows(np.sort(tri, axis=1))
    reflected_triangle_sets = []
    for axis, ids in enumerate(pairs):
        sign = np.ones(3); sign[axis] = -1
        error = float(np.linalg.norm(birth - birth[ids] * sign, axis=1).max())
        source_symmetry.append(error)
        if error > 1e-9:
            raise ValueError('Source fails geometric X/Y reflection; do not normalize it here.')
        if np.max(np.abs(protection - protection[ids])) > 1e-9:
            raise ValueError('Source protection masks fail X/Y reflection.')
        matched = bool(np.array_equal(source_triangles, sortrows(np.sort(ids[tri], axis=1))))
        reflected_triangle_sets.append(matched)
        if not matched:
            raise ValueError('Source triangles fail X/Y reflection; topology cannot be repaired here.')
    canonical = chart.copy(); canonical[:, 1:] = np.abs(canonical[:, 1:])
    distance, canonical_ids = cKDTree(chart).query(canonical)
    if distance.max() > 1e-9:
        raise ValueError('Source chart has no exact canonical-quarter correspondence.')
    quarter = np.unique(canonical_ids)
    slots = np.searchsorted(quarter, canonical_ids)
    qchart = chart[quarter]
    cfg = variation.recipe('TERMINAL_FOLD_RETENTION', fraction=.45, powers=[5, 6],
                           centres=[2.5, 7.5], axial=2.8, scales=[1.6, 1.6])
    xyz = birth.copy(); footprint = np.zeros(len(birth)); trees = None
    for gen in range(1, args.stages + 1):
        controls = stages[gen - 1]
        folder = root / family / f'G{gen:02}'
        signature = dict(algorithm=ALGORITHM, source_sha256=source_hash,
                         field_recipe=cfg, stage_controls=controls, stage=gen)
        if args.fold_first:
            signature.update(algorithm=ALGORITHM + '_FOLD_FIRST_V1', protection_policy=protection_policy)
        if folder.exists() and any(folder.iterdir()):
            meta_path = folder / 'generation.json'
            if not meta_path.exists() or json.loads(meta_path.read_text(encoding='utf8')).get('signature') != signature:
                raise FileExistsError('Existing stage is incomplete or belongs to different source/controls: ' + str(folder))
            with np.load(folder / 'checkpoint.npz', allow_pickle=False) as saved:
                if not np.array_equal(saved['faces'], tri) or not np.array_equal(saved['chart'], chart):
                    raise ValueError('Saved field stage changed the source topology or chart.')
                xyz = saved['xyz'].copy(); footprint = saved['field_memory'].copy()
            if not (folder / 'operation_fields.npz').exists() or not (folder / 'gate.ply').exists():
                raise FileExistsError('Existing stage is missing output artifacts: ' + str(folder))
            print('REUSED', family, gen, flush=True)
            continue
        if trees is None:
            trees, fieldpath = outside_trees(cfg, root)
        incoming = xyz.copy()
        p = incoming[quarter].copy(); physical_sign = np.where(p[:, :2] < 0, -1, 1)
        p[:, :2] = np.abs(p[:, :2])
        inside = variation.classify(p, cfg)
        zone = zone_field(qchart, controls)
        attenuation = (1 - protection[quarter]) * zone
        if not args.fold_first:
            attenuation *= 1 - footprint[quarter]
        active = inside & (attenuation > 0) & (np.linalg.norm(p[:, :2], axis=1) > 1e-10)
        xp = np.abs(qchart[:, 1]) < 1e-12; yp = np.abs(qchart[:, 2]) < 1e-12
        move = np.zeros_like(p); target = p.copy()
        for px, py, tree, subset in trees:
            ids = np.flatnonzero(active & (xp == px) & (yp == py))
            if not len(ids):
                continue
            _, where = tree.query(p[ids]); target[ids] = subset[where]
            if variation.classify(target[ids], cfg).any():
                raise ValueError('Nearest target is not outside the actual finite classifier.')
            move[ids] = controls['fraction'] * (target[ids] - p[ids])
        magnitude = np.linalg.norm(move, axis=1)
        move *= np.minimum(1, controls['budget'] / np.maximum(magnitude, 1e-15))[:, None]
        move *= attenuation[:, None]
        move[:, :2] *= physical_sign
        actual = move[slots].copy()
        actual[:, :2] *= np.where(chart[:, 1:] < 0, -1, 1)
        # Reflect the displacement, preserving the source XYZ exactly in cores.
        existing.reflect(actual, chart, pairs)
        xyz = incoming + actual
        previous_footprint = footprint.copy()
        if not args.fold_first:
            footprint = np.maximum(footprint, (zone * active)[slots])
        mesh = trimesh.Trimesh(xyz, tri, process=False)
        if not np.isfinite(xyz).all() or not mesh.is_watertight or not mesh.is_winding_consistent:
            raise ValueError('Nonfinite or topologically invalid field result; no repair.')
        symmetry_errors = []
        for axis, ids in enumerate(pairs):
            sign = np.ones(3); sign[axis] = -1
            symmetry_errors.append(float(np.linalg.norm(xyz - xyz[ids] * sign, axis=1).max()))
        if max(symmetry_errors) > 1e-9 or (core.any() and not np.array_equal(xyz[core], birth[core])):
            raise ValueError('Reflection or exact protected-core retention failed.')
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder / 'geometry.npz', xyz=xyz, faces=tri)
        np.savez_compressed(folder / 'checkpoint.npz', xyz=xyz, faces=tri, chart=chart,
                            memory=macro, valley_protection=valley,
                            protection=protection, field_memory=footprint)
        extra_fields = dict(macro_protection=macro, valley_protection=valley) if args.fold_first else {}
        np.savez_compressed(folder / 'operation_fields.npz', finite_inside=inside[slots],
                            active=active[slots], selected_zone=zone[slots],
                            protection=protection, previous_field_memory=previous_footprint,
                            effective_attenuation=attenuation[slots], canonical_query_xyz=p[slots],
                            canonical_nearest_outside_target=target[slots],
                            displacement=actual, canonical_vertex=canonical_ids, **extra_fields)
        mesh.export(folder / 'gate.ply')
        shutil.copy2(__file__, folder / 'field_follow_recipe.py')
        delta = np.linalg.norm(xyz - birth, axis=1)
        base.dump(folder / 'generation.json', dict(signature=signature, candidate=family,
            stage=f'G{gen:02}', source=str(source_path),
            parent=str(source_path) if gen == 1 else str(folder.parent / f'G{gen-1:02}' / 'checkpoint.npz'),
            operation='Selected protected nearest finite-outside movement on unchanged source triangles',
            field_recipe=cfg, field_cache=fieldpath, field_passes_total=gen, subdivision_passes_total=0,
            field_generations='Fixed source topology; no additional triangle splits because of minimum-area risk',
            controls=controls, protection_policy=protection_policy,
            earlier_field_zone_retention='Disabled; deliberate overlapping repeated deformation' if args.fold_first else 'Multiply by 1 - previous_field_memory',
            cap_policy='Selected endpoint sectors eligible; axis centre excluded; no endpoint XYZ or Z lock',
            moved_vertices=int((np.linalg.norm(actual, axis=1) > 1e-12).sum()),
            active_fraction=float(active[slots].mean()),
            maximum_actual_step=float(np.linalg.norm(actual, axis=1).max()),
            source_core_vertices=int(core.sum()), source_core_max_movement=float(delta[core].max()) if core.any() else 0.,
            source_vertex_RMS_movement=float(np.sqrt(np.mean(delta ** 2))),
            physical_vertices=len(xyz), physical_triangles=len(tri), minimum_triangle_area=float(mesh.area_faces.min()),
            minimum_area_threshold=1e-12, minimum_area_pass=bool(mesh.area_faces.min() > 1e-12),
            source_reflection_error=source_symmetry, geometric_reflection_error=symmetry_errors,
            reflected_triangle_sets_identical=reflected_triangle_sets,
            symmetry='Canonical quarter queries and reflected displacement; no coordinate averaging',
            separate_geometric_smoothing=False, CC_coordinate_averaging=False, random_noise=False,
            source_status='CHESHIRE finite Mandelbulb reconstruction inspired by the public IAAC process; not IAAC original code',
            limitations='Finite sampled outside targets, not an exact distance field; local mask is authored; no collision repair or fold-success guarantee. If nearest-grid growth remains rocky, it fails this design test regardless of pleat retention.',
            self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication='NOT_CHECKED'))
        print('GENERATED', family, gen, len(xyz), len(tri), 'step', np.linalg.norm(actual, axis=1).max(),
              'minimum_area', mesh.area_faces.min(), flush=True)


if __name__ == '__main__':
    main()
