"""Render exact original triangle subsets at one new measured-leaf camera.

This is an explicitly NEW focal camera, shared by NESTED02 and the candidate.
It does not replace the preserved close/body/front comparison. Exact original
triangles are retained in a focal sphere and a padded camera guard; cut edges
remain outside the visible orthographic frame. No vertex motion, remeshing,
normal correction, smooth shading, displacement or added surface is applied.

Blender --background --python render_leaf_detail.py -- --root TRIAL
  --variant ACANTHUS --output NEW_DIRECTORY --event-index 20 --resolution 900
"""
from pathlib import Path
import argparse
import copy
import gc
import importlib.util
import json
import shutil
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
RENDERER = HERE / 'render.py'
spec = importlib.util.spec_from_file_location('leaf_detail_preserved_render', RENDERER)
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
digest, write = render.digest, render.write
ANCESTRY = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states')
CHUNK = 65536


def unit(value):
    length = float(np.linalg.norm(value))
    if not np.isfinite(length) or length <= 1e-12:
        raise ValueError('A finite nonzero camera direction is required.')
    return np.asarray(value, dtype=float) / length


def auxiliary(receipt, stage, filename):
    path = ANCESTRY / stage / filename
    checksum = receipt.get('sources', {}).get(str(path))
    if checksum is None:
        # Canonical path strings can use either slash spelling on Windows.
        checksum = next((value for key, value in receipt.get('sources', {}).items()
                         if Path(key).resolve() == path.resolve()), None)
    if checksum is None or digest(path) != checksum:
        raise ValueError('Measured leaf camera needs the receipt-bound ancestry input: ' + str(path))
    return path, checksum


def measured_camera(root, receipt, expected, xyz, binding, event_index, ortho_scale):
    leaves = receipt.get('selected_leaves')
    if not isinstance(leaves, list):
        raise ValueError('An actual selected_leaves generation record is required.')
    selected = [event for event in leaves if event.get('source_event_index') == event_index]
    if len(selected) != 1:
        raise ValueError('Exactly one selected measured source event is required: ' + str(event_index))
    event = selected[0]
    chart_path, chart_sha = auxiliary(receipt, 'G04_NEUTRAL', 'control_quad.npz')
    phase_path, phase_sha = auxiliary(receipt, 'G06_MIDDLE', 'evidence.npz')
    ownership_path, ownership_sha = auxiliary(receipt, 'G03_SIDEWALL', 'evidence.npz')
    with np.load(chart_path, allow_pickle=False) as data:
        chart, quads = data['chart'], data['faces']
    n = len(chart)
    if n > len(xyz) or chart.ndim != 2 or chart.shape[1] < 1:
        raise ValueError('Candidate must retain the actual old-G4 vertex prefix.')
    t = chart[:, 0]
    with np.load(phase_path, allow_pickle=False) as data:
        phase = data['directional_phase'][:n].copy()
    with np.load(ownership_path, allow_pickle=False) as data:
        body_faces = np.repeat(data['face_event_ids'] == 0, 4)
    if len(body_faces) != len(quads):
        raise ValueError('Actual G3 ownership does not correspond to the G4 camera chart.')
    degree = np.bincount(quads.ravel(), minlength=n)
    support = np.divide(np.bincount(quads.ravel(), weights=np.repeat(body_faces.astype(float), 4),
                                   minlength=n), degree, out=np.zeros(n), where=degree > 0)
    centre_phase = 2 * np.pi * int(event['parent_cycle']) + np.interp(
        t, event['centre_t'], event['centre_phase_offset'])
    mask = ((np.abs(t - float(event['t_peak'])) < .01) &
            (np.abs(phase - centre_phase) < .2) & (support > .9))
    ids = np.flatnonzero(mask)
    if not len(ids):
        raise ValueError('No actual G4 old-ID controls lie in the measured leaf-peak window.')
    # One inherited phase family may contain reflected copies. Select the
    # observed quadrant toward the original close camera before taking a mean.
    preferred = np.asarray(binding['actual_views']['close_oblique']['position'], dtype=float) - np.asarray(
        binding['actual_views']['close_oblique']['target'], dtype=float)
    preferred[2] = 0.
    preferred = unit(preferred)
    radial = np.column_stack((xyz[ids, 0], xyz[ids, 1], np.zeros(len(ids))))
    radial /= np.maximum(np.linalg.norm(radial, axis=1), 1e-30)[:, None]
    score = radial @ preferred
    best = int(np.argmax(score))
    anchor = radial[best]
    visible = (radial @ anchor) >= np.cos(np.pi / 4)
    ids = ids[visible]
    target = xyz[ids].mean(axis=0)
    outward = unit(np.array([target[0], target[1], 0.]))
    height = float(np.ptp(xyz[:, 2]))
    position = target + .8 * height * outward + np.array([0., 0., .15 * height])
    forward = unit(target - position)
    right = unit(np.cross(forward, np.array([0., 0., 1.])))
    up = unit(np.cross(right, forward))
    metadata = dict(kind='NEW_MEASURED_LEAF_FOCAL_CAMERA', source_event_index=event_index,
        selected_event=event, target=target.tolist(), position=position.tolist(), ortho_scale=ortho_scale,
        candidate_G4_old_vertex_ids=ids.tolist(), actual_vertex_mean_target=True,
        longitudinal_window=.01, phase_window=.2, minimum_body_support=.9,
        reflected_copy_selection='Actual leaf-peak samples within 45 degrees of the sample most aligned '
            'with the preserved close-camera radial direction; no averaging across reflected quadrants.',
        preferred_reference_radial=preferred.tolist(), camera_radial=outward.tolist(),
        camera_offset='.8 * actual model height radial + .15 * height in Z',
        actual_model_height=height, shared_for_baseline_and_candidate=True,
        preserved_original_camera=False,
        auxiliary_sources=[dict(path=str(path), sha256=checksum) for path, checksum in
                           ((chart_path, chart_sha), (phase_path, phase_sha), (ownership_path, ownership_sha))])
    return (position.tolist(), target.tolist(), ortho_scale), (target, right, up), metadata


def exact_subset(output, label, expected, xyz, faces, basis, radius, scale, guard):
    target, right, up = basis
    selected = []
    halfwidth = .5 * scale * guard
    excluded_bbox_overlaps_visible_frame = 0
    for start in range(0, len(faces), CHUNK):
        block = faces[start:start + CHUNK]
        points = xyz[block] - target
        distance2 = np.einsum('ijk,ijk->ij', points, points)
        sphere = (distance2 <= radius ** 2).any(axis=1)
        horizontal, vertical = points @ right, points @ up
        camera_guard = ((horizontal.min(axis=1) <= halfwidth) &
                        (horizontal.max(axis=1) >= -halfwidth) &
                        (vertical.min(axis=1) <= halfwidth) &
                        (vertical.max(axis=1) >= -halfwidth))
        chosen = sphere | camera_guard
        visible_bbox = ((horizontal.min(axis=1) <= .5 * scale) &
                        (horizontal.max(axis=1) >= -.5 * scale) &
                        (vertical.min(axis=1) <= .5 * scale) &
                        (vertical.max(axis=1) >= -.5 * scale))
        excluded_bbox_overlaps_visible_frame += int(np.count_nonzero(~chosen & visible_bbox))
        selected.append(start + np.flatnonzero(chosen))
    face_ids = np.concatenate(selected)
    if not len(face_ids) or excluded_bbox_overlaps_visible_frame:
        raise ValueError('Exact subset is empty or cuts across the visible camera frame.')
    source_faces = faces[face_ids]
    vertex_ids, inverse = np.unique(source_faces.ravel(), return_inverse=True)
    subset_xyz, subset_faces = xyz[vertex_ids], inverse.reshape(-1, 3)
    if (not np.array_equal(vertex_ids[subset_faces], source_faces) or
            not np.array_equal(subset_xyz, xyz[vertex_ids])):
        raise ValueError('Exact triangle subset coordinate/connectivity mapping differs.')
    folder = output / label
    folder.mkdir()
    path, ids_path = folder / 'geometry.npz', folder / 'SOURCE_IDS.npz'
    np.savez_compressed(path, xyz=subset_xyz, faces=subset_faces)
    np.savez_compressed(ids_path, source_vertex_ids=vertex_ids, source_face_ids=face_ids)
    record = dict(geometry=str(path), geometry_sha256=digest(path),
        xyz_sha256=render.scaffold.array_hash(subset_xyz), faces_sha256=render.scaffold.array_hash(subset_faces),
        vertices=len(subset_xyz), triangles=len(subset_faces),
        source_geometry=expected, source_ids=dict(path=str(ids_path), sha256=digest(ids_path)),
        scope='Exact original native triangle subset; original vertex coordinates and triangle orientation '
            'unchanged. Vertex IDs are compactly reindexed, with complete source ID correspondence.',
        selection='Union of triangles with any vertex inside the focal sphere and triangles whose '
            'orthographic projected bounding box intersects the padded camera rectangle, at any depth.',
        focal_sphere=dict(center=target.tolist(), radius=radius),
        camera_guard=dict(orthographic_scale=scale, padding_factor=guard, halfwidth=halfwidth,
            excluded_triangle_bboxes_intersecting_visible_frame=excluded_bbox_overlaps_visible_frame,
            cut_boundary_outside_visible_frame=True),
        source_vertices_moved=False, source_triangles_changed=False, original_face_normals_preserved=True,
        added_surfaces=False, remeshing=False, open_cut_boundary=True,
        limitation='Subsetting can alter shadows cast by excluded distant geometry. Both sides use '
            'the same exact-subset rule and shared new camera; this is a focal review, not a full-model render.')
    # Read the complete saved crop back before Blender loads it.
    check_xyz, check_faces = render.load_arrays(record)
    if not np.array_equal(check_xyz, subset_xyz) or not np.array_equal(check_faces, subset_faces):
        raise ValueError('Saved exact crop roundtrip differs.')
    write(folder / 'SUBSET_RECEIPT.json', record)
    return record


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--variant', default='ACANTHUS')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--event-index', type=int, default=20)
    parser.add_argument('--resolution', type=int, default=900)
    parser.add_argument('--ortho-scale', type=float, default=1.65)
    parser.add_argument('--crop-radius', type=float, default=1.45)
    parser.add_argument('--camera-guard', type=float, default=1.15)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    if (not 64 <= args.resolution <= 4096 or
            not np.isfinite([args.ortho_scale, args.crop_radius, args.camera_guard]).all() or
            min(args.ortho_scale, args.crop_radius) <= 0. or args.camera_guard <= 1.):
        parser.error('Finite positive scale/radius, camera guard > 1 and resolution 64..4096 required.')
    root, output = args.root.resolve(), args.output.resolve()
    name = render.checked_name(args.variant)
    if output.exists():
        raise FileExistsError('Earlier leaf focal output is preserved: ' + str(output))
    binding = render.source_binding()
    expected, generation = render.candidate_state(root, name, binding)
    receipt = render.read_json(generation['receipt'])
    hashes = dict(leaf_renderer=digest(__file__), preserved_renderer=render.code_hashes())
    print('LEAF FOCAL LOAD actual saved candidate and measure selected event', flush=True)
    xyz, faces = render.load_arrays(expected)
    view, basis, focal = measured_camera(root, receipt, expected, xyz, binding,
                                          args.event_index, args.ortho_scale)
    output.mkdir(parents=True)
    source_snapshot = output / 'SOURCE_SNAPSHOT_render_leaf_detail.py'
    shutil.copyfile(__file__, source_snapshot)
    crops = {name: exact_subset(output, name, expected, xyz, faces, basis,
                                args.crop_radius, args.ortho_scale, args.camera_guard)}
    del xyz, faces
    gc.collect()
    print('LEAF FOCAL LOAD actual NESTED02 native G7; retain exact original triangle subset', flush=True)
    source_expected = copy.deepcopy(binding['saved_geometry'])
    xyz, faces = render.load_arrays(source_expected)
    crops['NESTED02'] = exact_subset(output, 'NESTED02', source_expected, xyz, faces, basis,
                                     args.crop_radius, args.ortho_scale, args.camera_guard)
    del xyz, faces
    gc.collect()
    write(output / 'PREPARATION_RECEIPT.json', dict(generation_receipt=generation, source_binding=binding,
        focal_camera=focal, exact_subsets=crops, executed_code_sha256=hashes))
    shared = render.scaffold.setup_scene()
    scene, camera = shared.setup_scene(args.resolution, 24)
    results = {}
    for label in ('NESTED02', name):
        crop = crops[label]
        print('LEAF FOCAL RENDER exact saved subset ' + label, flush=True)
        obj, counts = render.scaffold.add_native_object(Path(crop['geometry']), crop,
                                                         'Exact native leaf subset ' + label, shared)
        render.scaffold.set_smooth_flags(obj, False)
        conditions = render.base.actual_conditions(bpy, scene, camera, obj)
        expected_conditions = copy.deepcopy(binding['conditions'])
        expected_conditions['resolution'] = [args.resolution, args.resolution]
        render.require_close(conditions, expected_conditions)
        if bpy.app.version_string != binding['Blender_version']:
            raise ValueError('Original source and new focal renderer Blender versions differ.')
        before = render.scaffold.geometry_signature(obj, counts, False)
        actual_views, images = render.scaffold.render_views(scene, camera, {'leaf_detail': view},
                                                            output / label / 'render')
        after = render.scaffold.geometry_signature(obj, counts, False)
        if before != after:
            raise ValueError('Exact saved native subset changed during focal rendering.')
        result = dict(state=label, phase='new_leaf_focal_review', saved_geometry=crop,
            geometry_counts=counts, display_readback=after, actual_views=actual_views, images=images,
            conditions=conditions, all_flat=True, modifiers=[], normal_maps=False,
            geometry_unchanged_by_renderer=True, geometry_processing=False,
            new_camera=True, preserved_close_camera=False,
            source_original_triangle_subset=True, version=bpy.app.version_string)
        write(output / label / 'render' / 'receipt.json', result)
        results[label] = result
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        del obj, mesh, before, after
        gc.collect()
    render.require_close(results['NESTED02']['actual_views'], results[name]['actual_views'])
    if (render.source_binding() != binding or render.candidate_state(root, name, binding) != (expected, generation) or
            dict(leaf_renderer=digest(__file__), preserved_renderer=render.code_hashes()) != hashes or
            digest(source_snapshot) != hashes['leaf_renderer']):
        raise ValueError('Focal rendering inputs or executed code changed.')
    for crop in crops.values():
        if digest(crop['geometry']) != crop['geometry_sha256'] or digest(crop['source_ids']['path']) != crop['source_ids']['sha256']:
            raise ValueError('Exact saved triangle subset or source IDs changed.')
    result = dict(kind='NEW_MEASURED_LEAF_FOCAL_COMPARISON', candidate=name,
        generation_receipt=generation, source_binding=binding, focal_camera=focal,
        exact_subsets=crops, renders=results, resolution=[args.resolution, args.resolution], samples=24,
        shared_new_camera=True, preserved_original_close_camera=False,
        shared_original_material_lights_samples_all_flat=True, source_vertices_moved=False,
        source_native_topology_unchanged=True, no_surface_repair=True,
        executed_code_sha256=hashes, source_snapshot=dict(path=str(source_snapshot), sha256=digest(source_snapshot)),
        comparison_scope='Actual NESTED02 native G7 original triangles versus actual saved candidate '
            'original triangles at one new measured-leaf camera. Each side is an exact native subset; '
            'native generation/counts can differ and are recorded. No image retouching or geometry repair.')
    write(output / 'RENDER_LEAF_DETAIL_RECEIPT.json', result)
    print('LEAF_FOCAL_RENDER_DONE: ' + str(output), flush=True)


if __name__ == '__main__':
    main()
