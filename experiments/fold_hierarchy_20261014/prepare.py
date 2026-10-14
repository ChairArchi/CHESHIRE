"""Extract accepted G7 ancestry components; no candidate geometry is generated.

The accepted REVISED controls are an original/replay end-mask combination.
The same combination is applied to actual SURFACE/LINKED/FINAL differences.
Unwrapped MIDDLE phase is transported as an association coordinate through the
actual G6->G7 old-vertex/edge/face IDs, never used as a geometry stencil.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import shutil
import time
import zipfile

import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/fold_hierarchy_20261014/trial01')
E = Path('E:/CHESHIRE_DATA/experiments')
END = E/'end_rule_revision_20261014/trial01'
SOURCE = END/'REVISED/control_quad.npz'
SOURCE_SHA = '0915ac8f56509768c6329a7d848793c6936b903d4d9316e01b1076a76aba8e27'
END_RECEIPT_SHA = 'b77a701e01a53976e08ad07b963fb022931bf8e4efcc08d21485a55fddd31569'
MASK = E/'volume_junction_target_20261014/trial01/selection.npz'
MASK_SHA = '7bbfb7cdb50b3fad320451dc096b23f8f662c7a09a425324949cba39396584ab'
PATHS = {
    'original_surface': E/'whole_column_detail_20261013/trial01/SURFACE/MIDDLE/SPAN/G07',
    'original_linked': E/'parent_linked_folds_20261013/trial03/PARENT_LINKED/SPAN/G07',
    'original_final': E/'medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07',
    'original_middle6': E/'whole_column_detail_20261013/trial01/MIDDLE/SPAN/G06',
    'replay_surface': END/'replay/states/G07_SURFACE',
    'replay_linked': END/'replay/states/G07_LINKED_FINISHED',
    'replay_final': END/'replay/states/G07_FINAL',
    'replay_middle6': END/'replay/states/G06_MIDDLE',
}
ASSOCIATIONS = ('faces', 'chart', 'classes', 'rest', 'anchors', 'generation', 'surface')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def ah(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
        allow_nan=False)+'\n', encoding='utf8')


def member_hashes(path, keys):
    result = {}
    with zipfile.ZipFile(path) as archive:
        for key in keys:
            h = hashlib.sha256()
            with archive.open(key+'.npy') as stream:
                for block in iter(lambda: stream.read(8*1024**2), b''):
                    h.update(block)
            result[key] = h.hexdigest()
    return result


def load_xyz(label, bindings):
    path = PATHS[label]/'control_quad.npz'
    with np.load(path, allow_pickle=False) as data:
        xyz = data['xyz']
    expected = bindings[label]['metadata']['checks']['control_xyz_sha256']
    if xyz.shape != (7002114, 3) or not np.isfinite(xyz).all() or ah(xyz) != expected:
        raise ValueError('Actual bound G7 XYZ differs: '+label)
    return xyz


def lift_coordinate(value, edges, faces):
    """Actual frozen V/E/F association transport; not CC geometry averaging."""
    return np.concatenate([value, value[edges].mean(axis=1), value[faces].mean(axis=1)])


def frame(label, bindings):
    middle_label, surface_label = label+'_middle6', label+'_surface'
    middle, surface = PATHS[middle_label], PATHS[surface_label]
    info = bindings[middle_label]['metadata']
    with np.load(middle/'evidence.npz', allow_pickle=False) as state:
        phase6, support6 = state['directional_phase'], state['feature_support']
        phase_sha = ah(phase6)
        saved_z6 = state['frame_normalized_z'] if 'frame_normalized_z' in state.files else None
    with np.load(middle/'control_quad.npz', allow_pickle=False) as control:
        faces6 = control['faces']
    with np.load(surface/'evidence.npz', allow_pickle=False) as state:
        edges7 = state['input_edges']
        if len(edges7)+len(faces6)+len(phase6) != 7002114:
            raise ValueError('Actual G6->G7 V/E/F count differs.')
        lifted = lift_coordinate(phase6, edges7, faces6)
        support = lift_coordinate(support6, edges7, faces6)
        observed_wrapped = state['parent_phase'] if 'parent_phase' in state.files else None
    # MIDDLE's normalized height refers to its incoming DEPTH_08, not to the
    # displaced MIDDLE geometry. Reuse the stored replay frame when available;
    # otherwise bind the actual original incoming control and metadata bounds.
    input_binding = None
    if saved_z6 is None:
        incoming = Path(info['source'])/'control_quad.npz'
        incoming_sha = sha(incoming)
        if incoming_sha != info['source_control_sha256']:
            raise ValueError('Actual MIDDLE incoming control changed.')
        with np.load(incoming, allow_pickle=False) as control:
            incoming_xyz = control['xyz']
        operator = info['operator_metadata']
        if ah(incoming_xyz) != operator['input_xyz_sha256']:
            raise ValueError('Actual original MIDDLE incoming XYZ differs.')
        lo, hi = operator['actual_input_z_bounds']
        saved_z6 = (incoming_xyz[:, 2]-lo)/(hi-lo)
        input_binding = dict(path=str(incoming), sha256=incoming_sha)
        del incoming_xyz
    normalized_z = lift_coordinate(saved_z6, edges7, faces6)
    # Frozen G7 stores atan2(mean(sin),mean(cos)), not wrap(mean(phi)).
    # Confirm that actual transport separately, preserving our unwrapped lift.
    wrapped = np.arctan2(lift_coordinate(np.sin(phase6), edges7, faces6),
                         lift_coordinate(np.cos(phase6), edges7, faces6))
    wrapped_error = None
    if observed_wrapped is not None:
        wrapped_error = float(np.max(np.abs(wrapped-observed_wrapped)))
        if wrapped_error > 1e-12:
            raise ValueError('Actual saved wrapped phase ancestry differs.')
    proof = dict(source_phase_sha256=phase_sha, lifted_phase_sha256=ah(lifted),
        actual_G6_faces_sha256=ah(faces6), actual_G7_input_edges_sha256=ah(edges7),
        wrapped_saved_phase_max_error=wrapped_error, incoming_z_control=input_binding,
        unwrapped_phase_range=[float(lifted.min()), float(lifted.max())],
        transport='Concatenate actual old vertex values, input-edge means, input-face means. This scalar association is not a geometry refinement.',
        wrapped_scope='Existing wrapped phase is separately reproduced by sin/cos transport. parent_phase_unwrapped intentionally retains cycle identity.')
    return lifted, normalized_z, support, proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    root = parser.parse_args().root.resolve()
    if (root/'COMPONENTS.npz').exists() or (root/'PREPARATION.json').exists():
        raise FileExistsError('Existing preparation remains immutable.')
    started = time.perf_counter()
    if sha(SOURCE) != SOURCE_SHA or sha(END/'RECEIPT.json') != END_RECEIPT_SHA or sha(MASK) != MASK_SHA:
        raise ValueError('Accepted source, exact end receipt or mask changed.')
    root.mkdir(parents=True, exist_ok=True)
    snapshot = root/'source_snapshot/prepare.py'
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(__file__, snapshot)
    bindings = {}
    with np.load(SOURCE, allow_pickle=False) as accepted:
        actual_source = accepted['xyz']
    accepted_associations = member_hashes(SOURCE, ASSOCIATIONS)
    for label, folder in PATHS.items():
        print('BIND actual saved ancestry', label, flush=True)
        meta = read(folder/'generation.json')
        path = folder/'control_quad.npz'
        digest = sha(path)
        if digest != meta['control_file_sha256'] or not meta['checks']['passed']:
            raise ValueError('Actual ancestor control binding failed: '+label)
        association = member_hashes(path, ASSOCIATIONS)
        if not label.endswith('middle6') and association != accepted_associations:
            raise ValueError('Actual unchanged G7 association differs: '+label)
        bindings[label] = dict(folder=str(folder), control_sha256=digest,
            generation_json_sha256=sha(folder/'generation.json'), metadata=meta,
            association_npy_sha256=association)
    with np.load(MASK, allow_pickle=False) as mask_data:
        mask = mask_data['full_mask']
    if mask.shape != (len(actual_source),) or mask.min() < 0 or mask.max() > 1:
        raise ValueError('Accepted actual source-bound end mask differs.')
    print('EXTRACT effective existing SURFACE / LINKED / WIDE components', flush=True)
    osurf, rsurf = load_xyz('original_surface', bindings), load_xyz('replay_surface', bindings)
    base = osurf+mask[:, None]*(rsurf-osurf)
    olink, rlink = load_xyz('original_linked', bindings), load_xyz('replay_linked', bindings)
    dl_original, dl_replay = olink-osurf, rlink-rsurf
    linked = dl_original+mask[:, None]*(dl_replay-dl_original)
    del osurf, rsurf, dl_original, dl_replay
    ofinal, rfinal = load_xyz('original_final', bindings), load_xyz('replay_final', bindings)
    dw_original, dw_replay = ofinal-olink, rfinal-rlink
    wide = dw_original+mask[:, None]*(dw_replay-dw_original)
    exact_splice = ofinal+mask[:, None]*(rfinal-ofinal)
    if not np.array_equal(exact_splice, actual_source):
        raise ValueError('Accepted REVISED is not the exact bound original/replay splice.')
    reconstruction_error = float(np.max(np.abs(base+linked+wide-actual_source)))
    if reconstruction_error > 1e-12:
        raise ValueError('Extracted component reconstruction exceeds roundoff.')
    del olink, rlink, ofinal, rfinal, dw_original, dw_replay, exact_splice
    gc.collect()
    print('TRANSPORT actual unwrapped MIDDLE phase and material frame', flush=True)
    op, oz, of, orig_proof = frame('original', bindings)
    rp, rz, rf, replay_proof = frame('replay', bindings)
    phase = op+mask*(rp-op)
    normalized_z = oz+mask*(rz-oz)
    support = of+mask*(rf-of)
    del op, oz, of, rp, rz, rf
    gc.collect()
    arrays = dict(base_xyz=base, delta_linked=linked, delta_wide=wide,
        parent_phase_unwrapped=phase, normalized_z=normalized_z,
        feature_support=support, end_mask=mask)
    result = root/'COMPONENTS.npz'
    print('SAVE association-bound components only; no new candidate', flush=True)
    np.savez_compressed(result, **arrays)
    write(root/'PREPARATION.json', dict(date='2026-10-14', timezone='Asia/Seoul',
        schema='CHESHIRE_ACCEPTED_G7_COMPONENT_EXTRACTION_V1', candidate_generated=False,
        accepted_source=dict(path=str(SOURCE), sha256=SOURCE_SHA, xyz_sha256=ah(actual_source),
            association_npy_sha256=accepted_associations),
        original_replay_mask=dict(path=str(MASK), sha256=MASK_SHA,
            selected_controls=int(np.count_nonzero(mask))),
        source_binding=bindings, frame_proof=dict(original=orig_proof, replay=replay_proof),
        extraction=dict(base='Borig+m*(Breplay-Borig)',
            linked='(LINKED-SURFACE)orig+m*((LINKED-SURFACE)replay-(LINKED-SURFACE)orig)',
            wide='(FINAL-LINKED)orig+m*((FINAL-LINKED)replay-(FINAL-LINKED)orig)',
            exact_original_replay_splice_matches_accepted_source=True,
            base_plus_linked_plus_wide_max_coordinate_error=reconstruction_error,
            decomposition_scope='Effective frozen accepted late-stage differences, not a newly regenerated dependency chain. WIDE retains its combined MEDIUM/SMALL finish.',
            hierarchy_limit='MIDDLE SURFACE remains unchanged. Reweighting these late components alone cannot certify a rewritten G1-G7 growth hierarchy or remove the existing uniform 20*theta MIDDLE repetition.'),
        output=dict(path=str(result), sha256=sha(result), bytes=result.stat().st_size,
            arrays={key:dict(shape=list(value.shape), dtype=str(value.dtype),
                sha256=ah(value)) for key,value in arrays.items()}),
        executed_prepare_sha256=sha(snapshot), elapsed_seconds=time.perf_counter()-started))
    if sha(SOURCE) != SOURCE_SHA:
        raise ValueError('Accepted source changed during read-only preparation.')
    print(json.dumps(dict(prepared=str(result), bytes=result.stat().st_size,
        reconstruction_max_coordinate_error=reconstruction_error), indent=2), flush=True)


if __name__ == '__main__':
    main()
