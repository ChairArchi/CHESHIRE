"""Render three saved coherent-rule G05 candidates under frozen conditions.

One actual CC step takes frozen SIDEWALL_FAN G04 to G05. The old COMBINED
baseline reuses eight original PNGs and is never rendered here. No research
geometry is built or edited. Root runs Blender serially.
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
FROZEN_SIDEWALL_RENDER = HERE.parent / 'sidewall_fan_growth_20261013/render.py'
FROZEN_SIDEWALL_RENDER_SHA256 = '46dca7265908aeff47185a3434ff4b160727a169bb497c3a75c0cd87f4874251'
FROZEN_LATE_RENDER = HERE.parent / 'late_detail_rules_20261013/render.py'
FROZEN_LATE_RENDER_SHA256 = '1f6e7afc25fd8303b954b38a672587f55ca564af1a2b18fe8a7b29b0cb1d4586'
PARENT_ROOT = Path('E:/CHESHIRE_DATA/experiments/sidewall_fan_growth_20261013/trial01')
BASELINE_ROOT = Path('E:/CHESHIRE_DATA/experiments/late_detail_rules_20261013/trial01')
REPO = HERE.parents[1]
_spec = importlib.util.spec_from_file_location('coherent_detail_broad_render_recipe', BROAD_RENDER)
_broad = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_broad)
VIEWS = _broad.VIEWS
CASES = ('SPAN', 'COUNTER')
MODES = ('COHERENT', 'DIRECTIONAL', 'ROLE_CURVATURE')
RENDER_MODES = MODES
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
    sidewall = digest(FROZEN_SIDEWALL_RENDER)
    if sidewall != FROZEN_SIDEWALL_RENDER_SHA256:
        raise ValueError('Frozen sidewall renderer changed.')
    late = digest(FROZEN_LATE_RENDER)
    if late != FROZEN_LATE_RENDER_SHA256:
        raise ValueError('Frozen late-detail baseline renderer changed.')
    return dict(render=digest(__file__), broad_camera_recipe=digest(BROAD_RENDER),
                shared_material_scene_recipe=digest(SHARED_RENDER), frozen_parent_renderer=frozen,
                frozen_sidewall_renderer=sidewall, frozen_late_renderer=late)


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


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def checked_stage(source, generation, case):
    folder = Path(source['path']).resolve()
    info = read_json(folder / 'generation.json')
    if (info.get('subdivision_generation') != generation or info.get('input_case') != case or
        info.get('candidate') != 'SIDEWALL_FAN' or
        source.get('generation_sha256') != digest(folder / 'generation.json')):
        raise ValueError('Frozen stage identity differs: ' + str(folder))
    for filename, key, metadata_key in (
        ('control_quad.npz', 'control_sha256', 'control_file_sha256'),
        ('geometry.npz', 'geometry_sha256', 'geometry_file_sha256'),
        ('evidence.npz', 'evidence_sha256', 'evidence_file_sha256')):
        checksum = digest(folder / filename)
        if checksum != source[key] or checksum != info[metadata_key]:
            raise ValueError('Frozen parent stage changed: ' + str(folder / filename))
    return info


def checked_baseline(source, case):
    """Bind the reused COMBINED source to actual old geometry/render PASS."""
    stage = source['baseline']
    folder = Path(stage['path']).resolve()
    if folder != (BASELINE_ROOT / 'COMBINED' / case / 'G05').resolve():
        raise ValueError('Unexpected frozen COMBINED baseline path.')
    info = read_json(folder / 'generation.json')
    if (info.get('candidate') != 'COMBINED' or info.get('input_case') != case or
        info.get('subdivision_generation') != 5 or info.get('source_generation') != 4 or
        info.get('source_control_sha256') != source['control_sha256'] or
        Path(info.get('source', '')).resolve() != Path(source['path']).resolve() or
        info.get('preserved_parent', {}).get('generation_sha256') != source['generation_sha256'] or
        digest(folder / 'generation.json') != stage['generation_sha256']):
        raise ValueError('Frozen COMBINED baseline does not bind the same actual G04.')
    for filename, key, metadata_key in (
        ('control_quad.npz', 'control_sha256', 'control_file_sha256'),
        ('geometry.npz', 'geometry_sha256', 'geometry_file_sha256'),
        ('evidence.npz', 'evidence_sha256', 'evidence_file_sha256')):
        checksum = digest(folder / filename)
        if checksum != stage[key] or checksum != info[metadata_key]:
            raise ValueError('Frozen COMBINED source changed: ' + filename)
    documents = {}
    for key, name in (('baseline_verification', 'VERIFICATION.json'),
                      ('baseline_render_verification', 'RENDER_VERIFICATION.json')):
        path = Path(source[key]).resolve()
        if path != (BASELINE_ROOT / name).resolve() or digest(path) != source[key + '_sha256']:
            raise ValueError('Frozen baseline receipt changed: ' + name)
        documents[name] = read_json(path)
    proof = documents['VERIFICATION.json']
    modes = ['NEUTRAL', 'EQ4_ONLY', 'NORMAL_ONLY', 'COMBINED']
    if (proof.get('status') != 'PASS' or proof.get('expected_cases') != list(CASES) or
        proof.get('expected_modes') != modes or proof['cases'][case].get('passed') is not True):
        raise ValueError('Frozen complete independent baseline PASS required.')
    actual = proof['cases'][case]['states']['COMBINED']
    keys = ('control_xyz_sha256', 'control_faces_sha256', 'chart_sha256',
            'native_xyz_sha256', 'native_faces_sha256')
    if (actual.get('passed') is not True or actual.get('generation_json_sha256') != stage['generation_sha256'] or
        actual.get('actual_native_topology', {}).get('passed') is not True or
        any(actual.get('actual_native_symmetry', {}).get(axis, {}).get('passed') is not True for axis in ('X', 'Y')) or
        any(actual.get('hashes', {}).get(key) != info['checks'][key] for key in keys)):
        raise ValueError('Frozen actual COMBINED topology/symmetry/replay binding differs.')
    rendered = documents['RENDER_VERIFICATION.json']
    if (rendered.get('passed') is not True or rendered.get('expected_cases') != list(CASES) or
        rendered.get('expected_modes') != modes or rendered.get('source_images') != 32 or
        rendered.get('independent_geometry_verification_sha256') != source['baseline_verification_sha256']):
        raise ValueError('Frozen complete baseline render correspondence PASS required.')
    matches = [s for s in rendered.get('states', []) if s.get('input_case') == case and s.get('candidate') == 'COMBINED']
    if len(matches) != 1:
        raise ValueError('One exact COMBINED image-source entry required.')
    state = matches[0]
    if (state.get('generation_sha256') != stage['generation_sha256'] or
        state.get('geometry_sha256') != stage['geometry_sha256'] or
        state.get('control_sha256') != stage['control_sha256'] or
        state.get('independent_geometry_generation_sha256') != stage['generation_sha256'] or
        Path(state.get('geometry', '')).resolve() != (folder / 'geometry.npz').resolve() or
        state.get('native_arrays', {}).get('xyz_sha256') != info['checks']['native_xyz_sha256'] or
        state.get('native_arrays', {}).get('faces_sha256') != info['checks']['native_faces_sha256']):
        raise ValueError('Frozen baseline render source differs from actual PASS state.')
    return info


def bound_parent(root, case):
    root = Path(root).resolve()
    recipe_path, index_path = root / 'RECIPE.json', root / 'source_index.json'
    recipe, index = read_json(recipe_path), read_json(index_path)
    if (recipe.get('cases') != list(CASES) or recipe.get('modes') != list(MODES) or
        recipe.get('source_generation') != 4 or recipe.get('final_generation') != 5 or
        recipe.get('added_CC_passes') != 1 or set(index) != set(CASES) or
        Path(recipe.get('preserved_parent_root', '')).resolve() != PARENT_ROOT.resolve() or
        Path(recipe.get('frozen_baseline_root', '')).resolve() != BASELINE_ROOT.resolve()):
        raise ValueError('Complete two-input three-mode G04-to-G05 recipe/source index required.')
    source = index[case]
    stages = ((3, source['g3'], 'G03_events'), (4, source, 'G04'), (5, source['neutral'], 'G05'))
    for generation, stage, name in stages:
        if Path(stage['path']).resolve() != (PARENT_ROOT / 'SIDEWALL_FAN' / case / name).resolve():
            raise ValueError('Unexpected frozen SIDEWALL_FAN lineage path.')
        checked_stage(stage, generation, case)
    verification_path, parent_recipe_path = Path(source['parent_verification']), Path(source['parent_recipe'])
    if (verification_path.resolve() != (PARENT_ROOT / 'VERIFICATION.json').resolve() or
        parent_recipe_path.resolve() != (PARENT_ROOT / 'RECIPE.json').resolve() or
        digest(verification_path) != source['parent_verification_sha256'] or
        digest(parent_recipe_path) != source['parent_recipe_sha256']):
        raise ValueError('Frozen parent verification/recipe changed.')
    verification = read_json(verification_path)
    if (verification.get('status') != 'PASS' or verification.get('expected_cases') != list(CASES) or
        verification.get('expected_modes') != ['SIDEWALL_FAN']):
        raise ValueError('Frozen complete parent verification PASS required.')
    proofs = verification['cases'][case]['stages']
    if len(proofs) != 3:
        raise ValueError('Exactly three bound frozen parent stages required.')
    for (generation, stage, _), proof in zip(stages, proofs):
        if (proof.get('passed') is not True or proof['semantics']['actual_generation'] != generation or
            proof.get('generation_json_sha256') != stage['generation_sha256']):
            raise ValueError('Frozen parent PASS-stage binding differs.')
    code = recipe['geometry_code_sha256']
    parent_code = read_json(parent_recipe_path)['geometry_code_sha256']
    if any(code.get(name) != checksum for name, checksum in parent_code.items()):
        raise ValueError('Inherited frozen geometry code differs.')
    for name, checksum in code.items():
        path = (REPO / name).resolve()
        if not path.is_relative_to(REPO.resolve()) or digest(path) != checksum:
            raise ValueError('Generation code changed: ' + name)
    baseline = checked_baseline(source, case)
    provenance = dict(recipe_source=str(recipe_path), recipe_sha256=digest(recipe_path),
        source_index_source=str(index_path), source_index_sha256=digest(index_path),
        parent_control_source=str(Path(source['path']) / 'control_quad.npz'),
        parent_control_sha256=source['control_sha256'],
        parent_generation_source=str(Path(source['path']) / 'generation.json'),
        parent_generation_sha256=source['generation_sha256'],
        parent_verification_source=str(verification_path), parent_verification_sha256=digest(verification_path),
        baseline_generation_source=str(Path(source['baseline']['path']) / 'generation.json'),
        baseline_generation_sha256=source['baseline']['generation_sha256'],
        baseline_verification_source=source['baseline_verification'],
        baseline_verification_sha256=source['baseline_verification_sha256'],
        baseline_render_verification_source=source['baseline_render_verification'],
        baseline_render_verification_sha256=source['baseline_render_verification_sha256'])
    return source, recipe, provenance


def source_state(root, mode, case):
    if mode not in MODES or case not in CASES:
        raise ValueError('Known coherent-rule mode/case required.')
    folder = Path(root).resolve() / mode / case / 'G05'
    geometry, metadata, control = folder / 'geometry.npz', folder / 'generation.json', folder / 'control_quad.npz'
    info = read_json(metadata)
    source, recipe, provenance = bound_parent(root, case)
    if (info.get('subdivision_generation') != 5 or info.get('source_generation') != 4 or
        info.get('added_CC_passes') != 1 or info.get('added_topology_events') != 0 or
        info.get('source_surface') != 'mean' or info.get('input_case') != case or info.get('candidate') != mode or
        info.get('native_surface') != 'Explicit arithmetic quad-centre fans' or
        Path(info.get('source', '')).resolve() != Path(source['path']).resolve() or
        info.get('source_control_sha256') != source['control_sha256'] or
        info.get('preserved_parent') != source or info.get('geometry_code_sha256') != recipe['geometry_code_sha256'] or
        info.get('coherent_rules') != recipe.get('coherent_rules') or not recipe.get('coherent_rules')):
        raise ValueError('Bound frozen G04 plus one actual CC to native G05 required: ' + str(folder))
    geometry_hash, control_hash = digest(geometry), digest(control)
    if info.get('geometry_file_sha256') != geometry_hash or info.get('control_file_sha256') != control_hash:
        raise ValueError('Saved generation/geometry/control hashes differ: ' + str(folder))
    return folder, info, dict(source=str(geometry), source_sha256=geometry_hash,
        generation_source=str(metadata), generation_sha256=digest(metadata),
        control_source=str(control), control_sha256=control_hash, **provenance)


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
    parser.add_argument('--mode', nargs='+', choices=RENDER_MODES, default=list(RENDER_MODES))
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
    spec = importlib.util.spec_from_file_location('coherent_detail_shared_render_recipe', SHARED_RENDER)
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
        if source_state(args.root, mode, case)[2] != source or hashes != code_hashes():
            raise ValueError('Source or rendering code changed during rendering.')
        receipt = dict(input_case=case, candidate=mode, subdivision_generation=GENERATION,
            engine='Blender Cycles', version=bpy.app.version_string, resolution=RESOLUTION, samples=SAMPLES,
            views=VIEWS, actual_views=actual_views, material=MATERIAL, modifiers=[], normal_maps=False,
            conditions=conditions, code_sha256=hashes, render_script=str(Path(__file__).resolve()),
            render_script_sha256=hashes['render'], source_arrays=arrays, images=images, **source,
            source_generation=4, added_CC_passes=1, added_topology_events=0,
            scope='Actual saved arithmetic quad-centre-fan native geometry; Blender display coordinates are float32; no geometry modifiers or maps',
            geometry_certification='Not performed by renderer; independent symmetry/topology verification remains separate')
        (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
        print('RENDERED', case, mode, 'G05', flush=True)


if __name__ == '__main__':
    main()
