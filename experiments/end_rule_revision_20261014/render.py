"""Separate actual G7 end-geometry revision from smooth-normal presentation.

The original-only phase is independent of the pending candidate receipt.  Both
phases use fixed original flat images and four saved cameras, including a real
macro reference.  Smooth means polygon-normal interpolation only, never moving
vertices, changing connectivity, subdivision, remeshing or a modifier.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import math
import shutil
import struct
import sys
import zlib

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01')
PRESERVED_RENDER = HERE.parent / 'rim_ornament_adaptation_20261014/render.py'
PRESERVED_RENDER_SHA256 = 'bdb0264f017969467eab4a195a6370d83f6f2d79af0987cd676f7746f0a28391'
CAMERA_PLACEMENT = Path('E:/CHESHIRE_DATA/experiments/rim_ornament_adaptation_20261014/trial01/PLACEMENT.json')
CAMERA_PLACEMENT_SHA256 = '23f2a9f2f0af1d9bcf2cc72604ae1e13c52c7602795801537b2519c87c12b8ae'
MACRO_RECEIPT = CAMERA_PLACEMENT.parent / 'ORIGINAL_G7/views/receipt.json'
MACRO_RECEIPT_SHA256 = '02cdc37033f24d77fd34f7f6ac3f9866852c2b0be596be1f73ebf7b37f02264e'
CHECKER = HERE.parent / 'whole_column_detail_20261013/surface_boards.py'
CHECKER_SHA256 = 'b2276f3fbda604637f90a6f4dec7cc71528687c92ec8dcd7dfe3cea6bb5ea6f0'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prior_render = load_module('end_revision_preserved_renderer', PRESERVED_RENDER)
digest, read_json, require_close = prior_render.digest, prior_render.read_json, prior_render.require_close
SOURCE, base, helper = prior_render.SOURCE, prior_render.base, prior_render.helper
SOURCE_GEOMETRY_SHA256 = prior_render.SOURCE_GEOMETRY_SHA256
array_hash = prior_render.native.array_hash
add_native_object, render_views = prior_render.add_native_object, prior_render.render_views


def code_hashes():
    if digest(PRESERVED_RENDER) != PRESERVED_RENDER_SHA256 or digest(CHECKER) != CHECKER_SHA256:
        raise ValueError('Preserved native renderer/reference checker changed.')
    return dict(render=digest(__file__), preserved_renderer_sha256=PRESERVED_RENDER_SHA256,
        preserved_renderer_code=prior_render.code_hashes(), image_checker_sha256=CHECKER_SHA256)


def verify_native_png(path):
    """Dependency-free PNG dimensions and complete chunk CRC verification."""
    with Path(path).open('rb') as stream:
        if stream.read(8) != b'\x89PNG\r\n\x1a\n':
            raise ValueError('Actual native PNG required.')
        first, end = True, False
        while not end:
            header = stream.read(8)
            if len(header) != 8:
                raise ValueError('Incomplete original PNG chunk header.')
            length, name = struct.unpack('>I4s', header)
            data, crc_bytes = stream.read(length), stream.read(4)
            if len(data) != length or len(crc_bytes) != 4:
                raise ValueError('Incomplete original PNG chunk data.')
            if struct.unpack('>I', crc_bytes)[0] != zlib.crc32(name + data) & 0xffffffff:
                raise ValueError('Original PNG chunk checksum mismatch.')
            if first:
                if name != b'IHDR' or len(data) != 13 or struct.unpack('>II', data[:8]) != (900, 900):
                    raise ValueError('Actual 900-square original PNG required.')
                first = False
            end = name == b'IEND'
        if stream.read(1):
            raise ValueError('Unexpected bytes after original PNG end chunk.')


def checked_original_images(info, source):
    """Preserved checker source/array/camera/hash checks, without Pillow in Blender."""
    path = SOURCE / 'views/receipt.json'
    receipt = read_json(path)
    if (receipt.get('candidate') != info['candidate'] or receipt.get('input_case') != 'SPAN' or
            receipt.get('subdivision_generation') != info['subdivision_generation'] or
            receipt.get('code_sha256') != prior_render.prior.code_hashes() or
            any(receipt.get(key) != value for key, value in source.items())):
        raise ValueError('Preserved original source/render-code receipt differs.')
    require_close(receipt['conditions'], base.expected_conditions())
    if any(receipt['source_arrays'][key + '_sha256'] != info['checks']['native_' + key + '_sha256']
            for key in ('xyz', 'faces')):
        raise ValueError('Actual original rendered native-array hash differs.')
    records = {item['view']: item for item in receipt['images']}
    if len(records) != len(receipt['images']) or set(records) != set(prior_render.VIEWS):
        raise ValueError('Three distinct preserved original images required.')
    images, actual = [], {}
    for view, (position, target, scale) in prior_render.VIEWS.items():
        direction = [t - p for p, t in zip(position, target)]
        length = math.sqrt(sum(value * value for value in direction))
        expected = dict(position=list(position), target=list(target), scale=scale,
            forward=[value / length for value in direction])
        require_close(receipt['actual_views'][view], expected, 'original-camera.' + view)
        if receipt['views'][view] != json.loads(json.dumps(prior_render.VIEWS[view])):
            raise ValueError('Original declared camera differs.')
        png = path.parent / (view + '.png')
        checksum = digest(png)
        if records[view]['filename'] != png.name or records[view]['sha256'] != checksum:
            raise ValueError('Actual preserved original PNG changed.')
        verify_native_png(png)
        actual[view] = receipt['actual_views'][view]
        images.append(dict(view=view, path=str(png), sha256=checksum,
            receipt=str(path), receipt_sha256=digest(path)))
    return images, receipt, actual


def fixed_source_state():
    """Only original data and completed prior macro evidence; no pending candidate."""
    if (digest(CAMERA_PLACEMENT) != CAMERA_PLACEMENT_SHA256 or
            digest(MACRO_RECEIPT) != MACRO_RECEIPT_SHA256):
        raise ValueError('Fixed original macro camera/reference changed.')
    parent_info, source = helper.parent_state()
    if source['source_sha256'] != SOURCE_GEOMETRY_SHA256:
        raise ValueError('Original native G7 geometry changed.')
    placement = read_json(CAMERA_PLACEMENT)
    views = prior_render.all_views(placement)
    images, original_receipt, original_views = checked_original_images(parent_info, source)
    images = [dict(item, reused_reference=True, shading='FLAT') for item in images]
    macro = read_json(MACRO_RECEIPT)
    if (macro.get('candidate') != 'ORIGINAL_G7' or macro.get('original_body') != source or
            macro.get('original_body_unchanged_in_blender') is not True or
            macro.get('body_geometry_processing') is not False or macro.get('modifiers') != [] or
            macro.get('smooth_shading') is not False or macro.get('images') is None or
            len(macro['images']) != 1 or macro['images'][0].get('view') != 'macro' or
            macro.get('version') != original_receipt['version'] or
            macro.get('conditions') != original_receipt['conditions'] or
            macro.get('code_sha256') != prior_render.code_hashes()):
        raise ValueError('Actual unchanged original flat macro reference required.')
    if macro['original_body_display_readback'] != macro['original_body_counts']['expected_display_arrays']:
        raise ValueError('Actual original macro body readback mismatch.')
    require_close(macro['views'], {'macro': views['macro']}, 'fixed-macro')
    item = macro['images'][0]
    png = MACRO_RECEIPT.parent / 'macro.png'
    if item['filename'] != png.name or digest(png) != item['sha256']:
        raise ValueError('Original flat macro PNG changed.')
    verify_native_png(png)
    images.append(dict(item, path=str(png), receipt=str(MACRO_RECEIPT),
        receipt_sha256=MACRO_RECEIPT_SHA256, reused_reference=True, shading='FLAT'))
    actual_views = dict(original_views, macro=macro['actual_views']['macro'])
    binding = dict(source_native_path=source['source'], source_native_geometry_sha256=SOURCE_GEOMETRY_SHA256,
        original_source=source, camera_placement=str(CAMERA_PLACEMENT),
        camera_placement_sha256=CAMERA_PLACEMENT_SHA256, views=views,
        actual_reference_views=actual_views, reference_images=images,
        reference_conditions=original_receipt['conditions'], reference_Blender_version=original_receipt['version'])
    return parent_info, source, binding


def snapshot_source(root):
    source = Path(__file__).resolve()
    relative = Path('experiments') / HERE.name / 'render.py'
    target = Path(root) / 'source_snapshot_render' / relative
    checksum = digest(source)
    if target.exists():
        if digest(target) != checksum:
            raise ValueError('Frozen renderer snapshot differs; use a new experiment root.')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    record = dict(source=str(source), relative_path=relative.as_posix(), snapshot=str(target), sha256=checksum)
    verify_snapshot(record)
    return record


def verify_snapshot(record):
    if (record.get('sha256') != digest(__file__) or
            any(digest(record[key]) != record['sha256'] for key in ('source', 'snapshot'))):
        raise ValueError('Actual renderer/source snapshot changed.')


def geometry_signature(obj, counts, smooth):
    """Check native display coordinates/indices and actual polygon normal flags."""
    import numpy as np
    mesh = obj.data
    if (len(obj.modifiers) or obj.hide_render or not np.array_equal(np.asarray(obj.matrix_world), np.eye(4)) or
            len(mesh.vertices) != counts['vertices'] or len(mesh.polygons) != counts['triangles'] or
            len(mesh.loops) != 3 * counts['triangles']):
        raise ValueError('Saved body mesh/object state changed.')
    xyz = np.empty(3 * len(mesh.vertices), np.float32)
    mesh.vertices.foreach_get('co', xyz)
    xyz_hash = array_hash(xyz)
    del xyz
    indices = np.empty(len(mesh.loops), np.int32)
    mesh.loops.foreach_get('vertex_index', indices)
    indices_hash = array_hash(indices)
    del indices
    flags = np.empty(len(mesh.polygons), bool)
    mesh.polygons.foreach_get('use_smooth', flags)
    smooth_count = int(np.count_nonzero(flags))
    flags_hash = array_hash(flags)
    del flags
    expected_count = len(mesh.polygons) if smooth else 0
    if smooth_count != expected_count:
        raise ValueError('Actual polygon smooth-normal flags differ from declared shading.')
    geometry = dict(xyz_float32_sha256=xyz_hash, triangle_indices_int32_sha256=indices_hash)
    if geometry != counts['expected_display_arrays']:
        raise ValueError('Actual saved geometry coordinates/connectivity were changed inside Blender.')
    return dict(geometry=geometry, smooth_polygons=smooth_count, polygons=len(mesh.polygons),
        use_smooth_flags_sha256=flags_hash, all_use_smooth=bool(smooth),
        geometry_unchanged=True, modifiers=[], custom_normal_map=False)


def set_smooth_flags(obj, value):
    import numpy as np
    flags = np.full(len(obj.data.polygons), value, bool)
    obj.data.polygons.foreach_set('use_smooth', flags)
    del flags
    obj.data.update()


def setup_scene():
    import bpy
    shared = load_module('end_revision_frozen_scene', base.SHARED_RENDER)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    return shared


def conditions_for(bpy, scene, camera, obj, counts, smooth, binding):
    actual = base.actual_conditions(bpy, scene, camera, obj)
    expected = dict(base.expected_conditions(), smooth_polygons=counts['triangles'] if smooth else 0)
    require_close(actual, expected)
    reference = dict(binding['reference_conditions'], smooth_polygons=expected['smooth_polygons'])
    require_close(actual, reference)
    if bpy.app.version_string != binding['reference_Blender_version']:
        raise ValueError('Original and new render Blender versions differ.')
    return actual


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')


def render_state(root, state, geometry_path, expected, binding, snapshot, hashes, candidate_binding=None,
                 obj=None, counts=None, shared=None, scene=None, camera=None):
    import bpy
    smooth = state.endswith('_SMOOTH')
    output = root / state / 'views'
    if output.exists():
        raise FileExistsError('Earlier actual render preserved: ' + str(output))
    if obj is None:
        shared = setup_scene()
        obj, counts = add_native_object(geometry_path, expected, 'Actual saved ' + state, shared)
        scene, camera = shared.setup_scene(900, 24)
    set_smooth_flags(obj, smooth)
    before = geometry_signature(obj, counts, smooth)
    conditions = conditions_for(bpy, scene, camera, obj, counts, smooth, binding)
    actual_views, images = render_views(scene, camera, binding['views'], output)
    for view in actual_views:
        require_close(actual_views[view], binding['actual_reference_views'][view], 'matched-camera.' + view)
    after = geometry_signature(obj, counts, smooth)
    if before != after:
        raise ValueError('Actual geometry/shading flags changed during rendering.')
    verify_snapshot(snapshot)
    if code_hashes() != hashes or fixed_source_state()[2] != binding:
        raise ValueError('Actual saved source/reference/renderer changed during rendering.')
    result = dict(state=state, kind='ACTUAL_SAVED_BODY_GEOMETRY_WITH_EXPLICIT_NORMAL_SHADING',
        source_binding=binding, candidate_binding=candidate_binding,
        geometry_path=str(geometry_path), saved_geometry=expected, geometry_counts=counts,
        display_readback=after, geometry_unchanged_in_renderer=True,
        shading='SMOOTH_NORMAL_INTERPOLATION_ONLY' if smooth else 'FLAT_NATIVE_TRIANGLES',
        smooth_shading=smooth, geometry_smoothing=False, normal_interpolation_only=smooth,
        geometry_processing=False, modifiers=[], remesh=False, Boolean_fusion=False,
        ornaments_added=False, new_source_growth_G8=False, source_growth_generation=7,
        version=bpy.app.version_string, conditions=conditions, views=binding['views'],
        actual_views=actual_views, images=images, code_sha256=hashes, render_source_snapshot=snapshot,
        scope='Actual saved entire-body mesh at four fixed original cameras. Coordinates/connectivity are read back unchanged before and after rendering. Smooth states change only polygon use_smooth flags and interpolate shading normals; they are a presentation diagnostic, not a geometric improvement. No extra ornaments, modifier, geometry averaging, subdivision, remesh, fusion, image crop or synthesis.')
    write_json(output / 'receipt.json', result)
    print('END_RULE_RENDERED', state, len(images), 'actual PNGs; geometry readback unchanged', flush=True)
    return obj, counts, shared, scene, camera


def original_phase(root, snapshot, hashes):
    import bpy
    parent_info, source, binding = fixed_source_state()
    if (root / 'SOURCE_BINDING.json').exists() or (root / 'ORIGINAL_FLAT/receipt.json').exists():
        raise FileExistsError('Earlier original-only phase preserved.')
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / 'SOURCE_BINDING.json', binding)
    flat_folder = root / 'ORIGINAL_FLAT'
    flat_folder.mkdir()
    flat_record = dict(state='ORIGINAL_FLAT', kind='FOUR_REUSED_ACTUAL_ORIGINAL_FLAT_IMAGES',
        source_binding=binding, images=binding['reference_images'], code_sha256=hashes,
        render_source_snapshot=snapshot, smooth_shading=False, geometry_smoothing=False,
        geometry_processing=False, modifiers=[], new_renders=0,
        scope='Three preserved original native G7 images plus its preserved actual macro image. All are flat native shading; source/camera/PNG hashes are fixed and verified. No new render or geometry generation.')
    write_json(flat_folder / 'receipt.json', flat_record)
    expected = dict(geometry_sha256=SOURCE_GEOMETRY_SHA256,
        xyz_sha256=parent_info['checks']['native_xyz_sha256'],
        faces_sha256=parent_info['checks']['native_faces_sha256'])
    obj, counts, shared, scene, camera = render_state(root, 'ORIGINAL_SMOOTH', Path(source['source']),
        expected, binding, snapshot, hashes)
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    gc.collect()
    print('END_RULE_ORIGINAL_ONLY_DONE: 4 reused flat + 4 actual smooth-normal diagnostics', flush=True)


def candidate_state(root, binding):
    info = read_json(root / 'RECEIPT.json')
    if (info.get('source_native_geometry_sha256') != SOURCE_GEOMETRY_SHA256 or
            Path(info.get('source_native_path', '')).resolve() != Path(binding['source_native_path']).resolve()):
        raise ValueError('Revised body must be bound to the actual original native G7.')
    variant = info.get('variants', {}).get('REVISED')
    if not isinstance(variant, dict):
        raise ValueError('One actual saved whole-body REVISED variant required.')
    path = root / 'REVISED/geometry.npz'
    if Path(variant.get('geometry', '')).resolve() != path.resolve() or digest(path) != variant.get('geometry_sha256'):
        raise ValueError('Actual saved revised native geometry differs.')
    for key in ('xyz_sha256', 'faces_sha256'):
        value = variant.get(key)
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError('Actual revised array hash required: ' + key)
    candidate = dict(receipt=str(root / 'RECEIPT.json'), receipt_sha256=digest(root / 'RECEIPT.json'),
        variant=variant, original_source=binding['original_source'])
    return path, variant, candidate


def candidate_phase(root, snapshot, hashes):
    import bpy
    parent_info, source, binding = fixed_source_state()
    saved_binding = read_json(root / 'SOURCE_BINDING.json')
    if saved_binding != json.loads(json.dumps(binding)):
        raise ValueError('Original-only phase source/camera/reference binding differs.')
    original = read_json(root / 'ORIGINAL_SMOOTH/views/receipt.json')
    if original.get('code_sha256') != hashes:
        raise ValueError('Original/candidate phases must use the same frozen renderer.')
    verify_snapshot(original['render_source_snapshot'])
    path, expected, candidate = candidate_state(root, binding)
    obj, counts, shared, scene, camera = render_state(root, 'REVISED_FLAT', path, expected,
        binding, snapshot, hashes, candidate_binding=candidate)
    if candidate_state(root, binding)[2] != candidate:
        raise ValueError('Actual revised candidate binding changed.')
    render_state(root, 'REVISED_SMOOTH', path, expected, binding, snapshot, hashes,
        candidate_binding=candidate, obj=obj, counts=counts, shared=shared, scene=scene, camera=camera)
    if candidate_state(root, binding)[2] != candidate:
        raise ValueError('Actual revised candidate binding changed.')
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    gc.collect()
    print('END_RULE_CANDIDATE_ONLY_DONE: same saved revised body, 4 flat + 4 smooth-normal diagnostic PNGs', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--phase', choices=('original_only', 'candidate_only', 'all'), required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    if root == SOURCE.resolve() or SOURCE.resolve() in root.parents:
        raise ValueError('Original source is read-only.')
    hashes = code_hashes()
    snapshot = snapshot_source(root)
    if args.phase in ('original_only', 'all'):
        original_phase(root, snapshot, hashes)
    if args.phase in ('candidate_only', 'all'):
        candidate_phase(root, snapshot, hashes)


if __name__ == '__main__':
    main()
