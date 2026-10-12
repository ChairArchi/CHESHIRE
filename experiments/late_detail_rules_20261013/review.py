"""Verify four matched late-detail conditions and compose eight four-column boards.

NEUTRAL reuses eight frozen SIDEWALL_FAN G05 originals only after exact actual
control/native array identity and independent replay PASS. Three new conditions
provide 24 new PNGs. Image correspondence is separate from aesthetic success.
"""
from pathlib import Path
import argparse
import importlib.util
import json

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FROZEN_REVIEW = HERE.parent / 'sidewall_fan_growth_20261013/review.py'
FROZEN_REVIEW_SHA256 = 'de2cffcf82e18de79f2ddd8e22b833a9bf09d808e3c018161062194d511837e6'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render = load_module('late_detail_review_render', HERE / 'render.py')
previous = load_module('late_detail_frozen_sidewall_review', FROZEN_REVIEW)
VIEWS, CASES, MODES = render.VIEWS, render.CASES, render.MODES
LABELS = dict(NEUTRAL='NEUTRAL · 기존 G05 원본', EQ4_ONLY='EQ4_ONLY · 신규',
              NORMAL_ONLY='NORMAL_ONLY · 신규', COMBINED='COMBINED · 신규')
HASH_KEYS = ('control_xyz_sha256', 'control_faces_sha256', 'chart_sha256',
             'native_xyz_sha256', 'native_faces_sha256')


def independent_state(root, mode, case, info, source, verification):
    """Bind actual replay/native proof to the exact saved generation metadata."""
    if verification['cases'][case].get('passed') is not True:
        raise ValueError('Independent case PASS required: ' + case)
    proof = verification['cases'][case]['states'][mode]
    if (proof.get('passed') is not True or
        proof.get('generation_json_sha256') != source['generation_sha256'] or
        proof.get('actual_native_topology', {}).get('passed') is not True or
        any(proof.get('actual_native_symmetry', {}).get(axis, {}).get('passed') is not True for axis in ('X', 'Y')) or
        any(proof.get('hashes', {}).get(key) != info['checks'][key] for key in HASH_KEYS)):
        raise ValueError('Actual replay/topology/symmetry proof differs from saved state: ' + case + '/' + mode)
    return proof


def neutral_reference(root, case, info, source, proof):
    identity = info.get('neutral_identity', {})
    expected = info['preserved_parent']['neutral']
    actual_identity = proof.get('neutral_identity', {})
    if (identity.get('passed') is not True or identity.get('reference') != expected or
        actual_identity.get('passed') is not True or actual_identity.get('reference') != expected or
        actual_identity.get('arrays') != identity.get('arrays')):
        raise ValueError('Independent exact NEUTRAL identity binding required: ' + case)
    inventories = dict(control_quad=['anchors', 'chart', 'classes', 'faces', 'generation', 'rest', 'surface', 'xyz'],
                       geometry=['faces', 'xyz'])
    if set(identity.get('arrays', {})) != {'control_quad.npz', 'geometry.npz'}:
        raise ValueError('Complete control/native identity inventory required.')
    for name, keys in inventories.items():
        entry = identity['arrays'][name + '.npz']
        if entry.get('exact_dtype_shape_bytes') is not True or entry.get('array_keys') != keys:
            raise ValueError('All array-key dtype/shape/byte identity required: ' + name)
    old_folder = render.PARENT_ROOT / 'SIDEWALL_FAN' / case / 'G05'
    if Path(expected['path']).resolve() != old_folder.resolve():
        raise ValueError('NEUTRAL reference must be the frozen actual SIDEWALL_FAN G05.')
    old_info = render.checked_stage(expected, 5, case)
    if any(info['checks'][key] != old_info['checks'][key] for key in HASH_KEYS):
        raise ValueError('NEUTRAL control/chart/native array hashes differ from image source.')
    state, receipt = previous.verify_state(render.PARENT_ROOT, 'SIDEWALL_FAN', case, previous.render, True)
    state.update(candidate='NEUTRAL', image_candidate='SIDEWALL_FAN',
        reused_reference=True, bound_neutral_source=source,
        neutral_identity=identity, neutral_generation_sha256=source['generation_sha256'])
    return state, receipt


def verify(root):
    root = Path(root).resolve()
    if root == render.PARENT_ROOT.resolve():
        raise ValueError('New output root must differ from frozen reference root.')
    hashes = render.code_hashes()
    if render.digest(FROZEN_REVIEW) != FROZEN_REVIEW_SHA256:
        raise ValueError('Frozen source/image verifier changed.')
    old_hashes = previous.render.code_hashes()
    if hashes['frozen_sidewall_renderer'] != old_hashes['render']:
        raise ValueError('Frozen source renderer differs from old receipts.')
    if json.loads(json.dumps(previous.VIEWS)) != json.loads(json.dumps(VIEWS)):
        raise ValueError('Old/new camera recipes differ.')
    for key in ('broad_camera_recipe', 'shared_material_scene_recipe'):
        if hashes[key] != old_hashes[key]:
            raise ValueError('Old/new original scene recipe bytes differ: ' + key)
    verification_path = root / 'VERIFICATION.json'
    verification = render.read_json(verification_path)
    if (verification.get('status') != 'PASS' or verification.get('expected_cases') != list(CASES) or
        verification.get('expected_modes') != list(MODES) or set(verification.get('cases', {})) != set(CASES)):
        raise ValueError('Independent complete two-input/four-mode verification PASS required.')
    states, version, conditions, actual_views = [], None, None, None
    for case in CASES:
        if set(verification['cases'][case].get('states', {})) != set(MODES):
            raise ValueError('Exactly four independently replayed conditions required: ' + case)
        for mode in MODES:
            _, info, source = render.source_state(root, mode, case)
            proof = independent_state(root, mode, case, info, source, verification)
            if mode == 'NEUTRAL':
                state, receipt = neutral_reference(root, case, info, source, proof)
            else:
                state, receipt = previous.verify_state(root, mode, case, render, False)
                state.update(image_candidate=mode, source_provenance=source)
            if version is None:
                version, conditions, actual_views = receipt['version'], receipt['conditions'], receipt['actual_views']
            if (receipt['version'] != version or receipt['conditions'] != conditions or
                receipt['actual_views'] != actual_views):
                raise ValueError('Actual old/new Blender version, cameras or material/scene conditions differ.')
            state['independent_geometry_generation_sha256'] = proof['generation_json_sha256']
            states.append(state)
    reused_count = sum(len(s['images']) for s in states if s['reused_reference'])
    new_count = sum(len(s['images']) for s in states if not s['reused_reference'])
    if len(states) != 8 or reused_count != 8 or new_count != 24:
        raise ValueError('Exactly eight frozen reference plus 24 new original PNGs required.')
    return dict(passed=True, expected_cases=list(CASES), expected_modes=list(MODES),
        subdivision_generation=5, source_generation=4, added_CC_passes=1,
        actual_mesh_states=len(states), source_images=reused_count + new_count,
        reused_reference_images=reused_count, newly_rendered_images=new_count,
        reference_root=str(render.PARENT_ROOT.resolve()), new_root=str(root),
        Blender_version=version, conditions=conditions, actual_views=actual_views,
        code_sha256=hashes, frozen_code_sha256=old_hashes,
        frozen_review_sha256=FROZEN_REVIEW_SHA256,
        independent_geometry_verification=str(verification_path),
        independent_geometry_verification_sha256=render.digest(verification_path),
        neutral_identity_scope='All control/native array keys, dtype, shape and bytes are identical; NPZ containers/evidence/metadata are not claimed identical.',
        crop=False, resize=False, states=states,
        scope='Saved source/parent/code, independent replay receipt, old/new renderer conditions and original PNG correspondence',
        visual_success='NOT_ASSESSED_BY_COMPOSITOR',
        geometry_certification='Actual geometry claims belong to the separately linked independent VERIFICATION.json; aesthetic/reference fidelity remains unassessed')


def compose(root, verification):
    root = Path(root).resolve()
    if str(root) != verification['new_root']:
        raise ValueError('Only the verified new root may receive comparison boards.')
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
            canvas = Image.new('RGB', (3600, 1020), 'white')
            draw = ImageDraw.Draw(canvas)
            heading = f'{case} · {view} · 실제 G05 동일 조건 / NEUTRAL 기존 8장 + 신규 24장'
            if draw.textbbox((0, 0), heading, font=title)[2] > 3552:
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
                sources.append(dict(candidate=mode, image_candidate=state['image_candidate'], caption=caption,
                    path=str(path), sha256=item['sha256'], reused_reference=state['reused_reference']))
            target = output / f'{case}_{view}.png'
            canvas.save(target)
            boards.append(dict(output=str(target), output_sha256=render.digest(target), input_case=case,
                               view=view, crop=False, resize=False, sources=sources))
    source_list = dict(reference_root=verification['reference_root'], new_root=verification['new_root'],
        reused_reference_images=8, newly_rendered_images=24, original_images_total=32,
        source_note='NEUTRAL: frozen SIDEWALL_FAN G05 originals after independent exact array identity PASS; other three modes: newly rendered originals',
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
    parser.add_argument('--verify-only', action='store_true', help='Read-only source/replay/receipt/PNG verification; no new boards.')
    args = parser.parse_args()
    verification = verify(args.root)
    if not args.verify_only:
        compose(args.root, verification)
    print('RENDER_VERIFICATION_PASS: 8 frozen NEUTRAL + 24 new original PNGs',
          '' if args.verify_only else '/ 8 four-column boards', flush=True)


if __name__ == '__main__':
    main()
