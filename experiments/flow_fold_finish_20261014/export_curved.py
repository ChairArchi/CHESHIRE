"""Export the stored continuous-flow fold study without mesh changes."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import time

import numpy as np

HERE = Path(__file__).resolve().parent
HELPER = HERE.parent/'model_exports_20261014/export_latest.py'
spec = importlib.util.spec_from_file_location('cheshire_preserved_ply_helper', HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
digest, FACE = helper.digest, helper.FACE
SOURCE = Path('E:/CHESHIRE_DATA/experiments/flow_fold_finish_20261014/trial02/FLOW/geometry.npz')
RECEIPT = SOURCE.parents[1]/'RECEIPT.json'
OUTPUT = Path('E:/CHESHIRE_DATA/exports/20261014/COLUMN_FLOW_FOLDS_CURVED')
TARGET = np.array([-.8127592552124007, .42607142838364565, 6.369917540048999])
RADIUS = .28


def write_ply(path, xyz, faces, expected_sha):
    """Existing exact PLY recipe with a truthful generic study comment."""
    if len(xyz) > np.iinfo(np.int32).max or faces.min() < 0 or faces.max() >= len(xyz):
        raise ValueError('PLY signed int32 face indexing is invalid.')
    header = ('ply\nformat binary_little_endian 1.0\n'
        'comment CHESHIRE stored G7 continuous inherited-flow fine folds\n'
        'comment Source geometry SHA256 '+expected_sha+'\n'
        'comment Original coordinates and units unchanged\n'
        f'element vertex {len(xyz)}\nproperty double x\nproperty double y\nproperty double z\n'
        f'element face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n').encode('ascii')
    with open(path, 'xb') as stream:
        stream.write(header)
        for start in range(0, len(xyz), 262144):
            np.ascontiguousarray(xyz[start:start+262144], dtype='<f8').tofile(stream)
        for start in range(0, len(faces), 262144):
            block = faces[start:start+262144]
            packed = np.empty(len(block), FACE)
            packed['count'], packed['indices'] = 3, block
            packed.tofile(stream)
    expected_bytes = len(header)+len(xyz)*24+len(faces)*13
    if path.stat().st_size != expected_bytes:
        raise ValueError('PLY byte length differs.')
    with open(path, 'rb') as stream:
        if stream.read(len(header)) != header:
            raise ValueError('PLY header differs.')
        for start in range(0, len(xyz), 262144):
            source = xyz[start:start+262144]
            actual = np.fromfile(stream, dtype='<f8', count=source.size).reshape(source.shape)
            if not np.array_equal(actual, source):
                raise ValueError('PLY coordinate roundtrip differs.')
        for start in range(0, len(faces), 262144):
            source = faces[start:start+262144]
            actual = np.fromfile(stream, dtype=FACE, count=len(source))
            if not np.all(actual['count'] == 3) or not np.array_equal(actual['indices'], source):
                raise ValueError('PLY triangle roundtrip differs.')
        if stream.read(1):
            raise ValueError('Unexpected PLY trailing bytes.')
    return dict(path=str(path), vertices=len(xyz), triangles=len(faces), bytes=expected_bytes,
        sha256=digest(path), exact_coordinate_and_triangle_roundtrip=True,
        coordinates='binary float64; unchanged source axes/model units',
        faces='uchar3 + signed int32 indices')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', default=None, help='Optional actual repository commit hash.')
    args = parser.parse_args()
    started = time.perf_counter()
    if OUTPUT.exists():
        raise FileExistsError('Existing export directory is preserved.')
    receipt_sha = digest(RECEIPT)
    receipt = json.loads(RECEIPT.read_text(encoding='utf8'))
    if (receipt['kind'] != 'CONTINUOUS_PARENT_FLOW_FINE_FOLD_REPLACEMENT' or
            receipt['generation'] != 7 or receipt['new_G8']):
        raise ValueError('Actual continuous-flow G7 receipt required.')
    variant = receipt['variants']['FLOW']
    expected_sha = variant['geometry_sha256']
    if (len(expected_sha) != 64 or Path(variant['geometry']).resolve() != SOURCE.resolve() or
            digest(SOURCE) != expected_sha):
        raise ValueError('Actual stored FLOW source differs from frozen receipt binding.')
    code_sha, helper_sha = digest(__file__), digest(HELPER)
    OUTPUT.mkdir(parents=True)
    shutil.copyfile(__file__, OUTPUT/'SOURCE_SNAPSHOT_export_model.py')
    shutil.copyfile(HELPER, OUTPUT/'SOURCE_SNAPSHOT_preserved_export_helper.py')
    shutil.copyfile(RECEIPT, OUTPUT/'SOURCE_RECEIPT.json')
    with np.load(SOURCE, allow_pickle=False) as saved:
        xyz, faces = saved['xyz'], saved['faces']
    if xyz.shape != (14004226, 3) or faces.shape != (28008448, 3):
        raise ValueError('Frozen native counts differ.')
    print('EXPORT exact stored continuous-flow full native model', flush=True)
    full = write_ply(OUTPUT/'CHESHIRE_COLUMN_G7_FLOW_FOLDS_CURVED_FULL.ply', xyz, faces, expected_sha)
    chosen = []
    for start in range(0, len(faces), 131072):
        block = faces[start:start+131072]
        center = xyz[block].mean(axis=1)
        chosen.append(start+np.flatnonzero(np.sum((center-TARGET)**2, axis=1) <= RADIUS**2))
    face_ids = np.concatenate(chosen)
    if not len(face_ids):
        raise ValueError('Saved target detail crop is empty.')
    vertex_ids, inverse = np.unique(faces[face_ids].ravel(), return_inverse=True)
    detail = write_ply(OUTPUT/'CHESHIRE_COLUMN_G7_FLOW_FOLDS_CURVED_DETAIL.ply',
                       xyz[vertex_ids], inverse.reshape(-1, 3), expected_sha)
    detail.update(scope='Exact stored triangle subset; open cut boundary, no caps or new surface.',
        selection='Triangle centroids within radius of the same saved macro-camera target.',
        target=TARGET.tolist(), radius=RADIUS)
    ids_path = OUTPUT/'DETAIL_SOURCE_IDS.npz'
    np.savez_compressed(ids_path, source_vertex_ids=vertex_ids, source_face_ids=face_ids)
    if (digest(SOURCE) != expected_sha or digest(RECEIPT) != receipt_sha or
            digest(__file__) != code_sha or digest(HELPER) != helper_sha):
        raise ValueError('Frozen source or executed export code changed.')
    manifest = dict(date='2026-10-14', timezone='Asia/Seoul', source=str(SOURCE), source_sha256=expected_sha,
        source_receipt=str(RECEIPT), source_receipt_sha256=receipt_sha,
        export_code=str(Path(__file__).resolve()), export_code_sha256=code_sha,
        preserved_helper=str(HELPER), preserved_helper_sha256=helper_sha,
        checkpoint=args.checkpoint, classification='Stored continuous-flow study result; prior accepted model remains preserved.',
        full=full, detail=detail,
        detail_source_ids=dict(path=str(ids_path), sha256=digest(ids_path)),
        source_geometry_modified=False, simplification=False,
        units='Unchanged source model units; no scale conversion applied.',
        seconds=time.perf_counter()-started)
    (OUTPUT/'MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    (OUTPUT/'README.txt').write_text('CHESHIRE G7 continuous inherited-flow folds / 2026-10-14\n\n'
        'FULL: complete stored native model; no simplification.\n'
        'DETAIL: exact stored triangle subset for lightweight close inspection.\n'
        'DETAIL has an open cut boundary. Coordinates and model units are unchanged.\n'
        'PLY contains no materials or cameras. See MANIFEST.json for exact verification.\n', encoding='utf8')
    print(json.dumps(dict(full=full, detail=detail, seconds=manifest['seconds'])), flush=True)


if __name__ == '__main__':
    main()
