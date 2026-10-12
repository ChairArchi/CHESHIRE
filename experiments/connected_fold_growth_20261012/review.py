"""Verify all six real G05 render sources and compose eight unchanged-size boards.

This verifies source/renderer/image correspondence, not aesthetic quality,
symmetry, collision freedom or topology. No source imagery is edited or resized.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import math

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('connected_review_render', HERE / 'render.py')
render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render)
VIEWS, MODES, CASES = render.VIEWS, render.MODES, render.CASES
LABELS = dict(SMOOTH_CONTROL='대조: 활성 이벤트 없이 CC 2회',
              ROOT_ONLY='부모 접힘 생성 후 CC 2회',
              BRANCHED='부모·자식·손자 연결 성장 후 CC 2회')


def verify(root):
    """A missing case/state/image fails; an empty root can never pass."""
    root = Path(root).resolve()
    hashes = render.code_hashes()
    states, version, common_conditions = [], None, None
    for case in CASES:
        for mode in MODES:
            folder, info, source = render.source_state(root, mode, case)
            receipt_path = folder / 'views/receipt.json'
            receipt = json.loads(receipt_path.read_text(encoding='utf8'))
            if (receipt.get('input_case') != case or receipt.get('candidate') != mode or
                receipt.get('subdivision_generation') != 5 or receipt.get('engine') != 'Blender Cycles' or
                receipt.get('views') != json.loads(json.dumps(VIEWS)) or
                receipt.get('resolution') != 900 or receipt.get('samples') != 24 or
                receipt.get('material') != render.MATERIAL or receipt.get('modifiers') != [] or
                receipt.get('normal_maps') is not False or receipt.get('code_sha256') != hashes or
                receipt.get('render_script_sha256') != hashes['render'] or
                Path(receipt.get('render_script', '')).resolve() != (HERE / 'render.py').resolve()):
                raise ValueError('Render identity/code/camera/material declaration differs: ' + str(folder))
            for key, value in source.items():
                if receipt.get(key) != value:
                    raise ValueError('Saved source changed: ' + str(folder) + ' / ' + key)
            if not receipt.get('version'):
                raise ValueError('Missing Blender version.')
            version = receipt['version'] if version is None else version
            common_conditions = receipt['conditions'] if common_conditions is None else common_conditions
            if receipt['version'] != version or receipt['conditions'] != common_conditions:
                raise ValueError('Different Blender version or actual render conditions between states.')
            render.require_close(receipt['conditions'], render.expected_conditions())
            arrays = receipt['source_arrays']
            if (arrays.get('xyz_sha256') != info['checks']['native_xyz_sha256'] or
                arrays.get('faces_sha256') != info['checks']['native_faces_sha256']):
                raise ValueError('Render-loaded native arrays do not match generation metadata.')
            if set(receipt.get('actual_views', {})) != set(VIEWS):
                raise ValueError('Missing actual camera observation.')
            declared_images = receipt.get('images', [])
            if (len(declared_images) != 4 or {item['view'] for item in declared_images} != set(VIEWS)):
                raise ValueError('Exactly four distinct original renders required.')
            by_view = {item['view']: item for item in declared_images}
            images = []
            for view, (position, target, scale) in VIEWS.items():
                direction = [t - p for p, t in zip(position, target)]
                length = math.sqrt(sum(value * value for value in direction))
                expected = dict(position=list(position), target=list(target), scale=scale,
                                forward=[value / length for value in direction])
                render.require_close(receipt['actual_views'][view], expected, 'actual_camera.' + view)
                path = folder / 'views' / f'{view}.png'
                image_hash = render.digest(path)
                if by_view[view]['filename'] != path.name or by_view[view]['sha256'] != image_hash:
                    raise ValueError('Original PNG changed: ' + str(path))
                with Image.open(path) as image:
                    if image.size != (900, 900) or image.format != 'PNG':
                        raise ValueError('Original 900 by 900 PNG required: ' + str(path))
                    image.verify()
                images.append(dict(view=view, path=str(path), sha256=image_hash))
            states.append(dict(input_case=case, candidate=mode, subdivision_generation=5,
                geometry=source['source'], geometry_sha256=source['source_sha256'],
                generation_source=source['generation_source'], generation_sha256=source['generation_sha256'],
                control_source=source['control_source'], control_sha256=source['control_sha256'],
                native_arrays=arrays, render_receipt=str(receipt_path),
                render_receipt_sha256=render.digest(receipt_path), images=images,
                constructive_event_count_quarter_accepted=info.get('constructive_event_count')))
    return dict(passed=True, expected_cases=list(CASES), expected_modes=list(MODES),
        subdivision_generation=5, actual_mesh_states=len(states), source_images=sum(len(s['images']) for s in states),
        Blender_version=version, conditions=common_conditions, code_sha256=hashes,
        crop=False, resize=False, states=states,
        scope='Saved G05 native source, renderer, cameras, material and original PNG correspondence only',
        geometry_certification='Independent geometric verifier required; renderer/review does not certify symmetry or topology')


def compose(root, verification):
    root = Path(root).resolve()
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Earlier comparison/verification preserved.')
    title = ImageFont.truetype(r'C:\Windows\Fonts\malgunbd.ttf', 28)
    label = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 23)
    states = {(s['input_case'], s['candidate']): s for s in verification['states']}
    output.mkdir()
    boards = []
    for case in CASES:
        for view in VIEWS:
            canvas = Image.new('RGB', (2700, 1020), 'white')
            draw = ImageDraw.Draw(canvas)
            heading = f'{case} · {view} · 동일 카메라·재질 / 실제 G05 대안 비교'
            draw.text((24, 12), heading, font=title, fill='black')
            sources = []
            for index, mode in enumerate(MODES):
                caption = LABELS[mode]
                if draw.textbbox((0, 0), caption, font=label)[2] > 852:
                    raise ValueError('Caption exceeds its original-image column.')
                draw.text((index * 900 + 24, 61), caption, font=label, fill='black')
                item = next(i for i in states[case, mode]['images'] if i['view'] == view)
                path = Path(item['path'])
                if render.digest(path) != item['sha256']:
                    raise ValueError('Original image changed while composing.')
                with Image.open(path) as image:
                    canvas.paste(image.convert('RGB'), (index * 900, 105))
                sources.append(dict(candidate=mode, caption=caption, path=str(path), sha256=item['sha256']))
            target = output / f'{case}_{view}.png'
            canvas.save(target)
            boards.append(dict(output=str(target), output_sha256=render.digest(target),
                input_case=case, view=view, crop=False, resize=False, sources=sources))
    (output / 'SOURCE_LIST.json').write_text(json.dumps(boards, ensure_ascii=False, indent=2), encoding='utf8')
    verification['boards'] = boards
    verification['comparison_boards'] = len(boards)
    verification['source_list_sha256'] = render.digest(output / 'SOURCE_LIST.json')
    verification['review_script_sha256'] = render.digest(__file__)
    (root / 'RENDER_VERIFICATION.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    return verification


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true', help='Read-only source/receipt/PNG verification; no new board files.')
    args = parser.parse_args()
    verification = verify(args.root)
    if not args.verify_only:
        compose(args.root, verification)
    print('RENDER_VERIFICATION_PASS', verification['actual_mesh_states'], 'states /',
          verification['source_images'], 'original images',
          '' if args.verify_only else '/ 8 boards', flush=True)


if __name__ == '__main__':
    main()
