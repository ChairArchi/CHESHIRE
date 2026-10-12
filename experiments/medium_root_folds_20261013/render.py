"""Render the saved WIDE_ROOT relief continuing the latest actual G7 column."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
PARENT_RENDER = HERE.parent / 'parent_linked_folds_20261013/render.py'
PARENT_RENDER_SHA256 = 'ffea4c1cfec42101a1dc1c0adf7cabe5d91655f1756d4671fb64f80483950d56'
PARENT = Path('E:/CHESHIRE_DATA/experiments/parent_linked_folds_20261013/trial03/PARENT_LINKED/SPAN/G07')
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial01')
spec = importlib.util.spec_from_file_location('wide_root_preserved_parent_render', PARENT_RENDER)
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)
digest, read_json, require_close = parent.digest, parent.read_json, parent.require_close
VIEWS = parent.VIEWS


def code_hashes():
    if digest(PARENT_RENDER) != PARENT_RENDER_SHA256:
        raise ValueError('Preserved parent G7 camera/material renderer changed.')
    return dict(render=digest(__file__), parent_renderer=PARENT_RENDER_SHA256,
        parent_code_sha256=parent.code_hashes())


def parent_state():
    info = read_json(PARENT / 'generation.json')
    if (info.get('candidate') != 'PARENT_LINKED' or info.get('input_case') != 'SPAN' or
        info.get('subdivision_generation') != 7 or info.get('source_generation') != 7 or
        info.get('added_CC_passes') != 0 or info.get('added_normal_field_passes') != 2 or
        info.get('smoothing_passes') != 3):
        raise ValueError('Actual latest trial03 PARENT_LINKED SPAN G7 required.')
    return info, parent.saved_state(PARENT, info)


def source_state(root):
    root = Path(root).resolve()
    if root == PARENT.resolve() or PARENT.resolve() in root.parents:
        raise ValueError('Preserved parent G7 is read-only.')
    folder = root / 'WIDE_ROOT/SPAN/G07'
    info = read_json(folder / 'generation.json')
    parent_info, parent_source = parent_state()
    if (info.get('candidate') != 'WIDE_ROOT' or info.get('input_case') != 'SPAN' or
        info.get('source_generation') != 7 or info.get('subdivision_generation') != 7 or
        info.get('added_CC_passes') != 0 or info.get('added_normal_field_passes') != 2 or
        info.get('smoothing_passes') != 4 or
        Path(info.get('source', '')).resolve() != PARENT.resolve() or
        Path(info.get('parent_stage', '')).resolve() != PARENT.resolve() or
        info.get('source_control_sha256') != parent_source['control_sha256'] or
        info.get('source_generation_json_sha256') != parent_source['generation_sha256']):
        raise ValueError('Latest saved G7 plus two new field passes and four delta-smoothing passes required; no added CC.')
    if info.get('cumulative_normal_field_passes') != parent_info['cumulative_normal_field_passes'] + 2:
        raise ValueError('Cumulative field count must include the actual parent history and two new passes.')
    source = parent.saved_state(folder, info)
    source.update(parent_source=str(PARENT), parent_control_sha256=parent_source['control_sha256'],
        parent_geometry_sha256=parent_source['source_sha256'], parent_generation_sha256=parent_source['generation_sha256'])
    return folder, info, source


def render_state(info, source, output, hashes):
    import bpy
    import numpy as np
    from mathutils import Vector
    shared_spec = importlib.util.spec_from_file_location('wide_root_shared_scene', parent.surface.raw.base.SHARED_RENDER)
    shared = importlib.util.module_from_spec(shared_spec)
    shared_spec.loader.exec_module(shared)
    if output.exists():
        raise FileExistsError('Existing render preserved: ' + str(output))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    with np.load(source['source'], allow_pickle=False) as data:
        xyz, faces = data['xyz'], data['faces']
        if (xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all() or
            faces.ndim != 2 or faces.shape[1] != 3 or not len(faces) or
            not np.issubdtype(faces.dtype, np.integer) or faces.min() < 0 or faces.max() >= len(xyz)):
            raise ValueError('Finite saved native XYZ and indexed triangles required.')
        arrays = {key + '_sha256': hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast('B')).hexdigest()
                  for key, array in (('xyz', xyz), ('faces', faces))}
        if any(arrays[key + '_sha256'] != info['checks']['native_' + key + '_sha256'] for key in ('xyz', 'faces')):
            raise ValueError('Actual loaded native-array hashes differ.')
        vertex_count, face_count = len(xyz), len(faces)
        mesh = bpy.data.meshes.new('Saved wide-root native G7')
        mesh.vertices.add(vertex_count)
        mesh.vertices.foreach_set('co', np.asarray(xyz, np.float32).ravel())
        del xyz
        mesh.loops.add(3 * face_count)
        mesh.loops.foreach_set('vertex_index', faces.ravel())
        del faces
        mesh.polygons.add(face_count)
        mesh.polygons.foreach_set('loop_start', np.arange(0, 3 * face_count, 3, dtype=np.int32))
        mesh.polygons.foreach_set('loop_total', np.full(face_count, 3, dtype=np.int32))
        mesh.update(calc_edges=True)
        obj = bpy.data.objects.new('Saved wide-root native G7', mesh)
        bpy.context.collection.objects.link(obj)
        shared.material(obj)
    scene, camera = shared.setup_scene(900, 24)
    conditions = parent.surface.raw.base.actual_conditions(bpy, scene, camera, obj)
    require_close(conditions, parent.surface.raw.base.expected_conditions())
    output.mkdir()
    actual_views, images = {}, []
    for name, (position, target, scale) in VIEWS.items():
        camera.location = position
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        actual_views[name] = dict(position=list(camera.location), target=list(target), scale=float(camera.data.ortho_scale),
            forward=list(camera.rotation_euler.to_matrix() @ Vector((0, 0, -1))))
        require_close(actual_views[name], dict(position=list(position), target=list(target), scale=scale,
            forward=list((Vector(target) - Vector(position)).normalized())), 'camera.' + name)
        path = output / (name + '.png')
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        images.append(dict(view=name, filename=path.name, sha256=digest(path)))
    if (digest(source['source']) != source['source_sha256'] or
        digest(source['control_source']) != source['control_sha256'] or
        digest(source['generation_source']) != source['generation_sha256'] or code_hashes() != hashes):
        raise ValueError('Source or code changed during rendering.')
    receipt = dict(candidate='WIDE_ROOT', input_case='SPAN', source_generation=7, subdivision_generation=7,
        added_CC_passes=0, added_normal_field_passes=2,
        cumulative_normal_field_passes=info['cumulative_normal_field_passes'], smoothing_passes=info['smoothing_passes'],
        version=bpy.app.version_string, views=VIEWS, actual_views=actual_views,
        conditions=conditions, code_sha256=hashes, source_arrays=arrays, images=images, **source,
        scope='Latest actual saved G7 plus two new normal-field passes and four delta-smoothing passes; no added CC; saved native only; float32 display; no modifiers/maps or geometry certification.')
    (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    print('RENDERED WIDE_ROOT SPAN G7', len(images), 'views', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    hashes = code_hashes()
    folder, info, source = source_state(args.root)
    render_state(info, source, folder / 'views', hashes)
    if source_state(args.root)[2] != source:
        raise ValueError('Saved latest parent/final G7 states changed while rendering.')


if __name__ == '__main__':
    main()
