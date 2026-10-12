"""Two scales of continuous relief in an actually sampled broad shoulder.

The geometry direction is pooled from incoming native triangles rather than
the world Z axis. The profile is authored; no fractal or discovered crease
grammar is claimed. G4/G5 are active stages, and G6 only refines their carrier.
"""
from pathlib import Path
import importlib.util
import sys

import numpy as np
from scipy.interpolate import PchipInterpolator

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import measure

_spec = importlib.util.spec_from_file_location('broad_previous_active',
    HERE.parent/'parent_guided_detail_20261012/active_folds.py')
previous = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(previous)
finish, bulb, t = previous.finish, previous.bulb, previous.t

RECIPE = dict(output_generation=6, active_generations=[4, 5],
    maximum_total_shift=.65, end_limits=[.10, .90],
    centre_arc=.54, centre_sweep_arc=.075,
    primary_halfwidth_arc=.17, primary_height_cap=.28,
    primary_height_width_ratio=.40, side_groove_ratio=.42,
    side_groove_offset_arc=.23, side_groove_halfwidth_arc=.105,
    secondary_offset_arc=-.19, secondary_halfwidth_arc=.075,
    secondary_height_cap=.085, secondary_height_width_ratio=.13,
    secondary_start_q=-.62, secondary_gate_span=.45,
    frame_halfwidth_arc=.28, frame_axial_sigma=.13,
    amplitude_scope='Pilot comparison condition, not a user design constraint',
    normal_scope='Arc-weighted incoming native triangle normals, longitudinally pooled and PCHIP interpolated',
    fine_detail_scope='Existing bulb is replaced in this broad patch in both CLEAR_ONLY and BROAD_ACTIVE; no new bulb evaluation',
    topology_scope='Inherited connectivity is held only for this comparison')


def centre(q, recipe=RECIPE):
    return recipe['centre_arc']+recipe['centre_sweep_arc']*np.sin(.72*np.pi*np.asarray(q))


def ownership(chart, patch, recipe=RECIPE):
    coordinates = measure.coordinates(chart, patch)
    weight = coordinates['envelope'].copy()
    ends = (chart[:, 0] <= recipe['end_limits'][0]) | (chart[:, 0] >= recipe['end_limits'][1])
    weight[ends] = 0.
    return dict(coordinates, weight=weight, ends=ends)


def signed_height(chart, patch, generation, recipe=RECIPE):
    owned = ownership(chart, patch, recipe)
    q, u = owned['q'], owned['u']
    middle = centre(q, recipe)
    width = np.interp(chart[:, 0], patch['parameter'], patch['physical_width'])
    if generation == 4:
        positive = bulb.compact((u-middle)/recipe['primary_halfwidth_arc'])
        negative = np.maximum(
            bulb.compact((u-middle-recipe['side_groove_offset_arc'])/recipe['side_groove_halfwidth_arc']),
            bulb.compact((u-middle+recipe['side_groove_offset_arc'])/recipe['side_groove_halfwidth_arc']))
        negative *= recipe['side_groove_ratio']*(1.-positive)**2
        amplitude = np.minimum(recipe['primary_height_cap'], recipe['primary_height_width_ratio']*width)
    elif generation == 5:
        middle = middle+recipe['secondary_offset_arc']
        gate = previous.guidance._quintic((q-recipe['secondary_start_q'])/recipe['secondary_gate_span'])
        positive = gate*bulb.compact((u-middle)/recipe['secondary_halfwidth_arc'])
        negative = .40*gate*bulb.compact((u-middle+.095)/.055)*(1.-positive)**2
        amplitude = np.minimum(recipe['secondary_height_cap'], recipe['secondary_height_width_ratio']*width)
    else:
        raise ValueError('Only actual G4/G5 active stages are declared.')
    height = amplitude*(positive-negative)*owned['weight']
    return height, dict(height=height, positive_band=positive, negative_band=negative,
        amplitude=amplitude, q=q, u=u, patch_weight=owned['weight'], fixed_ends=owned['ends'])


def pool_normals(parameter, arc, triangle_normals, recipe=RECIPE):
    """Pool actual face normals by physical transverse arc and axial distance."""
    parameter, arc, normals = map(np.asarray, (parameter, arc, triangle_normals))
    if normals.shape != arc.shape+(3,) or len(parameter) != len(arc):
        raise ValueError('Actual normal samples must match the sampled patch.')
    total = arc[:, -1]
    if np.any(total <= 0.) or not np.isfinite(normals).all():
        raise ValueError('A positive physical arc and finite normals are required.')
    q = 2.*(parameter-parameter[0])/np.ptp(parameter)-1.
    fraction = arc/total[:, None]
    steps = np.diff(arc, axis=1)
    quadrature = .5*np.c_[steps[:, :1], steps[:, :-1]+steps[:, 1:], steps[:, -1:]]
    cross_weight = quadrature*bulb.compact((fraction-centre(q, recipe)[:, None])/recipe['frame_halfwidth_arc'])
    cross_weight /= cross_weight.sum(axis=1)[:, None]
    raw = np.sum(cross_weight[..., None]*normals, axis=1)
    axial = np.exp(-.5*((q[:, None]-q[None, :])/recipe['frame_axial_sigma'])**2)
    axial /= axial.sum(axis=1)[:, None]
    pooled = axial@raw
    lengths = np.linalg.norm(pooled, axis=1)
    if not np.isfinite(pooled).all() or np.any(lengths < .10):
        raise ValueError('Actual broad shoulder normals cancel; no synthetic fallback.')
    return bulb.unit(pooled), cross_weight, axial, lengths


def incoming_frame(mesh, chart, patch, recipe=RECIPE):
    native = t.growth.native(mesh)
    pchart = np.concatenate([chart, t.face_values(mesh, chart)])
    sampler = bulb.study.NativeChartSampler(native.xyz, native.faces[:, :3], pchart)
    uv = patch['surface_uv']
    xyz, ids, bary = sampler.sample(uv, records=True)
    triangles = native.xyz[native.faces[ids, :3]]
    normals = bulb.unit(np.cross(triangles[..., 1, :]-triangles[..., 0, :],
                                 triangles[..., 2, :]-triangles[..., 0, :]))
    arc = np.c_[np.zeros(len(xyz)), np.cumsum(np.linalg.norm(np.diff(xyz, axis=1), axis=2), axis=1)]
    pooled, cross, axial, lengths = pool_normals(patch['parameter'], arc, normals, recipe)
    return dict(parameter=patch['parameter'], source_uv=uv, source_xyz=xyz,
        source_triangle_ids=ids, source_barycentric=bary, actual_triangle_normals=normals,
        actual_transverse_arc=arc, transverse_weights=cross, axial_weights=axial,
        pooled_normals=pooled, pooled_vector_lengths=lengths,
        incoming_generation=np.array(mesh.generation),
        incoming_control_xyz_sha256=np.array(finish.array_hash(mesh.xyz)))


def normal_delta(chart, patch, frame, generation, recipe=RECIPE):
    if int(frame['incoming_generation']) != generation:
        raise ValueError('Frame must belong to the actual incoming stage.')
    height, fields = signed_height(chart, patch, generation, recipe)
    parameter = np.clip(chart[:, 0], frame['parameter'][0], frame['parameter'][-1])
    normals = bulb.unit(PchipInterpolator(frame['parameter'], frame['pooled_normals'], axis=0)(parameter))
    normals[:, :2] *= np.where(chart[:, 1:] < 0., -1., 1.)
    delta = height[:, None]*normals
    fields['applied_pooled_normals'] = normals
    return delta, fields


def guarded_weight(mesh, chart, patch, recipe=RECIPE):
    """Zero all incident controls when a fan centre lies outside the patch."""
    controls = ownership(chart, patch, recipe)
    fans = ownership(t.face_values(mesh, chart), patch, recipe)
    weight = controls['weight'].copy()
    outside_faces = fans['weight'] == 0.
    if outside_faces.any():
        weight[np.unique(mesh.faces[outside_faces])] = 0.
    return weight, controls, fans


def final_positions(reference, baseline, active_delta, weight, recipe=RECIPE):
    candidate = baseline+weight[:, None]*(reference+active_delta-baseline)
    total = previous._bound(candidate-reference, recipe['maximum_total_shift'])
    result = reference+total
    result[weight == 0.] = baseline[weight == 0.]
    return result
