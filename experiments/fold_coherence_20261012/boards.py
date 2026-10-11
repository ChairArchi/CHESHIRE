"""Compact coherence comparisons from saved actual-mesh renders only.

Missing renders fail immediately. No mesh edits, image retouching, new
renders or waiting loops are performed here.
"""
from pathlib import Path
import argparse
import importlib.util

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    'preserved_transfer_board_layout', HERE.parent / 'fold_transfer_20261012/boards.py')
_layout = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_layout)
board = _layout.board

DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/fold_coherence_20261012')
DEFAULT_OUTPUT = HERE.parents[1] / 'docs/fold_coherence_20261012/images'
OLD_SPAN_G3 = Path('E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G03')
OLD_COUNTER_G3 = Path('E:/CHESHIRE_DATA/fold_transfer_20261012/COUNTER/G03')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--boards', nargs='+',
                        choices=('whole', 'detail', 'progression', 'final', 'flow_detail', 'diagnosis', 'curved', 'curved_field', 'ruled', 'ruled_final', 'ruled_near'),
                        default=['whole'])
    parser.add_argument('--ruled-final-gen', type=int, choices=(3, 4, 5, 6), default=4,
                        help='Last actual RULED generation in the meso board; missing images fail.')
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    old = dict(SPAN=OLD_SPAN_G3, COUNTER=OLD_COUNTER_G3)
    folders = {name: [old[name], root / 'RESERVE' / name / 'G03',
                      root / 'FLOW' / name / 'G03']
               for name in ('SPAN', 'COUNTER')}
    columns = ['Existing G3', 'RESERVE G3', 'FLOW G3']

    if 'ruled_final' in args.boards:
        final_folders = [Path('E:/CHESHIRE_DATA/fold_transfer_20261012/SPAN_G5_TAG_ONLY/G05'),
                         root / 'FLOW/SPAN/G05', root / 'RULED/SPAN/G06']
        rows = [[folder / 'preview' / (view + '.png') for folder in final_folders]
                for view in ('front', 'oblique', 'side')]
        board(output / 'ruled_g6_whole_comparison.png',
              'SPAN | previous field G5, FLOW G5 and RULED G6',
              ['Previous TAG_ONLY G5', 'FLOW G5', 'RULED G6'],
              ['Front', 'Oblique', 'Side'], rows,
              'Fixed actual-mesh cameras; different recipes and generation/field histories. This is a design comparison, not a matched causal test.')
        board(output / 'ruled_g6_views.png',
              'RULED G6 | texture-dominated result - not recommended',
              ['Front', 'Oblique', 'Side'], ['RULED G6\nNot recommended'],
              [[root / 'RULED/SPAN/G06/preview' / (view + '.png')
                for view in ('front', 'oblique', 'side')]],
              'Design failure: finer repeated grid dominates the surface without a new qualitative fold hierarchy. Preserved as scaling-limit evidence.')

    if 'ruled_near' in args.boards:
        near_folders = [Path('E:/CHESHIRE_DATA/fold_transfer_20261012/SPAN_G5_TAG_ONLY/G05'),
                        root / 'RULED/SPAN/G06']
        rows = [[folder / 'detail' / (view + '.png') for folder in near_folders]
                for view in ('front_meso', 'side_meso')]
        board(output / 'previous_vs_ruled_g6_detail.png',
              'SPAN | previous field G5 and RULED G6 at fixed meso views',
              ['Previous TAG_ONLY G5', 'RULED G6 / texture failure'],
              ['Front meso\nz = 2.8 / span 4', 'Side meso\nz = 5.0 / span 4'], rows,
              'Different recipes and histories; fixed cameras only. RULED G6 is not recommended: texture dominates without richer fold hierarchy.')

    if 'ruled' in args.boards:
        ruled_g4_folders = [root / mode / 'SPAN/G04' for mode in ('CURVED', 'RULED')]
        rows = [[folder / 'preview' / (view + '.png') for folder in ruled_g4_folders]
                for view in ('front', 'oblique', 'side')]
        board(output / 'curved_vs_ruled_g4.png',
              'SPAN G4 | field development and repeated RULED kernel',
              ['CURVED G4', 'RULED G4'], ['Front', 'Oblique', 'Side'], rows,
              'RULED repeats a different Task36 kernel from zero-field CURVED G2. This design comparison is not a single-variable field test.')
        generations = list(range(3, args.ruled_final_gen + 1))
        ruled_folders = [root / 'RULED/SPAN' / ('G0' + str(g)) for g in generations]
        rows = [[folder / 'detail' / (view + '.png') for folder in ruled_folders]
                for view in ('front_meso', 'side_meso')]
        board(output / ('ruled_meso_progression_g%02d.png' % args.ruled_final_gen),
              'RULED | repeated-kernel meso progression without field',
              ['RULED G' + str(g) for g in generations],
              ['Front meso\nz = 2.8 / span 4', 'Side meso\nz = 5.0 / span 4'], rows,
              ('G6 is not recommended: texture dominance without a new fold hierarchy. ' if args.ruled_final_gen == 6 else '')
              + 'Zero field history; one repeated kernel without new authored child returns.')

    if 'curved_field' in args.boards:
        curved_field_folders = [root / 'CURVED/SPAN/G03',
                                root / 'DIAGNOSIS/CURVED_PREFIELD/G04',
                                root / 'CURVED/SPAN/G04']
        rows = [[folder / 'detail' / (view + '.png') for folder in curved_field_folders]
                for view in ('front_meso', 'side_meso')]
        board(output / 'curved_g4_field_diagnosis.png',
              'CURVED | retained G3 structure and the second field pass at G4',
              ['CURVED G3 / first field', 'G4 PRE_FIELD', 'G4 WITH_FIELD'],
              ['Front meso\nz = 2.8 / span 4', 'Side meso\nz = 5.0 / span 4'], rows,
              'G4 pre/post share topology and surface policy; pre-field retains the G3 field. This isolates the added G4 field displacement.')

    if 'curved' in args.boards:
        curved_folders = [root / mode / 'SPAN/G03' for mode in ('FLOW', 'LATE', 'CURVED')]
        rows = [[folder / 'detail' / (view + '.png') for folder in curved_folders]
                for view in ('front_meso', 'side_meso')]
        board(output / 'late_curved_g3_detail.png',
              'SPAN G3 | inherited faceting, CC averaging and groove continuity',
              ['FLOW G3', 'LATE G3', 'CURVED G3'],
              ['Front meso\nz = 2.8 / span 4', 'Side meso\nz = 5.0 / span 4'], rows,
              'LATE/CURVED share delayed field history; CURVED enables weighted CC averaging with tags. FLOW has different prior operations.')

    if 'diagnosis' in args.boards:
        diagnosis_folders = [root / 'DIAGNOSIS/SPAN' / mode / 'G02'
                             for mode in ('INTERPOLATED', 'TASK36_ONLY', 'WITH_FIELD')]
        rows = [[folder / 'detail' / (view + '.png') for folder in diagnosis_folders]
                for view in ('front_meso', 'side_meso')]
        board(output / 'g2_operation_diagnosis.png',
              'SPAN G2 operation slices | inherited grain, Task36 placement and field',
              ['INTERPOLATED / G1 mean', 'TASK36_ONLY', 'WITH_FIELD'],
              ['Front meso\nz = 2.8 / span 4', 'Side meso\nz = 5.0 / span 4'], rows,
              'INTERPOLATED averages G1 controls on G2 topology, not exact surface sampling. G1 grain is shared; Task36 to field has identical faces.')

    if 'whole' in args.boards:
        for name in ('SPAN', 'COUNTER'):
            rows = [[folder / 'preview' / (view + '.png') for folder in folders[name]]
                    for view in ('front', 'oblique', 'side')]
            board(output / (name.lower() + '_g3_comparison.png'),
                  name + ' G3 | existing growth, reserved surfaces and fold flow',
                  columns, ['Front', 'Oblique', 'Side'], rows,
                  'Fixed actual-mesh cameras. RESERVE reduces cell placement; FLOW also adds authored child returns. Quietness is not a success claim.')

    if 'detail' in args.boards:
        rows = [[folder / 'detail' / (view + '.png') for folder in folders['SPAN']]
                for view in ('front_meso', 'side_meso')]
        board(output / 'span_g3_detail.png',
              'SPAN G3 | deep grooves, continuous ribs and panel risk',
              columns, ['Front meso\nz = 2.8 / span 4', 'Side meso\nz = 5.0 / span 4'], rows,
              'Same saved meso cameras. Compare groove depth, rib continuity and shelf-grid dominance; images are resized in full.')

    if 'progression' in args.boards:
        for name in ('SPAN', 'COUNTER'):
            stages = [root / 'FLOW' / name / ('G0' + str(g)) for g in (3, 4, 5)]
            rows = [[folder / 'preview' / (view + '.png') for folder in stages]
                    for view in ('front', 'oblique', 'side')]
            board(output / (name.lower() + '_flow_progression.png'),
                  name + ' FLOW | G3 to G5 actual-mesh progression',
                  ['FLOW G3', 'FLOW G4', 'FLOW G5'], ['Front', 'Oblique', 'Side'], rows,
                  'Same cameras and material. Progression preserves each saved mesh; more detail is not proof of better fold hierarchy.')

    old_g5_root = Path('E:/CHESHIRE_DATA/fold_transfer_20261012')
    if 'final' in args.boards:
        for name in ('SPAN', 'COUNTER'):
            final_folders = [old_g5_root / (name + '_G5_TAG_ONLY/G05'),
                             root / 'FLOW' / name / 'G05']
            rows = [[folder / 'preview' / (view + '.png') for folder in final_folders]
                    for view in ('front', 'oblique', 'side')]
            board(output / (name.lower() + '_g5_final_comparison.png'),
                  name + ' G5 | previous tag-only field and new fold-flow development',
                  ['Previous TAG_ONLY G5', 'New FLOW G5'], ['Front', 'Oblique', 'Side'], rows,
                  'Fixed actual-mesh views. The development recipes differ; this is a design comparison, not a single-variable test.')

    if 'flow_detail' in args.boards:
        detail_folders = [old_g5_root / 'SPAN_G5_TAG_ONLY/G05']
        detail_folders += [root / 'FLOW/SPAN' / ('G0' + str(g)) for g in (3, 4, 5)]
        rows = [[folder / 'detail' / (view + '.png') for folder in detail_folders]
                for view in ('front_meso', 'side_meso')]
        board(output / 'span_flow_detail.png',
              'SPAN | previous G5 and new FLOW fold development at fixed meso views',
              ['Previous TAG_ONLY G5', 'FLOW G3', 'FLOW G4', 'FLOW G5'],
              ['Front meso\nz = 2.8 / span 4', 'Side meso\nz = 5.0 / span 4'], rows,
              'Same saved cameras. Assess deep grooves, connected ribs, quiet faces and shelf-grid dominance together; no retouching.')


if __name__ == '__main__':
    main()
