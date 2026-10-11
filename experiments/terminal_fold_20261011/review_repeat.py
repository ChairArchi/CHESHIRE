"""Finite actual-quad progression review; no material-chart transfer or generation.

The two matched inputs and their G1/G2/G3 descendants stay separate from the
earlier terminal controls. Expensive core validation is opt-in and final-only.
"""
from pathlib import Path
import argparse
import contextlib
import io
import json
import sys

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'curved_fold_side_20261011'))
import review

ROOT = Path('E:/CHESHIRE_DATA/terminal_fold_20261011')
SEQUENCES = (
    ('IAAC_REPEAT', 'IAAC_QUAD_INPUT/G00', 'Folded quad input'),
    ('CYLINDER_REPEAT', 'IAAC_CYLINDER_MATCHED_QUAD_INPUT/G00', 'Matched cylinder quad input'),
)


def views(folder):
    return [folder / 'preview' / (view + '.png') for view in review.VIEWS]


def stage_metrics(folder):
    meta = json.loads((folder / 'generation.json').read_text(encoding='utf8'))
    # Only small numerical/boolean metadata; recipes and array audits stay out.
    keep = ('vertices', 'triangles', 'quads', 'minimum_', 'movement', 'moved',
            'active_fraction', 'actual_step', 'passes_total', 'quad_control')
    result = {key: value for key, value in meta.items()
              if any(token in key for token in keep)
              and isinstance(value, (int, float, bool, type(None)))}
    control_vertices = meta.get('control_vertices')
    vertices = control_vertices or meta.get('physical_vertices', meta.get('vertices'))
    moved = meta.get('moved_vertices')
    if vertices and moved is not None:
        key = 'moved_control_vertex_fraction_from_json' if control_vertices else 'moved_vertex_fraction_from_json'
        result[key] = moved / vertices
    previous_control = meta.get('previous_control_vertices')
    previous = previous_control or meta.get('previous_vertices')
    previous_moved = meta.get('previous_control_vertices_moved') if previous_control else meta.get('previous_vertices_moved')
    if previous and previous_moved is not None:
        key = 'previous_control_vertex_moved_fraction_from_json' if previous_control else 'previous_vertex_moved_fraction_from_json'
        result[key] = previous_moved / previous
    # The G0 writer predates explicit control counts. Read only the small G0
    # control adapter when its numerical count is absent; never infer from fans.
    if not any('quad' in key and isinstance(value, int) and not isinstance(value, bool)
               for key, value in result.items()) and (folder / 'control_quad.npz').exists():
        with np.load(folder / 'control_quad.npz') as control:
            result['control_quads_from_saved_adapter'] = len(control['faces'])
            result['control_vertices_from_saved_adapter'] = len(control['xyz'])
    result['metadata_source'] = str(folder / 'generation.json')
    return result


def actual_sections(path, models, zs, size=310):
    segments = {}
    # Load one mesh at a time; later generations can have many actual triangles.
    for label, folder in models:
        mesh = review.mesh(folder)
        for z in zs:
            segments[label, z] = trimesh.intersections.mesh_plane(mesh, [0, 0, 1], [0, 0, z])
        del mesh
    extent = max((float(np.abs(value[:, :, :2]).max()) for value in segments.values()
                  if len(value)), default=1.)
    extent = max(.5, np.ceil(extent * 10) / 10)
    scale = (size / 2 - 32) / extent
    canvas = Image.new('RGB', (size * len(models), 56 + size * len(zs) + 36), '#f6f5ef')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(review.FONT, 16)
    for column, (label, _) in enumerate(models):
        draw.text((column * size + 10, 14), label, fill='#203039', font=font)
        for row, z in enumerate(zs):
            ox, oy = column * size + size / 2, 56 + row * size + size / 2
            draw.text((column * size + 10, 64 + row * size), f'Physical Z={z:g}', fill='#203039', font=font)
            draw.line((ox - size * .4, oy, ox + size * .4, oy), fill='#d8d6ce')
            draw.line((ox, oy - size * .4, ox, oy + size * .4), fill='#d8d6ce')
            for segment in segments[label, z]:
                draw.line([(ox + scale * p[0], oy - scale * p[1]) for p in segment],
                          fill='#245e68', width=1)
            if not len(segments[label, z]):
                draw.text((ox - 42, oy + 12), 'No section', fill='#6b6b65', font=font)
    draw.text((10, canvas.height - 27), f'Common XY scale {scale:.2f} px/unit; all actual segments, including intersections.',
              fill='#203039', font=font)
    canvas.save(path)
    return dict(physical_z=list(zs), xy_pixels_per_unit=scale,
                segment_counts={label: {str(z): len(segments[label, z]) for z in zs}
                                for label, _ in models})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--validate', action='store_true',
                        help='Run existing core validation on the two G03 outputs only.')
    parser.add_argument('--endpoint-sections', action='store_true',
                        help='Add a separate small actual-section board at Z=.3 and 9.7.')
    args = parser.parse_args()
    out = args.root / 'review'
    out.mkdir(parents=True, exist_ok=True)
    final_rows, models, metrics = [], [], {}
    for name, source_name, label in SEQUENCES:
        source = args.root / source_name
        stages = [args.root / name / f'G{stage:02}' for stage in (1, 2, 3)]
        folders = [source, *stages]
        review.board(out / (name + '_progression.png'),
                     ['G0 / input', 'G1 / split + field', 'G2 / split + field', 'G3 / split + field'],
                     [(view, [folder / 'preview' / (view + '.png') for folder in folders])
                      for view in review.VIEWS], 500)
        final_rows.extend([(label + ' / G0', views(source)), (name + ' / G3', views(stages[-1]))])
        models.extend([(name.replace('_REPEAT', '') + ' G0', source),
                       (name.replace('_REPEAT', '') + ' G3', stages[-1])])
        measurements = {f'G{stage:02}': stage_metrics(folder) for stage, folder in enumerate(folders)}
        metrics[name] = dict(input=str(source), stages=measurements,
                             all_saved_stages_minimum_area_pass=all(
                                 value.get('minimum_area_pass') is True for value in measurements.values()))
    review.board(out / 'repeat_final_comparison.png', review.VIEWS, final_rows, 650)
    metrics['actual_sections'] = actual_sections(out / 'repeat_actual_sections.png', models, (2.3, 4.5, 6., 7.8))
    if args.endpoint_sections:
        metrics['endpoint_sections'] = actual_sections(out / 'repeat_endpoint_sections.png', models, (.3, 9.7), 250)
    metrics['scope'] = ('Actual saved quad-control surfaces rendered as face-centre triangle fans. '
                        'Progression and metrics use saved stages, with no source-chart transfer. '
                        'Motion/counts come from generation JSON; missing G0 control counts use its saved quad adapter. '
                        'Sections include every intersection segment. Topological closure does not certify fabrication.')
    review.dump(out / 'repeat_metrics.json', metrics)
    if args.validate:
        checks = {}
        for name, _, _ in SEQUENCES:
            with contextlib.redirect_stdout(io.StringIO()):
                checks[name] = review.validate(args.root / name / 'G03')
            check = checks[name]
            print('VALIDATE', name, 'area_pass', check['minimum_area_pass'],
                  'X/Y', check['mirror_max_distance'], check['front_back_reflection']['maximum_vertex_distance'],
                  check['self_intersection'], flush=True)
        review.dump(out / 'repeat_validation.json', checks)
    print('REPEAT REVIEW COMPLETE', '2 sequences / G0-G3', str(out), flush=True)


if __name__ == '__main__':
    main()
