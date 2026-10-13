"""One bounded fairing and finite fork-fold update of the selected SPAN G7.

Actual geometry continues WIDE_ROOT_FINISHED, never CENTRAL_SPINDLE.
The saved WIDE_ROOT evidence supplies registered phase/height/feature IDs;
identical association bytes bind those coordinates to this actual input.
Only one final native mesh is saved. No new subdivision is performed.
"""
from pathlib import Path
import argparse
import ctypes
import gc
import json
import shutil
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OLD = HERE.parent/'parent_linked_folds_20261013'
sys.path.insert(0, str(OLD))
import study as base  # noqa: E402
import smooth_relief as prior  # noqa: E402

if Path(base.__file__).resolve() != (OLD/'study.py').resolve():
    raise ImportError('The frozen parent-linked study must supply mesh helpers.')

operator = base.module('finite_fork_fixed_operator', HERE/'fold_operator.py')
core, loader, digest, write = base.core, base.loader, base.digest, base.write
SOURCE = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07')
SOURCE_RECEIPT_SHA256 = 'c7452dc63998c61783215f0bb23434ea5e9b223d89fcd836d1a4081907ab2cf5'
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/finite_fork_folds_20261013/trial01')


def process_memory():
    """Actual Windows counters for this Python process, including save/checks."""
    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong)]+[
            (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
                'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    get_process = ctypes.windll.kernel32.GetCurrentProcess
    get_process.restype = ctypes.c_void_p
    read_memory = ctypes.windll.psapi.GetProcessMemoryInfo
    read_memory.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong)
    read_memory.restype = ctypes.c_int
    if not read_memory(get_process(), ctypes.byref(counters), counters.cb):
        raise OSError('GetProcessMemoryInfo failed.')
    return dict(peak_working_set_bytes=int(counters.PeakWorkingSetSize),
        current_working_set_bytes=int(counters.WorkingSetSize),
        peak_pagefile_usage_bytes=int(counters.PeakPagefileUsage),
        scope='Windows counters for this one generation Python process; render processes excluded.')


def load():
    if digest(SOURCE/'generation.json') != SOURCE_RECEIPT_SHA256:
        raise ValueError('The selected latest SPAN checkpoint receipt changed.')
    info = prior.checked_receipt(SOURCE)
    if (info.get('candidate') != 'WIDE_ROOT_FINISHED' or info.get('added_CC_passes') != 0
            or info.get('finish_smoothing_passes') != 3):
        raise ValueError('Selected WIDE_ROOT_FINISHED G7 required.')
    source_summary = SOURCE.parents[2]/'SUMMARY.json'
    if base.read(source_summary)['generation_json_sha256'] != SOURCE_RECEIPT_SHA256:
        raise ValueError('Source summary and selected generation receipt disagree.')
    frame_folder = Path(info['raw_field_stage'])
    frame = prior.checked_receipt(frame_folder)
    if (frame.get('candidate') != 'WIDE_ROOT'
            or digest(frame_folder/'generation.json') != info['raw_field_generation_json_sha256']
            or frame['control_file_sha256'] != info['raw_field_control_sha256']
            or frame['evidence_file_sha256'] != info['raw_field_evidence_sha256']):
        raise ValueError('Actual registered raw-field dependency changed.')
    associations = prior.association_hashes(frame_folder/'control_quad.npz', SOURCE/'control_quad.npz')
    data = loader.arrays(SOURCE/'control_quad.npz',
        ('xyz', 'faces', 'classes', 'rest', 'anchors', 'chart', 'generation', 'surface'))
    mesh = core.ArrayMesh(data['xyz'], data['faces'], data['classes'], data['rest'],
        data['anchors'], int(data['generation']))
    mesh.surface = str(data['surface'])
    if (mesh.generation != 7 or mesh.surface != 'mean'
            or mesh.xyz.shape != (info['control_vertices'], 3)
            or mesh.faces.shape != (info['control_quads'], 4)
            or prior.array_hash(mesh.xyz) != info['checks']['control_xyz_sha256']):
        raise ValueError('Actual source arrays disagree with the saved receipt.')
    pairs = loader.arrays(SOURCE/'evidence.npz', ('mirror_x_vertex_pairs',
        'mirror_y_vertex_pairs', 'mirror_x_face_pairs', 'mirror_y_face_pairs'))
    coordinates = loader.arrays(frame_folder/'evidence.npz',
        ('parent_phase', 'normalized_z', 'feature_support'))
    height = float(frame['operator_metadata']['physical_height'])
    ancestry = dict(info['frame_ancestry'])
    ancestry.update(actual_geometry_source=str(SOURCE),
        actual_geometry_source_control_sha256=info['control_file_sha256'],
        actual_geometry_source_generation_sha256=SOURCE_RECEIPT_SHA256,
        registered_coordinate_source=str(frame_folder),
        registered_coordinate_evidence_sha256=frame['evidence_file_sha256'],
        registered_coordinate_generation_sha256=digest(frame_folder/'generation.json'),
        unchanged_source_association_npy_sha256=associations,
        source_scope='Actual latest SPAN XYZ only; WIDE_ROOT supplies saved registered frame on byte-identical associations.')
    bindings = dict(source_summary=str(source_summary), source_summary_sha256=digest(source_summary),
        frame_folder=str(frame_folder), frame_receipt_sha256=digest(frame_folder/'generation.json'),
        frame_control_sha256=frame['control_file_sha256'], frame_evidence_sha256=frame['evidence_file_sha256'])
    return mesh, data['chart'], pairs, coordinates, height, info, ancestry, bindings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    started = time.perf_counter()
    root = args.root.resolve()
    if root.exists() and any(root.iterdir()):
        raise FileExistsError('Prior output is preserved; use a new output root.')
    if root == SOURCE.resolve() or SOURCE.resolve() in root.parents:
        raise ValueError('The selected source is read-only.')
    before_memory = base.finish.memory_guard()
    root.mkdir(parents=True, exist_ok=True)
    write(root/'RUN_REQUEST.json', dict(date='2026-10-13', timezone='Asia/Seoul',
        basis_commit='ebaa00b9ac5d291a4c519dbfba1ffc7b862580a0', source=str(SOURCE),
        source_receipt_sha256=SOURCE_RECEIPT_SHA256, input_case='SPAN', candidate='FINITE_FORK',
        design_scope='Only the selected existing SPAN column is developed. CENTRAL_SPINDLE is preserved without further development.',
        sequence=['Bounded actual G7 geometry fairing', 'Finite fork-fold surface relief'],
        added_CC_passes=0, added_topology_events=0, added_normal_field_passes=1,
        new_inputs=0, candidate_count=1, generation=7))
    print('LOAD latest actual SPAN G7 and saved registered frame', flush=True)
    mesh, chart, pairs, coords, height, source, ancestry, bindings = load()
    hashes = dict(source['geometry_code_sha256'])
    hashes.update(operator.code_hashes())
    hashes[str((HERE/'run.py').relative_to(REPO))] = digest(HERE/'run.py')
    for name, expected in hashes.items():
        original = REPO/Path(name.replace('\\', '/'))
        if digest(original) != expected:
            raise ValueError('Frozen geometric source changed: '+name)
        snapshot = root/'source_snapshot'/name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, snapshot)
        if digest(snapshot) != expected:
            raise ValueError('Source snapshot bytes differ: '+name)
    write(root/'RECIPE.json', dict(date='2026-10-13', timezone='Asia/Seoul',
        input_case='SPAN', candidate='FINITE_FORK', source=str(SOURCE),
        source_receipt_sha256=SOURCE_RECEIPT_SHA256, recipe=operator.RECIPE,
        geometry_code_sha256=hashes, frame_bindings=bindings))
    input_hash = prior.array_hash(mesh.xyz)
    vertex_pairs = dict(X=pairs['mirror_x_vertex_pairs'], Y=pairs['mirror_y_vertex_pairs'])
    print('APPLY one fixed fairing then finite fork-fold sequence to whole G7', flush=True)
    out, metadata, state = operator.build(mesh, chart, vertex_pairs,
        coords['parent_phase'], coords['normalized_z'], coords['feature_support'], height)
    if (out.generation != 7 or out.xyz.shape != mesh.xyz.shape
            or not np.array_equal(out.faces, mesh.faces) or prior.array_hash(mesh.xyz) != input_hash):
        raise ValueError('Unchanged source arrays and actual G7 topology required.')
    state.update(mirror_x_face_pairs=pairs['mirror_x_face_pairs'],
        mirror_y_face_pairs=pairs['mirror_y_face_pairs'])
    print('VERIFY actual reflected control XYZ and oriented quads', flush=True)
    symmetry = loader.actual_symmetry(out, state)
    context = dict(input_case='SPAN', candidate='FINITE_FORK', source=str(SOURCE),
        source_generation=7, source_control_sha256=source['control_file_sha256'],
        source_generation_json_sha256=SOURCE_RECEIPT_SHA256, parent_stage=str(SOURCE),
        parent_control_sha256=source['control_file_sha256'],
        parent_generation_json_sha256=SOURCE_RECEIPT_SHA256,
        geometry_code_sha256=hashes, added_CC_passes=0, added_topology_events=0,
        added_normal_field_passes=1, cumulative_normal_field_passes=source['cumulative_normal_field_passes']+1,
        added_mandelbulb_evaluations=0, operator_metadata=metadata, frame_ancestry=ancestry,
        source_bindings=bindings, symmetry=symmetry, memory_guard_before_load=before_memory,
        design_scope='Single whole-column SPAN G7 development; fixed finite-length fork-fold relief after bounded fine-scale geometric fairing.',
        methodology_scope='Same closed topology and registered phase; actual source geometry is boundedly averaged in this update. Forks are surface relief, not topological branching.',
        validation_scope='Finite/closed-oriented/connectivity/no-orphan/native-area checks once at save, actual reflected control XYZ and oriented quad cycles, then matched actual renders.',
        intermediate_scope='Actual fairing intermediate = source XYZ + saved delta_fairing; no intermediate native mesh is claimed.',
        exclusions=['CENTRAL_SPINDLE development', 'G8', 'New inputs', 'Candidate matrix',
            'Full independent replay', 'Native triangle-set sorting', 'Self-intersection repair',
            'Fabrication suitability', 'Reference-exact implementation', 'Aesthetic certification'])
    del mesh, pairs, coords, vertex_pairs
    gc.collect()
    folder = root/'FINITE_FORK/SPAN/G07'
    print('SAVE final actual G7 and required existing mesh checks', flush=True)
    record = core.save(folder, out, chart, context, state)
    if digest(SOURCE/'generation.json') != SOURCE_RECEIPT_SHA256:
        raise ValueError('Preserved source receipt changed during run.')
    base.checked(SOURCE, source, (('control_quad.npz', 'control_file_sha256'),
        ('evidence.npz', 'evidence_file_sha256')))
    for rel, expected in hashes.items():
        if digest(REPO/rel) != expected:
            raise ValueError('Generation source bytes changed during execution: '+rel)
    if digest(Path(bindings['source_summary'])) != bindings['source_summary_sha256']:
        raise ValueError('Preserved source summary changed.')
    frame = Path(bindings['frame_folder'])
    for name, key in [('generation.json', 'frame_receipt_sha256'),
            ('control_quad.npz', 'frame_control_sha256'), ('evidence.npz', 'frame_evidence_sha256')]:
        if digest(frame/name) != bindings[key]:
            raise ValueError('Preserved registered-frame dependency changed.')
    write(root/'SUMMARY.json', dict(date='2026-10-13', timezone='Asia/Seoul',
        source=str(SOURCE), source_generation=7, source_control_sha256=source['control_file_sha256'],
        input_case='SPAN', candidate='FINITE_FORK', folder=str(folder), subdivision_generation=7,
        added_CC_passes=0, added_topology_events=0, added_normal_field_passes=1,
        cumulative_normal_field_passes=context['cumulative_normal_field_passes'],
        generation_json_sha256=digest(folder/'generation.json'), checks=record['checks'],
        symmetry=symmetry, operator_metadata=metadata, frame_ancestry=ancestry,
        geometry_code_sha256=hashes, elapsed_generation_seconds=time.perf_counter()-started,
        actual_generation_process_memory=process_memory(),
        visual_success='PENDING_MATCHED_ACTUAL_RENDER_REVIEW'))
    print('DONE one SPAN G7 finite fork-fold update; G8 and second input untouched', flush=True)


if __name__ == '__main__':
    main()
