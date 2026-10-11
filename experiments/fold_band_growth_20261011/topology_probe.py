"""Same actual SPAN_SPARSE surface, existing quad versus triangle field loops.

No new geometry operator. Triangle lineage includes the original render fan
centres as controls; quad lineage excludes them and recreates fans after every
field step. Both call iaac_repeat.py n4 with the same sampled outside grid,
18 escape iterations and .55 fractional attraction. This coarse grid is not
the locally refined G2/G3 grid used by newer FIELD_SEED/FULL_LOOP experiments.
"""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent


def comparison_board(root, stage):
    rows = [('SPAN_SPARSE G00', root / 'inputs' / 'SPAN_SPARSE' / 'G00'),
            ('QUAD_NEAREST ' + stage, root / 'QUAD_NEAREST' / stage),
            ('TRI_NEAREST ' + stage, root / 'TRI_NEAREST' / stage)]
    views = ('front', 'oblique', 'side')
    if not all((folder / 'preview' / (view + '.png')).exists() for _, folder in rows for view in views):
        return
    width, height, header = 560, 560, 34
    board = Image.new('RGB', (3 * width, len(rows) * (height + header)), '#efefec')
    draw = ImageDraw.Draw(board)
    for row, (name, folder) in enumerate(rows):
        for column, view in enumerate(views):
            x, y = column * width, row * (height + header)
            draw.text((x + 12, y + 10), name + ' / ' + view, fill='#202020')
            with Image.open(folder / 'preview' / (view + '.png')) as image:
                board.paste(image.convert('RGB').resize((width, height)), (x, y + header))
    output = root / 'review'
    output.mkdir(exist_ok=True)
    board.save(output / ('topology_' + stage + '_comparison.png'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path,
                        default=Path('E:/CHESHIRE_DATA/fold_band_growth_20261011'))
    parser.add_argument('--mode', choices=('quad', 'tri'), required=True)
    parser.add_argument('--stages', type=int, choices=(1, 2, 3), default=2)
    args = parser.parse_args()
    root = args.root.resolve()
    source = root / 'inputs' / 'SPAN_SPARSE' / 'G00'
    if args.mode == 'tri':
        prepared = root / 'inputs' / 'SPAN_SPARSE_TRI_SAME_SURFACE' / 'G00'
        prepared.mkdir(parents=True, exist_ok=True)
        # Deliberately copy ONLY the physical triangle checkpoint, never quads.
        target = prepared / 'checkpoint.npz'
        if target.exists():
            with np.load(source / 'checkpoint.npz', allow_pickle=False) as a, np.load(target, allow_pickle=False) as b:
                if not all(np.array_equal(a[k], b[k]) for k in ('xyz', 'faces', 'chart')):
                    raise FileExistsError('Existing triangle input differs; preserved.')
        else:
            shutil.copy2(source / 'checkpoint.npz', target)
        if (prepared / 'control_quad.npz').exists():
            raise ValueError('Triangle control ablation must not have sibling quads.')
        record = dict(source=str(source / 'checkpoint.npz'), exact_same_xyz_faces_chart=True,
                      preparation='Byte copy of actual physical checkpoint only; no remeshing.',
                      comparison='Render fan centres become triangle controls; original quad controls absent.',
                      original_physical_vertices=802, original_physical_triangles=1600,
                      original_quad_vertices=402, original_quads=400)
        (prepared / 'provenance.json').write_text(json.dumps(record, indent=2), encoding='utf8')
        source = prepared
    family = 'TRI_NEAREST' if args.mode == 'tri' else 'QUAD_NEAREST'
    project = HERE.parents[1]
    environment = os.environ.copy()
    environment['PYTHONPATH'] = str(project / 'src') + os.pathsep + environment.get('PYTHONPATH', '')
    command = [sys.executable, '-B', str(HERE.parent / 'terminal_fold_20261011' / 'iaac_repeat.py'),
               '--source', str(source), '--output-root', str(root), '--name', family,
               '--variant', 'n4', '--stages', str(args.stages), '--budgets', '.35', '.28', '.22']
    subprocess.run(command, check=True, env=environment)
    (root / family / 'topology_provenance.json').write_text(json.dumps(dict(
        source=str(source), mode=args.mode, wrapper=str(Path(__file__).resolve()),
        command=command, input_actual_surface='Identical saved 802-vertex / 1600-triangle G00 surface',
        target_grid='Existing sampled coarse finite-outside targets at every stage; no G2/G3 target refinement',
        field='Same n4 recipe, 18 finite escape iterations, .55 nearest-outside fraction',
        limitation='Control lineage and sample positions differ as intended. Both physical triangle counts grow by four and match at each stage; no IAAC exact reproduction claim.'
    ), indent=2), encoding='utf8')
    comparison_board(root, f'G{args.stages:02}')


if __name__ == '__main__':
    main()
