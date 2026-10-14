"""Prepare display-only fans of two actual preserved intermediate controls.

This does not replay any operator, create a candidate, displace a stored
control vertex, or claim that an original intermediate native was stored.
Each stored quad is displayed as four triangles meeting its arithmetic mean.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path('E:/CHESHIRE_DATA/experiments/parent_continuity_20261014/audit01')
SOURCE = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states')
CONTROLS = {
    'G06_MIDDLE': '38998220e63e9b9bd98f3d63870db444c681b9531d761581083c554021b8528d',
    'G07_SURFACE': '89653a94af3b2de1d875a3206a15a127f4418ef957cd011d4bca05c44fa21921',
}
PRESERVED = HERE.parent/'ordered_primary_folds_20261014/render.py'
PRESERVED_SHA = 'a5973a77346ab068b24f6dd659e4dc6804337a649240702ac4a2a3a167ccda06'
spec = importlib.util.spec_from_file_location('continuity_preserved_baseline', PRESERVED)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
digest, read_json, write = previous.digest, previous.read_json, previous.write


def ah(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def code_hashes():
    if digest(PRESERVED) != PRESERVED_SHA:
        raise ValueError('Preserved actual comparison adapter changed.')
    return dict(prepare=digest(__file__), preserved_renderer_sha256=PRESERVED_SHA,
                preserved_renderer_code=previous.code_hashes())


def snapshot(root):
    source = Path(__file__).resolve()
    target = root/'source_snapshot_prepare/experiments'/HERE.name/source.name
    if target.exists():
        raise FileExistsError('Earlier actual preparation snapshot preserved.')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    record = dict(source=str(source), snapshot=str(target), sha256=digest(source))
    previous.verify_snapshot(record)
    return record


def prepare_state(root, name, checksum):
    source = SOURCE/name/'control_quad.npz'
    metadata_path = SOURCE/name/'generation.json'
    if digest(source) != checksum:
        raise ValueError('Actual preserved control changed: '+name)
    metadata_sha = digest(metadata_path)
    metadata = read_json(metadata_path)
    if (metadata['stage_id'] != name or metadata['checkpoint_kind'] != 'CONTROL_AND_EVIDENCE_ONLY' or
            metadata['native_surface'] != 'NOT_STORED_INTERMEDIATE'):
        raise ValueError('Original intermediate storage status differs: '+name)
    with np.load(source, allow_pickle=False) as saved:
        xyz, quads = saved['xyz'], saved['faces']
        generation = int(saved['generation'])
    nv, nq = len(xyz), len(quads)
    if (xyz.dtype != np.float64 or xyz.shape != (nv, 3) or quads.shape != (nq, 4) or
            quads.dtype.kind not in 'iu' or quads.min() < 0 or quads.max() >= nv or
            not np.isfinite(xyz).all() or generation != metadata['subdivision_generation'] or
            nv != metadata['control_vertices'] or nq != metadata['control_quads']):
        raise ValueError('Actual preserved control arrays/counts differ: '+name)
    source_arrays = dict(xyz_sha256=ah(xyz), quads_sha256=ah(quads))
    if (source_arrays['xyz_sha256'] != metadata['checks']['control_xyz_sha256'] or
            source_arrays['quads_sha256'] != metadata['checks']['control_faces_sha256']):
        raise ValueError('Actual control arrays differ from preserved generation metadata.')
    output = root/name/'display_geometry.npz'
    if output.exists():
        raise FileExistsError('Earlier actual display derivative preserved.')
    native_xyz = np.empty((nv+nq, 3), dtype=np.float64)
    native_xyz[:nv] = xyz
    native_faces = np.empty((4*nq, 3), dtype=np.int64)
    for start in range(0, nq, 131072):
        stop = min(start+131072, nq)
        block = quads[start:stop]
        native_xyz[nv+start:nv+stop] = xyz[block].mean(axis=1)
        fans = native_faces[4*start:4*stop].reshape(-1, 4, 3)
        fans[:, :, 0] = block
        fans[:, :, 1] = np.roll(block, -1, axis=1)
        fans[:, :, 2] = (nv+np.arange(start, stop, dtype=np.int64))[:, None]
    if not np.array_equal(native_xyz[:nv], xyz):
        raise ValueError('Stored control coordinates were changed by display preparation.')
    arrays = dict(xyz_sha256=ah(native_xyz), faces_sha256=ah(native_faces))
    output.parent.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output, xyz=native_xyz, faces=native_faces)
    checksum_display = digest(output)
    with np.load(output, allow_pickle=False) as saved:
        loaded_xyz, loaded_faces = saved['xyz'], saved['faces']
    if (ah(loaded_xyz) != arrays['xyz_sha256'] or ah(loaded_faces) != arrays['faces_sha256'] or
            not np.array_equal(loaded_xyz[:nv], xyz)):
        raise ValueError('Complete saved display-array roundtrip differs.')
    if digest(source) != checksum or digest(metadata_path) != metadata_sha:
        raise ValueError('Original preserved source changed during display derivation.')
    return dict(state=name, generation=generation,
        original_control=dict(path=str(source), sha256=checksum,
            generation_json=str(metadata_path), generation_json_sha256=metadata_sha,
            control_vertices=nv, control_quads=nq, arrays=source_arrays,
            checkpoint_kind=metadata['checkpoint_kind'],
            native_surface=metadata['native_surface']),
        display_geometry=dict(geometry=str(output), geometry_sha256=checksum_display,
            **arrays, vertices=nv+nq, triangles=4*nq),
        display_derivation=dict(method='ARITHMETIC_QUAD_CENTRE_FAN_ONLY',
            equation='display_xyz=[stored_xyz, mean(stored_xyz[stored_quad],axis=1)]; each quad q gets triangles (q[i],q[(i+1)%4],nv+quad_id)',
            stored_vertices_unchanged_exactly=True,
            saved_source_prefix_sha256=ah(loaded_xyz[:nv]),
            added_display_centres=nq, subdivision_operators=0, displacement_operators=0,
            smoothing_operators=0, source_control_connectivity_unchanged=True,
            complete_saved_array_roundtrip=True,
            scope='Display-only tessellation of the exact stored control cage. Original intermediate native was NOT_STORED_INTERMEDIATE; this is not a historical native export or a new design candidate.',
            nonplanar_quad_scope='Each stored nonplanar quad is represented by the declared arithmetic-centre triangle fan; no stored control vertex is repositioned.'),
        preserved_stage_metadata=dict(source_generation=metadata['source_generation'],
            source_control_sha256=metadata['source_control_sha256'],
            added_CC_passes=metadata['added_CC_passes'],
            operator=metadata['operator_metadata'].get('implementation', metadata['operator_metadata'].get('stage'))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    if (root/'AUDIT_RECEIPT.json').exists():
        raise FileExistsError('Earlier completed audit preserved.')
    root.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    hashes = code_hashes()
    binding = previous.source_binding()
    source_snapshot = snapshot(root)
    states = {}
    for name, checksum in CONTROLS.items():
        print('DISPLAY ONLY '+name+': preserved controls -> arithmetic quad-centre fans', flush=True)
        states[name] = prepare_state(root, name, checksum)
    if states['G07_SURFACE']['preserved_stage_metadata']['source_control_sha256'] != CONTROLS['G06_MIDDLE']:
        raise ValueError('Actual G6 -> G7 preserved parent relationship differs.')
    if code_hashes() != hashes or previous.source_binding() != binding:
        raise ValueError('Actual source, baseline or preparation code changed.')
    previous.verify_snapshot(source_snapshot)
    result = dict(kind='PRESERVED_PARENT_CONTINUITY_DISPLAY_AUDIT', date='2026-10-14',
        design_candidates_generated=0, source_controls_modified=False,
        source_intermediate_natives='NOT_STORED_INTERMEDIATE',
        source_binding=binding, states=states, code_sha256=hashes,
        source_snapshot=source_snapshot, seconds=time.perf_counter()-started,
        comparison_scope='Two preserved controls only, G06_MIDDLE and its actual neutral-CC child G07_SURFACE. Display fans preserve every stored vertex; no modeling operator is replayed. Compare with latest NESTED02 using its actual close/body cameras and all-flat conditions.')
    write(root/'AUDIT_RECEIPT.json', result)
    print(json.dumps(dict(receipt=str(root/'AUDIT_RECEIPT.json'), seconds=result['seconds'],
                         display_geometries={k:v['display_geometry'] for k,v in states.items()})), flush=True)


if __name__ == '__main__':
    main()
