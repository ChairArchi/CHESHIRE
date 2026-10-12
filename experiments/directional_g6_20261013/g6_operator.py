"""One G05 -> G06 directional CC step; two amplitudes, one half-period rule.

The actual frozen DIRECTIONAL G05 is the input, never relabelled as G04.
Actual G05 -> G04 -> G03 face ancestry supplies ownership and reflection signs.
The inherited root frame is fixed; phase, normals and local scales are evaluated
on the actual incoming G05 geometry. Coherent normal compensation remains a
flat regular-scale approximation, not an exact curved-surface offset rule.
"""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(REPO/'src') not in sys.path:
    sys.path.insert(0, str(REPO/'src'))
from cheshire.reference_subdivision import (  # noqa: E402
    LOCAL_INCIDENT_SCALE, WEIGHTS, mean_incident, subdivide, topology,
)

_spec = importlib.util.spec_from_file_location('directional_g6_frozen_root_helper',
    HERE.parent/'coherent_fold_detail_20261013/fold_operator.py')
_fold = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fold)

MODES = ('DEPTH_08', 'DEPTH_16')
RECIPE = {
    'schema': 'DIRECTIONAL_HALF_PERIOD_G6_V1',
    'source_generation': 5, 'output_generation': 6, 'subdivision_passes_added': 1,
    'source_candidate': 'DIRECTIONAL', 'scale_mode': LOCAL_INCIDENT_SCALE,
    'amplitudes': {'DEPTH_08': .8, 'DEPTH_16': 1.6},
    'band': dict(deepcopy(_fold.RECIPE['band']), period_root_radius=.35),
    'normal': {'face': 'face_scalar', 'edge_incident_mean_factor': .5,
               'vertex_incident_mean_factor': '1 - 1 / actual degree'},
    'fixed_zero': ['w1', 'w2', 'w3', 'w4', 'w6', 'w7'],
    'support': 'actual G05 parent_face -> actual G04 parent_face -> G03 face_event_ids > 0',
    'reflection': 'same ancestry maps actual G03 mirror_face_signs to G05 centroids; no absolute-value clamp or XYZ averaging',
    'phase': '2*pi*(minor/.35 + .16*major + .20*sin(.90*major+.31)); root coordinates divided by inherited root radius',
    'coefficient_scope': 'new dimensionless normal amplitudes times actual G05 local incident mean-edge scale',
    'coherence_scope': 'flat regular-scale constant-field approximation; not exact on curved/nonuniform regions',
    'scope': 'two amplitudes at one period; no role/curvature gate, Eq4, new topology event, or Mandelbulb pass',
}


def _int_vector(mapping, key, size=None):
    try:
        value = np.asarray(mapping[key])
    except (KeyError, TypeError) as exc:
        raise ValueError('Missing actual ancestry: '+key) from exc
    if value.ndim != 1 or value.dtype.kind not in 'iu' or (size is not None and value.shape != (size,)):
        raise ValueError('Actual integer ancestry vector required: '+key)
    return value


def _hash(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def build(mesh, g5_evidence, g4_evidence, g3_evidence, mode):
    """Return ``(G06 ArrayMesh, JSON-safe metadata, NPZ-safe state)``.

    Source hash binding to the frozen DIRECTIONAL G05 and actual reflection-ID
    propagation are handled by the runner. Dicts and open NpzFile mappings are
    accepted. No source arrays or frozen module constants are modified.
    """
    if mode not in MODES or mesh.generation != RECIPE['source_generation']:
        raise ValueError('Declared mode and actual DIRECTIONAL G05 parent required.')
    xyz, faces, classes = np.asarray(mesh.xyz), np.asarray(mesh.faces), np.asarray(mesh.classes)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError('Finite actual G05 controls required.')
    if faces.ndim != 2 or faces.shape[1] != 4 or not faces.size or faces.dtype.kind not in 'iu':
        raise ValueError('Actual all-quad G05 required; no repair.')
    if faces.min() < 0 or faces.max() >= len(xyz):
        raise ValueError('Invalid actual G05 face indices.')
    if classes.shape != (len(xyz),) or classes.dtype.kind not in 'iu' or not np.isin(classes, [-1, 0, 1, 2]).all():
        raise ValueError('Actual G05 previous-point classes required.')
    t = topology(mesh)
    if np.any(t['degree'] == 0):
        raise ValueError('Orphan controls are not repaired.')
    parent54 = _int_vector(g5_evidence, 'parent_face', len(faces))
    parent43 = _int_vector(g4_evidence, 'parent_face')
    owners = _int_vector(g3_evidence, 'face_event_ids')
    if not len(parent43) or not len(owners) or parent54.min() < 0 or parent54.max() >= len(parent43):
        raise ValueError('Actual G05 -> G04 face ancestry required.')
    if parent43.min() < 0 or parent43.max() >= len(owners) or np.any(owners < 0):
        raise ValueError('Actual G04 -> G03 ownership ancestry required.')
    try:
        signs = np.asarray(g3_evidence['mirror_face_signs'])
    except (KeyError, TypeError) as exc:
        raise ValueError('Actual G03 mirror face signs required.') from exc
    if signs.shape != (len(owners), 2) or signs.dtype.kind not in 'iu' or not np.isin(signs, [-1, 1]).all():
        raise ValueError('Actual G03 mirror signs must be integer +/-1 pairs.')
    parent53 = parent43[parent54]
    support = (owners[parent53] > 0).astype(float)
    face_signs = signs[parent53]
    frame, radius, basis = _fold._root_frame(g3_evidence)
    centroids = xyz[faces].mean(axis=1)
    canonical = centroids*np.column_stack([face_signs, np.ones(len(faces), int)])
    coordinates = ((canonical-frame['origin']) @ basis[:, :2])/radius
    band_recipe = RECIPE['band']
    long = coordinates[:, 0]
    phase = 2*np.pi*(coordinates[:, 1]/band_recipe['period_root_radius'] +
        band_recipe['major_linear']*long + band_recipe['major_warp_amplitude']*
        np.sin(band_recipe['major_warp_frequency']*long+band_recipe['major_warp_phase']))
    band = np.cos(phase)
    amplitude = RECIPE['amplitudes'][mode]
    scalar = amplitude*support*band
    edge_scalar = scalar[t['ef']].mean(axis=1)
    vertex_scalar = mean_incident(np.repeat(scalar, t['n']), t['a'], len(xyz))
    controls = {key: np.zeros(len(faces) if key in ('wf', 'w3', 'w4', 'w6') else
                             len(xyz) if key in ('wp', 'w2') else len(t['edges'])) for key in WEIGHTS}
    controls['wf'] = scalar
    controls['we'] = .5*edge_scalar
    controls['wp'] = (1-1/t['degree'])*vertex_scalar
    out, metadata, state = subdivide(mesh, {'weights': {key: 0. for key in WEIGHTS}},
        scale_mode=LOCAL_INCIDENT_SCALE, resolved_controls=controls)
    out.surface = 'mean'
    supported_edges = np.all(support[t['ef']] > 0, axis=1)
    phase_delta = phase[t['ef'][:, 1]]-phase[t['ef'][:, 0]]
    phase_abs = np.abs(phase_delta[supported_edges])
    state.update(input_g5_to_g4_face_ids=parent54.copy(), input_g4_to_g3_face_ids=parent43.copy(),
        input_g5_to_g3_face_ids=parent53, input_g3_face_event_ids=owners.copy(),
        input_g3_mirror_face_signs=signs.copy(), input_face_mirror_signs=face_signs,
        input_face_support=support, input_edge_support=support[t['ef']].mean(axis=1),
        input_vertex_support=mean_incident(np.repeat(support, t['n']), t['a'], len(xyz)),
        input_vertex_degree=t['degree'], input_point_classes=classes.copy(),
        root_coordinates=coordinates, face_phase=phase, face_band=band, face_scalar=scalar,
        inherited_root_radius=np.array(radius), physical_wavelength=np.array(.35*radius),
        applied_amplitude=np.array(amplitude))
    state.update({'inherited_root_pca_'+key: value.copy() for key, value in frame.items()})
    metadata.update(experiment='DIRECTIONAL_G6_20261013', mode=mode, recipe=deepcopy(RECIPE),
        source_generation=5, output_generation=6, source_candidate='DIRECTIONAL',
        subdivision_passes_added=1, added_topology_events=0, added_field_passes=0,
        applied_amplitude=amplitude, supported_face_count=int(support.sum()),
        resolved_control_ranges={key: [float(value.min()), float(value.max())] for key, value in controls.items()},
        phase_diagnostics=dict(physical_wavelength=.35*radius,
            cycles_across_inherited_root_minor_extent=float(frame['extent'][1]/(.35*radius)),
            supported_adjacent_edge_count=int(supported_edges.sum()),
            supported_neighbor_unwrapped_phase_abs_quantiles=[] if not len(phase_abs) else
                np.quantile(phase_abs, [0, .5, .9, 1.]).tolist(),
            alias_fraction_over_pi=0. if not len(phase_abs) else float((phase_abs > np.pi).mean()),
            supported_mirror_seam_edge_count=int((supported_edges &
                np.any(face_signs[t['ef'][:, 0]] != face_signs[t['ef'][:, 1]], axis=1)).sum()),
            interpretation='Unwrapped adjacent-phase sampling diagnostic; not an aesthetic or full-resolution certificate.'),
        source_array_hashes={name: _hash(value) for name, value in {
            'xyz': xyz, 'faces': faces, 'classes': classes, 'g5_parent_face': parent54,
            'g4_parent_face': parent43, 'g3_face_event_ids': owners, 'g3_mirror_face_signs': signs}.items()},
        controls_scope='Actual resolved coefficients override the zero fallback row; wf/we/wp are dimensionless local-scale requests.',
        amplitude_scope='A=1.6 doubles the new request; it does not guarantee preserved absolute depth or a total-displacement cap.',
        coherence_scope=RECIPE['coherence_scope'],
        success_scope='Fine-fold visibility and hierarchy require actual matched renders; no reference-exact replication claim.')
    return out, metadata, state
