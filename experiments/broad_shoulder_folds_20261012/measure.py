"""Measured broad upper shoulder on the actual, relaxed WALL G03 carrier.

The same authored material window is used on SPAN and COUNTER. It was selected
by small actual-native section diagnostics, rather than inherited from a narrow
legacy parent rail. Surface arc supplies the transverse coordinate; actual
triangles and barycentric coordinates retain the source of every sample.
This module measures and maps a patch only. It performs no deformation, mesh
refinement, final reflection, automatic semantic shoulder discovery or render.
"""
from pathlib import Path
import hashlib
import importlib.util
import json

import numpy as np
import trimesh


HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('broad_shoulder_legacy_guidance',
    HERE.parent/'parent_guided_detail_20261012/guidance.py')
guidance = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guidance)
t, bulb = guidance.t, guidance.bulb

SELECTION = dict(parameter_range=[.70, .87],
    transverse_range=[.90, float(np.pi/2.-.005)],
    longitudinal_samples=41, transverse_samples=129,
    axial_plateau_fraction=.60, transverse_fade_fraction=.12,
    minimum_physical_width=.50,
    selection_scope='One fixed material window on both inputs; actual native XYZ measures its physical support',
    selection_limit='Authored shared window selected by actual width and normal diagnostics; not automatic natural-shoulder detection',
    reflection_scope='Canonical abs material X/Y coordinates; caller constructively reflects geometry',
    boundary_scope='Quintic fade to zero at all four material patch boundaries; front symmetry seam remains outside the patch')


def array_hash(value):
    """SHA256 of the exact contiguous array bytes, matching legacy receipts."""
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _recipe(recipe):
    selected = dict(SELECTION)
    if recipe is not None:
        selected.update(recipe)
    s0, s1 = map(float, selected['parameter_range'])
    c0, c1 = map(float, selected['transverse_range'])
    if not 0. < s0 < s1 < 1. or not 0. < c0 < c1 < np.pi/2.:
        raise ValueError('Patch must lie strictly within the body and canonical quarter.')
    if int(selected['longitudinal_samples']) < 4 or int(selected['transverse_samples']) < 3:
        raise ValueError('At least four longitudinal and three transverse samples required.')
    if not 0. <= float(selected['axial_plateau_fraction']) < 1.:
        raise ValueError('Axial plateau fraction must be in [0,1).')
    if not 0. < float(selected['transverse_fade_fraction']) <= .5:
        raise ValueError('Transverse fade fraction must be in (0,.5].')
    if float(selected['minimum_physical_width']) <= 0.:
        raise ValueError('A positive actual physical width threshold is required.')
    return selected


def measure_patch(mesh, chart, recipe=SELECTION):
    """Measure a shared broad shoulder on the supplied actual G03 surface.

    ``physical_width`` is the boundary chord perpendicular to the fitted actual
    longitudinal centreline tangent. ``transverse_arc`` is cumulative actual
    sampled surface distance and must not be substituted for that width test.
    ``pooled_normal`` is an arc-weighted average of actual native vertex normals;
    pooling changes normal directions only. Source XYZ is never smoothed here.
    """
    selected = _recipe(recipe)
    chart = np.asarray(chart, float)
    if int(mesh.generation) != 3:
        raise ValueError('Measure the actual common relaxed WALL G03 carrier, before new folds.')
    if chart.shape != (len(mesh.xyz), 3) or not np.isfinite(chart).all():
        raise ValueError('Finite control-aligned N x 3 material chart required.')
    if not np.isfinite(mesh.xyz).all():
        raise ValueError('Actual carrier XYZ must be finite.')
    parameter = np.linspace(*selected['parameter_range'], int(selected['longitudinal_samples']))
    cross = np.linspace(*selected['transverse_range'], int(selected['transverse_samples']))
    surface_uv = np.stack(np.meshgrid(parameter, cross, indexing='ij'), axis=-1)
    sampler = bulb.study.native_sampler(mesh, chart)
    surface_xyz, triangle_ids, barycentric = sampler.sample(surface_uv, records=True)
    native = t.growth.native(mesh)
    triangles = native.faces[:, :3]
    normal_mesh = trimesh.Trimesh(native.xyz, triangles, process=False)
    vertex_normals = np.asarray(normal_mesh.vertex_normals)
    surface_normals = bulb.unit(np.sum(
        vertex_normals[triangles[triangle_ids]]*barycentric[..., None], axis=-2))
    if np.any(np.linalg.norm(surface_normals, axis=-1) < .99):
        raise ValueError('Actual native surface has an undefined sampled normal.')
    steps = np.linalg.norm(np.diff(surface_xyz, axis=1), axis=-1)
    transverse_arc = np.c_[np.zeros(len(parameter)), np.cumsum(steps, axis=1)]
    if np.any(steps <= 1e-12):
        raise ValueError('Actual shoulder arc must increase strictly at every sampled section.')
    # Trapezoidal weights prevent material sampling density from masquerading as
    # a uniform physical-area normal pool. This remains a section-normal pool.
    weights = np.zeros_like(transverse_arc)
    weights[:, :-1] += steps/2.
    weights[:, 1:] += steps/2.
    pooled_normal = bulb.unit(np.sum(surface_normals*weights[..., None], axis=1))
    if np.any(np.linalg.norm(pooled_normal, axis=-1) < .99):
        raise ValueError('Actual shoulder normal pool is degenerate; no synthetic fallback.')
    # Actual centreline at half surface arc, not at half material theta.
    centre_cross = np.array([np.interp(row[-1]*.5, row, cross) for row in transverse_arc])
    centre_uv = np.column_stack([parameter, centre_cross])
    centre_xyz, centre_ids, centre_bary = sampler.sample(centre_uv, records=True)
    q = 2.*(parameter-parameter[0])/(parameter[-1]-parameter[0])-1.
    coefficients = np.polyfit(q, centre_xyz, 3)
    longitudinal_tangent = bulb.unit(np.column_stack([
        np.polyval(np.polyder(coefficients[:, i]), q) for i in range(3)]))
    tangent = bulb.unit(longitudinal_tangent-pooled_normal*
        np.sum(longitudinal_tangent*pooled_normal, axis=1)[:, None])
    if np.any(np.linalg.norm(tangent, axis=-1) < .99):
        raise ValueError('Actual fitted centreline has no stable surface tangent.')
    bitangent = bulb.unit(np.cross(pooled_normal, tangent))
    chord = surface_xyz[:, -1]-surface_xyz[:, 0]
    chord_length = np.linalg.norm(chord, axis=1)
    physical_width = np.linalg.norm(chord-longitudinal_tangent*
        np.sum(chord*longitudinal_tangent, axis=1)[:, None], axis=1)
    if np.any(physical_width < float(selected['minimum_physical_width'])):
        raise ValueError('Actual broad shoulder fails the declared minimum physical chord width: '
                         f'{physical_width.min():.9g} < {selected["minimum_physical_width"]}')
    normal_angle = np.degrees(np.arccos(np.clip(
        np.sum(surface_normals*pooled_normal[:, None, :], axis=-1), -1., 1.)))
    replay_xyz = np.sum(native.xyz[triangles[triangle_ids]]*barycentric[..., None], axis=-2)
    sampling_error = float(np.max(np.abs(replay_xyz-surface_xyz)))
    if sampling_error > 3e-12:
        raise ValueError(f'Actual native barycentric provenance mismatch: {sampling_error}')
    return dict(parameter=parameter, surface_uv=surface_uv, surface_xyz=surface_xyz,
        triangle_ids=triangle_ids, barycentric=barycentric,
        surface_normals=surface_normals, normal_pool_arc_weights=weights,
        transverse_arc=transverse_arc, physical_width=physical_width,
        chord_length=chord_length, arc_to_chord_ratio=transverse_arc[:, -1]/chord_length,
        pooled_normal=pooled_normal, tangent=tangent, bitangent=bitangent,
        longitudinal_tangent=longitudinal_tangent,
        centreline_uv=centre_uv, centreline_xyz=centre_xyz,
        centreline_triangle_ids=centre_ids, centreline_barycentric=centre_bary,
        centreline_fit_coefficients=coefficients, normal_angle_degrees=normal_angle,
        normal_angle_p90_by_row=np.percentile(normal_angle, 90., axis=1),
        source_xyz_hash=np.array(array_hash(mesh.xyz)),
        source_chart_hash=np.array(array_hash(chart)),
        source_face_hash=np.array(array_hash(mesh.faces)),
        source_native_xyz_hash=np.array(array_hash(native.xyz)),
        source_native_face_hash=np.array(array_hash(triangles)),
        source_generation=np.array(3), native_sample_max_error=np.array(sampling_error),
        axial_plateau_fraction=np.array(selected['axial_plateau_fraction']),
        transverse_fade_fraction=np.array(selected['transverse_fade_fraction']),
        selection_recipe_json=np.array(json.dumps(selected, sort_keys=True)),
        physical_width_definition=np.array('Actual lower-to-upper section chord perpendicular to fitted actual longitudinal centreline tangent'),
        normal_definition=np.array('Arc-weighted pool of barycentrically interpolated actual native vertex normals; no XYZ smoothing'),
        scope=np.array('One broad authored shared material patch, measured on actual G03; not automatic semantic shoulder segmentation'))


def _legacy_map(patch):
    """Adapt only the documented monotonic arc map to the existing inverse."""
    return dict(parameter=patch['parameter'], parent_shoulder_uv=patch['surface_uv'],
        parent_shoulder_arc=patch['transverse_arc'])


def coordinates(chart, patch):
    """Canonical q in [-1,+1], u in actual transverse arc fraction, and fade.

    X/Y material reflection leaves the scalar map invariant. Values outside the
    patch remain available for diagnostics, while the envelope is exactly zero.
    Caller restores final XYZ exactly to BASELINE outside this support.
    """
    chart = np.asarray(chart, float)
    if chart.ndim != 2 or chart.shape[1] != 3 or not np.isfinite(chart).all():
        raise ValueError('Finite N x 3 material chart required.')
    parameter = np.asarray(patch['parameter'])
    q = 2.*(chart[:, 0]-parameter[0])/(parameter[-1]-parameter[0])-1.
    cross = np.arctan2(np.abs(chart[:, 2]), np.abs(chart[:, 1]))
    u = guidance._arc_coordinate(chart[:, 0], cross, _legacy_map(patch))
    axial = guidance._quintic((1.-np.abs(q))/(1.-float(patch['axial_plateau_fraction'])))
    axial *= np.linalg.norm(chart[:, 1:], axis=1) > .2
    fade = float(patch['transverse_fade_fraction'])
    transverse = guidance._quintic(u/fade)*guidance._quintic((1.-u)/fade)
    envelope = axial*transverse
    return dict(q=q, u=u, envelope=envelope, axial_weight=axial,
                transverse_weight=transverse, active=envelope > 0.)


def uv_at_fraction(parameters, fraction, patch):
    """Invert the same interpolated actual arc map; return flattened N x 2 UV.

    This accepts scalar or broadcastable arrays. Parameters and fractions must
    be within the measured patch; it does not extrapolate a surface position.
    """
    parameters, fraction = np.broadcast_arrays(np.asarray(parameters, float), np.asarray(fraction, float))
    axis = np.asarray(patch['parameter'])
    if (not np.isfinite(parameters).all() or not np.isfinite(fraction).all() or
            np.any(parameters < axis[0]) or np.any(parameters > axis[-1]) or
            np.any(fraction < 0.) or np.any(fraction > 1.)):
        raise ValueError('Actual patch inverse requires finite in-range parameters and fractions.')
    return guidance._uv_at_fraction(parameters, fraction, _legacy_map(patch))
