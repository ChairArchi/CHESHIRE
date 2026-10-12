"""Render one saved neutral-CC G7 surface finish of a selected whole-column G6."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RAW_RENDER = HERE / 'render.py'
RAW_RENDER_SHA256 = 'f5ce95165c264df3d4f5c77c0eff483e8db29094e64f3fca06e77a43de906700'
spec = importlib.util.spec_from_file_location('whole_column_raw_surface_reference', RAW_RENDER)
raw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(raw)
digest, read_json, require_close = raw.digest, raw.read_json, raw.require_close
STAGES, VIEWS = raw.STAGES, raw.VIEWS


def code_hashes():
    if digest(RAW_RENDER) != RAW_RENDER_SHA256:
        raise ValueError('Preserved G6 camera/material renderer changed.')
    return dict(render=digest(__file__), raw_renderer=RAW_RENDER_SHA256, raw_code_sha256=raw.code_hashes())


def source_state(root, stage):
    root = Path(root).resolve()
    parent_folder, parent_info, parent_source = raw.source_state(root, stage)
    folder = root / 'SURFACE' / stage / 'SPAN/G07'
    info = read_json(folder / 'generation.json')
    if (info.get('candidate') != stage + '_SURFACE' or info.get('input_case') != 'SPAN' or
        info.get('source_generation') != 6 or info.get('subdivision_generation') != 7 or
        info.get('added_CC_passes') != 1 or info.get('neutral_passes') != 1 or
        info.get('added_normal_field_passes') != 0 or
        Path(info.get('source', '')).resolve() != raw.PARENT.resolve() or
        Path(info.get('parent_stage', '')).resolve() != parent_folder or
        info.get('parent_stage_control_sha256') != parent_source['control_sha256'] or
        info.get('parent_stage_generation_sha256') != parent_source['generation_sha256']):
        raise ValueError('Actual selected G6 plus exactly one neutral CC pass to G7 required; no new normal field.')
    code = info.get('geometry_code_sha256', {})
    if not code:
        raise ValueError('Generation code hashes required.')
    for name, checksum in code.items():
        path = (REPO / name).resolve()
        if not path.is_relative_to(REPO.resolve()) or digest(path) != checksum:
            raise ValueError('Generation code changed: ' + name)
    geometry, control = folder / 'geometry.npz', folder / 'control_quad.npz'
    gh, ch = digest(geometry), digest(control)
    if gh != info['geometry_file_sha256'] or ch != info['control_file_sha256']:
        raise ValueError('Saved neutral-CC G7 geometry/control changed.')
    source = dict(source=str(geometry), source_sha256=gh,
        generation_source=str(folder / 'generation.json'), generation_sha256=digest(folder / 'generation.json'),
        control_source=str(control), control_sha256=ch, parent_source=str(parent_folder),
        parent_control_sha256=parent_source['control_sha256'], parent_geometry_sha256=parent_source['source_sha256'],
        parent_generation_sha256=parent_source['generation_sha256'])
    return folder, info, source, (parent_folder, parent_info, parent_source)


def render_state(info, source, output, hashes):
    import bpy
    import numpy as np
    from mathutils import Vector
    shared_spec = importlib.util.spec_from_file_location('whole_column_surface_shared_scene', raw.base.SHARED_RENDER)
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
        mesh = bpy.data.meshes.new('Saved neutral CC native G7')
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
        obj = bpy.data.objects.new('Saved neutral CC native G7', mesh)
        bpy.context.collection.objects.link(obj)
        shared.material(obj)
    scene, camera = shared.setup_scene(900, 24)
    conditions = raw.base.actual_conditions(bpy, scene, camera, obj)
    require_close(conditions, raw.base.expected_conditions())
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
    receipt = dict(candidate=info['candidate'], input_case='SPAN', source_generation=6, subdivision_generation=7,
        added_CC_passes=1, neutral_passes=1, added_normal_field_passes=0,
        version=bpy.app.version_string, views=VIEWS, actual_views=actual_views,
        conditions=conditions, code_sha256=hashes, source_arrays=arrays, images=images, **source,
        scope='Actual selected saved G6 plus one neutral CC to G7; no new field; saved native only; float32 display; no modifiers/maps or geometry certification.')
    (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    print('RENDERED', info['candidate'], 'SPAN G7', len(images), 'views', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--stage', choices=STAGES, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    hashes = code_hashes()
    folder, info, source, parent = source_state(args.root, args.stage)
    render_state(info, source, folder / 'views', hashes)
    if source_state(args.root, args.stage)[2:] != (source, parent):
        raise ValueError('Saved selected G6/G7 states changed while rendering.')


if __name__ == '__main__':
    main()
