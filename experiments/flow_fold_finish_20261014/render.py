"""Render one flow-aligned surface finish against the accepted detailed design."""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/flow_fold_finish_20261014/trial01')
PRESERVED = HERE.parent / 'fold_hierarchy_20261014/render.py'
PRESERVED_SHA256 = 'f38dbaea29bdd71ef6000f64328bdd4db7515404901253365ce072588c2db141'
spec = importlib.util.spec_from_file_location('flow_finish_frozen_renderer', PRESERVED)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
scaffold, base = previous.scaffold, previous.base
digest, read_json, require_close = previous.digest, previous.read_json, previous.require_close
array_hash = previous.array_hash
SOURCE_CONTROL, SOURCE_CONTROL_SHA256 = previous.SOURCE_CONTROL, previous.SOURCE_CONTROL_SHA256
CURRENT_GEOMETRY, CURRENT_GEOMETRY_SHA256 = previous.CURRENT_GEOMETRY, previous.CURRENT_GEOMETRY_SHA256


def code_hashes():
    if digest(PRESERVED) != PRESERVED_SHA256:
        raise ValueError('Preserved renderer changed.')
    return dict(render=digest(__file__), preserved_renderer_sha256=PRESERVED_SHA256,
                preserved_renderer_code=previous.code_hashes())


def candidate_state(root, bare):
    path = root / 'RECEIPT.json'
    info = read_json(path)
    if (Path(info.get('source_control_path', '')).resolve() != SOURCE_CONTROL.resolve() or
            info.get('source_control_sha256') != SOURCE_CONTROL_SHA256 or
            digest(SOURCE_CONTROL) != SOURCE_CONTROL_SHA256 or
            Path(info.get('design_source_native_path', '')).resolve() != CURRENT_GEOMETRY.resolve() or
            info.get('design_source_native_geometry_sha256') != CURRENT_GEOMETRY_SHA256):
        raise ValueError('Actual generator control and accepted design source differ.')
    snapshots = info.get('source_snapshots')
    if not isinstance(snapshots, dict) or not snapshots:
        raise ValueError('Executed source snapshots required.')
    for record in snapshots.values():
        if any(digest(record[key]) != record.get('sha256') for key in ('source', 'snapshot')):
            raise ValueError('Executed generator source/snapshot differs.')
    variants = info.get('variants')
    if not isinstance(variants, dict) or set(variants) != {'FLOW'}:
        raise ValueError('Exactly one FLOW saved body required.')
    expected = variants['FLOW']
    geometry = root / 'FLOW/geometry.npz'
    if (Path(expected.get('geometry', '')).resolve() != geometry.resolve() or
            digest(geometry) != expected.get('geometry_sha256')):
        raise ValueError('Actual saved FLOW geometry differs.')
    for key in ('vertices', 'triangles', 'faces_sha256'):
        if expected.get(key) != bare['saved_geometry'][key]:
            raise ValueError('FLOW must preserve actual original native fan topology/counts.')
    for key in ('geometry_sha256', 'xyz_sha256', 'faces_sha256'):
        if not isinstance(expected.get(key), str) or len(expected[key]) != 64:
            raise ValueError('Actual native file/array hashes required.')
    return previous.canonical(dict(receipt=str(path), receipt_sha256=digest(path), variant=expected))


def saved_state(root):
    binding, bare, current = previous.fixed_sources()
    return binding, current, candidate_state(root, bare)


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


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    if root == CURRENT_GEOMETRY.parent.resolve() or CURRENT_GEOMETRY.parent.resolve() in root.parents:
        raise ValueError('Preserved design source is read-only.')
    output = root / 'FLOW_FLAT/views'
    if output.exists():
        raise FileExistsError('Earlier actual render preserved.')
    hashes = code_hashes()
    binding, current, candidate = saved_state(root)
    expected = candidate['variant']
    path = Path(expected['geometry'])
    snapshot = snapshot_source(root)
    shared = scaffold.setup_scene()
    obj, counts = scaffold.add_native_object(path, expected, 'Actual saved flow-aligned folds', shared)
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
        raise ValueError('Saved geometry/native indices/all-flat flags changed while rendering.')
    verify_snapshot(snapshot)
    if code_hashes() != hashes or saved_state(root) != (binding, current, candidate):
        raise ValueError('Actual source/candidate/code binding changed during rendering.')
    result = dict(state='FLOW_FLAT', kind='ACTUAL_SAVED_FLOW_ALIGNED_FOLD_FINISH_ALL_FLAT_RENDER',
        source_binding=binding, candidate_binding=candidate, comparison_reference=current,
        comparison_scope='Accepted detailed design versus one new flow-aligned surface finish; saved native topology differs between these two bodies.',
        geometry_path=str(path), saved_geometry=expected, geometry_counts=counts, display_readback=after,
        geometry_unchanged_in_renderer=True, geometry_processing=False, geometry_smoothing=False,
        shading='ALL_FLAT_NATIVE_TRIANGLES', smooth_shading=False, smooth_polygons=0,
        normal_maps=False, modifiers=[], remesh=False, Boolean_fusion=False, ornaments_added=False,
        selective_mask_dependency=False, source_growth_generation=7, new_source_growth_G8=False,
        generator_validation_evidence=expected.get('validation'),
        generator_validation_scope='Hash-bound generator evidence carried without independently certifying aesthetic success or global collisions.',
        version=bpy.app.version_string, conditions=conditions, views=binding['views'], actual_views=actual_views,
        images=images, code_sha256=hashes, render_source_snapshot=snapshot,
        scope='Four actual saved-mesh PNGs with unchanged coordinates/indices and all-flat flags verified before and after rendering. Accepted REFINED images are reused under identical cameras/material/lights/shading. Bare source is used only for topology and frozen camera provenance, not displayed as the final design comparison. No renderer geometry operation, smoothing, selective mask, modifier, normal map or synthesized image.')
    (output / 'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    gc.collect()
    print('FLOW_FOLD_FINISH_RENDER_DONE: 4 actual PNGs; saved coordinates/native indices/all-flat readbacks verified', flush=True)


if __name__ == '__main__':
    main()
