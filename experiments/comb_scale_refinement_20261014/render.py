"""Display one local large-scale refinement against the accepted fine-comb body."""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/comb_scale_refinement_20261014/trial01')
SCAFFOLD = HERE.parent / 'comb_relief_20261014/render.py'
SCAFFOLD_SHA256 = '08c503ae0895869090693ca01301394332583cdb6d3d129abc97300629496c13'
SOURCE_RECEIPT = Path('E:/CHESHIRE_DATA/experiments/comb_relief_20261014/trial01/RECEIPT.json')
SOURCE_RECEIPT_SHA256 = '2373a46b3fd1192966b0205bd96f174394fa97ba58cc8715a3a83de4daf4cdbc'
SOURCE = SOURCE_RECEIPT.parent / 'RELIEF/geometry.npz'
SOURCE_GEOMETRY_SHA256 = 'e874da795215bcd28f31a153f052d774bb2313b828c58cc381989dc115ed3f9e'
SOURCE_FLAT_RECEIPT = SOURCE_RECEIPT.parent / 'RELIEF_FLAT/views/receipt.json'
SOURCE_FLAT_RECEIPT_SHA256 = '25c6ede28b883992c4dccb64b3f73e92857f8e709fbc6f3b95834ed197bf4e3a'
spec = importlib.util.spec_from_file_location('comb_scale_frozen_native_scaffold', SCAFFOLD)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
scaffold = previous.scaffold
digest, read_json, require_close = scaffold.digest, scaffold.read_json, scaffold.require_close
array_hash, base = scaffold.array_hash, scaffold.base


def canonical(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def code_hashes():
    if digest(SCAFFOLD) != SCAFFOLD_SHA256:
        raise ValueError('Preserved native render scaffold changed.')
    return dict(render=digest(__file__), scaffold_sha256=SCAFFOLD_SHA256,
        preserved_scaffold_code=previous.code_hashes())


def fixed_source_binding():
    if digest(SOURCE_RECEIPT) != SOURCE_RECEIPT_SHA256 or digest(SOURCE) != SOURCE_GEOMETRY_SHA256:
        raise ValueError('Actual saved revised source changed.')
    source_info = read_json(SOURCE_RECEIPT)
    expected = source_info.get('variants', {}).get('RELIEF')
    if (not isinstance(expected, dict) or Path(expected.get('geometry', '')).resolve() != SOURCE.resolve() or
            expected.get('geometry_sha256') != SOURCE_GEOMETRY_SHA256):
        raise ValueError('Actual saved revised source binding required.')
    _, _, cameras = scaffold.fixed_source_state()
    return canonical(dict(source_native_path=str(SOURCE), source_native_geometry_sha256=SOURCE_GEOMETRY_SHA256,
        source_receipt=str(SOURCE_RECEIPT), source_receipt_sha256=SOURCE_RECEIPT_SHA256,
        saved_source=expected, views=cameras['views'], actual_reference_views=cameras['actual_reference_views'],
        reference_conditions=cameras['reference_conditions'], reference_Blender_version=cameras['reference_Blender_version'],
        camera_placement=cameras['camera_placement'], camera_placement_sha256=cameras['camera_placement_sha256']))


def source_flat_state(binding):
    import numpy as np
    if digest(SOURCE_FLAT_RECEIPT) != SOURCE_FLAT_RECEIPT_SHA256:
        raise ValueError('Actual same-source all-flat receipt changed.')
    receipt = read_json(SOURCE_FLAT_RECEIPT)
    expected = binding['saved_source']
    if (receipt.get('state') != 'RELIEF_FLAT' or receipt.get('saved_geometry') != expected or
            Path(receipt.get('geometry_path', '')).resolve() != SOURCE.resolve() or
            receipt.get('code_sha256') != previous.code_hashes() or
            receipt.get('geometry_unchanged_in_renderer') is not True or receipt.get('smooth_shading') is not False or
            receipt.get('geometry_smoothing') is not False or receipt.get('geometry_processing') is not False or
            receipt.get('modifiers') != [] or receipt.get('normal_maps') is not False or
            receipt.get('remesh') is not False or receipt.get('Boolean_fusion') is not False or
            receipt.get('ornaments_added') is not False):
        raise ValueError('Actual same-source all-flat native render required.')
    prior_candidate = receipt.get('candidate_binding', {})
    if prior_candidate.get('receipt_sha256') != SOURCE_RECEIPT_SHA256 or prior_candidate.get('variant') != expected:
        raise ValueError('Actual same-source all-flat geometry provenance differs.')
    previous.verify_snapshot(receipt['render_source_snapshot'])
    counts, readback = receipt['geometry_counts'], receipt['display_readback']
    if (counts['source_arrays'] != {key: expected[key] for key in ('xyz_sha256', 'faces_sha256')} or
            any(counts[key] != expected[key] for key in ('vertices', 'triangles')) or
            readback.get('geometry') != counts['expected_display_arrays'] or readback.get('smooth_polygons') != 0 or
            readback.get('all_use_smooth') is not False or readback.get('geometry_unchanged') is not True or
            readback.get('modifiers') != [] or
            readback.get('use_smooth_flags_sha256') != array_hash(np.zeros(expected['triangles'], bool))):
        raise ValueError('Actual same-source all-flat coordinates/indices/flags readback differs.')
    require_close(receipt['conditions'], binding['reference_conditions'])
    require_close(receipt['views'], binding['views'])
    if receipt['version'] != binding['reference_Blender_version']:
        raise ValueError('Original/reference Blender versions differ.')
    records = receipt.get('images')
    if (not isinstance(records, list) or len(records) != 4 or
            {item['view'] for item in records} != set(binding['views'])):
        raise ValueError('Four actual preserved source flat PNGs required.')
    images = []
    for item in records:
        view = item['view']
        path = SOURCE_FLAT_RECEIPT.parent / (view + '.png')
        if item['filename'] != path.name or digest(path) != item['sha256']:
            raise ValueError('Actual preserved source all-flat PNG changed.')
        scaffold.verify_native_png(path)
        require_close(receipt['actual_views'][view], binding['actual_reference_views'][view], 'same-source-flat-camera.' + view)
        images.append(dict(view=view, path=str(path), sha256=item['sha256'], reused_reference=True,
            receipt=str(SOURCE_FLAT_RECEIPT), receipt_sha256=SOURCE_FLAT_RECEIPT_SHA256))
    return dict(state='SOURCE_FLAT', saved_geometry=expected, images=images, geometry_counts=counts,
        display_readback=readback, conditions=receipt['conditions'], actual_views=receipt['actual_views'],
        Blender_version=receipt['version'], source_receipt=str(SOURCE_FLAT_RECEIPT),
        source_receipt_sha256=SOURCE_FLAT_RECEIPT_SHA256)


def candidate_state(root, binding):
    info = read_json(root / 'RECEIPT.json')
    if (Path(info.get('source_native_path', '')).resolve() != SOURCE.resolve() or
            info.get('source_native_geometry_sha256') != SOURCE_GEOMETRY_SHA256):
        raise ValueError('Actual REFINED candidate must bind to the same revised native source.')
    variants = info.get('variants')
    if not isinstance(variants, dict) or set(variants) != {'REFINED'}:
        raise ValueError('Exactly one actual saved REFINED body required.')
    expected = variants['REFINED']
    path = root / 'REFINED/geometry.npz'
    if (Path(expected.get('geometry', '')).resolve() != path.resolve() or
            digest(path) != expected.get('geometry_sha256')):
        raise ValueError('Actual REFINED geometry differs.')
    for key in ('vertices', 'triangles'):
        value = expected.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError('Actual positive RELIEF native vertex/triangle counts required.')
    for key in ('geometry_sha256', 'xyz_sha256', 'faces_sha256'):
        value = expected.get(key)
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError('Actual REFINED file/array hash required.')
    candidate = canonical(dict(receipt=str(root / 'RECEIPT.json'),
        receipt_sha256=digest(root / 'RECEIPT.json'), variant=expected))
    return path, expected, candidate


def saved_state(root):
    binding = fixed_source_binding()
    source_flat = source_flat_state(binding)
    path, expected, candidate = candidate_state(root, binding)
    return binding, source_flat, path, expected, candidate


def snapshot_source(root):
    source = Path(__file__).resolve()
    relative = Path('experiments') / HERE.name / source.name
    target = Path(root) / 'source_snapshot_render' / relative
    checksum = digest(source)
    if target.exists():
        if digest(target) != checksum:
            raise ValueError('Earlier renderer snapshot differs; use a new experiment root.')
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


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    if root == SOURCE.parent.resolve() or SOURCE.parent.resolve() in root.parents:
        raise ValueError('Preserved source is read-only.')
    output = root / 'REFINED_FLAT/views'
    if output.exists():
        raise FileExistsError('Earlier actual REFINED render preserved.')
    hashes = code_hashes()
    binding, source_flat, path, expected, candidate = saved_state(root)
    snapshot = snapshot_source(root)
    shared = scaffold.setup_scene()
    obj, counts = scaffold.add_native_object(path, expected, 'Actual saved locally refined scale body', shared)
    scaffold.set_smooth_flags(obj, False)
    before = scaffold.geometry_signature(obj, counts, False)
    scene, camera = shared.setup_scene(900, 24)
    conditions = base.actual_conditions(bpy, scene, camera, obj)
    require_close(conditions, source_flat['conditions'])
    require_close(conditions, base.expected_conditions())
    if bpy.app.version_string != source_flat['Blender_version']:
        raise ValueError('Source/candidate Blender versions differ.')
    actual_views, images = scaffold.render_views(scene, camera, binding['views'], output)
    for view in actual_views:
        require_close(actual_views[view], source_flat['actual_views'][view], 'matched-flat-camera.' + view)
    after = scaffold.geometry_signature(obj, counts, False)
    if before != after:
        raise ValueError('Actual saved candidate coordinates/native indices/all-flat flags changed.')
    verify_snapshot(snapshot)
    if code_hashes() != hashes or saved_state(root) != (binding, source_flat, path, expected, candidate):
        raise ValueError('Actual source/candidate/reference/code binding changed during rendering.')
    result = dict(state='REFINED_FLAT', kind='ACTUAL_SAVED_LOCAL_SCALE_REFINEMENT_ALL_FLAT_NATIVE_RENDER',
        source_binding=binding, candidate_binding=candidate, source_flat_reference=source_flat,
        geometry_path=str(path), saved_geometry=expected, geometry_counts=counts, display_readback=after,
        geometry_unchanged_in_renderer=True, geometry_processing=False, geometry_smoothing=False,
        shading='ALL_FLAT_NATIVE_TRIANGLES', smooth_shading=False, smooth_polygons=0,
        normal_maps=False, modifiers=[], remesh=False, Boolean_fusion=False, ornaments_added=False,
        selective_mask_dependency=False, source_growth_generation=7, new_source_growth_G8=False,
        source_native_vertices=binding['saved_source']['vertices'],
        source_native_triangles=binding['saved_source']['triangles'],
        added_native_vertices=counts['vertices'] - binding['saved_source']['vertices'],
        added_native_triangles=counts['triangles'] - binding['saved_source']['triangles'],
        native_topology_changed=expected['faces_sha256'] != binding['saved_source']['faces_sha256'],
        generator_validation_evidence=expected.get('validation'),
        generator_validation_scope='Control/boundary evidence is carried from the hash-bound generator receipt; the renderer verifies its saved candidate arrays and does not re-run generator boundary checks.',
        version=bpy.app.version_string, conditions=conditions, views=binding['views'], actual_views=actual_views,
        images=images, code_sha256=hashes, render_source_snapshot=snapshot,
        scope='One actual saved REFINED entire-body mesh under all-flat native shading and four frozen cameras. The exact source body\'s four existing all-flat PNGs are reused. Candidate native topology/counts may differ; its actual coordinates and indices match its own saved arrays and remain unchanged in Blender. All candidate and source polygon normal flags are independently verified false. Generator control/boundary evidence is hash-bound separately. No renderer geometry operation, selective mask, added ornament, modifier, remesh, Boolean, image crop or synthesis. Geometry and aesthetic quality require actual visual review.')
    (output / 'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    gc.collect()
    print('COMB_SCALE_REFINEMENT_FLAT_RENDER_DONE: 4 actual PNGs, candidate saved coordinates/indices and all-flat flags verified', flush=True)


if __name__ == '__main__':
    main()
