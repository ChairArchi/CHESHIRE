"""One actual closed three-tip sculpted leaf prototype, without a body edit.

Three thin closed lanceolate leaves overlap at the same finite z=0 root cap.
They are separate closed shells with overlapping roots, not a Boolean union.
Z is the main growth axis, X the leaf width/fan axis, and Y the thickness/rib
axis. A small turning tip is confined to the final part of each leaf.
"""
from pathlib import Path
import argparse
import hashlib
import json

import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/local_ornament_comparison_20261014/trial01')
RECIPE = dict(
    schema='CHESHIRE_AUTHORED_THREE_TIP_LEAF_PROTOTYPE_V1', date='2026-10-14',
    leaf_count=3, longitudinal_rings_per_leaf=96, angular_samples_per_ring=64,
    root_width_halfspan=.035, root_thickness_halfspan=.009,
    body_thickness_halfspan=.012,
    leaves=[
        dict(name='CENTRAL', height=1., width_halfspan=.205, fan_x=0., bend_y=.065,
             tip_start=.79, tip_turn_radians=1.05, rib_height=.045),
        dict(name='LEFT', height=.82, width_halfspan=.160, fan_x=-.255, bend_y=-.035,
             tip_start=.77, tip_turn_radians=-.90, rib_height=.033),
        dict(name='RIGHT', height=.86, width_halfspan=.165, fan_x=.270, bend_y=-.020,
             tip_start=.77, tip_turn_radians=-.95, rib_height=.034),
    ],
    centreline_body='x=fan_x*smoothstep(t); y=bend_y*smoothstep(t); z=height*t until tip_start',
    centreline_tip='Tangent-continuous circular YZ tip arc; arc length=(1-tip_start)*height; turn=tip_turn_radians; x fan continues smoothly.',
    width='root_width*(1-t)^2 + width_halfspan*sin(pi*t)^.85*(.88+.12*cos(pi*t)); multiplied by 1+.16*sin(6*pi*t)^2*sin(pi*t)^2',
    thickness='root_thickness*(1-t)+body_thickness*sin(pi*t)^.85',
    rib='rib_height*sin(pi*t)^1.1*(1-.35*t)*max(sin(angle),0)^6',
    edge_cupping='.018*sin(pi*t)^1.4*cos(angle)^4 along the local thickness axis',
    section='C(t)+width*cos(angle)*U(t)+(thickness*sin(angle)+rib+edge_cupping)*V(t)',
    frames='T=unit(actual centreline derivative), U=unit(Xaxis-T*dot(Xaxis,T)), V=T cross U',
    root_topology='One finite elliptical root ring and closed base fan for every leaf; identical roots overlap at z=0. Three separate closed shells are intentional.',
    tip_topology='Each final ring closes to one actual tip vertex; no open sheet or floating shard.',
    normalization='One uniform scale by actual global zmax; zmin remains zero. Assert actual maximum XY radius<=1.',
    body_modified=False, Tissue_used=False, AI_image_used=False,
    interpretation='One authored acanthus-like leaf cluster prototype; no reference-exact botanical reconstruction, collision certificate, or established aesthetic success.',
)


def _unit(value):
    value = np.asarray(value, float)
    return value/np.maximum(np.linalg.norm(value, axis=-1, keepdims=True), 1e-30)


def _smoothstep(t):
    return t*t*(3-2*t)


def _centreline(t, leaf):
    t = np.asarray(t, float)
    height, start = leaf['height'], leaf['tip_start']
    x = leaf['fan_x']*_smoothstep(t)
    dx = leaf['fan_x']*6*t*(1-t)
    y = leaf['bend_y']*_smoothstep(t)
    z = height*t
    dy = leaf['bend_y']*6*t*(1-t)
    dz = np.full_like(t, height)
    late = t > start
    if np.any(late):
        y0 = leaf['bend_y']*_smoothstep(start)
        theta0 = np.arctan2(leaf['bend_y']*6*start*(1-start), height)
        alpha = leaf['tip_turn_radians']
        length = (1-start)*height
        radius = length/alpha
        s = (t[late]-start)/(1-start)
        theta = theta0+alpha*s
        y[late] = y0+radius*(np.cos(theta0)-np.cos(theta))
        z[late] = height*start+radius*(np.sin(theta)-np.sin(theta0))
        dy[late] = height*np.sin(theta)
        dz[late] = height*np.cos(theta)
    return np.column_stack([x, y, z]), np.column_stack([dx, dy, dz])


def _leaf(leaf):
    nr, na = RECIPE['longitudinal_rings_per_leaf'], RECIPE['angular_samples_per_ring']
    t = np.arange(nr, dtype=float)/nr
    angle = 2*np.pi*np.arange(na)/na
    centre, derivative = _centreline(t, leaf)
    tangent = _unit(derivative)
    width_axis = np.tile([1., 0., 0.], (nr, 1))
    width_axis -= tangent*tangent[:, 0, None]
    width_axis = _unit(width_axis)
    thickness_axis = np.cross(tangent, width_axis)
    sine = np.sin(np.pi*t)
    width = (RECIPE['root_width_halfspan']*(1-t)**2+
             leaf['width_halfspan']*sine**.85*(.88+.12*np.cos(np.pi*t)))
    width *= 1+.16*np.sin(6*np.pi*t)**2*sine**2
    thickness = RECIPE['root_thickness_halfspan']*(1-t)+RECIPE['body_thickness_halfspan']*sine**.85
    rib = leaf['rib_height']*sine**1.1*(1-.35*t)
    edge = .018*sine**1.4
    across = width[:, None]*np.cos(angle)[None, :]
    normal = (thickness[:, None]*np.sin(angle)[None, :]+
              rib[:, None]*np.maximum(np.sin(angle), 0.)[None, :]**6+
              edge[:, None]*np.cos(angle)[None, :]**4)
    xyz = (centre[:, None, :]+across[:, :, None]*width_axis[:, None, :]+
           normal[:, :, None]*thickness_axis[:, None, :]).reshape(-1, 3)
    root_id, tip_id = len(xyz), len(xyz)+1
    tip = _centreline(np.array([1.]), leaf)[0][0]
    xyz = np.concatenate([xyz, np.array([[0., 0., 0.], tip])])
    j = np.arange(na)
    k = (j+1)%na
    faces = []
    for ring in range(nr-1):
        a, b = ring*na+j, ring*na+k
        c, d = (ring+1)*na+k, (ring+1)*na+j
        faces.extend((np.column_stack([a, b, c]), np.column_stack([a, c, d])))
    faces.append(np.column_stack([np.full(na, root_id), k, j]))
    faces.append(np.column_stack([(nr-1)*na+j, (nr-1)*na+k, np.full(na, tip_id)]))
    return xyz, np.concatenate(faces).astype(np.int64), dict(
        name=leaf['name'], root_vertex_id=root_id, tip_vertex_id=tip_id,
        root_ring_vertex_ids=list(range(na)), tip_unscaled_xyz=tip.tolist())


def _hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def _check_leaf(xyz, faces):
    edges_directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges, inverse, count = np.unique(np.sort(edges_directed, axis=1), axis=0,
                                     return_inverse=True, return_counts=True)
    signs = np.where(edges_directed[:, 0] < edges_directed[:, 1], 1, -1)
    orientation = np.bincount(inverse, weights=signs, minlength=len(edges))
    points = xyz[faces]
    area = .5*np.linalg.norm(np.cross(points[:, 1]-points[:, 0], points[:, 2]-points[:, 0]), axis=1)
    volume = float(np.einsum('ij,ij->i', points[:, 0], np.cross(points[:, 1], points[:, 2])).sum()/6)
    result = dict(finite=bool(np.isfinite(xyz).all()), closed_two_face_edges=bool(np.all(count == 2)),
        consistently_oriented=bool(np.all(orientation == 0)), Euler=int(len(xyz)-len(edges)+len(faces)),
        no_orphan_vertices=bool(len(np.unique(faces)) == len(xyz)),
        minimum_triangle_area=float(area.min()), signed_volume=volume)
    result['passed'] = bool(result['finite'] and result['closed_two_face_edges'] and
        result['consistently_oriented'] and result['Euler'] == 2 and result['no_orphan_vertices'] and
        result['minimum_triangle_area'] > 1e-12 and volume > 0)
    if not result['passed']:
        raise ValueError('Closed leaf integrity failed; no geometry repair or retuning.')
    return result


def build_geometry():
    """Return actual normalized triangle geometry and its JSON-safe receipt."""
    vertices, triangles, records = [], [], []
    offset_v = offset_f = 0
    for leaf in RECIPE['leaves']:
        xyz, faces, record = _leaf(leaf)
        vertices.append(xyz); triangles.append(faces+offset_v)
        record.update(vertex_start=offset_v, vertex_count=len(xyz),
                      face_start=offset_f, face_count=len(faces))
        record['root_vertex_id'] += offset_v
        record['tip_vertex_id'] += offset_v
        record['root_ring_vertex_ids'] = (np.asarray(record['root_ring_vertex_ids'])+offset_v).tolist()
        records.append(record)
        offset_v += len(xyz); offset_f += len(faces)
    xyz, faces = np.concatenate(vertices), np.concatenate(triangles)
    raw_height = float(xyz[:, 2].max())
    if raw_height <= 0 or float(xyz[:, 2].min()) < -1e-12:
        raise ValueError('Authored source does not stay above its z=0 root plane.')
    xyz /= raw_height
    maximum_radius = float(np.linalg.norm(xyz[:, :2], axis=1).max())
    if maximum_radius > 1. or not np.isclose(xyz[:, 2].max(), 1., atol=1e-14):
        raise ValueError('Declared prototype normalization failed; no retuning.')
    for record in records:
        start, count = record['vertex_start'], record['vertex_count']
        fs, fc = record['face_start'], record['face_count']
        record['checks'] = _check_leaf(xyz[start:start+count], faces[fs:fs+fc]-start)
        record['root_xyz'] = xyz[record['root_vertex_id']].tolist()
        record['tip_xyz'] = xyz[record['tip_vertex_id']].tolist()
        if not np.all(xyz[record['root_ring_vertex_ids'], 2] == 0.):
            raise ValueError('A closed leaf root ring moved away from the common root plane.')
    return xyz, faces, dict(schema=RECIPE['schema'], recipe=RECIPE, leaves=records,
        vertices=len(xyz), triangles=len(faces), raw_height_uniform_normalizer=raw_height,
        actual_z_range=[float(xyz[:, 2].min()), float(xyz[:, 2].max())],
        actual_maximum_XY_radius=maximum_radius, xyz_sha256=_hash(xyz), faces_sha256=_hash(faces),
        closed_components=3, all_components_have_common_z0_root=True,
        root_overlap_scope='Three intentionally overlapping finite closed base caps, without Boolean union or welding.',
        body_modified=False, self_intersections='NOT_SCREENED; ROOT_INTERSECTIONS_INTENTIONALLY_ALLOWED',
        visual_status='PENDING_ACTUAL_RENDER', source_code=str(Path(__file__).resolve()),
        source_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    folder = args.root.resolve()/'prototypes'
    geometry_path, receipt_path = folder/'LEAF_CLUSTER.npz', folder/'LEAF_PROTOTYPE_RECEIPT.json'
    if geometry_path.exists() or receipt_path.exists():
        raise FileExistsError('Existing prototype preserved; no overwrite or second variant.')
    xyz, faces, receipt = build_geometry()
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(geometry_path, xyz=xyz, faces=faces)
    receipt['geometry_file'] = str(geometry_path)
    receipt['geometry_file_sha256'] = hashlib.sha256(geometry_path.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    print(json.dumps(dict(geometry=str(geometry_path), receipt=str(receipt_path),
                         vertices=len(xyz), triangles=len(faces), closed_leaves=3), ensure_ascii=False))


if __name__ == '__main__':
    main()
