"""Actual WALL-parent measurements and attached, parent-oriented colony frames.

The saved G2 rail confines a search; it is never treated as the current trough.
All returned source points are barycentric samples on the supplied native body.
This module neither deforms a body nor performs the final X/Y reflection.
"""
from pathlib import Path
import hashlib
import importlib.util
import sys

import numpy as np
from scipy.spatial import cKDTree
import trimesh


HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / 'fold_visible_gate_20261012'
sys.path.insert(0, str(LEGACY))
_spec = importlib.util.spec_from_file_location('parent_guidance_bulb', LEGACY/'bulb_detail.py')
bulb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bulb)
_spec = importlib.util.spec_from_file_location('parent_guidance_child', LEGACY/'child_fold.py')
child = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(child)
t = bulb.study.previous.anchor.t


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _arrays(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key].copy() for key in data.files}


def _quintic(value):
    value = np.clip(np.asarray(value, float), 0., 1.)
    return value**3*(10.-15.*value+6.*value*value)


def _interp(parameter, samples, values):
    values = np.asarray(values)
    if values.ndim == 1:
        return np.interp(parameter, samples, values)
    return np.column_stack([np.interp(parameter, samples, values[:, i])
                            for i in range(values.shape[1])])


def measure_parent(source: Path, parent_index=1, *, mesh=None, chart=None):
    """Read a real G3 trough, preserving the old detector and native evidence.

    ``mesh/chart`` may supply the runner's common bounded-relaxed G3 carrier.
    ``parent_depth`` is the signed normal deficit below its *actual* shoulder
    chord (clipped at zero); the old constructed depth is retained separately.
    """
    source = Path(source)
    if (mesh is None) != (chart is None):
        raise ValueError('Supply both the actual carrier mesh and its chart.')
    supplied = mesh is not None
    if not supplied:
        mesh, chart, _ = t.load(source)
    if mesh.generation != 3:
        raise ValueError('Actual WALL G03 carrier required.')
    rail_path = source/f'rails_{int(parent_index)}.npz'
    rail = _arrays(rail_path)
    sampler = bulb.study.native_sampler(mesh, chart)
    result = child.measure_child(sampler, rail)
    parameter = result['parameter']
    search_parameter = result['parent_search_parameter']
    detected = result['parent_search_valid'] & result['parent_search_central']
    prominence = np.interp(parameter, search_parameter[detected],
                           result['parent_search_prominence'][detected])
    prominence_raw = np.interp(parameter, search_parameter, result['parent_search_prominence'])
    lower = np.interp(parameter, rail['parameter'], rail['lower_cross'])
    valley = result['parent_valley_cross']
    upper = result['parent_upper_cross']
    fraction = np.linspace(0., 1., 129)
    left_cross = lower[:, None]+(valley-lower)[:, None]*fraction
    left_uv = np.stack([np.broadcast_to(parameter[:, None], left_cross.shape), left_cross], axis=2)
    left_xyz, left_ids, left_bary = sampler.sample(left_uv, records=True)
    left_arc = np.concatenate([np.zeros((len(parameter), 1)),
        np.cumsum(np.linalg.norm(np.diff(left_xyz, axis=1), axis=2), axis=1)], axis=1)
    left_signed_arc = left_arc-left_arc[:, -1:]
    shoulder_xyz = result['parent_shoulder_xyz']
    lower_xyz, valley_xyz, upper_xyz = left_xyz[:, 0], left_xyz[:, -1], shoulder_xyz[:, -1]
    scaled = (parameter-parameter.mean())/(np.ptp(parameter)/2.)
    valley_coef = np.polyfit(scaled, valley_xyz, 3)
    tangent = bulb.unit(np.column_stack([np.polyval(np.polyder(valley_coef[:, i]), scaled)
                                        for i in range(3)]))
    across = upper_xyz-lower_xyz
    across = bulb.unit(across-tangent*np.sum(across*tangent, axis=1)[:, None])
    normal = bulb.unit(np.cross(tangent, across))
    old_normal = _interp(parameter, rail['parameter'], rail['normal'])
    orientation = np.where(np.sum(normal*old_normal, axis=1) >= 0., 1., -1.)
    normal *= orientation[:, None]
    tangent *= orientation[:, None]
    chord = upper_xyz-lower_xyz
    chord_squared = np.sum(chord*chord, axis=1)
    if np.any(chord_squared <= 1e-20):
        raise ValueError('Actual parent shoulder chord has zero width.')
    chord_fraction = np.clip(np.sum((valley_xyz-lower_xyz)*chord, axis=1)/chord_squared, 0., 1.)
    chord_point = lower_xyz+chord_fraction[:, None]*chord
    signed_deficit = np.sum((chord_point-valley_xyz)*normal, axis=1)
    depth = np.maximum(0., signed_deficit)
    width_vector = upper_xyz-valley_xyz
    width_vector -= tangent*np.sum(width_vector*tangent, axis=1)[:, None]
    width = np.linalg.norm(width_vector, axis=1)
    if np.any(width <= 1e-10) or not np.any(depth > 1e-10):
        raise ValueError('Actual parent has no positive outward shoulder width/depth.')
    result['legacy_parent_target_depth'] = result['parent_depth'].copy()
    result.update(parent_index=np.array(int(parent_index)), parent_depth=depth,
        parent_observed_prominence=prominence,
        parent_observed_prominence_raw=prominence_raw,
        parent_observed_prominence_measured_mask=result['parent_valley_measured_mask'].copy(),
        parent_observed_prominence_definition=np.array('Actual native trough prominence in the legacy detector pooled-normal projection; only bracketed missing central rays are interpolated'),
        parent_signed_chord_deficit=signed_deficit, parent_chord_projection_fraction=chord_fraction,
        parent_chord_xyz=chord_point, parent_valley_xyz=valley_xyz,
        parent_lower_xyz=lower_xyz, parent_upper_xyz=upper_xyz,
        parent_tangent=tangent, parent_normal=normal, parent_across=across,
        parent_shoulder_width=width, parent_valley_fit_coefficients=valley_coef,
        parent_lower_cross=lower, parent_lower_shoulder_uv=left_uv,
        parent_lower_shoulder_xyz=left_xyz, parent_lower_shoulder_triangle_ids=left_ids,
        parent_lower_shoulder_barycentric=left_bary, parent_lower_shoulder_signed_arc=left_signed_arc,
        parent_surface_uv=np.concatenate([left_uv[:, :-1], result['parent_shoulder_uv']], axis=1),
        parent_surface_signed_arc=np.concatenate([left_signed_arc[:, :-1], result['parent_shoulder_arc']], axis=1),
        source_path=np.array(str(source.resolve())), source_generation=np.array(3),
        source_control_sha256=np.array(_hash(source/'control_quad.npz')),
        source_rails_sha256=np.array(_hash(rail_path)), supplied_carrier=np.array(supplied),
        measured_carrier_xyz_sha256=np.array(hashlib.sha256(np.ascontiguousarray(mesh.xyz).tobytes()).hexdigest()),
        parent_depth_definition=np.array('Actual lower/upper shoulder chord projected on current pooled parent normal; not prescribed rail depth'),
        signed_arc_definition=np.array('Actual left and right sampled surface arc, signed at valley and normalized by right shoulder total arc'),
        axial_plateau_fraction=np.array(.6), transverse_fade_fraction=np.array(.15))
    return result


def _linear_interp(query, abscissa, values):
    """Monotonic interpolation with explicit linear extension for diagnostics."""
    query = np.asarray(query, float)
    result = np.interp(query, abscissa, values)
    below, above = query < abscissa[0], query > abscissa[-1]
    result[below] = values[0]+(query[below]-abscissa[0])*(values[1]-values[0])/(abscissa[1]-abscissa[0])
    result[above] = values[-1]+(query[above]-abscissa[-1])*(values[-1]-values[-2])/(abscissa[-1]-abscissa[-2])
    return result


def _arc_coordinate(parameter, cross, parent):
    samples = np.asarray(parent['parameter'])
    uv = np.asarray(parent.get('parent_surface_uv', parent['parent_shoulder_uv']))
    arc = np.asarray(parent.get('parent_surface_signed_arc', parent['parent_shoulder_arc']))
    arc = arc/np.asarray(parent['parent_shoulder_arc'])[:, -1:]
    low = np.clip(np.searchsorted(samples, parameter, side='right')-1, 0, len(samples)-2)
    high = low+1
    alpha = np.clip((parameter-samples[low])/(samples[high]-samples[low]), 0., 1.)
    result = np.zeros_like(parameter, dtype=float)
    for row in range(len(samples)):
        for ids, weight in ((low, 1.-alpha), (high, alpha)):
            mask = ids == row
            if mask.any():
                result[mask] += weight[mask]*_linear_interp(cross[mask], uv[row, :, 1], arc[row])
    return result


def patch_coordinates(chart, parent):
    """Canonical material ownership; q is [-1,+1], u is signed physical arc.

    The negative-side corridor uses measured left shoulder arc, with the same
    physical normalization as the right side. This does not infer XYZ from UV.
    """
    chart = np.asarray(chart, float)
    if chart.ndim != 2 or chart.shape[1] != 3 or not np.isfinite(chart).all():
        raise ValueError('Finite N×3 material chart required.')
    samples = np.asarray(parent['parameter'])
    q = 2.*(chart[:, 0]-samples[0])/(samples[-1]-samples[0])-1.
    cross = np.arctan2(np.abs(chart[:, 2]), np.abs(chart[:, 1]))
    u = _arc_coordinate(chart[:, 0], cross, parent)
    plateau = float(parent.get('axial_plateau_fraction', .6))
    fade = float(parent.get('transverse_fade_fraction', .15))
    axial = _quintic((1.-np.abs(q))/(1.-plateau))
    body = np.linalg.norm(chart[:, 1:], axis=1) > .2
    axial *= body
    transverse = _quintic(u/fade)*_quintic((1.-u)/fade)
    core = bulb.compact(u/.25)
    return dict(q=q, u=u, envelope=axial*transverse, core_weight=axial*core,
                axial_weight=axial, transverse_weight=transverse)


def _uv_at_fraction(parameter, fraction, parent):
    parameter, fraction = np.broadcast_arrays(np.asarray(parameter, float), np.asarray(fraction, float))
    samples = np.asarray(parent['parameter'])
    rows = np.asarray(parent.get('parent_surface_uv', parent['parent_shoulder_uv']))[:, :, 1]
    arc = np.asarray(parent.get('parent_surface_signed_arc', parent['parent_shoulder_arc']))
    arc = arc/np.asarray(parent['parent_shoulder_arc'])[:, -1:]
    result = np.empty(parameter.size)
    for i, (p, f) in enumerate(zip(parameter.ravel(), fraction.ravel())):
        low = int(np.clip(np.searchsorted(samples, p, side='right')-1, 0, len(samples)-2))
        high = low+1
        alpha = np.clip((p-samples[low])/(samples[high]-samples[low]), 0., 1.)
        # Invert the same longitudinally interpolated piecewise-linear map used
        # by patch_coordinates, rather than interpolate separately inverted UV.
        knots = np.unique(np.r_[rows[low], rows[high]])
        values = ((1.-alpha)*_linear_interp(knots, rows[low], arc[low])+
                  alpha*_linear_interp(knots, rows[high], arc[high]))
        if np.any(np.diff(values) <= 0.):
            raise ValueError('Measured physical-arc chart is not strictly monotonic.')
        result[i] = np.interp(f, values, knots)
    return np.column_stack([parameter.ravel(), result])


def make_guided_colonies(mesh, chart, parent, recipe):
    """Few attached colonies in one measured shoulder, with inherited frames.

    The caller supplies the actual carrier *after* any middle-fold operation.
    Parent UV ownership is retained, while every point/frame is read anew on it.
    No nearest-world-point substitution and no synthetic fallback frame is used.
    """
    native = t.growth.native(mesh)
    triangles = native.faces[:, :3]
    physical = trimesh.Trimesh(native.xyz, triangles, process=False)
    normals = physical.vertex_normals.copy()
    pchart = np.concatenate([chart, t.face_values(mesh, chart)])
    canonical = (pchart[:, 1] >= -1e-12) & (pchart[:, 2] >= -1e-12) & (np.linalg.norm(pchart[:, 1:], axis=1) > .2)
    surface_ids = np.flatnonzero(canonical)
    tree = cKDTree(native.xyz[surface_ids])
    sampler = bulb.study.native_sampler(mesh, chart)
    parameter = np.asarray(parent['parameter'])
    valley = np.asarray(parent['parent_valley_xyz'])
    longitudinal_arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(valley, axis=0), axis=1))]
    radius = float(recipe.get('primary_radius', .30))
    secondary_radius = float(recipe.get('secondary_radius', .14))
    count = int(recipe.get('guided_primary_count', np.clip(np.floor(longitudinal_arc[-1]/(2.3*radius))+1, 3, 7)))
    if not 3 <= count <= 7 or longitudinal_arc[-1] <= 1e-10:
        raise ValueError('Guided primary count must be 3–7 on a positive actual parent arc.')
    golden = (np.sqrt(5.)-1.)/2.
    index = np.arange(count)
    phase = (index+.5+.22*(2.*np.mod((index+1)*golden, 1.)-1.))/count
    station = np.interp((.20+.60*phase)*longitudinal_arc[-1], longitudinal_arc, parameter)
    shoulder_fraction = .55+.16*(2.*np.mod((index+1)*golden+.17, 1.)-1.)
    primary_uv = _uv_at_fraction(station, shoulder_fraction, parent)
    centres, pooled, tangents, bitangents, radii, amplitudes = [], [], [], [], [], []
    levels, parents, sample_uv, source_ids, source_bary = [], [], [], [], []
    unpooled, pooled_counts, trajectory_uv, trajectory_xyz, trajectory_ids, trajectory_bary = [], [], [], [], [], []

    def add(uv, r, amplitude, level, parent_id, inherited=None, fraction=None):
        xyz, tri, bary = sampler.sample(np.asarray(uv)[None], records=True)
        point, tri, bary = xyz[0], int(tri[0]), bary[0]
        naive = bulb.unit(bary@normals[triangles[tri]])
        ids = surface_ids[np.asarray(tree.query_ball_point(point, r), int)]
        ids = ids[(normals[ids]@naive) > .25]
        weights = bulb.compact(np.linalg.norm(native.xyz[ids]-point, axis=1)/r)
        normal = bulb.unit(np.sum(weights[:, None]*normals[ids], axis=0)) if weights.sum() else naive
        if inherited is None:
            pp = np.clip(uv[0]+np.linspace(-.04, .04, 5)*np.ptp(parameter), parameter[0], parameter[-1])
            curve_uv = _uv_at_fraction(pp, np.full(5, fraction), parent)
            curve, curve_ids, curve_bary = sampler.sample(curve_uv, records=True)
            coefficients = np.polyfit(pp-uv[0], curve, 2)
            direction = coefficients[1]
            trajectory_uv.append(curve_uv); trajectory_xyz.append(curve)
            trajectory_ids.append(curve_ids); trajectory_bary.append(curve_bary)
        else:
            direction = inherited
        tangent = bulb.unit(direction-normal*np.dot(direction, normal))
        if np.linalg.norm(normal) < .9 or np.linalg.norm(tangent) < .9:
            raise ValueError('Actual incoming shoulder has no stable normal/tangent frame.')
        bitangent = bulb.unit(np.cross(normal, tangent))
        # Positive transverse direction is the actual inherited upper shoulder.
        across = _interp(np.array([uv[0]]), parameter, parent['parent_across'])[0]
        if np.dot(bitangent, across) < 0.:
            tangent *= -1.; bitangent *= -1.
        centres.append(point); pooled.append(normal); tangents.append(tangent); bitangents.append(bitangent)
        radii.append(r); amplitudes.append(amplitude); levels.append(level); parents.append(parent_id)
        sample_uv.append(uv); source_ids.append(tri); source_bary.append(bary); pooled_counts.append(len(ids))
        unpooled.append(naive)

    for uv, f in zip(primary_uv, shoulder_fraction):
        add(uv, radius, float(recipe.get('primary_amplitude', .22)), 0, -1, fraction=f)
    secondary_count = int(recipe.get('secondary_per_primary', 2))
    if secondary_count != 2:
        raise ValueError('This bounded pilot retains two secondary buds per primary.')
    for primary in range(count):
        p, f = station[primary], shoulder_fraction[primary]
        for secondary in range(secondary_count):
            angle = 2.*np.pi*np.mod((primary+1)*golden+secondary*.38196601125, 1.)
            offset = .65*radius
            delta_p = .01*np.ptp(parameter)
            pp = np.clip(np.array([p-delta_p, p+delta_p]), parameter[0], parameter[-1])
            curve = sampler.sample(_uv_at_fraction(pp, np.full(2, f), parent))
            speed = np.linalg.norm(curve[1]-curve[0])/(pp[1]-pp[0])
            if speed <= 1e-10:
                raise ValueError('Actual inherited longitudinal trajectory has zero speed.')
            shoulder_length = np.interp(p, parameter, parent['parent_shoulder_arc'][:, -1])
            sp = np.clip(p+offset*np.cos(angle)/speed, parameter[0], parameter[-1])
            sf = np.clip(f+offset*np.sin(angle)/shoulder_length, .35, .75)
            uv = _uv_at_fraction(np.array([sp]), np.array([sf]), parent)[0]
            add(uv, secondary_radius, float(recipe.get('secondary_amplitude', .07)), 1, primary,
                inherited=tangents[primary])
    uv = np.asarray(sample_uv)
    coords = patch_coordinates(np.column_stack([uv[:, 0], np.cos(uv[:, 1]), np.sin(uv[:, 1])]), parent)
    if np.any((coords['u'] < .35-1e-8) | (coords['u'] > .75+1e-8)):
        raise ValueError('Attached colony centre escaped its measured owned shoulder.')
    return dict(centres=np.asarray(centres), normals=np.asarray(pooled), tangents=np.asarray(tangents),
        bitangents=np.asarray(bitangents), radii=np.asarray(radii), amplitudes=np.asarray(amplitudes),
        levels=np.asarray(levels), parent_ids=np.asarray(parents), native_vertex_ids=np.full(len(centres), -1, int),
        pooled_native_normal_counts=np.asarray(pooled_counts), sample_uv=uv, source_xyz=np.asarray(centres),
        source_triangle_ids=np.asarray(source_ids), source_barycentric=np.asarray(source_bary),
        primary_sample_uv=uv[:count], primary_source_xyz=np.asarray(centres)[:count],
        primary_source_triangle_ids=np.asarray(source_ids)[:count], primary_source_barycentric=np.asarray(source_bary)[:count],
        primary_unpooled_normals=np.asarray(unpooled)[:count],
        owner_parent_indices=np.full(len(centres), int(parent['parent_index']), int), owned_arc_fraction=coords['u'],
        primary_requested_arc_fraction=shoulder_fraction, trajectory_sample_uv=np.asarray(trajectory_uv),
        trajectory_sample_xyz=np.asarray(trajectory_xyz), trajectory_source_triangle_ids=np.asarray(trajectory_ids),
        trajectory_source_barycentric=np.asarray(trajectory_bary),
        source_control_generation=np.array(mesh.generation),
        source_carrier_xyz_sha256=np.array(hashlib.sha256(np.ascontiguousarray(mesh.xyz).tobytes()).hexdigest()),
        symmetry_policy=np.array('Canonical-quadrant samples only; runner constructively reflects final carrier/detail delta'))
