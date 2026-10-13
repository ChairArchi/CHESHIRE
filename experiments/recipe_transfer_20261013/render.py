"""Render saved recipe-transfer stages only; each invocation loads one native mesh.

G numbers are actual subdivision counts. This renderer neither generates nor
refines geometry. The root runner supplies the metadata-bound STAGES.json.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/recipe_transfer_20261013/trial01')
FROZEN_RENDER = HERE.parent / 'coherent_fold_detail_20261013/render.py'
FROZEN_SHA256 = 'fcea58674b2d8b000a4d626c27f503fb5e01d0553993105336e3fbf325d4f237'
SHARED_SHA256 = '0eb6acf7c088ffc77797e3271504f2f3745f269d9600c8d0181f396c36a26031'
BROAD_SHA256 = 'f8a290812b64104b957016a6aa8ab97ab60566dcf2ffac54f0b5db99f53a1e91'
spec = importlib.util.spec_from_file_location('recipe_transfer_frozen_scene_checks', FROZEN_RENDER)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
digest, read_json, require_close = base.digest, base.read_json, base.require_close

STAGES = ('G00_INPUT', 'G01_ANCESTRY', 'G02_OVERLAP', 'G03_SIDEWALL',
          'G04_NEUTRAL', 'G05_DIRECTIONAL', 'G06_MIDDLE', 'G07_FINAL')
GENERATIONS = dict(zip(STAGES, range(8)))
FINAL = 'G07_FINAL'
VIEWS = dict(front=((0, 32, 5), (0, 0, 5), 12.),
             whole_oblique=((-18, 28, 12), (0, 0, 5), 12.),
             body_oblique=((-18, 28, 12), (0, 0, 6.25), 4.3),
             close_oblique=((-18, 28, 12), (-.6, .72, 6.6), 1.25))
PROGRESSION_VIEWS = ('front', 'whole_oblique')
COMPARISON_VIEWS = ('front', 'body_oblique', 'close_oblique')
COUNT_KEYS = ('source_generation', 'added_CC_passes', 'added_field_passes',
              'field_passes_total', 'field_iterations', 'added_normal_field_passes',
              'added_normal_field_passes_this_finish', 'cumulative_normal_field_passes',
              'smoothing_passes', 'finish_smoothing_passes')


def code_hashes():
    for path, expected in ((FROZEN_RENDER, FROZEN_SHA256),
                           (base.SHARED_RENDER, SHARED_SHA256),
                           (base.BROAD_RENDER, BROAD_SHA256)):
        if digest(path) != expected:
            raise ValueError('Frozen material/scene/checker changed: ' + str(path))
    return dict(render=digest(__file__), frozen_renderer=FROZEN_SHA256,
                shared_material_scene_recipe=SHARED_SHA256, broad_camera_recipe=BROAD_SHA256)


def stage_views(stage):
    return dict(VIEWS) if stage == FINAL else {name: VIEWS[name] for name in PROGRESSION_VIEWS}


def manifest(root):
    root = Path(root).resolve()
    path = root / 'STAGES.json'
    document = read_json(path)
    items = document if isinstance(document, list) else document['stages']
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise ValueError('Ordered stage records required.')
    ids = [item['id'] for item in items]
    if len(set(ids)) != len(ids) or any(stage not in ids for stage in STAGES):
        raise ValueError('Eight distinct selected G0-G7 stages required.')
    selected = [item['id'] for item in items if item['id'] in STAGES]
    if selected != list(STAGES):
        raise ValueError('Selected subdivision stages must be ordered G0 through G7.')
    return {item['id']: item for item in items}, dict(
        manifest_source=str(path), manifest_sha256=digest(path))


def saved_state(folder, info):
    """Bind the actual saved files and their code; no mesh arrays are loaded."""
    code = info.get('geometry_code_sha256', {})
    if not code or info.get('checks', {}).get('passed') is not True:
        raise ValueError('Saved generation code and passed mesh checks required.')
    for name, expected in code.items():
        path = (REPO / name).resolve()
        if not path.is_relative_to(REPO.resolve()) or digest(path) != expected:
            raise ValueError('Saved generation code changed: ' + name)
    geometry, control = folder / 'geometry.npz', folder / 'control_quad.npz'
    gh, ch = digest(geometry), digest(control)
    if gh != info['geometry_file_sha256'] or ch != info['control_file_sha256']:
        raise ValueError('Saved native/control files changed: ' + str(folder))
    if any(not isinstance(info['checks'].get('native_' + key + '_sha256'), str)
           for key in ('xyz', 'faces')):
        raise ValueError('Saved native-array hashes required.')
    return dict(source=str(geometry), source_sha256=gh,
                generation_source=str(folder / 'generation.json'),
                generation_sha256=digest(folder / 'generation.json'),
                control_source=str(control), control_sha256=ch)


def source_state(root, stage):
    if stage not in STAGES:
        raise ValueError('Selected stage required.')
    root = Path(root).resolve()
    index, binding = manifest(root)
    item = index[stage]
    folder = (root / item['folder']).resolve()
    if folder != root / 'states' / stage:
        raise ValueError('Stage must use its declared new trial states folder.')
    info = read_json(folder / 'generation.json')
    if (item.get('generation') != GENERATIONS[stage] or
        info.get('subdivision_generation') != GENERATIONS[stage] or
        info.get('input_case') != 'WAIST_FULL' or not info.get('candidate') or
        item.get('generation_json_sha256') != digest(folder / 'generation.json')):
        raise ValueError('Stage identity, actual subdivision count or manifest binding differs.')
    source = saved_state(folder, info)
    source.update(stage_id=stage, **binding)
    return folder, info, source


def render_state(info, source, output, views, hashes):
    import bpy
    import numpy as np
    from mathutils import Vector
    shared_spec = importlib.util.spec_from_file_location('recipe_transfer_shared_scene', base.SHARED_RENDER)
    shared = importlib.util.module_from_spec(shared_spec)
    shared_spec.loader.exec_module(shared)
    if output.exists():
        raise FileExistsError('Existing native render preserved: ' + str(output))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for old_mesh in list(bpy.data.meshes):
        if old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
    with np.load(source['source'], allow_pickle=False) as data:
        xyz, faces = data['xyz'], data['faces']
        if (xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all() or
            faces.ndim != 2 or faces.shape[1] != 3 or not len(faces) or
            not np.issubdtype(faces.dtype, np.integer) or faces.min() < 0 or faces.max() >= len(xyz)):
            raise ValueError('Finite saved native XYZ and indexed triangles required.')
        arrays = {key + '_sha256': hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast('B')).hexdigest()
                  for key, array in (('xyz', xyz), ('faces', faces))}
        if any(arrays[key + '_sha256'] != info['checks']['native_' + key + '_sha256']
               for key in ('xyz', 'faces')):
            raise ValueError('Loaded native-array hashes differ from saved generation.')
        vertex_count, face_count = len(xyz), len(faces)
        mesh = bpy.data.meshes.new('Saved recipe-transfer native ' + source['stage_id'])
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
        obj = bpy.data.objects.new('Saved recipe-transfer native ' + source['stage_id'], mesh)
        bpy.context.collection.objects.link(obj)
        shared.material(obj)
    scene, camera = shared.setup_scene(900, 24)
    conditions = base.actual_conditions(bpy, scene, camera, obj)
    require_close(conditions, base.expected_conditions())
    output.mkdir()
    actual_views, images = {}, []
    for name, (position, target, scale) in views.items():
        camera.location = position
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        actual_views[name] = dict(position=list(camera.location), target=list(target),
                                 scale=float(camera.data.ortho_scale),
                                 forward=list(camera.rotation_euler.to_matrix() @ Vector((0, 0, -1))))
        require_close(actual_views[name], dict(position=list(position), target=list(target), scale=scale,
            forward=list((Vector(target) - Vector(position)).normalized())), 'camera.' + name)
        path = output / (name + '.png')
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        images.append(dict(view=name, filename=path.name, sha256=digest(path)))
    if (any(digest(source[key]) != source[checksum] for key, checksum in (
            ('source', 'source_sha256'), ('control_source', 'control_sha256'),
            ('generation_source', 'generation_sha256'), ('manifest_source', 'manifest_sha256')))
            or code_hashes() != hashes):
        raise ValueError('Saved source, manifest or renderer changed during rendering.')
    receipt = dict(candidate=info['candidate'], input_case=info['input_case'],
        subdivision_generation=info['subdivision_generation'],
        operation_counts={key: info[key] for key in COUNT_KEYS if key in info},
        native_vertices=vertex_count, native_triangles=face_count,
        version=bpy.app.version_string, views=views, actual_views=actual_views,
        conditions=conditions, code_sha256=hashes, source_arrays=arrays, images=images, **source,
        scope='Actual saved input-transfer stages; G is subdivision, not field iteration. Native arrays only; float32 display; no geometry modifiers, maps, smooth shading or geometry/aesthetic certification.')
    (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    print('RENDERED', source['stage_id'], 'actual G' + str(info['subdivision_generation']), len(images), 'views', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--stage', choices=STAGES, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    hashes = code_hashes()
    folder, info, source = source_state(args.root, args.stage)
    render_state(info, source, folder / 'views', stage_views(args.stage), hashes)
    if source_state(args.root, args.stage)[2] != source:
        raise ValueError('Saved stage changed while rendering.')


if __name__ == '__main__':
    main()
