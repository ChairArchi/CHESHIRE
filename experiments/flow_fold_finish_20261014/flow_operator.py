"""Broad continuous signed fine folds tied to the saved parent flow.

One source-normal displacement is averaged once and mirrored by actual IDs.
No per-cell roof, new topology, sparse warpage mask, or source averaging.
"""
from pathlib import Path
import hashlib
import importlib.util

import numpy as np

HERE = Path(__file__).resolve().parent
FIELD_PATH = HERE.parent/'whole_column_detail_20261013/whole_field.py'
AVERAGE_RECIPE_PATH = HERE.parent/'parent_linked_folds_20261013/smooth_relief.py'
UNIT_PATH = HERE.parents[1]/'src/cheshire/reference_subdivision.py'
FIELD_SHA = '4c66d67cb7583acc7d27f65349e2ba5272b3881fb6375efe74a54c811f7fd094'
AVERAGE_RECIPE_SHA = 'd60646629b715eba3a76c10fedeef25b88d59ea3ed6f93d795a84ae065b547cb'
UNIT_SHA = '091e7f1ac3e2255c85ee3d3c2fb5a9bc3b38cbf0723aadea59f3f5ab06a5c16a'
CHUNK = 65536


def _file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


for _path, _sha in ((FIELD_PATH, FIELD_SHA), (AVERAGE_RECIPE_PATH, AVERAGE_RECIPE_SHA),
                   (UNIT_PATH, UNIT_SHA)):
    if _file_hash(_path) != _sha:
        raise ValueError('Frozen existing helper changed: '+str(_path))
_spec = importlib.util.spec_from_file_location('cheshire_continuous_flow_existing_field', FIELD_PATH)
field = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(field)


def helper_paths():
    """Local frozen normal/mirror/unit code and copied averaging recipe."""
    return [FIELD_PATH, AVERAGE_RECIPE_PATH, UNIT_PATH]


def _hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def _smoothstep(value):
    x = np.clip(value, 0., 1.)
    return x*x*x*(10.+x*(-15.+6.*x))


def _average_delta(delta, faces, degree):
    """Frozen smooth_relief uniform_displacement_pass recipe, one pass.

    Reproduced locally to avoid its CLI module's unrelated plain study import.
    On the verified closed quad graph this is .5 self + .5 edge-neighbour mean.
    """
    mean = np.zeros_like(delta)
    for start in range(0, len(faces), CHUNK):
        quad = faces[start:start+CHUNK]
        ids = quad.ravel()
        for component in range(3):
            values = delta[:, component][quad]
            contribution = .5*(np.roll(values, 1, axis=1)+np.roll(values, -1, axis=1))
            mean[:, component] += np.bincount(ids, weights=contribution.ravel(),
                                              minlength=len(delta))
    mean /= degree[:, None]
    mean += delta
    mean *= .5
    return mean


def build(control_xyz, control_quads, parent_phase_unwrapped, normalized_z,
          vertex_pair_x, vertex_pair_y, height):
    """Return ``(output_controls, JSON_metadata, NPZ_state)``; no writes.

    The caller constructs the ordinary arithmetic native fan of these output
    controls. No native fan centre is independently lifted by this operator.
    """
    xyz, q = np.asarray(control_xyz), np.asarray(control_quads)
    if (xyz.ndim != 2 or xyz.shape[1] != 3 or xyz.dtype.kind != 'f' or
            not len(xyz) or not np.isfinite(xyz).all() or q.ndim != 2 or
            q.shape[1] != 4 or q.dtype.kind not in 'iu' or not len(q) or
            q.min() < 0 or q.max() >= len(xyz)):
        raise ValueError('Finite actual G7 all-quad carrier required.')
    count = len(xyz)
    phase, z = np.asarray(parent_phase_unwrapped), np.asarray(normalized_z)
    if (phase.shape != (count,) or z.shape != (count,) or
            not np.isfinite(phase).all() or not np.isfinite(z).all() or
            z.min() < -1e-12 or z.max() > 1+1e-12):
        raise ValueError('Actual inherited unwrapped phase and normalized height required.')
    z = np.clip(z, 0., 1.)  # Inherited coordinate roundoff only.
    height = float(height)
    if not np.isfinite(height) or height <= 0:
        raise ValueError('Positive inherited physical height required.')
    ids, pairs = field._mirror_pairs({'X': vertex_pair_x, 'Y': vertex_pair_y}, count)
    degree = np.bincount(q.ravel(), minlength=count)
    if (degree == 0).any():
        raise ValueError('Source orphan control vertex is not repaired.')
    psi = 12.*phase+2.*np.pi*400.*z
    max_gap = np.zeros(count, float)
    sampled_edge_differences = []
    for start in range(0, len(q), CHUNK):
        quad = q[start:start+CHUNK]
        value = psi[quad]
        gap = np.abs(np.roll(value, -1, axis=1)-value)
        vertex_gap = np.maximum(gap, np.roll(gap, 1, axis=1))
        np.maximum.at(max_gap, quad.ravel(), vertex_gap.ravel())
        # Deterministic representative samples; amplitude limits use ALL edges.
        sampled_edge_differences.append(gap[::32].ravel())
    sampling_gain = np.minimum(1., ((np.pi/2.)/np.maximum(max_gap, 1e-30))**2)
    endfade = _smoothstep(z/.06)*_smoothstep((1.-z)/.06)
    flank = .55+.45*np.sin(phase)**2
    amplitude = height*.00025
    signed_request = amplitude*endfade*flank*sampling_gain*np.cos(psi)
    if not np.isfinite(signed_request).all() or (sampling_gain <= 0).any():
        raise ValueError('Finite continuous nonbinary fine-fold request required.')
    print('FLOW_FINE: actual source normals; one signed continuous displacement', flush=True)
    normals = field._input_normals(xyz, q)
    normal_sha = _hash(normals)
    raw_delta = normals*signed_request[:, None]
    del normals
    raw_norm = np.linalg.norm(raw_delta, axis=1)
    delta = _average_delta(raw_delta, q, degree)
    del raw_delta, degree
    delta = field._transport(delta, ids, pairs)[0]
    output = xyz+delta
    if not np.isfinite(output).all():
        raise ValueError('Nonfinite continuous fine-fold output.')
    norms = np.linalg.norm(delta, axis=1)
    if norms.max(initial=0.) > amplitude*(1.+1e-10):
        raise ValueError('Filtered vector displacement exceeded fixed amplitude bound.')
    actual_changed = 0
    actual_reflection_error = 0.
    for start in range(0, count, CHUNK):
        sl = slice(start, min(start+CHUNK, count))
        indices = ids[sl]
        actual_changed += int(np.count_nonzero(np.any(output[sl] != xyz[sl], axis=1)))
        for axis, pair in ((0, pairs['X']), (1, pairs['Y'])):
            reflected = delta[pair[indices]].copy()
            reflected[:, axis] *= -1
            actual_reflection_error = max(actual_reflection_error,
                float(np.max(np.abs(delta[sl]-reflected))))
    if actual_reflection_error > 1e-12:
        raise ValueError('Actual continuous displacement lost mirror symmetry.')
    edge_samples = np.concatenate(sampled_edge_differences)
    metadata = dict(implementation='INHERITED_PARENT_CONTINUOUS_FINE_FOLDS_V1',
        source_generation=7, output_generation=7, added_CC_passes=0,
        added_topology_events=0, normal_field_passes=1,
        formula='psi=12*saved_unwrapped_parent_phase+2*pi*400*saved_normalized_z',
        signed_request='H*.00025*S(z/.06)*S((1-z)/.06)*(.55+.45*sin(parent_phase)^2)*sampling_gain*cos(psi)',
        smoothstep='S(t)=clip(t,0,1)^3*(10-15*clip(t,0,1)+6*clip(t,0,1)^2)',
        sampling='sampling_gain=min(1,((pi/2)/max_actual_incident_edge_abs_delta_psi)^2); positive, continuous amplitude attenuation, no binary surface support or warpage mask.',
        displacement_filter='Exactly one .5*new_delta+.5*uniform_actual_edge_neighbor_mean(new_delta); actual source geometry is not averaged.',
        physical_height_reference=height, fixed_amplitude_bound=amplitude,
        source_vertices=count, source_quads=len(q), actual_changed_control_vertices=actual_changed,
        raw_signed_request_nonzero_vertices=int(np.count_nonzero(signed_request)),
        final_nonzero_delta_vertices=int(np.count_nonzero(norms)),
        final_nonzero_delta_vertex_fraction=float(np.count_nonzero(norms)/count),
        positive_signed_request_vertices=int(np.count_nonzero(signed_request > 0)),
        negative_signed_request_vertices=int(np.count_nonzero(signed_request < 0)),
        body_endfade_nonzero_vertices=int(np.count_nonzero(endfade)),
        sampling_gain_range=[float(sampling_gain.min()), float(sampling_gain.max())],
        sampling_gain_quantiles=np.quantile(sampling_gain, [.01, .1, .5, .9, .99]).tolist(),
        sampling_gain_below_half_fraction=float(np.mean(sampling_gain < .5)),
        max_incident_phase_gap_quantiles=np.quantile(max_gap, [.1, .5, .9, .99]).tolist(),
        representative_edge_phase_gap_quantiles=np.quantile(edge_samples, [.1, .5, .9, .95, .99]).tolist(),
        representative_edge_phase_below_pi_over2_fraction=float(np.mean(edge_samples < np.pi/2)),
        edge_sample_scope='Every 32nd quad in deterministic 65536-face chunks; all edges used for actual amplitude attenuation.',
        flank_gain_range=[float(flank.min()), float(flank.max())],
        raw_delta_norm_quantiles=np.quantile(raw_norm, [.1, .5, .9, .99, 1.]).tolist(),
        filtered_delta_norm_quantiles=np.quantile(norms, [.1, .5, .9, .99, 1.]).tolist(),
        maximum_delta_XY_symmetry_error=actual_reflection_error,
        source_xyz_sha256=_hash(xyz), output_xyz_sha256=_hash(output),
        unchanged_control_quad_sha256=_hash(q), source_normal_sha256=normal_sha,
        inherited_parent_phase_sha256=_hash(phase), inherited_normalized_z_sha256=_hash(z),
        delta_sha256=_hash(delta), source_geometry_averaged=False,
        fan_centres_independently_lifted=False, native_roof_added=False,
        code_binding={'normal_and_mirror_helper': dict(path=str(FIELD_PATH), sha256=FIELD_SHA),
            'copied_uniform_delta_average_recipe': dict(path=str(AVERAGE_RECIPE_PATH), sha256=AVERAGE_RECIPE_SHA),
            'imported_unit_dependency': dict(path=str(UNIT_PATH), sha256=UNIT_SHA),
            'operator': dict(path=str(Path(__file__).resolve()), sha256=_file_hash(__file__))},
        limits='Inherited authored phase sets variable physical pitch. Geometry effect is continuous across shared controls; numerical checks do not establish visual quality, global collision freedom, or fabrication suitability.')
    state = dict(delta=delta, sampling_gain=sampling_gain.astype(np.float32),
                 endfade=endfade.astype(np.float32))
    return output, metadata, state
