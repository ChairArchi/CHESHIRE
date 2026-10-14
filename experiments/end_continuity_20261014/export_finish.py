"""Export a receipt-bound coherent G7 native model, without mesh changes.

Adapted from the preserved exact hierarchy exporter. Geometry is discovered
from the selected actual receipt at runtime; no pending geometry SHA is baked
into this script. This module performs no export on import.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import time

import numpy as np

HERE = Path(__file__).resolve().parent
HELPER = HERE.parent/'model_exports_20261014/export_latest.py'
TEMPLATE = HERE.parent/'fold_hierarchy_20261014/export_model.py'
HELPER_SHA = '86ca0cb13856af317efbe9d63a461ddedb704e49b3af1207d454c9a5121feb62'
TEMPLATE_SHA = '194fb0515f5aea7ffee30ab56feb13a0f1c12d457ec121df1e785c7e9aadc444'
spec = importlib.util.spec_from_file_location('coherent_preserved_ply_helper', HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
digest, FACE = helper.digest, helper.FACE
ROOT = Path('E:/CHESHIRE_DATA/experiments/end_continuity_20261014/trial02')
OUTPUT = Path('E:/CHESHIRE_DATA/exports/20261014/COLUMN_COHERENT_FLOW')
FACES_SHA = '67109d7c7378b6cdfe82a713c74a860c98cdd53adcdce311f8612b3e6565a9ee'
TARGET = np.array([-.8127592552124007, .42607142838364565, 6.369917540048999])
RADIUS = .28


def ah(value):
    import hashlib
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def write_ply(path, xyz, faces, source_sha):
    """Exact source doubles and integer triangles, with complete readback."""
    if (len(xyz)>np.iinfo(np.int32).max or faces.min()<0 or faces.max()>=len(xyz)):
        raise ValueError('PLY signed int32 face indexing is invalid.')
    header = ('ply\nformat binary_little_endian 1.0\n'
        'comment CHESHIRE stored G7 coherent replay and continuous fine-fold finish\n'
        'comment Source geometry SHA256 '+source_sha+'\n'
        'comment Original coordinates and units unchanged\n'
        f'element vertex {len(xyz)}\nproperty double x\nproperty double y\nproperty double z\n'
        f'element face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n').encode('ascii')
    with open(path,'xb') as stream:
        stream.write(header)
        for start in range(0,len(xyz),262144):
            np.ascontiguousarray(xyz[start:start+262144],dtype='<f8').tofile(stream)
        for start in range(0,len(faces),262144):
            block=faces[start:start+262144]
            packed=np.empty(len(block),FACE)
            packed['count'],packed['indices']=3,block
            packed.tofile(stream)
    expected_bytes=len(header)+len(xyz)*24+len(faces)*13
    if path.stat().st_size!=expected_bytes:raise ValueError('PLY byte length differs.')
    with open(path,'rb') as stream:
        if stream.read(len(header))!=header:raise ValueError('PLY header differs.')
        for start in range(0,len(xyz),262144):
            source=xyz[start:start+262144]
            actual=np.fromfile(stream,dtype='<f8',count=source.size).reshape(source.shape)
            if not np.array_equal(actual,source):raise ValueError('PLY coordinate roundtrip differs.')
        for start in range(0,len(faces),262144):
            source=faces[start:start+262144]
            actual=np.fromfile(stream,dtype=FACE,count=len(source))
            if not np.all(actual['count']==3) or not np.array_equal(actual['indices'],source):
                raise ValueError('PLY triangle roundtrip differs.')
        if stream.read(1):raise ValueError('Unexpected PLY trailing bytes.')
    return dict(path=str(path),vertices=len(xyz),triangles=len(faces),bytes=expected_bytes,
        sha256=digest(path),exact_coordinate_and_triangle_roundtrip=True,
        coordinates='binary float64; unchanged source axes/model units',
        faces='uchar3 + signed int32 indices')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--variant',default='COHERENT_FLOW')
    parser.add_argument('--checkpoint',default=None,help='Optional actual repository commit hash.')
    args=parser.parse_args();started=time.perf_counter()
    root,output=args.root.resolve(),args.output.resolve()
    if output.exists():raise FileExistsError('An existing export directory is preserved.')
    for path,expected in ((HELPER,HELPER_SHA),(TEMPLATE,TEMPLATE_SHA)):
        if digest(path)!=expected:raise ValueError('Preserved exact export dependency changed: '+str(path))
    receipt_path=root/'RECEIPT.json'
    receipt_sha=digest(receipt_path)
    receipt=json.loads(receipt_path.read_text(encoding='utf8'))
    variant=receipt['variants'][args.variant]
    source=Path(variant['geometry']).resolve()
    if not source.is_relative_to(root) or source.name!='geometry.npz':
        raise ValueError('Actual receipt geometry must belong to the selected trial.')
    expected=variant['geometry_sha256']
    if (digest(source)!=expected or variant['faces_sha256']!=FACES_SHA or
            variant['vertices']!=14004226 or variant['triangles']!=28008448):
        raise ValueError('Actual receipt native binding/counts differ.')
    checked_sources={}
    for name,checksum in receipt.get('sources',{}).items():
        if digest(name)!=checksum:raise ValueError('Actual generation input changed: '+name)
        checked_sources[name]=checksum
    checked_snapshots={}
    for name,record in receipt['source_snapshots'].items():
        if any(digest(record[key])!=record['sha256'] for key in ('source','snapshot')):
            raise ValueError('Actual executed generation source/snapshot differs: '+name)
        checked_snapshots[name]=record
    code_sha=digest(__file__)
    output.mkdir(parents=True)
    shutil.copyfile(__file__,output/'SOURCE_SNAPSHOT_export_finish.py')
    shutil.copyfile(HELPER,output/'SOURCE_SNAPSHOT_preserved_export_helper.py')
    shutil.copyfile(TEMPLATE,output/'SOURCE_SNAPSHOT_preserved_export_template.py')
    shutil.copyfile(receipt_path,output/'SOURCE_GENERATION_RECEIPT.json')
    with np.load(source,allow_pickle=False) as saved:
        xyz,faces=saved['xyz'],saved['faces']
    if (xyz.shape!=(14004226,3) or faces.shape!=(28008448,3) or
            xyz.dtype!=np.dtype('float64') or not np.isfinite(xyz).all() or
            ah(xyz)!=variant['xyz_sha256'] or ah(faces)!=FACES_SHA):
        raise ValueError('Actual complete native arrays differ from the receipt.')
    print('EXPORT exact coherent full native G7 model',flush=True)
    full=write_ply(output/'CHESHIRE_COLUMN_G7_COHERENT_FLOW_FULL.ply',xyz,faces,expected)
    chosen=[]
    for start in range(0,len(faces),131072):
        block=faces[start:start+131072]
        center=xyz[block].mean(axis=1)
        chosen.append(start+np.flatnonzero(np.sum((center-TARGET)**2,axis=1)<=RADIUS**2))
    face_ids=np.concatenate(chosen)
    if not len(face_ids):raise ValueError('The saved macro-target triangle subset is empty.')
    vertex_ids,inverse=np.unique(faces[face_ids].ravel(),return_inverse=True)
    print('EXPORT exact original near-detail triangle subset',flush=True)
    detail=write_ply(output/'CHESHIRE_COLUMN_G7_COHERENT_FLOW_DETAIL.ply',
        xyz[vertex_ids],inverse.reshape(-1,3),expected)
    detail.update(scope='Exact stored triangle subset; open cut boundary, no caps or new surface.',
        selection='Source triangle centroids within radius of the same saved macro-camera target.',
        target=TARGET.tolist(),radius=RADIUS)
    ids_path=output/'DETAIL_SOURCE_IDS.npz'
    np.savez_compressed(ids_path,source_vertex_ids=vertex_ids,source_face_ids=face_ids)
    if (digest(source)!=expected or digest(receipt_path)!=receipt_sha or
            digest(__file__)!=code_sha or digest(HELPER)!=HELPER_SHA or digest(TEMPLATE)!=TEMPLATE_SHA):
        raise ValueError('Frozen source, receipt or executed exporter changed.')
    manifest=dict(date='2026-10-14',timezone='Asia/Seoul',source=str(source),source_sha256=expected,
        source_receipt=str(receipt_path),source_receipt_sha256=receipt_sha,source_variant=args.variant,
        native_faces_sha256=FACES_SHA,checked_generation_sources=checked_sources,
        checked_generation_code_snapshots=checked_snapshots,
        export_code=str(Path(__file__).resolve()),export_code_sha256=code_sha,
        preserved_helper=dict(path=str(HELPER),sha256=HELPER_SHA),
        preserved_template=dict(path=str(TEMPLATE),sha256=TEMPLATE_SHA),
        checkpoint=args.checkpoint,full=full,detail=detail,
        detail_source_ids=dict(path=str(ids_path),sha256=digest(ids_path)),
        source_geometry_modified=False,simplification=False,
        units='Unchanged source model units; no scale conversion applied.',
        seconds=time.perf_counter()-started)
    (output/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (output/'README.txt').write_text('CHESHIRE G7 coherent replay and continuous fine folds / 2026-10-14\n\n'
        'FULL: complete stored native model, no simplification or scale conversion.\n'
        'DETAIL: exact stored triangle subset for lightweight close inspection.\n'
        'DETAIL has an open cut boundary; no caps or new surface are added.\n'
        'PLY contains no materials or cameras. Original coordinates/model units retained.\n'
        'See MANIFEST.json for receipt, source hashes and complete PLY roundtrip verification.\n',encoding='utf8')
    print(json.dumps(dict(full=full,detail=detail,seconds=manifest['seconds'])),flush=True)


if __name__=='__main__':
    main()
