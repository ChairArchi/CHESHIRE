"""Export the selected actual ordered-primary native mesh without changes.

The source geometry and arrays are discovered from the actual selected
generation receipt; this module does not export anything when imported.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import time

import numpy as np

HERE = Path(__file__).resolve().parent
PRESERVED = HERE.parent/'parent_nested_folds_20261014/export_model.py'
PRESERVED_SHA = '289c0318dccb01d73242284baf835ef0e5e6abd82e14f082d777cfb72fe0479a'
spec = importlib.util.spec_from_file_location('ordered_preserved_ply_export', PRESERVED)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
digest, ah, write_ply = previous.digest, previous.ah, previous.write_ply
ROOT = Path('E:/CHESHIRE_DATA/experiments/ordered_primary_folds_20261014/trial01')
OUTPUT = Path('E:/CHESHIRE_DATA/exports/20261014/COLUMN_ORDERED_PRIMARY')
BASE = Path('E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial02/NESTED/geometry.npz')
BASE_SHA = 'cde95d13f64d86739ac25e134e67024533d6be4fafec7a5d4c7a46896b65403e'
FACES_SHA = '67109d7c7378b6cdfe82a713c74a860c98cdd53adcdce311f8612b3e6565a9ee'
TARGET, RADIUS = previous.TARGET, previous.RADIUS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--checkpoint', default=None)
    args = parser.parse_args()
    started = time.perf_counter()
    root, output = args.root.resolve(), args.output.resolve()
    if output.exists():
        raise FileExistsError('Existing export directory is preserved.')
    dependencies = ((PRESERVED, PRESERVED_SHA),
                    (previous.PRESERVED, previous.PRESERVED_SHA),
                    (previous.previous.HELPER, previous.previous.HELPER_SHA),
                    (previous.previous.TEMPLATE, previous.previous.TEMPLATE_SHA))
    for path, checksum in dependencies:
        if digest(path) != checksum:
            raise ValueError('Preserved exact export dependency changed: '+str(path))
    receipt_path = root/'RECEIPT.json'
    receipt_sha = digest(receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding='utf8'))
    if (Path(receipt.get('comparison_source_native_path', '')).resolve() != BASE.resolve() or
            receipt.get('comparison_source_native_geometry_sha256') != BASE_SHA):
        raise ValueError('Selected ordered-primary trial must bind to latest NESTED.')
    if set(receipt['variants']) != {'ORDERED'}:
        raise ValueError('Exactly the selected ORDERED variant is exported.')
    variant = receipt['variants']['ORDERED']
    source = Path(variant['geometry']).resolve()
    if source != root/'ORDERED/geometry.npz':
        raise ValueError('Actual receipt geometry must belong to the selected trial.')
    expected = variant['geometry_sha256']
    if (digest(source) != expected or variant['faces_sha256'] != FACES_SHA or
            variant['vertices'] != 14004226 or variant['triangles'] != 28008448):
        raise ValueError('Actual receipt native binding/counts differ.')
    checked_sources = {}
    for name, checksum in receipt.get('sources', {}).items():
        if digest(name) != checksum:
            raise ValueError('Actual generation input changed: '+name)
        checked_sources[name] = checksum
    checked_snapshots = {}
    for name, record in receipt['source_snapshots'].items():
        if any(digest(record[key]) != record['sha256'] for key in ('source', 'snapshot')):
            raise ValueError('Actual executed generation source/snapshot differs: '+name)
        checked_snapshots[name] = record
    code_sha = digest(__file__)
    output.mkdir(parents=True)
    shutil.copyfile(__file__, output/'SOURCE_SNAPSHOT_export_model.py')
    for index, (path, _) in enumerate(dependencies):
        shutil.copyfile(path, output/f'SOURCE_SNAPSHOT_preserved_{index}_{path.name}')
    shutil.copyfile(receipt_path, output/'SOURCE_GENERATION_RECEIPT.json')
    with np.load(source, allow_pickle=False) as saved:
        xyz, faces = saved['xyz'], saved['faces']
    if (xyz.shape != (14004226, 3) or faces.shape != (28008448, 3) or
            xyz.dtype != np.dtype('float64') or not np.isfinite(xyz).all() or
            ah(xyz) != variant['xyz_sha256'] or ah(faces) != FACES_SHA):
        raise ValueError('Actual complete native arrays differ from the receipt.')
    print('EXPORT exact ordered-primary full native G7 model', flush=True)
    full = write_ply(output/'CHESHIRE_COLUMN_G7_ORDERED_PRIMARY_FULL.ply', xyz, faces, expected)
    chosen = []
    for start in range(0, len(faces), 131072):
        block = faces[start:start+131072]
        center = xyz[block].mean(axis=1)
        chosen.append(start+np.flatnonzero(np.sum((center-TARGET)**2, axis=1) <= RADIUS**2))
    face_ids = np.concatenate(chosen)
    if not len(face_ids):
        raise ValueError('The saved macro-target triangle subset is empty.')
    vertex_ids, inverse = np.unique(faces[face_ids].ravel(), return_inverse=True)
    print('EXPORT exact original near-detail triangle subset', flush=True)
    detail = write_ply(output/'CHESHIRE_COLUMN_G7_ORDERED_PRIMARY_DETAIL.ply',
                       xyz[vertex_ids], inverse.reshape(-1, 3), expected)
    detail.update(scope='Exact stored triangle subset; open cut boundary, no caps or new surface.',
                  selection='Source triangle centroids within radius of the saved macro-camera target.',
                  target=TARGET.tolist(), radius=RADIUS)
    ids_path = output/'DETAIL_SOURCE_IDS.npz'
    np.savez_compressed(ids_path, source_vertex_ids=vertex_ids, source_face_ids=face_ids)
    if (digest(source) != expected or digest(receipt_path) != receipt_sha or
            digest(__file__) != code_sha or any(digest(path) != sha for path, sha in dependencies)):
        raise ValueError('Frozen source, receipt or executed exporter changed.')
    manifest = dict(date='2026-10-14', timezone='Asia/Seoul', source=str(source), source_sha256=expected,
        source_receipt=str(receipt_path), source_receipt_sha256=receipt_sha, source_variant='ORDERED',
        native_faces_sha256=FACES_SHA, checked_generation_sources=checked_sources,
        checked_generation_code_snapshots=checked_snapshots,
        export_code=str(Path(__file__).resolve()), export_code_sha256=code_sha,
        preserved_dependencies=[dict(path=str(path), sha256=sha) for path, sha in dependencies],
        checkpoint=args.checkpoint, full=full, detail=detail,
        detail_source_ids=dict(path=str(ids_path), sha256=digest(ids_path)),
        source_geometry_modified=False, simplification=False,
        units='Unchanged source model units; no scale conversion applied.',
        seconds=time.perf_counter()-started)
    (output/'MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    (output/'README.txt').write_text('CHESHIRE G7 ordered-primary fold hierarchy / 2026-10-14\n\n'
        'FULL: complete stored native model, no simplification or scale conversion.\n'
        'DETAIL: exact stored triangle subset for lightweight close inspection.\n'
        'DETAIL has an open cut boundary; no caps or new surface are added.\n'
        'PLY contains no materials or cameras. Original coordinates/model units retained.\n'
        'See MANIFEST.json for receipt, source hashes and complete PLY roundtrip verification.\n', encoding='utf8')
    print(json.dumps(dict(full=full, detail=detail, seconds=manifest['seconds'])), flush=True)


if __name__ == '__main__':
    main()
