"""Read-only source interface check for saved attached-leaf construction.

Confirm that the original selected disk interiors were not referenced by
unselected original faces. This is separate from the generator's graph check.
No geometry is generated or changed; write only the verification receipt.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

import numpy as np


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = root/'INTERFACE_VERIFICATION.json'
    if output.exists():
        raise FileExistsError('Earlier interface receipt preserved.')
    summary = json.loads((root/'SUMMARY.json').read_text(encoding='utf-8'))
    folder = Path(summary['folder'])
    record = json.loads((folder/'generation.json').read_text(encoding='utf-8'))
    source = Path(record['source'])
    if (record['candidate'] != 'ATTACHED_LEAF' or not record['checks']['passed']
            or not record['symmetry']['passed']
            or digest(folder/'generation.json') != summary['generation_json_sha256']
            or digest(folder/'evidence.npz') != record['evidence_file_sha256']
            or digest(source/'control_quad.npz') != record['source_control_sha256']
            or digest(source/'generation.json') != record['source_generation_json_sha256']):
        raise ValueError('Actual source/output receipts differ.')
    source_info = json.loads((source/'generation.json').read_text(encoding='utf-8'))
    if digest(source/'evidence.npz') != source_info['evidence_file_sha256']:
        raise ValueError('Actual source reflection evidence differs.')
    with np.load(source/'control_quad.npz', allow_pickle=False) as data:
        faces = data['faces']
        vertex_count = len(data['classes'])
    with np.load(source/'evidence.npz', allow_pickle=False) as data:
        px, py = data['mirror_x_vertex_pairs'], data['mirror_y_vertex_pairs']
    with np.load(folder/'evidence.npz', allow_pickle=False) as data:
        selected_v = data['selected_source_vertex_ids']
        selected_f = data['selected_source_face_ids']
        keys = sorted(key for key in data.files if key.endswith('_source_boundary_vertices'))
        boundary = []
        for key in keys:
            ids = data[key]
            boundary.extend([ids, px[ids], py[ids], px[py[ids]]])
    boundary = np.unique(np.concatenate(boundary))
    interior = np.setdiff1d(selected_v, boundary)
    is_interior = np.zeros(vertex_count, bool)
    is_interior[interior] = True
    is_selected = np.zeros(len(faces), bool)
    is_selected[selected_f] = True
    violation_count, examples = 0, []
    for start in range(0, len(faces), 131072):
        stop = min(start+131072, len(faces))
        bad = np.any(is_interior[faces[start:stop]], axis=1) & ~is_selected[start:stop]
        ids = np.flatnonzero(bad)+start
        violation_count += len(ids)
        examples.extend(ids[:max(0, 12-len(examples))].tolist())
    proof = dict(date='2026-10-13', timezone='Asia/Seoul', passed=violation_count == 0,
        source=str(source), source_control_sha256=record['source_control_sha256'],
        source_evidence_sha256=source_info['evidence_file_sha256'],
        output_generation_sha256=summary['generation_json_sha256'],
        output_evidence_sha256=record['evidence_file_sha256'],
        canonical_patch_count=len(keys), reflected_patch_count=4*len(keys),
        selected_source_vertices=len(selected_v), selected_source_faces=len(selected_f),
        shared_boundary_vertices=len(boundary), selected_interior_vertices=len(interior),
        all_original_faces_scanned=len(faces), outside_face_interior_reference_count=violation_count,
        violating_face_examples=examples, code_sha256=digest(__file__),
        scope='Exact source-ID incidence check of all original faces; no new geometry, independent replay, or self-intersection certification.')
    output.write_text(json.dumps(proof, indent=2)+'\n', encoding='utf-8')
    target = root/'source_snapshot_validation'/Path(__file__).name
    target.parent.mkdir(exist_ok=True)
    shutil.copyfile(__file__, target)
    if not proof['passed']:
        raise ValueError('Selected interior was referenced outside the replaced disks.')
    print('SOURCE_INTERFACE_PASS',len(keys),'canonical disks;',len(interior),
        'interiors;',len(faces),'original faces scanned',flush=True)


if __name__ == '__main__':
    main()
