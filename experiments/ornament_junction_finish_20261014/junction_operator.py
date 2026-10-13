"""One constrained multiresolution fairing pass on actual source G7 geometry.

The coarse controls are the OLD-V prefix of the current G7, not an earlier
saved geometry. A user-authorized feathered mask limits fairing; radial crest
anchors and radial attenuation protect protrusion. Actual saved V/E/F ID maps
linearly lift the displacement. This is not an exact Catmull-Clark geometry
update, new subdivision, collision repair, or a proof of tangent continuity.
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
    schema='CHESHIRE_ORNAMENT_JUNCTION_CONSTRAINED_FAIRING_20261014',
    source_generation=7, output_generation=7, intended_coarse_level=4,
    taubin_pairs=12, lambda_step=.50, mu_step=-.53,
    averaging='Arithmetic average of unique neighbors on actual preserved coarse quad edges.',
    substep='P <- P + coefficient*effective_coarse_mask*(neighbor_mean(P)-P); anchors and mask-zero controls remain exact at every substep.',
    coarse_geometry='Actual latest source G7.xyz[:coarse_vertex_count]; no earlier coarse-stage XYZ is substituted.',
    lift='At each actual saved stage concatenate(old-V delta, mean endpoint delta per input_edges, mean corner delta per input_faces). Same rule lifts mask.',
    lift_scope='Linear ID-associated V/E/F displacement interpolation, not exact Catmull-Clark propagation or regeneration.',
    radial_component_gain=.35,
    radial_direction='Fixed input XY radial unit vector, applied once to accumulated coarse displacement before lifting.',
    radial_anchor_theta_bin_radians=.06, radial_anchor_z_bin_height_fraction=.025,
    radial_anchor_tolerance_height_fraction=.0005,
    radial_anchor_rule='Within selected coarse mask, group by floor(atan2(abs(Y),abs(X))/.06) and floor((Z-source_zmin)/(.025H)); retain radius >= bin maximum-.0005H. Union actual X/Y ID orbits.',
    radial_anchor_scope='Fixed selected original coarse controls only. Interpolated newly born controls can still move.',
    maximum_displacement_height_fraction=.0075,
    displacement_cap='D <- D*(B*tanh(norm(D)/B)/norm(D)), B=.0075H; zero displacement remains zero.',
    reflection='Frozen whole_field._transport reflects minimum-ID representative delta through actual commuting source X/Y involutions; input geometry is not reconstructed.',
    mask_scope='Supplied selected WALL-born overlap-band feather mask, not a new root/end-cap semantic classifier.',
    added_CC_passes=0, added_topology_events=0, added_mandelbulb_evaluations=0,
    normal_field_passes=0, source_geometry_averaged=True,
    preservation='Exact faces/classes/rest/anchors/chart and source coordinates where full lifted mask is zero; exact original coarse radial anchors.',
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


def _anchors(points, mask, coarse_pairs, height, source_zmin):
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
    fixed[selected] = radial[selected] >= maxima[inverse]-RECIPE['radial_anchor_tolerance_height_fraction']*height
    raw_count = int(fixed.sum())
    fixed |= fixed[coarse_pairs['X']] | fixed[coarse_pairs['Y']]
    fixed |= fixed[coarse_pairs['X'][coarse_pairs['Y']]]
    if np.any(fixed & (mask == 0.)):
        raise ValueError('Actual radial-anchor orbit escaped authorized symmetric coarse mask.')
    return fixed, dict(selected_coarse_control_count=len(selected), occupied_radial_bins=len(bins),
        radial_anchor_raw_count=raw_count, radial_anchor_orbit_count=int(fixed.sum()),
        radial_anchor_fraction_of_selected=float(fixed.sum()/len(selected)),
        radial_anchor_tolerance=RECIPE['radial_anchor_tolerance_height_fraction']*height,
        theta_bin_width_radians=RECIPE['radial_anchor_theta_bin_radians'],
        axial_bin_width=RECIPE['radial_anchor_z_bin_height_fraction']*height)


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
    radial = np.linalg.norm(source_coarse[:, :2], axis=1)
    radial_direction = np.zeros_like(source_coarse)
    np.divide(source_coarse[:, :2], radial[:, None], out=radial_direction[:, :2], where=radial[:, None] > 0.)
    radial_delta = np.sum(coarse_delta*radial_direction, axis=1)
    coarse_delta -= (1.-RECIPE['radial_component_gain'])*radial_delta[:, None]*radial_direction
    coarse_delta[effective_mask == 0.] = 0.
    coarse_delta, _, _, _ = field._transport(coarse_delta, np.arange(nc), coarse_pairs)
    coarse_delta[effective_mask == 0.] = 0.

    delta, full_mask = coarse_delta, mask
    for edges, stage_faces in maps:
        delta = _lift(delta, edges, stage_faces)
        full_mask = _lift(full_mask, edges, stage_faces)
    for axis in ('X', 'Y'):
        if not np.allclose(full_mask, full_mask[pairs[axis]], rtol=0., atol=1e-12):
            raise ValueError('Saved V/E/F maps did not preserve source-ID mask reflection: '+axis)
    delta, representative, fixed_x, fixed_y = field._transport(delta, ids, pairs)
    full_mask = full_mask[representative].copy()
    displacement_bound = RECIPE['maximum_displacement_height_fraction']*height
    norm_before_cap = np.linalg.norm(delta, axis=1)
    scale = np.ones(nv, float)
    active = norm_before_cap > 0.
    scale[active] = displacement_bound*np.tanh(norm_before_cap[active]/displacement_bound)/norm_before_cap[active]
    delta *= scale[:, None]
    delta[full_mask == 0.] = 0.
    delta[:nc][anchors] = 0.
    output_xyz = xyz+delta
    output_xyz[full_mask == 0.] = xyz[full_mask == 0.]
    output_xyz[:nc][anchors] = xyz[:nc][anchors]
    if not np.isfinite(output_xyz).all():
        raise ValueError('Nonfinite constrained fairing output; no fallback.')
    if not np.array_equal(output_xyz[full_mask == 0.], xyz[full_mask == 0.]):
        raise ValueError('Mask-zero actual source geometry changed.')
    if not np.array_equal(output_xyz[:nc][anchors], xyz[:nc][anchors]):
        raise ValueError('Original coarse radial anchors moved.')
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
    metadata = dict(experiment='ORNAMENT_JUNCTION_FINISH_20261014', recipe=deepcopy(RECIPE),
        source_generation=7, output_generation=7, coarse_level=7-len(maps),
        coarse_vertex_count=nc, coarse_quad_count=len(coarse_faces), coarse_unique_edge_count=len(edge_graph),
        actual_source_control_count=nv, actual_source_quad_count=len(faces), physical_height=height,
        mask_definition_scope=RECIPE['mask_scope'], mask_zero_source_coordinates_exact=True,
        original_coarse_radial_anchors_exact=True, anchor_statistics=anchor_stats,
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
        actual_lift_maps=map_records, lift_is_exact_catmull_clark_propagation=False,
        input_xyz_sha256=_hash(xyz), output_xyz_sha256=_hash(output_xyz),
        input_faces_sha256=_hash(faces), output_faces_sha256=_hash(out.faces),
        supplied_coarse_mask_sha256=_hash(np.asarray(coarse_mask)),
        effective_reflected_coarse_mask_sha256=_hash(mask), full_mask_sha256=_hash(full_mask),
        coarse_anchor_mask_sha256=_hash(anchors), displacement_vector_sha256=_hash(delta),
        saved_displacement_scope='Authored transported capped vector; output=actual source+vector with exact zero-mask/anchor assignment. Actual subtraction may retain floating-point rounding residuals.',
        faces_unchanged=True, classes_rest_anchors_unchanged=True, chart_unchanged=True,
        source_geometry_averaged=True, geometry_averaging_scope='Authorized coarse mask only, then actual ID-associated displacement lifting; no full-body smoothing.',
        added_CC_passes=0, added_topology_events=0, added_control_count=0, added_quad_count=0,
        added_mandelbulb_evaluations=0, normal_field_passes=0,
        fixed_x_vertex_count=int(fixed_x.sum()), fixed_y_vertex_count=int(fixed_y.sum()),
        source_pair_hashes={axis: _hash(pair) for axis, pair in pairs.items()},
        geometry_code_sha256=code_hashes(), symmetry_scope=RECIPE['reflection'],
        self_intersection='NOT_CHECKED', G1_continuity='NOT_GUARANTEED', fabrication='NOT_CHECKED',
        visual_status='PENDING_MATCHED_RENDER', interpretation=RECIPE['interpretation'])
    state = dict(displacement_vector=delta, full_mask=full_mask, coarse_mask=mask,
        effective_coarse_mask=effective_mask, coarse_radial_anchor_mask=anchors,
        coarse_displacement_vector=coarse_delta, mirror_x_vertex_pairs=pairs['X'],
        mirror_y_vertex_pairs=pairs['Y'])
    return out, metadata, state
