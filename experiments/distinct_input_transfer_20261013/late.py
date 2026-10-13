"""Case/path binding for a different input; all old late geometry is reused.

Only load/bind context functions are replaced. No old operator, coefficient,
phase, selection or displacement function is patched or edited.
"""
from pathlib import Path
import argparse
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
spec = importlib.util.spec_from_file_location('distinct_frozen_late_adapter',
    HERE.parent/'recipe_transfer_20261013/late.py')
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)
CASE = 'CENTRAL_SPINDLE'
original_bind = base.bind


def load(root, stage):
    path = base.folder(root, stage)
    info = base.read(path/'generation.json')
    if info['input_case'] != CASE or not info['checks']['passed']:
        raise ValueError('Actual verified CENTRAL_SPINDLE parent required.')
    if base.sha(path/'control_quad.npz') != info['control_file_sha256']:
        raise ValueError('Actual parent control changed.')
    data = base.arrays(path/'control_quad.npz')
    mesh = base.core.ArrayMesh(data['xyz'], data['faces'], data['classes'], data['rest'],
        data['anchors'], int(data['generation']))
    mesh.surface = str(data['surface'])
    if mesh.generation != info['subdivision_generation']:
        raise ValueError('Actual saved generation differs.')
    return mesh, data['chart'], info


def bind(*args, **kwargs):
    context = original_bind(*args, **kwargs)
    context.update(input_case=CASE,
        recipe_scope='G0 macro input and input-generation recipe differ; all selected G1--G7 operators, values and order remain unchanged.')
    return context


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--stage', choices=base.STAGES, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    base.recipe_proof()
    for name, expected in base.read(root/'RECIPE.json')['geometry_code_sha256'].items():
        if base.sha(REPO/name) != expected:
            raise ValueError('Frozen generation source differs: '+name)
    if base.folder(root, args.stage).exists():
        raise FileExistsError('Existing stage is preserved.')
    base.load, base.bind = load, bind
    print('DISTINCT INPUT / unchanged downstream', args.stage, flush=True)
    if args.stage in ('G05_DIRECTIONAL', 'G06_DEPTH08'):
        base.directional(root, args.stage)
    elif args.stage == 'G06_MIDDLE':
        base.middle(root)
    elif args.stage == 'G07_SURFACE':
        base.surface(root)
    elif args.stage in ('G07_LINKED_RAW', 'G07_WIDE_RAW'):
        base.fields(root, args.stage)
    else:
        base.filter_saved(root, args.stage)
    print('DONE', args.stage, flush=True)


if __name__ == '__main__':
    main()
