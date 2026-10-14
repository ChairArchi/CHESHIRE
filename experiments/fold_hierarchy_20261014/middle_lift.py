"""Extract the accepted MIDDLE contribution with the actual neutral CC stencil.

This is an ancestry extraction and reproduction check, not a candidate model.
The actual saved G7 quads supply G6 edge incidence without a new global sort.
The resulting operator is checked against both saved original/replay SURFACEs
before it is applied to the saved MIDDLE-only displacement vectors.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import shutil
import time

import numpy as np

HERE = Path(__file__).resolve().parent
PREPARE_SHA = '5e833d00b8639b70ab8f018fc25d97b88b93a3959a67d121b70a4614a62e0f29'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


if sha(HERE/'prepare.py') != PREPARE_SHA:
    raise ValueError('Frozen ancestry extraction code changed.')
spec = importlib.util.spec_from_file_location('hierarchy_frozen_prepare', HERE/'prepare.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
ah, read, write = prepare.ah, prepare.read, prepare.write


def actual_incidence(faces6, edges6, faces7, vertices6):
    """Recover exactly the existing CC child layout and its two-face edges."""
    nf, ne, nv = len(faces6), len(edges6), vertices6
    if faces6.shape != (nf, 4) or faces7.shape != (nf*4, 4):
        raise ValueError('Actual all-quad G6 and four-child G7 required.')
    child = faces7.reshape(nf, 4, 4)
    if not np.array_equal(child[:, :, 1], faces6):
        raise ValueError('Actual G7 old-corner ordering differs from G6.')
    if not np.all(child[:, :, 3] == (nv+ne+np.arange(nf))[:, None]):
        raise ValueError('Actual G7 completed face-center IDs differ.')
    following = child[:, :, 2]-nv
    if following.min() < 0 or following.max() >= ne:
        raise ValueError('Actual following edge IDs are out of bounds.')
    if not np.array_equal(child[:, :, 0]-nv, np.roll(following, 1, axis=1)):
        raise ValueError('Actual preceding/following edge layout differs.')
    for start in range(0, nf, 65536):
        q = faces6[start:start+65536]
        edge = edges6[following[start:start+65536]]
        b = np.roll(q, -1, axis=1)
        if not (np.array_equal(edge[:, :, 0], np.minimum(q, b)) and
                np.array_equal(edge[:, :, 1], np.maximum(q, b))):
            raise ValueError('Actual source edge endpoints do not match G7 child IDs.')
    incidence = np.bincount(following.ravel(), minlength=ne)
    if not np.all(incidence == 2):
        raise ValueError('Actual source edges require exactly two incident faces.')
    degree = np.bincount(edges6.ravel(), minlength=nv)
    face_degree = np.bincount(faces6.ravel(), minlength=nv)
    if degree.min() < 3 or not np.array_equal(degree, face_degree):
        raise ValueError('Actual closed quad edge/face vertex degree differs.')
    return following, degree, dict(
        actual_G6_faces_sha256=ah(faces6), actual_G6_input_edges_sha256=ah(edges6),
        actual_G7_faces_sha256=ah(faces7), actual_following_edge_ids_sha256=ah(following),
        old_corner_ids_exact=True, face_center_ids_exact=True,
        preceding_edge_ids_exact=True, every_edge_matches_actual_G6_endpoints=True,
        every_edge_has_two_face_incidences=True,
        source_vertex_edge_degree_equals_face_degree=True,
        G6_vertices=nv, G6_edges=ne, G6_quads=nf,
        G7_vertices=nv+ne+nf, G7_quads=4*nf)


def neutral_cc(value, faces, edges, following, degree):
    """Actual weights-zero CC linear stencil; no normals, scales or sorting."""
    nv, ne = len(value), len(edges)
    face = value[faces].mean(axis=1)
    edge_face_sum = np.column_stack([
        np.bincount(following.ravel(), weights=np.repeat(face[:, axis], 4), minlength=ne)
        for axis in range(3)])
    edge = (edge_face_sum+value[edges[:, 0]]+value[edges[:, 1]])/4
    del edge_face_sum
    fbar = np.column_stack([
        np.bincount(faces.ravel(), weights=np.repeat(face[:, axis], 4), minlength=nv)
        for axis in range(3)])/degree[:, None]
    midpoint = value[edges].mean(axis=1)
    rbar = np.column_stack([
        np.bincount(edges.ravel(), weights=np.repeat(midpoint[:, axis], 2), minlength=nv)
        for axis in range(3)])/degree[:, None]
    vertex = (fbar+2*rbar+(degree[:, None]-3)*value)/degree[:, None]
    return np.concatenate([vertex, edge, face])


def extract(label, bindings):
    middle, surface = prepare.PATHS[label+'_middle6'], prepare.PATHS[label+'_surface']
    middle_info = bindings[label+'_middle6']['metadata']
    surface_info = bindings[label+'_surface']['metadata']
    for path, expected in ((middle/'control_quad.npz', bindings[label+'_middle6']['control_sha256']),
                           (surface/'control_quad.npz', bindings[label+'_surface']['control_sha256'])):
        if sha(path) != expected:
            raise ValueError('Previously bound actual MIDDLE/SURFACE control changed.')
    op = surface_info['operator_metadata']
    if any(float(value) != 0 for value in op.get('weights', {}).values()):
        raise ValueError('Actual SURFACE is not a weights-zero neutral operator.')
    with np.load(middle/'control_quad.npz', allow_pickle=False) as data:
        x6, q6 = data['xyz'], data['faces']
    with np.load(surface/'control_quad.npz', allow_pickle=False) as data:
        x7, q7 = data['xyz'], data['faces']
    if ah(x6) != middle_info['checks']['control_xyz_sha256'] or ah(x7) != surface_info['checks']['control_xyz_sha256']:
        raise ValueError('Actual saved MIDDLE/SURFACE XYZ hash differs.')
    with np.load(surface/'evidence.npz', allow_pickle=False) as data:
        edges = data['input_edges']
    following, degree, proof = actual_incidence(q6, edges, q7, len(x6))
    print('REPRODUCE actual saved neutral CC SURFACE', label, flush=True)
    replay = neutral_cc(x6, q6, edges, following, degree)
    error = float(np.max(np.abs(replay-x7)))
    if error > 1e-13:
        raise ValueError('Actual saved SURFACE neutral CC reproduction exceeds tolerance: '+str(error))
    del replay, x7, q7
    gc.collect()
    with np.load(middle/'evidence.npz', allow_pickle=False) as data:
        delta6 = data['displacement_vector']
    incoming = Path(middle_info['source'])/'control_quad.npz'
    incoming_sha = sha(incoming)
    if incoming_sha != middle_info['source_control_sha256']:
        raise ValueError('Actual incoming DEPTH08 parent changed.')
    with np.load(incoming, allow_pickle=False) as data:
        incoming_xyz = data['xyz']
    if not np.array_equal(incoming_xyz+delta6, x6):
        raise ValueError('Actual saved MIDDLE displacement does not exactly reconstruct its output.')
    del incoming_xyz, x6
    print('LIFT actual saved MIDDLE-only displacement', label, flush=True)
    delta7 = neutral_cc(delta6, q6, edges, following, degree)
    proof.update(checked_saved_SURFACE_max_coordinate_error=error,
        coordinate_reproduction_tolerance=1e-13,
        actual_MIDDLE_delta_reconstructs_its_output_array_exact=True,
        actual_incoming_G6_control=dict(path=str(incoming), sha256=incoming_sha),
        actual_G6_delta_sha256=ah(delta6), actual_lifted_G7_delta_sha256=ah(delta7),
        actual_G6_evidence_sha256=sha(middle/'evidence.npz'),
        actual_G7_evidence_sha256=sha(surface/'evidence.npz'))
    return delta7, proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=prepare.DEFAULT_ROOT)
    root = parser.parse_args().root.resolve()
    if (root/'MIDDLE_COMPONENT.npz').exists() or (root/'MIDDLE_PREPARATION.json').exists():
        raise FileExistsError('Existing MIDDLE extraction remains immutable.')
    started = time.perf_counter()
    info_path = root/'PREPARATION.json'
    info = read(info_path)
    if sha(prepare.SOURCE) != prepare.SOURCE_SHA:
        raise ValueError('Accepted actual G7 source changed.')
    if sha(root/'COMPONENTS.npz') != info['output']['sha256']:
        raise ValueError('Existing component preparation changed.')
    snapshot = root/'source_snapshot/middle_lift.py'
    shutil.copyfile(__file__, snapshot)
    original, original_proof = extract('original', info['source_binding'])
    replay, replay_proof = extract('replay', info['source_binding'])
    if original_proof['actual_G6_faces_sha256'] != replay_proof['actual_G6_faces_sha256'] or original_proof['actual_G7_faces_sha256'] != replay_proof['actual_G7_faces_sha256']:
        raise ValueError('Original/replay actual ordered G6/G7 faces differ.')
    if sha(prepare.MASK) != prepare.MASK_SHA:
        raise ValueError('Accepted source end-mask changed.')
    with np.load(prepare.MASK, allow_pickle=False) as data:
        mask = data['full_mask']
    delta = original+mask[:, None]*(replay-original)
    if delta.shape != (7002114, 3) or not np.isfinite(delta).all():
        raise ValueError('Finite actual effective MIDDLE delta required.')
    result = root/'MIDDLE_COMPONENT.npz'
    np.savez_compressed(result, delta_middle=delta)
    write(root/'MIDDLE_PREPARATION.json', dict(date='2026-10-14', timezone='Asia/Seoul',
        schema='CHESHIRE_ACTUAL_NEUTRAL_CC_MIDDLE_DELTA_EXTRACTION_V1',
        candidate_generated=False, accepted_source=info['accepted_source'],
        prior_preparation=dict(path=str(info_path), sha256=sha(info_path)),
        actual_proofs=dict(original=original_proof, replay=replay_proof),
        stencil=dict(face='mean(delta at four actual G6 quad corners)',
            edge='(delta_a+delta_b+sum(two actual incident completed face deltas))/4',
            vertex='(Fbar+2*Rbar+(degree-3)*delta_vertex)/degree',
            actual_ID_order='Actual saved G7 old vertices, original input_edges, input_faces. Actual G7 child IDs validate all associations and edge incidence.',
            no_normals_or_global_topology_sort=True,
            numerical_scope='Same mathematical weights-zero reference operator; summation order may differ by inherited floating-point roundoff, measured on actual saved surfaces before delta extraction.'),
        effective_formula='delta_middle=neutralCC(deltaM6_original)+saved_end_mask*(neutralCC(deltaM6_replay)-neutralCC(deltaM6_original))',
        mask=dict(path=str(prepare.MASK), sha256=prepare.MASK_SHA),
        output=dict(path=str(result), sha256=sha(result), bytes=result.stat().st_size,
            array='delta_middle', shape=list(delta.shape), dtype=str(delta.dtype),
            array_sha256=ah(delta), maximum_norm=float(np.linalg.norm(delta, axis=1).max())),
        executed_source_sha256=dict(middle_lift=sha(snapshot), frozen_prepare=PREPARE_SHA),
        elapsed_seconds=time.perf_counter()-started,
        scope='Only accepted MIDDLE normal-field contribution transported by actual verified neutral G6->G7 operator. No candidate geometry, global G8, new G1-G7 growth rule, or source-code/data changes.'))
    if sha(prepare.SOURCE) != prepare.SOURCE_SHA:
        raise ValueError('Accepted source changed during read-only extraction.')
    print(json.dumps(dict(prepared=str(result), bytes=result.stat().st_size,
        original_surface_max_error=original_proof['checked_saved_SURFACE_max_coordinate_error'],
        replay_surface_max_error=replay_proof['checked_saved_SURFACE_max_coordinate_error']),indent=2), flush=True)


if __name__ == '__main__':
    main()
