"""Match six reused DIRECTIONAL G05 PNGs and twelve new G06 PNGs; six boards."""
from pathlib import Path
import argparse
import importlib.util
import json
import math
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('directional_g6_boards_render', HERE / 'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
MODES = ('BASE_G5', 'DEPTH_08', 'DEPTH_16')
LABELS = ('BASE_G5 · 기존 DIRECTIONAL G5', 'DEPTH_08 · 신규 G6 / 0.8', 'DEPTH_16 · 신규 G6 / 1.6')


def state(root, mode, case):
    old = mode == 'BASE_G5'
    if old:
        folder = render.PARENT_ROOT / 'DIRECTIONAL' / case / 'G05'
        info = render.read_json(folder / 'generation.json')
        source = dict(source=str(folder / 'geometry.npz'), source_sha256=render.digest(folder / 'geometry.npz'),
            generation_source=str(folder / 'generation.json'), generation_sha256=render.digest(folder / 'generation.json'),
            control_source=str(folder / 'control_quad.npz'), control_sha256=render.digest(folder / 'control_quad.npz'))
        hashes = render.base.code_hashes()
        if hashes['render'] != render.FROZEN_SHA256:
            raise ValueError('Frozen parent renderer changed.')
    else:
        folder, info, source = render.source_state(root, mode, case)
        hashes = render.code_hashes()
    candidate, generation = ('DIRECTIONAL', 5) if old else (mode, 6)
    if (info.get('input_case') != case or info.get('candidate') != candidate or
        info.get('subdivision_generation') != generation or
        source['source_sha256'] != info['geometry_file_sha256'] or source['control_sha256'] != info['control_file_sha256']):
        raise ValueError('Saved state identity/geometry hash differs.')
    receipt = render.read_json(folder / 'views/receipt.json')
    if (receipt.get('input_case') != case or receipt.get('candidate') != candidate or
        receipt.get('subdivision_generation') != generation or receipt.get('code_sha256') != hashes or
        any(receipt.get(key) != value for key, value in source.items())):
        raise ValueError('Actual source/render-code binding differs: ' + case + '/' + mode)
    render.require_close(receipt['conditions'], render.base.expected_conditions())
    arrays = receipt['source_arrays']
    if (arrays.get('xyz_sha256') != info['checks']['native_xyz_sha256'] or
        arrays.get('faces_sha256') != info['checks']['native_faces_sha256']):
        raise ValueError('Loaded native-array hashes differ from saved generation.')
    images = {item['view']: item for item in receipt['images']}
    if len(images) != len(receipt['images']) or (not old and set(images) != set(render.VIEWS)):
        raise ValueError('Distinct three new render views required.')
    actual_views, originals = {}, []
    for view, (position, target, scale) in render.VIEWS.items():
        direction = [t - p for p, t in zip(position, target)]
        length = math.sqrt(sum(x*x for x in direction))
        expected = dict(position=list(position), target=list(target), scale=scale,
                        forward=[x / length for x in direction])
        render.require_close(receipt['actual_views'][view], expected, 'camera.' + view)
        if receipt['views'][view] != json.loads(json.dumps(render.VIEWS[view])):
            raise ValueError('Camera recipe declaration differs.')
        actual_views[view] = receipt['actual_views'][view]
        path = folder / 'views' / (view + '.png')
        checksum = render.digest(path)
        if images[view]['filename'] != path.name or images[view]['sha256'] != checksum:
            raise ValueError('Original PNG changed: ' + str(path))
        with Image.open(path) as image:
            if image.size != (900, 900) or image.format != 'PNG':
                raise ValueError('Original 900 by 900 PNG required.')
            image.verify()
        originals.append(dict(view=view, path=str(path), sha256=checksum))
    return dict(input_case=case, candidate=mode, image_candidate=candidate, generation=generation,
        reused_reference=old, source=source, receipt=str(folder / 'views/receipt.json'),
        receipt_sha256=render.digest(folder / 'views/receipt.json'), code_sha256=hashes, images=originals), receipt, actual_views


def verify(root):
    root = Path(root).resolve()
    if root == render.PARENT_ROOT.resolve():
        raise ValueError('New root must differ from frozen G05 reference.')
    render.code_hashes()
    index = render.read_json(root / 'source_index.json')
    states, version, conditions, views = [], None, None, None
    for case in render.CASES:
        for mode in MODES:
            current, receipt, actual = state(root, mode, case)
            if mode == 'BASE_G5':
                parent = index[case]
                if (Path(parent['path']).resolve() != (render.PARENT_ROOT / 'DIRECTIONAL' / case / 'G05').resolve() or
                    parent['generation_sha256'] != current['source']['generation_sha256'] or
                    parent['control_sha256'] != current['source']['control_sha256'] or
                    parent['geometry_sha256'] != current['source']['source_sha256']):
                    raise ValueError('Reused G05 images must depict the actual G06 parent.')
            if version is None:
                version, conditions, views = receipt['version'], receipt['conditions'], actual
            if receipt['version'] != version or receipt['conditions'] != conditions or actual != views:
                raise ValueError('Actual old/new Blender version, conditions or three cameras differ.')
            for key in ('broad_camera_recipe', 'shared_material_scene_recipe'):
                if current['code_sha256'][key] != render.code_hashes()[key]:
                    raise ValueError('Original camera/material scene recipe bytes differ.')
            states.append(current)
    if len(states) != 6 or sum(len(s['images']) for s in states if s['reused_reference']) != 6 or sum(len(s['images']) for s in states if not s['reused_reference']) != 12:
        raise ValueError('Exactly six existing plus twelve new original PNGs required.')
    return dict(passed=True, new_root=str(root), reference_root=str(render.PARENT_ROOT.resolve()),
        referenced_G05_states=2, new_G06_states=4, reused_reference_images=6, new_images=12, states=states,
        conditions=conditions, actual_views=views, Blender_version=version, crop=False, resize=False,
        scope='Saved sources, current renderer/code/native-array receipts, same actual camera/material/scene conditions and original PNG hashes only.',
        geometry_certification='Root geometry checks are separate; no full replay, topology or aesthetic certification by this adapter.')


def compose(root, proof):
    root = Path(root).resolve()
    output = root / 'images'
    if str(root) != proof['new_root']:
        raise ValueError('Only verified root may receive boards.')
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Earlier comparison preserved.')
    title = ImageFont.truetype(r'C:\Windows\Fonts\malgunbd.ttf', 28)
    label = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 23)
    states = {(s['input_case'], s['candidate']): s for s in proof['states']}
    output.mkdir()
    boards = []
    for case in render.CASES:
        for view in render.VIEWS:
            canvas = Image.new('RGB', (2700, 1020), 'white')
            draw = ImageDraw.Draw(canvas)
            draw.text((24, 12), f'{case} · {view} · 실제 G5 부모 / G6 깊이 대조 · 기존 6장 + 신규 12장', font=title, fill='black')
            sources = []
            for column, mode in enumerate(MODES):
                draw.text((900*column + 24, 61), LABELS[column], font=label, fill='black')
                item = next(i for i in states[case, mode]['images'] if i['view'] == view)
                if render.digest(item['path']) != item['sha256']:
                    raise ValueError('Original changed during composition.')
                with Image.open(item['path']) as image:
                    if image.size != (900, 900):
                        raise ValueError('Original dimensions changed.')
                    canvas.paste(image.convert('RGB'), (900*column, 105))
                sources.append(dict(candidate=mode, **item))
            path = output / f'{case}_{view}.png'
            canvas.save(path)
            boards.append(dict(input_case=case, view=view, output=str(path), sha256=render.digest(path), sources=sources))
    proof.update(boards=boards, comparison_boards=6, boards_script_sha256=render.digest(__file__))
    for path in (output / 'SOURCE_LIST.json', root / 'RENDER_VERIFICATION.json'):
        path.write_text(json.dumps(proof, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    proof = verify(args.root)
    if not args.verify_only:
        compose(args.root, proof)
    print('RENDER_VERIFICATION_PASS: 6 reused G5 + 12 new G6 PNGs', flush=True)


if __name__ == '__main__':
    main()
