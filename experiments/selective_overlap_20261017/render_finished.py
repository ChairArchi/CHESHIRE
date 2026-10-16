"""Reuse the verified native renderer, with a full binary PLY input reader."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import numpy as np
import bpy

HERE = Path(__file__).resolve().parent
RENDERER = HERE.parent / 'early_dynamic_variations_20261016/render_variations.py'
spec = importlib.util.spec_from_file_location('selective_verified_native_renderer', RENDERER)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
old_surface = renderer.surface


def surface(path):
    if path.suffix.lower() != '.ply':
        return old_surface(path)
    lines = []
    with path.open('rb') as f:
        while True:
            line = f.readline()
            if not line or len(lines) > 100:
                raise ValueError('Invalid actual native PLY header.')
            lines.append(line.decode('ascii').strip())
            if lines[-1] == 'end_header':
                break
        offset = f.tell()
    nv = int(next(l for l in lines if l.startswith('element vertex ')).split()[-1])
    nf = int(next(l for l in lines if l.startswith('element face ')).split()[-1])
    required = ['ply', 'format binary_little_endian 1.0',
                'property double x', 'property double y', 'property double z',
                'property list uchar uint vertex_indices', 'end_header']
    if any(l not in lines for l in required) or path.stat().st_size != offset + nv * 24 + nf * 13:
        raise ValueError('Require exact full float64/uint32 triangle PLY.')
    source_x = np.memmap(path, dtype='<f8', mode='r', offset=offset, shape=(nv, 3))
    source_t = np.memmap(path, dtype=np.dtype([('n', 'u1'), ('v', '<u4', (3,))]),
                         mode='r', offset=offset + nv * 24, shape=(nf,))
    if not np.all(source_t['n'] == 3):
        raise ValueError('Actual full native triangles required.')
    x = np.asarray(source_x, dtype=np.float32)
    t = np.asarray(source_t['v'], dtype=np.int32)
    if not np.isfinite(x).all() or t.min() < 0 or t.max() >= nv:
        raise ValueError('Nonfinite/invalid actual native PLY.')
    mesh = bpy.data.meshes.new('Saved complete native surface')
    mesh.vertices.add(nv)
    mesh.vertices.foreach_set('co', x.ravel())
    mesh.loops.add(nf * 3)
    mesh.loops.foreach_set('vertex_index', t.ravel())
    mesh.polygons.add(nf)
    mesh.polygons.foreach_set('loop_start', 3 * np.arange(nf, dtype=np.int32))
    mesh.polygons.foreach_set('loop_total', np.full(nf, 3, dtype=np.int32))
    mesh.polygons.foreach_set('use_smooth', np.ones(nf, bool))
    obj = bpy.data.objects.new('Actual finished column', mesh)
    bpy.context.collection.objects.link(obj)
    rx = np.empty_like(x)
    rt = np.empty(nf * 3, np.int32)
    mesh.vertices.foreach_get('co', rx.ravel())
    mesh.loops.foreach_get('vertex_index', rt)
    if renderer.ah(rx) != renderer.ah(x) or renderer.ah(rt) != renderer.ah(t.ravel()) or len(obj.modifiers):
        raise ValueError('Complete native PLY render readback differs.')
    return obj, x, dict(vertices=nv, triangles=nf, source_kind='FULL_NATIVE_BINARY_PLY',
                        display_xyz_sha256=renderer.ah(rx), display_triangles_sha256=renderer.ah(rt))


renderer.surface = surface
renderer.main()
args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[args.index('--output') + 1])
receipt = out / 'RENDER_RECEIPT.json'
result = json.loads(receipt.read_text(encoding='utf8'))
result.update(full_PLY_loader_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              source_geometry_decimation=False, source_coordinates_modified=False)
receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
