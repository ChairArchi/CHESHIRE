"""Embed six receipt-bound native PNG derivatives in the literal viewer.

Images are resized without cropping to 680 square, JPEG quality 82. Original
PNG files and model geometry remain unchanged. No viewer is built on import.
"""
from pathlib import Path
import argparse
import base64
import importlib.util
import io
import json

from PIL import Image

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ordered_viewer_native_render', HERE/'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
OUTPUT = HERE.parents[1]/'output/ordered-primary-folds'
VIEWS = {'front': 'front', 'body': 'body_oblique', 'close': 'close_oblique'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=render.ROOT)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if output.exists():
        raise FileExistsError('Earlier viewer is preserved.')
    binding = render.source_binding()
    expected, candidate = render.candidate_state(root, binding)
    receipt_path = root/'ORDERED_FLAT/review/receipt.json'
    receipt = render.read_json(receipt_path)
    receipt_sha = render.digest(receipt_path)
    if (receipt['state'] != 'ORDERED' or receipt['phase'] != 'review' or
            receipt['saved_geometry'] != expected or receipt['candidate_binding'] != candidate or
            receipt['source_binding'] != binding or receipt['code_sha256'] != render.code_hashes() or
            receipt['geometry_unchanged_by_renderer'] is not True or
            receipt['geometry_processing'] is not False or receipt['all_flat'] is not True or
            receipt['normal_maps'] is not False or receipt['modifiers'] != []):
        raise ValueError('Actual saved candidate/render provenance differs.')
    render.verify_snapshot(receipt['source_snapshot'])
    render.previous.previous.frozen.previous.display_proof(receipt, expected)
    render.require_close(receipt['conditions'], binding['conditions'])
    render.require_close(receipt['actual_views'], binding['actual_views'])
    template_path = HERE/'viewer.fragment.html'
    template = template_path.read_text(encoding='utf8')
    if template.count('__IMAGE_DATA__') != 1 or template.count('__DEFAULT_IMAGE__') != 1:
        raise ValueError('Literal viewer template placeholders differ.')
    source_items = {x['view']: x for x in binding['images']}
    candidate_items = {x['view']: x for x in receipt['images']}
    if set(candidate_items) != set(render.VIEWS):
        raise ValueError('All three actual candidate images are required.')
    output.mkdir(parents=True)
    data, records = {}, []
    for state in ('before', 'after'):
        data[state] = {}
        for label, view in VIEWS.items():
            item = source_items[view] if state == 'before' else candidate_items[view]
            source = Path(item['path']) if state == 'before' else receipt_path.parent/item['filename']
            if render.digest(source) != item['sha256']:
                raise ValueError('Actual native PNG changed: '+str(source))
            render.scaffold.verify_native_png(source)
            with Image.open(source) as image:
                if image.size != (900, 900):
                    raise ValueError('Actual native PNG dimensions differ.')
                derivative = image.convert('RGB').resize((680, 680), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                derivative.save(buffer, format='JPEG', quality=82, optimize=True)
            payload = buffer.getvalue()
            target = output/f'{state}_{label}.jpg'
            target.write_bytes(payload)
            data[state][label] = 'data:image/jpeg;base64,'+base64.b64encode(payload).decode('ascii')
            records.append(dict(state=state, view=view, source_png=str(source),
                source_png_sha256=item['sha256'], derivative_jpeg=str(target),
                derivative_jpeg_sha256=render.digest(target), source_size=[900, 900],
                derivative_size=[680, 680], crop=False, jpeg_quality=82,
                actual_camera=receipt['actual_views'][view]))
    fragment = template.replace('__IMAGE_DATA__', json.dumps(data, ensure_ascii=False))
    fragment = fragment.replace('__DEFAULT_IMAGE__', data['after']['body'])
    encoded = fragment.encode('utf8')
    if len(encoded) >= 1000000:
        raise ValueError('Inline fragment exceeds 1 MB.')
    if any(x in fragment for x in ('__IMAGE_DATA__', '__DEFAULT_IMAGE__', '<html', '<body', '<!doctype')):
        raise ValueError('Inline fragment contract differs.')
    path = output/'ordered-primary-folds.html'
    path.write_bytes(encoded)
    proof = dict(comparison='Latest actual NESTED02 versus actual ORDERED',
        native_geometry_before=binding['source_native_path'],
        native_geometry_before_sha256=binding['source_native_geometry_sha256'],
        native_geometry_after=expected['geometry'], native_geometry_after_sha256=expected['geometry_sha256'],
        candidate_generation_receipt=candidate,
        candidate_render_receipt=str(receipt_path), candidate_render_receipt_sha256=receipt_sha,
        baseline_render_receipt=binding['source_render_receipt'],
        baseline_render_receipt_sha256=binding['source_render_receipt_sha256'],
        same_actual_cameras=True, same_actual_conditions=True,
        all_flat=True, geometry_processing=False, normal_maps=False, images=records,
        viewer_path=str(path), viewer_sha256=render.digest(path), viewer_bytes=len(encoded),
        default_state='after', default_view='body',
        template=str(template_path), template_sha256=render.digest(template_path),
        builder=str(Path(__file__).resolve()), builder_sha256=render.digest(__file__))
    render.write(output/'SOURCE_IMAGES.json', proof)
    print(json.dumps(dict(viewer=str(path), bytes=len(encoded), source_images=len(records)), indent=2))


if __name__ == '__main__':
    main()
