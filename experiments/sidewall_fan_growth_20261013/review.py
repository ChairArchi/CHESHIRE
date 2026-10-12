"""Verify frozen ROOT_ONLY/BRANCHED plus new SIDEWALL_FAN and compose eight boards.

The comparison reuses 16 original PNGs and adds eight new ones. This verifies
source/renderer/camera/material/PNG correspondence, not visual or geometric
success. Original source images are never edited, cropped or resized.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import math

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render = load_module('sidewall_review_render', HERE / 'render.py')
frozen = load_module('sidewall_frozen_connected_render', render.FROZEN_RENDER)
VIEWS, CASES = render.VIEWS, render.CASES
MODES = ('ROOT_ONLY', 'BRANCHED', 'SIDEWALL_FAN')
REFERENCE_ROOT = Path('E:/CHESHIRE_DATA/experiments/connected_fold_growth_20261012/trial01')
LABELS = dict(ROOT_ONLY='기존 trial01: 부모 접힘',
              BRANCHED='기존 trial01: cap 자식·손자',
              SIDEWALL_FAN='새 trial01: sidewall 분기')


def verify_state(root, mode, case, renderer, reused):
    folder, info, source = renderer.source_state(root, mode, case)
    hashes = renderer.code_hashes()
    receipt_path = folder / 'views/receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf8'))
    if (receipt.get('input_case') != case or receipt.get('candidate') != mode or
        receipt.get('subdivision_generation') != 5 or receipt.get('engine') != 'Blender Cycles' or
        receipt.get('views') != json.loads(json.dumps(VIEWS)) or
        receipt.get('resolution') != 900 or receipt.get('samples') != 24 or
        receipt.get('material') != render.MATERIAL or receipt.get('modifiers') != [] or
        receipt.get('normal_maps') is not False or receipt.get('code_sha256') != hashes or
        receipt.get('render_script_sha256') != hashes['render'] or
        Path(receipt.get('render_script', '')).resolve() != Path(renderer.__file__).resolve()):
        raise ValueError('Render identity/code/camera/material declaration differs: ' + str(folder))
    for key, value in source.items():
        if receipt.get(key) != value:
            raise ValueError('Saved source changed: ' + str(folder) + ' / ' + key)
    if not receipt.get('version'):
        raise ValueError('Missing Blender version.')
    render.require_close(receipt['conditions'], render.expected_conditions())
    arrays = receipt['source_arrays']
    if (arrays.get('xyz_sha256') != info['checks']['native_xyz_sha256'] or
        arrays.get('faces_sha256') != info['checks']['native_faces_sha256']):
        raise ValueError('Render-loaded native arrays differ from generation metadata.')
    if set(receipt.get('actual_views', {})) != set(VIEWS):
        raise ValueError('Missing actual camera observation.')
    declared_images = receipt.get('images', [])
    if len(declared_images) != 4 or {item['view'] for item in declared_images} != set(VIEWS):
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
        images.append(dict(view=view, path=str(path), sha256=image_hash, reused_reference=reused))
    state = dict(input_case=case, candidate=mode, subdivision_generation=5,
        reused_reference=reused, source_root=str(Path(root).resolve()),
        geometry=source['source'], geometry_sha256=source['source_sha256'],
        generation_source=source['generation_source'], generation_sha256=source['generation_sha256'],
        control_source=source['control_source'], control_sha256=source['control_sha256'],
        native_arrays=arrays, render_receipt=str(receipt_path),
        render_receipt_sha256=render.digest(receipt_path), images=images,
        render_script=receipt['render_script'], code_sha256=hashes,
        constructive_event_count_quarter_accepted=info.get('constructive_event_count'),
        reflected_constructive_event_instances=info.get('reflected_constructive_event_instances'))
    return state, receipt


def verify(root, reference_root=REFERENCE_ROOT):
    """All six states and 24 images are required; empty/missing inputs fail."""
    root, reference_root = Path(root).resolve(), Path(reference_root).resolve()
    if root == reference_root:
        raise ValueError('New output root must differ from the frozen reference root.')
    hashes, frozen_hashes = render.code_hashes(), frozen.code_hashes()
    if hashes['frozen_parent_renderer'] != frozen_hashes['render']:
        raise ValueError('Frozen reference renderer SHA differs.')
    if json.loads(json.dumps(frozen.VIEWS)) != json.loads(json.dumps(VIEWS)):
        raise ValueError('Declared camera recipes differ between renderers.')
    for key in ('broad_camera_recipe', 'shared_material_scene_recipe'):
        if hashes[key] != frozen_hashes[key]:
            raise ValueError('Original camera/material/scene recipe bytes differ: ' + key)
    render.require_close(frozen.expected_conditions(), render.expected_conditions())
    states, version, conditions, actual_views = [], None, None, None
    for case in CASES:
        for mode in MODES:
            reused = mode != 'SIDEWALL_FAN'
            renderer = frozen if reused else render
            source_root = reference_root if reused else root
            state, receipt = verify_state(source_root, mode, case, renderer, reused)
            if version is None:
                version, conditions, actual_views = receipt['version'], receipt['conditions'], receipt['actual_views']
            if (receipt['version'] != version or receipt['conditions'] != conditions or
                receipt['actual_views'] != actual_views):
                raise ValueError('Actual Blender version, conditions or cameras differ between old/new states.')
            states.append(state)
    reused_count = sum(len(s['images']) for s in states if s['reused_reference'])
    new_count = sum(len(s['images']) for s in states if not s['reused_reference'])
    if len(states) != 6 or reused_count != 16 or new_count != 8:
        raise ValueError('Exactly four frozen reference states plus two new states required.')
    return dict(passed=True, expected_cases=list(CASES), expected_modes=list(MODES),
        subdivision_generation=5, actual_mesh_states=len(states), source_images=reused_count + new_count,
        reused_reference_images=reused_count, newly_rendered_images=new_count,
        reference_root=str(reference_root), new_root=str(root),
        Blender_version=version, conditions=conditions, actual_views=actual_views,
        code_sha256=hashes, frozen_code_sha256=frozen_hashes,
        frozen_renderer_sha256_expected=render.FROZEN_RENDER_SHA256,
        crop=False, resize=False, states=states,
        scope='Saved native sources, frozen/new renderer code, common actual cameras/material and original PNG correspondence only',
        geometry_certification='Independent geometric verifier required; this review does not certify visual hierarchy, symmetry or topology')


def compose(root, verification):
    root = Path(root).resolve()
    if str(root) != verification['new_root']:
        raise ValueError('Comparison may only be saved in the verified new root.')
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
            heading = f'{case} · {view} · 실제 G05 동일 조건 / 기존 16장 재사용 + 신규 8장'
            if draw.textbbox((0, 0), heading, font=title)[2] > 2652:
                raise ValueError('Heading exceeds comparison width.')
            draw.text((24, 12), heading, font=title, fill='black')
            sources = []
            for index, mode in enumerate(MODES):
                caption = LABELS[mode]
                if draw.textbbox((0, 0), caption, font=label)[2] > 852:
                    raise ValueError('Caption exceeds original-image column.')
                draw.text((index * 900 + 24, 61), caption, font=label, fill='black')
                state = states[case, mode]
                item = next(i for i in state['images'] if i['view'] == view)
                path = Path(item['path'])
                if render.digest(path) != item['sha256']:
                    raise ValueError('Original image changed while composing.')
                with Image.open(path) as image:
                    canvas.paste(image.convert('RGB'), (index * 900, 105))
                sources.append(dict(candidate=mode, caption=caption, path=str(path), sha256=item['sha256'],
                                    reused_reference=state['reused_reference']))
            target = output / f'{case}_{view}.png'
            canvas.save(target)
            boards.append(dict(output=str(target), output_sha256=render.digest(target),
                input_case=case, view=view, crop=False, resize=False, sources=sources))
    source_list = dict(reference_root=verification['reference_root'], new_root=verification['new_root'],
        reused_reference_images=16, newly_rendered_images=8, original_images_total=24,
        source_note='ROOT_ONLY and BRANCHED: frozen connected trial01 originals; SIDEWALL_FAN: newly rendered originals',
        boards=boards)
    (output / 'SOURCE_LIST.json').write_text(json.dumps(source_list, ensure_ascii=False, indent=2), encoding='utf8')
    verification['boards'] = boards
    verification['comparison_boards'] = len(boards)
    verification['source_list_sha256'] = render.digest(output / 'SOURCE_LIST.json')
    verification['review_script_sha256'] = render.digest(__file__)
    (root / 'RENDER_VERIFICATION.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    return verification


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--reference-root', type=Path, default=REFERENCE_ROOT)
    parser.add_argument('--verify-only', action='store_true', help='Read-only source/receipt/PNG verification; no new boards.')
    args = parser.parse_args()
    verification = verify(args.root, args.reference_root)
    if not args.verify_only:
        compose(args.root, verification)
    print('RENDER_VERIFICATION_PASS: 16 frozen + 8 new original PNGs',
          '' if args.verify_only else '/ 8 boards', flush=True)


if __name__ == '__main__':
    main()
