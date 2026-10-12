"""Full saved renders in matched columns; no retouching or cropping."""
from pathlib import Path
import argparse
import importlib.util

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('visible_board_layout',HERE.parent/'fold_transfer_20261012/boards.py')
layout=importlib.util.module_from_spec(spec);spec.loader.exec_module(layout)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--case',default='SPAN')
    p.add_argument('--modes',nargs='+',default=['CONTROL','PREVIOUS','DEPTH','WALL'])
    p.add_argument('--kind',choices=('column','gate'),default='column')
    args=p.parse_args()
    if args.kind=='column':
        folders=[args.root/mode/args.case/('G04' if mode=='CHILD' else 'G03') for mode in args.modes]
        groups=dict(whole=('front','oblique','side'),detail=('front_detail','side_detail'))
    else:
        folders=[args.root/'assemblies'/mode for mode in args.modes]
        groups=dict(gate=('front','oblique','side','detail'))
    labels=dict(CONTROL='Surface-preserving control',PREVIOUS='Previous small groove',DEPTH='Stronger groove only',WALL='Connected wall + groove',CHILD='Wall + measured child')
    for name,views in groups.items():
        layout.board(args.output/(args.case.lower()+'_'+name+'.png'),
            args.case+' | actual geometry / matched cameras',
            [labels[mode] for mode in args.modes],list(views),
            [[folder/'views'/(view+'.png') for folder in folders] for view in views],
            'Same input and shared fold coefficients. WALL deliberately rebuilds local interiors. Geometry only; intersections and fabrication untested.')


if __name__=='__main__':
    main()
