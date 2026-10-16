"""Export the saved native structural prototype with exact full PLY readback."""
from pathlib import Path
import argparse, json, shutil, sys, time
import numpy as np
sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'src'))
from cheshire.ornament_assembly import file_hash, record

CHUNK = 131072


def main(root, output, filename='CHESHIRE_COLUMN_STRUCTURAL_TISSUE_EXPERIMENT.ply'):
    started = time.perf_counter()
    meta_path = root/'SYNTHESIS_RECEIPT.json'
    qa_path = root/'GLOBAL_NATIVE_TOPOLOGY_QA.json'
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    qa = json.loads(qa_path.read_text(encoding='utf-8'))
    if (meta['kind'] != 'LIKED_HYBRID_NATIVE_FULL_XYZ_STRUCTURAL_TISSUE_REBUILD'
            or not meta['previous_global_hybrid_geometry_is_actual_base']
            or meta['assembly']['added_handles'] != 0
            or not qa['passed'] or qa['Euler_characteristic'] != 2
            or qa['source_receipt'] != record(meta_path)):
        raise ValueError('An audited closed structural prototype on the liked hybrid is required.')
    arrays = meta['assembly']['arrays']
    for key in ('XYZ', 'QUADS', 'TRIANGLES'):
        if file_hash(arrays[key]['path']) != arrays[key]['sha256']:
            raise ValueError('Source array changed: '+key)
    x = np.load(arrays['XYZ']['path'], mmap_mode='r')
    q = np.load(arrays['QUADS']['path'], mmap_mode='r')
    t = np.load(arrays['TRIANGLES']['path'], mmap_mode='r')
    nv, nt = len(x), len(t)
    if len(q) or x.dtype != np.float64 or nv >= 2**32:
        raise ValueError('Expected exact native triangles and float64 XYZ.')
    if Path(filename).name != filename or not filename.lower().endswith('.ply'):
        raise ValueError('Expected one PLY filename within the new output folder.')
    output.mkdir(parents=True, exist_ok=False)
    target = output/filename
    header = ('ply\nformat binary_little_endian 1.0\n'
        'comment CHESHIRE separate structural tissue prototype\n'
        'comment Native liked hybrid with selected closed-backed full XYZ replacements\n'
        f'element vertex {nv}\nproperty double x\nproperty double y\nproperty double z\n'
        f'element face {nt}\nproperty list uchar uint vertex_indices\nend_header\n').encode('ascii')
    dtype = np.dtype([('count','u1'),('indices','<u4',(3,))])
    with target.open('xb') as stream:
        stream.write(header)
        for a in range(0, nv, CHUNK):
            stream.write(np.asarray(x[a:a+CHUNK], dtype='<f8').tobytes())
        for a in range(0, nt, CHUNK):
            block = np.empty(min(CHUNK,nt-a),dtype=dtype)
            block['count'] = 3
            block['indices'] = t[a:a+CHUNK]
            stream.write(block.tobytes())
    expected = len(header)+24*nv+13*nt
    if target.stat().st_size != expected:
        raise ValueError('Native PLY byte size differs.')
    xx = np.memmap(target,mode='r',dtype='<f8',offset=len(header),shape=(nv,3))
    tt = np.memmap(target,mode='r',dtype=dtype,offset=len(header)+24*nv,shape=(nt,))
    for a in range(0,nv,CHUNK):
        if not np.array_equal(xx[a:a+CHUNK],x[a:a+CHUNK]):
            raise ValueError('Native PLY XYZ readback differs.')
    for a in range(0,nt,CHUNK):
        if (not np.all(tt['count'][a:a+CHUNK]==3)
                or not np.array_equal(tt['indices'][a:a+CHUNK],t[a:a+CHUNK])):
            raise ValueError('Native PLY triangle readback differs.')
    metadata = output/'metadata'; metadata.mkdir()
    copies = {}
    for p in (meta_path,qa_path,Path(meta['patch_index']['path'])):
        dest = metadata/p.name; shutil.copyfile(p,dest); copies[str(p)] = record(dest)
    snapshot = output/'source_snapshot'; snapshot.mkdir()
    dest = snapshot/Path(__file__).name; shutil.copyfile(__file__,dest)
    receipt = dict(kind='EXACT_NATIVE_STRUCTURAL_TISSUE_PROTOTYPE_PLY',
        model=record(target),bytes=expected,vertices=nv,triangles=nt,
        full_float64_XYZ_readback_exact=True,full_uint32_TRI_readback_exact=True,
        saved_native_geometry_not_decimated=True,source=record(meta_path),
        closed_native_topology_QA=record(qa_path),metadata_copies=copies,
        source_snapshot=record(dest),prototype=True,user_adopted=False,
        global_self_intersection_certified=False,manufacturing_strength_certified=False,
        elapsed_seconds=time.perf_counter()-started)
    (output/'MODEL_EXPORT.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('STRUCTURAL_NATIVE_PLY_READY',str(target),expected,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--filename',default='CHESHIRE_COLUMN_STRUCTURAL_TISSUE_EXPERIMENT.ply')
    a=p.parse_args();main(a.root,a.out,a.filename)
