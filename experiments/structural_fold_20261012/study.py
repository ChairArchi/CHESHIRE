"""Bounded solid cut / reflect / union study; one requested operation per call.

These R steps are structural Boolean edits, not subdivision generations or an
origami solver. No welding, repair, remeshing, smoothing, snapping or tag reuse.
"""
from pathlib import Path
import argparse
import json
import shutil
import sys

DEPS = Path('C:/Users/USER/CHESHIRE/scratch/grotesque_gate_20261010/deps')
sys.path.insert(0, str(DEPS))
import numpy as np
import trimesh
import manifold3d as md

ROOT = Path('E:/CHESHIRE_DATA/structural_fold_20261012')
SOURCE = Path('E:/CHESHIRE_DATA/fold_transfer_20261012/inputs/SPAN/G00/geometry.npz')
AREA_THRESHOLD = 1e-12
PLANES = {
    'LONGITUDINAL': [((1., 0., .22), (.08, 0., 5.)),
        ((.3, 1., -.16), (0., .06, 5.)), ((1., -.45, .10), (.05, 0., 5.))],
    'CROSS_FORK': [((-.30, 0., 1.), (0., 0., 5.)),
        ((0., -.24, 1.), (0., 0., 5.)), ((-.20, -.15, 1.), (0., 0., 5.))],
}


def solid(mesh):
    # Same Mesh64/status contract as the preserved gateflow.geometry wrapper.
    result = md.Manifold(md.Mesh64(np.asarray(mesh.vertices, dtype=np.float64),
        np.asarray(mesh.faces, dtype=np.uint64)))
    if result.status() != md.Error.NoError:
        raise ValueError('Manifold rejected surface: '+str(result.status()))
    return result


def from_solid(result):
    if result.status() != md.Error.NoError or result.is_empty():
        raise ValueError('Boolean failed or empty: '+str(result.status()))
    raw = result.to_mesh64()
    return trimesh.Trimesh(np.array(raw.vert_properties)[:, :3],
        np.array(raw.tri_verts), process=False)


def load(folder):
    with np.load(folder/'geometry.npz') as data:
        return trimesh.Trimesh(data['xyz'], data['faces'], process=False)


def require_new(folder):
    if folder.exists():
        raise FileExistsError('Existing result preserved: '+str(folder))


def inspect(mesh, result):
    edges, counts = np.unique(np.sort(mesh.edges, axis=1), axis=0, return_counts=True)
    components = trimesh.graph.connected_components(mesh.face_adjacency,
        nodes=np.arange(len(mesh.faces)))
    areas = mesh.area_faces
    valid_solid = result.status() == md.Error.NoError and not result.is_empty()
    parts = result.decompose() if valid_solid else []
    info = dict(vertices=len(mesh.vertices), triangles=len(mesh.faces),
        finite=bool(np.isfinite(mesh.vertices).all()),
        watertight=bool(mesh.is_watertight), winding_consistent=bool(mesh.is_winding_consistent),
        boundary_edges=int((counts == 1).sum()), nonmanifold_edges=int((counts > 2).sum()),
        zero_area_faces=int((areas == 0).sum()),
        area_under_1e_12=int((areas <= AREA_THRESHOLD).sum()),
        min_face_area=float(areas.min()) if len(areas) else None,
        components=len(components), manifold_components=len(parts),
        genus_by_component=[int(p.genus()) for p in parts],
        component_volumes=[float(p.volume()) for p in parts],
        euler_number=int(mesh.euler_number), volume=float(mesh.volume),
        bounds=mesh.bounds.tolist(), manifold_status=str(result.status()),
        self_intersection='NOT_CHECKED', thickness_structure_fabrication='NOT_CHECKED')
    passed = (valid_solid and len(mesh.faces) > 0 and info['finite'] and info['watertight']
        and info['winding_consistent'] and info['components'] == 1
        and info['manifold_components'] == 1 and info['nonmanifold_edges'] == 0
        and info['area_under_1e_12'] == 0 and info['volume'] > 0)
    return info, passed


def save(folder, mesh, result, meta, *, original_geometry=None, prior_failure=False):
    require_new(folder)
    info, passed = inspect(mesh, result)
    folder.mkdir(parents=True)
    if original_geometry is None:
        np.savez_compressed(folder/'geometry.npz', xyz=np.asarray(mesh.vertices),
            faces=np.asarray(mesh.faces, dtype=np.int64))
    else:
        shutil.copy2(original_geometry, folder/'geometry.npz')
    mesh.export(folder/'column.ply')
    record = dict(meta, checks=info, quick_integrity='PASS' if passed else 'FAIL',
        all_components_retained=True, area_failure_threshold=AREA_THRESHOLD,
        earlier_intermediate_failed=bool(prior_failure),
        no_quad_checkpoint='Boolean changes topology and invalidates previous chart/classes/tags.',
        symmetry_validation_scope='Constructive XY reflection only where stated; surface-distance verification is separate. Boolean vertex/triangle sets need not pair identically.')
    (folder/'generation.json').write_text(json.dumps(record, indent=2), encoding='utf8')
    shutil.copy2(__file__, folder/'study.py')
    print(json.dumps(dict(output=str(folder), quick_integrity=record['quick_integrity'], checks=info)), flush=True)
    # A fully saved intermediate has its own verdict. The current solid is
    # assessed independently after the explicitly recorded Boolean operation.
    return passed


def failed(folder, meta, result):
    # No mesh is invented when the backend does not provide a valid solid.
    require_new(folder)
    folder.mkdir(parents=True)
    meta = dict(meta, quick_integrity='FAIL', manifold_status=str(result.status()),
        empty=bool(result.is_empty()), geometry_saved=False, all_components_retained=True,
        self_intersection='NOT_CHECKED', note='No valid nonempty backend surface to export; no repair attempted.')
    (folder/'generation.json').write_text(json.dumps(meta, indent=2), encoding='utf8')
    shutil.copy2(__file__, folder/'study.py')
    print(json.dumps(dict(output=str(folder), quick_integrity='FAIL', manifold_status=str(result.status()))), flush=True)


def prepare():
    source_folder, seed_folder = ROOT/'SOURCE'/'G00', ROOT/'SEED'/'G00'
    require_new(source_folder)
    require_new(seed_folder)
    with np.load(SOURCE) as data:
        mesh = trimesh.Trimesh(data['xyz'], data['faces'], process=False)
    original = solid(mesh)
    source_ok = save(source_folder, mesh, original, dict(candidate='SOURCE', label='G00',
        source=str(SOURCE), operation='Unchanged source geometry copied byte-for-byte'), original_geometry=SOURCE)
    if not source_ok:
        return
    cutter = md.Manifold.cylinder(14., .22, .22, 16, False).translate((0., 0., -2.))
    seed = md.Manifold.batch_boolean([original, cutter], md.OpType.Subtract)
    meta = dict(candidate='SEED', label='G00', parent=str(source_folder),
        source=str(SOURCE), operation='Subtract one central vertical cylinder; no other preparation',
        cylinder=dict(radius=.22, height=14., bottom_z=-2., circular_segments=16),
        cavity_claim='Actual genus/components recorded; intended through-hole is not assumed.')
    if seed.status() != md.Error.NoError or seed.is_empty():
        failed(seed_folder, meta, seed)
    else:
        save(seed_folder, from_solid(seed), seed, meta)


def step(case, number):
    parent = ROOT/'SEED'/'G00' if number == 1 else ROOT/case/f'R{number-1:02}'
    folder = ROOT/case/f'R{number:02}'
    require_new(folder)
    previous = json.loads((parent/'generation.json').read_text(encoding='utf8'))
    if previous['quick_integrity'] != 'PASS':
        raise ValueError('Failed/disconnected previous result preserved; next step stopped: '+str(parent))
    original = solid(load(parent))
    raw_normal, point = PLANES[case][number-1]
    normal = np.asarray(raw_normal, dtype=float)
    normal /= np.linalg.norm(normal)
    offset = float(normal@np.asarray(point))
    positive = case == 'CROSS_FORK'
    half = original.trim_by_plane(normal if positive else -normal, offset if positive else -offset)
    matrix = np.column_stack((np.eye(3)-2*np.outer(normal, normal), 2*offset*normal))
    meta = dict(candidate=case, label=f'R{number:02}', step=number, parent=str(parent),
        source_seed=str(ROOT/'SEED'/'G00'), operation='Plane discard, offset-plane reflection, Boolean union, canonical-quarter XY reconstruction',
        plane=dict(raw_normal=raw_normal, unit_normal=normal.tolist(), point=point, offset=offset,
            kept_half='positive' if positive else 'negative'), reflection_matrix=matrix.tolist(),
        subdivision_passes=0, geometry_smoothing=False, legacy_tags_reused=False,
        cavity_claim='No assumed cavity or genus improvement; all components are retained.')
    if half.status() != md.Error.NoError or half.is_empty():
        failed(folder, dict(meta, failed_operation='plane_cut'), half)
        return
    reflected = half.transform(matrix)
    raw = md.Manifold.batch_boolean([half, reflected], md.OpType.Add)
    if raw.status() != md.Error.NoError or raw.is_empty():
        failed(folder, dict(meta, failed_operation='offset_reflection_union'), raw)
        return
    raw_folder = ROOT/case/(f'R{number:02}_RAW_PRE_XY')
    require_new(raw_folder)
    raw_ok = save(raw_folder, from_solid(raw), raw, dict(meta,
        label=f'R{number:02}_RAW_PRE_XY', operation='Plane discard, offset-plane reflection and Boolean union; before XY reconstruction'))
    quarter = raw.trim_by_plane((1., 0., 0.), 0.).trim_by_plane((0., 1., 0.), 0.)
    if quarter.status() != md.Error.NoError or quarter.is_empty():
        failed(folder, dict(meta, raw_pre_xy=str(raw_folder), failed_operation='canonical_quarter_cut'), quarter)
        return
    xy = quarter.mirror((1., 0., 0.)).mirror((0., 1., 0.))
    output = md.Manifold.batch_boolean([quarter, quarter.mirror((1., 0., 0.)),
        quarter.mirror((0., 1., 0.)), xy], md.OpType.Add)
    meta.update(raw_pre_xy=str(raw_folder), raw_pre_xy_quick_integrity='PASS' if raw_ok else 'FAIL',
        symmetry_construction='Trim X>=0 and Y>=0, union canonical quarter and its three exact plane reflections; no point averaging')
    if output.status() != md.Error.NoError or output.is_empty():
        failed(folder, dict(meta, failed_operation='XY_reflection_union'), output)
    else:
        save(folder, from_solid(output), output, meta, prior_failure=not raw_ok)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--case', choices=tuple(PLANES))
    parser.add_argument('--step', type=int, choices=(1, 2, 3))
    args = parser.parse_args()
    if args.prepare and args.step is not None:
        parser.error('--prepare does not accept --step')
    if args.case and args.step is None:
        parser.error('--case requires --step')
    prepare() if args.prepare else step(args.case, args.step)
