"""Replace the competing global MIDDLE field with two material parent folds.

The actual G6 DEPTH08 carrier is read-only. This operator uses its inherited
material chart for fold ownership and fresh actual normals for one bounded
primary displacement. The caller owns source binding and the neutral G7 CC.
"""
from pathlib import Path
import hashlib
import importlib.util

import numpy as np
from scipy.interpolate import PchipInterpolator


HERE = Path(__file__).resolve().parent
FLOW_PATH = HERE.parent/'flow_fold_finish_20261014/flow_curved_operator.py'
FLOW_SHA = '92248bd60d4d2188f05a7396fc0eec1989ae365644454081e911600e3e5bc844'
CHUNK = 65536


def _file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


if _file_hash(FLOW_PATH) != FLOW_SHA:
    raise ValueError('Frozen actual-normal and delta-average helper changed.')
_spec = importlib.util.spec_from_file_location('ordered_primary_frozen_flow', FLOW_PATH)
flow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(flow)
field = flow.field


def helper_paths():
    return [FLOW_PATH]+flow.helper_paths()


def _hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def _orbit_min(value, pairs):
    result = np.minimum(value, value[pairs['X']])
    return np.minimum(result, result[pairs['Y']])


def _symmetry_error(value, ids, pairs):
    maximum = 0.
    for start in range(0, len(value), CHUNK):
        sl = slice(start, min(start+CHUNK, len(value)))
        for axis, pair in ((0, pairs['X']), (1, pairs['Y'])):
            reflected = value[pair[ids[sl]]].copy()
            reflected[:, axis] *= -1.
            maximum = max(maximum, float(np.max(np.abs(value[sl]-reflected))))
    return maximum


def build(xyz, q, chart, support, vx, vy, H):
    """Return ``out, phase, envelope, metadata, state`` without file writes.

    Phase and envelope describe the new actual G6 parent. They must be carried
    through the caller's actual G6-to-G7 V/E/F associations for its children.
    """
    xyz, q, chart, support = map(np.asarray, (xyz, q, chart, support))
    if (xyz.ndim != 2 or xyz.shape[1] != 3 or xyz.dtype.kind != 'f'
            or not len(xyz) or not np.isfinite(xyz).all()
            or q.ndim != 2 or q.shape[1] != 4 or q.dtype.kind not in 'iu'
            or not len(q) or q.min() < 0 or q.max() >= len(xyz)):
        raise ValueError('Finite actual all-quad G6 DEPTH08 carrier required.')
    count = len(xyz)
    if chart.shape != xyz.shape or not np.isfinite(chart).all():
        raise ValueError('Actual unchanged inherited material chart required.')
    if (support.shape != (count,) or not np.isfinite(support).all()
            or np.any(support < 0.) or np.any(support > 1.)):
        raise ValueError('Actual inherited feature support in [0,1] required.')
    H = float(H)
    lo, hi = float(xyz[:, 2].min()), float(xyz[:, 2].max())
    if not np.isfinite(H) or H <= 0. or hi <= lo:
        raise ValueError('Positive physical reference and actual source height required.')
    if chart[:, 0].min() < -1e-12 or chart[:, 0].max() > 1.+1e-12:
        raise ValueError('Material t lies outside the actual inherited [0,1] chart.')
    ids, pairs = field._mirror_pairs({'X': vx, 'Y': vy}, count)
    representative = np.minimum(np.minimum(ids, pairs['X']),
        np.minimum(pairs['Y'], pairs['X'][pairs['Y']]))
    degree = np.bincount(q.ravel(), minlength=count)
    if np.any(degree == 0):
        raise ValueError('Source orphan controls are not repaired.')

    # Canonical reflection orbits preserve the original actual chart; neither
    # current radial XYZ nor a nearest-parameter estimate defines ownership.
    t = chart[representative, 0].copy()
    theta = np.arctan2(np.abs(chart[representative, 2]),
                      np.abs(chart[representative, 1]))
    slow = np.sin(2.*np.pi*t/.32+.25)
    broad = np.sin(2.*np.pi*t/.66)
    phase = (8.*theta-np.pi+1.8*np.sin(2.*theta)*slow
             +.45*np.sin(4.*theta)*broad)
    angular_derivative = (8.+3.6*np.cos(2.*theta)*slow
                          +1.8*np.cos(4.*theta)*broad)
    if np.any(angular_derivative < 2.6-1e-12):
        raise ValueError('Primary material phase reversed its angular ordering.')
    family_gain = .825+.175*np.cos(2.*theta)
    normalized_z = (xyz[:, 2]-lo)/(hi-lo)
    settings = field.RECIPE['envelope']
    height_envelope = PchipInterpolator(settings['knots'], settings['values'],
        extrapolate=False)(normalized_z)
    envelope = _orbit_min(H*.009*height_envelope*(1.-.7*support)*family_gain, pairs)
    profile = ((.5+.5*np.cos(phase))**2-.375)/.625
    if (not np.isfinite(phase).all() or not np.isfinite(envelope).all()
            or np.any(envelope < 0.) or np.any(profile < -.6-1e-12)
            or np.any(profile > 1.+1e-12)):
        raise ValueError('Invalid finite primary phase, envelope or profile.')
    signed_request = envelope*profile
    print('ORDERED_PRIMARY: fresh actual G6 DEPTH08 normals', flush=True)
    normals = field._input_normals(xyz, q)
    normal_sha = _hash(normals)
    zero_normals = int(np.count_nonzero(np.linalg.norm(normals, axis=1) == 0.))
    raw = normals*signed_request[:, None]
    del normals
    delta = flow._average_delta(raw, q, degree)
    del raw, degree
    norms = np.linalg.norm(delta, axis=1)
    cap_scale = np.divide(envelope, norms, out=np.ones_like(envelope), where=norms > 0.)
    delta *= np.minimum(1., cap_scale)[:, None]
    delta[envelope == 0.] = 0.
    delta = field._transport(delta, ids, pairs)[0]
    norms = np.linalg.norm(delta, axis=1)
    cap_violation = float(np.max(norms-envelope, initial=0.))
    displacement_symmetry = _symmetry_error(delta, ids, pairs)
    source_symmetry = _symmetry_error(xyz, ids, pairs)
    out = xyz+delta
    output_symmetry = _symmetry_error(out, ids, pairs)
    if (cap_violation > 1e-12 or displacement_symmetry > 1e-12
            or output_symmetry > source_symmetry+1e-12
            or not np.isfinite(out).all()):
        raise ValueError('Primary displacement exceeded its budget or actual reflection symmetry.')
    metadata = dict(
        implementation='MATERIAL_ORDERED_BROAD_PRIMARY_FOLDS_V1',
        source_generation=6, output_generation=6, added_CC_passes=0,
        added_topology_events=0, normal_field_passes=1,
        coordinates='t=actual inherited chart[:,0]; theta=atan2(abs(chart[:,2]),abs(chart[:,1])); canonical minimum-ID actual reflection orbit. Actual source Z is used only for the height envelope.',
        phase='8*theta-pi+1.8*sin(2*theta)*sin(2*pi*t/.32+.25)+.45*sin(4*theta)*sin(2*pi*t/.66)',
        phase_cycles_per_quarter=2, old_phase_cycles_per_quarter=5,
        profile='((.5+.5*cos(phase))**2-.375)/.625',
        analytic_profile_bounds=[-.6, 1.], actual_profile_range=[float(profile.min()), float(profile.max())],
        family_gain='.825+.175*cos(2*material_theta)',
        actual_family_gain_range=[float(family_gain.min()), float(family_gain.max())],
        envelope='orbit_min(H*.009*PCHIP(actual_normalized_source_Z)*(1-.7*actual_feature_support)*family_gain)',
        envelope_PCHIP=settings.copy(), physical_height_reference=H,
        actual_source_z_bounds=[lo, hi], actual_source_height=hi-lo,
        absolute_amplitude_bound=.009*H,
        envelope_quantiles=np.quantile(envelope, [0., .1, .5, .9, .99, 1.]).tolist(),
        actual_phase_range=[float(phase.min()), float(phase.max())],
        analytic_fixed_material_t_dphase_dtheta_lower_bound=2.6,
        actual_fixed_material_t_dphase_dtheta_minimum=float(angular_derivative.min()),
        reflection_seams='Phase is -pi at theta=0 and 3*pi at theta=pi/2. The cos-squared primary profile has zero phase derivative at both seams.',
        displacement_filter='Exactly one frozen .5*self+.5*uniform_actual_edge_neighbor_mean on the new delta only, then pointwise norm cap and actual-ID mirror-vector transport.',
        source_geometry_averaged=False, geometry_associations_unchanged=True,
        maximum_actual_displacement=float(norms.max(initial=0.)),
        displacement_norm_quantiles=np.quantile(norms, [0., .1, .5, .9, .99, 1.]).tolist(),
        actual_moved_control_vertices=int(np.count_nonzero(norms)),
        maximum_pointwise_budget_violation=cap_violation,
        maximum_delta_XY_symmetry_error=displacement_symmetry,
        maximum_source_XY_symmetry_error=source_symmetry,
        maximum_output_XY_symmetry_error=output_symmetry,
        zero_actual_input_normal_count=zero_normals,
        input_xyz_sha256=_hash(xyz), input_quads_sha256=_hash(q),
        unchanged_material_chart_sha256=_hash(chart), actual_feature_support_sha256=_hash(support),
        actual_source_normal_sha256=normal_sha, parent_phase_sha256=_hash(phase),
        parent_envelope_sha256=_hash(envelope), delta_primary_sha256=_hash(delta),
        output_xyz_sha256=_hash(out),
        source_hashes={str(path): _file_hash(path) for path in [Path(__file__).resolve()]+helper_paths()},
        limitations='One authored whole-body primary replacement, not semantic ridge detection, recursive topology growth, a global collision certificate or a claim of visual success. The caller must bind actual input files and render the actual descendant result.')
    state = dict(phase=phase, envelope=envelope, delta_primary=delta,
        family_gain=family_gain, material_t=t, material_theta=theta,
        normalized_z=normalized_z, profile=profile)
    return out, phase, envelope, metadata, state
