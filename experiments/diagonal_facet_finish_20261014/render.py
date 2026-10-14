"""Render one source/candidate pair with the same saved selective flat-quad mask."""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/diagonal_facet_finish_20261014/trial01')
SCAFFOLD = HERE.parent / 'end_rule_revision_20261014/render.py'
SCAFFOLD_SHA256 = '58b8dff2f1ef9b91a438d97b5d7174dca3048e3f6e9af44e56b2bfdadf0c1ce8'
SOURCE_RECEIPT = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/RECEIPT.json')
SOURCE_RECEIPT_SHA256 = 'b77a701e01a53976e08ad07b963fb022931bf8e4efcc08d21485a55fddd31569'
SOURCE = SOURCE_RECEIPT.parent / 'REVISED/geometry.npz'
SOURCE_GEOMETRY_SHA256 = '952386874740ca35a26dcb0a5a42cda4fb91eaa8f814f7668550d839a2b688ce'
CONTROL_NV, CONTROL_NQ = 7_002_114, 7_002_112
CHUNK_TRIANGLES = 250_000
spec = importlib.util.spec_from_file_location('diagonal_facet_frozen_render_scaffold', SCAFFOLD)
scaffold = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scaffold)
digest, read_json, require_close = scaffold.digest, scaffold.read_json, scaffold.require_close
array_hash, base = scaffold.array_hash, scaffold.base


def canonical(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def code_hashes():
    if digest(SCAFFOLD) != SCAFFOLD_SHA256:
        raise ValueError('Preserved render scaffold changed.')
    return dict(render=digest(__file__), scaffold_sha256=SCAFFOLD_SHA256,
        preserved_scaffold_code=scaffold.code_hashes())


def fixed_source():
    if digest(SOURCE_RECEIPT) != SOURCE_RECEIPT_SHA256 or digest(SOURCE) != SOURCE_GEOMETRY_SHA256:
        raise ValueError('Saved revised source changed.')
    prior_info = read_json(SOURCE_RECEIPT)
    expected = prior_info.get('variants', {}).get('REVISED')
    if (not isinstance(expected, dict) or Path(expected.get('geometry', '')).resolve() != SOURCE.resolve() or
            expected.get('geometry_sha256') != SOURCE_GEOMETRY_SHA256 or
            expected.get('vertices') != CONTROL_NV + CONTROL_NQ or
            expected.get('triangles') != 4 * CONTROL_NQ):
        raise ValueError('Actual saved revised native G7 source required.')
    _, _, camera_binding = scaffold.fixed_source_state()
    return expected, camera_binding


def mask_state(root):
    import numpy as np
    path = Path(root) / 'MASK.npz'
    checksum = digest(path)
    with np.load(path, allow_pickle=False) as data:
        flat_quads = data['flat_quads']
    if flat_quads.dtype != np.bool_ or flat_quads.shape != (CONTROL_NQ,):
        raise ValueError('Saved flat_quads must be exactly one bool per original control quad.')
    record = dict(path=str(path), sha256=checksum, key='flat_quads',
        flat_quads_array_sha256=array_hash(flat_quads), quads=CONTROL_NQ,
        flat_quads=int(np.count_nonzero(flat_quads)), control_vertices=CONTROL_NV,
        rule='smooth_triangle = NOT flat_quads[unique_native_center_vertex_id - control_vertices]')
    return flat_quads, record


def source_binding(root):
    expected, cameras = fixed_source()
    _, mask = mask_state(root)
    return canonical(dict(source_native_path=str(SOURCE), source_native_geometry_sha256=SOURCE_GEOMETRY_SHA256,
        source_receipt=str(SOURCE_RECEIPT), source_receipt_sha256=SOURCE_RECEIPT_SHA256,
        saved_source=expected, mask=mask, views=cameras['views'],
        actual_reference_views=cameras['actual_reference_views'],
        reference_conditions=cameras['reference_conditions'],
        reference_Blender_version=cameras['reference_Blender_version'],
        camera_placement=cameras['camera_placement'], camera_placement_sha256=cameras['camera_placement_sha256']))


def snapshot_source(root):
    source = Path(__file__).resolve()
    relative = Path('experiments') / HERE.name / 'render.py'
    target = Path(root) / 'source_snapshot_render' / relative
    checksum = digest(source)
    if target.exists():
        if digest(target) != checksum:
            raise ValueError('Frozen renderer snapshot differs; use a new root.')
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


def selective_flags(geometry, expected, flat_quads):
    """Assert one real native center per triangle before assigning any flag."""
    import numpy as np
    with np.load(geometry, allow_pickle=False) as data:
        faces = data['faces']
    if (faces.shape != (4 * CONTROL_NQ, 3) or faces.dtype.kind not in 'iu' or
            array_hash(faces) != expected['faces_sha256']):
        raise ValueError('Actual saved native triangle indices differ.')
    flags = np.empty(len(faces), bool)
    quad_counts = np.zeros(CONTROL_NQ, np.uint32)
    mapping_hash = hashlib.sha256()
    for start in range(0, len(faces), CHUNK_TRIANGLES):
        stop = min(start + CHUNK_TRIANGLES, len(faces))
        triangles = faces[start:stop]
        is_center = triangles >= CONTROL_NV
        if not np.all(np.count_nonzero(is_center, axis=1) == 1):
            raise ValueError('Every actual native triangle must contain exactly one quad-center vertex.')
        quad_ids = triangles[is_center].astype(np.int64, copy=False) - CONTROL_NV
        if np.any(quad_ids < 0) or np.any(quad_ids >= CONTROL_NQ):
            raise ValueError('Actual unique native center has an out-of-range original quad ID.')
        flags[start:stop] = np.logical_not(flat_quads[quad_ids])
        np.add.at(quad_counts, quad_ids, 1)
        mapping_hash.update(memoryview(np.ascontiguousarray(quad_ids, dtype=np.int32)).cast('B'))
    if not np.all(quad_counts == 4):
        raise ValueError('Each original control quad must have exactly four actual native fan triangles.')
    record = dict(native_faces_array_sha256=expected['faces_sha256'],
        native_triangles=len(faces), control_vertices=CONTROL_NV, original_quads=CONTROL_NQ,
        chunk_triangles=CHUNK_TRIANGLES, unique_center_assertion_passed=True,
        each_original_quad_has_four_native_triangles=True,
        mapped_quad_ids_int32_sha256=mapping_hash.hexdigest(),
        smooth_flags_sha256=array_hash(flags), smooth_polygons=int(np.count_nonzero(flags)),
        flat_polygons=int(len(flags) - np.count_nonzero(flags)))
    del faces, quad_counts
    return flags, record


def geometry_signature(obj, counts, mapping):
    import numpy as np
    mesh = obj.data
    if (len(obj.modifiers) or obj.hide_render or not np.array_equal(np.asarray(obj.matrix_world), np.eye(4)) or
            len(mesh.vertices) != counts['vertices'] or len(mesh.polygons) != counts['triangles'] or
            len(mesh.loops) != 3 * counts['triangles']):
        raise ValueError('Actual saved body mesh/object state changed.')
    xyz = np.empty(3 * len(mesh.vertices), np.float32)
    mesh.vertices.foreach_get('co', xyz)
    xyz_hash = array_hash(xyz)
    del xyz
    indices = np.empty(len(mesh.loops), np.int32)
    mesh.loops.foreach_get('vertex_index', indices)
    index_hash = array_hash(indices)
    del indices
    flags = np.empty(len(mesh.polygons), bool)
    mesh.polygons.foreach_get('use_smooth', flags)
    smooth_count, flags_hash = int(np.count_nonzero(flags)), array_hash(flags)
    del flags
    geometry = dict(xyz_float32_sha256=xyz_hash, triangle_indices_int32_sha256=index_hash)
    if (geometry != counts['expected_display_arrays'] or smooth_count != mapping['smooth_polygons'] or
            flags_hash != mapping['smooth_flags_sha256']):
        raise ValueError('Actual coordinates/connectivity/selective flags differ from saved source.')
    return dict(geometry=geometry, polygons=len(mesh.polygons), smooth_polygons=smooth_count,
        flat_polygons=len(mesh.polygons) - smooth_count, use_smooth_flags_sha256=flags_hash,
        geometry_unchanged=True, modifiers=[], custom_normal_map=False)


def candidate_state(root, binding):
    info = read_json(root / 'RECEIPT.json')
    if (Path(info.get('source_native_path', '')).resolve() != SOURCE.resolve() or
            info.get('source_native_geometry_sha256') != SOURCE_GEOMETRY_SHA256 or
            info.get('mask_sha256') != binding['mask']['sha256']):
        raise ValueError('Actual accent candidate must bind to the same revised source and selective mask.')
    variants = info.get('variants')
    if not isinstance(variants, dict) or set(variants) != {'ACCENT'}:
        raise ValueError('Exactly one actual saved ACCENT body required.')
    expected = variants['ACCENT']
    path = root / 'ACCENT/geometry.npz'
    if (Path(expected.get('geometry', '')).resolve() != path.resolve() or
            digest(path) != expected.get('geometry_sha256') or
            expected.get('faces_sha256') != binding['saved_source']['faces_sha256'] or
            expected.get('vertices') != CONTROL_NV + CONTROL_NQ or
            expected.get('triangles') != 4 * CONTROL_NQ):
        raise ValueError('Actual accent geometry/native connectivity differs.')
    for key in ('geometry_sha256', 'xyz_sha256', 'faces_sha256'):
        value = expected.get(key)
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError('Actual accent file/array hash required.')
    return path, expected, canonical(dict(receipt=str(root / 'RECEIPT.json'),
        receipt_sha256=digest(root / 'RECEIPT.json'), variant=expected))


def render_state(root, state, path, expected, binding, snapshot, hashes, candidate=None):
    import bpy
    output = root / state / 'views'
    if output.exists():
        raise FileExistsError('Earlier actual selective-mask render preserved.')
    shared = scaffold.setup_scene()
    obj, counts = scaffold.add_native_object(path, expected, 'Actual saved ' + state, shared)
    flat_quads, actual_mask = mask_state(root)
    if actual_mask != binding['mask']:
        raise ValueError('Actual saved mask changed before rendering.')
    flags, mapping = selective_flags(path, expected, flat_quads)
    del flat_quads
    obj.data.polygons.foreach_set('use_smooth', flags)
    del flags
    obj.data.update()
    before = geometry_signature(obj, counts, mapping)
    scene, camera = shared.setup_scene(900, 24)
    conditions = base.actual_conditions(bpy, scene, camera, obj)
    require_close(conditions, dict(binding['reference_conditions'], smooth_polygons=mapping['smooth_polygons']))
    require_close(conditions, dict(base.expected_conditions(), smooth_polygons=mapping['smooth_polygons']))
    if bpy.app.version_string != binding['reference_Blender_version']:
        raise ValueError('Frozen source/candidate Blender versions differ.')
    actual_views, images = scaffold.render_views(scene, camera, binding['views'], output)
    for view in actual_views:
        require_close(actual_views[view], binding['actual_reference_views'][view], 'matched-camera.' + view)
    after = geometry_signature(obj, counts, mapping)
    if before != after:
        raise ValueError('Actual geometry/selective flags changed during rendering.')
    verify_snapshot(snapshot)
    if code_hashes() != hashes or source_binding(root) != binding or digest(path) != expected['geometry_sha256']:
        raise ValueError('Actual source/camera/mask/code/geometry changed during rendering.')
    result = dict(state=state, kind='ACTUAL_BODY_WITH_SHARED_SELECTIVE_FLAT_QUAD_MASK',
        source_binding=binding, candidate_binding=candidate, geometry_path=str(path), saved_geometry=expected,
        geometry_counts=counts, mask_mapping=mapping, display_readback=after,
        geometry_unchanged_in_renderer=True, geometry_processing=False, geometry_smoothing=False,
        selective_normal_interpolation=True, shading='FLAT_ON_SAVED_QUADS_SMOOTH_ELSEWHERE',
        modifiers=[], normal_maps=False, remesh=False, Boolean_fusion=False, ornaments_added=False,
        source_growth_generation=7, new_source_growth_G8=False, version=bpy.app.version_string,
        conditions=conditions, views=binding['views'], actual_views=actual_views, images=images,
        code_sha256=hashes, render_source_snapshot=snapshot,
        scope='Actual saved entire body at four frozen cameras. Every native triangle was verified to contain exactly one quad-center ID; the same saved original quad mask assigns selective normal interpolation before and after. Coordinates/connectivity and all polygon normal flags are read back unchanged. No renderer geometry change, extra ornaments, modifier, remesh, Boolean, crop or synthesis. Normal interpolation is presentation; geometric and aesthetic success require actual visual review.')
    write_json(output / 'receipt.json', result)
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    gc.collect()
    print('DIAGONAL_FACET_RENDERED', state, len(images), 'actual PNGs; native geometry and selective flags verified', flush=True)
    return result


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')


def source_phase(root, snapshot, hashes):
    if (root / 'SOURCE_BINDING.json').exists():
        raise FileExistsError('Earlier source phase preserved.')
    binding = source_binding(root)
    write_json(root / 'SOURCE_BINDING.json', binding)
    render_state(root, 'SOURCE_SELECTIVE', SOURCE, binding['saved_source'], binding, snapshot, hashes)
    print('DIAGONAL_FACET_SOURCE_ONLY_DONE', flush=True)


def candidate_phase(root, snapshot, hashes):
    binding = source_binding(root)
    if read_json(root / 'SOURCE_BINDING.json') != binding:
        raise ValueError('Actual saved source/mask/camera phase binding differs.')
    source_receipt = read_json(root / 'SOURCE_SELECTIVE/views/receipt.json')
    if source_receipt.get('code_sha256') != hashes or source_receipt.get('source_binding') != binding:
        raise ValueError('Both phases must use the same frozen renderer/source/mask.')
    verify_snapshot(source_receipt['render_source_snapshot'])
    path, expected, candidate = candidate_state(root, binding)
    result = render_state(root, 'ACCENT_SELECTIVE', path, expected, binding, snapshot, hashes, candidate)
    if (candidate_state(root, binding)[2] != candidate or
            result['mask_mapping'] != source_receipt['mask_mapping'] or
            result['display_readback']['geometry']['triangle_indices_int32_sha256'] !=
            source_receipt['display_readback']['geometry']['triangle_indices_int32_sha256'] or
            result['display_readback']['use_smooth_flags_sha256'] !=
            source_receipt['display_readback']['use_smooth_flags_sha256']):
        raise ValueError('Source/candidate native indices or actual selective normal flags differ.')
    print('DIAGONAL_FACET_CANDIDATE_ONLY_DONE: same native indices and actual selective-normal mask', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--phase', choices=('source_only', 'candidate_only', 'all'), required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    if root == SOURCE.parent.resolve() or SOURCE.parent.resolve() in root.parents:
        raise ValueError('Preserved source is read-only.')
    hashes = code_hashes()
    snapshot = snapshot_source(root)
    if args.phase in ('source_only', 'all'):
        source_phase(root, snapshot, hashes)
    if args.phase in ('candidate_only', 'all'):
        candidate_phase(root, snapshot, hashes)


if __name__ == '__main__':
    main()
