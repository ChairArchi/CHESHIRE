"""One broad MEDIUM -> SMALL panel-flank fold sequence on actual latest G7.

Both stages displace the actual incoming surface along the existing incident
normal. Only each newly requested displacement is neighbor-averaged twice;
the source geometry is not averaged. All coordinates inherited from the
selected MIDDLE frame remain fixed. This is an authored rib/groove sequence,
not a pore system, topological branch, or reference-exact implementation.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OLD = HERE.parent/'parent_linked_folds_20261013'


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def _same_module(result, path):
    return (result is not None and getattr(result, '__file__', None) is not None and
        Path(result.__file__).resolve() == path.resolve())


# The existing smoothing file deliberately imports plain ``study``. The new
# runner is run.py and binds that name to the frozen old study. Also support
# direct library import without allowing an unrelated study.py to be selected.
base = sys.modules.get('study')
if not _same_module(base, OLD/'study.py'):
    base = _module('medium_root_existing_parent_study', OLD/'study.py')
finish = sys.modules.get('smooth_relief')
if not _same_module(finish, OLD/'smooth_relief.py'):
    _missing = object()
    _previous_study = sys.modules.get('study', _missing)
    sys.modules['study'] = base
    try:
        finish = _module('medium_root_existing_displacement_finish', OLD/'smooth_relief.py')
    finally:
        if _previous_study is _missing:
            del sys.modules['study']
        else:
            sys.modules['study'] = _previous_study

parent = base.operator
field = parent.field


def code_hashes():
    """Bind this operator and every directly reused geometric helper."""
    paths = (Path(__file__).resolve(), OLD/'study.py', OLD/'parent_folds.py',
        OLD/'smooth_relief.py', HERE.parent/'whole_column_detail_20261013/whole_field.py',
        REPO/'src/cheshire/reference_subdivision.py')
    return {str(path.relative_to(REPO)): base.digest(path) for path in paths}


RECIPE = {
    'schema': 'CHESHIRE_MEDIUM_PANEL_FLANK_FOLDS_V1',
    'source_generation': 7,
    'output_generation': 7,
    'sequence': ['MEDIUM', 'SMALL'],
    'added_CC_passes': 0,
    'added_topology_events': 0,
    'normal_field_passes': 2,
    'smoothing_passes': 4,
    'smoothing_iterations_per_new_delta': 2,
    'smoothing_alpha': .5,
    'smoothing_equation': 'new_delta_next=.5*new_delta+.5*uniform_actual_edge_neighbor_mean(new_delta)',
    'coordinates': 'Fixed inherited MIDDLE parent_phase, normalized_z, feature_support and height H; theta=atan2(abs(actual_initial_source_Y),abs(actual_initial_source_X)) fixed for both stages.',
    'wrapped_parent_phase': 'u=atan2(sin(parent_phase),cos(parent_phase))',
    'parent_mask': 'd=(abs(u)-1.55)/1.20; max(0,1-d*d)**3, exactly zero where abs(d)>=1',
    'medium_phase': 'q=2*pi*(abs(u)-1.55)/2.40+.30*sin(2*pi*z/.18+.5*cos(2*theta))',
    'medium_profile': 'cos(q)',
    'medium_signed_request': 'H*.0065*PCHIPenv*(1-.55*feature_support)*parent_mask*cos(q)',
    'small_mask': 'parent_mask*clip((cos(q)+.5)/1.5,0,1)',
    'small_phase': '3*q+.35*sin(2*pi*z/.09+.5*cos(2*theta))',
    'small_signed_request': 'H*.0016*PCHIPenv*(1-.55*feature_support)*small_mask*cos(small_phase)',
    'profile_scope': 'Cosine profiles in [-1,1]; broad parent panel-flank ribs and grooves, without a sharpened profile.',
    'medium_amplitude_height_fraction': .0065,
    'small_amplitude_height_fraction': .0016,
    'envelope': deepcopy(field.RECIPE['envelope']),
    'normal': field.RECIPE['normal'],
    'normal_implementation': field.RECIPE['normal_implementation'],
    'reflection': 'After two averages of each new delta, transport its minimum-ID orbit representative with actual commuting source X/Y IDs; fixed-ID seam components are zero.',
    'geometry_scope': 'Actual latest G7 -> source_xyz+delta_medium -> medium_xyz+delta_small; no averaging of existing source geometry, no new CC, associations unchanged.',
    'interpretation': 'One fixed authored broad panel-flank rib/groove sequence; no pore, demonstrated topological branch, or visual success claim.',
}


def _filter_and_reflect(delta, faces, degree, ids, pairs):
    for _ in range(2):
        delta = finish.uniform_displacement_pass(delta, faces, degree)
    return field._transport(delta, ids, pairs)[0]


def build(mesh, chart, vertex_pairs, parent_phase, normalized_z,
          feature_support, height):
    """Return ``(actual G7 ArrayMesh, JSON-safe metadata, NPZ-safe state)``.

    The runner binds the actual latest trial03 source and MIDDLE-frame ancestry.
    Saved deltas reconstruct the actual intermediate and final coordinates.
    No input array is modified; unchanged topology/associations are reused.
    """
    xyz, faces = np.asarray(mesh.xyz), np.asarray(mesh.faces)
    if mesh.generation != 7:
        raise ValueError('Actual latest saved G7 required.')
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not len(xyz) or not np.isfinite(xyz).all():
        raise ValueError('Finite actual source G7 XYZ required.')
    if (faces.ndim != 2 or faces.shape[1] != 4 or not len(faces) or
            faces.dtype.kind not in 'iu' or faces.min() < 0 or faces.max() >= len(xyz)):
        raise ValueError('Actual all-quad G7 required; no repair.')
    if np.asarray(chart).shape != xyz.shape or not np.isfinite(chart).all():
        raise ValueError('Actual unchanged source chart required.')
    if (np.asarray(mesh.classes).shape != (len(xyz),) or
            np.asarray(mesh.rest).shape != xyz.shape or
            np.asarray(mesh.anchors).ndim != 2 or len(mesh.anchors) != len(faces)):
        raise ValueError('Actual unchanged G7 classes/rest/anchors required.')
    phase = parent._vector(parent_phase, len(xyz), 'parent phase')
    z = parent._vector(normalized_z, len(xyz), 'normalized height', -1e-12, 1+1e-12)
    z = np.clip(z, 0., 1.)  # Roundoff only; supplied ancestry defines height.
    support = parent._vector(feature_support, len(xyz), 'feature support', 0., 1.)
    height = float(height)
    if not np.isfinite(height) or height <= 0:
        raise ValueError('Positive supplied inherited full-column height required.')
    ids, pairs = field._mirror_pairs(vertex_pairs, len(xyz))
    degree = np.bincount(faces.ravel(), minlength=len(xyz))
    if np.any(degree == 0):
        raise ValueError('Source orphan controls are not repaired.')

    theta = np.arctan2(np.abs(xyz[:, 1]), np.abs(xyz[:, 0]))
    u = np.arctan2(np.sin(phase), np.cos(phase))
    d = (np.abs(u)-1.55)/1.20
    parent_mask = np.maximum(0., 1-d*d)**3
    parent_mask[np.abs(d) >= 1.] = 0.
    q = (2*np.pi*(np.abs(u)-1.55)/2.40+
        .30*np.sin(2*np.pi*z/.18+.5*np.cos(2*theta)))
    medium_profile = np.cos(q)
    small_mask = parent_mask*np.clip((medium_profile+.5)/1.5, 0., 1.)
    small_phase = 3*q+.35*np.sin(2*np.pi*z/.09+.5*np.cos(2*theta))
    env = field.PchipInterpolator(RECIPE['envelope']['knots'],
        RECIPE['envelope']['values'], extrapolate=False)(z)
    attenuation = env*(1-.55*support)
    theta_hash = parent._hash(theta)
    del theta, u, d, env

    print('WIDE_ROOT MEDIUM: actual source normals; smooth only new delta twice', flush=True)
    normals = field._input_normals(xyz, faces)
    medium_normal_hash = parent._hash(normals)
    raw_delta = normals*(height*.0065*attenuation*parent_mask*medium_profile)[:, None]
    del normals, medium_profile
    delta_medium = _filter_and_reflect(raw_delta, faces, degree, ids, pairs)
    del raw_delta
    medium_stats = dict(parent._stats(delta_medium, height*.0065),
        **parent._mask_stats(parent_mask), input_vertex_normal_sha256=medium_normal_hash,
        new_displacement_smoothing_iterations=2, smoothing_alpha=.5)
    medium_xyz = xyz+delta_medium
    if not np.isfinite(medium_xyz).all():
        raise ValueError('Nonfinite actual MEDIUM stage; no fallback.')
    intermediate_hash = parent._hash(medium_xyz)

    print('WIDE_ROOT SMALL: actual MEDIUM normals; smooth only new delta twice', flush=True)
    normals = field._input_normals(medium_xyz, faces)
    small_normal_hash = parent._hash(normals)
    raw_delta = normals*(height*.0016*attenuation*small_mask*np.cos(small_phase))[:, None]
    del normals, attenuation, small_phase
    delta_small = _filter_and_reflect(raw_delta, faces, degree, ids, pairs)
    del raw_delta, degree, ids
    small_stats = dict(parent._stats(delta_small, height*.0016),
        **parent._mask_stats(small_mask), input_vertex_normal_sha256=small_normal_hash,
        new_displacement_smoothing_iterations=2, smoothing_alpha=.5)
    output_xyz = medium_xyz+delta_small
    del medium_xyz
    if not np.isfinite(output_xyz).all():
        raise ValueError('Nonfinite actual broad-fold output; no fallback.')

    # These association arrays are unchanged and never modified by the operator.
    # Sharing them avoids duplicating the dense source topology and ancestry.
    out = field.ArrayMesh(output_xyz, mesh.faces, mesh.classes, mesh.rest, mesh.anchors, 7)
    out.surface = 'mean'
    total_norm = np.empty(len(xyz), dtype=float)
    actual_unmoved = 0
    for start in range(0, len(xyz), 120000):
        stop = min(start+120000, len(xyz))
        total_norm[start:stop] = np.linalg.norm(output_xyz[start:stop]-xyz[start:stop], axis=1)
        actual_unmoved += int(np.count_nonzero(np.all(output_xyz[start:stop] == xyz[start:stop], axis=1)))
    face_hash = parent._hash(faces)
    metadata = dict(experiment='MEDIUM_ROOT_FOLDS_20261013', recipe=deepcopy(RECIPE),
        source_generation=7, output_generation=7, subdivision_generation=7,
        added_CC_passes=0, added_topology_events=0, added_normal_field_passes=2,
        smoothing_passes=4, physical_height=height, medium=medium_stats, small=small_stats,
        maximum_total_displacement=float(total_norm.max(initial=0.)),
        total_amplitude_bound=height*(.0065+.0016),
        total_displacement_norm_quantiles=np.quantile(total_norm, [0, .5, .9, .99, 1]).tolist(),
        total_nonzero_displacement_vertex_count=int(np.count_nonzero(total_norm)),
        total_nonzero_displacement_vertex_fraction=float(np.count_nonzero(total_norm)/len(xyz)),
        actual_unmoved_vertex_count=actual_unmoved,
        actual_unmoved_vertex_fraction=float(actual_unmoved/len(xyz)),
        inherited_feature_vertex_count=int(np.count_nonzero(support)),
        inherited_feature_vertex_fraction=float(np.count_nonzero(support)/len(xyz)),
        input_xyz_sha256=parent._hash(xyz), intermediate_medium_xyz_sha256=intermediate_hash,
        output_xyz_sha256=parent._hash(output_xyz), input_faces_sha256=face_hash,
        output_faces_sha256=face_hash, inherited_parent_phase_sha256=parent._hash(phase),
        inherited_normalized_z_sha256=parent._hash(z), inherited_feature_support_sha256=parent._hash(support),
        fixed_initial_theta_sha256=theta_hash,
        geometry_code_sha256=code_hashes(),
        faces_unchanged=True, classes_rest_anchors_unchanged=True, chart_unchanged=True,
        source_geometry_averaged=False,
        support_scope='Mask and displacement fractions are control-vertex shares, not surface area; each two-pass delta filter may add an edge-neighbor halo of at most two edges.',
        normal_scope='Existing helper evaluates actual source normals for MEDIUM and actual MEDIUM normals for SMALL; normals are hashed rather than saved in duplicate.',
        state_scope='Exact intermediate = actual source XYZ + delta_medium; exact final = intermediate + delta_small. Fixed inherited coordinates and masks are saved.',
        implementation_binding='Frozen parent_linked study.py and its field helpers; frozen smooth_relief.uniform_displacement_pass. Plain study import is explicitly bound to the old folder during smoothing-module load.',
        success_scope='Broad panel-flank rib/groove relief only; no pore, demonstrated topological branch, or claim that detail hierarchy or visual quality is solved.',
        validation_scope='Runner binds actual latest source and ancestry and verifies actual finite/closed/connected mesh, native fan area, explicit-ID symmetry and matched renders.')
    state = dict(delta_medium=delta_medium, delta_small=delta_small,
        parent_mask=parent_mask, small_mask=small_mask, parent_phase=phase,
        q=q, normalized_z=z, feature_support=support,
        mirror_x_vertex_pairs=pairs['X'], mirror_y_vertex_pairs=pairs['Y'])
    return out, metadata, state
