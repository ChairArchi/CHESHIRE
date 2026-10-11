"""Small review of saved development previews and generation metadata only.

No mesh generation, source-chart transfer, hash audit or default validation.
Explicit --validate paths invoke the existing core checker on those paths only.
"""
from pathlib import Path
import argparse
import contextlib
import io
import json
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'curved_fold_side_20261011'))
import review

ROOT = Path('E:/CHESHIRE_DATA/column_development_20261011')
OLD = Path('E:/CHESHIRE_DATA/terminal_fold_20261011/CAT_N4/G03')
FLOWS = {
    'SPAN_N4_COARSE': 'SPAN_R2',
    'SPAN_N4_REFINED': 'SPAN_R2',
    'WEAVE_BRIDGE4_REFINED': 'WEAVE_R2',
    'SPAN_RETURN_FINE': 'SPAN_R2',
    'SPAN_RETURN_COARSE': 'SPAN_COARSE',
    'SPAN_RETURN_STAGED': 'SPAN_COARSE',
}
INPUTS = ('SPAN', 'WEAVE', 'COUNTER', 'SPAN_R1',
          'WEAVE_R1', 'COUNTER_R1', 'SPAN_R2', 'WEAVE_R2', 'SPAN_COARSE')
RETURN_FLOWS = ('SPAN_RETURN_FINE', 'SPAN_RETURN_COARSE', 'SPAN_RETURN_STAGED')


def preview(folder, view):
    return folder / 'preview' / (view + '.png')


def metadata(folder):
    raw = json.loads((folder / 'generation.json').read_text(encoding='utf8'))
    keys = ('candidate', 'stage', 'source', 'parent', 'operation', 'variant',
            'vertices', 'triangles', 'physical_vertices', 'physical_triangles',
            'control_vertices', 'control_quads', 'source_control_vertices',
            'source_control_quads', 'minimum_triangle_area', 'minimum_area_threshold',
            'minimum_area_pass', 'target_mode', 'local_target_factor',
            'target_refinement', 'field_recipe', 'field_response', 'fraction',
            'maximum_requested_step', 'maximum_actual_step', 'active_fraction',
            'moved_vertices', 'previous_control_vertex_max_movement',
            'previous_control_vertices_moved', 'subdivision_passes_total',
            'field_passes_total', 'input_carrier_bilinear_splits',
            'cap_interior_sampling', 'cap_return_depth', 'proven_legacy_deep_cup_core',
            'fold_schedule', 'fold_event', 'fold_events_total', 'fold_operator',
            'fold_provenance', 'staged_field', 'field_iterations',
            'staged_field_interpretation', 'finite_inside_fraction',
            'return_active_fraction', 'return_moved_vertices', 'field_moved_vertices',
            'maximum_return_step', 'maximum_field_step')
    result = {key: raw[key] for key in keys if key in raw}
    if raw.get('control_vertices') and raw.get('moved_vertices') is not None:
        result['moved_control_vertex_fraction'] = raw['moved_vertices'] / raw['control_vertices']
    result['artifacts'] = dict(folder=str(folder), generation=str(folder / 'generation.json'),
                               actual_mesh=str(folder / 'gate.ply'),
                               authoritative_geometry=str(folder / 'geometry.npz'),
                               control_quads=str(folder / 'control_quad.npz'),
                               previews={view: str(preview(folder, view)) for view in review.VIEWS})
    return result


def input_overview(path, root, size=380):
    rows = (len(INPUTS) + 3) // 4
    canvas = Image.new('RGB', (size * 4, (size + 34) * rows), '#ebebe7')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(review.FONT, 19)
    for index, name in enumerate(INPUTS):
        ox, oy = index % 4 * size, index // 4 * (size + 34)
        draw.text((ox + 12, oy + 8), name + ' / G0', fill='#203039', font=font)
        with Image.open(preview(root / 'inputs' / name / 'G00', 'front')) as image:
            canvas.paste(image.convert('RGB').resize((size, size)), (ox, oy + 34))
    canvas.save(path)


def matched_board(path, labels, folders, size=600):
    review.board(path, labels,
                 [(view, [preview(folder, view) for folder in folders]) for view in review.VIEWS], size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--old-reference', type=Path, default=OLD)
    parser.add_argument('--validate', nargs='+', default=[], metavar='CANDIDATE_PATH',
                        help='Validate these explicit actual folders only, e.g. SPAN_N4_REFINED/G03.')
    args = parser.parse_args()
    out = args.root / 'review'
    input_paths = {name: args.root / 'inputs' / name / 'G00' for name in INPUTS}
    flow_paths = {name: [input_paths[source]] + [args.root / name / f'G{stage:02}' for stage in (1, 2, 3)]
                  for name, source in FLOWS.items()}
    # Fail before writing partial boards if rendering is still incomplete.
    required = [args.old_reference, *input_paths.values(),
                *(folder for folders in flow_paths.values() for folder in folders)]
    for folder in dict.fromkeys(required):
        for view in review.VIEWS:
            if not preview(folder, view).exists():
                raise FileNotFoundError('Actual preview not ready: ' + str(preview(folder, view)))
    index = dict(old_reference=metadata(args.old_reference),
                 inputs={name: metadata(folder) for name, folder in input_paths.items()},
                 flows={name: {f'G{stage:02}': metadata(folder) for stage, folder in enumerate(folders)}
                        for name, folders in flow_paths.items()})
    out.mkdir(parents=True, exist_ok=True)
    matched_board(out / 'development_final_comparison.png',
                  ['Previous CAT_N4 / G3', 'SPAN N4 refined / G3', 'WEAVE bridge4 refined / G3'],
                  [args.old_reference, flow_paths['SPAN_N4_REFINED'][-1], flow_paths['WEAVE_BRIDGE4_REFINED'][-1]])
    matched_board(out / 'span_target_comparison.png',
                  ['SPAN N4 / coarse targets', 'SPAN N4 / refined targets'],
                  [flow_paths['SPAN_N4_COARSE'][-1], flow_paths['SPAN_N4_REFINED'][-1]], 650)
    return_iterations = {name: [index['flows'][name][f'G{stage:02}'].get('field_iterations')
                                for stage in (1, 2, 3)] for name in RETURN_FLOWS}
    return_labels = []
    for label, name in zip(('Fine input', 'Coarse input', 'Coarse input'), RETURN_FLOWS):
        values = return_iterations[name]
        schedule = ('fixed ' + str(values[0])) if len(set(values)) == 1 else ('staged ' + '-'.join(map(str, values)))
        return_labels.append(label + ' / ' + schedule)
    review.board(out / 'return_early_pattern_comparison.png', return_labels,
                 [(f'G{stage} / {view}', [preview(flow_paths[name][stage], view) for name in RETURN_FLOWS])
                  for stage in (1, 2) for view in review.VIEWS], 420)
    matched_board(out / 'return_final_comparison.png',
                  ['Previous CAT_N4 / G3', *return_labels],
                  [args.old_reference, *(flow_paths[name][-1] for name in RETURN_FLOWS)], 550)
    for name, folders in flow_paths.items():
        matched_board(out / (name + '_progression.png'),
                      ['G0 / ' + FLOWS[name], 'G1 / split + field', 'G2 / split + field', 'G3 / split + field'],
                      folders, 440)
    input_overview(out / 'input_front_overview.png', args.root)
    coarse, fine = index['flows']['SPAN_N4_COARSE'], index['flows']['SPAN_N4_REFINED']
    index['span_comparison_metadata'] = {
        stage: dict(same_source=coarse[stage].get('source') == fine[stage].get('source'),
                    same_field_recipe=coarse[stage].get('field_recipe') == fine[stage].get('field_recipe'),
                    same_fraction=coarse[stage].get('fraction') == fine[stage].get('fraction'),
                    same_step_budget=coarse[stage].get('maximum_requested_step') == fine[stage].get('maximum_requested_step'),
                    target_modes=[coarse[stage].get('target_mode'), fine[stage].get('target_mode')],
                    local_target_factors=[coarse[stage].get('local_target_factor'), fine[stage].get('local_target_factor')])
        for stage in ('G01', 'G02', 'G03')}
    index['return_comparison_scope'] = dict(
        density='SPAN_RETURN_FINE vs SPAN_RETURN_COARSE: same analytic recipe, fixed 18 field iterations, fraction .18 and authored return schedule; sampled input density changes.',
        staged_field='SPAN_RETURN_COARSE vs SPAN_RETURN_STAGED: same coarse input, fraction .18 and authored returns; the finite escape iteration schedule is read from each saved stage. This is not guaranteed low-pass filtering.',
        actual_field_iterations=return_iterations,
        fold_provenance='Scheduled returns are authored smooth_deep PCHIP geometry, not spontaneous IAAC field folds. Actual logged parameters are retained per stage.')
    index['boards'] = ['development_final_comparison.png', 'span_target_comparison.png',
                       'return_early_pattern_comparison.png', 'return_final_comparison.png',
                       'input_front_overview.png'] + [name + '_progression.png' for name in FLOWS]
    index['scope'] = ('Actual saved previews and small generation metadata only. '
                      'SPAN coarse/refined changes target sampling with the same declared input and field; '
                      'WEAVE bridge4 changes both input and field and is a design comparison. '
                      'Control movement fractions exclude render-only face centres. '
                      'Our finite initial forms and field settings do not recover undisclosed IAAC code or numerical parameters.')
    if args.validate:
        checks = {}
        for name in dict.fromkeys(args.validate):
            folder = Path(name)
            if not folder.is_absolute():
                folder = args.root / folder
            with contextlib.redirect_stdout(io.StringIO()):
                checks[name] = review.validate(folder)
            check = checks[name]
            print('VALIDATE', name, 'area_pass', check['minimum_area_pass'],
                  'X/Y', check['mirror_max_distance'], check['front_back_reflection']['maximum_vertex_distance'],
                  check['self_intersection'], flush=True)
        review.dump(out / 'development_validation.json', checks)
        index['explicit_validation'] = dict(folders=list(checks), results='development_validation.json')
    review.dump(out / 'development_index.json', index)
    print('DEVELOPMENT REVIEW COMPLETE', f'{len(FLOWS)} flows / {len(INPUTS)} inputs', str(out), flush=True)


if __name__ == '__main__':
    main()
