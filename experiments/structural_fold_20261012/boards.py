"""Compact structural comparisons assembled from saved actual-mesh renders.

Run after the requested saved preview images exist. This script does not
generate geometry, render, retouch images, create placeholders or wait.
"""
from pathlib import Path
import argparse
import importlib.util

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    'preserved_coherence_board_layout', HERE.parent / 'fold_coherence_20261012/boards.py')
_layout = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_layout)
board = _layout.board

DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/structural_fold_20261012')
DEFAULT_OUTPUT = HERE.parents[1] / 'docs/structural_fold_20261012/images'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--boards', nargs='+', choices=('first', 'progression', 'finish'),
                        default=['first'])
    parser.add_argument('--families', nargs='+',
                        choices=('LONGITUDINAL', 'CROSS_FORK'),
                        default=['CROSS_FORK'],
                        help='Progression only; LONGITUDINAL stopped at R1 and has no R2.')
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    seed = root / 'SEED/G00'

    if 'first' in args.boards:
        folders = [root / 'SOURCE/G00', seed,
                   root / 'LONGITUDINAL/R01', root / 'CROSS_FORK/R01']
        rows = [[folder / 'preview' / (view + '.png') for folder in folders]
                for view in ('front', 'oblique', 'side')]
        board(output / 'first_step_comparison.png',
              'Structural test | source, bored seed and first cut-reflect-union step',
              ['SOURCE G0', 'SEED G0 / bored', 'LONG R1 / disconnected', 'CROSS R1 / one body'],
              ['Front', 'Oblique', 'Side'], rows,
              'All components shown. LONG R1 failed connectivity; CROSS R1 being connected is not aesthetic success. LONG R2 was not generated.')

    if 'progression' in args.boards:
        for family in args.families:
            folders = [seed, root / family / 'R01', root / family / 'R02']
            rows = [[folder / 'preview' / (view + '.png') for folder in folders]
                    for view in ('front', 'oblique', 'side')]
            board(output / (family.lower() + '_progression.png'),
                  family + ' | structural progression / stopped after R2 connectivity failure',
                  ['SEED G0 / axial bore', 'R1 / one body', 'R2 / FAIL: 2 components'],
                  ['Front', 'Oblique', 'Side'], rows,
                  'All components shown. CROSS R2 failed connectivity; no further structural steps. These Boolean edits are not physical origami.')

    if 'finish' in args.boards:
        folders = [seed, root / 'CROSS_FORK/R01',
                   root / 'SEED/G00_CC1', root / 'CROSS_FORK/R01_CC1']
        rows = [[folder / 'preview' / (view + '.png') for folder in folders]
                for view in ('front', 'oblique', 'side')]
        board(output / 'structural_finish_comparison.png',
              'Structural study closeout | one CC pass / both CC outputs fail strict XY symmetry',
              ['SEED G0', 'CROSS R1', 'SEED CC1 / XY FAIL', 'CROSS R1 CC1 / XY FAIL'],
              ['Front', 'Oblique', 'Side'], rows,
              'CC outputs remain closed, one component; genus 5 / 8 retained. Strict XY solid checks FAIL at unchanged thresholds. Diagnostic outcomes, not validated design solutions.')


if __name__ == '__main__':
    main()
