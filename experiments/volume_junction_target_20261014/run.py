"""One bounded envelope projection of the original marked SPAN G7 controls.

Prepare binds real source IDs/normals and the preserved marked region. Blender
builds an actual voxel-remeshed, smoothed TARGET only. Apply retains the original
G7 topology and blends toward eligible closest points; it is not topological
fusion. Original arrays and all prior rejected candidates remain untouched.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import shutil
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/volume_junction_target_20261014/trial01')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


previous = module('volume_target_frozen_source', HERE.parent/'finite_fork_folds_20261013/run.py')
helper = module('volume_target_frozen_region', HERE.parent/'ornament_junction_finish_20261014/run.py')
field = helper.operator.field
core, loader, digest, write = previous.core, previous.loader, previous.digest, previous.write
SOURCE = previous.SOURCE
from cheshire.reference_subdivision import ArrayMesh

RECIPE = dict(schema='CHESHIRE_LOCAL_VOLUME_ENVELOPE_PROJECTION_20261014',
    source_generation=7, output_generation=7,
    target_method='Blender VOXEL Remesh followed by actual geometry Smooth modifier; target only.',
    voxel_size_height_fraction=.0018, target_smooth_factor=.65, target_smooth_iterations=6,
    projection='Actual closest target-surface point, within maximum distance; source and target normal dot >= 0.',
    maximum_projection_distance_height_fraction=.0075, projection_blend=.85,
    mask_promotion='quintic_smoothstep(clip(original_coarse_marked_mask/.30,0,1)), then actual linear V/E/F scalar lifts.',
    delta_relaxation_iterations=2, delta_relaxation_factor=.5,
    delta_relaxation='Two uniform edge-neighbor averages of NEW displacement only, blended .5; zero mask and ineligible IDs reset to zero. Source coordinates are never averaged.',
    reflection='Canonical x<0,y>0 query; explicitly reflect vectors onto all actual X/Y ID partners before frozen representative transport.',
    preservation='Original G7 topology, classes, chart, rest, anchors and mask-zero coordinates remain exact.',
    added_CC_passes=0, added_topology_events=0, added_mandelbulb_evaluations=0,
    source_geometry_averaged=False, source_geometry_parametrically_rebuilt=False,
    source_geometry_envelope_projected=True,
    interpretation='Bounded local coordinate projection to a volumetric envelope. Original internal layers remain; no actual final-mesh fusion, collision repair or tangent-continuity certification.')


def quintic(value):
    x = np.clip(value, 0., 1.)
    return x*x*x*(10.+x*(-15.+6.*x))


def code_hashes(source):
    hashes = dict(source['geometry_code_sha256'])
    for p in [Path(__file__), HERE/'build_target.py',
              HERE.parent/'finite_fork_folds_20261013/run.py',
              HERE.parent/'finite_fork_folds_20261013/fold_operator.py',
              HERE.parent/'ornament_junction_finish_20261014/run.py',
              HERE.parent/'ornament_junction_finish_20261014/junction_operator.py',
              HERE.parent/'whole_column_detail_20261013/whole_field.py']:
        hashes[p.relative_to(REPO).as_posix()] = digest(p)
    return hashes


def snapshot(root, hashes):
    for rel, expected in hashes.items():
        source = REPO/rel.replace('\\', '/')
        if digest(source) != expected:
            raise ValueError('Source code mismatch: '+rel)
        dest = root/'source_snapshot'/rel.replace('\\', '/')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)


def incident_faces(faces, selected, count):
    hit = np.zeros(count, bool)
    hit[selected] = True
    result = []
    for start in range(0, len(faces), 262144):
        block = faces[start:start+262144]
        result.append(block[np.any(hit[block], axis=1)])
    return np.concatenate(result)


def selected_normals(xyz, faces, ids):
    local_faces = incident_faces(faces, ids, len(xyz))
    points = xyz[local_faces]
    centre = points.mean(axis=1)
    fn = np.cross(points-centre[:, None], np.roll(points, -1, axis=1)-centre[:, None]).sum(axis=1)
    lookup = np.full(len(xyz), -1, np.int32)
    lookup[ids] = np.arange(len(ids), dtype=np.int32)
    normals = np.zeros((len(ids), 3))
    for corner in range(4):
        index = lookup[local_faces[:, corner]]
        valid = index >= 0
        np.add.at(normals, index[valid], fn[valid])
    length = np.linalg.norm(normals, axis=1)
    if np.any(length <= 1e-16):
        raise ValueError('Degenerate selected source normal; no fallback.')
    return normals/length[:, None]


def prepare(root):
    if root.exists() and any(root.iterdir()):
        raise FileExistsError('Earlier output preserved; select a new empty root.')
    started = time.perf_counter()
    root.mkdir(parents=True, exist_ok=True)
    print('LOAD original source and preserved marked-region IDs', flush=True)
    mesh, chart, pairs, coords, height, source, ancestry, frame = previous.load()
    path, lifts, hierarchy = helper.load_lifts(mesh)
    nc = json.loads((Path(path)/'generation.json').read_text(encoding='utf-8'))['control_vertices']
    coarse_mask, region = helper.selection(mesh, nc, pairs, lifts[0]['input_faces'])
    mask = quintic(coarse_mask/.30)
    for lift in lifts:
        mask = np.concatenate([mask, mask[lift['input_edges']].mean(axis=1), mask[lift['input_faces']].mean(axis=1)])
    if len(mask) != len(mesh.xyz):
        raise ValueError('Actual lift must terminate at source G7.')
    for axis in ('x', 'y'):
        if not np.allclose(mask, mask[pairs['mirror_'+axis+'_vertex_pairs']], rtol=0., atol=1e-12):
            raise ValueError('Lifted selection symmetry failed.')
    canonical = (mask > 0.) & (mesh.xyz[:, 0] < 0.) & (mesh.xyz[:, 1] > 0.)
    ids = np.flatnonzero(canonical)
    normals = selected_normals(mesh.xyz, mesh.faces, ids)
    np.savez(root/'projection_request.npz', vertex_ids=ids, xyz=mesh.xyz[ids],
        source_normals=normals, weight=mask[ids])
    np.savez(root/'selection.npz', full_mask=mask, coarse_mask=coarse_mask)
    hashes = code_hashes(source)
    snapshot(root, hashes)
    request = dict(date='2026-10-14', timezone='Asia/Seoul',
        basis_commit='78d6f3fefcb61f16253b53b886853fa56a257350',
        source=str(SOURCE), source_generation_sha256=previous.SOURCE_RECEIPT_SHA256,
        source_control_sha256=source['control_file_sha256'],
        source_native_path=str(SOURCE/'geometry.npz'), source_native_sha256=digest(SOURCE/'geometry.npz'),
        height=height, request_npz=str(root/'projection_request.npz'),
        request_npz_sha256=digest(root/'projection_request.npz'),
        selection_npz_sha256=digest(root/'selection.npz'),
        max_distance=height*RECIPE['maximum_projection_distance_height_fraction'],
        voxel_size=height*RECIPE['voxel_size_height_fraction'],
        target_smooth_factor=RECIPE['target_smooth_factor'], target_smooth_iterations=RECIPE['target_smooth_iterations'],
        selected_canonical_controls=len(ids), selected_full_controls=int(np.count_nonzero(mask)),
        recipe=RECIPE, selected_region=region, hierarchy=hierarchy,
        geometry_code_sha256=hashes, prepare_elapsed_seconds=time.perf_counter()-started)
    write(root/'projection_request.json', request)
    write(root/'RUN_REQUEST.json', request)
    write(root/'RECIPE.json', request)
    print('PREPARED', len(ids), 'canonical controls', flush=True)


def relax_delta(mesh, ids, delta, eligible):
    faces = incident_faces(mesh.faces, ids, len(mesh.xyz))
    edges = np.stack([faces, np.roll(faces, -1, axis=1)], axis=-1).reshape(-1, 2)
    edges.sort(axis=1)
    edges = np.unique(edges, axis=0)
    # Both ends may be outside; those zero vectors still count in the source graph.
    lookup = np.full(len(mesh.xyz), -1, np.int32)
    lookup[ids] = np.arange(len(ids), dtype=np.int32)
    a, b = lookup[edges[:, 0]], lookup[edges[:, 1]]
    valid_a, valid_b = a >= 0, b >= 0
    degree = np.bincount(np.concatenate([a[valid_a], b[valid_b]]), minlength=len(ids))
    if np.any(degree == 0):
        raise ValueError('Selected controls have no source neighbors.')
    for iteration in range(RECIPE['delta_relaxation_iterations']):
        total = np.zeros_like(delta)
        both = valid_a & valid_b
        np.add.at(total, a[both], delta[b[both]])
        np.add.at(total, b[both], delta[a[both]])
        delta = (1.-RECIPE['delta_relaxation_factor'])*delta + RECIPE['delta_relaxation_factor']*total/degree[:, None]
        delta[~eligible] = 0.
    return delta


def apply(root):
    started = time.perf_counter()
    request = json.loads((root/'projection_request.json').read_text(encoding='utf-8'))
    if (root/'SUMMARY.json').exists():
        raise FileExistsError('Earlier output preserved.')
    if digest(root/'projection_request.npz') != request['request_npz_sha256'] or digest(root/'selection.npz') != request['selection_npz_sha256']:
        raise ValueError('Prepared source selection changed.')
    target_receipt = json.loads((root/'TARGET_RECEIPT.json').read_text(encoding='utf-8'))
    if digest(root/'projection_result.npz') != target_receipt['projection_file_sha256']:
        raise ValueError('Actual closest-point projection hash changed.')
    if (target_receipt['input_hashes']['request_npz_sha256'] != request['request_npz_sha256'] or
            target_receipt['input_hashes']['source_native_sha256'] != request['source_native_sha256'] or
            digest(root/'target_geometry.npz') != target_receipt['target_file_sha256']):
        raise ValueError('Target receipt lost actual source/request binding.')
    mesh, chart, pairs, coords, height, source, ancestry, frame = previous.load()
    if code_hashes(source) != request['geometry_code_sha256']:
        raise ValueError('Prepared geometry code changed.')
    with np.load(root/'selection.npz', allow_pickle=False) as data:
        mask, coarse_mask = data['full_mask'], data['coarse_mask']
    with np.load(root/'projection_request.npz', allow_pickle=False) as data:
        ids, selected_xyz = data['vertex_ids'], data['xyz']
    with np.load(root/'projection_result.npz', allow_pickle=False) as data:
        projected, eligible = data['points'].astype(float), data['eligible'].astype(bool)
        distances = data['distance']
        projection_ids = data['vertex_ids']
    if not np.array_equal(ids, projection_ids) or not np.array_equal(selected_xyz, mesh.xyz[ids]):
        raise ValueError('Projection lost actual source-ID association.')
    if not np.any(eligible):
        raise ValueError('No eligible actual projection; no output claimed.')
    if not np.isfinite(projected).all() or np.any(distances[eligible] > request['max_distance']*(1.+1e-6)):
        raise ValueError('Invalid bounded target projection.')
    local_delta = (projected-selected_xyz)*RECIPE['projection_blend']*mask[ids, None]
    local_delta[~eligible] = 0.
    local_delta = relax_delta(mesh, ids, local_delta, eligible)
    delta = np.zeros_like(mesh.xyz)
    delta[ids] = local_delta
    px, py = pairs['mirror_x_vertex_pairs'], pairs['mirror_y_vertex_pairs']
    delta[px[ids]] = local_delta*np.array([-1., 1., 1.])
    delta[py[ids]] = local_delta*np.array([1., -1., 1.])
    delta[px[py[ids]]] = local_delta*np.array([-1., -1., 1.])
    reflection = dict(X=px, Y=py)
    delta, representative, fixed_x, fixed_y = field._transport(delta, np.arange(len(mesh.xyz)), reflection)
    mask = mask[representative].copy()
    delta[mask == 0.] = 0.
    out_xyz = mesh.xyz+delta
    out_xyz[mask == 0.] = mesh.xyz[mask == 0.]
    actual_norm = np.linalg.norm(out_xyz-mesh.xyz, axis=1)
    bound = RECIPE['projection_blend']*request['max_distance']
    if actual_norm.max() > bound*(1.+1e-6) or not np.array_equal(out_xyz[mask == 0.], mesh.xyz[mask == 0.]):
        raise ValueError('Actual bounded/exact-preservation constraint failed.')
    def radial(x):
        r = np.linalg.norm(x[mask > 0., :2], axis=1)
        return dict(count=len(r), minimum=float(r.min()), maximum=float(r.max()), quantiles=np.quantile(r, [0.,.5,.9,.99,1.]).tolist())
    metadata = dict(recipe=RECIPE, physical_height=height, displacement_bound=bound,
        selected_full_control_count=int(np.count_nonzero(mask)),
        queried_canonical_control_count=len(ids), eligible_canonical_control_count=int(eligible.sum()),
        changed_actual_control_count=int(np.count_nonzero(actual_norm)),
        maximum_actual_displacement=float(actual_norm.max()),
        selected_radius_before=radial(mesh.xyz), selected_radius_after=radial(out_xyz),
        target_receipt_sha256=digest(root/'TARGET_RECEIPT.json'),
        target_receipt=target_receipt, full_mask_sha256=previous.prior.array_hash(mask),
        source_geometry_averaged=False, target_geometry_averaged=True,
        original_topology_preserved=True, actual_final_mesh_topological_fusion=False,
        G1_continuity='NOT_CERTIFIED', self_intersection='NOT_CHECKED', visual_status='PENDING_ACTUAL_RENDER')
    out = ArrayMesh(out_xyz, mesh.faces.copy(), mesh.classes.copy(), mesh.rest.copy(), mesh.anchors.copy(), 7)
    out.surface = 'mean'
    state = dict(full_mask=mask, coarse_mask=coarse_mask, displacement_vector=delta,
        mirror_x_vertex_pairs=px, mirror_y_vertex_pairs=py,
        mirror_x_face_pairs=pairs['mirror_x_face_pairs'], mirror_y_face_pairs=pairs['mirror_y_face_pairs'])
    symmetry = loader.actual_symmetry(out, state)
    context = dict(candidate='VOLUME_JUNCTION_TARGET', input_case='SPAN', source=str(SOURCE), source_generation=7,
        source_control_sha256=source['control_file_sha256'], source_generation_json_sha256=previous.SOURCE_RECEIPT_SHA256,
        parent_stage=str(SOURCE), parent_control_sha256=source['control_file_sha256'],
        parent_generation_json_sha256=previous.SOURCE_RECEIPT_SHA256,
        geometry_code_sha256=request['geometry_code_sha256'], added_CC_passes=0, added_topology_events=0,
        added_normal_field_passes=0, cumulative_normal_field_passes=source['cumulative_normal_field_passes'],
        added_mandelbulb_evaluations=0, source_geometry_averaged=False,
        source_geometry_parametrically_rebuilt=False, source_geometry_envelope_projected=True,
        operator_metadata=metadata, selected_region=request['selected_region'], hierarchy=request['hierarchy'],
        frame_ancestry=ancestry, symmetry=symmetry, methodology_scope=RECIPE['interpretation'])
    del mesh, coords, pairs, reflection
    gc.collect()
    folder = root/'VOLUME_JUNCTION_TARGET/SPAN/G07'
    print('SAVE projected original G7; required full mesh checks once', flush=True)
    record = core.save(folder, out, chart, context, state)
    previous.base.checked(SOURCE, source, (('control_quad.npz', 'control_file_sha256'), ('evidence.npz', 'evidence_file_sha256')))
    if digest(SOURCE/'generation.json') != previous.SOURCE_RECEIPT_SHA256:
        raise ValueError('Original source changed.')
    write(root/'SUMMARY.json', dict(date='2026-10-14', source=str(SOURCE),
        candidate='VOLUME_JUNCTION_TARGET', folder=str(folder), subdivision_generation=7,
        control_vertices=len(out.xyz), control_quads=len(out.faces), native_triangles=record['native_triangles'],
        generation_json_sha256=digest(folder/'generation.json'), checks=record['checks'], symmetry=symmetry,
        operator_metadata=metadata, geometry_code_sha256=request['geometry_code_sha256'],
        elapsed_apply_seconds=time.perf_counter()-started, actual_generation_process_memory=previous.process_memory(),
        visual_success='PENDING_ACTUAL_MATCHED_RENDER_REVIEW'))
    print('DONE bounded local envelope projection', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'apply'])
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    {'prepare':prepare, 'apply':apply}[args.stage](args.root.resolve())


if __name__ == '__main__':
    main()
