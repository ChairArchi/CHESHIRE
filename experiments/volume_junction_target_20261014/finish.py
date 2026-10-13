"""G7-derived actual volumetric finish; separate from the original growth recipe.

One finer voxel union removes overlapping internal sheets. Actual marked-region
weights limit additional smoothing; one geometric CC finish resolves voxel
facets. Applied X/Y Mirror retains explicit bilateral symmetry. No source file
is changed, no new ornament or Mandelbulb field is added, and this is not G8.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import shutil
import sys
import time
import traceback

import bpy
import numpy as np
from mathutils.kdtree import KDTree

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('volume_finish_frozen_target_builder', HERE/'build_target.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
digest, write = helper.digest, helper.write

RECIPE = dict(schema='CHESHIRE_G7_DERIVED_VOLUME_FINISH_20261014',
    voxel_size_height_fraction=.00075, remesh_mode='VOXEL', adaptivity=0.,
    marked_region_target_smooth_factor=.65, marked_region_target_smooth_iterations=3,
    smoothing_weight='Closest actual original G7 control in the marked axial support plus .03H collar; use preserved full_mask scalar. All other remeshed controls have zero smoothing weight.',
    symmetry='Applied X/Y Mirror with bisect, merge and clipping at source origin before geometric subdivision.',
    geometric_finish='One actual Catmull-Clark subdivision of the NEW remesh topology, applied and saved. This is a finish pass, not original source subdivision G8.',
    original_growth_source_generation=7, remesh_finish_CC_passes=1,
    original_chart_face_ID_ancestry_retained=False,
    new_ornament_events=0, added_mandelbulb_evaluations=0,
    scope='A separate whole-column volumetric finish candidate. Voxel remesh changes geometry globally; extra smoothing is restricted to marked support. Original G1-G7 files/formula remain untouched. No exact volume, undercut retention, self-intersection or fabrication certification.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    out = root/'volume_finish'
    if out.exists():
        raise FileExistsError('Earlier finish candidate preserved.')
    out.mkdir()
    started = time.perf_counter()
    request = json.loads((root/'projection_request.json').read_text(encoding='utf-8'))
    source = Path(request['source_native_path'])
    source_control = Path(request['source'])/'control_quad.npz'
    if digest(source) != request['source_native_sha256'] or digest(source_control) != request['source_control_sha256'] or digest(root/'selection.npz') != request['selection_npz_sha256']:
        raise ValueError('Preserved original source/selection changed.')
    height = request['height']
    hashes = dict(finish_code_sha256=digest(__file__), frozen_target_builder_sha256=digest(HERE/'build_target.py'),
        source_native_sha256=request['source_native_sha256'], source_control_sha256=request['source_control_sha256'],
        selection_npz_sha256=request['selection_npz_sha256'])
    snapshots = out/'source_snapshot'
    snapshots.mkdir()
    for p in [Path(__file__), HERE/'build_target.py', root/'projection_request.json']:
        shutil.copyfile(p, snapshots/p.name)
    write(out/'RUN_REQUEST.json', dict(recipe=RECIPE, input_hashes=hashes, source=str(source), height=height))
    phase = 'LOAD_ORIGINAL_NATIVE'
    try:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        helper.purge_unused_meshes()
        obj, source_record = helper.load_native(source)
        phase = 'FINE_VOXEL_UNION'
        modifier = obj.modifiers.new('Actual fine voxel union', 'REMESH')
        modifier.mode = 'VOXEL'
        modifier.voxel_size = height*RECIPE['voxel_size_height_fraction']
        modifier.adaptivity = 0.
        modifier.use_remove_disconnected = False
        modifier.use_smooth_shade = False
        remesh_properties = helper.actual_properties(modifier)
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        helper.purge_unused_meshes()
        print('FINE_VOXEL', len(obj.data.vertices), len(obj.data.polygons), flush=True)
        phase = 'MARKED_WEIGHT_TRANSFER'
        xyz = np.empty((len(obj.data.vertices), 3), np.float32)
        obj.data.vertices.foreach_get('co', xyz.ravel())
        with np.load(source_control, allow_pickle=False) as data:
            controls = data['xyz']
        with np.load(root/'selection.npz', allow_pickle=False) as data:
            mask = data['full_mask']
        support = controls[mask > 0.]
        low, high = float(support[:, 2].min()-.03*height), float(support[:, 2].max()+.03*height)
        keep = (controls[:, 2] >= low) & (controls[:, 2] <= high)
        points, weights = controls[keep], mask[keep]
        del controls, mask, support
        gc.collect()
        tree = KDTree(len(points))
        for index, point in enumerate(points):
            tree.insert(point, index)
        tree.balance()
        group = obj.vertex_groups.new(name='Actual preserved marked support')
        active = np.flatnonzero((xyz[:, 2] >= low) & (xyz[:, 2] <= high))
        assigned_count = 0
        # Blender vertex-group assignments retain actual nonquantized feather values.
        for index in active:
            nearest, owner, distance = tree.find(xyz[index])
            weight = float(weights[owner])
            if weight > 0.:
                group.add([int(index)], weight, 'REPLACE')
                assigned_count += 1
        print('MARKED_SMOOTH_WEIGHTS', assigned_count, flush=True)
        del xyz, points, weights, tree
        gc.collect()
        phase = 'MARKED_GEOMETRIC_SMOOTH'
        modifier = obj.modifiers.new('Marked-only actual smoothing', 'SMOOTH')
        modifier.factor = .65
        modifier.iterations = 3
        modifier.vertex_group = group.name
        modifier.use_x = modifier.use_y = modifier.use_z = True
        smooth_properties = helper.actual_properties(modifier)
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        helper.purge_unused_meshes()
        phase = 'ACTUAL_XY_MIRROR'
        modifier = obj.modifiers.new('Actual X Y reflection', 'MIRROR')
        modifier.use_axis = (True, True, False)
        modifier.use_bisect_axis = (True, True, False)
        modifier.use_bisect_flip_axis = (True, False, False)
        modifier.use_clip = True
        modifier.use_mirror_merge = True
        modifier.merge_threshold = 1e-6*height
        modifier.bisect_threshold = 1e-6*height
        mirror_properties = helper.actual_properties(modifier)
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        helper.purge_unused_meshes()
        phase = 'ONE_REAL_GEOMETRIC_CC_FINISH'
        modifier = obj.modifiers.new('One geometric finish pass', 'SUBSURF')
        modifier.subdivision_type = 'CATMULL_CLARK'
        modifier.levels = modifier.render_levels = 1
        modifier.use_limit_surface = True
        finish_properties = helper.actual_properties(modifier)
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        helper.purge_unused_meshes()
        obj.data.calc_loop_triangles()
        xyz = np.empty((len(obj.data.vertices), 3), np.float32)
        triangles = np.empty((len(obj.data.loop_triangles), 3), np.int32)
        obj.data.vertices.foreach_get('co', xyz.ravel())
        obj.data.loop_triangles.foreach_get('vertices', triangles.ravel())
        if not np.isfinite(xyz).all() or not len(triangles):
            raise ValueError('Invalid actual volume-finish mesh.')
        phase = 'SAVE_ACTUAL_FINISH'
        path = out/'geometry.npz'
        np.savez(path, xyz=xyz, faces=triangles)
        record = dict(date='2026-10-14', timezone='Asia/Seoul', candidate='G7_DERIVED_VOLUME_FINISH',
            source_generation=7, original_growth_generation_preserved_as_input=True,
            output_has_original_G7_ID_ancestry=False, recipe=RECIPE, input_hashes=hashes,
            source=str(source), source_control=str(source_control), native_source=source_record,
            geometry=str(path), geometry_sha256=digest(path), xyz_sha256=helper.array_hash(xyz), faces_sha256=helper.array_hash(triangles),
            vertices=len(xyz), triangles=len(triangles), polygons=len(obj.data.polygons),
            actual_remesh=remesh_properties, actual_marked_smooth=smooth_properties,
            actual_mirror=mirror_properties, actual_geometric_finish=finish_properties,
            marked_smoothing_weighted_vertices=assigned_count, smoothing_weight_transfer_z_range=[low, high],
            blender_version=bpy.app.version_string, remaining_modifiers=len(obj.modifiers),
            elapsed_finish_seconds=time.perf_counter()-started, visual_status='PENDING_ACTUAL_RENDER',
            source_files_unchanged=digest(source)==request['source_native_sha256'] and digest(source_control)==request['source_control_sha256'],
            scope=RECIPE['scope'])
        if not record['source_files_unchanged'] or digest(__file__) != hashes['finish_code_sha256']:
            raise ValueError('Frozen source changed during finish.')
        write(out/'FINISH_RECEIPT.json', record)
        print('VOLUME_FINISH_DONE', len(xyz), len(triangles), flush=True)
    except Exception as error:
        write(out/'FAILURE.json', dict(phase=phase, error=str(error), traceback=traceback.format_exc(),
            input_hashes=hashes, recipe=RECIPE, elapsed_seconds=time.perf_counter()-started))
        raise


if __name__ == '__main__':
    main()
