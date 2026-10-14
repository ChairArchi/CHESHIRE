"""All-flat diagnostic of the same saved ACCENT body; no new geometry or mask."""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
CORE = HERE / 'render.py'
CORE_SHA256 = 'c544eaa4633ac07a0e9ae3fd42cc5bc2b500065be8c232158bccd13409543e73'
SOURCE_FLAT_RECEIPT = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/REVISED_FLAT/views/receipt.json')
SOURCE_FLAT_RECEIPT_SHA256 = '28d2e6a0eb9229901bba3c3f57faf35fb86461f0d6843128ad10a9cde76ac995'
spec = importlib.util.spec_from_file_location('diagonal_facet_preserved_selective_renderer', CORE)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
digest, read_json, require_close = core.digest, core.read_json, core.require_close
DEFAULT_ROOT = core.DEFAULT_ROOT


def code_hashes():
    if digest(CORE) != CORE_SHA256:
        raise ValueError('Preserved selective renderer changed.')
    return dict(render_allflat=digest(__file__), selective_renderer_sha256=CORE_SHA256,
        preserved_selective_code=core.code_hashes())


def source_flat_state(binding):
    """Reuse the actual same source body, rendered previously with all-flat flags."""
    import numpy as np
    if digest(SOURCE_FLAT_RECEIPT) != SOURCE_FLAT_RECEIPT_SHA256:
        raise ValueError('Preserved same-source flat receipt changed.')
    receipt = read_json(SOURCE_FLAT_RECEIPT)
    expected = binding['saved_source']
    if (receipt.get('state') != 'REVISED_FLAT' or receipt.get('saved_geometry') != expected or
            Path(receipt.get('geometry_path', '')).resolve() != core.SOURCE.resolve() or
            receipt.get('code_sha256') != core.scaffold.code_hashes() or
            receipt.get('geometry_unchanged_in_renderer') is not True or
            receipt.get('smooth_shading') is not False or receipt.get('geometry_smoothing') is not False or
            receipt.get('geometry_processing') is not False or receipt.get('modifiers') != [] or
            receipt.get('normal_interpolation_only') is not False or receipt.get('remesh') is not False or
            receipt.get('Boolean_fusion') is not False or receipt.get('ornaments_added') is not False):
        raise ValueError('Actual same-source all-flat native render required.')
    candidate = receipt.get('candidate_binding', {})
    if (candidate.get('receipt_sha256') != core.SOURCE_RECEIPT_SHA256 or candidate.get('variant') != expected):
        raise ValueError('Preserved source all-flat geometry binding differs.')
    core.scaffold.verify_snapshot(receipt['render_source_snapshot'])
    counts, readback = receipt['geometry_counts'], receipt['display_readback']
    if (counts['source_arrays'] != {key: expected[key] for key in ('xyz_sha256', 'faces_sha256')} or
            any(counts[key] != expected[key] for key in ('vertices', 'triangles')) or
            readback.get('geometry') != counts['expected_display_arrays'] or
            readback.get('smooth_polygons') != 0 or readback.get('all_use_smooth') is not False or
            readback.get('geometry_unchanged') is not True or readback.get('modifiers') != [] or
            readback.get('use_smooth_flags_sha256') != core.array_hash(np.zeros(expected['triangles'], bool))):
        raise ValueError('Actual same-source flat coordinates/indices/flags readback differs.')
    require_close(receipt['conditions'], dict(binding['reference_conditions'], smooth_polygons=0))
    require_close(receipt['views'], binding['views'])
    if receipt['version'] != binding['reference_Blender_version']:
        raise ValueError('Same-source all-flat Blender version differs.')
    records = receipt.get('images')
    if (not isinstance(records, list) or len(records) != 4 or
            {item['view'] for item in records} != set(binding['views'])):
        raise ValueError('Four actual preserved source all-flat images required.')
    images = []
    for item in records:
        view = item['view']
        png = SOURCE_FLAT_RECEIPT.parent / (view + '.png')
        if item['filename'] != png.name or digest(png) != item['sha256']:
            raise ValueError('Actual same-source flat PNG changed.')
        core.scaffold.verify_native_png(png)
        require_close(receipt['actual_views'][view], binding['actual_reference_views'][view], 'same-source-flat-camera.' + view)
        images.append(dict(view=view, path=str(png), sha256=item['sha256'], reused_reference=True,
            receipt=str(SOURCE_FLAT_RECEIPT), receipt_sha256=SOURCE_FLAT_RECEIPT_SHA256))
    return dict(state='SOURCE_FLAT', saved_geometry=expected, images=images,
        display_readback=readback, geometry_counts=counts, conditions=receipt['conditions'],
        actual_views=receipt['actual_views'], Blender_version=receipt['version'],
        source_receipt=str(SOURCE_FLAT_RECEIPT), source_receipt_sha256=SOURCE_FLAT_RECEIPT_SHA256)


def allflat_state(root):
    binding = core.source_binding(root)
    path, expected, candidate = core.candidate_state(root, binding)
    source_flat = source_flat_state(binding)
    return binding, path, expected, candidate, source_flat


def snapshot_source(root):
    source = Path(__file__).resolve()
    relative = Path('experiments') / HERE.name / source.name
    target = Path(root) / 'source_snapshot_allflat' / relative
    checksum = digest(source)
    if target.exists():
        if digest(target) != checksum:
            raise ValueError('Earlier all-flat diagnostic source snapshot differs.')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    record = dict(source=str(source), relative_path=relative.as_posix(), snapshot=str(target), sha256=checksum)
    verify_snapshot(record)
    return record


def verify_snapshot(record):
    if (record.get('sha256') != digest(__file__) or
            any(digest(record[key]) != record['sha256'] for key in ('source', 'snapshot'))):
        raise ValueError('Actual all-flat diagnostic source/snapshot changed.')


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    if root == core.SOURCE.parent.resolve() or core.SOURCE.parent.resolve() in root.parents:
        raise ValueError('Preserved source is read-only.')
    output = root / 'ACCENT_FLAT/views'
    if output.exists():
        raise FileExistsError('Earlier actual all-flat diagnostic render preserved.')
    hashes = code_hashes()
    binding, path, expected, candidate, source_flat = allflat_state(root)
    snapshot = snapshot_source(root)
    shared = core.scaffold.setup_scene()
    obj, counts = core.scaffold.add_native_object(path, expected, 'Same saved ACCENT all-flat diagnostic', shared)
    core.scaffold.set_smooth_flags(obj, False)
    before = core.scaffold.geometry_signature(obj, counts, False)
    scene, camera = shared.setup_scene(900, 24)
    conditions = core.base.actual_conditions(bpy, scene, camera, obj)
    require_close(conditions, source_flat['conditions'])
    require_close(conditions, core.base.expected_conditions())
    if bpy.app.version_string != source_flat['Blender_version']:
        raise ValueError('Source/candidate all-flat Blender versions differ.')
    actual_views, images = core.scaffold.render_views(scene, camera, binding['views'], output)
    for view in actual_views:
        require_close(actual_views[view], source_flat['actual_views'][view], 'matched-all-flat-camera.' + view)
    after = core.scaffold.geometry_signature(obj, counts, False)
    if (before != after or after['geometry']['triangle_indices_int32_sha256'] !=
            source_flat['display_readback']['geometry']['triangle_indices_int32_sha256'] or
            after['use_smooth_flags_sha256'] != source_flat['display_readback']['use_smooth_flags_sha256']):
        raise ValueError('Actual saved coordinates/indices/all-flat flags changed or differ between bodies.')
    verify_snapshot(snapshot)
    if code_hashes() != hashes or allflat_state(root) != (binding, path, expected, candidate, source_flat):
        raise ValueError('Actual same-source/candidate/reference/code binding changed during diagnosis.')
    result = dict(state='ACCENT_FLAT', kind='SAME_SAVED_ACCENT_BODY_ALL_FLAT_RENDER_DIAGNOSTIC',
        source_binding=binding, candidate_binding=candidate, source_flat_reference=source_flat,
        geometry_path=str(path), saved_geometry=expected, geometry_counts=counts, display_readback=after,
        geometry_unchanged_in_renderer=True, geometry_processing=False, geometry_smoothing=False,
        shading='ALL_FLAT_NATIVE_TRIANGLES', smooth_shading=False, smooth_polygons=0,
        normal_maps=False, modifiers=[], remesh=False, Boolean_fusion=False, ornaments_added=False,
        new_geometry_experiment=False, same_saved_ACCENT_geometry=True, selective_mask_used=False,
        selective_mask_modified=False, source_growth_generation=7, new_source_growth_G8=False,
        version=bpy.app.version_string, conditions=conditions, views=binding['views'],
        actual_views=actual_views, images=images, code_sha256=hashes, render_source_snapshot=snapshot,
        scope='Rendering diagnosis of the exact already-saved ACCENT geometry under all-flat native polygon normals. The exact same source body\'s existing four all-flat PNGs are reused. No geometry, selective mask or prior render is changed. Actual coordinates, native indices and all-false use_smooth flags are read back unchanged. This isolates visibility under old flat shading and does not certify geometric or aesthetic improvement.')
    core.write_json(output / 'receipt.json', result)
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    gc.collect()
    print('DIAGONAL_FACET_ALL_FLAT_DONE: same saved ACCENT, 4 actual PNGs, native geometry/indices/all-flat flags verified', flush=True)


if __name__ == '__main__':
    main()
