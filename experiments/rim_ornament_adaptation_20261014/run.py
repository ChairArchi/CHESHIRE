"""Three surface-guided ornament visualizations; original G7 remains immutable."""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import shutil
import time

import numpy as np
from scipy.interpolate import PchipInterpolator

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/rim_ornament_adaptation_20261014/trial01')
PREVIOUS = Path('E:/CHESHIRE_DATA/experiments/local_ornament_comparison_20261014/trial01')
HELPER = HERE.parent/'local_ornament_comparison_20261014/run.py'
HELPER_SHA = '59c408cd0170171bc7e67e8b53b8dea18fbdf81be9d92f3ed5e5a2460cfc87a2'
spec = importlib.util.spec_from_file_location('preserved_local_ornament_tools', HELPER)
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)
digest, array_hash, write, inside = tools.digest, tools.array_hash, tools.write, tools.inside
SIGNS = tools.SIGNS
VARIANTS = ('MANDEL_RIBBON', 'LEAF_FAN', 'HYBRID')
RECIPE = dict(mandel=dict(length=.16, width=.074, normal_height=.045, interior=[0., 0., .22]),
    leaf=dict(length=.16, fan_width_scale=.20, normal_scale=.22, arch=.018, forward_rise=.025),
    hybrid_accents=[dict(leaf_z=.47, leaf_x=-.025, length=.036, width=.026, normal_height=.018),
                    dict(leaf_z=.72, leaf_x=.040, length=.026, width=.019, normal_height=.013)],
    guide='PCHIP through three actual connected-patch source vertices; normalized linear source-normal interpolation. Outside guide, straight endpoint continuation with constant endpoint normal.',
    body_geometry_changed=False, added_CC_passes=0, smoothing_passes=0,
    interpretation='Actual closed prototype meshes bent along source-derived local guides. Independent overlaps, not Boolean unions, source regeneration, G8 or a reference-exact algorithm.')


def unit(a):
    a = np.asarray(a, float)
    return a/np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-30)


class Guide:
    def __init__(self, group):
        self.points = np.asarray([r['source_xyz'] for r in group['roots']], float)
        self.normals = unit([r['source_outward_normal'] for r in group['roots']])
        self.anchor_index = int(group.get('anchor_root_index', len(self.points)//2))
        self.s = np.r_[0., np.cumsum(np.linalg.norm(np.diff(self.points, axis=0), axis=1))]
        self.s -= self.s[self.anchor_index]
        if not np.all(np.diff(self.s) > 0):
            raise ValueError('Distinct ordered actual source roots required.')
        self.curve = PchipInterpolator(self.s, self.points, axis=0)
        self.derivative = self.curve.derivative()
        self.min_query, self.max_query = 0., 0.
        self.size_factor = .38 if group['group_id'] == 3 else 1.

    def evaluate(self, distance):
        distance = np.asarray(distance, float).reshape(-1)
        self.min_query = min(self.min_query, float(distance.min()))
        self.max_query = max(self.max_query, float(distance.max()))
        clamped = np.clip(distance, self.s[0], self.s[-1])
        p = self.curve(clamped)
        derivative = self.derivative(clamped)
        n = unit(np.column_stack([np.interp(clamped, self.s, self.normals[:, k]) for k in range(3)]))
        t = unit(derivative-n*np.einsum('ij,ij->i', derivative, n)[:, None])
        p += (distance-clamped)[:, None]*t
        u = unit(np.cross(n, t))
        return p, t, u, n

    def map(self, a, b, c):
        p, _, u, n = self.evaluate(a)
        return p + np.asarray(b)[:, None]*u + np.asarray(c)[:, None]*n

    def evidence(self):
        return dict(actual_guide_root_count=len(self.points), anchor_root_index=self.anchor_index,
            root_arc_distances=self.s.tolist(), guide_chord_span=float(self.s[-1]-self.s[0]),
            actual_query_range=[self.min_query, self.max_query],
            ornament_size_factor=self.size_factor,
            endpoint_extension=[max(0., float(self.s[0]-self.min_query)), max(0., float(self.max_query-self.s[-1]))],
            scope='The guide roots are actual source points on a connected selected patch. PCHIP interiors and endpoint extensions are ornament guides, not certified source-surface projections or exact fold crests.')


def normals(xyz, faces):
    tri = xyz[faces]
    cross = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    result = np.zeros_like(xyz)
    for k in range(3):
        np.add.at(result, faces[:, k], cross)
    return unit(result)


def mandel_ribbon(proto, guide):
    x, _, _ = proto.T
    recipe = RECIPE['mandel']
    a = x*recipe['length']*guide.size_factor/np.ptp(proto[:, 0])
    b = proto[:, 1]*recipe['width']*guide.size_factor/np.ptp(proto[:, 1])
    c = (proto[:, 2]-.22)*recipe['normal_height']*guide.size_factor
    return guide.map(a, b, c)


def leaf_fan(proto, guide, interior):
    r = RECIPE['leaf']
    a = (proto[:, 2]-interior[2])*r['length']
    b = (proto[:, 0]-interior[0])*r['fan_width_scale']
    c = ((proto[:, 1]-interior[1])*r['normal_scale'] +
         r['arch']*(np.sin(np.pi*proto[:, 2])-np.sin(np.pi*interior[2])) +
         r['forward_rise']*(proto[:, 2]-interior[2]))
    return guide.map(a*guide.size_factor, b*guide.size_factor, c*guide.size_factor)


def accent(bulb, point, normal, tangent, recipe):
    n = unit(normal)
    t = unit(tangent-n*np.dot(tangent, n))
    u = np.cross(n, t)
    a = bulb[:, 0]*recipe['length']/np.ptp(bulb[:, 0])
    b = bulb[:, 1]*recipe['width']/np.ptp(bulb[:, 1])
    c = (bulb[:, 2]-.22)*recipe['normal_height']
    return point+a[:, None]*t+b[:, None]*u+c[:, None]*n


def check_piece(xyz, faces, contact_point):
    if not np.isfinite(xyz).all():
        raise ValueError('Nonfinite adapted prototype.')
    tri = xyz[faces]
    minimum = float(np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1).min())
    if minimum <= 0:
        raise ValueError('Degenerate adapted triangle.')
    actual_inside, intersections = inside(np.asarray(contact_point), xyz, faces)
    if not actual_inside:
        raise ValueError('Actual transformed ornament lost its interior attachment point.')
    return dict(actual_minimum_double_area=minimum, actual_contact_point_inside=actual_inside,
        ray_positive_crossings=intersections,
        contact_scope='Ray parity on actual transformed closed triangles; no weld, collision freedom or tangent-continuity claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    root = parser.parse_args().root.resolve()
    if (root/'RECEIPT.json').exists() or any((root/name).exists() for name in VARIANTS):
        raise FileExistsError('Previous saved candidate preserved.')
    if digest(HELPER) != HELPER_SHA:
        raise ValueError('Frozen local geometry helpers changed.')
    started = time.perf_counter()
    common = json.loads((root/'PLACEMENT.json').read_text(encoding='utf8'))
    previous = json.loads((PREVIOUS/'RECEIPT.json').read_text(encoding='utf8'))
    for filename, expected in tools.EXPECTED.items():
        if digest(tools.SOURCE/filename) != expected:
            raise ValueError('Original G7 changed.')
    snapshots = {}
    for path in (HERE/'run.py', HERE/'placement.py', HELPER):
        target = root/'source_snapshot'/path.parent.name/path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        snapshots[str(path)] = dict(snapshot=str(target), sha256=digest(path))
    prototypes, prototype_records = {}, {}
    for name in ('MANDELBULB', 'LEAF_CLUSTER'):
        path = PREVIOUS/'prototypes'/f'{name}.npz'
        if digest(path) != previous['variants'][name]['prototype_sha256']:
            raise ValueError('Frozen prototype changed: '+name)
        with np.load(path, allow_pickle=False) as data:
            prototypes[name] = (data['xyz'], data['faces'].astype(np.int32))
        prototype_records[name] = dict(path=str(path), sha256=digest(path))
    bulb, bulb_faces = prototypes['MANDELBULB']
    leaf, leaf_faces = prototypes['LEAF_CLUSTER']
    interior = np.asarray(previous['variants']['LEAF_CLUSTER']['prototype_interior_root'])
    canonical = {name: [] for name in VARIANTS}
    contacts = []
    prototype_normals = normals(leaf, leaf_faces)
    for group_index, group in enumerate(common['canonical_groups']):
        print('ADAPT actual source-patch group', group_index, flush=True)
        guide = Guide(group)
        body_contact = guide.points[guide.anchor_index]
        ribbon = mandel_ribbon(bulb, guide)
        fan = leaf_fan(leaf, guide, interior)
        record = dict(group=group_index,
            source_control_vertex_id=group['roots'][guide.anchor_index]['source_control_vertex_id'],
            mandel=check_piece(ribbon, bulb_faces, body_contact),
            leaf=check_piece(fan, leaf_faces, body_contact), accents=[])
        canonical['MANDEL_RIBBON'].append((ribbon, bulb_faces))
        canonical['LEAF_FAN'].append((fan, leaf_faces))
        canonical['HYBRID'].append((fan, leaf_faces))
        fan_normals = normals(fan, leaf_faces)
        for recipe in RECIPE['hybrid_accents']:
            eligible = np.arange(6144)
            eligible = eligible[(prototype_normals[eligible, 1] > .45) & (leaf[eligible, 2] > .30)]
            score = (leaf[eligible, 2]-recipe['leaf_z'])**2 + (leaf[eligible, 0]-recipe['leaf_x'])**2
            vertex = int(eligible[np.argmin(score)])
            _, tangents, _, _ = guide.evaluate([(leaf[vertex, 2]-interior[2])*RECIPE['leaf']['length']*guide.size_factor])
            sized_recipe = {k: (v*guide.size_factor if k in ('length', 'width', 'normal_height') else v) for k, v in recipe.items()}
            small = accent(bulb, fan[vertex], fan_normals[vertex], tangents[0], sized_recipe)
            canonical['HYBRID'].append((small, bulb_faces))
            record['accents'].append(dict(actual_leaf_vertex_id=vertex,
                actual_leaf_point=fan[vertex].tolist(), recipe=sized_recipe,
                checks=check_piece(small, bulb_faces, fan[vertex])))
        record['guide'] = guide.evidence()
        contacts.append(record)
    variants = {}
    for name in VARIANTS:
        print('SAVE actual reflected', name, flush=True)
        vertices, faces, orbit_bindings, offset = [], [], [], 0
        for piece_index, (xyz, tri) in enumerate(canonical[name]):
            start = offset
            for sign in SIGNS:
                sign = np.asarray(sign)
                vertices.append(xyz*sign)
                faces.append((tri[:, [0, 2, 1]] if sign.prod() < 0 else tri)+offset)
                offset += len(xyz)
            orbit_bindings.append(dict(start=start, vertices_per_copy=len(xyz), piece=piece_index))
        xyz, tri = np.concatenate(vertices), np.concatenate(faces)
        residual = 0.
        for orbit in orbit_bindings:
            start, nv = orbit['start'], orbit['vertices_per_copy']
            for j, sign in enumerate(SIGNS):
                residual = max(residual, float(abs(xyz[start+j*nv:start+(j+1)*nv]-xyz[start:start+nv]*sign).max()))
        if residual != 0:
            raise ValueError('Actual constructed mirror correspondence differs.')
        folder = root/name
        folder.mkdir()
        path = folder/'geometry.npz'
        np.savez_compressed(path, xyz=xyz, faces=tri)
        variants[name] = dict(geometry=str(path), geometry_sha256=digest(path),
            xyz_sha256=array_hash(xyz), faces_sha256=array_hash(tri), vertices=len(xyz), triangles=len(tri),
            actual_XY_reflection_residual=residual, canonical_pieces=len(canonical[name]),
            reflected_pieces=4*len(canonical[name]))
        del xyz, tri, vertices, faces
        gc.collect()
    for filename, expected in tools.EXPECTED.items():
        if digest(tools.SOURCE/filename) != expected:
            raise ValueError('Original source changed during trial.')
    for path, rec in snapshots.items():
        if digest(path) != rec['sha256'] or digest(rec['snapshot']) != rec['sha256']:
            raise ValueError('Executed source changed.')
    write(root/'RECEIPT.json', dict(date='2026-10-14', timezone='Asia/Seoul',
        authorization='User delegated technically feasible visualizations after two initial prototypes; no further motif-selection approval required.',
        basis_commit='2e3df44fa58a761efab50c28691d016a1fc44678',
        source_native_path=str(tools.SOURCE/'geometry.npz'), source_native_geometry_sha256=tools.EXPECTED['geometry.npz'],
        source_hashes_after=tools.EXPECTED, placement_sha256=digest(root/'PLACEMENT.json'),
        previous_trial=str(PREVIOUS), previous_receipt_sha256=digest(PREVIOUS/'RECEIPT.json'),
        prototypes=prototype_records, recipe=RECIPE, variants=variants, actual_local_checks=contacts,
        source_snapshots=snapshots, body_geometry_changed=False, added_CC_passes=0,
        seconds=time.perf_counter()-started, visual_success='PENDING_ACTUAL_MATCHED_RENDER',
        scope='Three actual saved local additions on unchanged original G7. Source-derived guide adaptation and one fixed hybrid hierarchy; no candidate matrix, whole-column smoothing, body tip replacement, Boolean fusion or new growth generation.'))
    print('SAVED three actual adapted ornaments; original G7 unchanged', flush=True)


if __name__ == '__main__':
    main()
