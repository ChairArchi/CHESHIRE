"""Inspect the already-saved actual whole-column voxel target, without geometry changes."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('volume_target_preview_frozen_renderer', HERE/'render.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
digest = renderer.digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    output = root/'target_views'
    if output.exists():
        raise FileExistsError('Earlier actual target previews preserved.')
    receipt = json.loads((root/'TARGET_RECEIPT.json').read_text(encoding='utf-8'))
    path = root/'target_geometry.npz'
    if digest(path) != receipt['target_file_sha256']:
        raise ValueError('Actual saved target changed.')
    with np.load(path, allow_pickle=False) as data:
        xyz, faces = data['xyz'], data['triangles']
    for key, array in [('xyz', xyz), ('triangles', faces)]:
        if hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast('B')).hexdigest() != receipt['actual_target']['target_'+key+'_sha256']:
            raise ValueError('Actual target array hash differs: '+key)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    shared_spec = importlib.util.spec_from_file_location('volume_target_preview_frozen_scene', renderer.base.SHARED_RENDER)
    shared = importlib.util.module_from_spec(shared_spec)
    shared_spec.loader.exec_module(shared)
    mesh = bpy.data.meshes.new('Actual saved full voxel target')
    mesh.vertices.add(len(xyz))
    mesh.vertices.foreach_set('co', xyz.ravel())
    mesh.loops.add(3*len(faces))
    mesh.loops.foreach_set('vertex_index', faces.ravel())
    mesh.polygons.add(len(faces))
    mesh.polygons.foreach_set('loop_start', np.arange(0, 3*len(faces), 3, dtype=np.int32))
    mesh.polygons.foreach_set('loop_total', np.full(len(faces), 3, np.int32))
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new('Actual saved full voxel target', mesh)
    bpy.context.collection.objects.link(obj)
    shared.material(obj)
    scene, camera = shared.setup_scene(900, 24)
    conditions = renderer.base.actual_conditions(bpy, scene, camera, obj)
    renderer.require_close(conditions, renderer.base.expected_conditions())
    output.mkdir()
    actual_views, images = {}, []
    for name, (position, target, scale) in renderer.VIEWS.items():
        camera.location = position
        camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        actual_views[name] = dict(position=list(camera.location), target=list(target), scale=float(camera.data.ortho_scale))
        path_png = output/(name+'.png')
        scene.render.filepath = str(path_png)
        bpy.ops.render.render(write_still=True)
        images.append(dict(view=name, filename=path_png.name, sha256=digest(path_png)))
    if digest(path) != receipt['target_file_sha256']:
        raise ValueError('Saved target changed during preview.')
    snapshot = root/'source_snapshot_target_preview'
    snapshot.mkdir()
    shutil.copyfile(__file__, snapshot/'target_preview.py')
    result = dict(kind='ACTUAL_FULL_COLUMN_VOXEL_TARGET_PREVIEW',
        source_target_path=str(path), source_target_sha256=receipt['target_file_sha256'],
        target_receipt_sha256=digest(root/'TARGET_RECEIPT.json'),
        vertices=len(xyz), triangles=len(faces), blender_version=bpy.app.version_string,
        views=renderer.VIEWS, actual_views=actual_views, conditions=conditions, images=images,
        renderer_code_sha256=digest(__file__), preserved_renderer_hashes=renderer.code_hashes(),
        geometry_processing_in_renderer=False, smooth_shading=False,
        scope='Actual saved voxel+Smooth TARGET itself, applied globally before this preview. Separate G7-derived finish candidate; not original locally projected G7, not G8, not original chart/face-ID preserving.')
    (output/'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('TARGET_PREVIEW_DONE', len(images), flush=True)


if __name__ == '__main__':
    main()
