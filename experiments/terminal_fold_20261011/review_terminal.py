"""Matched actual-mesh terminal boards and bounded movement diagnostics.

No geometry generation. Validation runs only when explicitly selected.
Material-chart correspondence uses exact existing vertices or their triangle
midpoints; it never substitutes nearest positions on the deformed surface.
"""
from pathlib import Path
import argparse
import contextlib
import io
import sys

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'curved_fold_side_20261011'))
import review

DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/terminal_fold_20261011')
BASELINE = review.ROOT / 'GEO01_FAN_MEMORY/G03'
ZS = (.2, .7, 5.9, 9.4, 9.9)


def checkpoint(folder):
    with np.load(folder / 'checkpoint.npz') as data:
        return {key: data[key] for key in data.files}


def chart_transfer(source, target, attributes):
    """Transfer through at most one exact triangle-midpoint adapter."""
    xyz, faces, chart = source['xyz'], source['faces'], source['chart']
    attrs = {key: np.asarray(value).reshape(len(chart), -1)
             for key, value in attributes.items()}
    for level in (0, 1):
        distance, ids = cKDTree(chart).query(target)
        if float(distance.max()) < 1e-9:
            return xyz[ids], {key: value[ids, 0] for key, value in attrs.items()}, level
        if level == 0:
            xyz, faces, fields = trimesh.remesh.subdivide(
                xyz, faces, vertex_attributes={'chart': chart, **attrs})
            chart = fields.pop('chart')
            attrs = fields
    raise ValueError('Target chart has no exact source/midpoint correspondence')


def baseline_data(folder):
    source = checkpoint(folder)
    tags = {'fan_core': source.get('memory', np.zeros(len(source['xyz'])))}
    legacy = checkpoint(review.ROOT / 'W06_SYMMETRIC_SMOOTH/G01')
    _, transferred, _ = chart_transfer(legacy, source['chart'], {
        'macro_core': legacy['memory'], 'valley_core': legacy['valley_protection']})
    tags.update(transferred)
    return source, tags


def terminal_extents(xyz, chart):
    result = {}
    for name, mask in [('base', chart[:, 0] < .13),
                       ('capital', chart[:, 0] > .87)]:
        points = xyz[mask]
        result[name] = dict(vertices=int(mask.sum()),
                            minimum_xyz=points.min(axis=0).tolist(),
                            maximum_xyz=points.max(axis=0).tolist(),
                            span_xyz=np.ptp(points, axis=0).tolist()) if len(points) else None
    return result


def movement_summary(delta, mask):
    values = delta[mask]
    return dict(vertices=int(mask.sum()), maximum=float(values.max()),
                rms=float(np.sqrt(np.mean(values ** 2)))) if len(values) else dict(vertices=0)


def meso_movement(xyz, faces, source_xyz, chart, fields):
    delta = np.linalg.norm(xyz - source_xyz, axis=1)
    # A saved authored mask takes precedence over the declared fallback band.
    name = next((key for key in ('meso_zone', 'meso_envelope', 'meso_mask')
                 if key in fields and fields[key].size == len(xyz)), None)
    outer = np.linalg.norm(chart[:, 1:], axis=1) >= .99
    if name:
        zone = np.asarray(fields[name]).reshape(-1) > 1e-8
        scope = 'Saved ' + name + ' > 1e-8, exterior material shell'
    else:
        zone = (chart[:, 0] > .20) & (chart[:, 0] < .85)
        scope = 'Fallback .20 < material s < .85, exterior shell; includes any central deformation'
    zone &= outer
    active = zone & (delta > .01)
    source_mesh = trimesh.Trimesh(source_xyz, faces, process=False)
    weights = np.bincount(faces.ravel(),
                          weights=np.repeat(source_mesh.area_faces / 3, 3),
                          minlength=len(xyz))
    denominator = float(weights[zone].sum())
    components = []
    ids = np.flatnonzero(active)
    if len(ids):
        edges = source_mesh.edges_unique
        edges = edges[active[edges].all(axis=1)]
        local = np.full(len(xyz), -1, dtype=np.int64)
        local[ids] = np.arange(len(ids))
        pairs = local[edges]
        graph = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])),
                           shape=(len(ids), len(ids))).tocsr()
        count, labels = connected_components(graph, directed=False)
        sizes = np.bincount(labels, minlength=count)
        areas = np.bincount(labels, weights=weights[ids], minlength=count)
        for index in np.argsort(areas)[::-1][:5]:
            components.append(dict(vertices=int(sizes[index]),
                                   reference_area_weight=float(areas[index]),
                                   zone_area_fraction=float(areas[index] / denominator)
                                   if denominator else None))
    return dict(scope=scope, displacement_threshold=.01,
                zone_vertices=int(zone.sum()), moved_vertices=int(active.sum()),
                moved_vertex_fraction=float(active.sum() / zone.sum()) if zone.any() else None,
                moved_reference_area_fraction=float(weights[active].sum() / denominator)
                if denominator else None, connected_moved_components=components,
                maximum_movement=float(delta[zone].max()) if zone.any() else None,
                interpretation='Connected moved regions quantify support, not proof of new grooves or aesthetic success.')


def section_board(out, models):
    size = 340
    segments = {(label, z): trimesh.intersections.mesh_plane(mesh, [0, 0, 1], [0, 0, z])
                for label, mesh in models for z in ZS}
    extent = max((float(np.abs(value[:, :, :2]).max()) for value in segments.values()
                  if len(value)), default=1.)
    extent = max(.5, np.ceil(extent * 10) / 10)
    scale = (size / 2 - 36) / extent
    canvas = Image.new('RGB', (size * len(models), 60 + size * len(ZS) + 40), '#f6f5ef')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(review.FONT, 17)
    for column, (label, _) in enumerate(models):
        draw.text((column * size + 12, 15), label, fill='#203039', font=font)
        for row, z in enumerate(ZS):
            ox, oy = column * size + size / 2, 60 + row * size + size / 2
            draw.text((column * size + 10, 68 + row * size), f'Physical Z={z:g}', fill='#203039', font=font)
            draw.line((ox - size * .4, oy, ox + size * .4, oy), fill='#d8d6ce')
            draw.line((ox, oy - size * .4, ox, oy + size * .4), fill='#d8d6ce')
            for segment in segments[label, z]:
                draw.line([(ox + scale * p[0], oy - scale * p[1]) for p in segment],
                          fill='#245e68', width=1)
            if not len(segments[label, z]):
                draw.text((ox - 45, oy + 15), 'No section', fill='#6b6b65', font=font)
    draw.text((12, canvas.height - 29), f'Common XY scale: {scale:.2f} px/unit. All actual section segments, including intersections.',
              fill='#203039', font=font)
    canvas.save(out / 'terminal_actual_sections.png')
    return dict(physical_z=list(ZS), xy_pixels_per_unit=scale, xy_half_extent=extent,
                segment_counts={label: {str(z): len(segments[label, z]) for z in ZS}
                                for label, _ in models})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--baseline', type=Path, default=BASELINE)
    parser.add_argument('--folders', nargs='+', required=True)
    parser.add_argument('--validate', nargs='*', default=None, metavar='FOLDER',
                        help='Validate only these selected folders; with no values, validate --folders.')
    args = parser.parse_args()
    selected = args.folders if args.validate == [] else (args.validate or [])
    if not set(selected).issubset(args.folders):
        parser.error('--validate names must also appear in --folders')
    out = args.root / 'review'
    out.mkdir(parents=True, exist_ok=True)
    source, tags = baseline_data(args.baseline)
    models = [('GEO01 G3 source', trimesh.Trimesh(source['xyz'], source['faces'], process=False))]
    rows = [('GEO01 G3 source', [args.baseline / 'preview' / (view + '.png') for view in review.VIEWS])]
    results = {'baseline': dict(folder=str(args.baseline),
                                terminal_extents=terminal_extents(source['xyz'], source['chart']))}
    for name in args.folders:
        folder = args.root / name
        data = checkpoint(folder)
        xyz, faces, chart = data['xyz'], data['faces'], data['chart']
        source_xyz, transferred, level = chart_transfer(source, chart, tags)
        delta = np.linalg.norm(xyz - source_xyz, axis=1)
        fields = dict(data)
        if (folder / 'operation_fields.npz').exists():
            with np.load(folder / 'operation_fields.npz') as values:
                fields.update({key: values[key] for key in values.files})
        central = (chart[:, 0] >= .13) & (chart[:, 0] <= .87)
        protected = {key: movement_summary(delta, central & (value >= 1 - 1e-12))
                     for key, value in transferred.items()}
        for key in ('macro_protection', 'valley_protection', 'pleat_protection'):
            if key in fields and fields[key].size == len(xyz):
                protected['declared_' + key] = movement_summary(
                    delta, central & (np.asarray(fields[key]).reshape(-1) >= 1 - 1e-12))
        results[name] = dict(source_midpoint_adapter_passes=level,
                             terminal_extents=terminal_extents(xyz, chart),
                             meso_movement=meso_movement(xyz, faces, source_xyz, chart, fields),
                             central_source_protected_movement=protected,
                             maximum_total_movement=float(delta.max()))
        models.append((name, trimesh.Trimesh(xyz, faces, process=False)))
        rows.append((name, [folder / 'preview' / (view + '.png') for view in review.VIEWS]))
    review.board(out / 'terminal_comparison.png', review.VIEWS, rows, 650)
    results['actual_sections'] = section_board(out, models)
    results['scope'] = ('Terminal extents use material s < .13 and s > .87. '
                        'Movement is relative to GEO01 G3 through exact material charts. '
                        'Fixed core coordinates do not certify preserved valley width, fold angle, or fabrication.')
    review.dump(out / 'terminal_metrics.json', results)
    if selected:
        checks = {}
        for name in selected:
            with contextlib.redirect_stdout(io.StringIO()):
                checks[name] = review.validate(args.root / name)
            check = checks[name]
            print('VALIDATE', name, 'area_pass', check['minimum_area_pass'],
                  'X/Y', check['mirror_max_distance'], check['front_back_reflection']['maximum_vertex_distance'],
                  check['self_intersection'], flush=True)
        review.dump(out / 'terminal_validation.json', checks)
    print('TERMINAL REVIEW COMPLETE', len(args.folders), 'candidates', str(out), flush=True)


if __name__ == '__main__':
    main()
