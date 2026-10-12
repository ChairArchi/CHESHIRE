"""Render one saved parent-linked whole-column relief; actual G7 remains G7."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PARENT_RENDER = HERE.parent / 'whole_column_detail_20261013/surface_render.py'
PARENT_RENDER_SHA256 = '991bdc01c84afac27c0c2bde365a6293c4756234021e671c68eaffb4e4d69bcc'
PARENT = Path('E:/CHESHIRE_DATA/experiments/whole_column_detail_20261013/trial01/SURFACE/MIDDLE/SPAN/G07')
spec = importlib.util.spec_from_file_location('parent_linked_frozen_surface_render', PARENT_RENDER)
surface = importlib.util.module_from_spec(spec)
spec.loader.exec_module(surface)
digest, read_json, require_close = surface.digest, surface.read_json, surface.require_close
VIEWS = surface.VIEWS


def code_hashes():
    if digest(PARENT_RENDER) != PARENT_RENDER_SHA256:
        raise ValueError('Preserved parent G7 scene/material renderer changed.')
    return dict(render=digest(__file__), parent_renderer=PARENT_RENDER_SHA256,
        parent_code_sha256=surface.code_hashes())


def check_geometry_code(info):
    code = info.get('geometry_code_sha256', {})
    if not code:
        raise ValueError('Generation code hashes required.')
    for name, checksum in code.items():
        path = (REPO / name).resolve()
        if not path.is_relative_to(REPO.resolve()) or digest(path) != checksum:
            raise ValueError('Generation code changed: ' + name)


def saved_state(folder, info):
    geometry, control = folder / 'geometry.npz', folder / 'control_quad.npz'
    gh, ch = digest(geometry), digest(control)
    if gh != info['geometry_file_sha256'] or ch != info['control_file_sha256']:
        raise ValueError('Saved G7 geometry/control changed: ' + str(folder))
    if info.get('checks', {}).get('passed') is not True or info.get('symmetry', {}).get('passed') is not True:
        raise ValueError('Saved mesh checks and reflected control correspondence must pass.')
    check_geometry_code(info)
    return dict(source=str(geometry), source_sha256=gh,
        generation_source=str(folder / 'generation.json'), generation_sha256=digest(folder / 'generation.json'),
        control_source=str(control), control_sha256=ch)


def parent_state():
    info = read_json(PARENT / 'generation.json')
    if (info.get('candidate') != 'MIDDLE_SURFACE' or info.get('input_case') != 'SPAN' or
        info.get('subdivision_generation') != 7 or info.get('source_generation') != 6 or
        info.get('added_CC_passes') != 1 or info.get('added_normal_field_passes') != 0):
        raise ValueError('Actual preserved MIDDLE_SURFACE SPAN G7 required.')
    return info, saved_state(PARENT, info)


def source_state(root):
    root = Path(root).resolve()
    folder = root / 'PARENT_LINKED/SPAN/G07'
    info = read_json(folder / 'generation.json')
    _, parent = parent_state()
    if (info.get('candidate') != 'PARENT_LINKED' or info.get('input_case') != 'SPAN' or
        info.get('source_generation') != 7 or info.get('subdivision_generation') != 7 or
        info.get('added_CC_passes') != 0 or info.get('added_normal_field_passes') != 2 or
        Path(info.get('source', '')).resolve() != PARENT.resolve() or
        Path(info.get('parent_stage', '')).resolve() != PARENT.resolve() or
        info.get('source_control_sha256') != parent['control_sha256'] or
        info.get('source_generation_json_sha256') != parent['generation_sha256']):
        raise ValueError('Actual preserved parent G7 plus two saved field passes and zero added CC passes required.')
    source = saved_state(folder, info)
    source.update(parent_source=str(PARENT), parent_control_sha256=parent['control_sha256'],
        parent_geometry_sha256=parent['source_sha256'], parent_generation_sha256=parent['generation_sha256'])
    return folder, info, source


def render_state(info, source, output, hashes):
    import bpy
    import numpy as np
    from mathutils import Vector
    shared_spec = importlib.util.spec_from_file_location('parent_linked_shared_scene', surface.raw.base.SHARED_RENDER)
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
        mesh = bpy.data.meshes.new('Saved parent-linked native G7')
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
        obj = bpy.data.objects.new('Saved parent-linked native G7', mesh)
        bpy.context.collection.objects.link(obj)
        shared.material(obj)
    scene, camera = shared.setup_scene(900, 24)
    conditions = surface.raw.base.actual_conditions(bpy, scene, camera, obj)
    require_close(conditions, surface.raw.base.expected_conditions())
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
    receipt = dict(candidate='PARENT_LINKED', input_case='SPAN', source_generation=7, subdivision_generation=7,
        added_CC_passes=0, added_normal_field_passes=2,
        version=bpy.app.version_string, views=VIEWS, actual_views=actual_views,
        conditions=conditions, code_sha256=hashes, source_arrays=arrays, images=images, **source,
        scope='Actual saved G7 plus two parent-linked field passes; no added CC; saved native only; float32 display; no modifiers/maps or geometry certification.')
    (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    print('RENDERED PARENT_LINKED SPAN G7', len(images), 'views', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    hashes = code_hashes()
    folder, info, source = source_state(args.root)
    render_state(info, source, folder / 'views', hashes)
    if source_state(args.root)[2] != source:
        raise ValueError('Saved parent/final G7 states changed while rendering.')


if __name__ == '__main__':
    main()
