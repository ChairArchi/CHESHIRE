"""Root-oriented signed detail in one actual coupled G04 -> G05 CC step.

This is a new CHESHIRE hypothesis, not recovered reference settings.  Coupled
face/edge/vertex offsets approximately agree on flat, regular-scale regions;
curved surfaces, varying scales, boundaries and changing scalar values do not
have exact offset agreement.  Actual event ownership supplies support, whereas
actual previous-point V/E/F classes retain their independent CC meaning.

All phases use actual G04 centroids, reflected by inherited face ancestry into
the one inherited root PCA frame. There is no coordinate clamp, chart-nearest
lookup, event-specific phase reset, XYZ averaging, or new topology event.
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
    LOCAL_INCIDENT_SCALE, WEIGHTS, fields as mesh_fields, mean_incident,
    subdivide, topology, unit,
)

MODES = ('COHERENT', 'DIRECTIONAL', 'ROLE_CURVATURE')
SUPPORT_POLICY = {
    'face': 'G03 actual face_event_ids > 0 transported by actual G04 parent_face',
    'edge_vertex': 'incident G04 face means; signed scalar pooled before normal coefficients',
    'boundary': 'final face scalar is multiplied by face support; coupled XYZ halo is allowed',
}
RECIPE = {
    'schema': 'ROOT_COHERENT_SIGNED_DETAIL_V1',
    'source_generation': 4, 'output_generation': 5, 'subdivision_passes_added': 1,
    'scale_mode': LOCAL_INCIDENT_SCALE, 'amplitude': .8,
    'band': {'period_root_radius': .70, 'major_linear': .16,
             'major_warp_amplitude': .20, 'major_warp_frequency': .90,
             'major_warp_phase': .31},
    'role_weights': {'SOURCE': 0., 'WALL': 1., 'CAP': .65},
    'role_pool': {'own_weight': 2., 'neighbor_mean_weight': 1., 'divisor': 3.},
    'geometry_gain': {'floor': .5, 'bending_scale': .35, 'planarity_scale': .03},
    'normal': {'face': 'face_scalar', 'edge_incident_mean_factor': .5,
               'vertex_incident_mean_factor': '1 - 1 / actual degree'},
    'fixed_zero': ['w1', 'w2', 'w3', 'w4', 'w6', 'w7'],
    'modes': {'COHERENT': 'constant supported signed scalar',
              'DIRECTIONAL': 'constant scalar times root-oriented cosine bands',
              'ROLE_CURVATURE': 'same bands times pooled role and actual geometry gains'},
    'planarity': 'max four cyclic fourth-plane distances / perimeter of the other three vertices',
    'bending': 'mean over four adjacent faces of 1 - clipped dot of actual unit face normals',
    'coherence_scope': 'flat regular-scale constant-field approximation; not exact for curved/nonuniform regions',
    'coefficient_scope': 'new dimensionless normal coefficients times current local incident mean-edge scales',
    'symmetry_scope': 'canonical inherited face signs applied to actual XYZ; no XYZ averaging',
    'support_policy': deepcopy(SUPPORT_POLICY),
}


def _hash(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _int_vector(mapping, key, size=None):
    try:
        array = np.asarray(mapping[key])
    except (KeyError, TypeError) as exc:
        raise ValueError('Missing actual provenance: ' + key) from exc
    if array.ndim != 1 or array.dtype.kind not in 'iu' or (size is not None and array.shape != (size,)):
        raise ValueError('Actual integer provenance vector required: ' + key)
    return array


def _root_frame(g3):
    frame = {}
    for name in ('origin', 'major', 'minor', 'normal', 'extent'):
        key = 'inherited_root_pca_' + name
        try:
            value = np.asarray(g3[key], float)
        except (KeyError, TypeError) as exc:
            raise ValueError('Missing inherited actual root frame: ' + key) from exc
        shape = (2,) if name == 'extent' else (3,)
        if value.shape != shape or not np.isfinite(value).all():
            raise ValueError('Invalid inherited actual root frame: ' + key)
        frame[name] = value
    basis = np.column_stack([frame[k] for k in ('major', 'minor', 'normal')])
    if not np.allclose(basis.T @ basis, np.eye(3), atol=2e-10, rtol=0.) or np.any(frame['extent'] <= 0):
        raise ValueError('Actual orthonormal nondegenerate inherited root frame required; no fallback.')
    try:
        radius = np.asarray(g3['inherited_root_radius'], float)
    except (KeyError, TypeError) as exc:
        raise ValueError('Missing actual inherited root radius.') from exc
    if radius.shape != () or not np.isfinite(radius) or radius <= 0:
        raise ValueError('Finite positive scalar inherited root radius required.')
    return frame, float(radius), basis


def quad_planarity(points):
    """Cyclic-start and reflection invariant extension of the triangle ratio.

    The four-cyclic maximum is authored aggregation. Unlike the existing
    reference fields diagnostic, the denominator is the remaining triangle's
    perimeter, not the full quad perimeter. Degenerate triangles are rejected;
    there is no world-axis plane or zero-value fallback.
    """
    points = np.asarray(points, float)
    if points.ndim != 3 or points.shape[1:] != (4, 3) or not np.isfinite(points).all():
        raise ValueError('Finite actual quad points required.')
    ratios = []
    for k in range(4):
        p = np.roll(points, -k, axis=1)
        cross = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        size = np.linalg.norm(cross, axis=1)
        perimeter = (np.linalg.norm(p[:, 1] - p[:, 0], axis=1) +
                     np.linalg.norm(p[:, 2] - p[:, 1], axis=1) +
                     np.linalg.norm(p[:, 0] - p[:, 2], axis=1))
        if np.any(size <= 0) or np.any(perimeter <= 0):
            raise ValueError('Degenerate actual quad triangle; no planarity fallback.')
        normal = cross / size[:, None]
        ratios.append(np.abs(((p[:, 3] - p[:, 0]) * normal).sum(axis=1)) / perimeter)
    return np.max(np.stack(ratios), axis=0)


def resolved_fields(mesh, g4_evidence, g3_evidence, mode):
    """Return ``(nine coefficient arrays, NPZ-safe actual input/field evidence)``.

    All inputs are read-only dictionaries or NpzFile mappings. Frozen source
    hash binding and exact reflection-map propagation belong to the runner and
    independent verifier. No point class is inferred from an anatomical role.
    """
    if mode not in MODES or mesh.generation != RECIPE['source_generation']:
        raise ValueError('A declared mode and actual frozen G04 parent are required.')
    xyz, faces, classes = np.asarray(mesh.xyz), np.asarray(mesh.faces), np.asarray(mesh.classes)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError('Finite actual input XYZ required.')
    if faces.ndim != 2 or faces.shape[1] != 4 or faces.dtype.kind not in 'iu' or not faces.size:
        raise ValueError('Actual all-quad CC parent required.')
    if faces.min() < 0 or faces.max() >= len(xyz):
        raise ValueError('Invalid actual quad indices; no repair.')
    if classes.shape != (len(xyz),) or classes.dtype.kind not in 'iu' or not np.isin(classes, [-1, 0, 1, 2]).all():
        raise ValueError('Actual previous-point classes required.')
    t = topology(mesh)
    if np.any(t['degree'] == 0):
        raise ValueError('Orphan input controls are not repaired.')
    f = mesh_fields(mesh, t)
    if np.any(np.linalg.norm(f['nf'], axis=1) < .99):
        raise ValueError('Actual input face normals are degenerate; no synthetic frame.')
    parent = _int_vector(g4_evidence, 'parent_face', len(faces))
    owners = _int_vector(g3_evidence, 'face_event_ids')
    roles = _int_vector(g3_evidence, 'face_roles', len(owners))
    if not len(owners) or parent.min() < 0 or parent.max() >= len(owners) or np.any(owners < 0):
        raise ValueError('Actual G04 -> G03 ownership ancestry required.')
    if not np.isin(roles, [0, 1, 2]).all() or not np.array_equal(owners > 0, roles > 0):
        raise ValueError('Actual SOURCE/WALL/CAP ownership roles required; no V/E/F reinterpretation.')
    try:
        signs = np.asarray(g3_evidence['mirror_face_signs'])
    except (KeyError, TypeError) as exc:
        raise ValueError('Actual inherited mirror face signs required.') from exc
    if signs.shape != (len(owners), 2) or signs.dtype.kind not in 'iu' or not np.isin(signs, [-1, 1]).all():
        raise ValueError('Actual G03 mirror face signs must be integer +/-1 pairs.')
    frame, radius, basis = _root_frame(g3_evidence)
    support = (owners[parent] > 0).astype(float)
    edge_support = support[t['ef']].mean(axis=1)
    vertex_support = mean_incident(np.repeat(support, t['n']), t['a'], len(xyz))
    mirror = signs[parent]
    canonical = f['c'] * np.column_stack([mirror, np.ones(len(faces), int)])
    coordinates = (canonical - frame['origin']) @ basis / radius
    band_recipe = RECIPE['band']
    long = coordinates[:, 0]
    phase = 2*np.pi * (coordinates[:, 1]/band_recipe['period_root_radius'] +
        band_recipe['major_linear']*long + band_recipe['major_warp_amplitude']*
        np.sin(band_recipe['major_warp_frequency']*long + band_recipe['major_warp_phase']))
    band = np.cos(phase)

    # Keep the input face's actual cyclic edge order; no sorted-neighbor ID rule.
    incident = t['ef'][t['fe']]
    neighbors = np.where(incident[:, :, 0] == np.arange(len(faces))[:, None],
                         incident[:, :, 1], incident[:, :, 0])
    bending = (1 - np.clip((f['nf'][:, None, :] * f['nf'][neighbors]).sum(axis=2), -1, 1)).mean(axis=1)
    planarity = quad_planarity(xyz[faces])
    role_map = RECIPE['role_weights']
    role_raw = np.asarray([role_map['SOURCE'], role_map['WALL'], role_map['CAP']])[roles[parent]]
    pool = RECIPE['role_pool']
    role_gain = (pool['own_weight']*role_raw + pool['neighbor_mean_weight']*role_raw[neighbors].mean(axis=1))/pool['divisor']
    gain_recipe = RECIPE['geometry_gain']
    geometry_gain = gain_recipe['floor'] + (1-gain_recipe['floor'])*np.exp(
        -bending/gain_recipe['bending_scale'] - planarity/gain_recipe['planarity_scale'])
    applied_gain = role_gain*geometry_gain if mode == 'ROLE_CURVATURE' else np.ones(len(faces))
    scalar = RECIPE['amplitude'] * support * (np.ones(len(faces)) if mode == 'COHERENT' else band) * applied_gain
    edge_scalar = scalar[t['ef']].mean(axis=1)
    vertex_scalar = mean_incident(np.repeat(scalar, t['n']), t['a'], len(xyz))
    controls = {key: np.zeros(len(faces) if key in ('wf', 'w3', 'w4', 'w6') else
                             len(xyz) if key in ('wp', 'w2') else len(t['edges'])) for key in WEIGHTS}
    controls['wf'] = scalar
    controls['we'] = RECIPE['normal']['edge_incident_mean_factor']*edge_scalar
    controls['wp'] = (1 - 1/t['degree'])*vertex_scalar
    previous = classes[faces]
    eligible = (((previous == 0).sum(1) == 1) & ((previous == 1).sum(1) == 2) &
                ((previous == 2).sum(1) == 1) &
                ((np.argmax(previous == 0, axis=1)+2) % 4 == np.argmax(previous == 2, axis=1)))
    delta = phase[t['ef'][:, 1]] - phase[t['ef'][:, 0]]
    supported_edges = np.all(support[t['ef']] > 0, axis=1)
    seam_edges = np.any(mirror[t['ef'][:, 0]] != mirror[t['ef'][:, 1]], axis=1) & supported_edges
    evidence = dict(
        input_g4_to_g3_face_ids=parent.copy(), input_g3_face_event_ids=owners.copy(),
        input_g3_face_roles=roles.copy(), input_g3_mirror_face_signs=signs.copy(),
        input_face_event_ids=owners[parent], input_face_roles=roles[parent],
        input_face_mirror_signs=mirror, input_point_classes=classes.copy(),
        input_face_support=support, input_edge_support=edge_support, input_vertex_support=vertex_support,
        input_face_neighbour_ids=neighbors, input_vertex_degree=t['degree'],
        input_face_normals=f['nf'], input_edge_normals=f['ne'], input_vertex_normals=f['nv'],
        face_centroids=f['c'], canonical_face_centroids=canonical, root_coordinates=coordinates,
        face_phase=phase, face_band=band, face_bending=bending, face_planarity=planarity,
        face_role_weight_raw=role_raw, face_role_gain=role_gain, face_geometry_gain=geometry_gain,
        face_applied_gain=applied_gain, face_scalar=scalar, edge_scalar=edge_scalar, vertex_scalar=vertex_scalar,
        phase_edge_delta=delta, supported_phase_edge_mask=supported_edges,
        phase_edge_alias_mask=supported_edges & (np.abs(delta) > np.pi),
        supported_phase_seam_edge_mask=seam_edges, eq4_eligible_mask=eligible,
        physical_wavelength=np.array(band_recipe['period_root_radius']*radius),
        root_minor_cycles=np.array(frame['extent'][1]/(band_recipe['period_root_radius']*radius)),
        inherited_root_radius=np.array(radius),
    )
    evidence.update({'inherited_root_pca_'+key: value.copy() for key, value in frame.items()})
    return controls, evidence


def build(mesh, g4_evidence, g3_evidence, mode):
    """Return actual G05 mesh, JSON-safe metadata, NPZ-safe full step evidence."""
    controls, evidence = resolved_fields(mesh, g4_evidence, g3_evidence, mode)
    out, metadata, state = subdivide(mesh, {'weights': {key: 0. for key in WEIGHTS}},
        scale_mode=LOCAL_INCIDENT_SCALE, resolved_controls=controls)
    out.surface = 'mean'
    state.update(evidence)
    supported = evidence['input_face_support'] > 0
    edge_mask = evidence['supported_phase_edge_mask']
    phase_abs = np.abs(evidence['phase_edge_delta'][edge_mask])
    ranges = {name: [float(value.min()), float(value.max())] for name, value in controls.items()}
    metadata.update(
        experiment='COHERENT_FOLD_DETAIL_20261013', mode=mode, recipe=deepcopy(RECIPE),
        support_policy=deepcopy(SUPPORT_POLICY), source_generation=4, output_generation=5,
        subdivision_passes_added=1, added_topology_events=0, added_field_passes=0,
        actual_class_counts={str(c): int((mesh.classes == c).sum()) for c in (-1, 0, 1, 2)},
        supported_face_count=int(supported.sum()), resolved_control_ranges=ranges,
        supported_eq4_eligible_count=int((evidence['eq4_eligible_mask'] & supported).sum()),
        supported_eq4_fallback_count=int((~evidence['eq4_eligible_mask'] & supported).sum()),
        phase_diagnostics=dict(physical_wavelength=float(evidence['physical_wavelength']),
            cycles_across_inherited_root_minor_extent=float(evidence['root_minor_cycles']),
            supported_adjacent_edge_count=int(edge_mask.sum()),
            supported_neighbor_unwrapped_phase_abs_quantiles=[] if not len(phase_abs) else
                np.quantile(phase_abs, [0, .5, .9, 1.]).tolist(),
            alias_fraction_over_pi=0. if not len(phase_abs) else float((phase_abs > np.pi).mean()),
            supported_mirror_seam_edge_count=int(evidence['supported_phase_seam_edge_mask'].sum()),
            interpretation='Sampling diagnostic only; not an aesthetic PASS threshold. Phase is unwrapped.'),
        source_array_hashes={name: _hash(value) for name, value in {
            'xyz': mesh.xyz, 'faces': mesh.faces, 'classes': mesh.classes,
            'g4_parent_face': evidence['input_g4_to_g3_face_ids'],
            'g3_face_event_ids': evidence['input_g3_face_event_ids'],
            'g3_face_roles': evidence['input_g3_face_roles'],
            'g3_mirror_face_signs': evidence['input_g3_mirror_face_signs']}.items()},
        coherence_scope=RECIPE['coherence_scope'],
        controls_scope='Global weights row is zero; actual dimensionless coefficients are saved resolved arrays, not world lengths.',
        anatomy_scope='G03 SOURCE/WALL/CAP roles gate scalar amplitude; never previous-point V/E/F classes.',
        amplitude_scope='No total-shift cap or preservation of organic/clay impression is imposed.',
        success_scope='Actual directional folds, hierarchy and reference fidelity require visual review.',
    )
    return out, metadata, state
