"""Compare latest original G7 and the saved WIDE_ROOT delta-finished G7."""
from pathlib import Path
import argparse
import importlib.util
import json
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('wide_root_finish_boards_render', HERE / 'finish_render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
SHARED_BOARDS = HERE / 'boards.py'
SHARED_BOARDS_SHA256 = 'ef51b311d234278adf9562689fcbe698982ab37d2639d552c9ea0da8b38f744b'
spec = importlib.util.spec_from_file_location('wide_root_finish_preserved_image_checks', SHARED_BOARDS)
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)


def verify(root):
    if render.digest(SHARED_BOARDS) != SHARED_BOARDS_SHA256:
        raise ValueError('Preserved raw comparison/image checker changed.')
    root = Path(root).resolve()
    folder, info, source = render.source_state(root)
    parent_info, parent_source = render.raw.parent_state()
    check_images = shared.shared.checks.checked_images
    old_images, old_receipt, old_views = check_images(parent_info, parent_source,
        render.PARENT / 'views/receipt.json', render.raw.parent.code_hashes())
    images, receipt, views = check_images(info, source, folder / 'views/receipt.json', render.code_hashes())
    for current in (old_receipt, receipt):
        if (current.get('source_generation') != 7 or current.get('added_CC_passes') != 0 or
            current.get('added_normal_field_passes') != 2):
            raise ValueError('Both states remain actual G7; pipeline added fields stay two and added CC stays zero.')
    if (receipt.get('added_normal_field_passes_this_finish') != 0 or
        receipt.get('normal_field_passes_computed_this_finish') != 0 or
        receipt.get('pipeline_added_normal_field_passes') != 2 or
        receipt.get('finish_smoothing_passes') != 3 or receipt.get('smoothing_passes') != 7 or
        receipt.get('cumulative_normal_field_passes') != info['cumulative_normal_field_passes']):
        raise ValueError('Delta-only finish counts must stay separate from the preserved field pipeline.')
    if receipt['version'] != old_receipt['version'] or receipt['conditions'] != old_receipt['conditions']:
        raise ValueError('Actual Blender version or material/scene conditions differ.')
    for view in render.VIEWS:
        render.require_close(views[view], old_views[view], 'matched-camera.' + view)
    for image in old_images:
        image['reused_reference'] = True
    for image in images:
        image['reused_reference'] = False
    return dict(passed=True, root=str(root), source_generation=7, subdivision_generation=7,
        added_CC_passes=0, added_normal_field_passes=2, pipeline_added_normal_field_passes=2,
        added_normal_field_passes_this_finish=0,
        normal_field_passes_computed_this_finish=0, smoothing_passes=7, finish_smoothing_passes=3,
        source_cumulative_normal_field_passes=parent_info['cumulative_normal_field_passes'],
        cumulative_normal_field_passes=info['cumulative_normal_field_passes'],
        raw_field_stage=source['raw_field_stage'], raw_field_control_sha256=source['raw_field_control_sha256'],
        raw_field_generation_json_sha256=source['raw_field_generation_json_sha256'],
        states=[dict(candidate='PARENT_LINKED', subdivision_generation=7, source=parent_source, images=old_images,
                     cumulative_normal_field_passes=parent_info['cumulative_normal_field_passes']),
                dict(candidate='WIDE_ROOT_FINISHED', subdivision_generation=7, source=source, images=images,
                     cumulative_normal_field_passes=info['cumulative_normal_field_passes'])],
        reused_parent_images=3, new_images=3, source_images=6, conditions=receipt['conditions'],
        actual_views=views, Blender_version=receipt['version'], crop=False, resize=False,
        image_check_script_sha256=SHARED_BOARDS_SHA256,
        scope='Latest preserved trial03 G7 compared with one saved raw-delta finish; pipeline fields two, newly computed finish fields zero, finish delta smoothing three; saved receipts and matched camera/material checks only; no aesthetic certification.')


def compose(proof):
    root = Path(proof['root'])
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Fresh verified delta-finish comparison output required.')
    title = ImageFont.truetype(r'C:\Windows\Fonts\malgunbd.ttf', 27)
    label = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 23)
    output.mkdir()
    labels = ('기존 G7 · 연결 띠 정리', '중간 접힘 + 작은 골 · 변위 마감 G7')
    view_labels = dict(front='전체 정면', body_oblique='본체 사선', close_oblique='근접 사선')
    boards = []
    for view in render.VIEWS:
        canvas = Image.new('RGB', (1800, 1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), f'SPAN · {view_labels[view]} · 중간 접힘과 작은 골의 변위 마감 · 실제 G7 / 추가 CC 0회', font=title, fill='black')
        sources = []
        for column, current in enumerate(proof['states']):
            draw.text((900*column + 24, 61), labels[column], font=label, fill='black')
            item = next(image for image in current['images'] if image['view'] == view)
            if render.digest(item['path']) != item['sha256']:
                raise ValueError('Original changed during composition.')
            with Image.open(item['path']) as image:
                if image.size != (900, 900):
                    raise ValueError('Original dimensions changed.')
                canvas.paste(image.convert('RGB'), (900*column, 105))
            sources.append(dict(candidate=current['candidate'], **item))
        path = output / ('SPAN_' + view + '.png')
        canvas.save(path)
        boards.append(dict(view=view, output=str(path), sha256=render.digest(path), sources=sources))
    proof.update(boards=boards, comparison_boards=3, boards_script_sha256=render.digest(__file__))
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
    print('WIDE_ROOT_FINISHED_RENDER_VERIFICATION_PASS: 3 reused latest G7 originals + 3 new finished G7 originals', flush=True)


if __name__ == '__main__':
    main()
