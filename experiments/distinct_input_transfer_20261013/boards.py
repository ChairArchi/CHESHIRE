"""Verified input and final comparisons for one distinct-input recipe transfer."""
from pathlib import Path
import argparse
import importlib.util
import json
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('distinct_input_boards_renderer', HERE / 'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
FROZEN_BOARDS = HERE.parent / 'recipe_transfer_20261013/boards.py'
FROZEN_BOARDS_SHA256 = '2368533ac09aaec75ab5ff5c35fbe7e603a87b277ce18429e589c3a23218800b'
spec = importlib.util.spec_from_file_location('distinct_input_frozen_image_checker', FROZEN_BOARDS)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
# Render-context adaptation only; the frozen native/image/scene checks remain.
prior.render = render
LABELS, VIEW_LABELS = prior.LABELS, prior.VIEW_LABELS
paste_original = prior.paste_original


def verify(root):
    if render.digest(FROZEN_BOARDS) != FROZEN_BOARDS_SHA256:
        raise ValueError('Preserved transfer image checker changed.')
    root = Path(root).resolve()
    proof = prior.verify(root)
    _, info, source = render.original_g0_state(root)
    views = {name: render.VIEWS[name] for name in render.PROGRESSION_VIEWS}
    images, receipt = prior.checked_images(info, source, root / 'reference_views/G00_INPUT/receipt.json',
                                          render.code_hashes(), views)
    if receipt['conditions'] != proof['conditions'] or receipt['version'] != proof['Blender_version']:
        raise ValueError('Original/new G0 must share actual Blender/material/scene conditions.')
    for view in views:
        render.require_close(receipt['actual_views'][view], proof['actual_views'][view],
                             'initial-matched-camera.' + view)
    for item in images:
        item.update(reused_reference=False, preserved_geometry_new_render=True)
    initial = dict(stage_id=render.REFERENCE_STAGE, candidate=info['candidate'], input_case='SPAN',
                   subdivision_generation=0, source=source, images=images)
    proof.update(input_case=render.INPUT_CASE, baseline_initial=initial,
        new_variant_images=18, new_original_input_reference_images=2, new_images=20,
        reused_baseline_images=3, source_images=23, frozen_boards_sha256=FROZEN_BOARDS_SHA256,
        scope='One distinct G0 input, unchanged downstream selected recipe. Eight actual G0-G7 stages. Stored original SPAN G0 is rendered twice without rebuilding; existing final SPAN G7 PNGs are reused. Native/source/image receipts only; no independent geometry replay or aesthetic certification.')
    return proof


def board(canvas, draw, title, label, view, title_text, states, labels, output, kind):
    draw.text((24, 12), title_text, font=title, fill='black')
    sources = []
    for column, (current, text) in enumerate(zip(states, labels)):
        draw.text((900 * column + 24, 61), text, font=label, fill='black')
        item = next(image for image in current['images'] if image['view'] == view)
        paste_original(canvas, item, (900 * column, 105))
        sources.append(dict(stage_id=current['stage_id'], **item))
    canvas.save(output)
    return dict(view=view, kind=kind, output=str(output), sha256=render.digest(output), sources=sources)


def compose(proof):
    root = Path(proof['root'])
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Earlier distinct-input comparison output preserved.')
    title = ImageFont.truetype(r'C:\Windows\Fonts\malgunbd.ttf', 27)
    label = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 23)
    output.mkdir()
    boards = []
    for view in render.PROGRESSION_VIEWS:
        canvas = Image.new('RGB', (3600, 2025), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), f'서로 다른 초기 매스에 같은 레시피 적용 · {VIEW_LABELS[view]} · 실제 subdivision G0–G7', font=title, fill='black')
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
    for view in render.PROGRESSION_VIEWS:
        canvas = Image.new('RGB', (1800, 1020), 'white')
        boards.append(board(canvas, ImageDraw.Draw(canvas), title, label, view,
            f'초기 매스 비교 · {VIEW_LABELS[view]} · 분할 전 실제 G0',
            (proof['baseline_initial'], proof['states'][0]),
            ('기존 SPAN · 저장된 G0', f'새 {render.INPUT_CASE} · 실제 G0'),
            output / ('INPUT_COMPARE_' + view + '.png'), 'initial_comparison'))
    for view in render.COMPARISON_VIEWS:
        canvas = Image.new('RGB', (1800, 1020), 'white')
        boards.append(board(canvas, ImageDraw.Draw(canvas), title, label, view,
            f'기존 입력 / 새 입력 · {VIEW_LABELS[view]} · 같은 레시피의 실제 G7',
            (proof['baseline'], proof['states'][-1]),
            ('기존 SPAN · 실제 G7', f'새 {render.INPUT_CASE} · 실제 G7'),
            output / ('FINAL_COMPARE_' + view + '.png'), 'final_comparison'))
    proof.update(boards=boards, progression_boards=2, initial_comparison_boards=2,
                 final_comparison_boards=3, boards_script_sha256=render.digest(__file__))
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
    print('DISTINCT_INPUT_TRANSFER_RENDER_VERIFICATION_PASS: 18 variant + 2 stored original G0 + 3 reused final originals', flush=True)


if __name__ == '__main__':
    main()
