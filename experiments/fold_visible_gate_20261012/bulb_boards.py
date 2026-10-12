"""Matched full and close views of actual finite-Mandelbulb surface relief."""
from pathlib import Path
import argparse
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'bulb_finish_boards', HERE.parent/'fold_transfer_20261012/boards.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', choices=('SPAN', 'COUNTER'), default='SPAN')
    args = parser.parse_args()
    modes = ('CONTROL', 'COARSE_CLUSTER', 'BOLD_DETAIL')
    labels = ('Current wall / matched G4', 'Irregular bulb colonies',
              'Stronger two-scale relief')
    groups = dict(whole=('front', 'side'),
                  close=('front_micro', 'oblique_micro', 'side_micro'))
    for name, views in groups.items():
        layout.board(
            args.output/(args.case.lower()+'_bulb_'+name+'.png'),
            args.case+' | actual fractal relief / matched cameras', labels, list(views),
            [[args.root/mode/args.case/'G04/views'/(view+'.png')
              for mode in modes] for view in views],
            'Finite Mandelbulb upper-envelope colonies on current geometry. '
            'Real displaced triangles / flat normals. Intersections allowed for this shape exploration.')


if __name__ == '__main__':
    main()
