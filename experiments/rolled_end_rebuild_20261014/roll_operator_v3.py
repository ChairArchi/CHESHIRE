"""One local ordered-fold rebuild on the unchanged original SPAN G7 topology.

Actual source chart coordinates address a verified original-body WALL context
only, excluding controls incident to nonzero preserved G3 topology events.
Separate connected support components remain separate. The large component
has three overlapping angular guide lobes; each guide is a quintic Bezier
profile with source endpoints, source endpoint directions and a measured
source radial envelope. No global inverse chart, fairing, new ornament,
normal field, Mandelbulb evaluation or subdivision is performed here.
"""
from copy import deepcopy
import hashlib
import importlib.util
from math import comb
from pathlib import Path
import sys

import numpy as np
from scipy.interpolate import LinearNDInterpolator, PchipInterpolator
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(REPO/'src') not in sys.path:
    sys.path.insert(0, str(REPO/'src'))
from cheshire.reference_subdivision import ArrayMesh

_FIELD_PATH = HERE.parent/'whole_column_detail_20261013/whole_field.py'
_spec = importlib.util.spec_from_file_location('rolled_end_frozen_id_transport', _FIELD_PATH)
field = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = field
_spec.loader.exec_module(field)

RECIPE = dict(
    schema='CHESHIRE_LOCAL_ORDERED_ROUNDED_FOLD_REBUILD_BODY_CONTEXT_V2_20261014',
    source_generation=7, output_generation=7, intended_coarse_level=4,
    source_geometry='Actual current G7 XYZ, including its retained old-G4 vertex prefix; no earlier XYZ is substituted.',
    local_chart_context_t=[.55, .700], local_chart_context_theta=[.20, 1.52],
    context_provenance='Required bool[nc] lift_maps[0][source_body_vertex_mask]; runner binds exact preserved G4 parent_face -> G3 face_event_ids and includes only controls whose every incident parent event is zero.',
    local_chart='t=chart[:,0]; theta=atan2(abs(chart[:,2]),abs(chart[:,1])). Only verified canonical x<0,y>0 local context is inverted.',
    expected_canonical_component_sizes=[406, 54, 19, 16, 1, 1],
    ignored_component_maximum_size=1,
    major_component_lobe_centres=[.405, .785, 1.115],
    major_component_lobe_basis='Independent read-only source-envelope audit: actual main-component radial maxima at theta .40690, .78494 and 1.11761; corresponding prominence .03050, .11718 and .06538. Weak seam near .603 is not assigned a new equal lobe.',
    major_component_kernel_halfwidth=.30,
    major_component_kernel='K(u)=max(0,1-u*u)^3 for abs(u)<1, zero otherwise; u=(theta-centre)/.30. Compact C2 kernel.',
    lobe_partition='Normalize three compact C2 angular kernels within the same actual EDGE-connected 406-control component; reject any uncovered component control. No infinite tails or gap/component bridging.',
    guide_coarse_membership_threshold=.20, guide_theta_bin_width=.055,
    guide_t_quantiles=[.05, .95], guide_t_padding=.004,
    endpoint_tangent_outside_difference=.003,
    profile='Quintic Bezier: P0=source(t0,theta), P1=P0+.18L*T0, P2=P0+1.20*(P5-P0)+A*N, P3=P0-.20*(P5-P0)+.82*A*N, P4=P5-.18L*T1, P5=source(t1,theta).',
    profile_scope='One fixed asymmetric rounded-fold profile; its actual sampled tangent turn is reported. A C-shaped return or visual success is not assumed.',
    crest_normal='N=normalized XY radial direction at the mean source endpoint; guide T=endpoint chord projected off N and oriented +Z.',
    endpoint_tangents='Actual source outside finite differences, normalized and sign-oriented to the forward endpoint chord. Tangent control length=.18*endpoint chord length.',
    radial_envelope='Actual source G7 radial maxima inside each lifted local lobe, binned by theta; endpoint and A=0 profile radial maxima provide explicit necessary floors.',
    radial_envelope_theta_samples=49, radial_calibration_profile_samples=81,
    radial_calibration_bisection_steps=48,
    radial_calibration='For each fixed theta sample, solve A once so the 81-sample profile maximum XY radius reaches its measured/floored envelope. Interpolate calibrated A in theta with PCHIP.',
    mask_promotion='quintic_smoothstep(clip(coarse_mask/.30,0,1)); multiply actual component/lobe membership before linear V/E/F lifting.',
    endpoint_feather_t=.004,
    final_blend='Lift actual scalar component memberships; multiply by quintic endpoint feather. Sum membership*(rebuilt_target-actual_G7_source), never lift a coarse displacement.',
    reflection='Frozen whole_field._transport after actual source-ID canonical delta reflection; preserve original source coordinates and source residuals.',
    maximum_displacement_height_fraction=.025,
    displacement_cap='D *= B*tanh(norm(D)/B)/norm(D), B=.025H. Applied to final transported local vector; cap/feather may reduce the calibrated profile peak.',
    preservation='Exact source where aggregate blend mask is zero. Faces, classes, rest, anchors, chart and all original IDs remain unchanged.',
    added_CC_passes=0, target_neutral_CC_passes=0, added_topology_events=0,
    added_mandelbulb_evaluations=0, normal_field_passes=0,
    source_geometry_averaged=False,
    interpretation='One local end-shape reconstruction authorized by the user, preserving the large source flow outside the marked support. No collision repair, fabrication certification or G1 guarantee.',
)


def _hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def code_hashes():
    paths = (Path(__file__).resolve(), _FIELD_PATH, REPO/'src/cheshire/reference_subdivision.py')
    return {p.relative_to(REPO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _quintic(x):
    x = np.clip(np.asarray(x, float), 0., 1.)
    return x*x*x*(10.+x*(-15.+6.*x))


def _summary(value):
    value = np.asarray(value, float)
    return dict(count=int(value.size), minimum=float(value.min()) if value.size else None,
        maximum=float(value.max()) if value.size else None,
        quantiles=np.quantile(value, [0., .5, .9, .99, 1.]).tolist() if value.size else None)


def _faces(value, count, name):
    value = np.asarray(value)
    if (value.ndim != 2 or value.shape[1] != 4 or not len(value) or
            value.dtype.kind not in 'iu' or value.min() < 0 or value.max() >= count):
        raise ValueError('Actual all-quad source indices required: '+name)
    return value


def _edges(faces):
    value = np.stack([faces, np.roll(faces, -1, axis=1)], axis=-1).reshape(-1, 2)
    value.sort(axis=1)
    return np.unique(value, axis=0)


def _lift(value, maps):
    for edge, face in maps:
        value = np.concatenate([value, value[edge].mean(axis=1), value[face].mean(axis=1)])
    return value


def _unit(value, label):
    value = np.asarray(value, float)
    length = np.linalg.norm(value, axis=-1)
    if np.any(length <= 1e-12) or not np.isfinite(value).all():
        raise ValueError('Degenerate local '+label+'; no fallback.')
    return value/length[..., None]


def _bezier(controls, s):
    """Paired vectorized controls (n,6,3) and scalar parameters (n,)."""
    s = np.asarray(s, float)
    basis = np.stack([comb(5, k)*s**k*(1.-s)**(5-k) for k in range(6)], axis=1)
    return np.einsum('nk,nkj->nj', basis, controls)


def _sample_profiles(controls):
    s = np.linspace(0., 1., RECIPE['radial_calibration_profile_samples'])
    basis = np.stack([comb(5, k)*s**k*(1.-s)**(5-k) for k in range(6)], axis=1)
    return np.einsum('sk,nkj->nsj', basis, controls)


def _curve_sanity(controls, normal, tangent):
    """Sampled planar noncrossing and tangent-turn facts, not surface proof."""
    points = _sample_profiles(controls)
    relative = points-points[:, :1]
    planar = np.stack([np.einsum('nsj,nj->ns', relative, tangent),
                       np.einsum('nsj,nj->ns', relative, normal)], axis=-1)
    crossing_count = 0
    minimum_segment_length = np.inf
    maximum_turn = 0.
    maximum_backward_step = 0.
    a_index, b_index = np.triu_indices(planar.shape[1]-1, k=2)
    cross = lambda a, b: a[..., 0]*b[..., 1]-a[..., 1]*b[..., 0]
    for curve in planar:
        segments = np.diff(curve, axis=0)
        length = np.linalg.norm(segments, axis=1)
        minimum_segment_length = min(minimum_segment_length, float(length.min()))
        if np.any(length <= 1e-12):
            raise ValueError('Degenerate sampled rebuilt profile segment.')
        angle = np.unwrap(np.arctan2(segments[:, 1], segments[:, 0]))
        maximum_turn = max(maximum_turn, float(angle.max()-angle.min()))
        maximum_backward_step = max(maximum_backward_step, float(max(0., -segments[:, 0].min())))
        a, b = curve[a_index], curve[b_index]
        da, db = segments[a_index], segments[b_index]
        denominator = cross(da, db)
        valid = np.abs(denominator) > 1e-14
        sa = np.divide(cross(b-a, db), denominator, out=np.zeros_like(denominator), where=valid)
        sb = np.divide(cross(b-a, da), denominator, out=np.zeros_like(denominator), where=valid)
        crossing_count += int(np.count_nonzero(valid & (sa > 1e-9) & (sa < 1.-1e-9) & (sb > 1e-9) & (sb < 1.-1e-9)))
    # Projected guide crossings are recorded, not a solid-geometry admission test.
    # The user permits overlap; actual native mesh checks and visual review remain required.
    return dict(profile_count=len(controls), samples_per_profile=points.shape[1],
        strict_nonadjacent_planar_segment_crossings=crossing_count,
        minimum_sampled_segment_length=minimum_segment_length,
        maximum_sampled_tangent_turn_radians=maximum_turn,
        maximum_sampled_backward_axial_step=maximum_backward_step,
        scope='Diagnostic projection of fixed-theta guide profiles. Crossing counts do not certify 3D intersections or impose a collision-free design constraint; actual mesh checks and visual review remain required.')


def _local_interpolator(points, chart, canonical, height, body_mask):
    body_mask = np.asarray(body_mask)
    if body_mask.dtype != np.dtype(bool) or body_mask.shape != (len(points),):
        raise ValueError('Actual boolean coarse source-body provenance mask required.')
    theta = np.arctan2(np.abs(chart[:, 2]), np.abs(chart[:, 1]))
    t = chart[:, 0]
    domain = canonical & (t >= .55) & (t <= .700) & (theta >= .20) & (theta <= 1.52)
    selected = domain & body_mask
    source_ids = np.flatnonzero(selected)
    uv = np.column_stack([t[source_ids], theta[source_ids]])
    if len(uv) < 20:
        raise ValueError('Insufficient actual local WALL chart context.')
    unique, first, inverse = np.unique(uv, axis=0, return_index=True, return_inverse=True)
    minima = np.full((len(unique), 3), np.inf)
    maxima = np.full((len(unique), 3), -np.inf)
    for k in range(3):
        np.minimum.at(minima[:, k], inverse, points[source_ids, k])
        np.maximum.at(maxima[:, k], inverse, points[source_ids, k])
    spread = np.linalg.norm(maxima-minima, axis=1)
    if spread.max() > 1e-9*height:
        raise ValueError('Noninjective local chart UV maps to different actual source positions.')
    interpolator = LinearNDInterpolator(unique, points[source_ids[first]], fill_value=np.nan, rescale=True)

    def sample(t_value, theta_value):
        t_value, theta_value = np.broadcast_arrays(t_value, theta_value)
        result = interpolator(np.column_stack([t_value.ravel(), theta_value.ravel()]))
        if not np.isfinite(result).all():
            raise ValueError('Local guide query escaped verified actual WALL context convex hull; no extrapolation.')
        return result.reshape(t_value.shape+(3,))

    return sample, dict(context_control_count=len(source_ids), unique_local_UV_count=len(unique),
        source_body_vertex_mask_sha256=_hash(body_mask),
        source_body_vertex_count=int(np.count_nonzero(body_mask)),
        canonical_context_domain_control_count=int(np.count_nonzero(domain)),
        canonical_context_excluded_nonbody_control_count=int(np.count_nonzero(domain & ~body_mask)),
        actual_context_t_range=[float(t[source_ids].min()), float(t[source_ids].max())],
        actual_context_theta_range=[float(theta[source_ids].min()), float(theta[source_ids].max())],
        requested_context_t_range=[.55, .700], requested_context_theta_range=[.20, 1.52],
        duplicate_local_UV_count=len(source_ids)-len(unique), maximum_duplicate_world_spread=float(spread.max()),
        world_spread_tolerance=1e-9*height, source_ids_sha256=_hash(source_ids),
        local_uv_sha256=_hash(uv), local_xyz_sha256=_hash(points[source_ids]),
        method='scipy LinearNDInterpolator on actual current-G7 coarse-prefix canonical original-body local WALL UV only; all nonzero preserved-G3-event incident controls excluded',
        global_inverse_chart_used=False)


def _bounds(uv):
    theta = uv[:, 1]
    bins = np.floor((theta-theta.min())/RECIPE['guide_theta_bin_width']).astype(int)
    centres, low, high = [], [], []
    for bin_id in np.unique(bins):
        group = uv[bins == bin_id]
        if len(group) < 3:
            continue
        centres.append(float(np.mean(group[:, 1])))
        q = np.quantile(group[:, 0], RECIPE['guide_t_quantiles'])
        low.append(float(q[0]-.004))
        high.append(float(q[1]+.004))
    if len(centres) < 3:
        q = np.quantile(uv[:, 0], RECIPE['guide_t_quantiles'])
        low, high = [float(q[0]-.004)], [float(q[1]+.004)]
        centres = [float(np.mean(theta))]
        lo_function = lambda value: np.full(np.asarray(value).shape, low[0])
        hi_function = lambda value: np.full(np.asarray(value).shape, high[0])
    else:
        lo_curve, hi_curve = PchipInterpolator(centres, low), PchipInterpolator(centres, high)
        lo_function = lambda value: lo_curve(np.clip(value, centres[0], centres[-1]))
        hi_function = lambda value: hi_curve(np.clip(value, centres[0], centres[-1]))
    return lo_function, hi_function, dict(theta_knots=centres, t0_values=low, t1_values=high,
        method='PCHIP with clamped theta endpoints' if len(centres) > 1 else 'Actual selected-lobe quantiles, constant in theta')


def _controls(sample, theta, t0, t1, amplitude):
    p0, p5 = sample(t0, theta), sample(t1, theta)
    chord = p5-p0
    length = np.linalg.norm(chord, axis=1)
    if np.any(length <= 1e-7):
        raise ValueError('Local guide endpoints have a degenerate chord.')
    normal = np.column_stack([p0[:, 0]+p5[:, 0], p0[:, 1]+p5[:, 1], np.zeros(len(theta))])
    normal = _unit(normal, 'radial direction')
    tangent = chord-np.sum(chord*normal, axis=1)[:, None]*normal
    tangent = _unit(tangent, 'axial direction')
    tangent[tangent[:, 2] < 0.] *= -1.
    t_start = _unit(p0-sample(t0-.003, theta), 'source start outside tangent')
    t_end = _unit(sample(t1+.003, theta)-p5, 'source end outside tangent')
    flip_start = np.sum(t_start*chord, axis=1) < 0.
    flip_end = np.sum(t_end*chord, axis=1) < 0.
    t_start[flip_start] *= -1.
    t_end[flip_end] *= -1.
    controls = np.stack([p0, p0+.18*length[:, None]*t_start,
        p0+1.20*chord+amplitude[:, None]*normal,
        p0-.20*chord+.82*amplitude[:, None]*normal,
        p5-.18*length[:, None]*t_end, p5], axis=1)
    return controls, normal, tangent, dict(start_direction_sign_reoriented_count=int(flip_start.sum()),
        end_direction_sign_reoriented_count=int(flip_end.sum()))


def _calibrate(sample, theta, low, high, source_t, source_theta, source_radius, height):
    """One scalar bisection per theta node; no visual or parameter search."""
    t0, t1 = low(theta), high(theta)
    if np.any(t1-t0 <= .004):
        raise ValueError('Insufficient nonzero source span for fixed rebuilt profile.')
    controls, normal, tangent, direction_stats = _controls(sample, theta, t0, t1, np.zeros(len(theta)))
    base_points = _sample_profiles(controls)
    base_max = np.linalg.norm(base_points[:, :, :2], axis=2).max(axis=1)
    source_peak = np.linalg.norm(sample(t0[:, None]+(t1-t0)[:, None]*np.linspace(0., 1., 81), theta[:, None])[:, :, :2], axis=2).max(axis=1)
    bins = np.argmin(np.abs(source_theta[:, None]-theta[None, :]), axis=1)
    valid = (source_t >= low(source_theta)) & (source_t <= high(source_theta))
    dense_peak = np.full(len(theta), -np.inf)
    np.maximum.at(dense_peak, bins[valid], source_radius[valid])
    populated = np.isfinite(dense_peak)
    source_peak[populated] = np.maximum(source_peak[populated], dense_peak[populated])
    target_peak = np.maximum(source_peak, base_max)
    lo, hi = np.zeros(len(theta)), np.full(len(theta), height)
    test = controls.copy()
    test[:, 2] += hi[:, None]*normal
    test[:, 3] += .82*hi[:, None]*normal
    if np.any(np.linalg.norm(_sample_profiles(test)[:, :, :2], axis=2).max(axis=1) < target_peak):
        raise ValueError('Fixed amplitude bracket does not contain measured source radial envelope.')
    for _ in range(RECIPE['radial_calibration_bisection_steps']):
        amplitude = .5*(lo+hi)
        test = controls.copy()
        test[:, 2] += amplitude[:, None]*normal
        test[:, 3] += .82*amplitude[:, None]*normal
        peak = np.linalg.norm(_sample_profiles(test)[:, :, :2], axis=2).max(axis=1)
        below = peak < target_peak
        lo[below], hi[~below] = amplitude[below], amplitude[~below]
    amplitude = .5*(lo+hi)
    final_controls, normal, tangent, _ = _controls(sample, theta, t0, t1, amplitude)
    achieved = np.linalg.norm(_sample_profiles(final_controls)[:, :, :2], axis=2).max(axis=1)
    sanity = _curve_sanity(final_controls, normal, tangent)
    amplitude_curve = PchipInterpolator(theta, amplitude)
    amplitude_function = lambda value: amplitude_curve(np.clip(value, theta[0], theta[-1]))
    return amplitude_function, dict(theta_samples=theta.tolist(), source_radial_peak=source_peak.tolist(),
        target_radial_peak=target_peak.tolist(), achieved_profile_radial_peak=achieved.tolist(),
        calibrated_amplitude=amplitude.tolist(), dense_source_populated_theta_bin_count=int(populated.sum()),
        base_profile_floor_raised_count=int(np.count_nonzero(base_max > source_peak)),
        maximum_base_profile_floor_raise=float(np.maximum(base_max-source_peak, 0.).max()),
        maximum_sampled_radial_calibration_error=float(np.abs(achieved-target_peak).max()),
        direction_statistics=direction_stats, profile_sanity=sanity,
        scope='Calibration of authored unblended uncapped guide profiles. Final feathered/capped mesh radial maxima are reported separately.')


def build(mesh, chart, vertex_pairs, coarse_faces, coarse_vertex_count, coarse_mask, lift_maps, height):
    """Return output mesh, JSON metadata and compact NPZ-safe evidence.

    All source arrays are read-only by convention and are never mutated.
    Memberships are lifted on actual preserved V/E/F birth associations;
    target points are evaluated directly at the actual G7 chart coordinates.
    """
    xyz, chart = np.asarray(mesh.xyz), np.asarray(chart)
    nv, nc = len(xyz), int(coarse_vertex_count)
    height = float(height)
    if (mesh.generation != 7 or getattr(mesh, 'surface', None) != 'mean' or xyz.shape != (nv, 3) or
            chart.shape != xyz.shape or not np.isfinite(xyz).all() or not np.isfinite(chart).all() or
            not 0 < nc < nv or nc != coarse_vertex_count or not np.isfinite(height) or height <= 0.):
        raise ValueError('Actual finite mean-native original G7 and preserved coarse prefix required.')
    faces = _faces(mesh.faces, nv, 'G7')
    coarse_faces = _faces(coarse_faces, nc, 'coarse prefix')
    if (np.asarray(mesh.classes).shape != (nv,) or np.asarray(mesh.rest).shape != xyz.shape or
            np.asarray(mesh.anchors).shape[0] != len(faces)):
        raise ValueError('Actual unchanged classes/rest/anchors required.')
    mask = np.asarray(coarse_mask, float).copy()
    if mask.shape != (nc,) or not np.isfinite(mask).all() or np.any(mask < 0.) or np.any(mask > 1.):
        raise ValueError('Finite authorized coarse mask in [0,1] required.')
    ids, pairs = field._mirror_pairs(vertex_pairs, nv)
    coarse_pairs = {key: value[:nc] for key, value in pairs.items()}
    for key, pair in coarse_pairs.items():
        if pair.max() >= nc or not np.array_equal(pair[pair], np.arange(nc)) or not np.allclose(mask, mask[pair], rtol=0., atol=1e-12):
            raise ValueError('Actual coarse prefix/mask source symmetry invalid: '+key)
    maps, map_records, running = [], [], nc
    for i, mapping in enumerate(lift_maps):
        edge = np.asarray(mapping['input_edges'])
        face = _faces(mapping['input_faces'], running, 'saved lift stage '+str(i))
        if edge.ndim != 2 or edge.shape[1] != 2 or edge.dtype.kind not in 'iu' or edge.min() < 0 or edge.max() >= running or np.any(edge[:, 0] == edge[:, 1]):
            raise ValueError('Actual saved edge birth associations required.')
        if i == 0 and not np.array_equal(face, coarse_faces):
            raise ValueError('First lift input faces differ from actual coarse topology.')
        out_count = running+len(edge)+len(face)
        map_records.append(dict(stage=i, input_vertex_count=running, output_vertex_count=out_count,
            input_edges_sha256=_hash(edge), input_faces_sha256=_hash(face)))
        maps.append((edge, face))
        running = out_count
    if not maps or running != nv:
        raise ValueError('Actual V/E/F hierarchy does not terminate at original G7.')

    coarse_xyz, coarse_chart = xyz[:nc], chart[:nc]
    canonical = (coarse_xyz[:, 0] < 0.) & (coarse_xyz[:, 1] > 0.)
    active_ids = np.flatnonzero((mask > 0.) & canonical)
    edge_graph = _edges(coarse_faces)
    inverse = np.full(nc, -1, np.int64)
    inverse[active_ids] = np.arange(len(active_ids))
    active_edges = inverse[edge_graph]
    active_edges = active_edges[np.all(active_edges >= 0, axis=1)]
    graph = coo_matrix((np.ones(2*len(active_edges)),
        (np.r_[active_edges[:, 0], active_edges[:, 1]], np.r_[active_edges[:, 1], active_edges[:, 0]])),
        shape=(len(active_ids), len(active_ids))).tocsr()
    count, labels = connected_components(graph, directed=False)
    components = sorted([active_ids[labels == value] for value in range(count)], key=lambda value: (-len(value), int(value.min())))
    component_sizes = [len(value) for value in components]
    if component_sizes != RECIPE['expected_canonical_component_sizes']:
        raise ValueError('Frozen marked WALL support component sizes differ: '+str(component_sizes))
    if 'source_body_vertex_mask' not in lift_maps[0]:
        raise ValueError('Missing runner-bound preserved-body vertex provenance mask.')
    source_body_vertex_mask = np.asarray(lift_maps[0]['source_body_vertex_mask'])
    if source_body_vertex_mask.dtype != np.dtype(bool) or source_body_vertex_mask.shape != (nc,):
        raise ValueError('Runner-bound source-body mask must be exact bool[nc].')
    sample, context_record = _local_interpolator(coarse_xyz, coarse_chart, canonical, height,
        source_body_vertex_mask)
    coarse_theta = np.arctan2(np.abs(coarse_chart[:, 2]), np.abs(coarse_chart[:, 1]))
    promoted = _quintic(mask/.30)
    lobe_specs, coarse_memberships = [], []
    for component_number, component in enumerate(components):
        if len(component) <= 1:
            continue
        theta = coarse_theta[component]
        if component_number == 0:
            centres = np.asarray(RECIPE['major_component_lobe_centres'])
            u = (theta[:, None]-centres[None, :])/RECIPE['major_component_kernel_halfwidth']
            partition = np.maximum(0., 1.-u*u)**3
            partition[np.abs(u) >= 1.] = 0.
            partition_sum = partition.sum(axis=1)
            if np.any(partition_sum <= 0.):
                raise ValueError('Fixed compact angular kernels leave an actual main-component control uncovered.')
            partition /= partition_sum[:, None]
        else:
            centres, partition = np.array([float(np.mean(theta))]), np.ones((len(theta), 1))
        for lobe_number, centre in enumerate(centres):
            membership = np.zeros(nc, float)
            membership[component] = promoted[component]*partition[:, lobe_number]
            # Reflect scalar membership via actual source IDs, not chart matching.
            membership = np.maximum.reduce([membership, membership[coarse_pairs['X']],
                membership[coarse_pairs['Y']], membership[coarse_pairs['X'][coarse_pairs['Y']]]])
            guide = component[partition[:, lobe_number] >= .20]
            if len(guide) < 3:
                raise ValueError('Fixed lobe has insufficient actual source guide controls.')
            uv = np.column_stack([coarse_chart[guide, 0], coarse_theta[guide]])
            low, high, bounds_record = _bounds(uv)
            coarse_memberships.append(membership)
            lobe_specs.append(dict(component=component_number, lobe=lobe_number, centre=float(centre),
                component_ids=component, guide_ids=guide, low=low, high=high, bounds=bounds_record))
    coarse_memberships = np.stack(coarse_memberships)
    if np.any(coarse_memberships.sum(axis=0) > 1.+1e-12):
        raise ValueError('Component/lobe partition exceeds authorized promoted scalar mask.')

    delta = np.zeros_like(xyz, dtype=float)
    full_mask = np.zeros(nv, float)
    canonical_full = (xyz[:, 0] < 0.) & (xyz[:, 1] > 0.)
    lobe_records = []
    for membership, spec in zip(coarse_memberships, lobe_specs):
        lifted = _lift(membership, maps)
        selected_ids = np.flatnonzero((lifted > 0.) & canonical_full)
        t = chart[selected_ids, 0]
        theta = np.arctan2(np.abs(chart[selected_ids, 2]), np.abs(chart[selected_ids, 1]))
        if t.min() < .55 or t.max() > .700 or theta.min() < .20 or theta.max() > 1.52:
            raise ValueError('Lifted lobe escaped verified local WALL chart context.')
        low, high = spec['low'], spec['high']
        t0, t1 = low(theta), high(theta)
        if np.any(t1 <= t0):
            raise ValueError('Actual lobe guide interval reversed.')
        theta_nodes = np.linspace(float(theta.min()), float(theta.max()), 49)
        amplitude, calibration = _calibrate(sample, theta_nodes, low, high, t, theta,
            np.linalg.norm(xyz[selected_ids, :2], axis=1), height)
        controls, normal, tangent, _ = _controls(sample, theta, t0, t1, amplitude(theta))
        s = np.clip((t-t0)/(t1-t0), 0., 1.)
        target = _bezier(controls, s)
        endpoint_weight = _quintic(np.minimum((t-t0)/.004, (t1-t)/.004))
        weight = lifted[selected_ids]*endpoint_weight
        local_delta = (target-xyz[selected_ids])*weight[:, None]
        delta[selected_ids] += local_delta
        full_mask[selected_ids] += weight
        lobe_records.append(dict(component_number=spec['component'], lobe_number=spec['lobe'],
            angular_centre=spec['centre'], canonical_component_control_count=len(spec['component_ids']),
            canonical_guide_control_count=len(spec['guide_ids']), canonical_lifted_control_count=len(selected_ids),
            canonical_blended_control_count=int(np.count_nonzero(weight)),
            source_canonical_component_ids=spec['component_ids'].tolist(),
            source_canonical_guide_ids=spec['guide_ids'].tolist(),
            source_component_ids_sha256=_hash(spec['component_ids']), source_guide_ids_sha256=_hash(spec['guide_ids']),
            coarse_membership_sha256=_hash(membership), lifted_membership_sha256=_hash(lifted),
            endpoint_feather_sha256=_hash(endpoint_weight), target_xyz_sha256=_hash(target),
            guide_bounds=spec['bounds'], radial_calibration=calibration,
            pre_cap_weighted_target_delta_norm=_summary(np.linalg.norm(local_delta, axis=1))))
    if not np.any(full_mask > 0.):
        raise ValueError('Fixed reconstruction has no nonzero authorized blend support.')
    canonical_ids = np.flatnonzero(full_mask > 0.)
    for pair, signs in ((pairs['X'], [-1., 1., 1.]), (pairs['Y'], [1., -1., 1.]),
                        (pairs['X'][pairs['Y']], [-1., -1., 1.])):
        target_ids = pair[canonical_ids]
        delta[target_ids] = delta[canonical_ids]*np.asarray(signs)
        full_mask[target_ids] = full_mask[canonical_ids]
    delta, representative, fixed_x, fixed_y = field._transport(delta, ids, pairs)
    full_mask = full_mask[representative].copy()
    if np.any(full_mask > 1.+1e-12):
        raise ValueError('Actual final local blend partition exceeds one.')
    norm_before_cap = np.linalg.norm(delta, axis=1)
    bound = .025*height
    scale = np.ones(nv, float)
    selected = norm_before_cap > 0.
    scale[selected] = bound*np.tanh(norm_before_cap[selected]/bound)/norm_before_cap[selected]
    delta *= scale[:, None]
    delta[full_mask == 0.] = 0.
    output_xyz = xyz+delta
    output_xyz[full_mask == 0.] = xyz[full_mask == 0.]
    if not np.isfinite(output_xyz).all() or not np.array_equal(output_xyz[full_mask == 0.], xyz[full_mask == 0.]):
        raise ValueError('Nonfinite reconstruction or changed mask-zero source.')
    actual_norm = np.linalg.norm(output_xyz-xyz, axis=1)
    if not np.any(actual_norm > 0.):
        raise ValueError('Actual local reconstruction made no nonzero source change.')
    if actual_norm.max() > bound*(1.+1e-12):
        raise ValueError('Actual local displacement exceeded authored bound.')
    selected = full_mask > 0.
    source_radial = np.linalg.norm(xyz[selected, :2], axis=1)
    output_radial = np.linalg.norm(output_xyz[selected, :2], axis=1)
    out = ArrayMesh(output_xyz, faces.copy(), np.asarray(mesh.classes).copy(),
        np.asarray(mesh.rest).copy(), np.asarray(mesh.anchors).copy(), 7)
    out.surface = 'mean'
    metadata = dict(experiment='ROLLED_END_REBUILD_BODY_CONTEXT_V2_20261014', recipe=deepcopy(RECIPE),
        source_generation=7, output_generation=7, coarse_level=7-len(maps),
        coarse_vertex_count=nc, coarse_quad_count=len(coarse_faces), actual_source_control_count=nv,
        actual_source_quad_count=len(faces), physical_height=height,
        selected_canonical_component_sizes=component_sizes, rebuilt_component_count=4,
        ignored_tiny_canonical_component_count=2, actual_lobe_count=len(lobe_records),
        local_source_interpolation=context_record, lobe_records=lobe_records, actual_lift_maps=map_records,
        selected_coarse_control_count=int(np.count_nonzero(coarse_memberships.sum(axis=0))),
        selected_full_control_count=int(np.count_nonzero(selected)),
        changed_actual_control_count=int(np.count_nonzero(actual_norm)),
        maximum_actual_displacement=float(actual_norm.max()), displacement_bound=bound,
        selected_displacement_norm=_summary(actual_norm[selected]),
        pre_cap_displacement_norm=_summary(norm_before_cap[selected]),
        cap_scale=_summary(scale[selected]), cap_scale_below_099_count=int(np.count_nonzero(scale[selected] < .99)),
        input_selected_radial_extrema=_summary(source_radial), output_selected_radial_extrema=_summary(output_radial),
        selected_radial_change=_summary(output_radial-source_radial),
        mask_zero_source_coordinates_exact=True, faces_unchanged=True,
        classes_rest_anchors_unchanged=True, chart_unchanged=True,
        source_geometry_averaged=False, no_global_inverse_chart=True,
        added_CC_passes=0, target_neutral_CC_passes=0, added_topology_events=0,
        added_control_count=0, added_quad_count=0, added_mandelbulb_evaluations=0, normal_field_passes=0,
        input_xyz_sha256=_hash(xyz), output_xyz_sha256=_hash(output_xyz),
        input_faces_sha256=_hash(faces), output_faces_sha256=_hash(out.faces),
        supplied_coarse_mask_sha256=_hash(np.asarray(coarse_mask)),
        coarse_lobe_memberships_sha256=_hash(coarse_memberships),
        full_mask_sha256=_hash(full_mask), displacement_vector_sha256=_hash(delta),
        saved_displacement_scope='Authored final transported/capped vector; actual source+vector may retain subtraction rounding residuals.',
        source_pair_hashes={key: _hash(value) for key, value in pairs.items()},
        geometry_code_sha256=code_hashes(), fixed_x_vertex_count=int(fixed_x.sum()), fixed_y_vertex_count=int(fixed_y.sum()),
        symmetry_scope=RECIPE['reflection'], self_intersection='NOT_CERTIFIED_PROJECTED_GUIDE_CROSSINGS_RECORDED',
        G1_continuity='NOT_GUARANTEED', fabrication='NOT_CHECKED',
        radial_envelope_preservation='Measured source envelope calibrates unblended guide. Feathering, guide interpolation and displacement cap prevent an exact final radial-envelope guarantee.',
        visual_status='PENDING_ACTUAL_MATCHED_RENDER', interpretation=RECIPE['interpretation'])
    state = dict(displacement_vector=delta, full_mask=full_mask,
        coarse_mask=np.asarray(coarse_mask).copy(), coarse_lobe_memberships=coarse_memberships,
        source_body_vertex_mask=source_body_vertex_mask.copy(),
        mirror_x_vertex_pairs=pairs['X'], mirror_y_vertex_pairs=pairs['Y'])
    return out, metadata, state
