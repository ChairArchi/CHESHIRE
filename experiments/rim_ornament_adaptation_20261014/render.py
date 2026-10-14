"""Render three saved rim additions with one unchanged G7 body and a real macro view."""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import math
import shutil
import sys

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/rim_ornament_adaptation_20261014/trial01')
VARIANTS = ('MANDEL_RIBBON', 'LEAF_FAN', 'HYBRID')
NATIVE_RENDERER = HERE.parent / 'local_ornament_comparison_20261014/render.py'
NATIVE_RENDERER_SHA256 = '2e3246c8311ee9bedd3b387861d3f2abd5134b6b3440c7a232d63ceefac0f78e'
spec = importlib.util.spec_from_file_location('rim_ornament_preserved_native_renderer', NATIVE_RENDERER)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
digest, read_json, require_close = native.digest, native.read_json, native.require_close
SOURCE, VIEWS, base, prior, helper = native.SOURCE, native.VIEWS, native.base, native.prior, native.helper
SOURCE_GEOMETRY_SHA256 = native.SOURCE_GEOMETRY_SHA256
add_native_object, body_signature = native.add_native_object, native.body_signature


def code_hashes():
    if digest(NATIVE_RENDERER) != NATIVE_RENDERER_SHA256:
        raise ValueError('Preserved native addition renderer changed.')
    return dict(render=digest(__file__), preserved_native_renderer=NATIVE_RENDERER_SHA256,
                preserved_native_code=native.code_hashes())


def source_state(root):
    root = Path(root).resolve()
    if root == SOURCE.resolve() or SOURCE.resolve() in root.parents:
        raise ValueError('Original SPAN source is read-only.')
    info, placement = read_json(root / 'RECEIPT.json'), read_json(root / 'PLACEMENT.json')
    parent_info, parent_source = helper.parent_state()
    if (info.get('source_native_geometry_sha256') != SOURCE_GEOMETRY_SHA256 or
            Path(info.get('source_native_path', '')).resolve() != Path(parent_source['source']).resolve() or
            parent_source['source_sha256'] != SOURCE_GEOMETRY_SHA256 or
            info.get('placement_sha256') != digest(root / 'PLACEMENT.json')):
        raise ValueError('Actual original G7 and saved placement binding required.')
    variants = info.get('variants')
    if not isinstance(variants, dict) or set(variants) != set(VARIANTS):
        raise ValueError('Exactly three actual saved rim-addition variants required.')
    for name in VARIANTS:
        path = root / name / 'geometry.npz'
        if (Path(variants[name].get('geometry', '')).resolve() != path.resolve() or
                digest(path) != variants[name]['geometry_sha256']):
            raise ValueError('Actual saved added geometry differs: ' + name)
        for key in ('xyz_sha256', 'faces_sha256'):
            value = variants[name].get(key)
            if not isinstance(value, str) or len(value) != 64:
                raise ValueError('Actual added array hash required: ' + name + '.' + key)
    all_views(placement)
    binding = dict(root=str(root), receipt=str(root / 'RECEIPT.json'),
        receipt_sha256=digest(root / 'RECEIPT.json'), placement=str(root / 'PLACEMENT.json'),
        placement_sha256=digest(root / 'PLACEMENT.json'), original_source=parent_source)
    return info, placement, parent_info, parent_source, binding


def all_views(placement):
    saved_camera = placement.get('macro_camera', {})
    macro = placement.get('macro_view') or dict(position=saved_camera.get('position'),
        target=saved_camera.get('target'), scale=saved_camera.get('ortho'))
    if not isinstance(macro, dict) or any(key not in macro for key in ('position', 'target', 'scale')):
        raise ValueError('Actual selected-end macro camera required in saved PLACEMENT.')
    for key in ('position', 'target'):
        values = macro[key]
        if (not isinstance(values, list) or len(values) != 3 or
                any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values)):
            raise ValueError('Invalid actual macro camera: ' + key)
    scale = macro['scale']
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0:
        raise ValueError('Positive finite actual macro ortho scale required.')
    if sum((a - b) ** 2 for a, b in zip(macro['position'], macro['target'])) < 1e-12:
        raise ValueError('Macro camera position and target must be distinct.')
    return {**VIEWS, 'macro': (macro['position'], macro['target'], scale)}


def snapshot_sources(root):
    records = []
    for name in ('render.py', 'boards.py'):
        source = HERE / name
        relative = Path('experiments') / HERE.name / name
        target = Path(root) / 'source_snapshot_render' / relative
        checksum = digest(source)
        if target.exists():
            if digest(target) != checksum:
                raise ValueError('Earlier rendering snapshot differs.')
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        records.append(dict(source=str(source), relative_path=relative.as_posix(),
                            snapshot=str(target), sha256=checksum))
    verify_snapshots(records)
    return records


def verify_snapshots(records):
    expected = {f'experiments/{HERE.name}/{name}': digest(HERE / name) for name in ('render.py', 'boards.py')}
    if (not isinstance(records, list) or len(records) != 2 or
            {item['relative_path']: item['sha256'] for item in records} != expected):
        raise ValueError('Actual rendering scripts differ from the two saved snapshots.')
    for item in records:
        if any(digest(item[key]) != item['sha256'] for key in ('source', 'snapshot')):
            raise ValueError('Rendering source/snapshot changed.')


def render_views(scene, camera, views, output):
    import bpy
    from mathutils import Vector
    output.mkdir(parents=True, exist_ok=False)
    actual_views, images = {}, []
    for view, (position, target, scale) in views.items():
        camera.location = position
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        actual_views[view] = dict(position=list(camera.location), target=list(target), scale=float(camera.data.ortho_scale),
            forward=list(camera.rotation_euler.to_matrix() @ Vector((0, 0, -1))))
        require_close(actual_views[view], dict(position=list(position), target=list(target), scale=scale,
            forward=list((Vector(target) - Vector(position)).normalized())), 'camera.' + view)
        png = output / (view + '.png')
        scene.render.filepath = str(png)
        bpy.ops.render.render(write_still=True)
        images.append(dict(view=view, filename=png.name, sha256=digest(png)))
    return actual_views, images


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    if any((root / name / 'views').exists() for name in ('ORIGINAL_G7', *VARIANTS)):
        raise FileExistsError('Earlier actual variant/macro renders preserved.')
    hashes = code_hashes()
    info, placement, parent_info, parent_source, binding = source_state(root)
    snapshots, views = snapshot_sources(root), all_views(placement)
    spec = importlib.util.spec_from_file_location('rim_ornament_frozen_scene', base.SHARED_RENDER)
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for previous in list(bpy.data.meshes):
        if previous.users == 0:
            bpy.data.meshes.remove(previous)
    expected_body = dict(geometry_sha256=SOURCE_GEOMETRY_SHA256,
        xyz_sha256=parent_info['checks']['native_xyz_sha256'],
        faces_sha256=parent_info['checks']['native_faces_sha256'])
    body, body_counts = add_native_object(Path(parent_source['source']), expected_body, 'Immutable original SPAN G7', shared)
    original_mesh_pointer = body.data.as_pointer()
    scene, camera = shared.setup_scene(900, 24)
    conditions = base.actual_conditions(bpy, scene, camera, body)
    require_close(conditions, base.expected_conditions())
    common = dict(binding=binding, original_body=parent_source, original_body_counts=body_counts,
        original_body_loaded_once=True, original_body_unchanged_in_blender=True,
        body_geometry_processing=False, added_geometry_processing=False, modifiers=[], smooth_shading=False,
        source_growth_generation=7, new_source_growth_G8=False, fusion_performed=False,
        version=bpy.app.version_string, conditions=conditions, code_sha256=hashes,
        render_source_snapshots=snapshots)
    original_output = root / 'ORIGINAL_G7/views'
    actual_views, images = render_views(scene, camera, {'macro': views['macro']}, original_output)
    actual_body = body_signature(body, body_counts)
    original_receipt = dict(common, candidate='ORIGINAL_G7', kind='ORIGINAL_G7_REAL_MACRO_REFERENCE',
        saved_placement=placement, original_body_display_readback=actual_body,
        views={'macro': views['macro']}, actual_views=actual_views, images=images,
        scope='New actual macro render of the unchanged original native G7 body; no ornament, modifier, smoothing, remesh, subdivision, image crop or synthesis.')
    (original_output / 'receipt.json').write_text(json.dumps(original_receipt, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    print('RIM_ORNAMENT_RENDERED ORIGINAL_G7 macro; original body retained', flush=True)
    for name in VARIANTS:
        expected = info['variants'][name]
        path = root / name / 'geometry.npz'
        added, added_counts = add_native_object(path, expected, 'Saved rim ' + name, shared)
        require_close(base.actual_conditions(bpy, scene, camera, added), conditions)
        output = root / name / 'views'
        actual_views, images = render_views(scene, camera, views, output)
        actual_body = body_signature(body, body_counts)
        if body.data.as_pointer() != original_mesh_pointer:
            raise ValueError('Original body mesh was replaced or reloaded.')
        verify_snapshots(snapshots)
        if code_hashes() != hashes or source_state(root)[4] != binding:
            raise ValueError('Actual saved data/source/code changed during comparison.')
        result = dict(common, candidate=name, kind='ORIGINAL_G7_PLUS_ACTUAL_SAVED_RIM_ADDITION_RENDER',
            saved_variant=expected, saved_placement=placement,
            added_geometry=str(path), added_geometry_sha256=expected['geometry_sha256'],
            added_geometry_counts=added_counts, original_body_display_readback=actual_body,
            views=views, actual_views=actual_views, images=images,
            scope='Original saved G7 native body loaded once and retained unchanged for all three variants. Each candidate adds only its actual independently saved rim ornament mesh. No body smoothing, remesh, G8, shading map, modifier or Boolean fusion. Flat native triangles and float32 display. Selected footprints may differ; occupied volume is not matched. Attachment aesthetics and intersection freedom require visual review.')
        (output / 'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
        mesh = added.data
        bpy.data.objects.remove(added, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        gc.collect()
        print('RIM_ORNAMENT_RENDERED', name, len(images), 'views; original body retained', flush=True)


if __name__ == '__main__':
    main()
