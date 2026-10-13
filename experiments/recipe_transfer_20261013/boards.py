"""Verify actual G0-G7 progression and compare the new G7 with preserved G7 PNGs."""
from pathlib import Path
import argparse
import importlib.util
import json
import math
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('recipe_transfer_boards_render', HERE / 'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
BASELINE_RENDER = HERE.parent / 'medium_root_folds_20261013/finish_render.py'
BASELINE_RENDER_SHA256 = '212aefe64f0115ce4c5be5fe5b18056e299842b890f881e25bcca828474b5c14'
BASELINE = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07')


def checked_images(info, source, receipt_path, hashes, views):
    receipt = render.read_json(receipt_path)
    if (receipt.get('candidate') != info['candidate'] or receipt.get('input_case') != info['input_case'] or
        receipt.get('subdivision_generation') != info['subdivision_generation'] or
        receipt.get('code_sha256') != hashes or any(receipt.get(key) != value for key, value in source.items())):
        raise ValueError('Actual native/render-code/source receipt differs: ' + str(receipt_path))
    render.require_close(receipt['conditions'], render.base.expected_conditions())
    if any(receipt['source_arrays'][key + '_sha256'] != info['checks']['native_' + key + '_sha256']
           for key in ('xyz', 'faces')):
        raise ValueError('Rendered native hashes differ from saved generation.')
    records = {item['view']: item for item in receipt['images']}
    if len(records) != len(receipt['images']) or set(records) != set(views):
        raise ValueError('One distinct original for every declared view required.')
    images = []
    for view, (position, target, scale) in views.items():
        direction = [t - p for p, t in zip(position, target)]
        length = math.sqrt(sum(value * value for value in direction))
        expected = dict(position=list(position), target=list(target), scale=scale,
                        forward=[value / length for value in direction])
        render.require_close(receipt['actual_views'][view], expected, 'camera.' + view)
        if receipt['views'][view] != json.loads(json.dumps(views[view])):
            raise ValueError('Declared fixed camera differs.')
        path = receipt_path.parent / (view + '.png')
        checksum = render.digest(path)
        if records[view]['filename'] != path.name or records[view]['sha256'] != checksum:
            raise ValueError('Original PNG changed: ' + str(path))
        with Image.open(path) as image:
            if image.size != (900, 900) or image.format != 'PNG':
                raise ValueError('Uncropped original 900 by 900 PNG required.')
            image.verify()
        images.append(dict(view=view, path=str(path), sha256=checksum, receipt=str(receipt_path),
                           receipt_sha256=render.digest(receipt_path)))
    return images, receipt


def baseline_state():
    if render.digest(BASELINE_RENDER) != BASELINE_RENDER_SHA256:
        raise ValueError('Preserved actual baseline renderer changed.')
    spec = importlib.util.spec_from_file_location('recipe_transfer_preserved_final_renderer', BASELINE_RENDER)
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    info = render.read_json(BASELINE / 'generation.json')
    if (info.get('candidate') != 'WIDE_ROOT_FINISHED' or info.get('input_case') != 'SPAN' or
        info.get('subdivision_generation') != 7 or info.get('source_generation') != 7 or
        info.get('added_CC_passes') != 0 or info.get('added_normal_field_passes_this_finish') != 0 or
        info.get('finish_smoothing_passes') != 3):
        raise ValueError('Preserved actual final baseline G7 required.')
    source = render.saved_state(BASELINE, info)
    views = {name: render.VIEWS[name] for name in render.COMPARISON_VIEWS}
    images, receipt = checked_images(info, source, BASELINE / 'views/receipt.json', baseline.code_hashes(), views)
    for item in images:
        item['reused_reference'] = True
    return dict(stage_id='PRESERVED_FINAL', candidate=info['candidate'], input_case=info['input_case'],
                subdivision_generation=7, source=source, images=images), receipt


def verify(root):
    root = Path(root).resolve()
    hashes = render.code_hashes()
    states, common_conditions, common_version, fixed_cameras = [], None, None, {}
    for stage in render.STAGES:
        folder, info, source = render.source_state(root, stage)
        views = render.stage_views(stage)
        images, receipt = checked_images(info, source, folder / 'views/receipt.json', hashes, views)
        expected_counts = {key: info[key] for key in render.COUNT_KEYS if key in info}
        if receipt.get('operation_counts') != expected_counts:
            raise ValueError('Subdivision/field/finish counts differ from actual generation metadata.')
        if common_conditions is None:
            common_conditions, common_version = receipt['conditions'], receipt['version']
        if receipt['conditions'] != common_conditions or receipt['version'] != common_version:
            raise ValueError('Progression must share actual material/scene and Blender version.')
        for view in views:
            if view in fixed_cameras:
                render.require_close(receipt['actual_views'][view], fixed_cameras[view], 'matched-camera.' + view)
            else:
                fixed_cameras[view] = receipt['actual_views'][view]
        for item in images:
            item['reused_reference'] = False
        states.append(dict(stage_id=stage, candidate=info['candidate'], input_case=info['input_case'],
            subdivision_generation=info['subdivision_generation'], source=source, images=images,
            operation_counts=expected_counts, native_vertices=receipt['native_vertices'],
            native_triangles=receipt['native_triangles']))
    old, old_receipt = baseline_state()
    if old_receipt['conditions'] != common_conditions or old_receipt['version'] != common_version:
        raise ValueError('Preserved and transferred G7 must share actual Blender/material/scene conditions.')
    for view in render.COMPARISON_VIEWS:
        render.require_close(old_receipt['actual_views'][view], fixed_cameras[view], 'baseline-matched-camera.' + view)
    _, manifest_binding = render.manifest(root)
    return dict(passed=True, root=str(root), **manifest_binding,
        selected_stages=list(render.STAGES), states=states, baseline=old,
        rendered_progression_generations=list(range(8)), new_images=18,
        reused_baseline_images=3, source_images=21, conditions=common_conditions,
        actual_views=fixed_cameras, Blender_version=common_version, crop=False, resize=False,
        render_code_sha256=hashes, baseline_renderer_sha256=BASELINE_RENDER_SHA256,
        scope='One new input with the saved selected recipe. Eight actual G0-G7 states, fixed whole-column cameras, final body/close comparisons. Other saved intermediates are not rendered. Source/native/image receipts only; no independent geometry replay or aesthetic certification.')


LABELS = dict(G00_INPUT='G0 · 새 초기 매스', G01_ANCESTRY='G1 · 계보 분할 + 유한 형상장',
    G02_OVERLAP='G2 · 중첩 return + 유한 형상장', G03_SIDEWALL='G3 · 벽 재구성 + 연결면 생성',
    G04_NEUTRAL='G4 · 중립 CC', G05_DIRECTIONAL='G5 · 방향성 분할',
    G06_MIDDLE='G6 · 작은 파장 + 전역 중간 접힘', G07_FINAL='G7 · 표면 세분 + 후속 접힘 마감')
VIEW_LABELS = dict(front='전체 정면', whole_oblique='전체 사선', body_oblique='본체 사선', close_oblique='근접 사선')


def paste_original(canvas, item, position):
    if render.digest(item['path']) != item['sha256']:
        raise ValueError('Original changed during composition.')
    with Image.open(item['path']) as image:
        if image.size != (900, 900):
            raise ValueError('Original dimensions changed.')
        canvas.paste(image.convert('RGB'), position)


def compose(proof):
    root = Path(proof['root'])
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Earlier verified comparison output preserved.')
    title = ImageFont.truetype(r'C:\Windows\Fonts\malgunbd.ttf', 27)
    label = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 23)
    output.mkdir()
    boards = []
    for view in render.PROGRESSION_VIEWS:
        canvas = Image.new('RGB', (3600, 2025), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), f'동일 레시피의 새 입력 적용 · {VIEW_LABELS[view]} · 실제 subdivision G0–G7', font=title, fill='black')
        sources = []
        for index, current in enumerate(proof['states']):
            column, row = index % 4, index // 4
            draw.text((900 * column + 24, 65 + 960 * row), LABELS[current['stage_id']], font=label, fill='black')
            item = next(image for image in current['images'] if image['view'] == view)
            paste_original(canvas, item, (900 * column, 105 + 960 * row))
            sources.append(dict(stage_id=current['stage_id'], **item))
        path = output / ('PROGRESSION_' + view + '.png')
        canvas.save(path)
        boards.append(dict(view=view, kind='progression', output=str(path), sha256=render.digest(path), sources=sources))
    final = proof['states'][-1]
    for view in render.COMPARISON_VIEWS:
        canvas = Image.new('RGB', (1800, 1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), f'기존 입력 / 새 입력 · {VIEW_LABELS[view]} · 같은 레시피의 실제 G7', font=title, fill='black')
        sources = []
        for column, (current, text) in enumerate(((proof['baseline'], '기존 SPAN · 실제 G7'),
                                                (final, '새 WAIST_FULL · 실제 G7'))):
            draw.text((900 * column + 24, 61), text, font=label, fill='black')
            item = next(image for image in current['images'] if image['view'] == view)
            paste_original(canvas, item, (900 * column, 105))
            sources.append(dict(stage_id=current['stage_id'], **item))
        path = output / ('FINAL_COMPARE_' + view + '.png')
        canvas.save(path)
        boards.append(dict(view=view, kind='final_comparison', output=str(path), sha256=render.digest(path), sources=sources))
    proof.update(boards=boards, progression_boards=2, final_comparison_boards=3,
                 boards_script_sha256=render.digest(__file__))
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
    print('RECIPE_TRANSFER_RENDER_VERIFICATION_PASS: 18 new originals + 3 preserved G7 originals', flush=True)


if __name__ == '__main__':
    main()
