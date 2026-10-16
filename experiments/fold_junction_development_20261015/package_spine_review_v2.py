"""Export a completed, internally reviewed native spine candidate exactly.

Requires actual close/front/body receipts from render_spine_review_v2.py. The
preserved PLY writer independently reads back every float64 coordinate and
triangle. Baseline PNGs are reused, not rerendered. No geometry is modified.
"""
from pathlib import Path
import argparse
import importlib.util
import shutil
import time

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
REVIEW_PATH = HERE/'render_spine_review_v2.py'
REVIEW_SHA = 'a4fc6b0e256c03efe5754f56bef2ed24cf1bf87a926293925b8d2f76216b38ea'
PLY_PATH = HERE/'package.py'
PLY_SHA = '4ada4bcb1a772ffccec3f0e5281b8e4cb067695e8ac3213060dbf94d95f97321'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


review = module('spine_package_actual_review', REVIEW_PATH)
preserved = module('spine_package_frozen_PLY', PLY_PATH)
render, digest = review.render, review.digest


def code_hashes():
    if digest(REVIEW_PATH) != REVIEW_SHA or digest(PLY_PATH) != PLY_SHA:
        raise ValueError('Frozen staged renderer or exact PLY writer changed.')
    return dict(package_spine_review=digest(__file__), renderer=review.code_hashes(),
                preserved_PLY_sha256=PLY_SHA)


def checked_review(root, name):
    root, name = Path(root).resolve(), render.checked_name(name)
    binding = render.source_binding()
    expected, candidate = review.candidate_state(root, name, binding)
    path = root/(name+'_REVIEW')/'REVIEW_RECEIPT.json'
    result = render.read_json(path)
    if (result['kind'] != 'ACTUAL_NATIVE_SPINE_GATED_REVIEW_WITH_REUSED_CONTROL' or
            result['state'] != name or result['status'] != 'context_rendered_pending_final_visual_review' or
            result['saved_geometry'] != expected or result['candidate_binding'] != candidate or
            result['source_binding'] != binding or result['code_sha256'] != review.code_hashes() or
            result['version'] != binding['Blender_version'] or
            result['native_candidate_loaded_once'] is not True or result['shared_native_object'] is not True or
            result['baseline_rerendered'] is not False or result['all_flat'] is not True or
            result['same_native_geometry_for_close_and_context'] is not True or
            result['geometry_processing'] is not False or result['normal_maps'] is not False or
            result['modifiers'] != [] or result['mesh_edges'] != 0 or set(result['stages']) != {'close','context'}):
        raise ValueError('Completed actual native close/context review provenance differs.')
    snapshots = result['source_snapshots']
    sources = {'render_spine_review_v2.py':REVIEW_PATH, 'fast_render.py':review.FAST_PATH,
               'render.py':review.fast.PRESERVED}
    if set(snapshots) != set(sources):
        raise ValueError('All actual executed spine renderer snapshots are required.')
    for filename, source in sources.items():
        record = snapshots[filename]
        render.verify_snapshot(record)
        if Path(record['source']).resolve() != source.resolve() or record['sha256'] != digest(source):
            raise ValueError('Executed renderer and snapshot binding differs.')
    images, stages = [], {}
    for stage_name, views in [('close', {'close_oblique'}), ('context', {'front','body_oblique'})]:
        stage_path = path.parent/stage_name/'receipt.json'
        reference = result['stages'][stage_name]
        if Path(reference['receipt']).resolve() != stage_path.resolve() or digest(stage_path) != reference['receipt_sha256']:
            raise ValueError('Actual close/context receipt changed.')
        stage = render.read_json(stage_path)
        if (stage['kind'] != 'ACTUAL_SAVED_NATIVE_SPINE_REVIEW_STAGE' or stage['state'] != name or
                stage['phase'] != stage_name or stage['saved_geometry'] != expected or
                stage['candidate_binding'] != candidate or stage['source_binding'] != binding or
                stage['code_sha256'] != review.code_hashes() or stage['source_snapshots'] != snapshots or
                stage['source_snapshot'] != snapshots['render_spine_review_v2.py'] or
                stage['version'] != binding['Blender_version'] or stage['baseline_rerendered'] is not False or
                stage['geometry_unchanged_by_renderer'] is not True or stage['all_flat'] is not True or
                stage['geometry_processing'] is not False or stage['normal_maps'] is not False or
                stage['modifiers'] != [] or stage['mesh_edges'] != 0 or
                stage['resolution_matched_to_source'] is not True or
                stage['native_connectivity_matched_to_source'] is not True or
                set(stage['actual_views']) != views or len(stage['images']) != len(views) or
                {item['view'] for item in stage['images']} != views):
            raise ValueError('Actual staged saved-geometry flat render proof differs.')
        counts, display = stage['geometry_counts'], stage['display_readback']
        if (counts['vertices'] != expected['vertices'] or counts['triangles'] != expected['triangles'] or
                counts['source_arrays'] != {key:expected[key] for key in ('xyz_sha256','faces_sha256')} or
                display['geometry'] != counts['expected_display_arrays'] or
                display['polygons'] != expected['triangles'] or display['smooth_polygons'] != 0 or
                display['all_use_smooth'] is not False or display['geometry_unchanged'] is not True or
                display['modifiers'] != [] or display['custom_normal_map'] is not False):
            raise ValueError('Complete native/display/flat-shading readbacks differ.')
        render.require_close(stage['conditions'], binding['conditions'])
        controls = {item['view']:item for item in binding['images']}
        if stage['reused_control_images'] != [item for item in binding['images'] if item['view'] in views]:
            raise ValueError('Exact reused source frames/receipts differ.')
        for item in stage['images']:
            view = item['view']
            png = stage_path.parent/(view+'.png')
            if (item['filename'] != png.name or digest(png) != item['sha256'] or
                    Path(reference['images'][view]).resolve() != png.resolve()):
                raise ValueError('Actual candidate PNG binding differs.')
            render.require_close(stage['actual_views'][view], binding['actual_views'][view])
            with Image.open(png) as opened:
                if opened.format != 'PNG' or opened.size != (900,900):
                    raise ValueError('Original actual 900px PNG required.')
                opened.verify()
            control = controls[view]
            images.append(dict(view=view, candidate=str(png), candidate_sha256=item['sha256'],
                               reference=control['path'], reference_sha256=control['sha256']))
        stages[stage_name] = dict(path=str(stage_path), sha256=digest(stage_path))
    decision = result['internal_decision']
    decision_path = Path(decision['path'])
    if (digest(decision_path) != decision['sha256'] or
            review.decision_record(decision_path, expected, candidate,
                Path(stages['close']['path'])) != decision['value'] or
            decision['value']['action'] != 'render_context'):
        raise ValueError('Exact internal close-to-context decision changed.')
    return dict(expected=expected, candidate=candidate, binding=binding, rendered=result,
        review_receipt=dict(path=str(path), sha256=digest(path)), stages=stages,
        images=images, internal_decision=decision)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--variant', default='SPINE')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--status', choices=('research_probe','accepted'), default='research_probe')
    parser.add_argument('--detail-radius', type=float, default=.65)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    name = render.checked_name(args.variant)
    if output.exists():
        raise FileExistsError('Earlier actual spine export is preserved.')
    if not np.isfinite(args.detail_radius) or args.detail_radius <= 0:
        parser.error('Finite positive actual detail selection radius required.')
    started, hashes = time.perf_counter(), code_hashes()
    state = checked_review(root, name)
    expected, candidate, binding = state['expected'], state['candidate'], state['binding']
    xyz, faces = render.load_arrays(expected)
    target = np.asarray(binding['actual_views']['close_oblique']['target'], np.float64)
    chosen = []
    for start in range(0, len(faces), 131072):
        block = faces[start:start+131072]
        centers = xyz[block].mean(axis=1)
        chosen.append(start+np.flatnonzero(np.sum((centers-target)**2,axis=1) <= args.detail_radius**2))
    face_ids = np.concatenate(chosen)
    if not len(face_ids):
        raise ValueError('Exact native close-region triangle subset is empty.')
    vertex_ids, inverse = np.unique(faces[face_ids].ravel(), return_inverse=True)
    output.mkdir(parents=True)
    print('SPINE_EXPORT exact full saved native model', flush=True)
    full = preserved.write_ply(output/('CHESHIRE_'+name+'_FULL.ply'), xyz, faces, expected['geometry_sha256'])
    detail = preserved.write_ply(output/('CHESHIRE_'+name+'_DETAIL.ply'), xyz[vertex_ids],
                                inverse.reshape(-1,3), expected['geometry_sha256'])
    detail.update(scope='Exact saved native triangle subset; open boundary, no caps.',
                  target=target.tolist(), radius=args.detail_radius)
    ids_path = output/'DETAIL_SOURCE_IDS.npz'
    np.savez_compressed(ids_path, source_vertex_ids=vertex_ids, source_face_ids=face_ids)
    viewer = preserved.write_viewer(output, name, state['images'], expected, True, full, detail)
    viewer_path = Path(viewer['path'])
    document = viewer_path.read_text(encoding='utf-8')
    status_note = ('내부 검수 후 내보낸 연구 후보입니다. 최종 미적 채택을 뜻하지 않습니다.'
                   if args.status == 'research_probe' else '검수 후 채택된 실제 메시입니다.')
    document = document.replace('</h1>', '</h1><p>'+status_note+'</p>', 1)
    viewer_path.write_text(document, encoding='utf-8')
    viewer['sha256'] = digest(viewer_path)
    copies = {}
    sources = dict(generation=Path(candidate['receipt']), review=Path(state['review_receipt']['path']),
                   close=Path(state['stages']['close']['path']), context=Path(state['stages']['context']['path']),
                   internal_decision=Path(state['internal_decision']['path']))
    sources.update({path.name:path for path in (Path(__file__).resolve(), REVIEW_PATH, PLY_PATH)})
    sources.update({'executed_'+name:Path(record['snapshot']) for name,record in state['rendered']['source_snapshots'].items()})
    for label, source in sources.items():
        destination = output/('SOURCE_'+label+source.suffix if not label.endswith(source.suffix) else 'SOURCE_'+label)
        shutil.copyfile(source, destination)
        if digest(source) != digest(destination):
            raise ValueError('Exact exported provenance copy differs.')
        copies[label] = dict(source=str(source), path=str(destination), sha256=digest(destination))
    if checked_review(root, name) != state or code_hashes() != hashes:
        raise ValueError('Actual source/geometry/PNG/decision/executed code changed during export.')
    manifest = dict(kind='ACTUAL_SAVED_NATIVE_SPINE_PACKAGE', status=args.status,
        research_probe_not_adopted=args.status=='research_probe', source_variant=name,
        source_geometry=expected, generation_receipt=candidate, review_receipt=state['review_receipt'],
        stage_receipts=state['stages'], internal_context_decision=state['internal_decision'],
        source_binding=binding, executed_code_sha256=hashes, exact_provenance_copies=copies,
        full=full, detail=detail, detail_source_ids=dict(path=str(ids_path), sha256=digest(ids_path)),
        comparison=viewer, compared_pngs=state['images'], source_geometry_modified=False,
        simplification=False, source_geometry_SHA_comment='Exact saved native NPZ file SHA256',
        units='Unchanged source axes/model units.',
        quality=render.read_json(candidate['receipt']).get('quality'),
        acceptance='Export command follows internal whole+close visual review; counts are not beauty evidence.',
        seconds=time.perf_counter()-started)
    preserved.write_json(output/'MANIFEST.json', manifest)
    with (output/'README.txt').open('x', encoding='utf-8') as stream:
        stream.write('CHESHIRE actual saved SPINE candidate\nStatus: '+args.status+'\n\n'
            'comparison.html: exact same-camera900px original/candidate PNGs, offline.\n'
            'FULL PLY: all actual saved float64 coordinates and native triangles, complete readback verified.\n'
            'DETAIL PLY: exact native triangle subset; open cut boundary, no caps.\n'
            'Internal close approval authorizes context rendering only; research status is not beauty adoption.\n')
    print('ACTUAL_SPINE_PACKAGE_DONE '+str(output), flush=True)


if __name__ == '__main__':
    main()
