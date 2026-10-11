"""Assemble saved G5 renders for the old-point pin isolation comparison.

The three SPAN detail columns share the saved pre-field return state. The
field columns differ only in blanket old-point pinning; legacy tag protection
remains active. Missing images fail immediately; this script never waits or
creates render placeholders.
"""
from pathlib import Path
import argparse
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from boards import board, DEFAULT_ROOT, DEFAULT_OUTPUT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--boards', nargs='+', choices=('detail', 'views'),
                        default=['detail', 'views'])
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    tag_only = {name: root / (name + '_G5_TAG_ONLY/G05')
                for name in ('SPAN', 'COUNTER')}

    if 'detail' in args.boards:
        folders = [root / 'SPAN_G5_FROM_RETURN/RETURN_ONLY/G05',
                   root / 'SPAN_G5_FROM_RETURN/PROTECTED/G05',
                   tag_only['SPAN']]
        rows = [[folder / 'detail' / (view + '.png') for folder in folders]
                for view in ('front_meso', 'side_meso')]
        board(output / 'g5_pin_comparison.png',
              'SPAN G5 | isolate blanket old-point pinning during the field pass',
              ['RETURN_ONLY / no field', 'PROTECTED / old + tag', 'TAG_ONLY / tag only'],
              ['Front meso\nz = 2.8 / span 4', 'Side meso\nz = 5.0 / span 4'], rows,
              'Same pre-field state and raw field vectors. TAG_ONLY releases blanket old-point pins while retaining legacy tag protection.')

    if 'views' in args.boards:
        rows = [[tag_only[name] / 'preview' / (view + '.png')
                 for view in ('front', 'oblique', 'side')]
                for name in ('SPAN', 'COUNTER')]
        board(output / 'g5_tag_only_views.png',
              'G5 TAG_ONLY | actual mesh with legacy tag protection',
              ['Front', 'Oblique', 'Side'],
              ['SPAN\nTAG_ONLY G5', 'COUNTER\nTAG_ONLY G5'], rows,
              'Fixed cameras and material. Only blanket old-point pinning changes from PROTECTED; no new field query, return or G6.')


if __name__ == '__main__':
    main()
