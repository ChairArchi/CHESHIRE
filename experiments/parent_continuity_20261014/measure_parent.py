"""Read-only stage separation of the actual NESTED02 parent and new deltas.

Writes scalar measurement JSON only. Does not generate a candidate or change
any saved source geometry. Angles measure local face direction changes, not
semantic damage or a collision certificate.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time

import numpy as np

SOURCE = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states')
BASE = Path('E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial02')
OUTPUT = Path('E:/CHESHIRE_DATA/experiments/parent_continuity_20261014/audit01')
CHUNK = 32768
QUANTILES = [0., .25, .5, .75, .9, .95, .99, 1.]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def ah(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def normals(points):
    relative = points-points.mean(axis=-2, keepdims=True)
    cross = np.cross(relative, np.roll(relative, -1, axis=-2)).sum(axis=-2)
    length = np.linalg.norm(cross, axis=-1)
    if np.any(length <= 0.):
        raise ValueError('Degenerate actual measured quad normal.')
    return cross/length[..., None]


class Summary:
    def __init__(self, thresholds, stride=31):
        self.thresholds, self.stride = thresholds, stride
        self.count, self.maximum = 0, 0.
        self.exceed = np.zeros(len(thresholds), dtype=np.int64)
        self.samples = []

    def add(self, values):
        v = np.asarray(values).ravel()
        if not np.isfinite(v).all():
            raise ValueError('Nonfinite measurement.')
        self.count += len(v)
        self.maximum = max(self.maximum, float(v.max(initial=0.)))
        self.exceed += np.array([np.count_nonzero(v > t) for t in self.thresholds])
        self.samples.append(v[::self.stride].copy())

    def report(self):
        sample = np.concatenate(self.samples)
        return dict(count=self.count, maximum=self.maximum,
            sampled_quantile_probabilities=QUANTILES,
            sampled_quantiles=np.quantile(sample, QUANTILES).tolist(),
            quantile_sample_count=len(sample), quantile_stride=self.stride,
            thresholds=self.thresholds, all_incidence_exceed_counts=self.exceed.tolist(),
            all_incidence_exceed_fractions=(self.exceed/self.count).tolist())


def angle(a, b):
    return np.degrees(np.arccos(np.clip(np.einsum('...i,...i->...', a, b), -1., 1.)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    output = parser.parse_args().output.resolve()
    if (output/'MEASUREMENTS.json').exists():
        raise FileExistsError('Preserved earlier audit.')
    started = time.perf_counter()
    receipt = read(BASE/'RECEIPT.json')
    nested = receipt['nested']
    surface_info = read(SOURCE/'G07_SURFACE/generation.json')
    middle_info = read(SOURCE/'G06_MIDDLE/generation.json')
    paths = [BASE/'RECEIPT.json', BASE/'PARENT_STATE.npz', BASE/'NESTED_STATE.npz',
        SOURCE/'G07_SURFACE/control_quad.npz', SOURCE/'G07_SURFACE/generation.json',
        SOURCE/'G06_MIDDLE/control_quad.npz', SOURCE/'G06_MIDDLE/generation.json']
    sources = {str(p): digest(p) for p in paths}
    if sources[str(SOURCE/'G07_SURFACE/control_quad.npz')] != surface_info['control_file_sha256']:
        raise ValueError('Actual G7 SURFACE source changed.')
    if sources[str(SOURCE/'G06_MIDDLE/control_quad.npz')] != middle_info['control_file_sha256']:
        raise ValueError('Actual G6 MIDDLE source changed.')
    with np.load(SOURCE/'G07_SURFACE/control_quad.npz', allow_pickle=False) as saved:
        surface, q = saved['xyz'], saved['faces']
    with np.load(BASE/'PARENT_STATE.npz', allow_pickle=False) as saved:
        primary_delta = saved['primary_delta']
    carrier = surface+primary_delta
    del primary_delta
    if ah(carrier) != nested['input_xyz_sha256'] or ah(q) != nested['input_quads_sha256']:
        raise ValueError('Actual NESTED02 incoming carrier or quad association differs.')
    with np.load(BASE/'NESTED_STATE.npz', allow_pickle=False) as saved:
        dc, ds, mask = saved['delta_child'], saved['delta_small'], saved['parent_mask']
    if ah(dc) != nested['child']['delta_sha256'] or ah(ds) != nested['small']['delta_sha256']:
        raise ValueError('Actual saved NESTED02 child deltas changed.')
    if ah(carrier+dc+ds) != nested['output_xyz_sha256']:
        raise ValueError('Saved stage deltas do not reproduce actual final controls.')
    labels = ('SURFACE_to_PRIMARY_WEIGHTED_CARRIER', 'CARRIER_to_CHILD', 'CHILD_to_FINAL', 'CARRIER_to_FINAL')
    angles = {name: Summary([5., 15., 30., 60.]) for name in labels}
    edges = {name: Summary([.1, .25, .5, 1., 2.]) for name in labels}
    vertex_sum = np.zeros_like(carrier)
    degree = np.bincount(q.ravel(), minlength=len(carrier))
    print('MEASURE actual parent/CHILD/SMALL in one G7 face traversal', flush=True)
    for start in range(0, len(q), CHUNK):
        qq = q[start:start+CHUNK]
        p0, p1 = surface[qq], carrier[qq]
        dchild, dsmall = dc[qq], ds[qq]
        p2 = p1+dchild
        p3 = p2+dsmall
        nn = [normals(p) for p in (p0, p1, p2, p3)]
        for name, a, b in zip(labels, (0, 1, 2, 1), (1, 2, 3, 3)):
            angles[name].add(angle(nn[a], nn[b]))
        for component in range(3):
            vertex_sum[:, component] += np.bincount(qq.ravel(),
                weights=np.repeat(nn[1][:, component], 4), minlength=len(carrier))
        for name, pa, delta in zip(labels, (p0, p1, p2, p1), (p1-p0, dchild, dsmall, dchild+dsmall)):
            length = np.linalg.norm(np.roll(pa, -1, axis=1)-pa, axis=2)
            if np.any(length <= 0.):
                raise ValueError('Zero actual edge length.')
            difference = np.linalg.norm(np.roll(delta, -1, axis=1)-delta, axis=2)
            edges[name].add(difference/length)
    mean_length = np.linalg.norm(vertex_sum/degree[:, None], axis=1)
    source_turn = np.degrees(np.arccos(np.clip(mean_length, 0., 1.)))
    source_groups = {}
    moved = np.linalg.norm(dc+ds, axis=1)
    for threshold in (5., 15., 30.):
        selected = source_turn >= threshold
        source_groups[str(threshold)+'deg'] = dict(vertices=int(selected.sum()),
            old_phase_mask_protected=int(np.count_nonzero(selected & (mask == 0.))),
            child_or_small_moved=int(np.count_nonzero(selected & (moved > 1e-12))),
            delta_quantiles=np.quantile(moved[selected], QUANTILES).tolist() if selected.any() else [])
    del vertex_sum, mean_length, degree, dc, ds, mask, moved
    with np.load(SOURCE/'G06_MIDDLE/control_quad.npz', allow_pickle=False) as saved:
        x6, q6 = saved['xyz'], saved['faces']
    if len(q) != 4*len(q6) or not np.array_equal(q.reshape(-1, 4, 4)[:, :, 1], q6):
        raise ValueError('Actual G6/G7 four-child corner correspondence differs.')
    cc = Summary([5., 15., 30., 60.])
    print('MEASURE saved G6 MIDDLE to saved neutral CC G7 child directions', flush=True)
    for start in range(0, len(q6), CHUNK//4):
        stop = min(start+CHUNK//4, len(q6))
        parent_n = normals(x6[q6[start:stop]])
        child_n = normals(surface[q[4*start:4*stop]]).reshape(-1, 4, 3)
        cc.add(angle(parent_n[:, None, :], child_n))
    result = dict(date='2026-10-14', sources=sources,
        code=dict(path=str(Path(__file__).resolve()), sha256=digest(__file__)),
        actual_carrier_reproduced=True, actual_child_and_small_reproduce_final=True,
        actual_native_model_generated=False,
        face_direction_change_degrees={name: summary.report() for name, summary in angles.items()},
        edge_relative_delta_change={name: summary.report() for name, summary in edges.items()},
        neutral_CC_G6_parent_to_G7_each_child_face_degrees=cc.report(),
        carrier_incident_normal_dispersion_angle_degrees=dict(quantiles=QUANTILES,
            values=np.quantile(source_turn, QUANTILES).tolist(), groups=source_groups,
            definition='acos(norm(mean(incident actual carrier unit quad normals))); unsigned vertex normal-cone dispersion, not signed principal curvature.'),
        counting='Face direction counts use all actual quads. Edge counts use all four oriented quad-edge incidences, so each shared edge is counted twice. Quantiles use deterministic every-31st incidence samples; exceedance counts and maxima use all incidences.',
        interpretation='Stage-separated geometric changes only. Nonzero angle/edge change is not automatically damage. Actual G6/G7 correspondence is checked; CC child direction change includes intended smoothing. Existing source defects cannot be attributed to new CHILD/SMALL from these statistics. No semantic ridge/termination detection, self-intersection test or aesthetic verdict.',
        elapsed_seconds=time.perf_counter()-started)
    for path, expected in sources.items():
        if digest(path) != expected:
            raise ValueError('Read-only audit source changed during measurement.')
    output.mkdir(parents=True, exist_ok=True)
    (output/'MEASUREMENTS.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print('MEASUREMENTS_SAVED', str(output/'MEASUREMENTS.json'), result['elapsed_seconds'], flush=True)


if __name__ == '__main__':
    main()
