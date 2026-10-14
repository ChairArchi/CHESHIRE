"""Protect actual mature parent bends at a fixed ancestral sampling scale.

No coordinates are changed. G5-index corners are sampled from the actual
current G7 carrier. The resulting guard attenuates future displacements only.
"""
from pathlib import Path
import hashlib
import importlib.util

import numpy as np

HERE = Path(__file__).resolve().parent
LIFT_PATH = HERE.parent/'fold_hierarchy_20261014/middle_lift.py'
LIFT_SHA = 'a690992d598b80edda23fdcb6f0319b91acafe2d1f531f0d9226022e20b44105'
CHUNK = 32768


def _file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


if _file_hash(LIFT_PATH) != LIFT_SHA:
    raise ValueError('Frozen actual CC incidence helper changed.')
_spec = importlib.util.spec_from_file_location('parent_guard_frozen_incidence', LIFT_PATH)
lift = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lift)


def helper_paths():
    return [LIFT_PATH, LIFT_PATH.parent/'prepare.py']


def _hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def _quintic(value):
    s = np.clip(value, 0., 1.)
    return s*s*s*(10.+s*(-15.+6.*s))


def _recover_edges(parent, child, nv):
    """Recover actual following-edge IDs from the verified child layout."""
    nf, ne = len(parent), 2*len(parent)
    if child.shape != (4*nf, 4):
        raise ValueError('Four actual quad children per parent required.')
    layout = child.reshape(nf, 4, 4)
    following = layout[:, :, 2]-nv
    if following.min() < 0 or following.max() >= ne:
        raise ValueError('Ancestral edge IDs outside their actual V/E/F range.')
    a, b = parent, np.roll(parent, -1, axis=1)
    endpoints = np.stack([np.minimum(a, b), np.maximum(a, b)], axis=-1)
    edges = np.full((ne, 2), -1, dtype=np.int64)
    edges[following.ravel()] = endpoints.reshape(-1, 2)
    if np.any(edges < 0):
        raise ValueError('Not every actual ancestral edge was recovered.')
    # This frozen validator checks old corners, face centres, preceding and
    # following edges, every endpoint association, incidence and vertex degree.
    following_checked, degree, proof = lift.actual_incidence(parent, edges, child, nv)
    if not np.array_equal(following_checked, following):
        raise ValueError('Recovered actual edge incidence changed.')
    return edges, degree, proof


def _carry(value, edges, faces):
    return np.concatenate([value, value[edges].mean(axis=1), value[faces].mean(axis=1)])


def _pairs(vx, vy, count):
    ids = np.arange(count, dtype=np.int64)
    px, py = np.asarray(vx), np.asarray(vy)
    for label, pair in (('X', px), ('Y', py)):
        if (pair.shape != (count,) or pair.dtype.kind not in 'iu'
                or pair.min() < 0 or pair.max() >= count
                or not np.array_equal(pair[pair], ids)):
            raise ValueError('Actual '+label+' reflection involution required.')
    if not np.array_equal(px[py], py[px]):
        raise ValueError('Actual X/Y involutions do not commute.')
    return px, py


def build_guard(xyz7, q6, q7, vx7, vy7, H):
    """Return ``guard7, metadata, state``. A zero guard preserves the carrier."""
    xyz7, q6, q7 = map(np.asarray, (xyz7, q6, q7))
    if (xyz7.ndim != 2 or xyz7.shape[1] != 3 or xyz7.dtype.kind != 'f'
            or not np.isfinite(xyz7).all() or not len(xyz7)
            or q6.ndim != 2 or q6.shape[1] != 4 or q6.dtype.kind not in 'iu'
            or q7.ndim != 2 or q7.shape[1] != 4 or q7.dtype.kind not in 'iu'
            or not len(q6) or len(q6) % 4 or len(q7) != 4*len(q6)):
        raise ValueError('Actual finite mature G7 carrier and G6/G7 quad associations required.')
    H = float(H)
    if not np.isfinite(H) or H <= 0.:
        raise ValueError('Positive physical reference height required.')
    if len(xyz7) != len(q7)+2 or q7.min() < 0 or q7.max() >= len(xyz7):
        raise ValueError('Actual closed genus-zero quad carrier count or indices differ.')
    q5 = q6.reshape(-1, 4, 4)[:, :, 1].copy()
    nv5, nv6 = len(q5)+2, len(q6)+2
    if q5.min() < 0 or q5.max() >= nv5 or q6.min() < 0 or q6.max() >= nv6:
        raise ValueError('Actual old-corner prefix correspondence differs.')
    px, py = _pairs(vx7, vy7, len(xyz7))
    print('GEOMETRY_GUARD: recover and validate actual G5/G6/G7 child IDs', flush=True)
    edges5, degree5, proof56 = _recover_edges(q5, q6, nv5)
    edges6, _, proof67 = _recover_edges(q6, q7, nv6)
    xyz5 = xyz7[:nv5]
    total = np.zeros((nv5, 3), dtype=float)
    print('GEOMETRY_GUARD: mature parent normal cone at G5-index sampling', flush=True)
    for start in range(0, len(q5), CHUNK):
        quad = q5[start:start+CHUNK]
        points = xyz5[quad]
        relative = points-points.mean(axis=1)[:, None, :]
        cross = np.cross(relative, np.roll(relative, -1, axis=1)).sum(axis=1)
        length = np.linalg.norm(cross, axis=1)
        if np.any(length <= 0.) or not np.isfinite(length).all():
            raise ValueError('Degenerate mature ancestral-sample quad normal.')
        unit = cross/length[:, None]
        for axis in range(3):
            total[:, axis] += np.bincount(quad.ravel(),
                weights=np.repeat(unit[:, axis], 4), minlength=nv5)
    cone5 = np.degrees(np.arccos(np.clip(np.linalg.norm(total/degree5[:, None], axis=1), 0., 1.)))
    raw_guard5 = 1.-_quintic((cone5-5.)/20.)
    hard_faces5 = np.any(cone5[q5] >= 25., axis=1)
    hard_controls5 = np.zeros(nv5, dtype=bool)
    hard_controls5[q5[hard_faces5].ravel()] = True
    # Apply the requested whole-face core before feathering. Otherwise forcing
    # the descendant face interiors to zero later creates an unfeathered rim.
    protection = 1.-raw_guard5
    protection[hard_controls5] = 1.
    neighbour_sum = (np.bincount(edges5[:, 0], weights=protection[edges5[:, 1]], minlength=nv5)
                     +np.bincount(edges5[:, 1], weights=protection[edges5[:, 0]], minlength=nv5))
    protection = .5*protection+.5*neighbour_sum/degree5
    protection[hard_controls5] = 1.
    guard5 = 1.-protection
    guard6 = _carry(guard5, edges5, q5)
    guard7 = _carry(guard6, edges6, q6)
    if guard7.shape != (len(xyz7),):
        raise ValueError('Actual guard V/E/F transport count differs.')
    hard_faces7 = np.repeat(hard_faces5, 16)
    hard_controls7 = np.zeros(len(xyz7), dtype=bool)
    for start in range(0, len(q7), CHUNK):
        selected = hard_faces7[start:start+CHUNK]
        hard_controls7[q7[start:start+CHUNK][selected].ravel()] = True
    guard7[hard_controls7] = 0.
    guard7 = np.minimum(guard7, guard7[px])
    guard7 = np.minimum(guard7, guard7[py])
    symmetry = max(float(np.max(np.abs(guard7-guard7[px]))),
                   float(np.max(np.abs(guard7-guard7[py]))))
    if (not np.isfinite(guard7).all() or np.any(guard7 < 0.) or np.any(guard7 > 1.)
            or symmetry != 0. or np.any(guard7[hard_controls7] != 0.)):
        raise ValueError('Guard range, exact hard core or scalar symmetry failed.')
    all_zero_faces7 = np.zeros(len(q7), dtype=bool)
    for start in range(0, len(q7), CHUNK):
        all_zero_faces7[start:start+CHUNK] = np.all(guard7[q7[start:start+CHUNK]] == 0., axis=1)
    if np.any(hard_faces7 & ~all_zero_faces7):
        raise ValueError('A requested hard descendant face lost exact four-corner protection.')
    metadata = dict(implementation='MATURE_PARENT_ANCESTRAL_NORMAL_CONE_GUARD_V1',
        source_generation=7, output_generation=7, added_CC_passes=0,
        added_topology_events=0, parent_geometry_changed=False,
        sampling='Actual current mature G7 carrier XYZ at actual inherited G5-index old-corner prefix. These are mature parent samples, not the saved historical G5 shape.',
        metric='cone=acos(norm(mean(incident actual sampled-parent unit quad normals))) in degrees; unsigned normal dispersion, not signed curvature or semantic ridge detection.',
        thresholds_degrees=dict(soft_start=5., hard_core=25.),
        raw_guard='1-quintic(clip((cone-5deg)/20deg,0,1))',
        hard_core='Any G5 sampled face corner cone>=25deg selects the entire sampled face. All its G7 descendant face corners have zero guard.',
        feather='One G5-graph pass on protection: .5*self+.5*actual_edge_neighbor_mean; original whole-face corner core restored afterwards.',
        transport='Actual G5-to-G6-to-G7 V/E/F scalar concatenation, followed by explicit zero on all hard face descendants and conservative actual reflection-orbit minimum.',
        native_fan_protection='Every requested hard G7 descendant quad has all four corners at zero guard. If caller keeps new delta exactly zero there, ordinary arithmetic native fan centres and all its triangles remain the carrier exactly.',
        physical_height_reference=H,
        G5_sample_vertices=nv5, G5_sample_quads=len(q5), G6_vertices=nv6,
        G6_quads=len(q6), G7_vertices=len(xyz7), G7_quads=len(q7),
        cone_quantile_probabilities=[0., .25, .5, .75, .9, .95, .99, 1.],
        cone5_quantiles=np.quantile(cone5, [0., .25, .5, .75, .9, .95, .99, 1.]).tolist(),
        raw_high_cone_vertices=int(np.count_nonzero(cone5 >= 25.)),
        hard_G5_faces=int(hard_faces5.sum()), hard_G5_face_fraction=float(hard_faces5.mean()),
        original_whole_face_core_G5_vertices=int(hard_controls5.sum()),
        requested_hard_G7_faces=int(hard_faces7.sum()),
        all_zero_guard_G7_faces=int(all_zero_faces7.sum()),
        all_zero_guard_G7_face_fraction=float(all_zero_faces7.mean()),
        zero_guard_G7_vertices=int(np.count_nonzero(guard7 == 0.)),
        full_guard_G7_vertices=int(np.count_nonzero(guard7 == 1.)),
        partial_guard_G7_vertices=int(np.count_nonzero((guard7 > 0.) & (guard7 < 1.))),
        guard7_quantiles=np.quantile(guard7, [0., .1, .25, .5, .75, .9, .99, 1.]).tolist(),
        scalar_reflection_max_error=symmetry,
        actual_ancestry_checks=dict(G5_to_G6=proof56, G6_to_G7=proof67),
        input_carrier_xyz_sha256=_hash(xyz7), input_G6_quads_sha256=_hash(q6),
        input_G7_quads_sha256=_hash(q7), recovered_G5_quads_sha256=_hash(q5),
        mature_G5_index_samples_sha256=_hash(xyz5), cone5_sha256=_hash(cone5),
        output_guard7_sha256=_hash(guard7),
        code_binding={str(p): _file_hash(p) for p in [Path(__file__).resolve()]+helper_paths()},
        limits='Fixed geometric protection candidate. A large cone may represent desired ornament or an existing defect. No automatic semantic ridge/valley/end classification, curvature-radius guarantee, collision test, broadest possible hierarchy protection or aesthetic success claim. Guard may suppress new detail over a broad area; actual matched renders decide its usefulness.')
    state = dict(cone_degrees5=cone5, raw_guard5=raw_guard5, guard5=guard5,
        hard_faces5=hard_faces5, hard_controls5=hard_controls5,
        hard_faces7=hard_faces7, hard_controls7=hard_controls7,
        all_zero_faces7=all_zero_faces7, guard7=guard7)
    return guard7, metadata, state
