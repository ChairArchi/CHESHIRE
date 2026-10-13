"""Bounded source fairing, then one finite fork-shaped normal relief on G7.

Unlike the earlier delta-only finishes, the first stage explicitly averages
the actual source geometry.  Only its final accumulated motion is capped.
The second stage makes finite stem/two-arm surface folds, not new topology or
demonstrated botanical branching.  All coefficients below form one fixed
authored CHESHIRE recipe; importing this file generates no geometry.
"""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_spec = importlib.util.spec_from_file_location('finite_fork_existing_medium_helpers',
    HERE.parent/'medium_root_folds_20261013/root_folds.py')
previous = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = previous
_spec.loader.exec_module(previous)
base, parent, field, finish = previous.base, previous.parent, previous.field, previous.finish

RECIPE = {
    'schema': 'CHESHIRE_BOUNDED_FAIRING_FINITE_FORK_V2',
    'revision_reason': 'One visual correction after trial01: fork readability and mesh-scale zipper reduction were insufficient. Same original SPAN baseline; no stacking trial01 geometry.',
    'source_generation': 7, 'output_generation': 7,
    'sequence': ['BOUNDED_SOURCE_TAUBIN', 'FINITE_FORK_NORMAL_RELIEF'],
    'added_CC_passes': 0, 'added_topology_events': 0,
    'normal_field_passes': 1, 'added_mandelbulb_evaluations': 0,
    'source_geometry_averaged': True,
    'geometry_smoothing_steps': 72, 'taubin_pairs': 36,
    'taubin_lambda': .50, 'taubin_mu': -.53,
    'taubin_equation': 'Xnext=X+c*E*L(X); L(X)=2*(S(X)-X); S(X)=.5*X+.5*uniform_actual_quad_edge_neighbor_mean(X)',
    'fairing_envelope': 'E=PCHIPenv(z)*(1-feature_support), applied in every positive and negative substep',
    'fairing_cap_height_fraction': .0015,
    'fairing_cap_scope': 'Cap final accumulated source delta only; no per-substep clipping. Then actual-ID reflection.',
    'fairing_interpretation': 'Bounded source geometry averaging. The displacement cap does not prove exact silhouette or low-frequency preservation.',
    'envelope': deepcopy(field.RECIPE['envelope']),
    'coordinates': 'Fixed inherited parent_phase/z/support/H; theta=atan2(abs(actual_original_source_Y),abs(actual_original_source_X)). Neither phase nor height is re-inferred after fairing.',
    'ribbon_coordinate': 'u=atan2(sin(parent_phase),cos(parent_phase)); r=abs(u)-1.55',
    'ribbon_mask': 'One inside abs(r)<=.75; quintic fade to zero at abs(r)>=1.20',
    'axial_centres': [.16, .29, .43, .57, .72, .86],
    'axial_stagger': '.018*sin(6*theta)**2; continuous and mirror-smooth, common to all centres at each vertex',
    'pulse_length_height_fraction': .10, 'pulse_half_length_height_fraction': .05,
    'pulse_progress': 's=(z-centre-stagger)/.05; only abs(s)<1 participates',
    'pulse_PCHIP_knots': [-1., -.85, -.50, 0., .50, .85, 1.],
    'pulse_PCHIP_values': [0., 0., .70, 1., .70, 0., 0.],
    'fork_centre': 'a=.70*quintic_smoothstep(clip((s+.40)/.80,0,1)); two transverse centres r=+a and r=-a',
    'kernel': 'K(t)=max(0,1-t*t)**3 for abs(t)<1, otherwise zero',
    'one_arm_profile': 'R(t)=K(t/.45)-.35*K(t/.85)',
    'fork_profile': '(R(r-a)+R(r+a))/1.30',
    'fork_profile_conservative_range': [-7/13, 1.],
    'profile_bound_derivation': 'Each R is between -.35 and .65; two arms divided by 1.30 give [-7/13,1]. At a=0,r=0 the stem is 1; at a=.70,r=+/-.70 the separated arm is .50 before envelopes.',
    'fold_amplitude_height_fraction': .0055,
    'fold_signed_request': '.0055*H*PCHIPenv(z)*(1-support)*ribbon_mask*pulse_PCHIP(s)*fork_profile',
    'normal': field.RECIPE['normal'],
    'normal_implementation': field.RECIPE['normal_implementation'],
    'normal_pooling_steps': 3,
    'normal_pooling_scope': 'Three topological uniform quad-edge averages of actual fairing-surface normals, then unit normalization; not a fixed physical footprint.',
    'delta_smoothing_steps': 3,
    'delta_smoothing_scope': 'Three existing S averages of only the newly requested fold delta; source geometry is not an operand in this second filter.',
    'fully_protected_controls': 'Exact support==1 controls and z endpoints remain fixed in both final deltas; filtering may create a three-edge relief halo elsewhere.',
    'reflection': 'Actual commuting X/Y source involutions; canonical vector transport, fixed-ID seam components zero; no XYZ welding or reflection repair.',
    'geometry_scope': 'SourceXYZ+delta_fairing+delta_fold; G7 topology/classes/rest/anchors/chart unchanged.',
    'interpretation': 'One authored finite fork-shaped surface relief after bounded fairing. Not topological branching, reference-exact implementation, or established visual success.',
}


def code_hashes():
    result = previous.code_hashes()
    result[Path(__file__).resolve().relative_to(REPO).as_posix()] = base.digest(__file__)
    return result


def _hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def _quintic(value):
    value = np.clip(np.asarray(value, float), 0., 1.)
    return value**3*(10.+value*(-15.+6.*value))


def _kernel(value):
    value = np.asarray(value, float)
    return np.where(np.abs(value) < 1., np.maximum(0., 1-value*value)**3, 0.)


def _arm(value):
    return _kernel(value/.45)-.35*_kernel(value/.85)


def _fork(r, s):
    """Finite, smoothly splitting pair; the 1.30 divisor bounds overlap."""
    a = .70*_quintic((s+.40)/.80)
    return (_arm(r-a)+_arm(r+a))/1.30


def _stats(delta, height, bound, chunk=262144):
    maximum, sum_squared, moved = 0., 0., 0
    for start in range(0, len(delta), chunk):
        values = delta[start:start+chunk]
        squared = np.einsum('ij,ij->i', values, values)
        maximum = max(maximum, float(np.sqrt(squared.max(initial=0.))))
        sum_squared += float(squared.sum())
        moved += int(np.count_nonzero(squared))
    return dict(amplitude_norm_bound=float(bound), maximum_actual_displacement=maximum,
                maximum_actual_height_fraction=maximum/height,
                rms_actual_displacement=float(np.sqrt(sum_squared/len(delta))),
                nonzero_displacement_vertex_count=moved,
                nonzero_displacement_vertex_fraction=moved/len(delta),
                displacement_vector_sha256=_hash(delta), statistics_scope='Chunked exact max/count/RMS; no sampled quantiles')


def _sum_stats(first, second, height, bound, chunk=262144):
    maximum, sum_squared, moved = 0., 0., 0
    for start in range(0, len(first), chunk):
        values = first[start:start+chunk]+second[start:start+chunk]
        squared = np.einsum('ij,ij->i', values, values)
        maximum = max(maximum, float(np.sqrt(squared.max(initial=0.))))
        sum_squared += float(squared.sum())
        moved += int(np.count_nonzero(squared))
    return dict(amplitude_norm_bound=float(bound), maximum_actual_displacement=maximum,
                maximum_actual_height_fraction=maximum/height,
                rms_actual_displacement=float(np.sqrt(sum_squared/len(first))),
                nonzero_displacement_vertex_count=moved,
                nonzero_displacement_vertex_fraction=moved/len(first),
                statistics_scope='Chunked exact sum-delta max/count/RMS; no full temporary total-delta array')


def _bounded_fairing(xyz, faces, degree, envelope, protected, ids, pairs, height):
    points = xyz.copy()
    for _ in range(36):
        for coefficient in (.50, -.53):
            update = finish.uniform_displacement_pass(points, faces, degree)
            update -= points
            update *= 2*coefficient
            update *= envelope[:, None]
            points += update
            del update
    delta = points-xyz
    del points
    bound, capped, raw_maximum = height*.0015, 0, 0.
    for start in range(0, len(delta), 262144):
        value = delta[start:start+262144]
        norm = np.linalg.norm(value, axis=1)
        raw_maximum = max(raw_maximum, float(norm.max(initial=0.)))
        capped += int(np.count_nonzero(norm > bound))
        value *= np.minimum(1., bound/np.maximum(norm, 1e-30))[:, None]
    delta[protected] = 0.
    delta = field._transport(delta, ids, pairs)[0]
    return delta, dict(uncapped_maximum_actual_displacement=raw_maximum,
                       cap_applied_vertex_count=capped, cap_applied_vertex_fraction=capped/len(delta))


def _relief_profile(xyz, phase, z, chunk=262144):
    """Evaluate six non-overlapping finite pulses with bounded temporaries."""
    profile = np.zeros(len(xyz), float)
    pulse_mask = np.zeros(len(xyz), float)
    ribbon_mask = np.zeros(len(xyz), float)
    pulse_index = np.full(len(xyz), -1, np.int8)
    interpolator = field.PchipInterpolator(RECIPE['pulse_PCHIP_knots'],
        RECIPE['pulse_PCHIP_values'], extrapolate=False)
    centres = np.asarray(RECIPE['axial_centres'])
    for start in range(0, len(xyz), chunk):
        stop = min(start+chunk, len(xyz))
        current = xyz[start:stop]
        theta = np.arctan2(np.abs(current[:, 1]), np.abs(current[:, 0]))
        stagger = .018*np.sin(6*theta)**2
        wrapped = np.arctan2(np.sin(phase[start:stop]), np.cos(phase[start:stop]))
        r = np.abs(wrapped)-1.55
        mask = 1-_quintic((np.abs(r)-.75)/.45)
        ribbon_mask[start:stop] = mask
        distance = z[start:stop, None]-centres[None, :]-stagger[:, None]
        index = np.argmin(np.abs(distance), axis=1)
        s = distance[np.arange(len(current)), index]/.05
        active = np.abs(s) < 1.
        pulse = interpolator(np.clip(s, -1., 1.))
        pulse[~active] = 0.
        profile[start:stop] = mask*pulse*_fork(r, s)
        pulse_mask[start:stop] = mask*pulse
        pulse_index[start:stop] = np.where(active & (mask > 0), index, -1)
    return profile, pulse_mask, ribbon_mask, pulse_index


def build(mesh, chart, vertex_pairs, parent_phase, normalized_z, feature_support, height):
    """Return (actual G7 ArrayMesh, JSON-safe metadata, minimal array evidence)."""
    xyz, faces = np.asarray(mesh.xyz), np.asarray(mesh.faces)
    if (mesh.generation != 7 or xyz.ndim != 2 or xyz.shape[1] != 3 or
            not len(xyz) or not np.isfinite(xyz).all()):
        raise ValueError('Finite actual saved source G7 required.')
    if (faces.ndim != 2 or faces.shape[1] != 4 or not len(faces) or
            faces.dtype.kind not in 'iu' or faces.min() < 0 or faces.max() >= len(xyz)):
        raise ValueError('Actual all-quad G7 topology required; no repair.')
    if (np.asarray(chart).shape != xyz.shape or not np.isfinite(chart).all() or
            np.asarray(mesh.classes).shape != (len(xyz),) or
            np.asarray(mesh.rest).shape != xyz.shape or len(mesh.anchors) != len(faces)):
        raise ValueError('Actual unchanged G7 associations/chart required.')
    phase = parent._vector(parent_phase, len(xyz), 'parent phase')
    z = np.clip(parent._vector(normalized_z, len(xyz), 'normalized height', -1e-12, 1+1e-12), 0., 1.)
    support = parent._vector(feature_support, len(xyz), 'feature support', 0., 1.)
    height = float(height)
    if not np.isfinite(height) or height <= 0:
        raise ValueError('Positive inherited full-column height required.')
    ids, pairs = field._mirror_pairs(vertex_pairs, len(xyz))
    degree = np.bincount(faces.ravel(), minlength=len(xyz))
    if np.any(degree == 0):
        raise ValueError('Orphan controls are not repaired.')
    envelope = field.PchipInterpolator(RECIPE['envelope']['knots'],
        RECIPE['envelope']['values'], extrapolate=False)(z)*(1-support)
    protected = (support == 1.) | (z == 0.) | (z == 1.)
    input_hash = _hash(xyz)
    print('FINITE_FORK: bounded actual source Taubin 36 pairs', flush=True)
    delta_fairing, cap_info = _bounded_fairing(xyz, faces, degree, envelope, protected, ids, pairs, height)
    fairing_xyz = xyz+delta_fairing
    if not np.isfinite(fairing_xyz).all():
        raise ValueError('Nonfinite bounded fairing; no fallback.')
    fairing_hash = _hash(fairing_xyz)
    fairing_stats = dict(_stats(delta_fairing, height, height*.0015), **cap_info)

    print('FINITE_FORK: actual fairing normals; topological normal pooling 3 steps', flush=True)
    normals = field._input_normals(fairing_xyz, faces)
    input_normal_hash = _hash(normals)
    for _ in range(3):
        normals = finish.uniform_displacement_pass(normals, faces, degree)
    normals = field.unit(normals)
    pooled_normal_hash = _hash(normals)
    profile, pulse_mask, ribbon_mask, pulse_index = _relief_profile(xyz, phase, z)
    signed = height*.0055*envelope*profile
    signed_range = [float(signed.min()), float(signed.max())]
    raw_delta = normals*signed[:, None]
    raw_delta_hash = _hash(raw_delta)
    del normals, signed, profile, envelope
    print('FINITE_FORK: new fold delta uniform pooling 3 steps then ID reflection', flush=True)
    for _ in range(3):
        raw_delta = finish.uniform_displacement_pass(raw_delta, faces, degree)
    raw_delta[protected] = 0.
    delta_fold = field._transport(raw_delta, ids, pairs)[0]
    del raw_delta, degree, ids
    output_xyz = fairing_xyz+delta_fold
    del fairing_xyz
    if not np.isfinite(output_xyz).all():
        raise ValueError('Nonfinite finite-fork output; no fallback.')
    if not np.array_equal(output_xyz[protected], xyz[protected]):
        raise ValueError('Fully protected source controls moved; no repair.')
    fold_stats = _stats(delta_fold, height, height*.0055)
    total_stats = _sum_stats(delta_fairing, delta_fold, height, height*.0070)
    if (fairing_stats['maximum_actual_displacement'] > height*.0015*(1+1e-12) or
            fold_stats['maximum_actual_displacement'] > height*.0055*(1+1e-12)):
        raise ValueError('Declared final component displacement bound exceeded.')
    out = field.ArrayMesh(output_xyz, mesh.faces, mesh.classes, mesh.rest, mesh.anchors, 7)
    out.surface = 'mean'
    metadata = dict(experiment='FINITE_FORK_FOLDS_20261013', recipe=deepcopy(RECIPE),
        source_generation=7, output_generation=7, added_CC_passes=0,
        added_topology_events=0, normal_field_passes=1, added_mandelbulb_evaluations=0,
        source_geometry_averaged=True, geometry_smoothing_steps=72,
        taubin_pairs=36, taubin_lambda=.50, taubin_mu=-.53,
        fairing_cap_height_fraction=.0015, normal_pooling_steps=3,
        normal_pooling_scope=RECIPE['normal_pooling_scope'], delta_smoothing_steps=3,
        inherited_height=height, input_xyz_sha256=input_hash, fairing_xyz_sha256=fairing_hash,
        output_xyz_sha256=_hash(output_xyz), input_vertex_normal_sha256=input_normal_hash,
        pooled_vertex_normal_sha256=pooled_normal_hash, raw_fold_delta_sha256=raw_delta_hash,
        signed_fold_request_range=signed_range, fairing=fairing_stats, fold=fold_stats,
        total_displacement=total_stats, pulse_support=parent._mask_stats(pulse_mask),
        ribbon_support=parent._mask_stats(ribbon_mask),
        fully_protected_control_count=int(np.count_nonzero(protected)),
        fully_protected_controls_unchanged=True,
        input_faces_sha256=_hash(faces), input_chart_sha256=_hash(chart),
        input_classes_sha256=_hash(mesh.classes), input_rest_sha256=_hash(mesh.rest),
        input_anchors_sha256=_hash(mesh.anchors), geometry_code_sha256=code_hashes(),
        taubin_precedent=dict(path='experiments/fold_visible_gate_20261012/detail_finish.py',
            sha256=base.digest(HERE.parent/'fold_visible_gate_20261012/detail_finish.py'),
            scope='Existing bounded lambda/mu source-relaxation precedent; its G3 runner is not called.'),
        input_mutated=False, topology_associations_preserved=True,
        interpretation=RECIPE['interpretation'], visual_status='PENDING_MATCHED_RENDER')
    state = dict(delta_fairing=delta_fairing, delta_fold=delta_fold,
        parent_phase=phase, normalized_z=z, feature_support=support,
        finite_pulse_mask=pulse_mask, ribbon_mask=ribbon_mask, finite_pulse_index=pulse_index,
        mirror_x_vertex_pairs=pairs['X'], mirror_y_vertex_pairs=pairs['Y'])
    return out, metadata, state
