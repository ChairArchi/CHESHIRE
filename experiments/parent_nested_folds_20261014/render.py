"""Render the saved parent-nested candidate against the latest COHERENT_FLOW.

The previous review images are reused under their actual frozen conditions.
Only the new saved mesh is loaded; no geometry or shading correction occurs.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path('E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial01')
PRESERVED = HERE.parent/'end_continuity_20261014/render_finish.py'
PRESERVED_SHA = '019b2b9746d6a3eeef5a10886fe876bd9fe7aa0d0b2bfdeb753597c6bba704a2'
BASE = Path('E:/CHESHIRE_DATA/experiments/end_continuity_20261014/trial02')
BASE_RECEIPT_SHA = 'a7cb4e8934df4af5a98efb2978f22eff74c1f4eda129ed7079a15aa3ff26abe3'
BASE_RENDER_SHA = '7391bf039e5928e3beb526ff155009bb1f31248ffec2265cb13a5fc531bc5860'
BASE_GEOMETRY_SHA = 'e7adee3cd77d4882143aba82623e8cf839193c693866ab21315b410fb05bd34c'
VIEWS = ('close_oblique', 'body_oblique', 'front')
spec = importlib.util.spec_from_file_location('parent_nested_preserved_renderer', PRESERVED)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
scaffold, base = previous.scaffold, previous.base
digest, read_json, require_close = previous.digest, previous.read_json, previous.require_close


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')


def code_hashes():
    if digest(PRESERVED) != PRESERVED_SHA:
        raise ValueError('Preserved actual render code changed.')
    return dict(renderer=digest(__file__), preserved_renderer_sha256=PRESERVED_SHA,
                preserved_renderer_code=previous.code_hashes())


def verify_snapshot(record):
    if any(digest(record[key]) != record['sha256'] for key in ('source', 'snapshot')):
        raise ValueError('Executed source/snapshot changed.')


def source_binding():
    receipt_path = BASE/'RECEIPT.json'
    render_path = BASE/'COHERENT_FLOW_FLAT/review/receipt.json'
    if digest(receipt_path) != BASE_RECEIPT_SHA or digest(render_path) != BASE_RENDER_SHA:
        raise ValueError('Latest COHERENT_FLOW actual receipts changed.')
    expected = read_json(receipt_path)['variants']['COHERENT_FLOW']
    geometry = Path(expected['geometry'])
    if digest(geometry) != BASE_GEOMETRY_SHA or expected['geometry_sha256'] != BASE_GEOMETRY_SHA:
        raise ValueError('Latest COHERENT_FLOW actual saved source changed.')
    r = read_json(render_path)
    if (r['saved_geometry'] != expected or
            r['candidate_binding'] != dict(receipt=str(receipt_path), receipt_sha256=BASE_RECEIPT_SHA) or
            r['code_sha256'] != previous.code_hashes() or r['state'] != 'COHERENT_FLOW' or
            r['phase'] != 'review' or r['geometry_unchanged_by_renderer'] is not True or
            r['all_flat'] is not True or r['geometry_processing'] is not False or
            r['normal_maps'] is not False or r['modifiers'] != []):
        raise ValueError('Latest COHERENT_FLOW all-flat render provenance differs.')
    verify_snapshot(r['source_snapshot'])
    previous.frozen.previous.display_proof(r, expected)
    require_close(r['conditions'], base.expected_conditions())
    if (set(r['actual_views']) != set(VIEWS) or len(r['images']) != len(VIEWS) or
            {item['view'] for item in r['images']} != set(VIEWS)):
        raise ValueError('Latest actual close/body/front source images required.')
    images = []
    for item in r['images']:
        view = item['view']
        image = render_path.parent/(view+'.png')
        if item['filename'] != image.name or digest(image) != item['sha256']:
            raise ValueError('Latest COHERENT_FLOW actual source image changed.')
        scaffold.verify_native_png(image)
        require_close(r['actual_views'][view], r['source_binding']['actual_views'][view],
                      'actual-source-camera.'+view)
        images.append(dict(view=view, path=str(image), sha256=item['sha256'],
                           reused_reference=True, receipt=str(render_path),
                           receipt_sha256=BASE_RENDER_SHA))
    return dict(state='CURRENT_COHERENT_FLOW', source_native_path=str(geometry),
        source_native_geometry_sha256=BASE_GEOMETRY_SHA,
        source_receipt=str(receipt_path), source_receipt_sha256=BASE_RECEIPT_SHA,
        source_render_receipt=str(render_path), source_render_receipt_sha256=BASE_RENDER_SHA,
        saved_geometry=expected, views={v:r['source_binding']['views'][v] for v in VIEWS},
        actual_views=r['actual_views'], conditions=r['conditions'], Blender_version=r['version'],
        geometry_counts=r['geometry_counts'], display_readback=r['display_readback'], images=images)


def candidate_state(root, binding):
    receipt_path = root/'RECEIPT.json'
    receipt = read_json(receipt_path)
    if (Path(receipt.get('comparison_source_native_path', '')).resolve() !=
            Path(binding['source_native_path']).resolve() or
            receipt.get('comparison_source_native_geometry_sha256') !=
            binding['source_native_geometry_sha256']):
        raise ValueError('Candidate must bind to the latest actual COHERENT_FLOW source.')
    variants = receipt.get('variants')
    if not isinstance(variants, dict) or set(variants) != {'NESTED'}:
        raise ValueError('Exactly one saved NESTED candidate required.')
    expected = variants['NESTED']
    geometry = root/'NESTED/geometry.npz'
    if (Path(expected.get('geometry', '')).resolve() != geometry.resolve() or
            digest(geometry) != expected.get('geometry_sha256') or
            any(expected.get(key) != binding['saved_geometry'][key]
                for key in ('faces_sha256', 'vertices', 'triangles'))):
        raise ValueError('Saved candidate or shared native connectivity differs.')
    snapshots = receipt.get('source_snapshots')
    if not isinstance(snapshots, dict) or not snapshots:
        raise ValueError('Executed generator source snapshots required.')
    for record in snapshots.values():
        verify_snapshot(record)
    return expected, dict(receipt=str(receipt_path), receipt_sha256=digest(receipt_path))


def snapshot(root):
    source = Path(__file__).resolve()
    target = root/'source_snapshot_render/experiments'/HERE.name/source.name
    checksum = digest(source)
    if target.exists():
        if digest(target) != checksum:
            raise ValueError('Earlier renderer snapshot preserved.')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    record = dict(source=str(source), snapshot=str(target), sha256=checksum)
    verify_snapshot(record)
    return record


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    output = root/'NESTED_FLAT/review'
    if output.exists():
        raise FileExistsError('Earlier actual candidate render preserved.')
    binding = source_binding()
    expected, candidate = candidate_state(root, binding)
    hashes, snap = code_hashes(), snapshot(root)
    shared = scaffold.setup_scene()
    obj, counts = scaffold.add_native_object(Path(expected['geometry']), expected,
                                             'Actual saved parent-nested column', shared)
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
    result = dict(state='NESTED', phase='review', saved_geometry=expected, candidate_binding=candidate,
        source_binding=binding, geometry_counts=counts, display_readback=after, conditions=conditions,
        actual_views=actual_views, images=images, geometry_unchanged_by_renderer=True, all_flat=True,
        geometry_processing=False, normal_maps=False, modifiers=[], version=bpy.app.version_string,
        code_sha256=hashes, source_snapshot=snap,
        comparison_scope='Latest COHERENT_FLOW versus parent-nested G7 design. Existing source PNGs are reused; the saved candidate alone is loaded and rendered. Same cameras, material, lights, resolution, samples, native faces/counts and all-flat shading. No geometry processing or normal-map detail is performed by the renderer.')
    previous.frozen.previous.display_proof(result, expected)
    write(output/'receipt.json', result)
    print('PARENT_NESTED_RENDER_DONE: three actual close/body/front PNGs; saved mesh and all-flat readbacks verified', flush=True)


if __name__ == '__main__':
    main()
