"""Read-only source-connected local guides for two fitted ornament tests.

The guide is a path of existing G7 control edges inside the previously marked
selection. It is not presented as an automatically detected fold crest.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree


HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/rim_ornament_adaptation_20261014/trial01')
SOURCE = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07')
SELECTION = Path('E:/CHESHIRE_DATA/experiments/volume_junction_target_20261014/trial01')
COARSE = Path('E:/CHESHIRE_DATA/experiments/sidewall_fan_growth_20261013/trial01/SIDEWALL_FAN/SPAN/G04/control_quad.npz')
PRIOR = Path('E:/CHESHIRE_DATA/experiments/local_ornament_comparison_20261014/trial01/PLACEMENT.json')
EXPECTED = {
    'generation.json': 'c7452dc63998c61783215f0bb23434ea5e9b223d89fcd836d1a4081907ab2cf5',
    'control_quad.npz': '0d966671a028cd56f49d0c5d1e626207652e789d281a9fa69475c3492f95fdc6',
    'geometry.npz': '98a88c6727045e0a5aad67df6cd6295de6c14655a78ac0ca95812a5f37841e91',
}
SELECTION_SHA = '7bbfb7cdb50b3fad320451dc096b23f8f662c7a09a425324949cba39396584ab'
NORMAL_SHA = 'e5a80eee35ace9fca07029c0e2e249f3571133e639b01d7cd38fe5aa038208f2'
SEEDS = (7272, 8893, 12781, 43114, 93144, 92393)
SIGNS = ((1, 1, 1), (-1, 1, 1), (1, -1, 1), (-1, -1, 1))
HEIGHT = 9.735842284057451
CAMERA_POSITION = np.array([-18., 28., 12.])
CAMERA_TARGET = np.array([-.6, .72, 6.6])


def digest(path):
    result = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def array_hash(array):
    return hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast('B')).hexdigest()


def unit(vector):
    vector = np.asarray(vector, np.float64)
    length = np.linalg.norm(vector)
    if length < 1e-12:
        raise ValueError('Degenerate local source direction.')
    return vector / length


def components(coarse_xyz, chart, mask, faces):
    selected = np.flatnonzero((mask > 0) & (coarse_xyz[:, 0] < 0) & (coarse_xyz[:, 1] > 0))
    lookup = np.full(len(mask), -1, np.int32)
    lookup[selected] = np.arange(len(selected))
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 3]], faces[:, [3, 0]]])
    edges = lookup[edges]
    edges = edges[(edges >= 0).all(axis=1)]
    graph = coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(len(selected), len(selected)))
    count, labels = connected_components(graph, directed=False)
    found = sorted([selected[labels == k] for k in range(count)], key=len, reverse=True)
    if [len(group) for group in found] != [406, 54, 19, 16, 1, 1]:
        raise ValueError('The original marked coarse components changed.')
    groups = []
    for component_index, component in enumerate(found[:4]):
        theta = np.arctan2(abs(chart[component, 2]), abs(chart[component, 1]))
        split = [component[theta < .60], component[(theta >= .60) & (theta < .95)], component[theta >= .95]] if component_index == 0 else [component]
        groups.extend((component_index, component, subgroup) for subgroup in split)
    return groups


def original_selected_edges(source_faces, selected_ids, source_vertex_count):
    """Actual source-control edges, with both endpoints in saved selection."""
    lookup = np.full(source_vertex_count, -1, np.int32)
    lookup[selected_ids] = np.arange(len(selected_ids))
    collected = []
    for start in range(0, len(source_faces), 400000):
        f = lookup[source_faces[start:start + 400000]]
        for i, j in ((0, 1), (1, 2), (2, 3), (3, 0)):
            edge = f[:, [i, j]]
            edge = edge[(edge >= 0).all(axis=1)]
            if len(edge):
                collected.append(np.sort(edge, axis=1))
    edges = np.unique(np.concatenate(collected), axis=0)
    if not len(edges):
        raise ValueError('No original edges inside the marked source selection.')
    return edges


def root_frame(path_xyz, arc, index, normal, fallback):
    """A coherent path-window chord, projected to the actual tangent plane."""
    distance = arc[index]
    lo = max(0, int(np.searchsorted(arc, distance - .020, side='left')))
    hi = min(len(arc) - 1, int(np.searchsorted(arc, distance + .020, side='right')))
    if hi <= lo:
        lo, hi = max(0, index - 1), min(len(arc) - 1, index + 1)
    tangent = path_xyz[hi] - path_xyz[lo]
    tangent -= normal * np.dot(tangent, normal)
    if np.linalg.norm(tangent) < 1e-8:
        tangent = fallback - normal * np.dot(fallback, normal)
    tangent = unit(tangent)
    advance = path_xyz[min(index + 1, len(arc) - 1)] - path_xyz[max(index - 1, 0)]
    if np.dot(tangent, advance) < 0:
        tangent = -tangent
    frame = np.column_stack([tangent, unit(np.cross(normal, tangent)), normal])
    if not np.allclose(frame.T @ frame, np.eye(3), atol=1e-12) or np.linalg.det(frame) < .999999:
        raise ValueError('Non-orthonormal source frame.')
    return frame, (lo, hi)


def build_group(group_id, component_index, component, coarse_ids, labels, all_ids,
                xyz, normals, weights, edges, lengths, facing):
    seed_id = SEEDS[group_id]
    seed_index = int(np.flatnonzero(all_ids == seed_id)[0])
    seed_xyz, seed_normal = xyz[seed_index], normals[seed_index]
    distances = np.linalg.norm(xyz - seed_xyz, axis=1)
    allowed = (labels == group_id) & (distances <= .13) & (weights > .5)
    if not allowed[seed_index]:
        raise ValueError('Original representative is outside its selected patch.')
    retained_edges = allowed[edges].all(axis=1)
    e, length = edges[retained_edges], lengths[retained_edges]
    graph = coo_matrix((length, (e[:, 0], e[:, 1])), shape=(len(xyz), len(xyz)))
    geodesic, predecessor = dijkstra(graph.tocsr(), directed=False, indices=seed_index, return_predecessors=True)
    connected = np.isfinite(geodesic) & allowed
    normal_dot = normals @ seed_normal
    visible = connected & (normal_dot > .5) & (facing > .30)
    if visible.sum() < 3:
        raise ValueError('Too few actual visible roots in a source-connected patch.')
    selected = xyz[visible]
    centered = selected - selected.mean(axis=0)
    projected = centered - (centered @ seed_normal)[:, None] * seed_normal
    eigenvalues, eigenvectors = np.linalg.eigh(projected.T @ projected / max(1, len(projected) - 1))
    axis = unit(eigenvectors[:, -1])
    # Deterministic sign: principal component points in increasing source Z,
    # with dominant coordinate sign as a fallback for an almost horizontal axis.
    if axis[2] < -1e-10 or (abs(axis[2]) <= 1e-10 and axis[np.argmax(abs(axis))] < 0):
        axis = -axis
    coordinate = (xyz - seed_xyz) @ axis
    eligible = np.flatnonzero(visible & (geodesic > .040))
    eligible = sorted(eligible, key=lambda i: (-abs(float(coordinate[i])), float(geodesic[i]), int(all_ids[i])))
    if not eligible:
        raise ValueError('The actual local source path is too short.')
    chosen = None
    for endpoint in eligible[:100]:
        path = [int(endpoint)]
        while path[-1] != seed_index:
            parent = int(predecessor[path[-1]])
            if parent < 0 or len(path) > len(xyz):
                raise ValueError('Invalid original-edge predecessor path.')
            path.append(parent)
        path = np.asarray(path[::-1], np.int64)
        path_xyz = xyz[path]
        arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(path_xyz, axis=0), axis=1))]
        normal_compatible = (normals[path] @ normals[endpoint]) > .5
        middle_candidates = np.flatnonzero(visible[path] & normal_compatible & (arc >= .20 * arc[-1]) & (arc <= .80 * arc[-1]))
        if not len(middle_candidates):
            continue
        middle = int(middle_candidates[np.argmin(abs(arc[middle_candidates] - .5 * arc[-1]))])
        if min(np.linalg.norm(path_xyz[middle] - path_xyz[0]), np.linalg.norm(path_xyz[-1] - path_xyz[middle])) < .015:
            continue
        chosen = path, path_xyz, arc, middle
        break
    if chosen is None:
        raise ValueError('No three well-separated actual source roots with coherent visible normals.')
    path, path_xyz, arc, middle = chosen
    roots = []
    root_indices = (0, middle, len(path) - 1)
    for chain_index, index in enumerate(root_indices):
        vertex_index = int(path[index])
        normal = unit(normals[vertex_index])
        frame, window = root_frame(path_xyz, arc, index, normal, axis)
        root_xyz = xyz[vertex_index]
        patch_local = (xyz[visible] - root_xyz) @ frame
        roots.append(dict(
            group_id=group_id, root_chain_index=chain_index,
            source_control_vertex_id=int(all_ids[vertex_index]), source_xyz=root_xyz.tolist(),
            source_outward_normal=normal.tolist(), frame_columns=frame.tolist(),
            source_mask_weight=float(weights[vertex_index]), close_camera_facing=float(facing[vertex_index]),
            path_vertex_index=int(index), source_path_arc_distance=float(arc[index]),
            relative_anchor_arc_distance=float(arc[index] - arc[middle]),
            normal_angle_from_old_seed_degrees=float(np.degrees(np.arccos(np.clip(np.dot(normal, seed_normal), -1, 1)))),
            source_path_tangent_window_indices=list(window),
            actual_patch_local_quantile_extent=np.quantile(patch_local, [.05, .95], axis=0).tolist(),
        ))
    root_normals = np.asarray([root['source_outward_normal'] for root in roots])
    pair_angles = np.degrees(np.arccos(np.clip(root_normals @ root_normals.T, -1, 1)))
    if pair_angles.max() >= 60.000001:
        raise ValueError('Actual root normals exceed the fixed sixty-degree coherence bound.')
    root_positions = np.asarray([root['source_xyz'] for root in roots])
    root_chords = np.linalg.norm(np.diff(root_positions, axis=0), axis=1)
    for i, root in enumerate(roots):
        root['adjacent_root_chord_distances'] = [float(root_chords[j]) for j in (i - 1, i) if 0 <= j < 2]
    actual_guide_chord = float(np.linalg.norm(path_xyz[-1] - path_xyz[0]))
    target_length = float(np.clip(actual_guide_chord + .035, .14, .18))
    return dict(
        group_id=group_id, marked_component=component_index,
        marked_component_coarse_vertices=len(component), group_coarse_vertices=len(coarse_ids),
        original_coarse_group_ids=coarse_ids.tolist(), old_representative_source_vertex_id=seed_id,
        patch_radius=.13, candidate_patch_vertices=int(allowed.sum()),
        source_connected_patch_vertices=int(connected.sum()), visible_normal_coherent_patch_vertices=int(visible.sum()),
        original_connected_edge_count=len(e), actual_selected_patch_xyz_extent=np.ptp(xyz[connected], axis=0).tolist(),
        tangent_PCA_eigenvalues=eigenvalues.tolist(), tangent_PCA_direction=axis.tolist(),
        tangent_PCA_full_span=float(np.ptp(coordinate[visible])),
        tangent_PCA_trimmed_interval=np.quantile(coordinate[visible], [.05, .95]).tolist(),
        roots=roots, anchor_root_index=1, source_path_vertex_ids=all_ids[path].tolist(),
        source_path_xyz=path_xyz.tolist(), source_path_normals=normals[path].tolist(),
        source_path_arc_distances=arc.tolist(), source_path_arc_length=float(arc[-1]),
        source_path_chord_length=actual_guide_chord,
        root_arc_distances_relative_to_anchor=[root['relative_anchor_arc_distance'] for root in roots],
        actual_root_pair_normal_angle_max_degrees=float(pair_angles.max()),
        actual_root_adjacent_chord_distances=root_chords.tolist(),
        suggested_total_ribbon_length=target_length,
        suggested_extension_scope='The suggested ribbon length is a design bound. Any extrapolation beyond these actual source roots must be separately recorded by the assembler; it is not an observed source surface.',
        guide_scope='Existing G7 control-edge shortest path inside the selected patch; source-connected local fitting guide, not a certified fold crest or semantic ornament boundary.',
    )


def placement():
    for name, sha in EXPECTED.items():
        if digest(SOURCE / name) != sha:
            raise ValueError('Original G7 changed: ' + name)
    if digest(SELECTION / 'selection.npz') != SELECTION_SHA or digest(SELECTION / 'projection_request.npz') != NORMAL_SHA:
        raise ValueError('Original marked selection or original source normals changed.')
    previous = json.loads(PRIOR.read_text(encoding='utf-8'))
    if tuple(anchor['source_control_vertex_id'] for anchor in previous['canonical_anchors']) != SEEDS:
        raise ValueError('Previous six representative ends differ.')
    with np.load(SOURCE / 'control_quad.npz', allow_pickle=False) as data:
        source_xyz, source_faces = data['xyz'], data['faces']
        chart = data['chart'][:109410].copy()
    with np.load(COARSE, allow_pickle=False) as data:
        coarse_faces = data['faces']
    with np.load(SELECTION / 'selection.npz', allow_pickle=False) as data:
        mask = data['coarse_mask']
    with np.load(SELECTION / 'projection_request.npz', allow_pickle=False) as data:
        ids, xyz, normals, weights = data['vertex_ids'], data['xyz'], data['source_normals'], data['weight']
    if not np.array_equal(source_xyz[ids], xyz):
        raise ValueError('Selected source coordinates do not match original G7 exactly.')
    if not np.allclose(np.linalg.norm(normals, axis=1), 1., atol=1e-12):
        raise ValueError('Saved actual source normals are not unit length.')
    grouped = components(source_xyz[:len(mask)], chart, mask, coarse_faces)
    coarse_ids = np.concatenate([group[2] for group in grouped])
    coarse_labels = np.concatenate([np.full(len(group[2]), i, np.int32) for i, group in enumerate(grouped)])
    nearest_distance, nearest = cKDTree(source_xyz[coarse_ids]).query(xyz)
    labels = coarse_labels[nearest]
    edges = original_selected_edges(source_faces, ids, len(source_xyz))
    lengths = np.linalg.norm(xyz[edges[:, 1]] - xyz[edges[:, 0]], axis=1)
    if (lengths <= 0).any():
        raise ValueError('Degenerate actual source edge.')
    facing = np.einsum('ij,ij->i', normals, (CAMERA_POSITION - xyz) / np.linalg.norm(CAMERA_POSITION - xyz, axis=1)[:, None])
    groups = [build_group(i, component_index, component, group_ids, labels, ids,
                          xyz, normals, weights, edges, lengths, facing)
              for i, (component_index, component, group_ids) in enumerate(grouped)]
    representative = groups[0]
    macro_target = np.asarray(representative['roots'][1]['source_xyz']) + np.asarray(representative['roots'][1]['source_outward_normal']) * .008
    view_direction = unit(CAMERA_POSITION - CAMERA_TARGET)
    macro_position = macro_target + view_direction * np.linalg.norm(CAMERA_POSITION - CAMERA_TARGET)
    return dict(
        date='2026-10-14', source=str(SOURCE), source_generation=7, source_hashes=EXPECTED,
        source_control_coordinate_sha256=array_hash(source_xyz),
        original_marked_selection=str(SELECTION / 'selection.npz'), marked_selection_sha256=SELECTION_SHA,
        original_normal_request=str(SELECTION / 'projection_request.npz'), original_normal_request_sha256=NORMAL_SHA,
        previous_local_comparison_placement=str(PRIOR), previous_local_comparison_placement_sha256=digest(PRIOR),
        coarse_topology=str(COARSE), coarse_topology_sha256=digest(COARSE),
        physical_height=HEIGHT, reflection_signs=SIGNS, canonical_groups=groups,
        canonical_anchors=[root for group in groups for root in group['roots']],
        canonical_group_count=len(groups), canonical_root_count=sum(len(group['roots']) for group in groups),
        canonical_centre_roots=[group['roots'][group['anchor_root_index']] for group in groups],
        source_selection_vertex_count=len(ids), source_selection_edge_count=len(edges),
        dense_group_assignment_rule='Nearest actual marked coarse vertex among the six original groups, followed by actual original-control-edge connectivity inside each .13-radius patch. Nearest-group assignment is a bounded geometric grouping; it is not an exact material ancestry inversion.',
        root_visibility_rule='Actual source outward normals; camera-facing dot > .30, seed-normal dot > .50 and all three root-pair normal angles < 60 degrees.',
        frame_rule='Local X follows an actual-source-edge path-window chord projected into the source tangent plane; local Z is the saved original source outward normal. Local Y is Z cross X. No global-up tangent is used.',
        macro_camera=dict(view='macro_7272', original_end_source_vertex_id=7272,
                          target=macro_target.tolist(), position=macro_position.tolist(), ortho=.30,
                          rule='Same viewing direction as original close_oblique; target is actual middle root of selected end 7272 plus .008 along its original outward normal.'),
        source_body_geometry_changed=False, added_body_smoothing=0, added_body_CC_passes=0,
        scope='Only source-bound placement evidence is produced here. Original G7 coordinates, topology and existing prototypes are not modified. Independent ornament overlap and source-edge guidance do not certify Boolean fusion, collision freedom or tangent continuity.',
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    root = parser.parse_args().root.resolve()
    target = root / 'PLACEMENT.json'
    if target.exists():
        raise FileExistsError('Placement checkpoint is immutable; use a new root.')
    snapshot = root / 'source_snapshot' / HERE.name / 'placement.py'
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if snapshot.exists():
        raise FileExistsError('Placement source snapshot already exists.')
    shutil.copyfile(Path(__file__).resolve(), snapshot)
    source_sha = digest(snapshot)
    started = time.perf_counter()
    result = placement()
    if digest(Path(__file__).resolve()) != source_sha or digest(snapshot) != source_sha:
        raise ValueError('Executed placement source differs from snapshot.')
    result['source_snapshot'] = dict(source=str(Path(__file__).resolve()), snapshot=str(snapshot), sha256=source_sha)
    result['seconds'] = time.perf_counter() - started
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(dict(saved=str(target), sha256=digest(target), groups=[dict(
        id=g['group_id'], roots=[r['source_control_vertex_id'] for r in g['roots']],
        guide_chord=g['source_path_chord_length'], guide_arc=g['source_path_arc_length'],
        normal_angle_max=g['actual_root_pair_normal_angle_max_degrees']) for g in result['canonical_groups']]), indent=2), flush=True)


if __name__ == '__main__':
    main()
