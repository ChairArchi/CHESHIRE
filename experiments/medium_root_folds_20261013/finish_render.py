"""Render one saved delta-only finish; actual G7 and existing field history are retained."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
RAW_RENDER = HERE / 'render.py'
RAW_RENDER_SHA256 = '42dea9023a652f0d96af892733a9c49acc8d885f9f1ca9f5bb3847f01501f0c3'
spec = importlib.util.spec_from_file_location('wide_root_finish_preserved_renderer', RAW_RENDER)
raw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(raw)
digest, read_json, require_close = raw.digest, raw.read_json, raw.require_close
PARENT, VIEWS = raw.PARENT, raw.VIEWS
RAW = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial01/WIDE_ROOT/SPAN/G07')
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial02')


def code_hashes():
    if digest(RAW_RENDER) != RAW_RENDER_SHA256:
        raise ValueError('Preserved raw WIDE_ROOT renderer changed.')
    return dict(render=digest(__file__), raw_renderer=RAW_RENDER_SHA256, raw_code_sha256=raw.code_hashes())


def raw_state():
    info = read_json(RAW / 'generation.json')
    ch, jh = digest(RAW / 'control_quad.npz'), digest(RAW / 'generation.json')
    if (info.get('candidate') != 'WIDE_ROOT' or info.get('input_case') != 'SPAN' or
        info.get('source_generation') != 7 or info.get('subdivision_generation') != 7 or
        info.get('added_CC_passes') != 0 or info.get('added_normal_field_passes') != 2 or
        info.get('smoothing_passes') != 4 or ch != info.get('control_file_sha256')):
        raise ValueError('Actual preserved raw WIDE_ROOT G7 with two fields and four delta-smoothing passes required.')
    return info, dict(raw_field_stage=str(RAW), raw_field_control_sha256=ch, raw_field_generation_json_sha256=jh)


def source_state(root):
    root = Path(root).resolve()
    if any(root == source.resolve() or source.resolve() in root.parents for source in (PARENT, RAW)):
        raise ValueError('Preserved parent and raw G7 states are read-only.')
    folder = root / 'WIDE_ROOT_FINISHED/SPAN/G07'
    info = read_json(folder / 'generation.json')
    _, parent_source = raw.parent_state()
    raw_info, raw_source = raw_state()
    if (info.get('candidate') != 'WIDE_ROOT_FINISHED' or info.get('input_case') != 'SPAN' or
        info.get('source_generation') != 7 or info.get('subdivision_generation') != 7 or
        info.get('added_CC_passes') != 0 or info.get('added_normal_field_passes') != 2 or
        info.get('added_normal_field_passes_this_finish') != 0 or
        info.get('finish_smoothing_passes') != 3 or info.get('smoothing_passes') != raw_info['smoothing_passes'] + 3 or
        info.get('cumulative_normal_field_passes') != raw_info['cumulative_normal_field_passes'] or
        Path(info.get('source', '')).resolve() != PARENT.resolve() or
        Path(info.get('parent_stage', '')).resolve() != PARENT.resolve() or
        Path(info.get('raw_field_stage', '')).resolve() != RAW.resolve() or
        info.get('source_control_sha256') != parent_source['control_sha256'] or
        info.get('source_generation_json_sha256') != parent_source['generation_sha256'] or
        any(info.get(key) != value for key, value in raw_source.items() if key != 'raw_field_stage')):
        raise ValueError('One saved raw-delta finish required: G7, CC0, no recomputed field, three finish smoothing passes.')
    source = raw.parent.saved_state(folder, info)
    source.update(parent_source=str(PARENT), parent_control_sha256=parent_source['control_sha256'],
        parent_geometry_sha256=parent_source['source_sha256'], parent_generation_sha256=parent_source['generation_sha256'],
        **raw_source)
    return folder, info, source


def render_state(info, source, output, hashes):
    import bpy
    import numpy as np
    from mathutils import Vector
    shared_spec = importlib.util.spec_from_file_location('wide_root_finish_shared_scene', raw.parent.surface.raw.base.SHARED_RENDER)
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
        mesh = bpy.data.meshes.new('Saved wide-root delta-finished native G7')
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
        obj = bpy.data.objects.new('Saved wide-root delta-finished native G7', mesh)
        bpy.context.collection.objects.link(obj)
        shared.material(obj)
    scene, camera = shared.setup_scene(900, 24)
    conditions = raw.parent.surface.raw.base.actual_conditions(bpy, scene, camera, obj)
    require_close(conditions, raw.parent.surface.raw.base.expected_conditions())
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
    receipt = dict(candidate='WIDE_ROOT_FINISHED', input_case='SPAN', source_generation=7, subdivision_generation=7,
        added_CC_passes=0, added_normal_field_passes=2, pipeline_added_normal_field_passes=2,
        added_normal_field_passes_this_finish=0, normal_field_passes_computed_this_finish=0,
        cumulative_normal_field_passes=info['cumulative_normal_field_passes'],
        smoothing_passes=info['smoothing_passes'], finish_smoothing_passes=info['finish_smoothing_passes'],
        version=bpy.app.version_string, views=VIEWS, actual_views=actual_views,
        conditions=conditions, code_sha256=hashes, source_arrays=arrays, images=images, **source,
        scope='Saved raw two-field G7 pipeline plus three delta-only finish smoothing passes; no field recomputation and no added CC; total delta smoothing seven; saved native only; float32 display; no modifiers/maps or geometry certification.')
    (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    print('RENDERED WIDE_ROOT_FINISHED SPAN G7', len(images), 'views', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    hashes = code_hashes()
    folder, info, source = source_state(args.root)
    render_state(info, source, folder / 'views', hashes)
    if source_state(args.root)[2] != source:
        raise ValueError('Saved parent/raw/finished G7 states changed while rendering.')


if __name__ == '__main__':
    main()
