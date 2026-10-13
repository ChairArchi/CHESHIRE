"""Three matched native-image comparisons of original SPAN G7 and parametric rolled-end rebuilding."""
from pathlib import Path
import argparse
import importlib.util
import json
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rolled_end_rebuild_boards_renderer', HERE / 'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
IMAGE_CHECKER = HERE.parent / 'whole_column_detail_20261013/surface_boards.py'
IMAGE_CHECKER_SHA256 = 'b2276f3fbda604637f90a6f4dec7cc71528687c92ec8dcd7dfe3cea6bb5ea6f0'
spec = importlib.util.spec_from_file_location('rolled_end_rebuild_frozen_native_image_checks', IMAGE_CHECKER)
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


def verify(root):
    if render.digest(IMAGE_CHECKER) != IMAGE_CHECKER_SHA256:
        raise ValueError('Preserved native/image/camera checker changed.')
    root = Path(root).resolve()
    folder, info, source, (parent_info, parent_source) = render.source_state(root)
    old_images, old_receipt, old_views = checks.checked_images(parent_info, parent_source,
        render.PARENT / 'views/receipt.json', render.prior.code_hashes())
    images, receipt, views = checks.checked_images(info, source,
        folder / 'views/receipt.json', render.code_hashes())
    if (receipt.get('source_generation') != info['source_generation'] or
        any(receipt.get(key) != info[key] for key in ('added_CC_passes', 'added_topology_events',
            'added_normal_field_passes', 'added_mandelbulb_evaluations')) or
        receipt.get('operation_record') != render.operation_record(info)):
        raise ValueError('Actual event counts or saved operator metadata differ.')
    if old_receipt['conditions'] != receipt['conditions'] or old_receipt['version'] != receipt['version']:
        raise ValueError('Actual Blender/material/scene conditions differ.')
    for view in render.VIEWS:
        render.require_close(views[view], old_views[view], 'matched-camera.' + view)
    for item in old_images:
        item['reused_reference'] = True
    for item in images:
        item['reused_reference'] = False
    return dict(passed=True, root=str(root), source_generation=7, subdivision_generation=7,
        added_CC_passes=info['added_CC_passes'], added_topology_events=info['added_topology_events'],
        added_normal_field_passes=info['added_normal_field_passes'],
        added_mandelbulb_evaluations=info['added_mandelbulb_evaluations'],
        operation_record=render.operation_record(info),
        states=[dict(candidate=parent_info['candidate'], subdivision_generation=7, source=parent_source, images=old_images),
                dict(candidate=info['candidate'], subdivision_generation=7, source=source, images=images)],
        reused_parent_images=3, new_images=3, source_images=6, conditions=receipt['conditions'],
        actual_views=views, Blender_version=receipt['version'], crop=False, resize=False,
        image_check_script_sha256=IMAGE_CHECKER_SHA256,
        scope='Original WIDE_ROOT_FINISHED SPAN G7 versus one saved ROLLED_END_REBUILD G7. The generator parametrically rebuilt individual rolled ends. No source geometry averaging, new topology, subdivision, normal-field pass or Mandelbulb evaluation is introduced. Saved native/source/code/image receipts and matched camera/material checks only; no independent geometry replay or aesthetic certification.')


def compose(proof):
    root = Path(proof['root'])
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Earlier verified comparison output preserved.')
    title = ImageFont.truetype(r'C:\Windows\Fonts\malgunbd.ttf', 27)
    label = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 23)
    output.mkdir()
    labels = ('\uae30\uc874 \ub9d0\ub9bc \u00b7 \uc2e4\uc81c G7',
              '\ub05d \ud615\uc0c1 \uc7ac\uc870\ud615 \u00b7 \uc2e4\uc81c G7')
    view_labels = dict(front='\uc804\uccb4 \uc815\uba74', body_oblique='\ubab8\uccb4 \uc0ac\uc120', close_oblique='\uadfc\uc811 \uc0ac\uc120')
    boards = []
    for view in render.VIEWS:
        canvas = Image.new('RGB', (1800, 1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), f'SPAN \u00b7 {view_labels[view]} \u00b7 \ub05d \ud615\uc0c1 \uc7ac\uc870\ud615 \ube44\uad50 \u00b7 G7', font=title, fill='black')
        sources = []
        for column, current in enumerate(proof['states']):
            draw.text((900 * column + 24, 61), labels[column], font=label, fill='black')
            item = next(image for image in current['images'] if image['view'] == view)
            if render.digest(item['path']) != item['sha256']:
                raise ValueError('Original changed during composition.')
            with Image.open(item['path']) as image:
                if image.size != (900, 900):
                    raise ValueError('Original dimensions changed.')
                canvas.paste(image.convert('RGB'), (900 * column, 105))
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
    print('ROLLED_END_REBUILD_RENDER_VERIFICATION_PASS: 3 reused original G7 + 3 new actual G7 PNGs', flush=True)


if __name__ == '__main__':
    main()
