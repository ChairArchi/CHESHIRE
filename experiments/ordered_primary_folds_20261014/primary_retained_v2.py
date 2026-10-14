"""Strengthen two existing MIDDLE families without replacing their geometry."""
from pathlib import Path
import hashlib
import importlib.util

import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states/G06_MIDDLE')
CONTROL_SHA = '38998220e63e9b9bd98f3d63870db444c681b9531d761581083c554021b8528d'
EVIDENCE_SHA = '1f1984a368ea03cc780d5ca72429837cbf6215ac3f7113c7ef4b1fee96a2685e'
HELPER = HERE.parent/'flow_fold_finish_20261014/flow_curved_operator.py'
HELPER_SHA = '92248bd60d4d2188f05a7396fc0eec1989ae365644454081e911600e3e5bc844'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def ah(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


if digest(HELPER) != HELPER_SHA:
    raise ValueError('Frozen actual mirror-vector helper changed.')
spec = importlib.util.spec_from_file_location('retained_primary_frozen_flow', HELPER)
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)


def helper_paths():
    return [HELPER]+flow.helper_paths()


def build(xyz, q, chart, support, vx, vy, H):
    for name, checksum in (('control_quad.npz', CONTROL_SHA), ('evidence.npz', EVIDENCE_SHA)):
        if digest(SOURCE/name) != checksum:
            raise ValueError('Preserved actual MIDDLE input changed.')
    with np.load(SOURCE/'evidence.npz', allow_pickle=False) as saved:
        phase, delta, envelope = saved['directional_phase'], saved['displacement_vector'], saved['envelope']
        if (not np.array_equal(support, saved['feature_support']) or
                not np.array_equal(vx, saved['mirror_x_vertex_pairs']) or
                not np.array_equal(vy, saved['mirror_y_vertex_pairs'])):
            raise ValueError('Actual MIDDLE support or reflection IDs differ.')
    with np.load(SOURCE/'control_quad.npz', allow_pickle=False) as saved:
        if (not np.array_equal(xyz+delta, saved['xyz']) or
                not np.array_equal(q, saved['faces']) or
                not np.array_equal(chart, saved['chart'])):
            raise ValueError('Actual preserved MIDDLE delta does not reconstruct its output.')
    if not all(np.isfinite(a).all() for a in (xyz, phase, delta, envelope, support)):
        raise ValueError('Finite preserved input required.')
    ids, pairs = flow.field._mirror_pairs({'X': vx, 'Y': vy}, len(xyz))
    representative = np.minimum(np.minimum(ids, pairs['X']),
        np.minimum(pairs['Y'], pairs['X'][pairs['Y']]))
    k = phase/(2.*np.pi)
    family = 1.-(1.-np.exp(-((k-1.)/.70)**4))*(1.-np.exp(-((k-4.)/.70)**4))
    gain = (1.+1.6*family*(1.-.75*support))[representative]
    moved = flow.field._transport(gain[:, None]*delta, ids, pairs)[0]
    amplitude = .006*float(H)*envelope*(1.-.55*support)*gain
    amplitude = np.minimum(amplitude, amplitude[pairs['X']])
    amplitude = np.minimum(amplitude, amplitude[pairs['Y']])
    out = xyz+moved
    if (not np.isfinite(out).all() or gain.min() < 1.-1e-12 or gain.max() > 2.6+1e-12
            or np.any(amplitude < 0.)):
        raise ValueError('Retained primary gain or geometry failed.')
    metadata = dict(implementation='RETAINED_MIDDLE_PRIMARY_HIERARCHY_V3',
        source_generation=6, output_generation=6, added_CC_passes=0, added_topology_events=0,
        source_control=str(SOURCE/'control_quad.npz'), source_control_sha256=CONTROL_SHA,
        source_evidence=str(SOURCE/'evidence.npz'), source_evidence_sha256=EVIDENCE_SHA,
        original_MIDDLE_reconstruction_exact=True,
        phase='Actual saved unwrapped G6 MIDDLE directional_phase; original family paths preserved.',
        phase_cycles_per_quarter=5,
        family='p=1-(1-exp(-((phase/(2*pi)-1)/.70)^4))*(1-exp(-((phase/(2*pi)-4)/.70)^4))',
        gain='1+1.6*p*(1-.75*actual_feature_support)',
        gain_range=[float(gain.min()), float(gain.max())],
        old_NESTED_primary_gain='.95+.35*p; maximum 1.30',
        new_primary_gain_maximum=2.6, event_support_one_gain_maximum=1.4,
        source_geometry_averaged=False, new_displacement_filter_passes=0,
        delta='Actual saved MIDDLE displacement multiplied by the declared reflection-invariant family gain; canonical actual-ID mirror-vector transport only.',
        envelope='Conservative orbit-min(.006H*saved_envelope*(1-.55*saved_support)*new_gain).',
        maximum_actual_displacement=float(np.linalg.norm(moved, axis=1).max()),
        actual_delta_norm_quantiles=np.quantile(np.linalg.norm(moved, axis=1), [0,.1,.5,.9,.99,1]).tolist(),
        maximum_added_displacement=float(np.linalg.norm(moved-delta, axis=1).max()),
        input_xyz_sha256=ah(xyz), output_xyz_sha256=ah(out),
        saved_phase_sha256=ah(phase), saved_delta_sha256=ah(delta),
        output_delta_sha256=ah(moved), parent_envelope_sha256=ah(amplitude),
        code_sha256=digest(__file__),
        limitations='Existing geometric vocabulary retained and amplified in two inherited phase families. Not new semantic ridge detection, topology growth, a collision certificate, or visual success before actual renders.')
    state = dict(phase=phase, envelope=amplitude, delta_primary=moved,
        saved_middle_delta=delta, primary_gain=gain, primary_family=family,
        feature_support=support)
    return out, phase, amplitude, metadata, state
