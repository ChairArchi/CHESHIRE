"""Compare saved actual column renders; no rendering, retouching or wait loop."""
from pathlib import Path
import argparse
import importlib.util

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    'preserved_column_board_layout', HERE.parent / 'fold_transfer_20261012/boards.py')
_layout = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_layout)
board = _layout.board

DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/fold_return_20261012')
DEFAULT_REFERENCE = Path('E:/CHESHIRE_DATA/fold_coherence_20261012/CURVED/SPAN/G02')
DEFAULT_ANCHOR = Path('E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G02')
DEFAULT_OUTPUT = HERE.parents[1] / 'docs/fold_return_20261012/images'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--reference', type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument('--anchor-reference', type=Path, default=DEFAULT_ANCHOR)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--boards', nargs='+', choices=('whole', 'detail', 'anchor'),
                        default=['whole', 'detail'])
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    columns = ['CURVED G2 / reference', 'CONTROL G3 / CC only',
               'RETURN G3 / 2 returns + CC']
    footer = ('Matched G2 source and CC rule. RETURN adds two authored meso returns. '
              'No field or new cell offsets; not fractal emergence or physical origami.')

    if 'whole' in args.boards:
        folders = [args.reference.resolve(), root / 'CONTROL/SPAN/G03', root / 'RETURN/SPAN/G03']
        sources = [[folder / 'preview' / (view + '.png') for folder in folders]
                   for view in ('front', 'oblique', 'side')]
        board(output / 'g3_whole.png',
              'Column return study | G2 source and matched G3 alternatives',
              columns, ['Front', 'Oblique', 'Side'], sources, footer)

    if 'detail' in args.boards:
        folders = [root / 'REFERENCE_G02', root / 'CONTROL/SPAN/G03', root / 'RETURN/SPAN/G03']
        names = ('front_meso', 'side_meso', 'front_upper', 'side_upper')
        sources = [[folder / 'detail' / (name + '.png') for folder in folders]
                   for name in names]
        board(output / 'g3_detail.png',
              'Column return study | fixed near views / geometry only',
              columns,
              ['Front meso\nz = 2.8 / span 4', 'Side meso\nz = 5.0 / span 4',
               'Front upper\nz = 6.1 / span 4', 'Side upper\nz = 6.1 / span 4'],
              sources, footer)

    if 'anchor' in args.boards:
        columns = ['OVERLAP G2 / visual anchor', 'ANCHOR G3 / CC only',
                   'ANCHOR G4 / CC only']
        footer = ('Source inherits 2 fractal-field passes. G3/G4: existing CC only; '
                  '0 new field or authored return. Surface refinement, not new fold growth.')
        folders = [args.anchor_reference.resolve(), root / 'ANCHOR/SPAN/G03',
                   root / 'ANCHOR/SPAN/G04']
        sources = [[folder / 'preview' / (name + '.png') for folder in folders]
                   for name in ('front', 'oblique', 'side')]
        board(output / 'anchor_whole.png',
              'Visual anchor continuation | inherited folds and CC-only surface refinement',
              columns, ['Front', 'Oblique', 'Side'], sources, footer)

        folders[0] = root / 'REFERENCE_ANCHOR_G02'
        names = ('front_meso', 'side_meso', 'front_upper', 'side_upper')
        sources = [[folder / 'detail' / (name + '.png') for folder in folders]
                   for name in names]
        board(output / 'anchor_detail.png',
              'Visual anchor continuation | fixed near views / no new fold growth',
              columns,
              ['Front meso\nz = 2.8 / span 4', 'Side meso\nz = 5.0 / span 4',
               'Front upper\nz = 6.1 / span 4', 'Side upper\nz = 6.1 / span 4'],
              sources, footer)


if __name__ == '__main__':
    main()
