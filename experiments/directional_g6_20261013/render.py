"""Render saved directional G06 variants only; root runs Blender serially."""
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
spec = importlib.util.spec_from_file_location('directional_g6_frozen_render', FROZEN_RENDER)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
digest, read_json, require_close = base.digest, base.read_json, base.require_close
CASES, MODES = ('SPAN', 'COUNTER'), ('DEPTH_08', 'DEPTH_16')
VIEWS = {key: base.VIEWS[key] for key in ('front', 'shoulder_oblique', 'shoulder_side')}
PARENT_ROOT = Path('E:/CHESHIRE_DATA/experiments/coherent_fold_detail_20261013/trial01')


def code_hashes():
    if digest(FROZEN_RENDER) != FROZEN_SHA256:
        raise ValueError('Frozen G05 renderer changed.')
    return dict(render=digest(__file__), frozen_renderer=digest(FROZEN_RENDER),
        broad_camera_recipe=digest(base.BROAD_RENDER), shared_material_scene_recipe=digest(base.SHARED_RENDER))


def source_state(root, mode, case):
    if mode not in MODES or case not in CASES:
        raise ValueError('Known G06 mode/case required.')
    root = Path(root).resolve()
    folder = root / mode / case / 'G06'
    info, recipe, index = (read_json(folder / 'generation.json'), read_json(root / 'RECIPE.json'),
                           read_json(root / 'source_index.json'))
    source = index[case]
    parent = PARENT_ROOT / 'DIRECTIONAL' / case / 'G05'
    if (recipe.get('cases') != list(CASES) or recipe.get('modes') != list(MODES) or
        info.get('subdivision_generation') != 6 or info.get('source_generation') != 5 or
        info.get('added_CC_passes') != 1 or info.get('input_case') != case or info.get('candidate') != mode or
        Path(source['path']).resolve() != parent.resolve() or
        Path(info.get('source', '')).resolve() != parent.resolve() or
        info.get('source_control_sha256') != source['control_sha256'] or
        not info.get('directional_rules') or info['directional_rules'] != recipe.get('directional_rules')):
        raise ValueError('Actual DIRECTIONAL G05 plus one saved G06 step required.')
    if (digest(parent / 'generation.json') != source['generation_sha256'] or
        digest(parent / 'control_quad.npz') != source['control_sha256']):
        raise ValueError('Actual frozen G05 parent changed.')
    code = info['geometry_code_sha256']
    if code != recipe['geometry_code_sha256'] or not code:
        raise ValueError('Current geometry-code binding required.')
    for name, checksum in code.items():
        path = (REPO / name).resolve()
        if not path.is_relative_to(REPO.resolve()) or digest(path) != checksum:
            raise ValueError('Generation code changed: ' + name)
    geometry, control = folder / 'geometry.npz', folder / 'control_quad.npz'
    geometry_hash, control_hash = digest(geometry), digest(control)
    if geometry_hash != info['geometry_file_sha256'] or control_hash != info['control_file_sha256']:
        raise ValueError('Saved geometry/control changed.')
    return folder, info, dict(source=str(geometry), source_sha256=geometry_hash,
        generation_source=str(folder / 'generation.json'), generation_sha256=digest(folder / 'generation.json'),
        control_source=str(control), control_sha256=control_hash,
        parent_control_sha256=source['control_sha256'], parent_generation_sha256=source['generation_sha256'],
        recipe_sha256=digest(root / 'RECIPE.json'), source_index_sha256=digest(root / 'source_index.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--case', nargs='+', choices=CASES, default=list(CASES))
    parser.add_argument('--mode', nargs='+', choices=MODES, default=list(MODES))
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    if len(set(args.case)) != len(args.case) or len(set(args.mode)) != len(args.mode):
        parser.error('Repeated modes/cases are not allowed.')
    import bpy
    import numpy as np
    from mathutils import Vector
    shared_spec = importlib.util.spec_from_file_location('directional_g6_shared_scene', base.SHARED_RENDER)
    shared = importlib.util.module_from_spec(shared_spec)
    shared_spec.loader.exec_module(shared)
    hashes = code_hashes()
    for case in args.case:
        for mode in args.mode:
            folder, info, source = source_state(args.root, mode, case)
            output = folder / 'views'
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
                if arrays['xyz_sha256'] != info['checks']['native_xyz_sha256'] or arrays['faces_sha256'] != info['checks']['native_faces_sha256']:
                    raise ValueError('Actual loaded native-array hashes differ.')
                mesh = bpy.data.meshes.new('Saved directional G06 native')
                mesh.vertices.add(len(xyz))
                mesh.vertices.foreach_set('co', np.asarray(xyz, np.float32).ravel())
                mesh.loops.add(3 * len(faces))
                mesh.loops.foreach_set('vertex_index', faces.ravel())
                mesh.polygons.add(len(faces))
                mesh.polygons.foreach_set('loop_start', np.arange(0, 3 * len(faces), 3, dtype=np.int32))
                mesh.polygons.foreach_set('loop_total', np.full(len(faces), 3, dtype=np.int32))
                mesh.update(calc_edges=True)
                obj = bpy.data.objects.new('Saved directional G06 native', mesh)
                bpy.context.collection.objects.link(obj)
                shared.material(obj)
            del xyz, faces
            scene, camera = shared.setup_scene(900, 24)
            conditions = base.actual_conditions(bpy, scene, camera, obj)
            require_close(conditions, base.expected_conditions())
            output.mkdir()
            actual_views, images = {}, []
            for name, (position, target, scale) in VIEWS.items():
                camera.location = position
                camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
                camera.data.ortho_scale = scale
                actual_views[name] = dict(position=list(camera.location), target=list(target),
                    scale=float(camera.data.ortho_scale), forward=list(camera.rotation_euler.to_matrix() @ Vector((0, 0, -1))))
                require_close(actual_views[name], dict(position=list(position), target=list(target), scale=scale,
                    forward=list((Vector(target) - Vector(position)).normalized())), 'camera.' + name)
                path = output / (name + '.png')
                scene.render.filepath = str(path)
                bpy.ops.render.render(write_still=True)
                images.append(dict(view=name, filename=path.name, sha256=digest(path)))
            if source_state(args.root, mode, case)[2] != source or code_hashes() != hashes:
                raise ValueError('Source or code changed while rendering.')
            receipt = dict(input_case=case, candidate=mode, subdivision_generation=6, source_generation=5,
                version=bpy.app.version_string, views=VIEWS, actual_views=actual_views, conditions=conditions,
                code_sha256=hashes, source_arrays=arrays, images=images, **source,
                scope='Saved native only; Blender float32 display coordinates; no modifiers/maps; no geometry certification.')
            (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
            print('RENDERED', case, mode, 'G06', flush=True)


if __name__ == '__main__':
    main()
