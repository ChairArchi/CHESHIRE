"""Compare saved actual meshes; run core checks only on explicit selections."""
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('directional_mesh_review', HERE.parent / 'curved_fold_side_20261011/review.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
ROOT = Path('E:/CHESHIRE_DATA/directional_growth_20261012')
BASE = Path('E:/CHESHIRE_DATA/fold_band_growth_20261011/ANCESTRY_STAGED')


def board(path, labels, folders, size=600):
    paths = [[folder / 'preview' / (view + '.png') for folder in folders] for view in old.VIEWS]
    for row in paths:
        for image in row:
            if not image.exists():
                raise FileNotFoundError(image)
    old.board(path, labels, list(zip(old.VIEWS, paths)), size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--compare', nargs='+', default=[])
    parser.add_argument('--baseline-root', type=Path, default=BASE)
    parser.add_argument('--baseline-label', default='Previous staged')
    parser.add_argument('--baseline-stage', default='G02')
    parser.add_argument('--board-name', default='early_comparison')
    parser.add_argument('--progression', nargs='*', default=[])
    parser.add_argument('--validate', nargs='*', default=[])
    args = parser.parse_args()
    out = args.root / 'review'
    out.mkdir(parents=True, exist_ok=True)
    if args.compare:
        board(out / (args.board_name + '.png'),
              [args.baseline_label + ' / ' + args.baseline_stage] + args.compare,
              [args.baseline_root / args.baseline_stage] + [args.root / name for name in args.compare])
    for name in args.progression:
        stages = sorted(folder for folder in (args.root / name).glob('G[0-9][0-9]')
                        if (folder / 'generation.json').exists())
        board(out / (name + '_progression.png'), ['Shared G1'] + [p.name for p in stages],
              [BASE / 'G01'] + stages, size=500)
    if args.validate:
        path = out / 'core_validation.json'
        checks = json.loads(path.read_text(encoding='utf8')) if path.exists() else {}
        for name in args.validate:
            folder = args.root / name
            saved = folder / 'core_validation.json'
            if saved.exists():
                checks[name] = json.loads(saved.read_text(encoding='utf8'))
                print('REUSE_CORE', name, flush=True)
            else:
                checks[name] = old.validate(folder)
        old.dump(path, checks)
    print('REVIEW_COMPLETE', str(out), flush=True)


if __name__ == '__main__':
    main()
