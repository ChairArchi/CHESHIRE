"""Render saved DESIGN_A: actual G6 plus topology events, with no added CC pass."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FROZEN_RENDER = HERE.parent / 'coherent_fold_detail_20261013/render.py'
FROZEN_SHA256 = 'fcea58674b2d8b000a4d626c27f503fb5e01d0553993105336e3fbf325d4f237'
PARENT_RENDER = HERE.parent / 'directional_g6_20261013/render.py'
PARENT_RENDER_SHA256 = 'f73887a4b519f786981a2a806bb6577e34154a4cb4f719d58b2d0ec5a93bd327'
PARENT = Path('E:/CHESHIRE_DATA/experiments/directional_g6_20261013/trial01/DEPTH_08/SPAN/G06')
spec = importlib.util.spec_from_file_location('design_one_frozen_render', FROZEN_RENDER)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
digest, read_json, require_close = base.digest, base.read_json, base.require_close
VIEWS = dict(front=base.VIEWS['front'],
    body_oblique=((-18, 28, 12), (0, 0, 6.25), 4.3),
    body_side=((-32, 0, 6.25), (0, 0, 6.25), 4.3))


def code_hashes():
    if digest(FROZEN_RENDER) != FROZEN_SHA256 or digest(PARENT_RENDER) != PARENT_RENDER_SHA256:
        raise ValueError('Frozen camera/material adapters changed.')
    return dict(render=digest(__file__), frozen_renderer=digest(FROZEN_RENDER),
        parent_renderer=digest(PARENT_RENDER), broad_camera_recipe=digest(base.BROAD_RENDER),
        shared_material_scene_recipe=digest(base.SHARED_RENDER))


def source_state(root):
    folder = Path(root).resolve() / 'DESIGN_A/SPAN/G06_designed'
    info = read_json(folder / 'generation.json')
    if (info.get('candidate') != 'DESIGN_A' or info.get('input_case') != 'SPAN' or
        info.get('source_generation') != 6 or info.get('subdivision_generation') != 6 or
        info.get('added_CC_passes') != 0 or Path(info.get('source', '')).resolve() != PARENT.resolve() or
        info.get('source_control_sha256') != digest(PARENT / 'control_quad.npz')):
        raise ValueError('Actual DEPTH_08 G6 plus design events and zero added CC passes required.')
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
        raise ValueError('Saved design geometry/control changed.')
    return folder, info, dict(source=str(geometry), source_sha256=gh,
        generation_source=str(folder / 'generation.json'), generation_sha256=digest(folder / 'generation.json'),
        control_source=str(control), control_sha256=ch, parent_source=str(PARENT),
        parent_control_sha256=digest(PARENT / 'control_quad.npz'),
        parent_geometry_sha256=digest(PARENT / 'geometry.npz'),
        parent_generation_sha256=digest(PARENT / 'generation.json'))


def parent_state():
    info = read_json(PARENT / 'generation.json')
    gh, ch = digest(PARENT / 'geometry.npz'), digest(PARENT / 'control_quad.npz')
    if (info.get('candidate') != 'DEPTH_08' or info.get('input_case') != 'SPAN' or
        info.get('subdivision_generation') != 6 or gh != info['geometry_file_sha256'] or ch != info['control_file_sha256']):
        raise ValueError('Actual saved DEPTH_08 SPAN G6 required.')
    return info, dict(source=str(PARENT / 'geometry.npz'), source_sha256=gh,
        generation_source=str(PARENT / 'generation.json'), generation_sha256=digest(PARENT / 'generation.json'),
        control_source=str(PARENT / 'control_quad.npz'), control_sha256=ch)


def render_state(info, source, output, views, hashes):
    import bpy
    import numpy as np
    from mathutils import Vector
    shared_spec = importlib.util.spec_from_file_location('design_one_shared_scene', base.SHARED_RENDER)
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
        arrays = {key + '_sha256': hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()
                  for key, array in (('xyz', xyz), ('faces', faces))}
        if any(arrays[key + '_sha256'] != info['checks']['native_' + key + '_sha256'] for key in ('xyz', 'faces')):
            raise ValueError('Actual loaded native-array hashes differ.')
        mesh = bpy.data.meshes.new('Saved DESIGN_A native G6')
        mesh.vertices.add(len(xyz))
        mesh.vertices.foreach_set('co', np.asarray(xyz, np.float32).ravel())
        mesh.loops.add(3 * len(faces))
        mesh.loops.foreach_set('vertex_index', faces.ravel())
        mesh.polygons.add(len(faces))
        mesh.polygons.foreach_set('loop_start', np.arange(0, 3 * len(faces), 3, dtype=np.int32))
        mesh.polygons.foreach_set('loop_total', np.full(len(faces), 3, dtype=np.int32))
        mesh.update(calc_edges=True)
        obj = bpy.data.objects.new('Saved DESIGN_A native G6', mesh)
        bpy.context.collection.objects.link(obj)
        shared.material(obj)
    del xyz, faces
    scene, camera = shared.setup_scene(900, 24)
    conditions = base.actual_conditions(bpy, scene, camera, obj)
    require_close(conditions, base.expected_conditions())
    output.mkdir()
    actual_views, images = {}, []
    for name, (position, target, scale) in views.items():
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
    receipt = dict(candidate=info['candidate'], input_case='SPAN', source_generation=info['source_generation'], subdivision_generation=6,
        added_CC_passes=info['added_CC_passes'], version=bpy.app.version_string, views=views, actual_views=actual_views,
        conditions=conditions, code_sha256=hashes, source_arrays=arrays, images=images, **source,
        scope='Actual G6 plus topology events; saved native only; float32 display; no modifiers/maps or geometry certification.')
    (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    print('RENDERED', info['candidate'], 'SPAN G6', len(images), 'views', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    hashes = code_hashes()
    folder, info, source = source_state(args.root)
    reference = Path(args.root).resolve() / 'reference_views'
    if (folder / 'views').exists() or reference.exists():
        raise FileExistsError('Existing design/reference renders preserved.')
    parent_info, parent_source = parent_state()
    render_state(info, source, folder / 'views', VIEWS, hashes)
    render_state(parent_info, parent_source, reference, {k: v for k, v in VIEWS.items() if k != 'front'}, hashes)
    if source_state(args.root)[2] != source or parent_state()[1] != parent_source:
        raise ValueError('Saved states changed while rendering.')


if __name__ == '__main__':
    main()
