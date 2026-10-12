"""One coupled CC G04 -> G05 step with a bounded two-factor rule comparison.

The coefficients below are a new local-scale hypothesis, not an exact replay
of the old decoupled/frozen-world-length late-detail experiment.  The support
comes from actual G03 event ownership and the actual intervening CC parent-face
map.  Event roles (source/wall/cap) are never used as V/E/F point classes.

Completed face points feed edge and vertex rules.  Consequently a zero direct
control at a point does not imply that its final XYZ stays unchanged; there is
an incident-face coupling halo.  No coordinate restoration or averaging is
performed here.  The runner independently propagates and verifies reflection
correspondence from the frozen parent.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO / 'src') not in sys.path:
    sys.path.insert(0, str(REPO / 'src'))

from cheshire.reference_subdivision import (  # noqa: E402
    LOCAL_INCIDENT_SCALE, WEIGHTS, mean_incident, subdivide, topology,
)

MODES = ('NEUTRAL', 'EQ4_ONLY', 'NORMAL_ONLY', 'COMBINED')
SUPPORT_POLICY = {
    'source': 'G03 actual face_event_ids > 0 (root and accepted child territory)',
    'face': 'G04 face inherits G03 support through actual G04 evidence parent_face',
    'edge': 'arithmetic mean of the two G04 incident-face supports',
    'vertex': 'arithmetic mean of all G04 incident-face supports',
    'coupling': 'completed new face points feed edge and vertex rules; no XYZ pinning',
}
RECIPE = {
    'schema': 'LATE_DETAIL_COUPLED_2X2_V1',
    'source_generation': 4,
    'output_generation': 5,
    'subdivision_passes_added': 1,
    'scale_mode': LOCAL_INCIDENT_SCALE,
    'eq4': {'w3': 1.8, 'w4': 0.6},
    'normal': {'wf': 0.8, 'we': -0.2, 'wp': 0.4},
    'fixed_zero': ['w1', 'w2', 'w6', 'w7'],
    'factors': {
        'NEUTRAL': {'eq4': False, 'normal': False},
        'EQ4_ONLY': {'eq4': True, 'normal': False},
        'NORMAL_ONLY': {'eq4': False, 'normal': True},
        'COMBINED': {'eq4': True, 'normal': True},
    },
    'coefficient_scope': 'new hypothesis; dimensionless coefficients times current local incident scale',
    'class_scope': 'actual G04 previous-point V=0/E=1/F=2 classes only; invalid face patterns use declared Eq1 fallback',
    'ownership_scope': 'event ownership defines spatial support, not point classes or DS roles',
    'support_policy': deepcopy(SUPPORT_POLICY),
}


def _hash(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _integer_vector(evidence, key, size=None):
    """Accept a plain dict or an open np.load(...npz) mapping, without coercion."""
    try:
        value = np.asarray(evidence[key])
    except (KeyError, TypeError) as exc:
        raise ValueError('Missing actual provenance array: ' + key) from exc
    if value.ndim != 1 or value.dtype.kind not in 'iu':
        raise ValueError('Integer one-dimensional provenance required: ' + key)
    if size is not None and value.shape != (size,):
        raise ValueError('Wrong provenance length: ' + key)
    return value


def _eligible(mesh):
    """The reference Eq4 pattern, independently exposed as a saved diagnostic."""
    classes = mesh.classes[mesh.faces]
    valid = ((classes == 0).sum(1) == 1)
    valid &= ((classes == 1).sum(1) == 2) & ((classes == 2).sum(1) == 1)
    previous = np.argmax(classes == 0, axis=1)
    face = np.argmax(classes == 2, axis=1)
    return valid & ((previous + 2) % 4 == face)


def build(mesh, g4_evidence, g3_evidence, mode):
    """Return ``(G05 ArrayMesh, JSON-safe metadata, NPZ-safe state)``.

    ``mesh`` is the frozen actual G04 CC control mesh. ``g4_evidence`` must
    contain its actual ``parent_face`` map to G03; ``g3_evidence`` must contain
    actual ``face_event_ids``. NpzFile mappings and dictionaries are accepted.
    The caller retains responsibility for matching these arrays to their
    source hashes and for propagating exact reflection IDs through this step.
    Input arrays are never modified. No large mesh is loaded by this module.
    """
    if mode not in MODES:
        raise ValueError('Unknown late-detail mode: ' + str(mode))
    if mesh.generation != RECIPE['source_generation']:
        raise ValueError('The actual frozen G04 parent is required.')
    xyz = np.asarray(mesh.xyz)
    faces = np.asarray(mesh.faces)
    classes = np.asarray(mesh.classes)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError('Finite actual parent XYZ required.')
    if faces.ndim != 2 or faces.shape[1] != 4 or faces.dtype.kind not in 'iu':
        raise ValueError('Actual all-quad CC parent required; no topology repair.')
    if faces.size == 0 or faces.min() < 0 or faces.max() >= len(xyz):
        raise ValueError('Valid actual all-quad face indices required.')
    if classes.shape != (len(xyz),) or classes.dtype.kind not in 'iu':
        raise ValueError('Actual G04 point classes required; no fabricated classes.')
    if not np.isin(classes, [-1, 0, 1, 2]).all():
        raise ValueError('Unknown actual point class; no reinterpretation.')
    t = topology(mesh)
    if np.any(t['degree'] == 0):
        raise ValueError('Orphan input vertices are not repaired.')
    parent = _integer_vector(g4_evidence, 'parent_face', len(faces))
    owners = _integer_vector(g3_evidence, 'face_event_ids')
    if not len(owners) or parent.min() < 0 or parent.max() >= len(owners):
        raise ValueError('G04 parent_face must index actual G03 ownership.')
    if np.any(owners < 0):
        raise ValueError('G03 event IDs must be nonnegative actual ownership.')

    face_support = (owners[parent] > 0).astype(float)
    edge_support = face_support[t['ef']].mean(axis=1)
    vertex_support = mean_incident(np.repeat(face_support, t['n']), t['a'], len(xyz))
    eligible = _eligible(mesh)
    factors = RECIPE['factors'][mode]
    kind = {'wf': 'face', 'w1': 'edge', 'we': 'edge', 'w2': 'vertex',
            'wp': 'vertex', 'w3': 'face', 'w4': 'face', 'w6': 'face', 'w7': 'edge'}
    supports = {'face': face_support, 'edge': edge_support, 'vertex': vertex_support}
    controls = {key: np.zeros_like(supports[kind[key]]) for key in WEIGHTS}
    if factors['eq4']:
        for key, coefficient in RECIPE['eq4'].items():
            controls[key] = supports[kind[key]] * coefficient
    if factors['normal']:
        for key, coefficient in RECIPE['normal'].items():
            controls[key] = supports[kind[key]] * coefficient

    out, metadata, state = subdivide(mesh, {'weights': {key: 0. for key in WEIGHTS}},
        scale_mode=LOCAL_INCIDENT_SCALE, resolved_controls=controls)
    out.surface = 'mean'
    if metadata['eq4_eligible'] != int(eligible.sum()):
        raise RuntimeError('Reference Eq4 eligibility and saved diagnostic disagree.')
    metadata.update(
        experiment='LATE_DETAIL_RULES_20261013', mode=mode,
        recipe=deepcopy(RECIPE), support_policy=deepcopy(SUPPORT_POLICY),
        factors=deepcopy(factors), source_generation=int(mesh.generation),
        output_generation=int(out.generation), subdivision_passes_added=1,
        field_iterations=0, native_surface='mean polygon fan (runner export)',
        actual_class_counts={str(c): int((classes == c).sum()) for c in (-1, 0, 1, 2)},
        supported_face_count=int(face_support.sum()),
        supported_eq4_eligible_count=int((eligible & (face_support > 0)).sum()),
        supported_eq4_fallback_count=int((~eligible & (face_support > 0)).sum()),
        partially_supported_edge_count=int(((edge_support > 0) & (edge_support < 1)).sum()),
        partially_supported_vertex_count=int(((vertex_support > 0) & (vertex_support < 1)).sum()),
        source_array_hashes={name: _hash(value) for name, value in {
            'xyz': xyz, 'faces': faces, 'classes': classes,
            'g4_parent_face': parent, 'g3_face_event_ids': owners}.items()},
        interpretation='Coupled factorial from one frozen G04; final visual success is not inferred from technical validity.',
        amplitude_scope='No total-displacement cap; local normal coefficients are new comparison choices, not user constraints.',
    )
    state.update(
        input_face_support=face_support, input_edge_support=edge_support,
        input_vertex_support=vertex_support, input_g4_to_g3_face_ids=parent.copy(),
        input_g3_face_event_ids=owners.copy(), input_point_classes=classes.copy(),
        eq4_eligible_mask=eligible,
    )
    return out, metadata, state
