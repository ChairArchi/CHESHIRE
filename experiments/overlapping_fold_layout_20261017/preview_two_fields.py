"""Show the actual two finite Mandel generating fields before column response.

Original finite_inside/classify is sampled separately for centres 3.2 and 6.8.
Marching-cubes surfaces approximate those sampled fields. They are not the
authored PCHIP column G0, a final column, exact fractal surfaces, or a mesh CSG.
The combined preview concatenates both full source meshes with ownership tags.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time

import numpy as np


REPO = Path(__file__).resolve().parents[2]
DEFAULT = Path('C:/Users/USER/CHESHIRE/scratch/TWO_MANDEL_INITIAL_COLORED_20261017')
_DLL_HANDLES = []


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def checks(x, t):
    directed = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]])
    edges, inverse, count = np.unique(np.sort(directed, axis=1), axis=0,
                                      return_inverse=True, return_counts=True)
    balance = np.bincount(inverse, weights=np.sign(directed[:, 1]-directed[:, 0]))
    p = x[t]
    area = .5*np.linalg.norm(np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=1)
    volume = float(np.einsum('ij,ij->i', p[:, 0], np.cross(p[:, 1], p[:, 2])).sum()/6.)
    return dict(vertices=len(x), triangles=len(t), finite=bool(np.isfinite(x).all()),
        closed_two_face_edges=bool(np.all(count == 2)),
        oriented_edges=bool(np.all(balance == 0)), Euler=int(len(x)-len(edges)+len(t)),
        minimum_triangle_area=float(area.min()), signed_volume=volume,
        exact_fractal_or_fabrication_certification=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError('Preserve the previous two-field preview.')
    started = time.perf_counter()
    seed = module('two_field_actual_seed_import', REPO/'experiments/column_development_20261011/seed_mass.py')
    prior = module('two_field_actual_recipe_import', REPO/'experiments/column_development_20261011/target_repeat.py')
    variation = seed.variation
    cfg = prior.field_recipe('n4', .55)
    cfg.update(centres=[3.2, 6.8], axial=3.3, iterations=8)
    deps = Path('C:/Users/USER/CHESHIRE/scratch/grotesque_gate_20261010/deps')
    if os.name == 'nt':
        _DLL_HANDLES.append(os.add_dll_directory(str(deps)))
    sys.path.insert(0, str(deps))
    from skimage.measure import marching_cubes
    axes = [np.linspace(-2.4, 2.4, 81), np.linspace(-2.4, 2.4, 81),
            np.linspace(-2., 12., 225)]
    shape = tuple(len(a) for a in axes)
    spacing = tuple(float(a[1]-a[0]) for a in axes)
    points = np.stack(np.meshgrid(*axes, indexing='ij'), axis=-1).reshape(-1, 3)
    grids = []
    meshes = []
    rows = []
    for index, centre in enumerate(cfg['centres']):
        single = dict(cfg, centres=[centre], powers=[cfg['powers'][index]])
        inside = variation.classify(points, single).reshape(shape)
        border = np.concatenate((inside[0].ravel(), inside[-1].ravel(),
                                 inside[:, 0].ravel(), inside[:, -1].ravel(),
                                 inside[:, :, 0].ravel(), inside[:, :, -1].ravel()))
        if border.any() or not inside.any():
            raise ValueError('Source surface is truncated by the sampling bounds or empty.')
        # Exact .5 creates coincident binary saddle vertices in this grid.
        # A declared .001 level offset separates those digital ambiguities.
        x, t, _normals, _values = marching_cubes(inside.astype(np.float32), .501,
            spacing=spacing, gradient_direction='descent', allow_degenerate=False)
        x = x.astype(np.float64)+np.array([a[0] for a in axes])
        t = t.astype(np.int64)
        proof = checks(x, t)
        if proof['signed_volume'] < 0:
            t = t[:, ::-1].copy()
            proof = checks(x, t)
        if not (proof['finite'] and proof['closed_two_face_edges'] and
                proof['oriented_edges'] and proof['minimum_triangle_area'] > 0):
            raise ValueError('Actual sampled source mesh failed native closure/orientation: '+str(proof))
        grids.append(inside)
        meshes.append((x, t))
        rows.append(dict(id='mass_'+('A' if index == 0 else 'B'), centre=centre,
                         cfg=single, inside_samples=int(inside.sum()),
                         all_six_sample_bounds_outside=True, native_checks=proof))
    actual_union = variation.classify(points, cfg).reshape(shape)
    if not np.array_equal(actual_union, grids[0] | grids[1]):
        raise ValueError('Actual original classifier differs from the two-source logical union.')
    output.mkdir(parents=True)
    offset = 0
    combined_xyz, combined_faces, tags = [], [], []
    for index, ((x, t), row) in enumerate(zip(meshes, rows)):
        path = output/(row['id']+'.npz')
        np.savez_compressed(path, xyz=x, faces=t)
        row.update(file=str(path), sha256=sha(path))
        combined_xyz.append(x); combined_faces.append(t+offset)
        tags.append(np.full(len(t), index, np.int32)); offset += len(x)
    np.savez_compressed(output/'combined.npz', xyz=np.concatenate(combined_xyz),
                        faces=np.concatenate(combined_faces))
    np.save(output/'source_mass_tags.npy', np.concatenate(tags))
    palette = [dict(name='A · 중심 Z=3.2', rgb=[.035, .35, .88]),
               dict(name='B · 중심 Z=6.8', rgb=[1., .32, .045])]
    plan = dict(common_scale=13.0, items=[dict(id='TWO_MANDEL_INITIAL',
        geometry=str(output/'combined.npz'), views=[], color=True,
        face_colors=str(output/'source_mass_tags.npy'), palette=palette,
        color_name='source_masses', color_meaning='Blue/orange are actual separate finite Mandel source-field ownership, not column density classes or mesh CSG result.')])
    (output/'RENDER_PLAN.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf8')
    receipt = dict(schema='CHESHIRE_ACTUAL_TWO_MANDEL_SOURCE_FIELDS_PREVIEW_V1',
        actual_cfg=cfg, sources=rows,
        sampling_bounds=[[float(a[0]), float(a[-1])] for a in axes],
        grid_shape=shape, spacing=spacing, all_source_boundaries_outside=True,
        exact_sampled_OR_proof=True, overlap_inside_samples=int((grids[0]&grids[1]).sum()),
        union_inside_samples=int(actual_union.sum()),
        source_kernel_code_sha256={str(Path(p).resolve()):sha(p) for p in
            (variation.__file__, variation.base.__file__, prior.__file__)},
        generator_sha256=sha(Path(__file__).resolve()),
        combined_geometry_sha256=sha(output/'combined.npz'),
        source_tags_sha256=sha(output/'source_mass_tags.npy'),
        interpretation='Two separately sampled original finite Mandel generating fields, displayed in different colors before the column response.',
        column_G0=False, exact_fractal_surface=False, mesh_CSG=False,
        final_column_geometry=False, marching_cubes_level=.501,
        approximation='Marching cubes on the stated binary finite-inside/outside world grid. Level .501 instead of exact .5 resolves coincident digital saddle vertices; the original finite classifier is unchanged.',
        elapsed_seconds=time.perf_counter()-started)
    (output/'SOURCE_FIELDS_RECEIPT.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(dict(output=str(output), triangles=[len(t) for _x,t in meshes],
                         overlap_samples=receipt['overlap_inside_samples'],
                         elapsed_seconds=receipt['elapsed_seconds'])), flush=True)


if __name__ == '__main__':
    main()
