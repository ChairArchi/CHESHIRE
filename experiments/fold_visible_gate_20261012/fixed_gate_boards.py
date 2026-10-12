"""Compare the fixed columns with plain, symmetric, and refolded lintels."""
from pathlib import Path
import argparse
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'fixed_gate_board_layout', HERE.parent/'fold_transfer_20261012/boards.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    modes = ('PLAIN', 'CONTROL', 'WALL')
    labels = ('Same-section plain lintel', 'New symmetric carrier',
              'Symmetric carrier + wall folds')
    for name, views in dict(whole=('front', 'oblique'), detail=('detail',)).items():
        layout.board(
            args.output/('fixed_gate_'+name+'.png'),
            'Fixed columns | newly generated symmetric lintel', labels, list(views),
            [[args.root/mode/'views'/(view+'.png') for mode in modes] for view in views],
            'Identical current columns; B opening; lintel section based on column width and depth. '
            'Actual triangles / matched cameras. Joints, intersections and fabrication untested.')


if __name__ == '__main__':
    main()
