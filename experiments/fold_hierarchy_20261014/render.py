"""Render one hierarchy update and its parent-scale finish at four frozen cameras.

Two distinct comparisons are retained: bare source versus hierarchy, and the
accepted detailed design versus the new finished design. No geometry operation
or selective shading occurs in this renderer.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/fold_hierarchy_20261014/trial01')
PRESERVED = HERE.parent / 'comb_scale_refinement_20261014/render.py'
PRESERVED_SHA256 = '8a82a55ed86afbbd923e7252ad2508844c19814bfe54f1f1f7d238d58b7324fb'
CURRENT_RECEIPT = Path('E:/CHESHIRE_DATA/experiments/comb_scale_refinement_20261014/trial01/RECEIPT.json')
CURRENT_RECEIPT_SHA256 = '507e9feaec57f86b709fec6a5cca5ac426dd74fcd2a97e5ca3d2b4c7d2748c37'
CURRENT_GEOMETRY = CURRENT_RECEIPT.parent / 'REFINED/geometry.npz'
CURRENT_GEOMETRY_SHA256 = '37549b71c997a65943fbb6416d008b748ecba4ab05898eadfea95bc994e3a710'
CURRENT_FLAT = CURRENT_RECEIPT.parent / 'REFINED_FLAT/views/receipt.json'
CURRENT_FLAT_SHA256 = 'fa4c19d07557915d1233f6b6b062c8561b390898da2425d2bdcc0f45c2039b3a'
SOURCE_CONTROL = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/REVISED/control_quad.npz')
SOURCE_CONTROL_SHA256 = '0915ac8f56509768c6329a7d848793c6936b903d4d9316e01b1076a76aba8e27'
spec = importlib.util.spec_from_file_location('hierarchy_preserved_renderer', PRESERVED)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
scaffold = previous.scaffold
digest, read_json, require_close = scaffold.digest, scaffold.read_json, scaffold.require_close
array_hash, base = scaffold.array_hash, scaffold.base


def canonical(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def code_hashes():
    if digest(PRESERVED) != PRESERVED_SHA256:
        raise ValueError('Preserved renderer changed.')
    return dict(render=digest(__file__), preserved_renderer_sha256=PRESERVED_SHA256,
                preserved_renderer_code=previous.code_hashes())


def display_proof(receipt, expected):
    import numpy as np
    counts, readback = receipt['geometry_counts'], receipt['display_readback']
    if (counts['source_arrays'] != {key: expected[key] for key in ('xyz_sha256', 'faces_sha256')} or
            any(counts[key] != expected[key] for key in ('vertices', 'triangles')) or
            readback.get('geometry') != counts['expected_display_arrays'] or
            readback.get('smooth_polygons') != 0 or readback.get('all_use_smooth') is not False or
            readback.get('geometry_unchanged') is not True or readback.get('modifiers') != [] or
            readback.get('use_smooth_flags_sha256') != array_hash(np.zeros(expected['triangles'], bool))):
        raise ValueError('Actual saved coordinates/indices/all-flat readback differs.')
    return counts, readback


def image_records(receipt, receipt_path, binding, reused):
    records = receipt.get('images')
    if (not isinstance(records, list) or len(records) != 4 or
            {item['view'] for item in records} != set(binding['views'])):
        raise ValueError('Exactly four actual frozen-camera images required.')
    images = []
    for item in records:
        view = item['view']
        png = receipt_path.parent / (view + '.png')
        if item['filename'] != png.name or digest(png) != item['sha256']:
            raise ValueError('Actual source PNG differs.')
        scaffold.verify_native_png(png)
        require_close(receipt['actual_views'][view], binding['actual_reference_views'][view], 'matched-camera.' + view)
        images.append(dict(view=view, path=str(png), sha256=item['sha256'], reused_reference=reused,
                           receipt=str(receipt_path), receipt_sha256=digest(receipt_path)))
    return images


def fixed_sources():
    bare_binding = previous.previous.fixed_source_binding()
    bare = previous.previous.source_flat_state(bare_binding)
    bare['state'] = 'SOURCE_BARE_REVISED_FLAT'
    if (digest(CURRENT_RECEIPT) != CURRENT_RECEIPT_SHA256 or
            digest(CURRENT_GEOMETRY) != CURRENT_GEOMETRY_SHA256 or digest(CURRENT_FLAT) != CURRENT_FLAT_SHA256):
        raise ValueError('Accepted detailed design source changed.')
    expected = read_json(CURRENT_RECEIPT).get('variants', {}).get('REFINED')
    if (not isinstance(expected, dict) or Path(expected.get('geometry', '')).resolve() != CURRENT_GEOMETRY.resolve() or
            expected.get('geometry_sha256') != CURRENT_GEOMETRY_SHA256):
        raise ValueError('Accepted detailed design binding differs.')
    receipt = read_json(CURRENT_FLAT)
    if (receipt.get('state') != 'REFINED_FLAT' or receipt.get('saved_geometry') != expected or
            Path(receipt.get('geometry_path', '')).resolve() != CURRENT_GEOMETRY.resolve() or
            receipt.get('code_sha256') != previous.code_hashes() or
            receipt.get('candidate_binding') != canonical(dict(receipt=str(CURRENT_RECEIPT),
                receipt_sha256=CURRENT_RECEIPT_SHA256, variant=expected)) or
            receipt.get('geometry_unchanged_in_renderer') is not True or
            receipt.get('shading') != 'ALL_FLAT_NATIVE_TRIANGLES' or
            receipt.get('smooth_shading') is not False or receipt.get('smooth_polygons') != 0 or
            receipt.get('geometry_processing') is not False or receipt.get('geometry_smoothing') is not False or
            receipt.get('modifiers') != [] or receipt.get('normal_maps') is not False or
            receipt.get('remesh') is not False or receipt.get('Boolean_fusion') is not False):
        raise ValueError('Accepted detailed source actual flat render provenance differs.')
    previous.verify_snapshot(receipt['render_source_snapshot'])
    counts, readback = display_proof(receipt, expected)
    require_close(receipt['conditions'], bare_binding['reference_conditions'])
    require_close(receipt['views'], bare_binding['views'])
    if receipt['version'] != bare_binding['reference_Blender_version']:
        raise ValueError('Reference Blender version differs.')
    current = dict(state='CURRENT_REFINED_FLAT', saved_geometry=expected,
        images=image_records(receipt, CURRENT_FLAT, bare_binding, True), geometry_counts=counts,
        display_readback=readback, conditions=receipt['conditions'], actual_views=receipt['actual_views'],
        Blender_version=receipt['version'], source_receipt=str(CURRENT_FLAT),
        source_receipt_sha256=CURRENT_FLAT_SHA256)
    binding = canonical(dict(views=bare_binding['views'],
        actual_reference_views=bare_binding['actual_reference_views'],
        reference_conditions=bare_binding['reference_conditions'],
        reference_Blender_version=bare_binding['reference_Blender_version'],
        camera_placement=bare_binding['camera_placement'], camera_placement_sha256=bare_binding['camera_placement_sha256'],
        bare_source=bare_binding, accepted_design_geometry=str(CURRENT_GEOMETRY),
        accepted_design_geometry_sha256=CURRENT_GEOMETRY_SHA256,
        accepted_design_receipt=str(CURRENT_RECEIPT), accepted_design_receipt_sha256=CURRENT_RECEIPT_SHA256))
    return binding, canonical(bare), canonical(current)


def candidate_states(root):
    path = root / 'RECEIPT.json'
    info = read_json(path)
    if (Path(info.get('source_control_path', '')).resolve() != SOURCE_CONTROL.resolve() or
            info.get('source_control_sha256') != SOURCE_CONTROL_SHA256 or
            digest(SOURCE_CONTROL) != SOURCE_CONTROL_SHA256 or
            Path(info.get('design_source_native_path', '')).resolve() != CURRENT_GEOMETRY.resolve() or
            info.get('design_source_native_geometry_sha256') != CURRENT_GEOMETRY_SHA256):
        raise ValueError('Actual generator source control and accepted design binding differ.')
    snapshots = info.get('source_snapshots')
    if not isinstance(snapshots, dict) or not snapshots:
        raise ValueError('Actual executed generator snapshots required.')
    for record in snapshots.values():
        if any(digest(record[key]) != record.get('sha256') for key in ('source', 'snapshot')):
            raise ValueError('Actual executed generator source/snapshot differs.')
    variants = info.get('variants')
    if not isinstance(variants, dict) or set(variants) != {'HIERARCHY', 'FINISHED'}:
        raise ValueError('Exactly HIERARCHY and FINISHED saved variants required.')
    candidates = {}
    for state, expected in variants.items():
        geometry = root / state / 'geometry.npz'
        if (Path(expected.get('geometry', '')).resolve() != geometry.resolve() or
                digest(geometry) != expected.get('geometry_sha256')):
            raise ValueError('Actual saved candidate differs: ' + state)
        for key in ('vertices', 'triangles'):
            if isinstance(expected.get(key), bool) or not isinstance(expected.get(key), int) or expected[key] <= 0:
                raise ValueError('Actual native counts required.')
        for key in ('geometry_sha256', 'xyz_sha256', 'faces_sha256'):
            if not isinstance(expected.get(key), str) or len(expected[key]) != 64:
                raise ValueError('Actual candidate array hashes required.')
        candidates[state] = canonical(dict(receipt=str(path), receipt_sha256=digest(path), variant=expected))
    a, b = variants['HIERARCHY'], variants['FINISHED']
    if any(a[key] != b[key] for key in ('vertices', 'triangles', 'faces_sha256')):
        raise ValueError('The two new bodies must share exact native connectivity/counts.')
    return candidates


def saved_state(root):
    binding, bare, current = fixed_sources()
    return binding, bare, current, candidate_states(root)


def snapshot_source(root):
    source = Path(__file__).resolve()
    relative = Path('experiments') / HERE.name / source.name
    target = root / 'source_snapshot_render' / relative
    checksum = digest(source)
    if target.exists():
        if digest(target) != checksum:
            raise ValueError('Earlier renderer snapshot differs.')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    record = dict(source=str(source), relative_path=relative.as_posix(), snapshot=str(target), sha256=checksum)
    verify_snapshot(record)
    return record


def verify_snapshot(record):
    if (record.get('sha256') != digest(__file__) or
            any(digest(record[key]) != record['sha256'] for key in ('source', 'snapshot'))):
        raise ValueError('Actual renderer source/snapshot differs.')


def render_variant(root, state, binding, bare, current, candidates, snapshot, hashes):
    import bpy
    output = root / (state + '_FLAT') / 'views'
    if output.exists():
        raise FileExistsError('Earlier actual render preserved: ' + str(output))
    candidate = candidates[state]
    expected = candidate['variant']
    path = Path(expected['geometry'])
    shared = scaffold.setup_scene()
    obj, counts = scaffold.add_native_object(path, expected, 'Actual saved ' + state, shared)
    scaffold.set_smooth_flags(obj, False)
    before = scaffold.geometry_signature(obj, counts, False)
    scene, camera = shared.setup_scene(900, 24)
    conditions = base.actual_conditions(bpy, scene, camera, obj)
    require_close(conditions, binding['reference_conditions'])
    require_close(conditions, base.expected_conditions())
    if bpy.app.version_string != binding['reference_Blender_version']:
        raise ValueError('Source and candidate Blender versions differ.')
    actual_views, images = scaffold.render_views(scene, camera, binding['views'], output)
    for view in actual_views:
        require_close(actual_views[view], binding['actual_reference_views'][view], 'matched-native-camera.' + view)
    after = scaffold.geometry_signature(obj, counts, False)
    if before != after:
        raise ValueError('Actual saved coordinates/native indices/all-flat flags changed while rendering.')
    verify_snapshot(snapshot)
    if code_hashes() != hashes or candidate_states(root) != candidates:
        raise ValueError('Actual candidate/source code changed during rendering.')
    result = dict(state=state + '_FLAT', kind='ACTUAL_SAVED_HIERARCHY_UPDATE_ALL_FLAT_RENDER',
        source_binding=binding, candidate_binding=candidate,
        comparison_reference=bare if state == 'HIERARCHY' else current,
        comparison_scope='Bare geometry hierarchy only' if state == 'HIERARCHY' else 'Combined hierarchy and larger-scale surface finish',
        geometry_path=str(path), saved_geometry=expected, geometry_counts=counts, display_readback=after,
        geometry_unchanged_in_renderer=True, geometry_processing=False, geometry_smoothing=False,
        shading='ALL_FLAT_NATIVE_TRIANGLES', smooth_shading=False, smooth_polygons=0,
        normal_maps=False, modifiers=[], remesh=False, Boolean_fusion=False, ornaments_added=False,
        selective_mask_dependency=False, source_growth_generation=7, new_source_growth_G8=False,
        generator_validation_evidence=expected.get('validation'),
        generator_validation_scope='Hash-bound generator evidence carried without certifying aesthetic success or global collisions.',
        version=bpy.app.version_string, conditions=conditions, views=binding['views'], actual_views=actual_views,
        images=images, code_sha256=hashes, render_source_snapshot=snapshot,
        scope='Four actual saved-mesh PNGs with unchanged coordinates/indices and all-flat flags verified before and after rendering. The hierarchy comparison uses bare source; the final design comparison uses the accepted detailed design, whose topology differs. These comparisons are separate and do not attribute combined design changes solely to hierarchy or solely to texture. No renderer geometry processing, smoothing, selective mask, modifier, normal map, image synthesis or new G8.')
    (output / 'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    gc.collect()
    print('FOLD_HIERARCHY_RENDERED', state, '4 actual PNGs, geometry/all-flat readbacks verified', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--phase', choices=('hierarchy', 'finished', 'all'), default='all')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    if root == CURRENT_RECEIPT.parent.resolve() or CURRENT_RECEIPT.parent.resolve() in root.parents:
        raise ValueError('Preserved design source is read-only.')
    hashes = code_hashes()
    binding, bare, current, candidates = saved_state(root)
    snapshot = snapshot_source(root)
    phases = ('HIERARCHY', 'FINISHED') if args.phase == 'all' else (args.phase.upper(),)
    for state in phases:
        render_variant(root, state, binding, bare, current, candidates, snapshot, hashes)
    if fixed_sources() != (binding, bare, current):
        raise ValueError('Actual preserved source/reference changed during rendering.')
    print('FOLD_HIERARCHY_RENDER_PHASE_DONE', args.phase, flush=True)


if __name__ == '__main__':
    main()
