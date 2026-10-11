"""Two genuine G0 masses on one preserved unsplit column topology.

SPAN reads the actual saved SPAN_SPARSE controls. COUNTER evaluates its
existing initial-mass recipe directly on the same material chart. Neither
input is a warp of OVERLAP G3. No field/growth pass or cap repair is added.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'src'))
sys.path.insert(0, str(HERE.parent / 'terminal_fold_20261011'))
spec = importlib.util.spec_from_file_location('transfer_existing_seed_mass',
    HERE.parent / 'column_development_20261011' / 'seed_mass.py')
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)
import iaac_repeat as repeated
from cheshire import task36_growth
from cheshire.reference_subdivision import ArrayMesh

DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/fold_transfer_20261012')
SPAN_SOURCE = Path('E:/CHESHIRE_DATA/fold_band_growth_20261011/inputs/SPAN_SPARSE/G00')
COUNTER_REFERENCE = Path('E:/CHESHIRE_DATA/column_development_20261011/inputs/COUNTER/G00')
ALGORITHM = 'PRESERVED_SPAN_AND_EXISTING_COUNTER_SAME_G0_TOPOLOGY_V1'
CARRIER = dict(rings=25, sectors=16, radius=.78)


def prepare(root=DEFAULT_ROOT):
    """Prepare or reuse these exact inputs and return name -> G00 Path."""
    root = Path(root).resolve()
    original, chart = seed.variation.carrier(CARRIER)
    with np.load(SPAN_SOURCE / 'control_quad.npz', allow_pickle=False) as saved:
        span_xyz = saved['xyz'].copy()
        if (not np.array_equal(saved['faces'], original.faces)
                or not np.array_equal(saved['chart'], chart)):
            raise ValueError('Saved SPAN no longer matches the original unsplit carrier topology/chart.')
    span_meta = json.loads((SPAN_SOURCE / 'generation.json').read_text(encoding='utf8'))
    counter_recipe = json.loads(json.dumps(seed.RECIPES['COUNTER']))
    folders = {}
    for name in ('SPAN', 'COUNTER'):
        folder = root / 'inputs' / name / 'G00'
        folders[name] = folder
        provenance = (dict(kind='actual_saved_G0_control',
            control=str(SPAN_SOURCE / 'control_quad.npz'),
            initial_function='seed_mass.legacy_core',
            source_code=str(HERE.parent / 'fold_band_growth_20261011' / 'sparse_input.py'),
            mass_recipe=span_meta['recipe']) if name == 'SPAN' else
            dict(kind='direct_existing_initial_mass_function_on_common_G0_chart',
            initial_function='seed_mass.evaluate',
            source_code=str(Path(seed.__file__).resolve()),
            recipe_dictionary='seed_mass.RECIPES[COUNTER]', mass_recipe=counter_recipe,
            existing_family_reference=str(COUNTER_REFERENCE),
            sampling_difference='Reference is 97 rings/64 sectors; this direct analytic resampling uses 25 rings/16 sectors. It is not a decimation or a later-checkpoint warp.'))
        signature = dict(algorithm=ALGORITHM, candidate=name, stage='G00',
            carrier=CARRIER, provenance=provenance)
        if folder.exists() and any(folder.iterdir()):
            saved_meta = folder / 'generation.json'
            if not saved_meta.exists():
                raise FileExistsError('Incomplete input preserved: ' + str(folder))
            old = json.loads(saved_meta.read_text(encoding='utf8'))
            if old.get('signature') != signature or old.get('quick_integrity') != 'PASS':
                raise FileExistsError('Different or failed input preserved: ' + str(folder))
            if not all((folder / f).exists() for f in
                    ('control_quad.npz', 'checkpoint.npz', 'geometry.npz', 'column.ply')):
                raise FileExistsError('Saved input lacks required actual artifacts: ' + str(folder))
            print('REUSED INPUT', name, folder, flush=True)
            continue
        xyz, parts = (span_xyz.copy(), {}) if name == 'SPAN' else seed.evaluate(chart, counter_recipe)
        mesh = ArrayMesh(xyz, original.faces.copy(), original.classes.copy(),
            original.rest.copy(), original.anchors.copy(), 0)
        mesh.surface = 'mean'
        physical = task36_growth.native(mesh)
        triangles = physical.faces[:, :3]
        physical_chart = np.concatenate([chart, chart[mesh.faces].mean(1)])
        reflection_failure = None
        try:
            _, errors, matches = repeated.reflection_state(physical.xyz, triangles, physical_chart)
        except ValueError as error:
            reflection_failure = str(error)
            errors = None
            matches = None
        actual = trimesh.Trimesh(physical.xyz, triangles, process=False)
        minimum_area = float(actual.area_faces.min())
        components = len(trimesh.graph.connected_components(actual.face_adjacency,
            nodes=np.arange(len(triangles)), min_len=1))
        cap_faces = np.array([np.all(chart[q, 0] < 1e-10) or
            np.all(chart[q, 0] > 1. - 1e-10) for q in mesh.faces])
        end_measurements = []
        for s in (0., 1.):
            ids = np.flatnonzero(np.abs(chart[:, 0] - s) < 1e-10)
            centre = ids[np.linalg.norm(chart[ids, 1:], axis=1) < 1e-10]
            rim = ids[np.linalg.norm(chart[ids, 1:], axis=1) > .99]
            end_measurements.append(dict(material_height=s,
                control_sample_count=len(ids), centre_control_count=len(centre),
                rim_control_count=len(rim), centre_z=xyz[centre, 2].tolist(),
                rim_z_min=float(xyz[rim, 2].min()), rim_z_max=float(xyz[rim, 2].max()),
                terminal_control_z_range=float(np.ptp(xyz[ids, 2]))))
        checks = dict(finite=bool(np.isfinite(physical.xyz).all()),
            watertight=bool(actual.is_watertight), winding_consistent=bool(actual.is_winding_consistent),
            components=components, minimum_triangle_area=minimum_area,
            minimum_area_threshold=1e-12, minimum_area_pass=minimum_area > 1e-12,
            geometric_reflection_error=errors, reflected_triangle_sets_identical=matches,
            reflection_failure=reflection_failure)
        passed = (checks['finite'] and checks['watertight'] and checks['winding_consistent']
            and checks['minimum_area_pass'] and components == 1 and reflection_failure is None)
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder / 'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces,
            chart=chart, classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors,
            generation=np.array(0), surface=np.array('mean'))
        np.savez_compressed(folder / 'geometry.npz', xyz=physical.xyz, faces=triangles)
        np.savez_compressed(folder / 'checkpoint.npz', xyz=physical.xyz, faces=triangles,
            chart=physical_chart, classes=physical.classes, rest=physical.rest,
            anchors=physical.anchors, generation=np.array(0), surface=np.array('mean'))
        if parts:
            np.savez_compressed(folder / 'input_parts.npz', **parts)
        actual.export(folder / 'column.ply')
        shutil.copy2(__file__, folder / 'input_adapter.py')
        shutil.copy2(seed.__file__, folder / 'source_seed_mass_recipe.py')
        if name == 'SPAN':
            shutil.copy2(SPAN_SOURCE / 'sparse_input_recipe.py', folder / 'source_sparse_input_recipe.py')
        metadata = dict(signature=signature, algorithm=ALGORITHM, candidate=name, stage='G00',
            operation='Read actual preserved SPAN initial geometry and restore original carrier lineage' if name == 'SPAN'
                else 'Evaluate unmodified existing COUNTER initial-mass recipe directly on the common unsplit material chart',
            source=provenance, carrier=CARRIER, generation=0, surface='mean',
            original_carrier_lineage='Rest, classes and anchors copied from the same unmodified variation.carrier(25,16,.78); generation reset is unnecessary because it is genuinely G0.',
            same_topology_and_chart_as=str(SPAN_SOURCE / 'control_quad.npz'),
            source_control_vertices=len(xyz), source_control_quads=len(mesh.faces),
            physical_vertices=len(physical.xyz), physical_triangles=len(triangles),
            bounding_box_min=xyz.min(0).tolist(), bounding_box_max=xyz.max(0).tolist(),
            terminal_measurements=end_measurements, terminal_control_quads=int(cap_faces.sum()),
            terminal_limit='Unsplit caps have only original centre/rim controls and can read as broad planar fan panels. No interior cap samples, flatness correction, remeshing or terminal repair were added.',
            field_passes_total=0, subdivision_growth_passes_total=0,
            initial_carrier_bilinear_splits=0, separate_geometric_smoothing=False,
            CC_coordinate_averaging=False, physical_fold_solver=False,
            provenance_limit='Explicit initial folded masses from existing CHESHIRE functions; no OVERLAP G3 warp and no claim of fractal-emergent initial folds.',
            quick_integrity='PASS' if passed else 'FAILED_PRESERVED_NO_REPAIR',
            self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication_thickness_structure='NOT_CHECKED',
            **checks)
        (folder / 'generation.json').write_text(json.dumps(metadata, indent=2), encoding='utf8')
        print('PREPARED INPUT', name, len(xyz), len(mesh.faces), len(physical.xyz), len(triangles),
            'area', minimum_area, 'symmetry', errors, 'quick', metadata['quick_integrity'], flush=True)
        if not passed:
            raise ValueError('Failed actual input preserved without repair or threshold change.')
    return folders


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    prepare(args.root)


if __name__ == '__main__':
    main()
