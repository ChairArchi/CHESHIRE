"""Constrained fairing plus neutral-CC target reconstruction of actual source G7.

The coarse controls are the OLD-V prefix of the current G7, not an earlier
saved geometry. A user-authorized feathered mask limits fairing; radial crest
anchors and radial attenuation protect protrusion. Actual saved V/E/F ID maps
lift the local blend mask. Three actual neutral-CC evaluations construct a
smooth target from the filtered current-G7 coarse prefix. The target replaces
fine residuals inside the blend region; it is not historical growth replay,
new output generations, collision repair, or a proof of tangent continuity.
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
from cheshire.reference_subdivision import ArrayMesh

_FIELD_PATH = HERE.parent/'whole_column_detail_20261013/whole_field.py'
_spec = importlib.util.spec_from_file_location('junction_frozen_source_id_transport', _FIELD_PATH)
field = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = field
_spec.loader.exec_module(field)


RECIPE = dict(
    schema='CHESHIRE_ORNAMENT_JUNCTION_NEUTRAL_TARGET_V2_20261014',
    source_generation=7, output_generation=7, intended_coarse_level=4,
    taubin_pairs=12, lambda_step=.50, mu_step=-.53,
    averaging='Arithmetic average of unique neighbors on actual preserved coarse quad edges.',
    substep='P <- P + coefficient*effective_coarse_mask*(neighbor_mean(P)-P); anchors and mask-zero controls remain exact at every substep.',
    coarse_geometry='Actual latest source G7.xyz[:coarse_vertex_count]; no earlier coarse-stage XYZ is substituted.',
    lift='At each actual saved stage linearly lift mask as old-V, endpoint mean, face mean. Reconstruct target XYZ with actual neutral Catmull-Clark stencils and verify exact saved child face order.',
    lift_scope='Linear V/E/F mask interpolation; actual neutral-CC smooth target construction from current-G7 coarse prefix. Not historical growth replay.',
    radial_component_gain=.35,
    radial_direction='Fixed actual input G7 XY radial direction, applied once to FINAL target-minus-source blended displacement.',
    radial_anchor_theta_bin_radians=.06, radial_anchor_z_bin_height_fraction=.025,
    radial_anchor_tolerance_height_fraction=.0005,
    radial_anchor_rule='Within selected coarse mask, group by floor(atan2(abs(Y),abs(X))/.06) and floor((Z-source_zmin)/(.025H)); retain radius >= bin maximum-.0005H. Union actual X/Y ID orbits.',
    fine_radial_anchor_tolerance_height_fraction=.00025,
    anchor_neighborhood_averages=2,
    anchor_neighborhood='Two actual quad-edge averages of binary movable weights, resetting all anchor weights to zero after each average; multiply the supplied lifted feather mask. Mask-zero source stays exact.',
    target_formula='target=neutral_CC^3(filtered_actual_G7_coarse_prefix); delta=(target-actual_G7)*blend_mask, then final radial attenuation, actual-ID reflection, smooth norm cap and exact anchor pins.',
    radial_anchor_scope='Fixed selected original coarse controls plus selected actual G7 fine radial crests. Both are fixed exactly in the final output.',
    maximum_displacement_height_fraction=.0075,
    displacement_cap='D <- D*(B*tanh(norm(D)/B)/norm(D)), B=.0075H; zero displacement remains zero.',
    reflection='Frozen whole_field._transport reflects minimum-ID representative delta through actual commuting source X/Y involutions; input geometry is not reconstructed.',
    mask_scope='Supplied selected WALL-born overlap-band feather mask, not a new root/end-cap semantic classifier.',
    added_CC_passes=0, added_topology_events=0, added_mandelbulb_evaluations=0,
    normal_field_passes=0, source_geometry_averaged=True,
    preservation='Exact faces/classes/rest/anchors/chart and source coordinates where full lifted mask is zero; exact original coarse and selected actual-G7 radial anchors.',
    smooth_target_CC_evaluations='Actual count of supplied coarse-to-source saved levels; output generation stays G7, added subdivision generations=0.',
    interpretation='Local geometry fairing to organize existing ornament junctions. No new ornament or detail, no guaranteed G1 continuity, no collision repair, and no automatic visual success.',
)


def _hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def code_hashes():
    paths = (Path(__file__).resolve(), _FIELD_PATH, REPO/'src/cheshire/reference_subdivision.py')
    return {p.relative_to(REPO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _faces(value, count, name):
    faces = np.asarray(value)
    if (faces.ndim != 2 or faces.shape[1] != 4 or not len(faces) or
            faces.dtype.kind not in 'iu' or faces.min() < 0 or faces.max() >= count):
        raise ValueError('Actual all-quad indices required: '+name)
    if any(np.any(faces[:, a] == faces[:, b]) for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))):
        raise ValueError('Repeated corners are not repaired: '+name)
    return faces


def _edges_from_faces(faces):
    pairs = np.stack([faces, np.roll(faces, -1, axis=1)], axis=-1).reshape(-1, 2)
    pairs.sort(axis=1)
    return np.unique(pairs, axis=0)


def _neighbor_laplacian(points, edges, degree):
    result = np.empty_like(points, dtype=float)
    a, b = edges[:, 0], edges[:, 1]
    for component in range(3):
        total = np.bincount(a, weights=points[b, component], minlength=len(points))
        total += np.bincount(b, weights=points[a, component], minlength=len(points))
        result[:, component] = total/degree-points[:, component]
    return result


def _lift(value, edges, faces):
    return np.concatenate([value, value[edges].mean(axis=1), value[faces].mean(axis=1)])


def _summary(values):
    values = np.asarray(values, float)
    if not len(values):
        return dict(count=0, minimum=None, maximum=None, quantiles=None)
    return dict(count=len(values), minimum=float(values.min()), maximum=float(values.max()),
                quantiles=np.quantile(values, [0., .5, .9, .99, 1.]).tolist())


def _radial_extrema(xyz, selection):
    radial = np.linalg.norm(xyz[:, :2], axis=1)
    return dict(global_radius=_summary(radial), selected_radius=_summary(radial[selection]))


def _anchors(points, mask, coarse_pairs, height, source_zmin, tolerance_fraction=None):
    if tolerance_fraction is None:
        tolerance_fraction = RECIPE['radial_anchor_tolerance_height_fraction']
    selected = np.flatnonzero(mask > 0.)
    if not len(selected):
        raise ValueError('Nonzero authorized coarse mask required.')
    radial = np.linalg.norm(points[:, :2], axis=1)
    theta = np.arctan2(np.abs(points[selected, 1]), np.abs(points[selected, 0]))
    theta_bin = np.floor(theta/RECIPE['radial_anchor_theta_bin_radians']).astype(np.int64)
    z_bin = np.floor((points[selected, 2]-source_zmin)/
                     (RECIPE['radial_anchor_z_bin_height_fraction']*height)).astype(np.int64)
    bins, inverse = np.unique(np.column_stack([theta_bin, z_bin]), axis=0, return_inverse=True)
    maxima = np.full(len(bins), -np.inf)
    np.maximum.at(maxima, inverse, radial[selected])
    fixed = np.zeros(len(points), bool)
    fixed[selected] = radial[selected] >= maxima[inverse]-tolerance_fraction*height
    raw_count = int(fixed.sum())
    fixed |= fixed[coarse_pairs['X']] | fixed[coarse_pairs['Y']]
    fixed |= fixed[coarse_pairs['X'][coarse_pairs['Y']]]
    if np.any(fixed & (mask == 0.)):
        raise ValueError('Actual radial-anchor orbit escaped authorized symmetric coarse mask.')
    return fixed, dict(selected_coarse_control_count=len(selected), occupied_radial_bins=len(bins),
        radial_anchor_raw_count=raw_count, radial_anchor_orbit_count=int(fixed.sum()),
        radial_anchor_fraction_of_selected=float(fixed.sum()/len(selected)),
        radial_anchor_tolerance=tolerance_fraction*height,
        theta_bin_width_radians=RECIPE['radial_anchor_theta_bin_radians'],
        axial_bin_width=RECIPE['radial_anchor_z_bin_height_fraction']*height)


def _neutral_cc_target(points, faces, edges, expected_child_faces):
    """Actual neutral CC stencils in saved V/E/F and reference child order."""
    nv, nf, ne = len(points), len(faces), len(edges)
    if np.any(edges[:, 0] >= edges[:, 1]):
        raise ValueError('Saved neutral-target edges must have ordered endpoints.')
    edge_keys = edges[:, 0]*nv+edges[:, 1]
    if np.any(edge_keys[1:] <= edge_keys[:-1]):
        raise ValueError('Saved neutral-target edge birth order must be lexicographic.')
    following = np.roll(faces, -1, axis=1)
    keys = np.minimum(faces, following)*nv+np.maximum(faces, following)
    face_edges = np.searchsorted(edge_keys, keys)
    if face_edges.max() >= ne or not np.array_equal(edge_keys[face_edges], keys):
        raise ValueError('Saved edge IDs do not associate to actual input quad edges.')
    del keys, following, edge_keys
    counts = np.bincount(face_edges.ravel(), minlength=ne)
    if np.any(counts != 2):
        raise ValueError('Neutral target requires actual closed two-face edges.')
    owners = np.repeat(np.arange(nf, dtype=np.int64), 4)
    first, second = np.full(ne, nf, np.int64), np.full(ne, -1, np.int64)
    np.minimum.at(first, face_edges.ravel(), owners)
    np.maximum.at(second, face_edges.ravel(), owners)
    if np.any(first == second):
        raise ValueError('Neutral-target edge has duplicated face owner.')
    face_points = np.zeros((nf, 3), float)
    for corner in range(4):
        face_points += points[faces[:, corner]]
    face_points *= .25
    edge_points = (points[edges[:, 0]]+points[edges[:, 1]]+face_points[first]+face_points[second])*.25
    degree = np.bincount(edges.ravel(), minlength=nv)
    face_degree = np.bincount(faces.ravel(), minlength=nv)
    if np.any(degree == 0) or np.any(face_degree == 0):
        raise ValueError('Neutral target does not repair orphan controls.')
    midpoint = (points[edges[:, 0]]+points[edges[:, 1]])*.5
    vertex_points = np.empty_like(points, dtype=float)
    for component in range(3):
        fbar = np.bincount(faces.ravel(), weights=np.repeat(face_points[:, component], 4), minlength=nv)/face_degree
        rtotal = np.bincount(edges[:, 0], weights=midpoint[:, component], minlength=nv)
        rtotal += np.bincount(edges[:, 1], weights=midpoint[:, component], minlength=nv)
        vertex_points[:, component] = (fbar+2.*rtotal/degree+(degree-3)*points[:, component])/degree
    if np.asarray(expected_child_faces).shape != (4*nf, 4):
        raise ValueError('Neutral-target child face count does not match actual saved next level.')
    for start in range(0, nf, 65536):
        stop = min(start+65536, nf)
        fe = face_edges[start:stop]
        centre_ids = np.broadcast_to(np.arange(start, stop)[:, None]+nv+ne, fe.shape)
        child = np.stack([np.roll(fe, 1, axis=1)+nv, faces[start:stop], fe+nv, centre_ids], axis=-1).reshape(-1, 4)
        if not np.array_equal(child, expected_child_faces[4*start:4*stop]):
            raise ValueError('Neutral-target reference child ID/order differs from actual saved topology.')
    target = np.concatenate([vertex_points, edge_points, face_points])
    if not np.isfinite(target).all():
        raise ValueError('Nonfinite neutral-target output.')
    return target, dict(input_control_count=nv, input_quad_count=nf, actual_edge_count=ne,
        output_control_count=len(target), actual_closed_two_face_edges=True,
        exact_saved_child_face_order=True, output_xyz_sha256=_hash(target),
        stencil='F=mean quad; E=(endpoints+two adjacent F)/4; V=(mean incident F+2*mean original edge midpoints+(degree-3)*P)/degree',
        interpretation='Actual neutral CC target evaluation, not historical weighted-growth replay.')


def _anchor_neighborhood_weight(faces, fixed, count):
    """Two graph averages of movable weights, with exact anchor resets."""
    incident = np.bincount(faces.ravel(), minlength=count)
    if np.any(incident == 0):
        raise ValueError('Anchor neighborhood does not repair orphan controls.')
    deficit = fixed.astype(float)
    for _ in range(RECIPE['anchor_neighborhood_averages']):
        active = deficit > 0.
        touched = faces[np.any(active[faces], axis=1)]
        weights = deficit[np.roll(touched, 1, axis=1)]+deficit[np.roll(touched, -1, axis=1)]
        deficit = np.bincount(touched.ravel(), weights=weights.ravel(), minlength=count)/(2.*incident)
        deficit[fixed] = 1.
    movable = np.clip(1.-deficit, 0., 1.)
    movable[fixed] = 0.
    return movable


def build(mesh, chart, vertex_pairs, coarse_faces, coarse_vertex_count, coarse_mask, lift_maps, height):
    """Return (actual G7 output mesh, JSON-safe metadata, NPZ-safe evidence).

    ``lift_maps`` is a stage-ordered list of dictionaries containing actual
    ``input_edges`` (E,2) and ``input_faces`` (F,4), in their SAVED birth order.
    The exact old-V/edge/face prefix sizes are checked against actual G7.
    No input array is modified and this function performs no file writes.
    """
    xyz, faces = np.asarray(mesh.xyz), np.asarray(mesh.faces)
    nv = len(xyz)
    if (mesh.generation != 7 or getattr(mesh, 'surface', None) != 'mean' or
            xyz.shape != (nv, 3) or not nv or not np.isfinite(xyz).all()):
        raise ValueError('Actual finite mean-native G7 source required.')
    faces = _faces(faces, nv, 'source G7')
    if np.asarray(chart).shape != xyz.shape or not np.isfinite(chart).all():
        raise ValueError('Actual unchanged source chart association required.')
    if (np.asarray(mesh.classes).shape != (nv,) or np.asarray(mesh.rest).shape != xyz.shape or
            np.asarray(mesh.anchors).shape[0] != len(faces)):
        raise ValueError('Actual source classes/rest/anchors required.')
    height = float(height)
    if not np.isfinite(height) or height <= 0.:
        raise ValueError('Positive inherited physical height required.')
    nc = int(coarse_vertex_count)
    if nc != coarse_vertex_count or not 0 < nc < nv:
        raise ValueError('Actual retained coarse OLD-V prefix count required.')
    coarse_faces = _faces(coarse_faces, nc, 'preserved coarse faces')
    mask = np.asarray(coarse_mask, float).copy()
    if (mask.shape != (nc,) or not np.isfinite(mask).all() or np.any(mask < 0.) or np.any(mask > 1.)):
        raise ValueError('Finite authorized coarse feather mask in [0,1] required.')
    ids, pairs = field._mirror_pairs(vertex_pairs, nv)
    coarse_pairs = {axis: pairs[axis][:nc] for axis in ('X', 'Y')}
    for axis, pair in coarse_pairs.items():
        if pair.max() >= nc or not np.array_equal(pair[pair], np.arange(nc)):
            raise ValueError('Actual source mirror does not retain coarse prefix: '+axis)
        if not np.allclose(mask, mask[pair], rtol=0., atol=1e-12):
            raise ValueError('Supplied coarse mask must preserve source-ID reflection: '+axis)
    representative_coarse = np.minimum.reduce([np.arange(nc), coarse_pairs['X'], coarse_pairs['Y'],
                                               coarse_pairs['X'][coarse_pairs['Y']]])
    mask = mask[representative_coarse].copy()

    maps, map_records, running_count = [], [], nc
    if not isinstance(lift_maps, (tuple, list)) or not len(lift_maps):
        raise ValueError('Stage-ordered actual saved V/E/F maps required.')
    for stage, mapping in enumerate(lift_maps):
        edges = np.asarray(mapping['input_edges'])
        stage_faces = _faces(mapping['input_faces'], running_count, 'lift stage input faces')
        if (edges.ndim != 2 or edges.shape[1] != 2 or not len(edges) or edges.dtype.kind not in 'iu' or
                edges.min() < 0 or edges.max() >= running_count or np.any(edges[:, 0] == edges[:, 1])):
            raise ValueError('Actual edge birth order required at lift stage '+str(stage))
        if stage == 0 and not np.array_equal(stage_faces, coarse_faces):
            raise ValueError('First lift input faces do not match actual preserved coarse topology.')
        result_count = running_count+len(edges)+len(stage_faces)
        maps.append((edges, stage_faces))
        map_records.append(dict(stage=stage, input_vertex_count=running_count,
            edge_birth_count=len(edges), face_birth_count=len(stage_faces), output_vertex_count=result_count,
            input_edges_sha256=_hash(edges), input_faces_sha256=_hash(stage_faces)))
        running_count = result_count
    if running_count != nv:
        raise ValueError('Actual V/E/F lift counts do not terminate at source G7.')

    source_coarse = xyz[:nc].copy()
    edge_graph = _edges_from_faces(coarse_faces)
    degree = np.bincount(edge_graph.ravel(), minlength=nc)
    if np.any(degree == 0):
        raise ValueError('Coarse topology has orphan controls; no repair.')
    source_zmin = float(xyz[:, 2].min())
    anchors, anchor_stats = _anchors(source_coarse, mask, coarse_pairs, height, source_zmin)
    effective_mask = mask.copy()
    effective_mask[anchors] = 0.
    if not np.any(effective_mask > 0.):
        raise ValueError('Radial anchors leave no authorized movable coarse controls.')
    current = source_coarse.copy()
    curvature_before = np.linalg.norm(_neighbor_laplacian(source_coarse, edge_graph, degree), axis=1)
    for _ in range(RECIPE['taubin_pairs']):
        for coefficient in (RECIPE['lambda_step'], RECIPE['mu_step']):
            current += coefficient*effective_mask[:, None]*_neighbor_laplacian(current, edge_graph, degree)
            current[effective_mask == 0.] = source_coarse[effective_mask == 0.]
    coarse_delta = current-source_coarse
    coarse_delta[effective_mask == 0.] = 0.
    coarse_delta, _, _, _ = field._transport(coarse_delta, np.arange(nc), coarse_pairs)
    coarse_delta[effective_mask == 0.] = 0.
    target = source_coarse+coarse_delta
    full_mask = mask
    target_records = []
    for stage, (edges, stage_faces) in enumerate(maps):
        expected_faces = maps[stage+1][1] if stage+1 < len(maps) else faces
        target, target_record = _neutral_cc_target(target, stage_faces, edges, expected_faces)
        target_record['stage'] = stage
        target_records.append(target_record)
        full_mask = _lift(full_mask, edges, stage_faces)
    for axis in ('X', 'Y'):
        if not np.allclose(full_mask, full_mask[pairs[axis]], rtol=0., atol=1e-12):
            raise ValueError('Saved V/E/F maps did not preserve source-ID mask reflection: '+axis)
    representative = np.minimum.reduce([ids, pairs['X'], pairs['Y'], pairs['X'][pairs['Y']]])
    full_mask = full_mask[representative].copy()
    fine_anchors, fine_anchor_stats = _anchors(xyz, full_mask, pairs, height, source_zmin,
        RECIPE['fine_radial_anchor_tolerance_height_fraction'])
    all_anchors = fine_anchors.copy()
    all_anchors[:nc] |= anchors
    anchor_weight = _anchor_neighborhood_weight(faces, all_anchors, nv)
    anchor_weight = anchor_weight[representative].copy()
    blend_mask = full_mask*anchor_weight
    blend_mask[all_anchors] = 0.
    delta = (target-xyz)*blend_mask[:, None]
    target_xyz_sha256 = _hash(target)
    del target
    for start in range(0, nv, 131072):
        stop = min(start+131072, nv)
        xy = xyz[start:stop, :2]
        radius_squared = np.sum(xy*xy, axis=1)
        radial_coefficient = np.divide(np.sum(delta[start:stop, :2]*xy, axis=1),
            radius_squared, out=np.zeros(stop-start), where=radius_squared > 0.)
        delta[start:stop, :2] -= (1.-RECIPE['radial_component_gain'])*radial_coefficient[:, None]*xy
    delta, representative, fixed_x, fixed_y = field._transport(delta, ids, pairs)
    displacement_bound = RECIPE['maximum_displacement_height_fraction']*height
    norm_before_cap = np.linalg.norm(delta, axis=1)
    scale = np.ones(nv, float)
    active = norm_before_cap > 0.
    scale[active] = displacement_bound*np.tanh(norm_before_cap[active]/displacement_bound)/norm_before_cap[active]
    delta *= scale[:, None]
    delta[full_mask == 0.] = 0.
    delta[all_anchors] = 0.
    output_xyz = xyz+delta
    output_xyz[full_mask == 0.] = xyz[full_mask == 0.]
    output_xyz[all_anchors] = xyz[all_anchors]
    if not np.isfinite(output_xyz).all():
        raise ValueError('Nonfinite constrained fairing output; no fallback.')
    if not np.array_equal(output_xyz[full_mask == 0.], xyz[full_mask == 0.]):
        raise ValueError('Mask-zero actual source geometry changed.')
    if not np.array_equal(output_xyz[all_anchors], xyz[all_anchors]):
        raise ValueError('Actual source coarse/fine radial anchors moved.')
    actual_delta = output_xyz-xyz
    actual_norm = np.linalg.norm(actual_delta, axis=1)
    if actual_norm.max() > displacement_bound*(1.+1e-12):
        raise ValueError('Actual source displacement exceeds authored bound.')
    curvature_after = np.linalg.norm(_neighbor_laplacian(output_xyz[:nc], edge_graph, degree), axis=1)
    out = ArrayMesh(output_xyz, faces.copy(), np.asarray(mesh.classes).copy(),
        np.asarray(mesh.rest).copy(), np.asarray(mesh.anchors).copy(), 7)
    out.surface = 'mean'
    selected_full = full_mask > 0.
    selected_coarse = mask > 0.
    metadata = dict(experiment='ORNAMENT_JUNCTION_FINISH_NEUTRAL_TARGET_V2_20261014', recipe=deepcopy(RECIPE),
        source_generation=7, output_generation=7, coarse_level=7-len(maps),
        coarse_vertex_count=nc, coarse_quad_count=len(coarse_faces), coarse_unique_edge_count=len(edge_graph),
        actual_source_control_count=nv, actual_source_quad_count=len(faces), physical_height=height,
        mask_definition_scope=RECIPE['mask_scope'], mask_zero_source_coordinates_exact=True,
        original_coarse_radial_anchors_exact=True, anchor_statistics=anchor_stats,
        actual_G7_fine_radial_anchors_exact=True, fine_anchor_statistics=fine_anchor_stats,
        all_radial_anchor_count=int(all_anchors.sum()),
        anchor_neighborhood_average_count=RECIPE['anchor_neighborhood_averages'],
        anchor_neighborhood_weight_sha256=_hash(anchor_weight),
        blend_mask_sha256=_hash(blend_mask),
        taubin_pairs=RECIPE['taubin_pairs'], taubin_substeps=2*RECIPE['taubin_pairs'],
        movable_coarse_control_count=int(np.count_nonzero(effective_mask)),
        selected_coarse_control_count=int(np.count_nonzero(selected_coarse)),
        selected_full_control_count=int(np.count_nonzero(selected_full)),
        changed_actual_control_count=int(np.count_nonzero(actual_norm)),
        maximum_actual_displacement=float(actual_norm.max()), displacement_bound=displacement_bound,
        selected_displacement_norm=_summary(actual_norm[selected_full]),
        lifted_displacement_norm_before_cap=_summary(norm_before_cap[selected_full]),
        coarse_laplacian_norm_before=_summary(curvature_before[selected_coarse]),
        coarse_laplacian_norm_after=_summary(curvature_after[selected_coarse]),
        laplacian_metric_scope='Uniform coarse-edge Laplacian magnitude proxy on actual source/output coarse OLD-V prefix; not principal curvature or a continuity guarantee.',
        input_radial_extrema=_radial_extrema(xyz, selected_full),
        output_radial_extrema=_radial_extrema(output_xyz, selected_full),
        actual_lift_maps=map_records, smooth_target_CC_records=target_records,
        smooth_target_CC_evaluations=len(maps), target_neutral_CC_passes=len(maps),
        added_subdivision_generations=0, target_is_historical_growth_replay=False,
        target_final_xyz_sha256=target_xyz_sha256,
        lift_is_exact_catmull_clark_propagation=False,
        neutral_target_stencil_scope='Actual neutral Catmull-Clark target, verified saved child face/vertex ordering; not propagation of original historical weighted growth.',
        input_xyz_sha256=_hash(xyz), output_xyz_sha256=_hash(output_xyz),
        input_faces_sha256=_hash(faces), output_faces_sha256=_hash(out.faces),
        supplied_coarse_mask_sha256=_hash(np.asarray(coarse_mask)),
        effective_reflected_coarse_mask_sha256=_hash(mask), full_mask_sha256=_hash(full_mask),
        coarse_anchor_mask_sha256=_hash(anchors), fine_anchor_mask_sha256=_hash(fine_anchors),
        all_anchor_mask_sha256=_hash(all_anchors), displacement_vector_sha256=_hash(delta),
        saved_displacement_scope='Authored transported capped vector; output=actual source+vector with exact zero-mask/anchor assignment. Actual subtraction may retain floating-point rounding residuals.',
        faces_unchanged=True, classes_rest_anchors_unchanged=True, chart_unchanged=True,
        source_geometry_averaged=True, geometry_averaging_scope='Authorized coarse fairing; actual neutral-CC target reconstruction followed by a local feathered blend that suppresses preexisting fine residuals inside the selected band.',
        added_CC_passes=0, added_topology_events=0, added_control_count=0, added_quad_count=0,
        added_mandelbulb_evaluations=0, normal_field_passes=0,
        fixed_x_vertex_count=int(fixed_x.sum()), fixed_y_vertex_count=int(fixed_y.sum()),
        source_pair_hashes={axis: _hash(pair) for axis, pair in pairs.items()},
        geometry_code_sha256=code_hashes(), symmetry_scope=RECIPE['reflection'],
        self_intersection='NOT_CHECKED', G1_continuity='NOT_GUARANTEED', fabrication='NOT_CHECKED',
        visual_status='PENDING_MATCHED_RENDER', interpretation=RECIPE['interpretation'])
    state = dict(displacement_vector=delta, full_mask=full_mask, blend_mask=blend_mask,
        anchor_neighborhood_weight=anchor_weight, fine_radial_anchor_mask=fine_anchors,
        all_radial_anchor_mask=all_anchors, coarse_mask=mask,
        effective_coarse_mask=effective_mask, coarse_radial_anchor_mask=anchors,
        coarse_displacement_vector=coarse_delta, mirror_x_vertex_pairs=pairs['X'],
        mirror_y_vertex_pairs=pairs['Y'])
    return out, metadata, state
