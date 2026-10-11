"""Arrange actual same-camera renders, separately for each input."""
from pathlib import Path
import argparse
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('region_existing_boards',
    HERE.parent/'fold_return_20261012/boards.py')
layout = importlib.util.module_from_spec(spec); spec.loader.exec_module(layout)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    for case in ('SPAN','COUNTER'):
        folders=[args.root/mode/case/'G03' for mode in ('CONTROL','GROOVE','RETURN')]
        columns=['G3 surface-preserving control','G3 measured V groove','G3 measured groove + return']
        for label,group,views in (
            ('whole','preview',('front','oblique','side')),
            ('detail','detail',('front_region','side_region','front_shoulder','side_shoulder'))):
            images=[[folder/group/(view+'.png') for folder in folders] for view in views]
            layout.board(args.output/(case.lower()+'_'+label+'.png'),
                case+' | same two region seeds / actual geometry sets guide, frame and scale',
                columns,list(views),images,
                'Same G2 input + same inactive G3 refinement. Two connected region folds; no new field, cell offsets or geometric averaging. Self-intersections untested.')
