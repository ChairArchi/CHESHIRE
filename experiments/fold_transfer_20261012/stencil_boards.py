"""Compare saved G5 stencil renders with the existing refinement/field controls.

This script only assembles actual saved images. It does not render, alter
geometry, fill missing images, or wait for an in-progress render.
"""
from pathlib import Path
import argparse
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from boards import board, DEFAULT_ROOT, DEFAULT_OUTPUT, SPAN_G3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--boards', nargs='+', choices=('detail', 'fronts', 'lineage'),
                        default=['detail'])
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    g4 = dict(SPAN=root / 'SPAN/RETURN_ONLY/G04',
              COUNTER=root / 'COUNTER_MATCHED/RETURN_ONLY/G04')
    field = {name: root / (name + '_G5_FROM_RETURN/PROTECTED/G05')
             for name in ('SPAN', 'COUNTER')}
    stencil = {name: root / (name + '_G5_STENCIL/G05')
               for name in ('SPAN', 'COUNTER')}

    if 'lineage' in args.boards:
        folders = [SPAN_G3, g4['SPAN'], field['SPAN']]
        rows = [[folder / 'detail' / (view + '.png') for folder in folders]
                for view in ('front_meso', 'side_meso')]
        board(output / 'g5_fold_lineage.png',
              'SPAN fold lineage | inherited fold relationships and added field detail',
              ['G3 OVERLAP', 'G4 RETURN_ONLY', 'G5 FIELD PROTECTED'],
              ['Front meso\nz = 2.8 / span 4', 'Side meso\nz = 5.0 / span 4'], rows,
              'Outer-rib splits and the shelf grid precede G5; the field adds fine lace. Fixed cameras; saved render contents are unchanged.')

    if 'detail' in args.boards:
        folders = [g4['SPAN'], root / 'SPAN_G5_FROM_RETURN/REFINED_ONLY/G05',
                   field['SPAN'], stencil['SPAN']]
        rows = [[folder / 'detail' / (view + '.png') for folder in folders]
                for view in ('front_meso', 'side_meso')]
        board(output / 'g5_stencil_comparison.png',
              'SPAN G5 | refinement, protected field and stencil comparison',
              ['G4 RETURN_ONLY', 'G5 REFINED_ONLY', 'G5 FIELD PROTECTED', 'G5 STENCIL'],
              ['Front meso\nz = 2.8 / span 4', 'Side meso\nz = 5.0 / span 4'], rows,
              'Fixed actual-mesh cameras. STENCIL uses existing Task36 with normal gain 0 and carried tag protection; no new return or field.')

    if 'fronts' in args.boards:
        rows = [[folder / 'preview/front.png'
                 for folder in (g4[name], field[name], stencil[name])]
                for name in ('SPAN', 'COUNTER')]
        board(output / 'g5_stencil_fronts.png',
              'Two initial masses | G4 return, G5 field and G5 stencil',
              ['G4 RETURN_ONLY', 'G5 FIELD PROTECTED', 'G5 STENCIL'],
              ['SPAN', 'COUNTER\nmatched G4 parent'], rows,
              'Same front camera and material. These branches have different operation sequences; surface refinement is not evidence of fold quality.')


if __name__ == '__main__':
    main()
