"""Render two exact preserved control cages, using display-only centre fans.

Same actual NESTED02 close/body cameras, material, lights and all-flat flags.
No candidate generation, geometry processing, normal map or surface modifier.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import shutil
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('parent_continuity_prepare_binding', HERE/'prepare_audit.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
previous = prepare.previous
scaffold, base = previous.scaffold, previous.base
digest, read_json, write = previous.digest, previous.read_json, previous.write
ROOT = prepare.ROOT
VIEWS = ('close_oblique', 'body_oblique')
STATES = ('G06_MIDDLE', 'G07_SURFACE')


def code_hashes():
    return dict(renderer=digest(__file__), preparation_code=prepare.code_hashes())


def audit_binding(root):
    path = root/'AUDIT_RECEIPT.json'
    receipt = read_json(path)
    binding = previous.source_binding()
    if (receipt['kind'] != 'PRESERVED_PARENT_CONTINUITY_DISPLAY_AUDIT' or
            receipt['design_candidates_generated'] != 0 or receipt['source_controls_modified'] is not False or
            receipt['source_intermediate_natives'] != 'NOT_STORED_INTERMEDIATE' or
            receipt['source_binding'] != binding or receipt['code_sha256'] != prepare.code_hashes() or
            set(receipt['states']) != set(STATES)):
        raise ValueError('Actual audit preparation/baseline binding differs.')
    previous.verify_snapshot(receipt['source_snapshot'])
    for name, record in receipt['states'].items():
        source = record['original_control']
        display = record['display_geometry']
        if (source['sha256'] != prepare.CONTROLS[name] or digest(source['path']) != source['sha256'] or
                digest(source['generation_json']) != source['generation_json_sha256'] or
                source['native_surface'] != 'NOT_STORED_INTERMEDIATE' or
                digest(display['geometry']) != display['geometry_sha256'] or
                record['display_derivation']['stored_vertices_unchanged_exactly'] is not True or
                record['display_derivation']['complete_saved_array_roundtrip'] is not True):
            raise ValueError('Actual immutable intermediate control/display binding differs.')
    return receipt, binding, dict(receipt=str(path), receipt_sha256=digest(path))


def snapshot(root):
    source = Path(__file__).resolve()
    target = root/'source_snapshot_render/experiments'/HERE.name/source.name
    if target.exists():
        raise FileExistsError('Earlier audit renderer snapshot preserved.')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    record = dict(source=str(source), snapshot=str(target), sha256=digest(source))
    previous.verify_snapshot(record)
    return record


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    if (root/'RENDER_AUDIT_RECEIPT.json').exists():
        raise FileExistsError('Earlier completed audit render preserved.')
    prepared, binding, candidate = audit_binding(root)
    hashes, snap = code_hashes(), snapshot(root)
    shared = scaffold.setup_scene()
    scene, camera = shared.setup_scene(900, 24)
    views = {view:binding['views'][view] for view in VIEWS}
    results = {}
    for name in STATES:
        record = prepared['states'][name]
        expected = record['display_geometry']
        output = root/(name+'_FLAT')/'review'
        if output.exists():
            raise FileExistsError('Earlier actual audit view preserved: '+name)
        print('AUDIT LOAD '+name+': actual preserved control display fans', flush=True)
        obj, counts = scaffold.add_native_object(Path(expected['geometry']), expected,
            'Preserved '+name+' control cage; display-only arithmetic fan', shared)
        scaffold.set_smooth_flags(obj, False)
        conditions = base.actual_conditions(bpy, scene, camera, obj)
        previous.require_close(conditions, binding['conditions'])
        if bpy.app.version_string != binding['Blender_version']:
            raise ValueError('Actual baseline/audit Blender version differs.')
        before = scaffold.geometry_signature(obj, counts, False)
        actual_views, images = scaffold.render_views(scene, camera, views, output)
        after = scaffold.geometry_signature(obj, counts, False)
        if before != after:
            raise ValueError('Actual display fan changed during rendering.')
        for view in VIEWS:
            previous.require_close(actual_views[view], binding['actual_views'][view], 'matched-camera.'+view)
        result = dict(state=name, phase='preserved_control_audit', saved_geometry=expected,
            audit_binding=candidate, original_control=record['original_control'],
            display_derivation=record['display_derivation'], source_binding=binding,
            geometry_counts=counts, display_readback=after, conditions=conditions,
            actual_views=actual_views, images=images, geometry_unchanged_by_renderer=True,
            original_native_surface='NOT_STORED_INTERMEDIATE',
            display_derived_for_audit=True, original_control_vertices_repositioned=False,
            all_flat=True, geometry_processing=False, normal_maps=False, modifiers=[],
            version=bpy.app.version_string, code_sha256=hashes, source_snapshot=snap,
            comparison_scope='Actual preserved intermediate control cage displayed only by arithmetic quad-centre fans. Original intermediate native was not stored. Same NESTED02 body/close actual camera, material, light, samples and all-flat conditions. No model generation, smoothing or displacement occurs.')
        previous.previous.previous.frozen.previous.display_proof(result, expected)
        write(output/'receipt.json', result)
        results[name] = dict(receipt=str(output/'receipt.json'), receipt_sha256=digest(output/'receipt.json'),
                             images={item['view']:str(output/item['filename']) for item in images})
        print('AUDIT_STATE_DONE '+name+': two actual PNGs; native-display readbacks unchanged', flush=True)
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        del obj, mesh, before, after
        gc.collect()
    if (audit_binding(root) != (prepared, binding, candidate) or code_hashes() != hashes):
        raise ValueError('Actual preserved controls, derived displays, baseline or executed code changed.')
    previous.verify_snapshot(snap)
    write(root/'RENDER_AUDIT_RECEIPT.json', dict(kind='PRESERVED_PARENT_CONTINUITY_RENDER_AUDIT',
        design_candidates_generated=0, original_control_vertices_repositioned=False,
        audit_binding=candidate, source_binding=binding, states=results,
        views=list(VIEWS), all_flat=True, geometry_processing=False,
        code_sha256=hashes, source_snapshot=snap))
    print('PARENT_CONTINUITY_AUDIT_RENDER_DONE: two preserved states x two matched actual views', flush=True)


if __name__ == '__main__':
    main()
