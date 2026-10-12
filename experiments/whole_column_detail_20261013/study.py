"""One full-column, two-scale normal-fold sequence on actual current G6.

No extra CC, topology event, local candidate matrix or external algorithm
research. Actual incoming geometry supplies each stage's normals. The parent
and all previous checkpoints remain read-only.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/whole_column_detail_20261013/trial01')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


loader = module('whole_column_frozen_loader', HERE.parent/'design_one_20261013/study.py')
field = module('whole_column_fixed_field', HERE/'whole_field.py')
core, digest, write = loader.core, loader.digest, loader.write
SOURCE = loader.SOURCE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    if root == SOURCE.resolve() or SOURCE.resolve() in root.parents:
        raise ValueError('Preserved current G6 is read-only.')
    if any((root/stage/'SPAN/G06').exists() for stage in ('MIDDLE', 'FINE')):
        raise FileExistsError('Earlier whole-column output cannot be overwritten.')
    core.memory_guard()
    print('LOAD actual current SPAN DEPTH_08 G6', flush=True)
    mesh, chart, source_faces, vertex_pairs, face_pairs, parent = loader.load_parent()
    baseline_xyz = mesh.xyz.copy()
    original_faces_hash = core.array_hash(mesh.faces)
    print('BUILD full-column feature memory, no isolated patch restriction', flush=True)
    face_support = (~source_faces).astype(float)
    degree = np.bincount(mesh.faces.ravel(), minlength=len(mesh.xyz))
    support = np.bincount(mesh.faces.ravel(), weights=np.repeat(face_support, 4),
        minlength=len(mesh.xyz))/degree
    del source_faces, face_support, degree
    hashes = dict(parent['geometry_code_sha256'])
    for path in (HERE/'study.py', HERE/'whole_field.py', HERE.parent/'design_one_20261013/study.py',
            HERE.parent/'design_one_20261013/batch_sweep.py'):
        hashes[str(path.relative_to(REPO))] = digest(path)
    for name, checksum in hashes.items():
        if digest(REPO/name) != checksum:
            raise ValueError('Frozen source code changed: '+name)
    records, incoming = [], SOURCE
    for stage in ('MIDDLE', 'FINE'):
        print('APPLY whole-column stage', stage, flush=True)
        out, metadata, state = field.build(mesh, chart, vertex_pairs, support, stage)
        if out.generation != 6 or core.array_hash(out.faces) != original_faces_hash:
            raise ValueError('Actual G6 topology must remain unchanged.')
        state.update(mirror_x_face_pairs=face_pairs['X'], mirror_y_face_pairs=face_pairs['Y'])
        proof = loader.actual_symmetry(out, state)
        total = np.linalg.norm(out.xyz-baseline_xyz, axis=1)
        metadata['total_displacement_from_original_quantiles'] = np.quantile(total, [0, .5, .9, .99, 1.]).tolist()
        folder = root/stage/'SPAN/G06'
        context = dict(input_case='SPAN', candidate=stage, source=str(SOURCE),
            source_generation=6, source_control_sha256=parent['control_file_sha256'],
            source_generation_json_sha256=digest(SOURCE/'generation.json'),
            parent_stage=str(incoming), parent_control_sha256=digest(incoming/'control_quad.npz'),
            parent_generation_json_sha256=digest(incoming/'generation.json'),
            geometry_code_sha256=hashes, added_CC_passes=0, added_topology_events=0,
            added_normal_field_passes=1, cumulative_normal_field_passes=len(records)+1,
            added_mandelbulb_evaluations=0, operator_metadata=metadata, symmetry=proof,
            design_scope='One whole-column sequence: original G6 -> middle directional folds -> fine directional folds. All are actual G6 states, not consecutive subdivision generations.',
            feature_memory_scope='Original saved event ancestry attenuates existing ornament; SOURCE body is also active. No selected disk limits the new support.',
            methodology_scope='Existing incident-normal extrusion and directional periodic band logic, with one authored full-body physical-scale profile; not reference-exact reproduction.',
            validation_scope='Existing finite/closed-oriented/control connectivity/no-orphan/native-area checks and actual oriented-control/XYZ reflection once per saved stage.',
            exclusions=['Independent full geometry replay', 'Native triangle-set sorting',
                'Self-intersection repair', 'Fabrication suitability', 'Aesthetic certification'])
        print('SAVE actual stage and required checks', stage, flush=True)
        record = core.save(folder, out, chart, context, state)
        records.append(dict(stage=stage, folder=str(folder),
            generation_json_sha256=digest(folder/'generation.json'),
            checks=record['checks'], symmetry=proof, operator_metadata=metadata))
        mesh, incoming = out, folder
        del state, record, total
        gc.collect()
    if digest(SOURCE/'control_quad.npz') != parent['control_file_sha256']:
        raise ValueError('Preserved current G6 changed during run.')
    write(root/'SUMMARY.json', dict(input_case='SPAN', source=str(SOURCE),
        source_generation=6, subdivision_generation=6, added_CC_passes=0,
        added_topology_events=0, whole_column_normal_passes=2, stages=records,
        quick_integrity_passed=all(x['checks']['passed'] for x in records),
        symmetry_passed=all(x['symmetry']['passed'] for x in records),
        geometry_code_sha256=hashes, visual_success='PENDING_WHOLE_COLUMN_REVIEW',
        completion_scope='Two actual whole-column stages; visual hierarchy and density require designer review.'))
    print('DONE one whole-column sequence, two saved G6 stages, CC added 0', flush=True)


if __name__ == '__main__':
    main()
