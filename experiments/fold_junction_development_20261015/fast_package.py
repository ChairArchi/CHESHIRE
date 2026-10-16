"""Exact PLY/HTML packaging adapter for verified fast_render.py receipts.

The preserved exporter is executed through an isolated function-global mapping;
no module globals, scripts, previous receipts or outputs are changed. Native
float64 coordinates and triangle indices use the unchanged PLY roundtrip code.
Only explicitly selected successful trials should be passed to this command.
"""
from pathlib import Path
import argparse
import copy
import importlib.util
import json
import shutil
import types

from PIL import Image

HERE = Path(__file__).resolve().parent
PRESERVED = HERE / 'package.py'
PRESERVED_SHA = '4ada4bcb1a772ffccec3f0e5281b8e4cb067695e8ac3213060dbf94d95f97321'
FAST_PATH = HERE / 'fast_render.py'
FAST_SHA = '45a48c67b5f260f83d74e1b481ac1e3d37dfbc9441a25e3185a8b9621b3c2247'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


fast = module('fast_package_verified_renderer', FAST_PATH)
preserved = module('fast_package_frozen_exporter', PRESERVED)
render = fast.render
digest = fast.digest


def execution_hashes():
    if digest(PRESERVED) != PRESERVED_SHA or digest(FAST_PATH) != FAST_SHA:
        raise ValueError('Frozen exact exporter or verified fast renderer changed.')
    return dict(export_adapter=digest(__file__), preserved_exporter_sha256=PRESERVED_SHA,
                verified_fast_renderer=fast.code_hashes())


def assert_eligible_source(root, expected=None):
    """Reject explicit stop/failure records and already rejected review roots."""
    root = Path(root).resolve()
    if (root / 'STOP.json').exists():
        raise ValueError('Stopped trial cannot be exported as an accepted result.')
    receipt = render.read_json(root / 'RECEIPT.json')
    records = [receipt]
    if expected is not None:
        records.append(expected.get('validation', {}))
    for record in records:
        for key in ('status', 'visual_success', 'aesthetic_success'):
            value = str(record.get(key, '')).upper()
            if value.startswith(('FAILED', 'REJECTED', 'NOT_ADOPTED', 'NO_ACTIVE_PARENT', 'STOPPED')):
                raise ValueError('Explicitly failed or rejected trial cannot be exported: ' + value)
    review_folder = HERE.parents[1] / 'docs' / HERE.name
    for review_path in review_folder.glob('TRIAL*_REVIEW.json'):
        review = render.read_json(review_path)
        reviewed_root = review.get('trial_root')
        if (reviewed_root and Path(reviewed_root).resolve() == root and
                str(review.get('status', '')).upper() in ('NOT_ADOPTED', 'FAILED', 'REJECTED')):
            raise ValueError('Selected trial was explicitly rejected in ' + str(review_path))


def checked_render(root, name, phase, expected, candidate, binding):
    """Verify fast renderer provenance without weakening geometry/PNG checks."""
    root = Path(root).resolve()
    render.checked_name(phase)
    assert_eligible_source(root, expected)
    execution_hashes()
    receipt_path = root / (name + '_FLAT') / phase / 'receipt.json'
    receipt = render.read_json(receipt_path)
    if (receipt['state'] != name or receipt['phase'] != phase or
            receipt['saved_geometry'] != expected or receipt['candidate_binding'] != candidate or
            receipt['source_binding'] != binding or receipt['code_sha256'] != fast.code_hashes() or
            receipt['geometry_unchanged_by_renderer'] is not True or receipt['all_flat'] is not True or
            receipt['geometry_processing'] is not False or receipt['normal_maps'] is not False or
            receipt['modifiers'] != []):
        raise ValueError('Actual fast-rendered saved-geometry provenance differs.')
    snapshots = receipt.get('source_snapshots')
    if not isinstance(snapshots, dict) or set(snapshots) != {'fast_render.py', 'render.py'}:
        raise ValueError('Both actual fast and preserved render source snapshots are required.')
    for filename, source in (('fast_render.py', FAST_PATH), ('render.py', fast.PRESERVED)):
        record = snapshots[filename]
        render.verify_snapshot(record)
        if (Path(record['source']).resolve() != source.resolve() or
                record['sha256'] != digest(source)):
            raise ValueError('Actual executed renderer snapshot binding differs.')
    if receipt.get('source_snapshot') != snapshots['fast_render.py']:
        raise ValueError('Primary snapshot must identify the actual fast renderer.')
    loading = receipt.get('mesh_loading', {})
    if (loading.get('Blender_edges') != 0 or loading.get('edge_graph_omitted') is not True or
            loading.get('Mesh_update_called') is not False or
            loading.get('material_recipe_unchanged') is not True or
            loading.get('material_recipe_executed_on_zero_polygon_template') is not True):
        raise ValueError('Actual verified edge-free loading declaration differs.')
    counts, display = receipt['geometry_counts'], receipt['display_readback']
    if (counts['vertices'] != expected['vertices'] or counts['triangles'] != expected['triangles'] or
            counts['source_arrays'] != {key:expected[key] for key in ('xyz_sha256', 'faces_sha256')} or
            display['geometry'] != counts['expected_display_arrays'] or
            display['polygons'] != expected['triangles'] or display['smooth_polygons'] != 0 or
            display['all_use_smooth'] is not False or display['geometry_unchanged'] is not True or
            display['modifiers'] != [] or display['custom_normal_map'] is not False):
        raise ValueError('Complete saved-array/display readbacks or actual flat flags differ.')
    expected_conditions = copy.deepcopy(binding['conditions'])
    expected_conditions['resolution'] = receipt['conditions']['resolution']
    render.require_close(receipt['conditions'], expected_conditions)
    if receipt['version'] != binding['Blender_version']:
        raise ValueError('Actual source/candidate Blender versions differ.')
    resolution_matches = receipt['conditions']['resolution'] == binding['conditions']['resolution']
    native_matches = all(expected[key] == binding['saved_geometry'][key]
                         for key in ('vertices', 'triangles', 'faces_sha256'))
    if (receipt['resolution_matched_to_source'] != resolution_matches or
            receipt['native_connectivity_matched_to_source'] != native_matches):
        raise ValueError('Declared resolution/native matching differs from actual saved records.')
    if (not receipt['images'] or set(receipt['actual_views']) != {item['view'] for item in receipt['images']} or
            len(receipt['images']) != len(receipt['actual_views'])):
        raise ValueError('Actual unique camera/image inventory required.')
    references = {item['view']:item for item in binding['images']}
    images = []
    for item in receipt['images']:
        view = item['view']
        if view not in render.VIEWS or item['filename'] != view + '.png':
            raise ValueError('Unknown or nonlocal actual PNG.')
        render.require_close(receipt['actual_views'][view], binding['actual_views'][view])
        path, reference = receipt_path.parent / item['filename'], references[view]
        if digest(path) != item['sha256'] or digest(reference['path']) != reference['sha256']:
            raise ValueError('Actual candidate/reference PNG changed.')
        for source, size in ((path, receipt['conditions']['resolution']),
                             (Path(reference['path']), binding['conditions']['resolution'])):
            with Image.open(source) as png:
                if png.format != 'PNG' or list(png.size) != list(size):
                    raise ValueError('Actual PNG dimensions differ from its recorded condition.')
                png.verify()
        images.append(dict(view=view, candidate=str(path), candidate_sha256=item['sha256'],
            reference=reference['path'], reference_sha256=reference['sha256']))
    return receipt, dict(path=str(receipt_path), sha256=digest(receipt_path)), images


def isolated_export_main():
    """Reuse the frozen export body with isolated bindings; mutate no module."""
    namespace = dict(preserved.__dict__)
    facade = types.SimpleNamespace(**{key:value for key,value in render.__dict__.items()
                                      if not key.startswith('__')})
    facade.code_hashes = execution_hashes
    namespace.update(__file__=str(Path(__file__).resolve()), RENDERER=FAST_PATH,
                     render=facade, checked_render=checked_render)
    return types.FunctionType(preserved.main.__code__, namespace, 'verified_fast_export_main')


def main():
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument('--output', type=Path, required=True)
    args, _ = parser.parse_known_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError('Earlier export package is preserved: ' + str(output))
    hashes = execution_hashes()
    isolated_export_main()()
    dependencies = {}
    for source, filename in ((PRESERVED, 'SOURCE_SNAPSHOT_preserved_package.py'),
                             (fast.PRESERVED, 'SOURCE_SNAPSHOT_preserved_render.py')):
        target = output / filename
        if target.exists():
            raise FileExistsError('Earlier dependency snapshot is preserved.')
        shutil.copyfile(source, target)
        if digest(target) != digest(source):
            raise ValueError('Export dependency snapshot differs.')
        dependencies[source.name] = dict(source=str(source), snapshot=str(target), sha256=digest(source))
    if execution_hashes() != hashes:
        raise ValueError('Executed packaging dependencies changed.')
    manifest = output / 'MANIFEST.json'
    record = dict(kind='VERIFIED_FAST_RENDER_EXACT_EXPORT_ADAPTER',
        manifest=dict(path=str(manifest), sha256=digest(manifest)),
        executed_code_sha256=hashes, preserved_dependency_snapshots=dependencies,
        isolated_function_globals=True, original_module_globals_modified=False,
        old_scripts_modified=False, saved_geometry_modified=False,
        PLY_writer='Unchanged preserved package.py write_ply; complete float64/index roundtrip.',
        comparison='Unchanged preserved local-image comparison.html writer; original PNG hashes verified.')
    preserved.write_json(output / 'FAST_PACKAGE_RECEIPT.json', record)
    print('VERIFIED_FAST_PACKAGE_DONE ' + str(output), flush=True)


if __name__ == '__main__':
    main()
