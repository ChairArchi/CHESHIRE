"""Verify and compose accepted design versus actual flow-aligned finish."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('flow_finish_board_renderer', HERE / 'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def verify(root):
    root = Path(root).resolve()
    binding, current, candidate = render.saved_state(root)
    expected = candidate['variant']
    receipt_path = root / 'FLOW_FLAT/views/receipt.json'
    receipt = render.read_json(receipt_path)
    hashes = render.code_hashes()
    if (receipt.get('state') != 'FLOW_FLAT' or receipt.get('source_binding') != binding or
            receipt.get('candidate_binding') != candidate or receipt.get('comparison_reference') != current or
            receipt.get('saved_geometry') != expected or
            Path(receipt.get('geometry_path', '')).resolve() != Path(expected['geometry']).resolve() or
            receipt.get('code_sha256') != hashes or receipt.get('geometry_unchanged_in_renderer') is not True or
            receipt.get('geometry_processing') is not False or receipt.get('geometry_smoothing') is not False or
            receipt.get('shading') != 'ALL_FLAT_NATIVE_TRIANGLES' or receipt.get('smooth_shading') is not False or
            receipt.get('smooth_polygons') != 0 or receipt.get('normal_maps') is not False or
            receipt.get('modifiers') != [] or receipt.get('remesh') is not False or
            receipt.get('Boolean_fusion') is not False or receipt.get('ornaments_added') is not False or
            receipt.get('selective_mask_dependency') is not False or receipt.get('source_growth_generation') != 7 or
            receipt.get('new_source_growth_G8') is not False or
            receipt.get('generator_validation_evidence') != expected.get('validation')):
        raise ValueError('Actual FLOW render provenance differs.')
    render.verify_snapshot(receipt['render_source_snapshot'])
    counts, readback = render.previous.display_proof(receipt, expected)
    render.require_close(receipt['conditions'], binding['reference_conditions'])
    render.require_close(receipt['conditions'], render.base.expected_conditions())
    render.require_close(receipt['views'], binding['views'])
    if receipt['version'] != binding['reference_Blender_version']:
        raise ValueError('Source/candidate Blender versions differ.')
    images = render.previous.image_records(receipt, receipt_path, binding, False)
    flow = dict(state='FLOW_FLAT', saved_geometry=expected, images=images,
                geometry_counts=counts, display_readback=readback)
    return dict(passed=True, root=str(root), source_binding=binding, candidate_binding=candidate,
        states=[current, flow], actual_views=binding['actual_reference_views'], conditions=binding['reference_conditions'],
        reused_accepted_design_images=4, new_flow_images=4, source_images=8, comparison_columns=2,
        each_body_saved_coordinate_index_readback_verified=True, all_flat_flags_verified_per_body=True,
        geometry_unchanged_by_renderer=True, native_topology_equal_in_comparison=False,
        generator_validation_evidence=expected.get('validation'),
        generator_validation_scope='Carried from hash-bound generator receipt; not independently rerun by image verifier.',
        aesthetic_success_certified=False, global_collision_freedom_certified=False,
        crop=False, resize=False, modifiers=[], normal_maps=False, renderer_geometry_processing=False,
        selective_mask_dependency=False, source_growth_generation=7, new_source_growth_G8=False,
        render_code_sha256=hashes, boards_code_sha256=render.digest(__file__),
        scope='One matched-camera/all-flat comparison: accepted REFINED versus new FLOW saved body. Native topology differs between the bodies. Saved coordinate/index readbacks and source PNG hashes are verified independently per body. Bare control source is not substituted for accepted detailed design. No geometry processing or synthesized image.')


def snapshot_source(root):
    source = Path(__file__).resolve()
    relative = Path('experiments') / HERE.name / source.name
    target = root / 'source_snapshot_boards' / relative
    checksum = render.digest(source)
    if target.exists():
        if render.digest(target) != checksum:
            raise ValueError('Earlier boards snapshot differs.')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    record = dict(source=str(source), relative_path=relative.as_posix(), snapshot=str(target), sha256=checksum)
    if any(render.digest(record[key]) != checksum for key in ('source', 'snapshot')):
        raise ValueError('Actual boards snapshot differs.')
    return record


def compose(proof):
    root = Path(proof['root'])
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Earlier actual comparison preserved.')
    snapshot = snapshot_source(root)
    output.mkdir()
    title = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 27)
    label = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 23)
    labels = ('Accepted detailed design | all-flat', 'Flow-aligned fold finish | all-flat')
    boards = []
    for view in proof['actual_views']:
        canvas = Image.new('RGB', (1800, 1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), 'SPAN | ' + view + ' | accepted design / flow-aligned finish', font=title, fill='black')
        sources = []
        for column, state in enumerate(proof['states']):
            draw.text((column * 900 + 24, 61), labels[column], font=label, fill='black')
            item = next(image for image in state['images'] if image['view'] == view)
            if render.digest(item['path']) != item['sha256']:
                raise ValueError('Actual PNG changed during composition.')
            with Image.open(item['path']) as image:
                if image.size != (900, 900) or image.format != 'PNG':
                    raise ValueError('Actual 900-square PNG required.')
                canvas.paste(image.convert('RGB'), (column * 900, 105))
            sources.append(dict(state=state['state'], **item))
        path = output / ('SPAN_' + view + '.png')
        canvas.save(path)
        boards.append(dict(view=view, output=str(path), sha256=render.digest(path), sources=sources))
    if any(render.digest(snapshot[key]) != snapshot['sha256'] for key in ('source', 'snapshot')):
        raise ValueError('Boards source changed during composition.')
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
    print('FLOW_FOLD_FINISH_MATCHED_RENDER_PASS: 4 accepted source + 4 actual new PNGs', flush=True)


if __name__ == '__main__':
    main()
