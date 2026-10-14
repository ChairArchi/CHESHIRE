"""Compare saved original/revised body geometry separately from normal shading."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('end_rule_revision_board_renderer', HERE / 'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
RENDER_SHA256 = '58b8dff2f1ef9b91a438d97b5d7174dca3048e3f6e9af44e56b2bfdadf0c1ce8'
STATES = ('ORIGINAL_FLAT', 'REVISED_FLAT', 'ORIGINAL_SMOOTH', 'REVISED_SMOOTH')


def canonical(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def snapshot_source(root):
    source = Path(__file__).resolve()
    relative = Path('experiments') / HERE.name / 'boards.py'
    target = Path(root) / 'source_snapshot_boards' / relative
    checksum = render.digest(source)
    if target.exists():
        if render.digest(target) != checksum:
            raise ValueError('Earlier board source snapshot differs.')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    record = dict(source=str(source), relative_path=relative.as_posix(), snapshot=str(target), sha256=checksum)
    verify_snapshot(record)
    return record


def verify_snapshot(record):
    if (record.get('sha256') != render.digest(__file__) or
            any(render.digest(record[key]) != record['sha256'] for key in ('source', 'snapshot'))):
        raise ValueError('Actual boards source/snapshot changed.')


def checked_images(receipt_path, receipt, binding, reused=False):
    records = receipt.get('images')
    if (not isinstance(records, list) or len(records) != 4 or
            {item['view'] for item in records} != set(binding['views'])):
        raise ValueError('Exactly four distinct matched actual images required.')
    images = []
    for item in records:
        view = item['view']
        path = Path(item['path']) if reused else receipt_path.parent / (view + '.png')
        if not reused:
            if item['filename'] != path.name:
                raise ValueError('Actual image filename differs.')
            render.require_close(receipt['actual_views'][view], binding['actual_reference_views'][view], 'camera.' + view)
        if render.digest(path) != item['sha256']:
            raise ValueError('Actual saved source PNG changed: ' + str(path))
        with Image.open(path) as image:
            if image.size != (900, 900) or image.format != 'PNG':
                raise ValueError('Actual 900-square native PNG required.')
            image.verify()
        images.append(dict(view=view, path=str(path), sha256=item['sha256'],
            receipt=str(receipt_path), receipt_sha256=render.digest(receipt_path), reused_reference=reused,
            underlying_reference_receipt=item.get('receipt') if reused else None,
            underlying_reference_receipt_sha256=item.get('receipt_sha256') if reused else None))
    return images


def check_render_receipt(receipt, state, binding, hashes, expected_geometry, candidate_binding):
    smooth = state.endswith('_SMOOTH')
    if (receipt.get('state') != state or receipt.get('source_binding') != binding or
            receipt.get('candidate_binding') != candidate_binding or
            receipt.get('code_sha256') != hashes or receipt.get('saved_geometry') != expected_geometry or
            Path(receipt.get('geometry_path', '')).resolve() != Path(expected_geometry['geometry']).resolve() or
            receipt.get('geometry_unchanged_in_renderer') is not True or
            receipt.get('smooth_shading') is not smooth or receipt.get('geometry_smoothing') is not False or
            receipt.get('normal_interpolation_only') is not smooth or
            receipt.get('geometry_processing') is not False or receipt.get('modifiers') != [] or
            receipt.get('remesh') is not False or receipt.get('Boolean_fusion') is not False or
            receipt.get('ornaments_added') is not False or receipt.get('new_source_growth_G8') is not False or
            receipt.get('source_growth_generation') != 7):
        raise ValueError('Actual saved body/shading/renderer receipt mismatch: ' + state)
    render.verify_snapshot(receipt['render_source_snapshot'])
    render.require_close(receipt['views'], binding['views'], 'declared-cameras.' + state)
    counts = receipt['geometry_counts']
    if counts['source_arrays'] != {key: expected_geometry[key] for key in ('xyz_sha256', 'faces_sha256')}:
        raise ValueError('Actual loaded saved arrays differ: ' + state)
    for key in ('vertices', 'triangles'):
        if key in expected_geometry and counts[key] != expected_geometry[key]:
            raise ValueError('Actual saved body counts differ: ' + state)
    expected_flags = counts['triangles'] if smooth else 0
    readback = receipt['display_readback']
    expected_flag_hash = render.array_hash(np.full(counts['triangles'], smooth, bool))
    if (readback.get('geometry') != counts['expected_display_arrays'] or
            readback.get('geometry_unchanged') is not True or readback.get('modifiers') != [] or
            readback.get('custom_normal_map') is not False or readback.get('all_use_smooth') is not smooth or
            readback.get('polygons') != counts['triangles'] or readback.get('smooth_polygons') != expected_flags or
            readback.get('use_smooth_flags_sha256') != expected_flag_hash):
        raise ValueError('Actual geometry/normal-flag readback differs: ' + state)
    conditions = receipt['conditions']
    render.require_close(conditions, dict(binding['reference_conditions'], smooth_polygons=expected_flags))
    if receipt['version'] != binding['reference_Blender_version']:
        raise ValueError('Original/revised Blender versions differ.')
    expected_shading = 'SMOOTH_NORMAL_INTERPOLATION_ONLY' if smooth else 'FLAT_NATIVE_TRIANGLES'
    if receipt.get('shading') != expected_shading:
        raise ValueError('Explicit shading label differs.')
    return readback


def verify(root):
    root = Path(root).resolve()
    if render.digest(HERE / 'render.py') != RENDER_SHA256:
        raise ValueError('The executed two-phase renderer changed.')
    hashes = render.code_hashes()
    parent_info, source, source_binding = render.fixed_source_state()
    binding = canonical(source_binding)
    if render.read_json(root / 'SOURCE_BINDING.json') != binding:
        raise ValueError('Frozen original source/camera/reference binding differs.')
    path, revised, candidate_binding = render.candidate_state(root, source_binding)
    candidate_binding = canonical(candidate_binding)
    original_path = root / 'ORIGINAL_FLAT/receipt.json'
    original = render.read_json(original_path)
    if (original.get('state') != 'ORIGINAL_FLAT' or
            original.get('kind') != 'FOUR_REUSED_ACTUAL_ORIGINAL_FLAT_IMAGES' or
            original.get('source_binding') != binding or original.get('images') != binding['reference_images'] or
            original.get('code_sha256') != hashes or original.get('smooth_shading') is not False or
            original.get('geometry_smoothing') is not False or original.get('geometry_processing') is not False or
            original.get('modifiers') != [] or original.get('new_renders') != 0):
        raise ValueError('Four actual original flat reference bindings required.')
    render.verify_snapshot(original['render_source_snapshot'])
    macro = render.read_json(render.MACRO_RECEIPT)
    original_geometry_readback = macro['original_body_display_readback']
    if original_geometry_readback != macro['original_body_counts']['expected_display_arrays']:
        raise ValueError('Preserved actual original flat body readback differs.')
    original_expected = dict(geometry_sha256=render.SOURCE_GEOMETRY_SHA256,
        xyz_sha256=parent_info['checks']['native_xyz_sha256'], faces_sha256=parent_info['checks']['native_faces_sha256'])
    states = []
    for state in STATES:
        if state == 'ORIGINAL_FLAT':
            states.append(dict(state=state, source_geometry=source['source'], geometry_sha256=render.SOURCE_GEOMETRY_SHA256,
                shading='FLAT_NATIVE_TRIANGLES', images=checked_images(original_path, original, binding, reused=True),
                geometry_readback=original_geometry_readback, actual_smooth_polygons=0,
                flag_evidence='Preserved actual original flat-render code checks all use_smooth flags false; receipt conditions record zero smooth polygons.'))
            continue
        receipt_path = root / state / 'views/receipt.json'
        receipt = render.read_json(receipt_path)
        is_original = state.startswith('ORIGINAL_')
        expected = original_expected if is_original else revised
        # Original renderer recorded source arrays without a duplicate geometry path key.
        expected_with_path = dict(expected, geometry=source['source']) if is_original else expected
        if is_original:
            if receipt.get('saved_geometry') != expected:
                raise ValueError('Actual original smooth source arrays differ.')
            check_receipt = dict(receipt, saved_geometry=expected_with_path)
        else:
            check_receipt = receipt
        readback = check_render_receipt(check_receipt, state, binding, hashes, expected_with_path,
            None if is_original else candidate_binding)
        states.append(dict(state=state, source_geometry=expected_with_path['geometry'],
            geometry_sha256=expected['geometry_sha256'], shading=receipt['shading'],
            images=checked_images(receipt_path, receipt, binding), geometry_readback=readback['geometry'],
            actual_smooth_polygons=readback['smooth_polygons'], actual_flag_hash=readback['use_smooth_flags_sha256'],
            source_arrays=receipt['geometry_counts']['source_arrays'], geometry_counts=receipt['geometry_counts']))
    by_state = {state['state']: state for state in states}
    for body in ('ORIGINAL', 'REVISED'):
        flat, smooth = by_state[body + '_FLAT'], by_state[body + '_SMOOTH']
        if flat['geometry_readback'] != smooth['geometry_readback'] or flat['geometry_sha256'] != smooth['geometry_sha256']:
            raise ValueError('Flat/smooth states did not use identical actual saved ' + body + ' geometry.')
    source_triangle_hash = by_state['ORIGINAL_SMOOTH']['source_arrays']['faces_sha256']
    return dict(passed=True, root=str(root), states=states, source_binding=binding,
        candidate_binding=candidate_binding, comparison_columns=4, source_images=16,
        reused_original_flat_images=4, new_original_smooth_images=4,
        new_revised_flat_images=4, new_revised_smooth_images=4,
        actual_views=binding['actual_reference_views'], reference_conditions=binding['reference_conditions'],
        only_allowed_condition_difference='smooth_polygons: zero for FLAT; all native triangles for SMOOTH',
        flat_smooth_coordinates_and_connectivity_identical=True,
        original_and_revised_triangle_connectivity_identical=(revised['faces_sha256'] == source_triangle_hash),
        geometry_success_certified=False, aesthetic_success_certified=False,
        smooth_normal_diagnostic_is_geometry_improvement=False,
        source_growth_generation=7, new_source_growth_G8=False, ornaments_added=False,
        modifiers=[], renderer_geometry_processing=False, crop=False, resize=False,
        render_code_sha256=hashes, boards_code_sha256=render.digest(__file__),
        scope='Four actual source/candidate body states at four matched cameras. Adjacent FLAT columns compare actual saved geometry; adjacent SMOOTH columns compare the same bodies with normal interpolation. Smooth flags are the only allowed render-condition difference. Coordinate/connectivity hashes are identical between each body\'s FLAT/SMOOTH states. This verifies provenance and diagnostic separation, not geometry quality, intersection freedom, aesthetics or successful end reconstruction.')


def compose(proof):
    root = Path(proof['root'])
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Earlier actual comparison preserved.')
    snapshot = snapshot_source(root)
    output.mkdir()
    title = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 27)
    label = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 22)
    labels = ('Original G7 | FLAT', 'Revised G7 | FLAT',
        'Original G7 | SMOOTH normals only', 'Revised G7 | SMOOTH normals only')
    boards = []
    for view in proof['actual_views']:
        canvas = Image.new('RGB', (3600, 1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), 'SPAN | ' + view + ' | saved geometry comparison + normal-shading diagnostic', font=title, fill='black')
        sources = []
        for column, state in enumerate(proof['states']):
            draw.text((column * 900 + 24, 61), labels[column], font=label, fill='black')
            item = next(image for image in state['images'] if image['view'] == view)
            if render.digest(item['path']) != item['sha256']:
                raise ValueError('Actual source PNG changed during composition.')
            with Image.open(item['path']) as image:
                if image.size != (900, 900):
                    raise ValueError('Actual source image dimensions changed.')
                canvas.paste(image.convert('RGB'), (column * 900, 105))
            sources.append(dict(state=state['state'], shading=state['shading'], **item))
        path = output / ('SPAN_' + view + '.png')
        canvas.save(path)
        boards.append(dict(view=view, output=str(path), sha256=render.digest(path), sources=sources))
    verify_snapshot(snapshot)
    proof.update(boards=boards, comparison_boards=4, boards_source_snapshot=snapshot)
    for path in (output / 'SOURCE_LIST.json', root / 'RENDER_VERIFICATION.json'):
        path.write_text(json.dumps(proof, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=render.DEFAULT_ROOT)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    proof = verify(args.root)
    if not args.verify_only:
        compose(proof)
    print('END_RULE_MATCHED_RENDER_PASS: 4 original flat + 4 original smooth + 4 revised flat + 4 revised smooth', flush=True)


if __name__ == '__main__':
    main()
