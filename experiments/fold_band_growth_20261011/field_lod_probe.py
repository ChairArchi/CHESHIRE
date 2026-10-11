"""One bounded finite-field detail-staging hypothesis using existing operators.

Same SPAN_SPARSE input and field-only quad loop as FIELD_SEED, but internal
escape iterations are 4, 8, 18 over three growth cycles, rather than 18,18,18.
No role offset, new folding formula, authored return, smoothing or memory mask.
This schedule is our hypothesis; it is not an IAAC disclosed recipe.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

import numpy as np
import trimesh
from PIL import Image, ImageDraw

import full_loop as loop

prior = loop.prior
SCHEDULE = (4, 8, 18)
BUDGETS = (.35, .28, .22)
ALGORITHM = 'FIELD_ONLY_INTERNAL_ESCAPE_STAGING_4_8_18_V1'


def board(root, stage):
    rows = [('FIELD_SEED / fixed 18,18,18', root / 'FIELD_SEED' / stage),
            ('FIELD_STAGED / 4,8,18', root / 'FIELD_STAGED' / stage)]
    views = ('front', 'oblique', 'side')
    if not all((folder / 'preview' / (view + '.png')).exists() for _, folder in rows for view in views):
        return
    width, height, header = 560, 560, 34
    result = Image.new('RGB', (3 * width, 2 * (height + header)), '#efefec')
    draw = ImageDraw.Draw(result)
    for row, (name, folder) in enumerate(rows):
        for col, view in enumerate(views):
            x, y = col * width, row * (height + header)
            draw.text((x + 12, y + 10), name + ' / ' + stage + ' / ' + view, fill='#202020')
            with Image.open(folder / 'preview' / (view + '.png')) as image:
                result.paste(image.convert('RGB').resize((width, height)), (x, y + header))
    (root / 'review').mkdir(exist_ok=True)
    result.save(root / 'review' / ('field_staged_' + stage + '_comparison.png'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('E:/CHESHIRE_DATA/fold_band_growth_20261011'))
    parser.add_argument('--stages', type=int, choices=(1, 2, 3), default=2)
    parser.add_argument('--board-only', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.board_only:
        for gen in range(1, args.stages + 1):
            board(root, f'G{gen:02}')
        return
    source = root / 'inputs' / 'SPAN_SPARSE' / 'G00' / 'checkpoint.npz'
    control = source.parent / 'control_quad.npz'
    xyz, quads, chart = prior.load_quads(control)
    source_vertices, source_quads = len(xyz), len(quads)
    hashes = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  control_sha256=hashlib.sha256(control.read_bytes()).hexdigest())
    _, curve_vertices, curve_segments, _ = loop.curves.attractor_curves('circle')
    for gen in range(1, args.stages + 1):
        cfg = prior.field_recipe('n4', .55)
        cfg['iterations'] = SCHEDULE[gen - 1]
        folder = root / 'FIELD_STAGED' / f'G{gen:02}'
        signature = dict(algorithm=ALGORITHM, **hashes, stage=gen, field_recipe=cfg,
                         internal_iteration_schedule=list(SCHEDULE), fraction=.55,
                         maximum_step=BUDGETS[gen - 1], target_factor=gen,
                         role_depth=0., quad_splits_per_cycle=1)
        if folder.exists() and any(folder.iterdir()):
            if not (folder / 'generation.json').exists() or json.loads((folder / 'generation.json').read_text(encoding='utf8')).get('signature') != signature:
                raise FileExistsError('Existing stage differs or incomplete; preserved: ' + str(folder))
            xyz, quads, chart = prior.load_quads(folder / 'control_quad.npz')
            print('REUSED FIELD_STAGED', gen, flush=True)
            continue
        # Never reuse a bank from a different escape-iteration classifier.
        trees, fieldpath = prior.helpers.outside_trees(cfg, root)
        cached = json.loads((Path(fieldpath) / 'field.json').read_text(encoding='utf8'))['parameters']
        if cached['iterations'] != cfg['iterations'] or cached['powers'] != cfg['powers']:
            raise ValueError('Outside bank does not match the actual stage classifier.')
        incoming = xyz.copy()
        xyz, quads, chart, payload, rolelog, fieldlog = loop.full_cycle(
            xyz, quads, chart, gen, cfg, trees, .55, BUDGETS[gen - 1], 0.,
            (.22, .15, .10)[gen - 1], gen, curve_vertices, curve_segments, 1.)
        if np.any(payload['role_displacement']):
            raise ValueError('Field-only comparison unexpectedly moved role offsets.')
        px, pt, pc = prior.physical_quads(xyz, quads, chart, gen)
        mesh = trimesh.Trimesh(px, pt, process=False)
        if not np.isfinite(px).all() or not mesh.is_watertight or not mesh.is_winding_consistent:
            raise ValueError('Invalid actual output; no repair.')
        _, errors, matches = prior.reflection_state(px, pt, pc)
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder / 'geometry.npz', xyz=px, faces=pt)
        np.savez_compressed(folder / 'checkpoint.npz', xyz=px, faces=pt, chart=pc)
        np.savez_compressed(folder / 'control_quad.npz', xyz=xyz, faces=quads, chart=chart)
        np.savez_compressed(folder / 'operation_fields.npz', **payload)
        mesh.export(folder / 'gate.ply')
        shutil.copy2(__file__, folder / 'field_lod_probe_recipe.py')
        prior.base.dump(folder / 'generation.json', dict(signature=signature, candidate='FIELD_STAGED', stage=f'G{gen:02}',
            source=str(source), parent=str(source) if gen == 1 else str(folder.parent / f'G{gen-1:02}' / 'checkpoint.npz'),
            operation='One existing bilinear quad split followed by finite nearest-outside attraction; role offsets disabled exactly',
            field_recipe=cfg, field_cache=fieldpath, field_step=fieldlog, role_disabled=True,
            field_iterations=cfg['iterations'], internal_iteration_schedule=list(SCHEDULE),
            actual_iterations_applied=list(SCHEDULE[:gen]), growth_cycles_total=gen,
            field_passes_total=gen, subdivision_passes_total=gen, role_offset_passes_total=0,
            counting_rule='Three growth cycles; each evaluates a finite classifier with internal iteration count 4, 8 or 18. Internal escape iterations are not folding generations.',
            baseline='FIELD_SEED: same source, n4, fraction .55, budgets .35/.28/.22, target refinement 1/2/3, fixed internal escape iterations 18/18/18',
            source_control_vertices=source_vertices, source_control_quads=source_quads,
            control_vertices=len(xyz), control_quads=len(quads), physical_vertices=len(px), physical_triangles=len(pt),
            previous_control_vertices=len(incoming), previous_control_vertex_max_movement=float(np.linalg.norm(xyz[:len(incoming)] - incoming, axis=1).max()),
            finite_inside_fraction=fieldlog['finite_inside_fraction'], fraction=.55, target_mode='refined', local_target_factor=gen,
            maximum_actual_step=fieldlog['maximum_field_step'], field_moved_vertices=fieldlog['field_moved_vertices'],
            minimum_triangle_area=float(mesh.area_faces.min()), minimum_area_threshold=1e-12,
            minimum_area_pass=bool(mesh.area_faces.min() > 1e-12), watertight=bool(mesh.is_watertight),
            winding_consistent=bool(mesh.is_winding_consistent), geometric_reflection_error=errors, reflected_triangle_sets_identical=matches,
            separate_geometric_smoothing=False, CC_coordinate_averaging=False, authored_return=False,
            endpoint_lock=False, feature_memory=False, random_noise=False, final_outside_guarantee=False,
            provenance='Our internal field-resolution staging hypothesis using existing CHESHIRE finite Mandelbulb reconstruction, not a disclosed IAAC schedule or original IAAC code',
            self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication='NOT_CHECKED'))
        print('GENERATED FIELD_STAGED', gen, len(px), len(pt), 'inside', fieldlog['finite_inside_fraction'],
              'field_iterations', cfg['iterations'], 'field_cache', fieldpath, flush=True)
    for gen in range(1, args.stages + 1):
        board(root, f'G{gen:02}')


if __name__ == '__main__':
    main()
