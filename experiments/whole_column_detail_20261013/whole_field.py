"""One authored whole-column MIDDLE -> FINE normal-displacement sequence.

This applies the existing incident-unit-face-normal displacement principle to
an actual dense G6. It adds neither a subdivision pass nor topology events.
Wavelengths and amplitudes use the physical incoming full-column height.
The fixed authored field is a CHESHIRE design recipe, not a reconstruction of
the unpublished IAAC, Hansmeyer, or Digital Grotesque implementation.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

import numpy as np
from scipy.interpolate import PchipInterpolator

REPO = Path(__file__).resolve().parents[2]
if str(REPO/'src') not in sys.path:
    sys.path.insert(0, str(REPO/'src'))
from cheshire.reference_subdivision import ArrayMesh, unit  # noqa: E402


STAGES = ('MIDDLE', 'FINE')
RECIPE = {
    'schema': 'CHESHIRE_WHOLE_COLUMN_FIXED_FIELD_V1',
    'source_generation': 6,
    'output_generation': 6,
    'added_CC_passes': 0,
    'added_topology_events': 0,
    'sequence': list(STAGES),
    'coordinates': 'z=(actual_input_Z-zmin)/actual_input_height; theta=atan2(abs(actual_input_Y),abs(actual_input_X))',
    'middle_phase': '20*theta+2*sin(2*theta)*sin(2*pi*z/.085)+.8*sin(4*theta)*sin(2*pi*z/.17)+.35*sin(6*theta)*sin(2*pi*z/.037)',
    'fine_phase': '72*theta+3.5*sin(2*theta)*sin(2*pi*z/.023)+.9*sin(6*theta)*sin(2*pi*z/.049)+1.2*sin(4*theta)*sin(phi_middle)',
    'profile': '((.5+.5*cos(phi))**3-.3125)/.6875',
    'profile_scope': 'Range [-5/11,1]; zero mean for uniform phase sampling, not guaranteed zero angular mean after phase warping.',
    'envelope': {
        'interpolation': 'PCHIP',
        'knots': [0., .05, .20, .38, .50, .64, .80, .94, 1.],
        'values': [0., .40, 1., .85, .55, 1., 1., .45, 0.],
    },
    'middle_amplitude_height_fraction': .006,
    'middle_feature_attenuation': '1-.55*actual_inherited_vertex_feature_support',
    'fine_amplitude_height_fraction': .0018,
    'fine_middle_modulation': '.7+.3*cos(phi_middle)**2',
    'fine_feature_attenuation': '1-.25*actual_inherited_vertex_feature_support',
    'normal': 'Normalize the arithmetic mean of incident actual-input unit face normals; recompute for each stage.',
    'normal_implementation': 'Chunked quad-centroid cross-sum face normals and incident accumulation; mathematically identical to reference_subdivision.fields(...)[nv], without edge topology/scale work.',
    'reflection': 'Evaluate actual full input, then transport minimum-ID orbit representative displacement through actual commuting X/Y involutions; fixed-ID seam normal components are zero.',
    'geometry_scope': 'xyz_out=actual_input_xyz+transported_displacement; faces, classes, rest, anchors, and G6 remain unchanged.',
    'interpretation': 'Fixed CHESHIRE whole-body design sequence; visual success requires matched renders, not numerical displacement alone.',
}


def _hash(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _mirror_pairs(vertex_pairs, count):
    """Validate existing ID correspondence; do not infer or repair symmetry."""
    ids = np.arange(count, dtype=np.int64)
    pairs = {}
    for axis in ('X', 'Y'):
        try:
            pair = np.asarray(vertex_pairs[axis])
        except (KeyError, TypeError) as exc:
            raise ValueError('Actual '+axis+' vertex mirror IDs required.') from exc
        if pair.shape != (count,) or pair.dtype.kind not in 'iu':
            raise ValueError('Actual integer '+axis+' mirror involution required.')
        if np.any(pair < 0) or np.any(pair >= count) or not np.array_equal(pair[pair], ids):
            raise ValueError('Invalid '+axis+' mirror involution; no repair.')
        pairs[axis] = pair
    if not np.array_equal(pairs['X'][pairs['Y']], pairs['Y'][pairs['X']]):
        raise ValueError('Actual X/Y mirror involutions must commute.')
    return ids, pairs


def _input_normals(xyz, faces, chunk_faces=65536):
    """Existing fields() vertex-normal recipe without full edge topology.

    For each actual quad, use the unit sum of the four crosses around its
    arithmetic centroid. Sum those unit face normals at each incident vertex,
    divide by incident face count, then normalize. Only accumulation order
    differs from the existing unchunked fields() implementation.
    """
    count = np.bincount(faces.ravel(), minlength=len(xyz))
    if np.any(count == 0):
        raise ValueError('Orphan controls are not repaired.')
    total = np.zeros_like(xyz, dtype=float)
    for start in range(0, len(faces), chunk_faces):
        quad = faces[start:start+chunk_faces]
        points = xyz[quad]
        relative = points-points.mean(axis=1)[:, None, :]
        face_normals = unit(np.cross(relative, np.roll(relative, -1, axis=1)).sum(axis=1))
        indices = quad.ravel()
        for component in range(3):
            total[:, component] += np.bincount(indices,
                weights=np.repeat(face_normals[:, component], 4), minlength=len(xyz))
    total /= count[:, None]
    return unit(total)


def _profile(phase):
    return ((.5+.5*np.cos(phase))**3-.3125)/.6875


def _middle_phase(theta, z):
    return (20*theta+2*np.sin(2*theta)*np.sin(2*np.pi*z/.085)+
        .8*np.sin(4*theta)*np.sin(2*np.pi*z/.17)+
        .35*np.sin(6*theta)*np.sin(2*np.pi*z/.037))


def _transport(delta, ids, pairs):
    """Reflect canonical vectors, preserving the actual source positions."""
    px, py = pairs['X'], pairs['Y']
    pxy = px[py]
    representative = np.minimum(np.minimum(ids, px), np.minimum(py, pxy))
    # A seam is declared only by the source's fixed-point IDs, never by an
    # epsilon-based XYZ weld. It cannot receive motion through its mirror plane.
    fixed_x, fixed_y = px == ids, py == ids
    delta[fixed_x, 0] = 0.
    delta[fixed_y, 1] = 0.
    reflected = delta[representative].copy()
    reflected[(ids == px[representative]) | (ids == pxy[representative]), 0] *= -1.
    reflected[(ids == py[representative]) | (ids == pxy[representative]), 1] *= -1.
    reflected[fixed_x, 0] = 0.
    reflected[fixed_y, 1] = 0.
    return reflected, representative, fixed_x, fixed_y


def build(mesh, chart, vertex_pairs, feature_support, stage):
    """Return ``(actual G6 ArrayMesh, JSON-safe metadata, NPZ-safe state)``.

    MIDDLE consumes the frozen G6; FINE consumes that actual MIDDLE output.
    The runner binds each parent by file hashes and verifies the final closed
    connected mesh, positive native fan area, and actual reflection symmetry.
    This function never changes its input arrays or reconstructs old geometry.
    """
    if stage not in STAGES or mesh.generation != 6:
        raise ValueError('Declared whole-column stage and actual G6 input required.')
    xyz, faces = np.asarray(mesh.xyz), np.asarray(mesh.faces)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not len(xyz) or not np.isfinite(xyz).all():
        raise ValueError('Finite actual G6 XYZ controls required.')
    if (faces.ndim != 2 or faces.shape[1] != 4 or not len(faces) or
            faces.dtype.kind not in 'iu' or faces.min() < 0 or faces.max() >= len(xyz)):
        raise ValueError('Actual all-quad G6 indices required; no repair.')
    if np.asarray(chart).shape != xyz.shape or not np.isfinite(chart).all():
        raise ValueError('Actual unchanged chart association required.')
    if np.asarray(mesh.classes).shape != (len(xyz),):
        raise ValueError('Actual G6 point classes required.')
    if np.asarray(mesh.rest).shape != xyz.shape or np.asarray(mesh.anchors).shape[0] != len(faces):
        raise ValueError('Actual G6 rest/anchor associations required.')
    support = np.asarray(feature_support, dtype=float)
    if (support.shape != (len(xyz),) or not np.isfinite(support).all() or
            np.any(support < 0) or np.any(support > 1)):
        raise ValueError('Actual inherited vertex feature support in [0,1] required.')
    ids, pairs = _mirror_pairs(vertex_pairs, len(xyz))
    zmin, zmax = float(xyz[:, 2].min()), float(xyz[:, 2].max())
    height = zmax-zmin
    if not np.isfinite(height) or height <= 0:
        raise ValueError('Positive physical whole-column height required.')
    z = (xyz[:, 2]-zmin)/height
    if z.min() < -1e-12 or z.max() > 1+1e-12:
        raise ValueError('Invalid normalized actual height; no extrapolation.')
    z = np.clip(z, 0., 1.)  # Roundoff only; physical source bounds define z.
    theta = np.arctan2(np.abs(xyz[:, 1]), np.abs(xyz[:, 0]))
    middle_phase = _middle_phase(theta, z)
    env = PchipInterpolator(RECIPE['envelope']['knots'],
        RECIPE['envelope']['values'], extrapolate=False)(z)
    normals = _input_normals(xyz, faces)
    if stage == 'MIDDLE':
        phase = middle_phase
        amplitude = height*RECIPE['middle_amplitude_height_fraction']
        attenuation = 1-.55*support
        modulation = np.ones(len(xyz), dtype=float)
    else:
        phase = (72*theta+3.5*np.sin(2*theta)*np.sin(2*np.pi*z/.023)+
            .9*np.sin(6*theta)*np.sin(2*np.pi*z/.049)+
            1.2*np.sin(4*theta)*np.sin(middle_phase))
        amplitude = height*RECIPE['fine_amplitude_height_fraction']
        attenuation = 1-.25*support
        modulation = .7+.3*np.cos(middle_phase)**2
    signed = amplitude*env*modulation*attenuation*_profile(phase)
    displacement, representative, fixed_x, fixed_y = _transport(
        normals*signed[:, None], ids, pairs)
    output_xyz = xyz+displacement
    if not np.isfinite(output_xyz).all():
        raise ValueError('Nonfinite actual whole-column output; no fallback.')
    out = ArrayMesh(output_xyz, faces.copy(), np.asarray(mesh.classes).copy(),
        np.asarray(mesh.rest).copy(), np.asarray(mesh.anchors).copy(), 6)
    out.surface = 'mean'
    displacement_norm = np.linalg.norm(displacement, axis=1)
    metadata = {
        'experiment': 'WHOLE_COLUMN_DETAIL_20261013',
        'stage': stage,
        'recipe': deepcopy(RECIPE),
        'source_generation': 6,
        'output_generation': 6,
        'subdivision_generation': 6,
        'added_CC_passes': 0,
        'added_topology_events': 0,
        'physical_height': height,
        'actual_input_z_bounds': [zmin, zmax],
        'amplitude_bound': amplitude,
        'maximum_actual_displacement': float(displacement_norm.max()),
        'displacement_norm_quantiles': np.quantile(displacement_norm, [0, .5, .9, .99, 1]).tolist(),
        'signed_displacement_quantiles': np.quantile(signed[representative], [0, .5, .9, .99, 1]).tolist(),
        'nonzero_displacement_vertex_count': int(np.count_nonzero(displacement_norm)),
        'nonzero_displacement_vertex_fraction': float(np.count_nonzero(displacement_norm)/len(xyz)),
        'inherited_feature_vertex_count': int(np.count_nonzero(support)),
        'inherited_feature_vertex_fraction': float(np.count_nonzero(support)/len(xyz)),
        'zero_input_normal_count': int(np.count_nonzero(np.linalg.norm(normals, axis=1) == 0)),
        'fixed_x_vertex_count': int(fixed_x.sum()),
        'fixed_y_vertex_count': int(fixed_y.sum()),
        'actual_input_normal_sha256': _hash(normals),
        'input_xyz_sha256': _hash(xyz),
        'input_faces_sha256': _hash(faces),
        'output_faces_sha256': _hash(out.faces),
        'faces_unchanged': True,
        'classes_rest_anchors_unchanged': True,
        'chart_unchanged': True,
        'physical_frequency_scope': 'Height-based axial wavelengths and fixed angular harmonics; no edge-length attenuation or additional subdivision.',
        'reflection_scope': 'Transported displacement is exactly reflected by source IDs; existing source XYZ values are retained, including their original floating-point residuals.',
        'state_scope': 'Input normals are hashed rather than saved; saved displacement_vector plus actual parent XYZ reproduces the output exactly.',
        'validation_scope': 'No claim of visual success, collision freedom, or watertight geometric embedding. Runner checks actual mesh and rendered result.',
    }
    state = {
        'directional_phase': phase,
        'signed_displacement': signed[representative],
        'envelope': env,
        'feature_support': support,
        'displacement_vector': displacement,
        'mirror_x_vertex_pairs': pairs['X'],
        'mirror_y_vertex_pairs': pairs['Y'],
    }
    return out, metadata, state
