"""Review connected surface finishes; detached component pilot is excluded."""
from pathlib import Path
import argparse
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'finish_compare_layout', HERE.parent/'fold_transfer_20261012/boards.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    folders = [args.root/'bulb_finish/CONTROL/SPAN/G04',
               args.root/'bulb_finish_g5/BOLD_DETAIL/SPAN/G05',
               args.root/'bulb_integrated/INTEGRATED/SPAN/G05']
    labels = ('Current wall', 'Finite Mandelbulb relief / G5',
              'Integral buds + root folds')
    for name, views in dict(close=('front_micro', 'oblique_micro', 'side_micro'),
                            whole=('front', 'side')).items():
        layout.board(args.output/('finish_'+name+'.png'),
            'Close detail | actual geometry / matched cameras', labels, list(views),
            [[folder/'views'/(view+'.png') for folder in folders] for view in views],
            'Same current column. Both finishes deform one connected surface. '
            'Uniform material / flat normals; no normal maps. Shape exploration with intersections allowed.')
    for name, views in dict(whole=('front', 'oblique'), detail=('detail',)).items():
        layout.board(args.output/('joined_gate_'+name+'.png'),
            'Gate junctions | identical columns, thicker overlapping lintel seats',
            ['Separate-seat control', 'Thickened overlapping seats'], list(views),
            [[args.root/'gate_joined'/mode/'views'/(view+'.png')
              for mode in ('CONTROL', 'JOINED')] for view in views],
            'Same two columns and lintel topology. Local section factor 1.65; actual sampled head overlap. '
            'Visual connection, with overlapping independently closed members.')


if __name__ == '__main__':
    main()
