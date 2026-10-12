"""Render saved SIDEWALL_FAN G05 using the frozen connected-trial recipe.

Run with Blender, serially. This module never builds or edits research geometry.
The topology events precede two actual CC subdivisions; they do not increment G.
Copied from the frozen connected renderer; no research geometry is modified.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import sys

HERE = Path(__file__).resolve().parent
BROAD_RENDER = HERE.parent / 'broad_shoulder_folds_20261012/render.py'
SHARED_RENDER = HERE.parent / 'iaac_mandelbrot_20261011/render_shared.py'
FROZEN_RENDER = HERE.parent / 'connected_fold_growth_20261012/render.py'
FROZEN_RENDER_SHA256 = '7a6687b1f84997cbe83d93fb7036930dd37b143f8add97203926cea8e35480ce'
_spec = importlib.util.spec_from_file_location('sidewall_broad_render_recipe', BROAD_RENDER)
_broad = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_broad)
VIEWS = _broad.VIEWS
CASES = ('SPAN', 'COUNTER')
MODES = ('SIDEWALL_FAN',)
GENERATION = 5
RESOLUTION, SAMPLES = 900, 24
MATERIAL = 'Existing uniform mineral; flat geometric normals'


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def code_hashes():
    frozen = digest(FROZEN_RENDER)
    if frozen != FROZEN_RENDER_SHA256:
        raise ValueError('Frozen connected renderer changed; original reference receipts must remain reproducible.')
    return dict(render=digest(__file__), broad_camera_recipe=digest(BROAD_RENDER),
                shared_material_scene_recipe=digest(SHARED_RENDER), frozen_parent_renderer=frozen)


def expected_conditions():
    return dict(engine='CYCLES', resolution=[RESOLUTION, RESOLUTION],
        resolution_percentage=100, samples=SAMPLES, denoising=True,
        view_transform='AgX', image_format='PNG', camera_type='ORTHO',
        material_base_color=[.50, .47, .41, 1.], material_roughness=.84,
        smooth_polygons=0, modifiers=[], normal_maps=False,
        world_color=[.055, .063, .075, 1.], world_strength=.4,
        lights=dict(Key=dict(position=[-20, 25, 32], power=36000, size=17, shape='DISK'),
                    Fill=dict(position=[24, 13, 15], power=8500, size=18, shape='DISK'),
                    Rim=dict(position=[0, -23, 29], power=26000, size=13, shape='DISK')))


def require_close(actual, expected, label='conditions'):
    """Allow Blender float storage error, never missing keys or altered settings."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError('Different keys: ' + label)
        for key in expected:
            require_close(actual[key], expected[key], label + '.' + key)
    elif isinstance(expected, (list, tuple)):
        if not isinstance(actual, (list, tuple)) or len(actual) != len(expected):
            raise ValueError('Different sequence: ' + label)
        for index, (a, e) in enumerate(zip(actual, expected)):
            require_close(a, e, label + f'[{index}]')
    elif isinstance(expected, (float, int)) and not isinstance(expected, bool):
        if isinstance(actual, bool) or not isinstance(actual, (float, int)) or not math.isfinite(actual) or abs(actual - expected) > 2e-6:
            raise ValueError('Different numeric value: ' + label)
    elif actual != expected:
        raise ValueError('Different value: ' + label)


def source_state(root, mode, case):
    folder = Path(root).resolve() / mode / case / 'G05'
    geometry, metadata, control = folder / 'geometry.npz', folder / 'generation.json', folder / 'control_quad.npz'
    info = json.loads(metadata.read_text(encoding='utf8'))
    if (info.get('subdivision_generation') != GENERATION or info.get('source_generation') != 3 or
        info.get('neutral_CC_passes_added') != 2 or info.get('input_case') != case or
        info.get('candidate') != mode or
        info.get('native_surface') != 'Explicit arithmetic quad-centre fans'):
        raise ValueError('Matched case/mode and actual G3 plus two CC passes to native G05 required: ' + str(folder))
    geometry_hash, control_hash = digest(geometry), digest(control)
    if info.get('geometry_file_sha256') != geometry_hash or info.get('control_file_sha256') != control_hash:
        raise ValueError('Saved generation/geometry/control hashes differ: ' + str(folder))
    return folder, info, dict(source=str(geometry), source_sha256=geometry_hash,
        generation_source=str(metadata), generation_sha256=digest(metadata),
        control_source=str(control), control_sha256=control_hash)


def actual_conditions(bpy, scene, camera, obj):
    material = obj.data.materials[0]
    bsdf = material.node_tree.nodes.get('Principled BSDF')
    background = scene.world.node_tree.nodes.get('Background')
    mapped = (bsdf.inputs['Normal'].is_linked or
              material.node_tree.nodes.get('Material Output').inputs['Displacement'].is_linked or
              any(node.type in ('TEX_IMAGE', 'NORMAL_MAP', 'BUMP') for node in material.node_tree.nodes))
    lights = {}
    for name in ('Key', 'Fill', 'Rim'):
        light = scene.objects[name]
        lights[name] = dict(position=list(light.location), power=float(light.data.energy),
                            size=float(light.data.size), shape=light.data.shape)
    return dict(engine=scene.render.engine,
        resolution=[scene.render.resolution_x, scene.render.resolution_y],
        resolution_percentage=scene.render.resolution_percentage, samples=scene.cycles.samples,
        denoising=scene.cycles.use_denoising, view_transform=scene.view_settings.view_transform,
        image_format=scene.render.image_settings.file_format, camera_type=camera.data.type,
        material_base_color=list(bsdf.inputs['Base Color'].default_value),
        material_roughness=float(bsdf.inputs['Roughness'].default_value),
        smooth_polygons=sum(p.use_smooth for p in obj.data.polygons),
        modifiers=[item.type for item in obj.modifiers], normal_maps=bool(mapped),
        world_color=list(background.inputs[0].default_value),
        world_strength=float(background.inputs[1].default_value), lights=lights)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--case', nargs='+', choices=CASES, default=list(CASES))
    parser.add_argument('--mode', nargs='+', choices=MODES, default=list(MODES))
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    if len(set(args.case)) != len(args.case) or len(set(args.mode)) != len(args.mode):
        parser.error('Repeated cases/modes are not allowed.')
    prepared = []
    for case in args.case:
        for mode in args.mode:
            folder, info, source = source_state(args.root, mode, case)
            if (folder / 'views').exists():
                raise FileExistsError('Earlier render directory preserved: ' + str(folder / 'views'))
            prepared.append((case, mode, folder, info, source))
    import bpy
    import numpy as np
    from mathutils import Vector
    spec = importlib.util.spec_from_file_location('sidewall_shared_render_recipe', SHARED_RENDER)
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    hashes = code_hashes()
    for case, mode, folder, info, source in prepared:
        output = folder / 'views'
        output.mkdir()
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        for old_mesh in list(bpy.data.meshes):
            if old_mesh.users == 0:
                bpy.data.meshes.remove(old_mesh)
        with np.load(source['source'], allow_pickle=False) as data:
            xyz, triangles = data['xyz'], data['faces']
            if (xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all() or
                triangles.ndim != 2 or triangles.shape[1] != 3 or not len(triangles) or
                not np.issubdtype(triangles.dtype, np.integer) or triangles.min() < 0 or triangles.max() >= len(xyz)):
                raise ValueError('Finite native XYZ and indexed triangles required.')
            arrays = dict(xyz_sha256=hashlib.sha256(np.ascontiguousarray(xyz).tobytes()).hexdigest(),
                faces_sha256=hashlib.sha256(np.ascontiguousarray(triangles).tobytes()).hexdigest(),
                xyz_dtype=str(xyz.dtype), faces_dtype=str(triangles.dtype),
                xyz_shape=list(xyz.shape), faces_shape=list(triangles.shape))
            if (arrays['xyz_sha256'] != info['checks']['native_xyz_sha256'] or
                arrays['faces_sha256'] != info['checks']['native_faces_sha256']):
                raise ValueError('Actual native arrays differ from generation metadata.')
            mesh = bpy.data.meshes.new('Actual saved G05 native surface')
            mesh.vertices.add(len(xyz))
            mesh.vertices.foreach_set('co', np.asarray(xyz, np.float32).ravel())
            mesh.loops.add(3 * len(triangles))
            mesh.loops.foreach_set('vertex_index', triangles.ravel())
            mesh.polygons.add(len(triangles))
            mesh.polygons.foreach_set('loop_start', np.arange(0, 3 * len(triangles), 3, dtype=np.int32))
            mesh.polygons.foreach_set('loop_total', np.full(len(triangles), 3, dtype=np.int32))
            mesh.update(calc_edges=True)
            obj = bpy.data.objects.new('Actual saved G05 native surface', mesh)
            bpy.context.collection.objects.link(obj)
            shared.material(obj)
        scene, camera = shared.setup_scene(RESOLUTION, SAMPLES)
        conditions = actual_conditions(bpy, scene, camera, obj)
        require_close(conditions, expected_conditions())
        actual_views, images = {}, []
        for name, (position, target, scale) in VIEWS.items():
            camera.location = position
            camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
            camera.data.ortho_scale = scale
            forward = camera.rotation_euler.to_matrix() @ Vector((0, 0, -1))
            actual_views[name] = dict(position=list(camera.location), target=list(target),
                scale=float(camera.data.ortho_scale), forward=list(forward))
            expected_forward = list((Vector(target) - Vector(position)).normalized())
            require_close(actual_views[name], dict(position=list(position), target=list(target),
                scale=scale, forward=expected_forward), 'camera.' + name)
            path = output / f'{name}.png'
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            images.append(dict(view=name, filename=path.name, sha256=digest(path)))
        if (source['source_sha256'] != digest(source['source']) or
            source['generation_sha256'] != digest(source['generation_source']) or
            source['control_sha256'] != digest(source['control_source']) or hashes != code_hashes()):
            raise ValueError('Source or rendering code changed during rendering.')
        receipt = dict(input_case=case, candidate=mode, subdivision_generation=GENERATION,
            engine='Blender Cycles', version=bpy.app.version_string, resolution=RESOLUTION, samples=SAMPLES,
            views=VIEWS, actual_views=actual_views, material=MATERIAL, modifiers=[], normal_maps=False,
            conditions=conditions, code_sha256=hashes, render_script=str(Path(__file__).resolve()),
            render_script_sha256=hashes['render'], source_arrays=arrays, images=images, **source,
            constructive_event_count_quarter_accepted=info.get('constructive_event_count'),
            scope='Actual saved arithmetic quad-centre-fan native geometry; Blender display coordinates are float32; no geometry modifiers or maps',
            geometry_certification='Not performed by renderer; independent symmetry/topology verification remains separate')
        (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
        print('RENDERED', case, mode, 'G05', flush=True)


if __name__ == '__main__':
    main()
