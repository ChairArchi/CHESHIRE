"""G5 comparison boards from saved actual renders; no new geometry/rendering.

Run only after the named G5 preview and detail images are available. Reuses
the existing compact board layout without changing previous study artifacts.
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
    parser.add_argument('--boards', nargs='+', choices=('progression', 'views', 'detail'),
                        default=['progression', 'views', 'detail'])
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    g4 = dict(SPAN=root / 'SPAN/RETURN_ONLY/G04',
              COUNTER=root / 'COUNTER_MATCHED/RETURN_ONLY/G04')
    g5 = dict(SPAN=root / 'SPAN_G5_FROM_RETURN',
              COUNTER=root / 'COUNTER_G5_FROM_RETURN')
    render = lambda folder, view: folder / 'preview' / (view + '.png')
    if 'progression' in args.boards:
        rows = [[render(g4[name], 'front'),
                 render(g5[name] / 'RETURN_ONLY/G05', 'front'),
                 render(g5[name] / 'PROTECTED/G05', 'front')]
                for name in ('SPAN', 'COUNTER')]
        board(output / 'g5_progression.png', 'G5 comparison | both inputs start from RETURN_ONLY G4',
              ['G4 RETURN_ONLY', 'G5 RETURN_ONLY', 'G5 PROTECTED'],
              ['SPAN', 'COUNTER\nmatched G4 parent'], rows,
              'G5 middle = refined geometry + small authored returns before field; right = same return state followed by protected field.')
    if 'views' in args.boards:
        rows = [[render(g5[name] / 'PROTECTED/G05', view)
                 for view in ('front', 'oblique', 'side')] for name in ('SPAN', 'COUNTER')]
        board(output / 'g5_views.png', 'G5 protected field | actual mesh in three views',
              ['Front', 'Oblique', 'Side'],
              ['SPAN\nPROTECTED G5', 'COUNTER\nPROTECTED G5'], rows,
              'Same view cameras and material. Increased sampling is separate from new return geometry; no fabrication claim.')
    if 'detail' in args.boards:
        folders = [g4['SPAN'], g5['SPAN'] / 'REFINED_ONLY/G05',
                   g5['SPAN'] / 'RETURN_ONLY/G05', g5['SPAN'] / 'PROTECTED/G05']
        rows = [[folder / 'detail' / (view + '.png') for folder in folders]
                for view in ('front_meso', 'side_meso')]
        board(output / 'g5_detail.png', 'SPAN G5 | separate refinement, authored returns and field effects',
              ['G4 RETURN_ONLY', 'G5 REFINED_ONLY', 'G5 RETURN_ONLY', 'G5 PROTECTED'],
              ['Front meso\nz = 2.8 / span 4', 'Side meso\nz = 5.0 / span 4'], rows,
              'Fixed actual-geometry cameras. REFINED_ONLY adds sampling without the new return or field; images are resized in full.')


if __name__ == '__main__':
    main()
