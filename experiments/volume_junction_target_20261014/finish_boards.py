"""Matched original versus actual saved G7-derived volume-finish images."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('volume_finish_source_image_checks', HERE/'boards.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
render, checks = helper.render, helper.checks
digest = render.digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    folder = args.root.resolve()/'volume_finish_v2'
    output = folder/'images'
    if output.exists():
        raise FileExistsError('Earlier comparison preserved.')
    info = json.loads((folder/'FINISH_RECEIPT.json').read_text(encoding='utf-8'))
    receipt = json.loads((folder/'views/receipt.json').read_text(encoding='utf-8'))
    if digest(folder/'geometry.npz') != info['geometry_sha256'] or receipt['source_finish_sha256'] != info['geometry_sha256'] or receipt['finish_receipt_sha256'] != digest(folder/'FINISH_RECEIPT.json'):
        raise ValueError('Actual finish-render-source binding mismatch.')
    parent_info, parent_source = render.parent_state()
    old_images, old_receipt, old_views = checks.checked_images(parent_info, parent_source,
        render.PARENT/'views/receipt.json', render.prior.code_hashes())
    if old_receipt['conditions'] != receipt['conditions'] or old_receipt['version'] != receipt['blender_version']:
        raise ValueError('Actual comparison render/material conditions differ.')
    for view in render.VIEWS:
        expected = {key:old_views[view][key] for key in ['position','target','scale']}
        render.require_close(receipt['actual_views'][view], expected, 'matched-camera.'+view)
    if digest(HERE/'finish_render_v2.py') != receipt['renderer_code_sha256']:
        raise ValueError('Actual frozen finish renderer changed.')
    old = {item['view']:item for item in old_images}
    new = {}
    for item in receipt['images']:
        path = folder/'views'/item['filename']
        if digest(path) != item['sha256']:
            raise ValueError('Actual finish image changed.')
        new[item['view']] = dict(path=str(path), **item)
    output.mkdir()
    title = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 27)
    label = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 23)
    boards = []
    for view in render.VIEWS:
        canvas = Image.new('RGB', (1800,1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24,12), 'SPAN | '+view+' | G7-derived volumetric finish', font=title, fill='black')
        sources = []
        for column, (name, item) in enumerate([('Original G7', old[view]), ('Volumetric finish | not growth G8', new[view])]):
            draw.text((24+column*900,61), name, font=label, fill='black')
            with Image.open(item['path']) as image:
                if image.size != (900,900):
                    raise ValueError('Actual image dimensions differ.')
                canvas.paste(image.convert('RGB'), (column*900,105))
            sources.append(dict(label=name, **item))
        path = output/('SPAN_'+view+'.png')
        canvas.save(path)
        boards.append(dict(view=view, output=str(path), sha256=digest(path), sources=sources))
    result = dict(passed=True, boards=boards, reused_original_images=3, new_actual_finish_images=3,
        conditions=receipt['conditions'], actual_views=receipt['actual_views'],
        source_finish_geometry_sha256=info['geometry_sha256'],
        original_source_generation=7, candidate='G7_DERIVED_VOLUME_FINISH',
        original_face_ID_ancestry_retained=False, original_growth_G8=False,
        crop=False, resize=False, renderer_geometry_processing=False,
        actual_recipe=info['recipe'], boards_code_sha256=digest(__file__),
        scope='Actual original and saved finish PNGs, equal cameras, material, lighting, sampling and flat shading. Geometry changed globally by remesh; extra smoothing is marked-region weighted. One CC pass finishes the new topology. No aesthetic or fabrication certification.')
    for path in [folder/'RENDER_VERIFICATION.json', output/'SOURCE_LIST.json']:
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    shutil.copyfile(__file__, folder/'source_snapshot_render'/'finish_boards.py')
    print('FINISH_MATCHED_COMPARISON_PASS', flush=True)


if __name__ == '__main__':
    main()
