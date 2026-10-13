"""Two bounded local ornament additions; the original native G7 is read-only."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/local_ornament_comparison_20261014/trial01')
SOURCE = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07')
SELECTION = Path('E:/CHESHIRE_DATA/experiments/volume_junction_target_20261014/trial01')
COARSE = Path('E:/CHESHIRE_DATA/experiments/sidewall_fan_growth_20261013/trial01/SIDEWALL_FAN/SPAN/G04/control_quad.npz')
EXPECTED = {'generation.json': 'c7452dc63998c61783215f0bb23434ea5e9b223d89fcd836d1a4081907ab2cf5',
            'control_quad.npz': '0d966671a028cd56f49d0c5d1e626207652e789d281a9fa69475c3492f95fdc6',
            'geometry.npz': '98a88c6727045e0a5aad67df6cd6295de6c14655a78ac0ca95812a5f37841e91'}
VARIANTS = ('MANDELBULB', 'LEAF_CLUSTER')
SIGNS = ((1, 1, 1), (-1, 1, 1), (1, -1, 1), (-1, -1, 1))


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def array_hash(a):
    return hashlib.sha256(memoryview(np.ascontiguousarray(a)).cast('B')).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def inside(point, xyz, faces):
    """Parity against actual closed prototype triangles, fixed non-axis ray."""
    direction = np.array([.829, .371, .419])
    direction /= np.linalg.norm(direction)
    a, b, c = xyz[faces[:, 0]], xyz[faces[:, 1]], xyz[faces[:, 2]]
    e1, e2 = b-a, c-a
    h = np.cross(direction, e2)
    det = np.einsum('ij,ij->i', e1, h)
    valid = abs(det) > 1e-14
    inv = np.divide(1., det, out=np.zeros_like(det), where=valid)
    s = point-a
    u = inv * np.einsum('ij,ij->i', s, h)
    q = np.cross(s, e1)
    v = inv * (q @ direction)
    t = inv * np.einsum('ij,ij->i', e2, q)
    hit = t[valid & (u > 1e-10) & (v > 1e-10) & (u+v < 1-1e-10) & (t > 1e-10)]
    hit = np.sort(hit)
    count = int(np.count_nonzero(np.r_[True, np.diff(hit) > 1e-8])) if len(hit) else 0
    return bool(count % 2), count


def interior_root(xyz, faces):
    """Find an actual interior point on the fixed z=.22 attachment slice."""
    level = .22
    tri = xyz[faces]
    ids = np.flatnonzero((tri[:, :, 2].min(1) < level) & (tri[:, :, 2].max(1) > level))
    candidates = []
    for index in ids:
        t = tri[index]
        points = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            if (t[a, 2]-level) * (t[b, 2]-level) < 0:
                points.append(t[a] + (t[b]-t[a]) * ((level-t[a, 2])/(t[b, 2]-t[a, 2])))
        if len(points) != 2:
            continue
        normal = np.cross(t[1]-t[0], t[2]-t[0])
        normal[2] = 0
        length = np.linalg.norm(normal)
        if length < 1e-12:
            continue
        point = (points[0]+points[1])*.5 - normal/length*.0005
        candidates.append((float(point[:2] @ point[:2]), point, int(index)))
    for _, point, index in sorted(candidates, key=lambda item: item[0])[:200]:
        ok, crossings = inside(point, xyz, faces)
        if ok:
            return point, dict(slice_z=level, actual_triangle_id=index,
                inward_horizontal_offset=.0005, positive_ray_crossings=crossings,
                actual_closed_triangle_parity_inside=True,
                scope='Actual source vertex is placed strictly inside added prototype. Overlap is verified; no Boolean union or tangent continuity is claimed.')
    raise ValueError('No actual interior attachment point found on fixed slice.')


def placement():
    for name, expected in EXPECTED.items():
        if digest(SOURCE/name) != expected:
            raise ValueError('Original source changed: '+name)
    if digest(SELECTION/'selection.npz') != '7bbfb7cdb50b3fad320451dc096b23f8f662c7a09a425324949cba39396584ab':
        raise ValueError('Original marked selection changed.')
    if digest(SELECTION/'projection_request.npz') != 'e5a80eee35ace9fca07029c0e2e249f3571133e639b01d7cd38fe5aa038208f2':
        raise ValueError('Saved original source normals changed.')
    with np.load(SOURCE/'control_quad.npz', allow_pickle=False) as data:
        xyz, chart = data['xyz'], data['chart']
    with np.load(SELECTION/'selection.npz', allow_pickle=False) as data:
        mask = data['coarse_mask']
    with np.load(COARSE, allow_pickle=False) as data:
        faces = data['faces']
    with np.load(SELECTION/'projection_request.npz', allow_pickle=False) as data:
        ids, normals = data['vertex_ids'], data['source_normals']
        if not np.array_equal(xyz[ids], data['xyz']):
            raise ValueError('Saved selected coordinates are not actual original G7.')
    selected = np.flatnonzero((mask > 0) & (xyz[:len(mask), 0] < 0) & (xyz[:len(mask), 1] > 0))
    lookup = np.full(len(mask), -1, np.int32)
    lookup[selected] = np.arange(len(selected))
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 3]], faces[:, [3, 0]]])
    edges = lookup[edges]
    edges = edges[(edges >= 0).all(1)]
    n, labels = connected_components(coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(len(selected), len(selected))), directed=False)
    components = sorted([selected[labels == k] for k in range(n)], key=len, reverse=True)
    if [len(c) for c in components] != [406, 54, 19, 16, 1, 1]:
        raise ValueError('Actual marked coarse components differ.')
    normal_index = np.full(len(xyz), -1, np.int32)
    normal_index[ids] = np.arange(len(ids))
    anchors = []
    for k, component in enumerate(components[:4]):
        theta = np.arctan2(abs(chart[component, 2]), abs(chart[component, 1]))
        groups = [component[theta < .60], component[(theta >= .60) & (theta < .95)], component[theta >= .95]] if k == 0 else [component]
        for group in groups:
            view = np.array([-18., 28., 12.])-xyz[group]
            view /= np.linalg.norm(view, axis=1)[:, None]
            facing = np.einsum('ij,ij->i', normals[normal_index[group]], view)
            group = group[(mask[group] >= min(.6, float(mask[group].max()))) & (facing > .3)]
            if not len(group):
                raise ValueError('No original visible attachment point.')
            vertex = int(group[np.argmax(np.linalg.norm(xyz[group, :2], axis=1))])
            z = normals[normal_index[vertex]].copy()
            z /= np.linalg.norm(z)
            x = np.array([0., 0., 1.])-z*z[2]
            x /= np.linalg.norm(x)
            y = np.cross(z, x)
            frame = np.column_stack([x, y, z])
            if not np.allclose(frame.T @ frame, np.eye(3), atol=1e-12) or np.linalg.det(frame) < .999999:
                raise ValueError('Invalid actual source frame.')
            anchors.append(dict(source_control_vertex_id=vertex, source_xyz=xyz[vertex].tolist(),
                source_outward_normal=z.tolist(), frame_columns=frame.tolist(),
                marked_component=k, marked_component_coarse_vertices=len(component),
                source_mask_weight=float(mask[vertex])))
    height = 9.735842284057451
    return dict(date='2026-10-14', source=str(SOURCE), source_generation=7,
        source_hashes=EXPECTED, marked_selection=str(SELECTION/'selection.npz'),
        marked_selection_sha256=digest(SELECTION/'selection.npz'),
        original_normal_request=str(SELECTION/'projection_request.npz'),
        original_normal_request_sha256=digest(SELECTION/'projection_request.npz'),
        reused_scope='Only original source vertex IDs/coordinates/normals and marked mask reused. No rejected volume geometry is loaded.',
        coarse_topology=str(COARSE), coarse_topology_sha256=digest(COARSE),
        anchor_rule='Three theta bands of main marked component plus three other non-singleton components; maximal actual radius among mask>=.6 and original close-camera facing>.3.',
        canonical_anchors=anchors, reflection_signs=SIGNS, prototype_copies=24,
        frame_rule='Local Z is original area-weighted outward normal; local X is global up projected into its tangent plane.',
        physical_height=height, footprint_radius=height*.004, prototype_normal_height=height*.006,
        root_embedding_fraction=.22, visible_normal_height=height*.006*.78,
        body_geometry_changed=False, added_CC_passes=0, added_global_smoothing=0)


def assemble(root, name, common):
    path = root/'prototypes'/f'{name}.npz'
    with np.load(path, allow_pickle=False) as data:
        xyz, faces = np.asarray(data['xyz'], np.float64), np.asarray(data['faces'], np.int32)
    interior, contact = interior_root(xyz, faces)
    radial = float(np.linalg.norm(xyz[:, :2]-interior[:2], axis=1).max())
    scale = np.array([common['footprint_radius']/radial]*2 + [common['prototype_normal_height']])
    local = (xyz-interior)*scale
    vertices, triangles = [], []
    for anchor in common['canonical_anchors']:
        original = local @ np.asarray(anchor['frame_columns']).T + anchor['source_xyz']
        for sign in SIGNS:
            sign = np.asarray(sign)
            vertices.append(original*sign)
            winding = faces[:, [0, 2, 1]] if sign.prod() < 0 else faces
            triangles.append(winding + (len(vertices)-1)*len(xyz))
    out_xyz, out_faces = np.concatenate(vertices), np.concatenate(triangles)
    if not np.isfinite(out_xyz).all():
        raise ValueError('Nonfinite addition.')
    smallest = float('inf')
    for start in range(0, len(out_faces), 500000):
        t = out_xyz[out_faces[start:start+500000]]
        smallest = min(smallest, float(np.linalg.norm(np.cross(t[:, 1]-t[:, 0], t[:, 2]-t[:, 0]), axis=1).min()))
    if smallest <= 0:
        raise ValueError('Degenerate added triangle.')
    residual = 0.
    nv = len(xyz)
    for k in range(6):
        original = out_xyz[k*4*nv:(k*4+1)*nv]
        for j, sign in enumerate(SIGNS):
            residual = max(residual, float(abs(out_xyz[(k*4+j)*nv:(k*4+j+1)*nv]-original*np.asarray(sign)).max()))
    if residual != 0:
        raise ValueError('Actual constructed reflected addition differs.')
    folder = root/name
    folder.mkdir(exist_ok=False)
    target = folder/'geometry.npz'
    np.savez_compressed(target, xyz=out_xyz, faces=out_faces)
    return dict(geometry=str(target), geometry_sha256=digest(target),
        xyz_sha256=array_hash(out_xyz), faces_sha256=array_hash(out_faces),
        vertices=len(out_xyz), triangles=len(out_faces), prototype=str(path),
        prototype_sha256=digest(path), prototype_vertices=len(xyz), prototype_triangles=len(faces),
        prototype_interior_root=interior.tolist(), root_contact=contact,
        local_scale=scale.tolist(), min_triangle_double_area=smallest,
        actual_constructive_XY_symmetry_residual=residual,
        local_normal_extent=[float(local[:, 2].min()), float(local[:, 2].max())],
        actual_footprint_radius=float(np.linalg.norm(local[:, :2], axis=1).max()),
        contact_scope='24 actual original body vertices lie inside their corresponding closed ornament prototype by invertible placement. Independent overlapping meshes; no Boolean fusion, global collision repair or tangent continuity certification.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    root = parser.parse_args().root.resolve()
    if (root/'RECEIPT.json').exists() or (root/'PLACEMENT.json').exists():
        raise FileExistsError('Saved trial is immutable; use a new output root.')
    started = time.perf_counter()
    snapshots = {}
    for name in ('run.py', 'mandel_prototype.py', 'leaf_prototype.py'):
        path = HERE/name
        target = root/'source_snapshot'/HERE.name/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        snapshots[name] = dict(source=str(path), snapshot=str(target), sha256=digest(path))
    print('LOAD immutable original G7 / same marked source anchors', flush=True)
    common = placement()
    write(root/'PLACEMENT.json', common)
    variants = {}
    for name in VARIANTS:
        print('ASSEMBLE '+name+' at 6 roots x 4 mirror copies', flush=True)
        variants[name] = assemble(root, name, common)
    for name, expected in EXPECTED.items():
        if digest(SOURCE/name) != expected:
            raise ValueError('Source file changed during trial.')
    for record in snapshots.values():
        if digest(record['source']) != record['sha256'] or digest(record['snapshot']) != record['sha256']:
            raise ValueError('Executed source snapshot changed.')
    write(root/'RECEIPT.json', dict(date='2026-10-14', timezone='Asia/Seoul',
        authorization='Latest explicit user instruction: 시험해보자 바로. Two bounded tests from preceding method comparison.',
        basis_commit='f88e299ce2f66744f6e2db83a106498c090de8fe',
        source_native_path=str(SOURCE/'geometry.npz'), source_native_geometry_sha256=EXPECTED['geometry.npz'],
        source_generation=7, source_hashes_after=EXPECTED,
        placement_sha256=digest(root/'PLACEMENT.json'), variants=variants,
        body_geometry_changed=False, body_reconstructed=False, added_CC_passes=0,
        prototype_copies_per_variant=24, source_snapshots=snapshots,
        seconds=time.perf_counter()-started,
        scope='Original G7 plus independent local ornament meshes only. Two prototypes, one placement recipe, no parameter sweep. Visual success requires matched rendered review.'))
    print('SAVED two actual additions; original files unchanged', flush=True)


if __name__ == '__main__':
    main()
