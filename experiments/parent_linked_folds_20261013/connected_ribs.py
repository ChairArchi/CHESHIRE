"""Broad connected-rib CHILD -> GRANDCHILD relief on the selected actual G7.

The fixed parent phase, normalized height, and feature support arrive from
the runner's actual G6 -> G7 CC correspondence. They are never re-inferred
from the resulting surface. Each pass reevaluates the actual incoming normal
using the existing whole-column helper. Both passes preserve G7 topology.

CHILD and GRANDCHILD name field dependencies, not demonstrated topological
branching. This authored CHESHIRE recipe is not a reference-exact method.

This one correction widens the child period by three and uses cosine relief
instead of the narrow sharpened profile. Parent masks, support, amplitudes,
and pass ordering remain unchanged; reduced faceting is not yet established.
"""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
HELPER_PATH = HERE.parent/'whole_column_detail_20261013/whole_field.py'


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


field = _module('connected_ribs_existing_whole_field', HELPER_PATH)

RECIPE = {
    'schema': 'CHESHIRE_PARENT_LINKED_BROAD_CONNECTED_RIB_V2',
    'source_generation': 7,
    'output_generation': 7,
    'sequence': ['CHILD', 'GRANDCHILD'],
    'added_CC_passes': 0,
    'added_topology_events': 0,
    'normal_field_passes': 2,
    'coordinates': 'parent_phase, normalized_z and feature_support transported from actual MIDDLE G6 through actual CC V/E/F IDs; theta=atan2(abs(initial_G7_Y),abs(initial_G7_X)) remains fixed for both passes',
    'wrapped_parent_phase': 'u=atan2(sin(parent_phase),cos(parent_phase))',
    'parent_mask': 'd=(abs(u)-.84)/.42; max(0,1-d*d)**3, exactly zero where abs(d)>=1',
    'child_phase': 'q=2*pi*(abs(u)-.84)/.84+.45*sin(2*pi*z/.065+.5*cos(2*theta))',
    'child_blend': 'b=.55*(.5+.5*sin(2*pi*z/.14+.8*cos(2*theta)))',
    'child_profile': 'pchild=(1-b)*cos(q)+b*cos(2*q)',
    'child_signed_displacement': 'H*.0014*PCHIPenv*(1-.55*feature_support)*parent_mask*pchild',
    'grandchild_mask': 'parent_mask*clip((pchild-.05)/.95,0,1)**2',
    'grandchild_phase': '2*q+.35*sin(2*pi*z/.031+.5*cos(2*theta))',
    'grandchild_signed_displacement': 'H*.00045*PCHIPenv*(1-.55*feature_support)*grandchild_mask*cos(grandchild_phase)',
    'profile': 'cos(phi)',
    'profile_scope': 'Cosine profile range [-1,1]; child is a convex blend of cos(q) and cos(2*q), without the sharpened profile.',
    'envelope': deepcopy(field.RECIPE['envelope']),
    'child_amplitude_height_fraction': .0014,
    'grandchild_amplitude_height_fraction': .00045,
    'height_scope': 'One supplied inherited full-column physical height H; not local edge size or a recomputed stage height.',
    'normal': field.RECIPE['normal'],
    'normal_implementation': field.RECIPE['normal_implementation'],
    'reflection': field.RECIPE['reflection'],
    'geometry_scope': 'Actual source G7 -> source_xyz+delta_child -> child_xyz+delta_grandchild; topology and all associations unchanged.',
    'interpretation': 'Authored parent-linked two-pass surface relief; no demonstrated topological branching, reference-exact reproduction, or visual success claim.',
}


def _hash(value):
    """Hash contiguous array memory without an additional full bytes copy."""
    contiguous = np.ascontiguousarray(value)
    return hashlib.sha256(memoryview(contiguous).cast('B')).hexdigest()


def _vector(value, count, label, lower=None, upper=None):
    value = np.asarray(value, dtype=float)
    if value.shape != (count,) or not np.isfinite(value).all():
        raise ValueError('Finite actual inherited '+label+' required.')
    if lower is not None and np.any(value < lower):
        raise ValueError('Actual inherited '+label+' below declared range.')
    if upper is not None and np.any(value > upper):
        raise ValueError('Actual inherited '+label+' above declared range.')
    return value


def _stats(delta, amplitude_bound):
    norms = np.linalg.norm(delta, axis=1)
    nonzero = int(np.count_nonzero(norms))
    return dict(amplitude_bound=float(amplitude_bound),
        maximum_actual_displacement=float(norms.max(initial=0.)),
        displacement_norm_quantiles=np.quantile(norms, [0, .5, .9, .99, 1]).tolist(),
        nonzero_displacement_vertex_count=nonzero,
        nonzero_displacement_vertex_fraction=float(nonzero/len(delta)),
        displacement_vector_sha256=_hash(delta))


def _mask_stats(mask):
    count = int(np.count_nonzero(mask))
    return dict(nonzero_mask_vertex_count=count,
        nonzero_mask_vertex_fraction=float(count/len(mask)),
        mask_range=[float(mask.min()), float(mask.max())],
        fraction_scope='Share of control vertices, not surface area.')


def build(mesh, chart, vertex_pairs, parent_phase, normalized_z,
          feature_support, height):
    """Return ``(actual G7 ArrayMesh, JSON-safe metadata, NPZ-safe state)``.

    Input files, fixed-coordinate transport, and source hashes are bound by
    the runner. The returned two displacement vectors reproduce the exact
    intermediate and final XYZ without separately saving the intermediate.
    No input array is mutated and no topology generation is added.
    """
    xyz, faces = np.asarray(mesh.xyz), np.asarray(mesh.faces)
    if mesh.generation != 7:
        raise ValueError('Actual selected MIDDLE_SURFACE G7 required.')
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not len(xyz) or not np.isfinite(xyz).all():
        raise ValueError('Finite actual incoming G7 XYZ required.')
    if (faces.ndim != 2 or faces.shape[1] != 4 or not len(faces) or
            faces.dtype.kind not in 'iu' or faces.min() < 0 or faces.max() >= len(xyz)):
        raise ValueError('Actual all-quad G7 required; no repair.')
    if np.asarray(chart).shape != xyz.shape or not np.isfinite(chart).all():
        raise ValueError('Actual unchanged G7 chart association required.')
    if (np.asarray(mesh.classes).shape != (len(xyz),) or
            np.asarray(mesh.rest).shape != xyz.shape or
            np.asarray(mesh.anchors).ndim != 2 or len(mesh.anchors) != len(faces)):
        raise ValueError('Actual G7 classes/rest/anchor associations required.')
    phase = _vector(parent_phase, len(xyz), 'parent phase')
    z = _vector(normalized_z, len(xyz), 'normalized height', -1e-12, 1+1e-12)
    z = np.clip(z, 0., 1.)  # Supplied CC transport bounds; roundoff only.
    support = _vector(feature_support, len(xyz), 'feature support', 0., 1.)
    height = float(height)
    if not np.isfinite(height) or height <= 0:
        raise ValueError('Positive supplied inherited full-column height required.')
    ids, pairs = field._mirror_pairs(vertex_pairs, len(xyz))

    # All field coordinates are fixed on the actual supplied G7 and inherited
    # MIDDLE phase. Only normals change between the two dependent passes.
    theta = np.arctan2(np.abs(xyz[:, 1]), np.abs(xyz[:, 0]))
    u = np.arctan2(np.sin(phase), np.cos(phase))
    d = (np.abs(u)-.84)/.42
    parent_mask = np.maximum(0., 1-d*d)**3
    parent_mask[np.abs(d) >= 1.] = 0.
    q = (2*np.pi*(np.abs(u)-.84)/.84+
        .45*np.sin(2*np.pi*z/.065+.5*np.cos(2*theta)))
    blend = .55*(.5+.5*np.sin(2*np.pi*z/.14+.8*np.cos(2*theta)))
    pchild = (1-blend)*np.cos(q)+blend*np.cos(2*q)
    env = field.PchipInterpolator(RECIPE['envelope']['knots'],
        RECIPE['envelope']['values'], extrapolate=False)(z)
    envelope_attenuation = env*(1-.55*support)
    grand_mask = parent_mask*np.clip((pchild-.05)/.95, 0., 1.)**2
    phase_grand = 2*q+.35*np.sin(2*np.pi*z/.031+.5*np.cos(2*theta))
    theta_hash = _hash(theta)
    del u, d, blend, theta

    print('PARENT_LINKED CHILD: actual incoming G7 normals', flush=True)
    normals = field._input_normals(xyz, faces)
    child_normal_hash = _hash(normals)
    signed_child = height*.0014*envelope_attenuation*parent_mask*pchild
    delta_child, representative, fixed_x, fixed_y = field._transport(
        normals*signed_child[:, None], ids, pairs)
    child_stats = dict(_stats(delta_child, height*.0014),
        **_mask_stats(parent_mask), input_vertex_normal_sha256=child_normal_hash)
    child_xyz = xyz+delta_child
    child_xyz_hash = _hash(child_xyz)
    fixed_x_count, fixed_y_count = int(fixed_x.sum()), int(fixed_y.sum())
    del normals, signed_child, representative, fixed_x, fixed_y, pchild

    print('PARENT_LINKED GRANDCHILD: actual CHILD surface normals', flush=True)
    normals = field._input_normals(child_xyz, faces)
    grand_normal_hash = _hash(normals)
    signed_grandchild = height*.00045*envelope_attenuation*grand_mask*np.cos(phase_grand)
    delta_grandchild, representative, fixed_x, fixed_y = field._transport(
        normals*signed_grandchild[:, None], ids, pairs)
    grand_stats = dict(_stats(delta_grandchild, height*.00045),
        **_mask_stats(grand_mask), input_vertex_normal_sha256=grand_normal_hash)
    output_xyz = child_xyz+delta_grandchild
    if not np.isfinite(output_xyz).all():
        raise ValueError('Nonfinite actual parent-linked relief; no fallback.')
    del normals, signed_grandchild, representative, fixed_x, fixed_y
    del child_xyz, phase_grand, envelope_attenuation, env

    out = field.ArrayMesh(output_xyz, faces.copy(), np.asarray(mesh.classes).copy(),
        np.asarray(mesh.rest).copy(), np.asarray(mesh.anchors).copy(), 7)
    out.surface = 'mean'
    # Accumulate only total displacement lengths, avoiding a full extra Nx3
    # temporary solely for the combined displacement receipt.
    total_norm = np.empty(len(xyz), dtype=float)
    for start in range(0, len(xyz), 120000):
        stop = min(start+120000, len(xyz))
        total_norm[start:stop] = np.linalg.norm(output_xyz[start:stop]-xyz[start:stop], axis=1)
    face_hash = _hash(faces)
    metadata = dict(experiment='PARENT_LINKED_CONNECTED_RIBS_20261013',
        recipe=deepcopy(RECIPE), source_generation=7, output_generation=7,
        subdivision_generation=7, added_CC_passes=0, added_topology_events=0,
        added_normal_field_passes=2, physical_height=height,
        child=child_stats, grandchild=grand_stats,
        maximum_total_displacement=float(total_norm.max(initial=0.)),
        total_displacement_norm_quantiles=np.quantile(total_norm, [0, .5, .9, .99, 1]).tolist(),
        total_nonzero_displacement_vertex_count=int(np.count_nonzero(total_norm)),
        total_nonzero_displacement_vertex_fraction=float(np.count_nonzero(total_norm)/len(xyz)),
        inherited_feature_vertex_count=int(np.count_nonzero(support)),
        inherited_feature_vertex_fraction=float(np.count_nonzero(support)/len(xyz)),
        fixed_x_vertex_count=fixed_x_count, fixed_y_vertex_count=fixed_y_count,
        input_xyz_sha256=_hash(xyz), intermediate_child_xyz_sha256=child_xyz_hash,
        output_xyz_sha256=_hash(output_xyz), input_faces_sha256=face_hash,
        output_faces_sha256=face_hash, inherited_parent_phase_sha256=_hash(phase),
        inherited_normalized_z_sha256=_hash(z), inherited_feature_support_sha256=_hash(support),
        fixed_initial_theta_sha256=theta_hash,
        geometry_code_sha256={str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (Path(__file__).resolve(), HELPER_PATH)},
        faces_unchanged=True, classes_rest_anchors_unchanged=True, chart_unchanged=True,
        support_scope='Mask and displacement fractions are control-vertex shares, not surface-area coverage.',
        normal_scope='Existing helper reevaluates actual source normals for CHILD and actual CHILD normals for GRANDCHILD; normals hashed rather than duplicated in evidence.',
        state_scope='Exact intermediate = actual source XYZ + delta_child; exact final = intermediate + delta_grandchild. Fixed inherited coordinates and masks are saved.',
        reflection_scope='Canonical minimum-ID displacement transport via actual input X/Y IDs; actual source positions and their existing floating-point residuals are retained.',
        success_scope='Authored dependent relief only. No demonstrated topological branching, reference-exact implementation, or claim of visual improvement.',
        validation_scope='Runner verifies closed/connected/finite actual mesh, native fan area, explicit-ID reflection, and matched renders.')
    state = dict(delta_child=delta_child, delta_grandchild=delta_grandchild,
        parent_mask=parent_mask, grand_mask=grand_mask, parent_phase=phase,
        q=q, normalized_z=z, feature_support=support,
        mirror_x_vertex_pairs=pairs['X'], mirror_y_vertex_pairs=pairs['Y'])
    return out, metadata, state
