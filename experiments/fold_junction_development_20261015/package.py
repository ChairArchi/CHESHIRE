"""Export exact saved triangles and a portable NESTED02 image comparison.

The full PLY retains the original float64 coordinates, axes and units. Detail
is an unchanged triangle subset with an open cut boundary. No mesh changes.
The HTML viewer uses local PNGs and has no server or external dependencies.
"""
from pathlib import Path
import argparse
import copy
import html
import importlib.util
import json
import shutil
import time

import numpy as np

HERE = Path(__file__).resolve().parent
RENDERER = HERE / 'render.py'
spec = importlib.util.spec_from_file_location('fold_junction_package_render', RENDERER)
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
digest, read_json = render.digest, render.read_json
TARGET = np.array([-.8127592552124007, .42607142838364565, 6.369917540048999])
RADIUS = .28
FACE = np.dtype([('count', 'u1'), ('indices', '<i4', (3,))])
BASE_EXPORT = Path('E:/CHESHIRE_DATA/exports/20261014/COLUMN_PARENT_NESTED')


def write_json(path, value):
    with open(path, 'x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def write_ply(path, xyz, faces, source_sha):
    """Exact binary PLY with complete coordinate/connectivity readback.

    Preserves the established parent_nested_folds export layout while using
    a variant-neutral comment and arbitrary actual native mesh counts.
    """
    if (len(xyz) > np.iinfo(np.int32).max or faces.min() < 0 or
            faces.max() >= len(xyz) or faces.max() > np.iinfo(np.int32).max):
        raise ValueError('PLY signed int32 face indexing is invalid.')
    header = ('ply\nformat binary_little_endian 1.0\n'
        'comment CHESHIRE receipt-bound fold-junction development\n'
        'comment Source geometry SHA256 ' + source_sha + '\n'
        'comment Original coordinates and units unchanged\n'
        f'element vertex {len(xyz)}\nproperty double x\nproperty double y\nproperty double z\n'
        f'element face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n').encode('ascii')
    with open(path, 'xb') as stream:
        stream.write(header)
        for start in range(0, len(xyz), 262144):
            np.ascontiguousarray(xyz[start:start + 262144], dtype='<f8').tofile(stream)
        for start in range(0, len(faces), 262144):
            block = faces[start:start + 262144]
            packed = np.empty(len(block), FACE)
            packed['count'], packed['indices'] = 3, block
            packed.tofile(stream)
    expected_bytes = len(header) + len(xyz) * 24 + len(faces) * 13
    if path.stat().st_size != expected_bytes:
        raise ValueError('PLY byte length differs.')
    with open(path, 'rb') as stream:
        if stream.read(len(header)) != header:
            raise ValueError('PLY header differs.')
        for start in range(0, len(xyz), 262144):
            source = xyz[start:start + 262144]
            actual = np.fromfile(stream, dtype='<f8', count=source.size).reshape(source.shape)
            if not np.array_equal(actual, source):
                raise ValueError('PLY coordinate roundtrip differs.')
        for start in range(0, len(faces), 262144):
            source = faces[start:start + 262144]
            actual = np.fromfile(stream, dtype=FACE, count=len(source))
            if not np.all(actual['count'] == 3) or not np.array_equal(actual['indices'], source):
                raise ValueError('PLY triangle roundtrip differs.')
        if stream.read(1):
            raise ValueError('Unexpected PLY trailing bytes.')
    return dict(path=str(path), vertices=len(xyz), triangles=len(faces), bytes=expected_bytes,
        sha256=digest(path), exact_coordinate_and_triangle_roundtrip=True,
        coordinates='binary float64; unchanged source axes/model units',
        faces='uchar3 + signed int32 indices')


def checked_render(root, name, phase, expected, candidate, binding):
    render.checked_name(phase)
    receipt_path = root / (name + '_FLAT') / phase / 'receipt.json'
    receipt = read_json(receipt_path)
    if (receipt['state'] != name or receipt['phase'] != phase or
            receipt['saved_geometry'] != expected or receipt['candidate_binding'] != candidate or
            receipt['source_binding'] != binding or receipt['code_sha256'] != render.code_hashes() or
            receipt['geometry_unchanged_by_renderer'] is not True or receipt['all_flat'] is not True or
            receipt['geometry_processing'] is not False or receipt['normal_maps'] is not False or
            receipt['modifiers'] != []):
        raise ValueError('Actual saved-geometry flat render provenance differs.')
    render.verify_snapshot(receipt['source_snapshot'])
    expected_conditions = copy.deepcopy(binding['conditions'])
    expected_conditions['resolution'] = receipt['conditions']['resolution']
    render.require_close(receipt['conditions'], expected_conditions)
    if receipt['version'] != binding['Blender_version']:
        raise ValueError('Actual source/candidate Blender versions differ.')
    if set(receipt['actual_views']) != {item['view'] for item in receipt['images']}:
        raise ValueError('Actual rendered camera/image inventory differs.')
    if len(receipt['images']) != len(receipt['actual_views']):
        raise ValueError('Actual rendered images must have unique views.')
    images = []
    baseline_images = {item['view']: item for item in binding['images']}
    for item in receipt['images']:
        view = item['view']
        if view not in render.VIEWS or item['filename'] != view + '.png':
            raise ValueError('Unknown or nonlocal rendered image.')
        render.require_close(receipt['actual_views'][view], binding['actual_views'][view])
        image = receipt_path.parent / item['filename']
        if digest(image) != item['sha256']:
            raise ValueError('Actual candidate PNG changed.')
        reference = baseline_images[view]
        if digest(reference['path']) != reference['sha256']:
            raise ValueError('Actual NESTED02 reference PNG changed.')
        images.append(dict(view=view, candidate=str(image), candidate_sha256=item['sha256'],
            reference=reference['path'], reference_sha256=reference['sha256']))
    return receipt, dict(path=str(receipt_path), sha256=digest(receipt_path)), images


def write_viewer(output, name, images, expected, matched, full, detail):
    image_dir = output / 'images'
    image_dir.mkdir()
    local_images = []
    for record in images:
        item = dict(view=record['view'])
        for side in ('reference', 'candidate'):
            target = image_dir / (record['view'] + '_' + side + '.png')
            shutil.copyfile(record[side], target)
            if digest(target) != record[side + '_sha256']:
                raise ValueError('Packaged actual PNG differs.')
            item[side] = 'images/' + target.name
        local_images.append(item)
    models = [('개발 모델 · 전체 PLY', Path(full['path']).name),
              ('개발 모델 · 근접 PLY', Path(detail['path']).name)]
    for label, filename in [('NESTED02 · 전체 PLY', 'CHESHIRE_COLUMN_G7_PARENT_NESTED_FULL.ply'),
                             ('NESTED02 · 근접 PLY', 'CHESHIRE_COLUMN_G7_PARENT_NESTED_DETAIL.ply')]:
        path = BASE_EXPORT / filename
        if path.is_file():
            models.append((label, path.resolve().as_uri()))
    links = '\n'.join('<a href="' + html.escape(path, quote=True) + '">' + html.escape(label) + '</a>'
                      for label, path in models)
    options = ''.join('<option value="' + html.escape(record['view'], quote=True) + '">' +
                      html.escape(record['view']) + '</option>' for record in local_images)
    note = ('카메라 · 재질 · 조명 · 샘플 · 900px · flat shading 동일' if matched else
            '미리보기: 카메라 · 재질 · 조명 · 샘플 · flat shading 동일, 이미지 해상도 차이 있음')
    title = 'CHESHIRE · NESTED02 / ' + name
    payload = json.dumps(local_images, ensure_ascii=False).replace('</', '<\\/')
    document = '''<!doctype html>
<html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title><style>
*{box-sizing:border-box}body{margin:0;background:#10151b;color:#eef1f5;font:15px/1.5 system-ui,sans-serif}
main{max-width:1200px;margin:auto;padding:26px}h1{font-size:23px;margin:0 0 5px}p{color:#b9c5d1;margin:8px 0 18px}
.controls{display:flex;flex-wrap:wrap;gap:16px;align-items:center;margin:18px 0}select{background:#202b37;color:#fff;border:1px solid #506173;padding:9px;border-radius:7px}input{width:250px;accent-color:#a5d8dc}
.stage{position:relative;width:min(100%,900px);aspect-ratio:1;margin:auto;background:#20272d;overflow:hidden}
.stage img{position:absolute;width:100%;height:100%;object-fit:contain;inset:0}.candidate{clip-path:inset(0 0 0 50%)}
.line{position:absolute;left:50%;top:0;bottom:0;width:2px;background:#a5d8dc;pointer-events:none}.badges{position:absolute;inset:14px 14px auto;display:flex;justify-content:space-between;pointer-events:none}.badges span{background:#10151bdd;padding:5px 9px;border-radius:5px;font-size:12px}.links{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}a{color:#a5d8dc;background:#202b37;padding:9px 12px;border-radius:6px;text-decoration:none}a:hover{text-decoration:underline}small{display:block;color:#9cabb9;margin-top:16px}
</style><main><h1>__TITLE__</h1><p>__NOTE__</p>
<div class="controls"><label>시점 <select id="view">__OPTIONS__</select></label>
<label>비교 경계 <input id="slider" type="range" min="0" max="100" value="50" aria-label="NESTED02와 개발 모델 비교 경계"></label></div>
<div class="stage"><img id="reference" alt="기존 NESTED02"><img id="candidate" class="candidate" alt="개발 모델"><div id="line" class="line"></div><div class="badges"><span>NESTED02</span><span>__NAME__</span></div></div>
<div class="links">__LINKS__</div><small>개발 모델: __VERTICES__ vertices / __TRIANGLES__ triangles. PLY는 원래 좌표와 단위를 보존합니다. 근접 PLY의 절단 경계는 열려 있습니다.</small>
<script>const images=__IMAGES__;const selector=document.getElementById('view');const slider=document.getElementById('slider');const candidate=document.getElementById('candidate');function updateView(){const image=images.find(item=>item.view===selector.value);document.getElementById('reference').src=image.reference;candidate.src=image.candidate;}function updateBoundary(){candidate.style.clipPath='inset(0 0 0 '+slider.value+'%)';document.getElementById('line').style.left=slider.value+'%';}selector.addEventListener('change',updateView);slider.addEventListener('input',updateBoundary);updateView();updateBoundary();</script></main></html>'''
    replacements = {'__TITLE__': html.escape(title), '__NAME__': html.escape(name),
        '__NOTE__': html.escape(note), '__OPTIONS__': options, '__LINKS__': links,
        '__VERTICES__': f"{expected['vertices']:,}", '__TRIANGLES__': f"{expected['triangles']:,}",
        '__IMAGES__': payload}
    for key, value in replacements.items():
        document = document.replace(key, value)
    viewer = output / 'comparison.html'
    with open(viewer, 'x', encoding='utf8') as stream:
        stream.write(document)
    return dict(path=str(viewer), sha256=digest(viewer), images=local_images,
                local_dependencies_only=True, baseline_model_links_are_external=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=render.ROOT)
    parser.add_argument('--variant', default='DEVELOPED')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--render-phase', default='review')
    parser.add_argument('--checkpoint', default=None)
    parser.add_argument('--detail-radius', type=float, default=RADIUS)
    args = parser.parse_args()
    started = time.perf_counter()
    root, output = args.root.resolve(), args.output.resolve()
    name = render.checked_name(args.variant)
    if output.exists():
        raise FileExistsError('Earlier exported package is preserved: ' + str(output))
    if not np.isfinite(args.detail_radius) or args.detail_radius <= 0:
        parser.error('Detail radius must be finite and positive.')
    binding = render.source_binding()
    expected, candidate = render.candidate_state(root, name, binding)
    rendered, render_receipt, images = checked_render(root, name, args.render_phase, expected, candidate, binding)
    xyz, faces = render.load_arrays(expected)
    code = dict(package=digest(__file__), renderer=render.code_hashes())
    chosen = []
    for start in range(0, len(faces), 131072):
        block = faces[start:start + 131072]
        centers = xyz[block].mean(axis=1)
        chosen.append(start + np.flatnonzero(np.sum((centers - TARGET) ** 2, axis=1) <= args.detail_radius ** 2))
    face_ids = np.concatenate(chosen)
    if not len(face_ids):
        raise ValueError('The actual stored near-detail triangle subset is empty.')
    vertex_ids, inverse = np.unique(faces[face_ids].ravel(), return_inverse=True)
    output.mkdir(parents=True)
    for path in (Path(__file__), RENDERER):
        shutil.copyfile(path, output / ('SOURCE_SNAPSHOT_' + path.name))
    shutil.copyfile(candidate['receipt'], output / 'SOURCE_GENERATION_RECEIPT.json')
    shutil.copyfile(render_receipt['path'], output / 'SOURCE_RENDER_RECEIPT.json')
    prefix = 'CHESHIRE_COLUMN_' + name
    print('EXPORT exact full saved model ' + name, flush=True)
    full = write_ply(output / (prefix + '_FULL.ply'), xyz, faces, expected['geometry_sha256'])
    print('EXPORT exact saved close-detail subset ' + name, flush=True)
    detail = write_ply(output / (prefix + '_DETAIL.ply'), xyz[vertex_ids], inverse.reshape(-1, 3),
                       expected['geometry_sha256'])
    detail.update(scope='Exact original triangle subset; open cut boundary, no caps or new surface.',
                  selection='Triangle centroids within radius of the preserved macro-camera target.',
                  target=TARGET.tolist(), radius=args.detail_radius)
    ids_path = output / 'DETAIL_SOURCE_IDS.npz'
    np.savez_compressed(ids_path, source_vertex_ids=vertex_ids, source_face_ids=face_ids)
    viewer = write_viewer(output, name, images, expected,
                          rendered['resolution_matched_to_source'], full, detail)
    if (render.source_binding() != binding or render.candidate_state(root, name, binding) != (expected, candidate) or
            checked_render(root, name, args.render_phase, expected, candidate, binding) !=
            (rendered, render_receipt, images) or
            dict(package=digest(__file__), renderer=render.code_hashes()) != code):
        raise ValueError('Actual geometry, receipts, PNGs or executed packaging code changed.')
    manifest = dict(date='2026-10-15', timezone='Asia/Seoul', source_variant=name,
        source_geometry=expected, generation_receipt=candidate, render_receipt=render_receipt,
        source_binding=binding, executed_code_sha256=code, checkpoint=args.checkpoint,
        full=full, detail=detail, detail_source_ids=dict(path=str(ids_path), sha256=digest(ids_path)),
        comparison=viewer, compared_pngs=images,
        resolution_matched_to_source=rendered['resolution_matched_to_source'],
        native_connectivity_matched_to_source=rendered['native_connectivity_matched_to_source'],
        source_geometry_modified=False, simplification=False,
        units='Unchanged original axes and model units; no scale conversion.',
        seconds=time.perf_counter() - started)
    write_json(output / 'MANIFEST.json', manifest)
    with open(output / 'README.txt', 'x', encoding='utf8') as stream:
        stream.write('CHESHIRE fold-junction development / 2026-10-15\n\n'
            'comparison.html: local, offline NESTED02 / saved-candidate image comparison.\n'
            'FULL PLY: complete original native triangles and float64 coordinates.\n'
            'DETAIL PLY: exact original triangle subset; open cut boundary, no caps.\n'
            'Original axes and model units retained; no simplification or scale conversion.\n'
            'Reference PLY links point to the preserved E: baseline export.\n'
            'See MANIFEST.json for source hashes, receipts and complete PLY roundtrip checks.\n')
    print(json.dumps(dict(full=full, detail=detail, viewer=viewer['path'], seconds=manifest['seconds'])), flush=True)


if __name__ == '__main__':
    main()
