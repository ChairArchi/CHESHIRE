"""One actual native load: close review, then gated context with reused control.

Only the saved candidate is rendered. The immutable NESTED02 baseline PNGs
and their native/render receipts are verified and reused. This helper does no
geometry processing. A fresh workspace decision file requests context views
or rejects the close result; this is internal QA, not a user approval flow.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import time

HERE = Path(__file__).resolve().parent
FAST_PATH = HERE / 'fast_render.py'
FAST_SHA = '45a48c67b5f260f83d74e1b481ac1e3d37dfbc9441a25e3185a8b9621b3c2247'
WORKSPACE = Path('C:/Users/USER/CHESHIRE')
spec = importlib.util.spec_from_file_location('spine_review_frozen_native', FAST_PATH)
fast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fast)
render, digest, write = fast.render, fast.digest, fast.write


def code_hashes():
    if digest(FAST_PATH) != FAST_SHA:
        raise ValueError('Frozen verified native loader changed.')
    return dict(spine_review_renderer=digest(__file__), frozen_fast_renderer=fast.code_hashes())


def candidate_state(root, name, binding):
    expected, candidate = render.candidate_state(root, name, binding)
    if any(expected[key] != binding['saved_geometry'][key]
           for key in ('vertices', 'triangles', 'faces_sha256')):
        raise ValueError('This spine trial must retain the actual accepted native connectivity.')
    generation = render.read_json(root / 'RECEIPT.json')
    reference = generation.get('variants', {}).get('REFERENCE_NESTED')
    if not isinstance(reference, dict) or any(
            reference.get(key) != binding['saved_geometry'][key]
            for key in ('geometry_sha256', 'xyz_sha256', 'faces_sha256', 'vertices', 'triangles')):
        raise ValueError('REFERENCE_NESTED must bind the exact accepted baseline arrays.')
    reference_path = Path(reference['geometry'])
    reference_path = reference_path.resolve() if reference_path.is_absolute() else (root/reference_path).resolve()
    if digest(reference_path) != binding['source_native_geometry_sha256']:
        raise ValueError('Receipt-bound reference native bytes changed.')
    return expected, candidate


def decision_record(path, expected, candidate, close_path):
    decision = render.read_json(path)
    if (decision.get('action') not in ('render_context', 'reject') or
            decision.get('generation_receipt_sha256') != candidate['receipt_sha256'] or
            decision.get('candidate_xyz_sha256') != expected['xyz_sha256'] or
            decision.get('close_receipt_sha256') != digest(close_path) or
            not isinstance(decision.get('reason'), str) or not decision['reason'].strip()):
        raise ValueError('Internal decision must bind this exact generation, candidate and close receipt.')
    return decision


def write_internal_decision(root, name, path, action, reason):
    """Host-side atomic internal QA decision; no Blender or beauty inference."""
    root, path = Path(root).resolve(), Path(path).resolve()
    name = render.checked_name(name)
    if (not path.is_relative_to(WORKSPACE.resolve()) or path.exists() or
            action not in ('render_context', 'reject') or not isinstance(reason, str) or not reason.strip()):
        raise ValueError('Fresh workspace file, explicit action and internal QA reason required.')
    close_path = root/(name+'_REVIEW')/'close/receipt.json'
    close = render.read_json(close_path)
    if close['kind'] != 'ACTUAL_SAVED_NATIVE_SPINE_REVIEW_STAGE' or close['state'] != name:
        raise ValueError('Exact completed candidate close receipt required.')
    decision = dict(action=action, reason=reason,
        generation_receipt_sha256=close['candidate_binding']['receipt_sha256'],
        candidate_xyz_sha256=close['saved_geometry']['xyz_sha256'],
        close_receipt_sha256=digest(close_path))
    pending = path.with_name(path.name+'.pending')
    path.parent.mkdir(parents=True, exist_ok=True)
    with pending.open('x', encoding='utf-8') as stream:
        json.dump(decision, stream, ensure_ascii=False, indent=2)
    if path.exists():
        raise FileExistsError('Another internal decision already exists.')
    pending.replace(path)
    return dict(path=str(path), sha256=digest(path), value=decision)


def snapshot_sources(root, name, hashes, candidate):
    folder = root / 'source_snapshot_render' / name / 'spine_review'
    if folder.exists():
        raise FileExistsError('Earlier spine review snapshots are preserved.')
    folder.mkdir(parents=True)
    snapshots = {}
    for source in (Path(__file__).resolve(), FAST_PATH, fast.PRESERVED):
        target = folder / source.name
        shutil.copyfile(source, target)
        record = dict(source=str(source), snapshot=str(target), sha256=digest(source))
        render.verify_snapshot(record)
        snapshots[source.name] = record
    shutil.copyfile(candidate['receipt'], folder/'SOURCE_GENERATION_RECEIPT.json')
    if code_hashes() != hashes:
        raise ValueError('Executed source changed while taking snapshots.')
    return snapshots


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--variant', default='SPINE')
    parser.add_argument('--decision-file', type=Path, required=True)
    parser.add_argument('--decision-timeout', type=float, default=1800)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    root, name = args.root.resolve(), render.checked_name(args.variant)
    decision_path = args.decision_file.resolve()
    if (not decision_path.is_relative_to(WORKSPACE.resolve()) or decision_path.exists() or
            not 1 <= args.decision_timeout <= 7200):
        parser.error('A fresh C: workspace decision path and timeout1–7200seconds are required.')
    output = root / (name+'_REVIEW')
    if output.exists():
        raise FileExistsError('Earlier close/context review is preserved: '+str(output))
    binding = render.source_binding()
    expected, candidate = candidate_state(root, name, binding)
    hashes = code_hashes()
    snapshots = snapshot_sources(root, name, hashes, candidate)
    started = time.perf_counter()
    shared = render.scaffold.setup_scene()
    print('SPINE_LOAD actual saved complete native candidate; control PNGs reused', flush=True)
    obj, counts = fast.add_native_object(Path(expected['geometry']), expected, 'Actual saved '+name, shared)
    scene, camera = shared.setup_scene(900, 24)
    conditions = render.base.actual_conditions(bpy, scene, camera, obj)
    render.require_close(conditions, binding['conditions'])
    if bpy.app.version_string != binding['Blender_version']:
        raise ValueError('Actual candidate and preserved baseline Blender versions differ.')
    if len(obj.data.edges):
        raise ValueError('The actual flat native candidate acquired an unused edge graph.')
    initial = render.scaffold.geometry_signature(obj, counts, False)
    preparation_seconds = time.perf_counter()-started
    stages = {}

    def unchanged():
        if (render.source_binding() != binding or
                candidate_state(root, name, binding) != (expected, candidate) or code_hashes() != hashes):
            raise ValueError('Baseline, candidate, generation provenance or executed source changed.')
        for record in snapshots.values():
            render.verify_snapshot(record)

    def stage(stage_name, views):
        before = render.scaffold.geometry_signature(obj, counts, False)
        if before != initial or len(obj.data.edges):
            raise ValueError('Candidate changed before the next actual view.')
        render.require_close(render.base.actual_conditions(bpy, scene, camera, obj), conditions)
        folder = output / stage_name
        actual_views, images = render.scaffold.render_views(scene, camera,
            {view:binding['views'][view] for view in views}, folder)
        after = render.scaffold.geometry_signature(obj, counts, False)
        if before != after or len(obj.data.edges):
            raise ValueError('Actual coordinates/connectivity/flat flags changed during rendering.')
        for view in views:
            render.require_close(actual_views[view], binding['actual_views'][view], 'matched-camera.'+view)
        unchanged()
        record = dict(kind='ACTUAL_SAVED_NATIVE_SPINE_REVIEW_STAGE', state=name, phase=stage_name,
            saved_geometry=expected, candidate_binding=candidate, source_binding=binding,
            geometry_counts=counts, display_readback=after, conditions=conditions,
            actual_views=actual_views, images=images,
            reused_control_images=[item for item in binding['images'] if item['view'] in views],
            baseline_rerendered=False, geometry_unchanged_by_renderer=True,
            geometry_processing=False, all_flat=True, normal_maps=False, modifiers=[], mesh_edges=0,
            version=bpy.app.version_string, code_sha256=hashes, source_snapshots=snapshots,
            source_snapshot=snapshots['render_spine_review.py'], resolution_matched_to_source=True,
            native_connectivity_matched_to_source=True)
        path = folder/'receipt.json'
        write(path, record)
        result = dict(receipt=str(path), receipt_sha256=digest(path),
                      images={item['view']:str(folder/item['filename']) for item in images})
        stages[stage_name] = result
        return path

    close_path = stage('close', ['close_oblique'])
    print('SPINE_CLOSE_READY '+str(close_path), flush=True)
    print('SPINE_INTERNAL_DECISION_WAIT '+str(decision_path), flush=True)
    waiting_started = time.perf_counter()
    decision, decision_binding = None, None
    while time.perf_counter()-waiting_started < args.decision_timeout:
        if decision_path.is_file():
            decision = decision_record(decision_path, expected, candidate, close_path)
            decision_binding = dict(path=str(decision_path), sha256=digest(decision_path), value=decision)
            break
        time.sleep(.25)
    decision_wait_seconds = time.perf_counter()-waiting_started
    if decision is not None and decision['action'] == 'render_context':
        stage('context', ['front', 'body_oblique'])
        status = 'context_rendered_pending_final_visual_review'
    else:
        status = 'close_rejected_internal' if decision is not None else 'internal_decision_timeout'
    unchanged()
    if decision_binding and digest(decision_path) != decision_binding['sha256']:
        raise ValueError('The exact internal decision changed after it was used.')
    write(output/'REVIEW_RECEIPT.json', dict(kind='ACTUAL_NATIVE_SPINE_GATED_REVIEW_WITH_REUSED_CONTROL',
        state=name, status=status, saved_geometry=expected, candidate_binding=candidate,
        source_binding=binding, stages=stages, internal_decision=decision_binding,
        code_sha256=hashes, source_snapshots=snapshots, version=bpy.app.version_string,
        native_candidate_loaded_once=True, shared_native_object=True, baseline_rerendered=False,
        same_native_geometry_for_close_and_context=('context' in stages), all_flat=True,
        geometry_processing=False, normal_maps=False, modifiers=[], mesh_edges=0,
        preparation_seconds=preparation_seconds, decision_wait_seconds=decision_wait_seconds,
        scope='Saved actual candidate only; source baseline PNGs reused unchanged. Close-first internal QA '
              'may authorize context rendering and does not constitute beauty adoption or user approval.'))
    print('SPINE_REVIEW_DONE '+status+' '+str(output), flush=True)


if __name__ == '__main__':
    main()
