"""Render the actual saved parent-guarded G7 candidate against NESTED02.

This is separate from the preserved-control display audit. Candidate geometry
comes only from its actual generation receipt; the renderer changes no shape.
"""
from pathlib import Path
import argparse
import importlib.util
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path('E:/CHESHIRE_DATA/experiments/parent_continuity_20261014/trial01')
PRESERVED = HERE.parent/'ordered_primary_folds_20261014/render.py'
PRESERVED_SHA = 'a5973a77346ab068b24f6dd659e4dc6804337a649240702ac4a2a3a167ccda06'
VARIANT = 'PARENT_GUARDED'
VIEWS = ('close_oblique', 'body_oblique', 'front')
spec = importlib.util.spec_from_file_location('continuity_candidate_preserved_renderer', PRESERVED)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
scaffold, base = previous.scaffold, previous.base
digest, read_json, write = previous.digest, previous.read_json, previous.write
verify_snapshot, require_close = previous.verify_snapshot, previous.require_close
source_binding = previous.source_binding


def code_hashes():
    if digest(PRESERVED) != PRESERVED_SHA:
        raise ValueError('Preserved actual NESTED02 render adapter changed.')
    return dict(renderer=digest(__file__), preserved_renderer_sha256=PRESERVED_SHA,
                preserved_renderer_code=previous.code_hashes())


def candidate_state(root, binding):
    receipt_path = root/'RECEIPT.json'
    receipt = read_json(receipt_path)
    if (Path(receipt.get('comparison_source_native_path', '')).resolve() !=
            Path(binding['source_native_path']).resolve() or
            receipt.get('comparison_source_native_geometry_sha256') !=
            binding['source_native_geometry_sha256']):
        raise ValueError('Actual candidate must bind to the preserved NESTED02 source.')
    variants = receipt.get('variants')
    if not isinstance(variants, dict) or set(variants) != {VARIANT}:
        raise ValueError('Exactly one actual PARENT_GUARDED candidate required.')
    expected = variants[VARIANT]
    geometry = root/VARIANT/'geometry.npz'
    if (Path(expected.get('geometry', '')).resolve() != geometry.resolve() or
            digest(geometry) != expected.get('geometry_sha256') or
            any(expected.get(key) != binding['saved_geometry'][key]
                for key in ('faces_sha256', 'vertices', 'triangles'))):
        raise ValueError('Saved candidate or original G7 native connectivity differs.')
    snapshots = receipt.get('source_snapshots')
    if not isinstance(snapshots, dict) or not snapshots:
        raise ValueError('Actual executed generator source snapshots required.')
    for record in snapshots.values():
        verify_snapshot(record)
    return expected, dict(receipt=str(receipt_path), receipt_sha256=digest(receipt_path))


def snapshot(root):
    source = Path(__file__).resolve()
    target = root/'source_snapshot_render/experiments'/HERE.name/source.name
    if target.exists():
        raise FileExistsError('Earlier actual candidate renderer snapshot preserved.')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    record = dict(source=str(source), snapshot=str(target), sha256=digest(source))
    verify_snapshot(record)
    return record


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    output = root/(VARIANT+'_FLAT')/'review'
    if output.exists():
        raise FileExistsError('Earlier actual candidate render preserved.')
    binding = source_binding()
    expected, candidate = candidate_state(root, binding)
    hashes, snap = code_hashes(), snapshot(root)
    shared = scaffold.setup_scene()
    obj, counts = scaffold.add_native_object(Path(expected['geometry']), expected,
                                             'Actual saved parent-guarded G7 column', shared)
    scaffold.set_smooth_flags(obj, False)
    scene, camera = shared.setup_scene(900, 24)
    conditions = base.actual_conditions(bpy, scene, camera, obj)
    require_close(conditions, binding['conditions'])
    if bpy.app.version_string != binding['Blender_version']:
        raise ValueError('Actual source/candidate Blender version differs.')
    before = scaffold.geometry_signature(obj, counts, False)
    actual_views, images = scaffold.render_views(scene, camera, binding['views'], output)
    after = scaffold.geometry_signature(obj, counts, False)
    if before != after:
        raise ValueError('Actual saved mesh or all-flat flags changed during rendering.')
    for view in VIEWS:
        require_close(actual_views[view], binding['actual_views'][view], 'matched-camera.'+view)
    if (source_binding() != binding or candidate_state(root, binding) != (expected, candidate) or
            code_hashes() != hashes):
        raise ValueError('Actual source/candidate/code changed during rendering.')
    verify_snapshot(snap)
    result = dict(state=VARIANT, phase='review', saved_geometry=expected, candidate_binding=candidate,
        source_binding=binding, geometry_counts=counts, display_readback=after, conditions=conditions,
        actual_views=actual_views, images=images, geometry_unchanged_by_renderer=True, all_flat=True,
        geometry_processing=False, normal_maps=False, modifiers=[], version=bpy.app.version_string,
        code_sha256=hashes, source_snapshot=snap, diagnostic_display_fan=False,
        comparison_scope='Actual saved PARENT_GUARDED G7 candidate versus latest NESTED02. Existing baseline PNGs are reused. Same cameras, material, lights, resolution, samples, native faces/counts and all-flat shading. This candidate renderer does not load audit01 display derivatives, process geometry or add normal-map detail.')
    previous.previous.previous.frozen.previous.display_proof(result, expected)
    write(output/'receipt.json', result)
    print('PARENT_GUARDED_RENDER_DONE: three actual close/body/front PNGs; saved geometry and all-flat readbacks verified', flush=True)


if __name__ == '__main__':
    main()
