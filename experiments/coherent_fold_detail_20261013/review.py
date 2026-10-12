"""Verify frozen COMBINED plus three coherent-rule candidates and compose boards.

Two frozen baseline states supply eight reused PNGs. Six newly replayed states
supply 24 new PNGs. No baseline mesh is generated or claimed newly replayed.
Source/condition correspondence is separate from visual hierarchy or beauty.
"""
from pathlib import Path
import argparse
import importlib.util
import json

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FROZEN_REVIEW = HERE.parent / 'late_detail_rules_20261013/review.py'
FROZEN_REVIEW_SHA256 = '288828789e1a4366fef1359a256c8ab44c505f1b273dd46972335daea5c58fa1'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render = load_module('coherent_detail_review_render', HERE / 'render.py')
previous = load_module('coherent_detail_frozen_late_review', FROZEN_REVIEW)
VIEWS, CASES = render.VIEWS, render.CASES
NEW_MODES = render.MODES
MODES = ('COMBINED',) + NEW_MODES
LABELS = dict(COMBINED='COMBINED · 기존 G05 원본', COHERENT='COHERENT · 신규',
              DIRECTIONAL='DIRECTIONAL · 신규', ROLE_CURVATURE='ROLE_CURVATURE · 신규')
HASH_KEYS = previous.HASH_KEYS
SHARED_HASH_KEYS = ('control_faces_sha256', 'chart_sha256', 'native_faces_sha256')


def independent_state(root, mode, case, info, source, verification):
    return previous.independent_state(root, mode, case, info, source, verification)


def baseline_reference(root, case):
    """Check existing actual PASS/image provenance, without replaying old meshes."""
    source, _, provenance = render.bound_parent(root, case)
    info = render.checked_baseline(source, case)
    folder, old_info, old_source = previous.render.source_state(render.BASELINE_ROOT, 'COMBINED', case)
    if info != old_info or folder.resolve() != Path(source['baseline']['path']).resolve():
        raise ValueError('Frozen baseline renderer and bound actual source disagree.')
    old_parent = old_info['preserved_parent']
    if any(source.get(key) != value for key, value in old_parent.items()):
        raise ValueError('Baseline and new candidates must share all actual G04/G03/neutral parent provenance.')
    verification = render.read_json(source['baseline_verification'])
    proof = previous.independent_state(render.BASELINE_ROOT, 'COMBINED', case,
                                        old_info, old_source, verification)
    state, receipt = previous.previous.verify_state(render.BASELINE_ROOT, 'COMBINED', case,
                                                     previous.render, True)
    old_render = render.read_json(source['baseline_render_verification'])
    if render.digest(render.BASELINE_ROOT / 'images/SOURCE_LIST.json') != old_render.get('source_list_sha256'):
        raise ValueError('Frozen baseline source-image inventory changed.')
    entries = [entry for entry in old_render['states']
               if entry['input_case'] == case and entry['candidate'] == 'COMBINED']
    if len(entries) != 1:
        raise ValueError('Exactly one frozen COMBINED render state required.')
    entry = entries[0]
    fields = ('geometry', 'geometry_sha256', 'generation_source', 'generation_sha256',
              'control_source', 'control_sha256', 'native_arrays', 'render_receipt',
              'render_receipt_sha256', 'render_script', 'code_sha256')
    if any(entry.get(key) != state[key] for key in fields):
        raise ValueError('Frozen baseline PASS render/source/receipt provenance differs.')
    old_images = {item['view']: (item['path'], item['sha256']) for item in entry['images']}
    actual_images = {item['view']: (item['path'], item['sha256']) for item in state['images']}
    if old_images != actual_images:
        raise ValueError('Frozen baseline PASS image inventory differs from actual PNGs.')
    if (old_render.get('Blender_version') != receipt['version'] or
        old_render.get('conditions') != receipt['conditions'] or
        old_render.get('actual_views') != receipt['actual_views'] or
        old_render.get('code_sha256') != previous.render.code_hashes() or
        old_render.get('review_script_sha256') != FROZEN_REVIEW_SHA256):
        raise ValueError('Frozen baseline render verification conditions/code differ.')
    state.update(image_candidate='COMBINED', reused_reference=True,
        baseline_reference_source=source['baseline'], source_provenance=old_source,
        prior_geometry_verification=source['baseline_verification'],
        prior_geometry_verification_sha256=source['baseline_verification_sha256'],
        prior_render_verification=source['baseline_render_verification'],
        prior_render_verification_sha256=source['baseline_render_verification_sha256'],
        independent_geometry_generation_sha256=proof['generation_json_sha256'],
        verification_scope='Frozen prior actual geometry PASS and current source/PNG hashes; no new baseline mesh or replay.',
        common_parent_control_sha256=source['control_sha256'], common_parent_generation_sha256=source['generation_sha256'])
    return state, receipt, old_info, source


def verify(root):
    root = Path(root).resolve()
    if root in (render.PARENT_ROOT.resolve(), render.BASELINE_ROOT.resolve()):
        raise ValueError('New output root must differ from both frozen roots.')
    hashes = render.code_hashes()
    if render.digest(FROZEN_REVIEW) != FROZEN_REVIEW_SHA256:
        raise ValueError('Frozen late-detail source/image verifier changed.')
    old_hashes = previous.render.code_hashes()
    if hashes['frozen_late_renderer'] != old_hashes['render']:
        raise ValueError('Frozen baseline renderer SHA differs from old original receipts.')
    if json.loads(json.dumps(previous.VIEWS)) != json.loads(json.dumps(VIEWS)):
        raise ValueError('Old/new camera recipes differ.')
    for key in ('broad_camera_recipe', 'shared_material_scene_recipe'):
        if hashes[key] != old_hashes[key]:
            raise ValueError('Old/new original scene recipe bytes differ: ' + key)
    render.require_close(previous.render.expected_conditions(), render.expected_conditions())
    verification_path = root / 'VERIFICATION.json'
    verification = render.read_json(verification_path)
    if (verification.get('status') != 'PASS' or verification.get('expected_cases') != list(CASES) or
        verification.get('expected_modes') != list(NEW_MODES) or
        set(verification.get('cases', {})) != set(CASES)):
        raise ValueError('Independent complete two-input/three-new-mode actual verification PASS required.')
    states, version, conditions, actual_views = [], None, None, None
    for case in CASES:
        if set(verification['cases'][case].get('states', {})) != set(NEW_MODES):
            raise ValueError('Exactly three independently replayed NEW conditions required: ' + case)
        baseline, baseline_receipt, baseline_info, parent_source = baseline_reference(root, case)
        if version is None:
            version, conditions, actual_views = (baseline_receipt['version'],
                                                 baseline_receipt['conditions'], baseline_receipt['actual_views'])
        states.append(baseline)
        receipts = [baseline_receipt]
        for mode in NEW_MODES:
            _, info, source = render.source_state(root, mode, case)
            proof = independent_state(root, mode, case, info, source, verification)
            if (info['source_control_sha256'] != parent_source['control_sha256'] or
                info['preserved_parent'] != parent_source or
                any(info['checks'][key] != baseline_info['checks'][key] for key in SHARED_HASH_KEYS)):
                raise ValueError('New/baseline actual G04 source or ordered G05 topology/chart differs: ' + case + '/' + mode)
            state, receipt = previous.previous.verify_state(root, mode, case, render, False)
            state.update(image_candidate=mode, source_provenance=source,
                independent_geometry_generation_sha256=proof['generation_json_sha256'],
                common_parent_control_sha256=parent_source['control_sha256'],
                common_parent_generation_sha256=parent_source['generation_sha256'],
                baseline_shared_hashes={key: baseline_info['checks'][key] for key in SHARED_HASH_KEYS},
                verification_scope='New actual independent coupled CC replay/topology/symmetry PASS, bound to this exact G05 metadata.')
            states.append(state)
            receipts.append(receipt)
        if any(receipt['version'] != version or receipt['conditions'] != conditions or
               receipt['actual_views'] != actual_views for receipt in receipts):
            raise ValueError('Actual baseline/new Blender version, cameras or material/scene conditions differ.')
    reused_count = sum(len(state['images']) for state in states if state['reused_reference'])
    new_count = sum(len(state['images']) for state in states if not state['reused_reference'])
    if len(states) != 8 or reused_count != 8 or new_count != 24:
        raise ValueError('Exactly two frozen baseline states/eight PNGs plus six new states/24 PNGs required.')
    return dict(passed=True, expected_cases=list(CASES), expected_modes=list(MODES),
        expected_new_modes=list(NEW_MODES), subdivision_generation=5, source_generation=4, added_CC_passes=1,
        actual_mesh_states=8, newly_replayed_mesh_states=6, referenced_prior_mesh_states=2,
        source_images=32, reused_reference_images=8, newly_rendered_images=24,
        reference_root=str(render.BASELINE_ROOT.resolve()), parent_root=str(render.PARENT_ROOT.resolve()), new_root=str(root),
        Blender_version=version, conditions=conditions, actual_views=actual_views,
        code_sha256=hashes, frozen_code_sha256=old_hashes, frozen_review_sha256=FROZEN_REVIEW_SHA256,
        independent_geometry_verification=str(verification_path),
        independent_geometry_verification_sha256=render.digest(verification_path),
        baseline_scope='Two frozen COMBINED states referenced through prior actual PASS, current source/parent/code/receipt/PNG hashes; no baseline rerun.',
        shared_scope='Actual same SIDEWALL_FAN G04 source hashes and ordered G05 control/native faces plus transported chart hashes.',
        crop=False, resize=False, states=states,
        scope='New independent replay receipt, frozen baseline PASS provenance, actual shared parent/topology/chart, old/new scene conditions and original PNG correspondence.',
        visual_success='NOT_ASSESSED_BY_COMPOSITOR',
        geometry_certification='Geometry claims belong to independently linked receipts; aesthetic/reference fidelity remains unassessed.')


def compose(root, verification):
    root = Path(root).resolve()
    if str(root) != verification['new_root']:
        raise ValueError('Only the verified new root may receive comparison boards.')
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Earlier comparison/verification preserved.')
    title = ImageFont.truetype(r'C:\Windows\Fonts\malgunbd.ttf', 28)
    label = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 23)
    states = {(state['input_case'], state['candidate']): state for state in verification['states']}
    output.mkdir()
    boards = []
    for case in CASES:
        for view in VIEWS:
            canvas = Image.new('RGB', (3600, 1020), 'white')
            draw = ImageDraw.Draw(canvas)
            heading = f'{case} · {view} · 실제 G05 동일 조건 / COMBINED 기존 8장 + 신규 24장'
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
                item = next(item for item in state['images'] if item['view'] == view)
                path = Path(item['path'])
                if render.digest(path) != item['sha256']:
                    raise ValueError('Original image changed while composing.')
                with Image.open(path) as image:
                    if image.size != (900, 900):
                        raise ValueError('Original image dimensions changed while composing.')
                    canvas.paste(image.convert('RGB'), (index * 900, 105))
                sources.append(dict(candidate=mode, image_candidate=state['image_candidate'], caption=caption,
                    path=str(path), sha256=item['sha256'], reused_reference=state['reused_reference']))
            target = output / f'{case}_{view}.png'
            canvas.save(target)
            boards.append(dict(output=str(target), output_sha256=render.digest(target),
                input_case=case, view=view, crop=False, resize=False, sources=sources))
    source_list = dict(reference_root=verification['reference_root'], new_root=verification['new_root'],
        referenced_prior_mesh_states=2, newly_replayed_mesh_states=6,
        reused_reference_images=8, newly_rendered_images=24, original_images_total=32,
        source_note='COMBINED: eight frozen late-detail G05 originals linked to prior actual geometry/render PASS; three new modes: 24 new originals. No new baseline mesh.',
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
    print('RENDER_VERIFICATION_PASS: 2 frozen COMBINED states/8 PNGs + 6 new states/24 PNGs',
          '' if args.verify_only else '/ 8 four-column boards', flush=True)


if __name__ == '__main__':
    main()
