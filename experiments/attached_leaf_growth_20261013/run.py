"""Connected Task32 leaf/child patches on the selected existing SPAN G7.

The latest WIDE_ROOT_FINISHED supplies actual geometry. The prior fixed loader
supplies its hash-bound registered frame and explicit reflection IDs only.
One whole column, no additional CC, no smoothing trial, no second input.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import shutil
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


SOURCE_LOADER = HERE.parent/'finite_fork_folds_20261013/run.py'
previous = module('attached_leaf_frozen_source_loader', SOURCE_LOADER)
operator = module('attached_leaf_fixed_operator', HERE/'leaf_operator.py')
core, loader, digest, write = previous.core, previous.loader, previous.digest, previous.write
SOURCE = previous.SOURCE
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/attached_leaf_growth_20261013/trial01')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    started = time.perf_counter()
    root = args.root.resolve()
    if root.exists() and any(root.iterdir()):
        raise FileExistsError('Prior output preserved; use a new empty root.')
    if root == SOURCE.resolve() or SOURCE.resolve() in root.parents:
        raise ValueError('Selected original column is read-only.')
    guard = previous.base.finish.memory_guard()
    root.mkdir(parents=True, exist_ok=True)
    write(root/'RUN_REQUEST.json', dict(date='2026-10-13', timezone='Asia/Seoul',
        basis_commit='4240d236d28a37551a26ce182cefafd70e662ebb',
        source=str(SOURCE), source_receipt_sha256=previous.SOURCE_RECEIPT_SHA256,
        input_case='SPAN', candidate='ATTACHED_LEAF', subdivision_generation=7,
        added_CC_passes=0, added_normal_field_passes=0, added_mandelbulb_evaluations=0,
        purpose='Actual connected roots with two cap-owned child folds; visual readability rather than surface smoothing.',
        excluded_inputs=['CENTRAL_SPINDLE', 'FINITE_FORK trial01', 'FINITE_FORK trial02'],
        execution='One selected whole column; fixed placements and recipe; no parameter matrix.'))
    print('LOAD original current SPAN G7 and registered source frame', flush=True)
    mesh, chart, pairs, coords, height, source, ancestry, bindings = previous.load()
    input_xyz_hash = previous.prior.array_hash(mesh.xyz)
    hashes = dict(source['geometry_code_sha256'])
    hashes.update(operator.code_hashes())
    for path in (HERE/'run.py', SOURCE_LOADER,
            HERE.parent/'finite_fork_folds_20261013/fold_operator.py'):
        hashes[path.relative_to(REPO).as_posix()] = digest(path)
    for rel, expected in hashes.items():
        path = REPO/Path(rel.replace('\\', '/'))
        if digest(path) != expected:
            raise ValueError('Frozen source changed: '+rel)
        target = root/'source_snapshot'/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        if digest(target) != expected:
            raise ValueError('Snapshot bytes differ: '+rel)
    write(root/'RECIPE.json', dict(date='2026-10-13', timezone='Asia/Seoul',
        input_case='SPAN', candidate='ATTACHED_LEAF', source=str(SOURCE),
        source_receipt_sha256=previous.SOURCE_RECEIPT_SHA256,
        recipe=operator.RECIPE, geometry_code_sha256=hashes, frame_bindings=bindings))
    source_counts = dict(vertices=len(mesh.xyz), faces=len(mesh.faces))
    reflection = dict(X=pairs['mirror_x_vertex_pairs'], Y=pairs['mirror_y_vertex_pairs'],
        face_X=pairs['mirror_x_face_pairs'], face_Y=pairs['mirror_y_face_pairs'])
    print('BUILD local closed-shell Task32 roots and cap children; splice into whole G7', flush=True)
    out, outchart, metadata, state = operator.build(mesh, chart, reflection,
        coords['parent_phase'], coords['normalized_z'], coords['feature_support'], height)
    if (out.generation != 7 or len(out.xyz) <= source_counts['vertices']
            or len(out.faces) <= source_counts['faces']
            or previous.prior.array_hash(mesh.xyz) != input_xyz_hash):
        raise ValueError('Actual unchanged source and connected G7 additions required.')
    events = int(metadata['added_topology_events'])
    if events <= 0:
        raise ValueError('No actual topology events were constructed.')
    print('VERIFY actual full-column reflected XYZ and oriented quad cycles', flush=True)
    symmetry = loader.actual_symmetry(out, state)
    context = dict(input_case='SPAN', candidate='ATTACHED_LEAF', source=str(SOURCE),
        source_generation=7, source_control_sha256=source['control_file_sha256'],
        source_generation_json_sha256=previous.SOURCE_RECEIPT_SHA256,
        parent_stage=str(SOURCE), parent_control_sha256=source['control_file_sha256'],
        parent_generation_json_sha256=previous.SOURCE_RECEIPT_SHA256,
        geometry_code_sha256=hashes, added_CC_passes=0,
        added_topology_events=events, added_normal_field_passes=0,
        cumulative_normal_field_passes=source['cumulative_normal_field_passes'],
        added_mandelbulb_evaluations=0, source_geometry_averaged=False,
        operator_metadata=metadata, frame_ancestry=ancestry, source_bindings=bindings,
        source_counts=source_counts, symmetry=symmetry, memory_guard_before_load=guard,
        design_scope='Only original SPAN G7 developed with connected Task32 roots and cap-owned descendants.',
        topology_scope='Topology-changing construction events do not increment subdivision generation. Temporary closed-shell backs/walls are excluded from the final column.',
        methodology_scope='Frozen existing Task32 sweep reused on small local closed shells, with explicit source-ID boundary attachment and reflected patch additions.',
        validation_scope='Source hashes and immutability, local surgery/interface checks, full actual control symmetry, then one full closed-oriented/connectivity/no-orphan/native-area check at save.',
        exclusions=['G8', 'CENTRAL_SPINDLE development', 'FINITE_FORK stacking',
            'Global source smoothing', 'Parameter matrix', 'Independent full replay',
            'Native triangle-set sorting', 'Self-intersection repair',
            'Fabrication suitability', 'Reference-exact reproduction', 'Aesthetic certification'])
    del mesh, chart, pairs, coords, reflection
    gc.collect()
    folder = root/'ATTACHED_LEAF/SPAN/G07'
    print('SAVE one actual whole G7; run required full mesh checks once', flush=True)
    record = core.save(folder, out, outchart, context, state)
    if digest(SOURCE/'generation.json') != previous.SOURCE_RECEIPT_SHA256:
        raise ValueError('Original source receipt changed.')
    previous.base.checked(SOURCE, source, (('control_quad.npz', 'control_file_sha256'),
        ('evidence.npz', 'evidence_file_sha256')))
    for rel, expected in hashes.items():
        if digest(REPO/rel) != expected:
            raise ValueError('Source code changed during construction: '+rel)
    if digest(Path(bindings['source_summary'])) != bindings['source_summary_sha256']:
        raise ValueError('Preserved source summary changed.')
    frame = Path(bindings['frame_folder'])
    for name, key in [('generation.json', 'frame_receipt_sha256'),
            ('control_quad.npz', 'frame_control_sha256'), ('evidence.npz', 'frame_evidence_sha256')]:
        if digest(frame/name) != bindings[key]:
            raise ValueError('Registered frame changed during construction.')
    write(root/'SUMMARY.json', dict(date='2026-10-13', timezone='Asia/Seoul',
        source=str(SOURCE), source_generation=7, input_case='SPAN', candidate='ATTACHED_LEAF',
        folder=str(folder), subdivision_generation=7, added_CC_passes=0,
        added_topology_events=events, added_normal_field_passes=0,
        added_mandelbulb_evaluations=0,
        generation_json_sha256=digest(folder/'generation.json'),
        control_vertices=len(out.xyz), control_quads=len(out.faces),
        native_triangles=record['native_triangles'], checks=record['checks'],
        symmetry=symmetry, operator_metadata=metadata, geometry_code_sha256=hashes,
        elapsed_generation_seconds=time.perf_counter()-started,
        actual_generation_process_memory=previous.process_memory(),
        visual_success='PENDING_MATCHED_ACTUAL_RENDER_REVIEW'))
    print('DONE actual connected leaf/child G7; renders pending', flush=True)


if __name__ == '__main__':
    main()
