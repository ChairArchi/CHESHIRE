"""Bounded existing weighted Doo-Sabin + finite n4 field comparison.

Imports the tested closed-manifold COMPAS DS operator; no new subdivision
engine. Positive STANDARD lineage carries material chart independently of
signed weighted geometry. Actual FACE/EDGE/VERTEX families select next-pass
weights. Render fans are not controls. No original IAAC DS-code claim.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil

import numpy as np
import trimesh
from compas.datastructures import Mesh
from cheshire.weighted_doosabin import weighted_doosabin_once
from cheshire.execution import ExecutionBudget

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('dual_probe_full_loop', HERE / 'full_loop.py')
full = importlib.util.module_from_spec(spec)
spec.loader.exec_module(full)
prior = full.prior
WEIGHTS = dict(w1_face=.65, w1_edge=.35, w1_vertex=.35,
               w10_face=-.12, w10_edge=.10, w10_vertex=.06)
ALGORITHM = 'EXISTING_WEIGHTED_DS_FINITE_N4_LOOP_V1'


def control_mesh(xyz, polygons):
    mesh = Mesh()
    for v, p in enumerate(xyz):
        mesh.add_vertex(key=v, x=float(p[0]), y=float(p[1]), z=float(p[2]))
    for f, polygon in enumerate(polygons):
        mesh.add_face([int(v) for v in polygon], fkey=f)
    return mesh


def padded(polygons, fill=-1):
    sizes = np.asarray([len(p) for p in polygons], dtype=np.int64)
    result = np.full((len(polygons), int(sizes.max())), fill, dtype=np.int64)
    for i, polygon in enumerate(polygons):
        result[i, :len(polygon)] = polygon
    return result, sizes


def edges(polygons):
    return np.unique(np.asarray([sorted((p[j], p[(j + 1) % len(p)]))
        for p in polygons for j in range(len(p))], dtype=np.int64), axis=0)


def physical_fans(xyz, polygons, chart):
    n = len(xyz)
    centre = np.asarray([xyz[p].mean(0) for p in polygons])
    cchart = np.asarray([chart[p].mean(0) for p in polygons])
    tri = np.asarray([[p[j], p[(j + 1) % len(p)], n + f]
        for f, p in enumerate(polygons) for j in range(len(p))], dtype=np.int64)
    return np.vstack([xyz, centre]), tri, np.vstack([chart, cchart])


def load_poly(folder):
    with np.load(folder / 'control_poly.npz', allow_pickle=False) as d:
        polygons = [row[:int(size)].tolist() for row, size in zip(d['polygons'], d['sizes'])]
        families = {f: dict(class_=str(label), generation=int(d['generation']))
                    for f, label in enumerate(d['families'])}
        for value in families.values():
            value['class'] = value.pop('class_')
        return d['xyz'].copy(), polygons, d['chart'].copy(), families


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', default='E:/CHESHIRE_DATA/fold_band_growth_20261011/inputs/SPAN_SPARSE/G00')
    p.add_argument('--output-root', default='E:/CHESHIRE_DATA/fold_band_growth_20261011')
    p.add_argument('--name', default='DUAL_FIELD_LOOP')
    p.add_argument('--stages', choices=(1, 2, 3), type=int, default=2)
    args = p.parse_args()
    source = Path(args.source).resolve()
    root = Path(args.output_root).resolve()
    family = Path(args.name)
    if family.is_absolute() or '..' in family.parts:
        raise ValueError('Output family must remain beneath output root.')
    control = source / 'control_quad.npz'
    xyz, quads, chart = prior.load_quads(control)
    polygons = quads.tolist()
    source_count = (len(xyz), len(polygons))
    families = None
    cfg = prior.field_recipe('n4', fraction=.55)
    cfg['iterations'] = 18
    trees = None
    for gen in range(1, args.stages + 1):
        folder = root / family / f'G{gen:02}'
        budget = (.35, .28, .22)[gen - 1]
        signature = dict(algorithm=ALGORITHM, source=str(control), stage=gen,
            weights=WEIGHTS, field_recipe=cfg, field_fraction=.55, field_budget=budget,
            local_target_factor=gen, source_control_vertices=source_count[0],
            source_control_faces=source_count[1],
            source_control_bytes=control.stat().st_size)
        if folder.exists() and any(folder.iterdir()):
            meta = json.loads((folder / 'generation.json').read_text(encoding='utf8'))
            if meta['signature'] != signature:
                raise FileExistsError('Conflicting saved DS input/recipe: ' + str(folder))
            xyz, polygons, chart, families = load_poly(folder)
            print('REUSED', args.name, gen, flush=True)
            continue
        incoming = control_mesh(xyz, polygons)
        step = weighted_doosabin_once(incoming, WEIGHTS, face_families=families,
            budget=ExecutionBudget(50000, 50000, 3), current_generation=gen - 1)
        keys = sorted(step.mesh.vertices())
        index = {key: i for i, key in enumerate(keys)}
        refined = np.asarray([step.mesh.vertex_coordinates(key) for key in keys])
        inherited_chart = np.asarray([sum((chart[ref.key] * ref.weight
            for ref in step.lineage.vertex_parents[key]), start=np.zeros(3)) for key in keys])
        fkeys = list(step.mesh.faces())
        polygons = [[index[v] for v in step.mesh.face_vertices(f)] for f in fkeys]
        families = {i: step.face_families[f] for i, f in enumerate(fkeys)}
        control_edges = edges(polygons)
        if trees is None:
            trees, field_cache = prior.helpers.outside_trees(cfg, root)
        xyz, fields, field_log = full.apply_field(refined, control_edges,
            inherited_chart, cfg, trees, .55, budget, gen)
        chart = inherited_chart
        render_xyz, render_tri, render_chart = physical_fans(xyz, polygons, chart)
        _, sym_error, tri_match = prior.reflection_state(render_xyz, render_tri, render_chart)
        actual = trimesh.Trimesh(render_xyz, render_tri, process=False)
        if not np.isfinite(render_xyz).all() or not actual.is_watertight or not actual.is_winding_consistent:
            raise ValueError('Actual DS fan surface is nonfinite or topologically invalid; no repair.')
        min_area = float(actual.area_faces.min())
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder / 'geometry.npz', xyz=render_xyz, faces=render_tri)
        np.savez_compressed(folder / 'checkpoint.npz', xyz=render_xyz, faces=render_tri, chart=render_chart)
        poly_array, sizes = padded(polygons)
        labels = np.asarray([families[f]['class'] for f in range(len(polygons))])
        np.savez_compressed(folder / 'control_poly.npz', xyz=xyz, polygons=poly_array,
            sizes=sizes, chart=chart, families=labels, generation=gen)
        parent_ids = [[ref.key for ref in step.lineage.vertex_parents[key]] for key in keys]
        parent_weights = [[ref.weight for ref in step.lineage.vertex_parents[key]] for key in keys]
        parents, parent_sizes = padded(parent_ids)
        weights = np.zeros_like(parents, dtype=float)
        for i, row in enumerate(parent_weights):
            weights[i, :len(row)] = row
        np.savez_compressed(folder / 'ds_lineage.npz', parents=parents,
            parent_sizes=parent_sizes, weights=weights,
            chart=chart, corner_parent=np.asarray([step.corner_parents[key] for key in keys]))
        np.savez_compressed(folder / 'operation_fields.npz', pre_field_xyz=refined, **fields)
        actual.export(folder / 'gate.ply')
        shutil.copy2(__file__, folder / 'dual_probe_recipe.py')
        prior.base.dump(folder / 'ds_operator_log.json', step.metadata)
        prior.base.dump(folder / 'generation.json', dict(signature=signature,
            candidate=args.name, stage=f'G{gen:02}', source=str(source / 'checkpoint.npz'),
            parent=str(source / 'checkpoint.npz') if gen == 1 else str(folder.parent / f'G{gen-1:02}' / 'checkpoint.npz'),
            operation='Existing weighted Doo-Sabin face-corner placement/connectivity, then existing finite nearest-outside field on all resulting controls',
            weights=WEIGHTS, field_recipe=cfg, field_log=field_log,
            field_passes_total=gen, subdivision_passes_total=gen, paired_cycles_total=gen,
            physical_vertices=len(render_xyz), physical_triangles=len(render_tri),
            control_vertices=len(xyz), control_faces=len(polygons),
            polygon_degrees=dict(zip(*[[str(v) for v in np.unique(sizes)], [int((sizes == v).sum()) for v in np.unique(sizes)]])),
            input_family_counts=step.metadata['input_family_counts'],
            output_family_counts=step.metadata['family_counts'],
            unsupported_weighted_polygon_fallbacks=step.metadata['fallback_faces'],
            lineage='Existing positive STANDARD DS sampling lineage; separate from signed weighted geometry',
            field_topology_check='Canonical control edge graph; actual physical triangle reflection checked separately',
            physical_surface='Explicit arithmetic mean polygon-centre fans; render-only fan centres are never next controls',
            minimum_triangle_area=min_area, minimum_area_threshold=1e-12, minimum_area_pass=min_area > 1e-12,
            geometric_reflection_error=sym_error, reflected_triangle_sets_identical=tri_match,
            watertight=bool(actual.is_watertight), winding_consistent=bool(actual.is_winding_consistent),
            components_before=step.metadata['components_before'], components_after=step.metadata['components_after'],
            separate_geometric_smoothing=False, authored_return=False, feature_memory=False,
            DS_coordinate_rule='Weighted corner averaging is intrinsic DS placement; no separate XYZ smoothing',
            source_status='CHESHIRE tested DS operator plus finite Mandelbulb reconstruction; no claim original IAAC used DS',
            self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication='NOT_CHECKED'))
        print('GENERATED', args.name, gen, len(render_xyz), len(render_tri),
              'control', len(xyz), len(polygons), 'minarea', min_area,
              'fallback', step.metadata['fallback_faces'], flush=True)


if __name__ == '__main__':
    main()
