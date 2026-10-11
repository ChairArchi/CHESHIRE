"""One unsplit Q400 ablation of the existing SPAN_COARSE analytic mass.

Same legacy_core and declared SPAN recipe; only preparatory sampling is reduced.
Caps have fewer interior samples and may lose their rounded return geometry.
No additional folding formula, coordinate smoothing or remeshing is introduced.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'sparse_seed_mass', HERE.parent / 'column_development_20261011' / 'seed_mass.py')
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)
from cheshire import task36_growth
from scipy.spatial import cKDTree


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('E:/CHESHIRE_DATA/fold_band_growth_20261011'))
    args = parser.parse_args()
    folder = args.root / 'inputs' / 'SPAN_SPARSE' / 'G00'
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError('Existing input preserved: ' + str(folder))
    mesh, chart = seed.variation.carrier(dict(rings=25, sectors=16, radius=.78))
    recipe = json.loads(json.dumps(seed.RECIPES['SPAN']))
    recipe['radius'][0] *= 1.10; recipe['radius'][-1] *= 1.10
    recipe['events'][-1]['span'] *= 1.35
    recipe['events'][-1]['return_depth'] *= 1.12
    xyz, parts = seed.legacy_core(chart, recipe, 'SPAN')
    mesh.xyz = xyz
    physical = task36_growth.native(mesh)
    tri = physical.faces[:, :3]
    physical_chart = np.vstack([chart, chart[mesh.faces].mean(axis=1)])
    actual = trimesh.Trimesh(physical.xyz, tri, process=False)
    if not np.isfinite(physical.xyz).all() or not actual.is_watertight or not actual.is_winding_consistent:
        raise ValueError('Invalid sparse input; no repair applied.')
    tree = cKDTree(physical_chart)
    errors = []
    for axis, material_axis in ((0, 1), (1, 2)):
        sign = np.ones(3); sign[material_axis] = -1
        distance, pairs = tree.query(physical_chart * sign)
        if distance.max() > 1e-9:
            raise ValueError('Missing reflected material correspondence.')
        physical_sign = np.ones(3); physical_sign[axis] = -1
        errors.append(float(np.linalg.norm(physical.xyz - physical.xyz[pairs] * physical_sign, axis=1).max()))
    if max(errors) > 1e-9:
        raise ValueError('Sparse input lost X/Y reflection.')
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder / 'geometry.npz', xyz=physical.xyz, faces=tri)
    np.savez_compressed(folder / 'checkpoint.npz', xyz=physical.xyz, faces=tri, chart=physical_chart)
    np.savez_compressed(folder / 'control_quad.npz', xyz=xyz, faces=mesh.faces, chart=chart)
    np.savez_compressed(folder / 'operation_fields.npz', **parts)
    actual.export(folder / 'gate.ply')
    shutil.copy2(__file__, folder / 'sparse_input_recipe.py')
    metadata = dict(candidate='SPAN_SPARSE', stage='G00',
        operation='Existing SPAN legacy_core and unchanged adjusted coarse recipe on unsplit 25-ring/16-sector carrier',
        recipe=recipe, control_vertices=len(xyz), control_quads=len(mesh.faces),
        vertices=len(physical.xyz), triangles=len(tri),
        minimum_triangle_area=float(actual.area_faces.min()), minimum_area_threshold=1e-12,
        minimum_area_pass=bool(actual.area_faces.min() > 1e-12),
        watertight=bool(actual.is_watertight), winding_consistent=bool(actual.is_winding_consistent),
        geometric_reflection_error=errors, input_carrier_bilinear_splits=0,
        cap_interior_sampling='Original unsplit carrier only; no added interior samples',
        source_code=str(Path(seed.__file__).resolve()), source_function='seed_mass.legacy_core',
        same_recipe_reference='E:/CHESHIRE_DATA/column_development_20261011/inputs/SPAN_COARSE/G00',
        limitation='Sampling ablation, not exact geometric decimation. Coarse cap samples may lose deep concave end returns. No guarantee of subsequent meso-scale improvement.',
        separate_geometric_smoothing=False, CC_coordinate_averaging=False,
        physical_fold_solver=False, self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication='NOT_CHECKED')
    (folder / 'generation.json').write_text(json.dumps(metadata, indent=2), encoding='utf8')
    print('INPUT SPAN_SPARSE', len(xyz), len(mesh.faces), len(physical.xyz), len(tri),
          'minimum_area', actual.area_faces.min(), 'reflection', errors, flush=True)


if __name__ == '__main__':
    main()
