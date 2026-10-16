"""Render a receipt-bound saved variant with the actual NESTED02 cameras.

No geometry processing, modifiers, normal maps or smooth shading. Arbitrary
native triangle counts are supported, including explicitly declared previews.
Use Blender --background --python render.py -- --root TRIAL --variant NAME.
"""
from pathlib import Path
import argparse
import copy
import importlib.util
import re
import shutil
import sys

HERE = Path(__file__).resolve().parent
PRESERVED = HERE.parent / 'parent_continuity_20261014/render_candidate.py'
PRESERVED_SHA = '1e95b3bf58bbee1012d70ccd4599ec687d045027b5fc181e02c389602bab1cbf'
ROOT = Path('E:/CHESHIRE_DATA/experiments/fold_junction_development_20261015/trial01')
VIEWS = ('close_oblique', 'body_oblique', 'front')
spec = importlib.util.spec_from_file_location('fold_junction_preserved_renderer', PRESERVED)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
scaffold, base = previous.scaffold, previous.base
digest, read_json, write = previous.digest, previous.read_json, previous.write
verify_snapshot, require_close = previous.verify_snapshot, previous.require_close
source_binding = previous.source_binding


def code_hashes():
    if digest(PRESERVED) != PRESERVED_SHA:
        raise ValueError('Preserved actual NESTED02 rendering adapter changed.')
    return dict(renderer=digest(__file__), preserved_renderer_sha256=PRESERVED_SHA,
                preserved_renderer_code=previous.code_hashes())


def checked_name(name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name) or name in ('.', '..'):
        raise ValueError('Variant must be a single plain file-name component.')
    return name


def candidate_state(root, name, binding=None):
    """Verify saved generation provenance without assuming a connectivity size."""
    root = Path(root).resolve()
    checked_name(name)
    binding = source_binding() if binding is None else binding
    receipt_path = root / 'RECEIPT.json'
    receipt = read_json(receipt_path)
    if (Path(receipt.get('comparison_source_native_path', '')).resolve() !=
            Path(binding['source_native_path']).resolve() or
            receipt.get('comparison_source_native_geometry_sha256') !=
            binding['source_native_geometry_sha256']):
        raise ValueError('Candidate must bind to the actual preserved NESTED02 source.')
    variants = receipt.get('variants')
    if not isinstance(variants, dict) or name not in variants:
        raise ValueError('Selected variant is absent from the actual generation receipt: ' + name)
    expected = dict(variants[name])
    required = ('geometry', 'geometry_sha256', 'xyz_sha256', 'faces_sha256', 'vertices', 'triangles')
    if any(key not in expected for key in required):
        raise ValueError('Saved variant needs geometry, complete array hashes and native counts.')
    geometry = Path(expected['geometry'])
    geometry = (root / geometry).resolve() if not geometry.is_absolute() else geometry.resolve()
    if not geometry.is_relative_to(root) or digest(geometry) != expected['geometry_sha256']:
        raise ValueError('Actual receipt-bound geometry must be unchanged and inside this trial.')
    if any(not isinstance(expected[key], int) or expected[key] <= 0 for key in ('vertices', 'triangles')):
        raise ValueError('Positive saved native vertex and triangle counts required.')
    expected['geometry'] = str(geometry)
    snapshots = receipt.get('source_snapshots')
    if not isinstance(snapshots, dict) or not snapshots:
        raise ValueError('Actual executed generation source snapshots required.')
    for record in snapshots.values():
        verify_snapshot(record)
    for path, checksum in receipt.get('sources', {}).items():
        if digest(path) != checksum:
            raise ValueError('Actual generation input changed: ' + path)
    return expected, dict(receipt=str(receipt_path), receipt_sha256=digest(receipt_path))


def load_arrays(expected):
    """Verify every original coordinate and face against the saved receipt."""
    import numpy as np
    path = Path(expected['geometry'])
    if digest(path) != expected['geometry_sha256']:
        raise ValueError('Saved native geometry file changed.')
    with np.load(path, allow_pickle=False) as data:
        xyz, faces = data['xyz'], data['faces']
    if (xyz.shape != (expected['vertices'], 3) or xyz.dtype != np.dtype('float64') or
            not np.isfinite(xyz).all() or faces.shape != (expected['triangles'], 3) or
            faces.dtype.kind not in 'iu' or faces.min() < 0 or faces.max() >= len(xyz) or
            scaffold.array_hash(xyz) != expected['xyz_sha256'] or
            scaffold.array_hash(faces) != expected['faces_sha256']):
        raise ValueError('Actual finite float64 native coordinates/triangles differ from the receipt.')
    return xyz, faces


def snapshot(root, name, phase):
    source = Path(__file__).resolve()
    target = root / 'source_snapshot_render' / name / phase / source.name
    if target.exists():
        raise FileExistsError('Earlier actual renderer snapshot preserved: ' + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    record = dict(source=str(source), snapshot=str(target), sha256=digest(source))
    verify_snapshot(record)
    return record


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--variant', default='DEVELOPED')
    parser.add_argument('--views', nargs='+', choices=VIEWS, default=list(VIEWS))
    parser.add_argument('--resolution', type=int, default=900,
                        help='900 is the matched final condition; other sizes are marked preview.')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    if len(set(args.views)) != len(args.views) or not 64 <= args.resolution <= 4096:
        parser.error('Views must be unique; resolution must be between 64 and 4096.')
    root, name = args.root.resolve(), checked_name(args.variant)
    phase = 'review' if args.resolution == 900 else f'preview_{args.resolution}'
    output = root / (name + '_FLAT') / phase
    if output.exists():
        raise FileExistsError('Earlier actual render is preserved: ' + str(output))
    binding = source_binding()
    expected, candidate = candidate_state(root, name, binding)
    hashes, snap = code_hashes(), snapshot(root, name, phase)
    shared = scaffold.setup_scene()
    obj, counts = scaffold.add_native_object(Path(expected['geometry']), expected,
                                             'Actual saved ' + name, shared)
    scaffold.set_smooth_flags(obj, False)
    scene, camera = shared.setup_scene(args.resolution, 24)
    conditions = base.actual_conditions(bpy, scene, camera, obj)
    expected_conditions = copy.deepcopy(binding['conditions'])
    expected_conditions['resolution'] = [args.resolution, args.resolution]
    require_close(conditions, expected_conditions)
    if bpy.app.version_string != binding['Blender_version']:
        raise ValueError('Actual source/candidate Blender version differs.')
    before = scaffold.geometry_signature(obj, counts, False)
    actual_views, images = scaffold.render_views(scene, camera,
        {view: binding['views'][view] for view in args.views}, output)
    after = scaffold.geometry_signature(obj, counts, False)
    if before != after:
        raise ValueError('Saved mesh or all-flat flags changed during rendering.')
    for view in args.views:
        require_close(actual_views[view], binding['actual_views'][view], 'matched-camera.' + view)
    if (source_binding() != binding or candidate_state(root, name, binding) != (expected, candidate) or
            code_hashes() != hashes):
        raise ValueError('Actual source/candidate/executed code changed during rendering.')
    verify_snapshot(snap)
    same_native = all(expected[key] == binding['saved_geometry'][key]
                      for key in ('vertices', 'triangles', 'faces_sha256'))
    result = dict(state=name, phase=phase, saved_geometry=expected, candidate_binding=candidate,
        source_binding=binding, geometry_counts=counts, display_readback=after, conditions=conditions,
        actual_views=actual_views, images=images, geometry_unchanged_by_renderer=True, all_flat=True,
        geometry_processing=False, normal_maps=False, modifiers=[], version=bpy.app.version_string,
        code_sha256=hashes, source_snapshot=snap, resolution_matched_to_source=args.resolution == 900,
        native_connectivity_matched_to_source=same_native,
        diagnostic_display_fan=bool(expected.get('diagnostic_display_fan', False)),
        comparison_scope='Actual saved variant versus NESTED02. Existing baseline PNGs are reused. '
            'Cameras, material, lights, samples and all-flat shading match. '
            'The saved variant is loaded without geometry processing. '
            'Resolution and native-connectivity match are recorded separately.')
    write(output / 'receipt.json', result)
    print('FOLD_JUNCTION_RENDER_DONE ' + name + ': ' + ', '.join(args.views), flush=True)


if __name__ == '__main__':
    main()
