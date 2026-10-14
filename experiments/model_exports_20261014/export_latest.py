"""Export the stored latest native model, without modifying or simplifying it."""
from pathlib import Path
import hashlib
import json
import time
import numpy as np

HERE=Path(__file__).resolve().parent
SOURCE=Path('E:/CHESHIRE_DATA/experiments/comb_scale_refinement_20261014/trial01/REFINED/geometry.npz')
EXPECTED='37549b71c997a65943fbb6416d008b748ecba4ab05898eadfea95bc994e3a710'
OUTPUT=Path('E:/CHESHIRE_DATA/exports/20261014/LATEST_COLUMN_SCALE_REFINED')
TARGET=np.array([-.8127592552124007,.42607142838364565,6.369917540048999])
RADIUS=.28
FACE=np.dtype([('count','u1'),('indices','<i4',(3,))],align=False)

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(8*1024**2),b''):h.update(block)
    return h.hexdigest()

def write_ply(path,xyz,faces):
    if len(xyz)>np.iinfo(np.int32).max or faces.min()<0 or faces.max()>=len(xyz):
        raise ValueError('PLY signed int32 face indexing is invalid.')
    header=('ply\nformat binary_little_endian 1.0\n'
        'comment CHESHIRE stored native G7 local scale refinement\n'
        'comment Source geometry SHA256 '+EXPECTED+'\n'
        'comment Original coordinates and units unchanged\n'
        f'element vertex {len(xyz)}\nproperty double x\nproperty double y\nproperty double z\n'
        f'element face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n').encode('ascii')
    with open(path,'xb') as stream:
        stream.write(header)
        for start in range(0,len(xyz),262144):
            np.ascontiguousarray(xyz[start:start+262144],dtype='<f8').tofile(stream)
        for start in range(0,len(faces),262144):
            block=faces[start:start+262144]
            packed=np.empty(len(block),FACE);packed['count']=3;packed['indices']=block
            packed.tofile(stream)
    expected=len(header)+len(xyz)*24+len(faces)*13
    if path.stat().st_size!=expected:raise ValueError('PLY byte length differs.')
    # Read back every written coordinate/index without loading a second model.
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
    return dict(path=str(path),vertices=len(xyz),triangles=len(faces),bytes=expected,
        sha256=digest(path),exact_coordinate_and_triangle_roundtrip=True,
        coordinates='binary float64, unchanged source axes/model units',faces='uchar3 + signed int32 indices')

def main():
    started=time.perf_counter()
    if (OUTPUT/'MANIFEST.json').exists():raise FileExistsError('Existing export preserved.')
    if digest(SOURCE)!=EXPECTED:raise ValueError('Latest native source changed.')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    with np.load(SOURCE,allow_pickle=False) as saved:xyz,faces=saved['xyz'],saved['faces']
    if xyz.shape!=(21842242,3) or faces.shape!=(43684480,3):raise ValueError('Latest native counts differ.')
    print('EXPORT latest full native model',flush=True)
    full=write_ply(OUTPUT/'CHESHIRE_COLUMN_G7_LATEST_FULL.ply',xyz,faces)
    print('EXPORT original near-detail triangles',flush=True)
    chosen=[]
    for start in range(0,len(faces),131072):
        block=faces[start:start+131072]
        center=xyz[block].mean(axis=1)
        distance=np.sum((center-TARGET)**2,axis=1)
        chosen.append(start+np.flatnonzero(distance<=RADIUS**2))
    face_ids=np.concatenate(chosen)
    if not len(face_ids):raise ValueError('Saved camera target detail crop is empty.')
    vertex_ids,inverse=np.unique(faces[face_ids].ravel(),return_inverse=True)
    detail=write_ply(OUTPUT/'CHESHIRE_COLUMN_G7_DETAIL.ply',xyz[vertex_ids],inverse.reshape(-1,3))
    detail.update(scope='Exact original triangle subset for close inspection; cut boundary is open, no caps or new surface.',
        selection='Source triangle centroids within radius of the saved macro camera target.',
        target=TARGET.tolist(),radius=RADIUS)
    np.savez_compressed(OUTPUT/'DETAIL_SOURCE_IDS.npz',source_vertex_ids=vertex_ids,source_face_ids=face_ids)
    if digest(SOURCE)!=EXPECTED:raise ValueError('Native source changed during export.')
    manifest=dict(date='2026-10-14',timezone='Asia/Seoul',source=str(SOURCE),source_sha256=EXPECTED,
        export_code=str(Path(__file__).resolve()),export_code_sha256=digest(__file__),
        latest_checkpoint='d9caf95325bff541489eecfbe64265eaf20ac7e5',
        full=full,detail=detail,source_geometry_modified=False,simplification=False,
        units='Unchanged source model units; no scale conversion applied.',seconds=time.perf_counter()-started)
    (OUTPUT/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (OUTPUT/'README.txt').write_text(
        'CHESHIRE latest column / 2026-10-14\n\n'
        'FULL: complete latest native G7 model, no simplification.\n'
        'DETAIL: original triangle subset for lightweight close inspection.\n'
        'The DETAIL cut boundary is open. Source coordinates/units are retained.\n'
        'No materials or cameras are encoded in PLY.\n'
        'Source hashes, counts and exact roundtrip verification: MANIFEST.json\n',encoding='utf8')
    print(json.dumps(dict(full=full,detail=detail,seconds=manifest['seconds'])),flush=True)

if __name__=='__main__':main()
