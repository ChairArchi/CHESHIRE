"""Finite eight-family catalogue of saved actual G0-G3 meshes.

This script reads previews and numerical generation metadata. It generates no
geometry, infers no IAAC parameter values, and validates only named G03 finals.
"""
from pathlib import Path
import argparse
import contextlib
import io
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'curved_fold_side_20261011'))
import review

ROOT = Path('E:/CHESHIRE_DATA/terminal_fold_20261011')
FAMILIES = ('IAAC_REPEAT', 'CYLINDER_REPEAT', 'CAT_N4', 'CAT_N8',
            'CAT_THREE', 'CAT_FIVE', 'CAT_RADIAL_IO', 'CAT_CC')
FOLDED_INPUT = 'IAAC_QUAD_INPUT/G00'
CYLINDER_INPUT = 'IAAC_CYLINDER_MATCHED_QUAD_INPUT/G00'


def source_name(family):
    return CYLINDER_INPUT if family == 'CYLINDER_REPEAT' else FOLDED_INPUT


def read_metrics(folder):
    meta = json.loads((folder / 'generation.json').read_text(encoding='utf8'))
    explicit = {'candidate', 'stage', 'operation', 'field_recipe', 'field_mode', 'mode',
                'projection_mode', 'subdivision_mode', 'subdivision_operator',
                'operator_state_frame', 'physical_surface', 'feature_memory',
                'endpoint_lock', 'separate_geometric_smoothing', 'CC_coordinate_averaging',
                'source_status', 'fraction', 'maximum_requested_step'}
    tokens = ('vertices', 'triangles', 'quads', 'minimum_', 'movement', 'moved',
              'active_fraction', 'actual_step', 'passes_total', 'quad_control')
    result = {key: value for key, value in meta.items()
              if key in explicit or (any(token in key for token in tokens)
                                     and isinstance(value, (int, float, bool, type(None))))}
    signature = meta.get('signature', {})
    result['algorithm'] = signature.get('algorithm')
    result['mode'] = next((meta[key] for key in ('field_mode', 'mode', 'projection_mode')
                           if meta.get(key) is not None),
                          signature.get('field_mode', signature.get('mode')))
    if folder.name == 'G00' and (folder / 'control_quad.npz').exists():
        if not result.get('control_quads') or not result.get('control_vertices'):
            with np.load(folder / 'control_quad.npz') as control:
                result['control_quads_from_adapter'] = len(control['faces'])
                result['control_vertices_from_adapter'] = len(control['xyz'])
    result['metadata_source'] = str(folder / 'generation.json')
    return result


def operator_vertex_count(meta):
    for key in ('control_vertices', 'control_vertices_from_adapter', 'physical_vertices', 'vertices'):
        if meta.get(key):
            return meta[key]
    return None


def family_metrics(root, family):
    folders = [root / source_name(family)] + [root / family / f'G{stage:02}' for stage in (1, 2, 3)]
    stages = [read_metrics(folder) for folder in folders]
    for index, meta in enumerate(stages):
        denominator = operator_vertex_count(meta)
        if denominator and meta.get('moved_vertices') is not None:
            meta['moved_operator_vertex_fraction_from_json'] = meta['moved_vertices'] / denominator
        if index:
            previous = operator_vertex_count(stages[index - 1])
            moved = meta.get('previous_control_vertices_moved')
            if moved is None:
                moved = meta.get('previous_vertices_moved')
            if previous and moved is not None:
                meta['previous_operator_vertex_moved_fraction_from_json'] = moved / previous
    return dict(input=str(folders[0]), final=str(folders[-1]),
                stages={f'G{index:02}': meta for index, meta in enumerate(stages)},
                all_saved_stages_minimum_area_pass=all(meta.get('minimum_area_pass') is True for meta in stages))


def front_overview(path, root, size=430):
    canvas = Image.new('RGB', (size * 4, (size + 34) * 2), '#ebebe7')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(review.FONT, 19)
    for index, family in enumerate(FAMILIES):
        column, row = index % 4, index // 4
        ox, oy = column * size, row * (size + 34)
        draw.text((ox + 12, oy + 8), family + ' / G3', fill='#203039', font=font)
        with Image.open(root / family / 'G03/preview/front.png') as source:
            canvas.paste(source.convert('RGB').resize((size, size)), (ox, oy + 34))
    canvas.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--validate', nargs='+', default=[], choices=FAMILIES, metavar='FAMILY',
                        help='Run existing core validation only on these named G03 families.')
    args = parser.parse_args()
    out = args.root / 'review/catalogue'
    out.mkdir(parents=True, exist_ok=True)
    # Read all required stage metadata and preview paths before writing boards.
    families = {family: family_metrics(args.root, family) for family in FAMILIES}
    for family in FAMILIES:
        folders = [args.root / source_name(family)] + [args.root / family / f'G{stage:02}' for stage in (1, 2, 3)]
        missing = [str(folder / 'preview' / (view + '.png')) for folder in folders for view in review.VIEWS
                   if not (folder / 'preview' / (view + '.png')).exists()]
        if missing:
            raise FileNotFoundError('Missing actual preview: ' + missing[0])
    front_overview(out / 'catalogue_front_overview.png', args.root)
    for group in range(2):
        names = FAMILIES[group * 4:(group + 1) * 4]
        review.board(out / f'catalogue_views_{group + 1}.png', list(names),
                     [(view, [args.root / family / 'G03/preview' / (view + '.png') for family in names])
                      for view in review.VIEWS], 500)
    for family in FAMILIES:
        folders = [args.root / source_name(family)] + [args.root / family / f'G{stage:02}' for stage in (1, 2, 3)]
        review.board(out / (family + '_progression.png'),
                     ['G0 / input', 'G1 / split + field', 'G2 / split + field', 'G3 / split + field'],
                     [(view, [folder / 'preview' / (view + '.png') for folder in folders])
                      for view in review.VIEWS], 440)
    index = dict(families=families,
                 boards=['catalogue_front_overview.png', 'catalogue_views_1.png', 'catalogue_views_2.png'],
                 progression_boards={family: family + '_progression.png' for family in FAMILIES},
                 parameter_provenance='N4/N8, field counts and algorithm variants are our defined finite tests. No blurred IAAC numerical label is treated as a recovered parameter.',
                 attractor_curves_implemented=False,
                 scope='Actual saved previews and generation metadata only. All sequences use the folded quad input except the topology-matched cylinder. Moved fractions use operator control vertices when available, excluding render-only fan centres. No material-chart transfer; earlier terminal controls remain separate.')
    if args.validate:
        checks = {}
        for family in dict.fromkeys(args.validate):
            with contextlib.redirect_stdout(io.StringIO()):
                checks[family] = review.validate(args.root / family / 'G03')
            check = checks[family]
            print('VALIDATE', family, 'area_pass', check['minimum_area_pass'],
                  'X/Y', check['mirror_max_distance'], check['front_back_reflection']['maximum_vertex_distance'],
                  check['self_intersection'], flush=True)
        review.dump(out / 'catalogue_validation.json', checks)
        index['selected_validation'] = 'catalogue_validation.json'
        index['validated_families'] = list(checks)
    review.dump(out / 'catalogue_index.json', index)
    print('CATALOGUE REVIEW COMPLETE', len(FAMILIES), 'families / G0-G3', str(out), flush=True)


if __name__ == '__main__':
    main()
