"""Explicit hypothesis batches; further batches depend on reviewed actual geometry."""
import argparse
from pathlib import Path
from task32_research import ROOT, write_new, read


def cc():
    return dict(kind='cc', row={})


def pilot():
    definitions = [dict(id='P01_NEUTRAL', hypothesis='Matched unchanged CC carrier control',
                        steps=[cc() for _ in range(4)])]
    for index, (growth, anisotropy, field) in enumerate([
            (.25, 0, 'bands'), (.55, 0, 'bands'), (.9, 0, 'bands'),
            (.55, .85, 'bands'), (.55, .85, 'nested'), (.9, .85, 'nested')], 2):
        spec = dict(growth=growth, anisotropy=anisotropy, field=field, lobes=5,
                    angular=3, twist=1.5, bending=.02, anchor=.002, seed=.001, maxiter=2000)
        definitions.append(dict(id=f'P{index:02}_GROWTH',
            hypothesis='Spatial rest-length incompatibility may create meso buckling; isotropic/anisotropic ablation',
            steps=[cc(), cc(), dict(kind='growth', spec=spec), cc(), cc()]))
    for index, (amplitude, coupling, twist) in enumerate([
            (140, 1, 1.5), (280, 1, 1.5), (280, 0, 1.5), (280, 1, 0)], 8):
        spec = dict(amplitude=amplitude, coupling=coupling, twist=twist, angular=3,
                    lobes=5, decay=.42, envelope_power=1.5, phase=0)
        steps = [cc(), cc(), dict(kind='hierarchy', spec=spec, level=0), cc(),
                 dict(kind='hierarchy', spec=spec, level=1), cc(),
                 dict(kind='hierarchy', spec=spec, level=2)]
        definitions.append(dict(id=f'P{index:02}_HIERARCHY',
            hypothesis='Parent-gated directional child fields may create connected scales without per-cell point-class forcing',
            steps=steps))
    folder = ROOT/'definitions/pilot'
    for d in definitions:
        write_new(folder/(d['id']+'.json'), d)
    write_new(folder/'batch.json', dict(ids=[d['id'] for d in definitions],
        allocation='Small G2 deformations first; G4 views before deeper allocation.',
        not_final_search_limit=True))
    return folder


def request(folder, tag, extra=None):
    paths = sorted(Path(folder).glob('P*.json'))
    items = []
    for p in paths:
        d = read(p)
        dest = ROOT/'candidates'/d['id']
        if not (dest/'completed.json').exists():
            continue
        stage = read(dest/'completed.json')['final_stage']
        for label, angles, width, target in [
                ('front', [0, 0], 5400, [-400.036865234375, -18.533447265625, 1750]),
                ('oblique', [28, 22], 5400, [-400.036865234375, -18.533447265625, 1750]),
                ('lintel', [0, 0], 2200, [-400.036865234375, -18.533447265625, 2950])]:
            items.append(dict(label=d['id']+' '+label, stage=stage, angles=angles, width=width, target=target))
    if extra:
        items.extend(extra)
    path = ROOT/'definitions/renders'/(tag+'.json')
    write_new(path, dict(items=items, resolution=900, cols=3, size=550, pages=99,
                         sheet_name=tag+'.png'))
    return path


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['pilot','request'])
    p.add_argument('--folder', type=Path); p.add_argument('--tag')
    a = p.parse_args()
    print(pilot() if a.action == 'pilot' else request(a.folder, a.tag))
