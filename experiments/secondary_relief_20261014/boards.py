"""Matched clean-source versus one saved triangle-native secondary-relief comparison."""
from pathlib import Path
import argparse
import importlib.util
import json
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('secondary_relief_comparison_renderer', HERE / 'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def checked_images(receipt, folder, receipt_path, reused):
    records = receipt.get('images')
    if not isinstance(records, list) or len(records) != len(render.VIEWS):
        raise ValueError('Exactly three actual native images required.')
    if {item['view'] for item in records} != set(render.VIEWS):
        raise ValueError('Actual view set differs.')
    images = {}
    for item in records:
        if item['filename'] != item['view'] + '.png':
            raise ValueError('Actual native image filename differs.')
        path = folder / item['filename']
        if render.digest(path) != item['sha256']:
            raise ValueError('Actual native image changed: ' + str(path))
        with Image.open(path) as image:
            if image.size != (900, 900):
                raise ValueError('Actual native image dimensions differ.')
        images[item['view']] = dict(path=str(path), **item, receipt=str(receipt_path),
            receipt_sha256=render.digest(receipt_path), reused_reference=reused)
    return images


def verify(root):
    root = Path(root).resolve()
    info, parent, source = render.source_state(root)
    old_path = render.SOURCE / 'views/receipt.json'
    new_path = root / 'views/receipt.json'
    old_receipt, receipt = render.read_json(old_path), render.read_json(new_path)
    if (Path(old_receipt.get('source_finish_path', '')).resolve() != (render.SOURCE / 'geometry.npz').resolve() or
            old_receipt.get('source_finish_sha256') != render.SOURCE_GEOMETRY_SHA256 or
            old_receipt.get('finish_receipt_sha256') != source['source_finish_receipt_sha256'] or
            old_receipt.get('renderer_code_sha256') != render.CLEAN_RENDER_SHA256 or
            old_receipt.get('preserved_renderer_hashes') != render.helper.code_hashes() or
            old_receipt.get('geometry_processing_in_renderer') is not False or
            old_receipt.get('smooth_shading') is not False):
        raise ValueError('Actual accepted clean source-image provenance mismatch.')
    if (receipt.get('candidate') != 'SECONDARY_RELIEF' or receipt.get('source') != source or
            receipt.get('source_arrays') != {key: info[key] for key in ('xyz_sha256', 'faces_sha256')} or
            receipt.get('code_sha256') != render.code_hashes() or
            receipt.get('operation_record') != render.operation_record(info) or
            receipt.get('vertices') != info['vertices'] or receipt.get('triangles') != info['triangles'] or
            receipt.get('geometry_processing_in_renderer') is not False or receipt.get('smooth_shading') is not False):
        raise ValueError('Actual secondary-relief image/source/code/recipe binding mismatch.')
    render.verify_snapshots(receipt.get('render_source_snapshots'))
    render.require_close(receipt['conditions'], render.base.expected_conditions())
    if old_receipt['conditions'] != receipt['conditions'] or old_receipt['blender_version'] != receipt['blender_version']:
        raise ValueError('Actual clean-source/relief material, lighting, sampling or Blender conditions differ.')
    for view, (position, target, scale) in render.VIEWS.items():
        expected = dict(position=list(position), target=list(target), scale=scale)
        render.require_close(receipt['actual_views'][view], expected, 'new-camera.' + view)
        render.require_close(old_receipt['actual_views'][view], expected, 'accepted-source-camera.' + view)
        render.require_close(receipt['actual_views'][view], old_receipt['actual_views'][view], 'matched-camera.' + view)
    old_images = checked_images(old_receipt, render.SOURCE / 'views', old_path, True)
    images = checked_images(receipt, root / 'views', new_path, False)
    return dict(passed=True, root=str(root), candidate='SECONDARY_RELIEF',
        source_candidate=parent['candidate'], source=source, source_arrays=receipt['source_arrays'],
        states=[dict(label='Accepted clean finish', images=old_images),
                dict(label='Secondary relief', images=images)],
        reused_accepted_clean_images=3, new_saved_relief_images=3, source_images=6,
        conditions=receipt['conditions'], actual_views=receipt['actual_views'],
        Blender_version=receipt['blender_version'], operation_record=render.operation_record(info),
        render_code_sha256=receipt['code_sha256'], render_source_snapshots=receipt['render_source_snapshots'],
        crop=False, resize=False, renderer_geometry_processing=False,
        original_growth_G8=False, source_triangle_indices_unchanged=True,
        scope='Actual accepted clean-source PNGs versus one saved secondary-relief candidate, equal camera, material, lighting, sampling and flat native shading. One low-amplitude analytic theta/height normal displacement; no added CC, voxel or topology. The phase does not track actual fold ridges and does not recover inherited feature memory. Saved provenance and image checks do not certify near-view aesthetic success, self-intersection freedom or fabrication.')


def compose(proof):
    root = Path(proof['root'])
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Earlier matched comparison preserved.')
    output.mkdir()
    title = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 27)
    label = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 23)
    labels = ('\uae30\uc874 \uc815\ub9ac \ud615\uc0c1', '\uc18c\uaddc\ubaa8 \ubd80\uc870 \ucd94\uac00')
    view_labels = dict(front='\uc804\uccb4 \uc815\uba74', body_oblique='\ubab8\uccb4 \uc0ac\uc120', close_oblique='\uadfc\uc811 \uc0ac\uc120')
    boards = []
    for view in render.VIEWS:
        canvas = Image.new('RGB', (1800, 1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), f'SPAN | {view_labels[view]} | \uc18c\uaddc\ubaa8 \ubd80\uc870 \ube44\uad50', font=title, fill='black')
        sources = []
        for column, state in enumerate(proof['states']):
            draw.text((column * 900 + 24, 61), labels[column], font=label, fill='black')
            item = state['images'][view]
            if render.digest(item['path']) != item['sha256']:
                raise ValueError('Actual source image changed during comparison.')
            with Image.open(item['path']) as image:
                if image.size != (900, 900):
                    raise ValueError('Actual source dimensions changed.')
                canvas.paste(image.convert('RGB'), (column * 900, 105))
            sources.append(dict(label=state['label'], **item))
        path = output / ('SPAN_' + view + '.png')
        canvas.save(path)
        boards.append(dict(view=view, output=str(path), sha256=render.digest(path), sources=sources))
    render.verify_snapshots(proof['render_source_snapshots'])
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
    print('SECONDARY_RELIEF_MATCHED_RENDER_PASS: 3 accepted clean + 3 new saved native PNGs', flush=True)


if __name__ == '__main__':
    main()
