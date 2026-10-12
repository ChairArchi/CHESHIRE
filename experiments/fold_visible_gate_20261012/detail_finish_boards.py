"""Matched actual-geometry G05/G06 close views; no image synthesis or retouching."""
from pathlib import Path
import argparse
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'detail_finish_board_layout', HERE.parent/'fold_transfer_20261012/boards.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--counter', action='store_true')
    args = parser.parse_args()
    case = 'COUNTER' if args.counter else 'SPAN'
    folders = [args.root/'bulb_integrated/INTEGRATED'/case/'G05']
    labels = ['Integral detail / G5']
    if not args.counter:
        folders.append(args.root/'bulb_finish_g6/INTEGRATED_G06'/case/'G06')
        labels.append('Same detail / G6')
    relaxed_root = 'bulb_finish_g6_relaxed_g3_counter' if args.counter else 'bulb_finish_g6_relaxed_g3'
    folders.append(args.root/relaxed_root/'RELAXED_G06'/case/'G06')
    labels.append('Bounded carrier relaxation / G6')
    views = ['front_micro', 'side_micro'] if args.counter else [
        'front_micro', 'oblique_micro', 'side_micro']
    layout.board(args.output/(case.lower()+'_refinement.png'),
        case+' | actual surface geometry, matched cameras', labels, views,
        [[folder/'views'/(view+'.png') for folder in folders] for view in views],
        'Same attached finite-bulb recipe. Carrier shift <= 0.04 original units; '
        'one connected surface. Flat geometric normals / identical material.')
    if not args.counter:
        whole = ['front', 'side']
        layout.board(args.output/'span_refinement_whole.png',
            'SPAN | whole form after bounded surface refinement', labels, whole,
            [[folder/'views'/(view+'.png') for folder in folders] for view in whole],
            'Identical scale and camera. Carrier changes are bounded; original '
            'WALL coordinates are not claimed to remain exact after relaxation.')


if __name__ == '__main__':
    main()
