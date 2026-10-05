"""Read-only per-vertex measurement of COMPAS polygon meshes."""

from collections import deque
from itertools import combinations
from math import acos, dist, fsum, hypot, isfinite, pi
from numbers import Real

from compas.datastructures import Mesh

from .normalization import _finite_number, normalize_values
from .validation import validate_mesh


def analyze_vertex_attributes(mesh: Mesh) -> dict:
    """Measure geometry and topology without changing mesh data.

    Distances use COMPAS's surface-area-weighted mesh centroid and min-max
    normalization. Undefined centroids (e.g. zero-area meshes) or distances
    exceeding float range produce None, never NaN/inf. Basic invalid inputs
    and inconsistent COMPAS topology raise ValueError.

    approximate_curvature is the mean pairwise angle between incident unit
    face normals, divided by pi. It is a dimensionless normal-variation proxy,
    not differential curvature, and depends on face winding and tessellation.
    Boundary vertices, incomplete face fans, and degenerate/unavailable normals
    return None. No boundary extrapolation or geometry repair is performed.

    boundary_distance is a multi-source breadth-first edge-hop distance.
    Components without any boundary seed (including closed meshes) get None.
    """
    problems = validate_mesh(mesh)
    if problems:
        raise ValueError("Invalid mesh: " + " ".join(problems))
    if not mesh.is_valid():
        raise ValueError("Mesh has inconsistent COMPAS topology; no repair performed.")

    keys = list(mesh.vertices())
    coordinates = {key: mesh.vertex_coordinates(key) for key in keys}
    neighbors = {key: mesh.vertex_neighbors(key) for key in keys}
    boundaries = {key: mesh.is_vertex_on_boundary(key) for key in keys}
    heights = normalize_values({key: xyz[2] for key, xyz in coordinates.items()})
    centroid = _mesh_centroid(mesh)
    distances = {}
    for key, xyz in coordinates.items():
        distance = None if centroid is None else dist(xyz, centroid)
        distances[key] = distance if distance is not None and isfinite(distance) else None
    normalized_distances = normalize_values(distances)
    boundary_distances = _boundary_distances(neighbors, boundaries)
    normals = {face: _face_normal(mesh, face) for face in mesh.faces()}

    return {
        key: {
            "valence": len(neighbors[key]),
            "boundary": boundaries[key],
            "normalized_height": heights[key],
            "centroid_distance": distances[key],
            "normalized_centroid_distance": normalized_distances[key],
            "approximate_curvature": _curvature(mesh, key, neighbors[key], boundaries[key], normals),
            "boundary_distance": boundary_distances[key],
        }
        for key in keys
    }


def attribute_summary(attributes: dict) -> dict:
    """Return min/max/mean for each numeric attribute, ignoring None.

    Boolean attributes are excluded. All-null attributes have None statistics;
    empty input returns {}. Non-finite numeric values raise ValueError.
    """
    names = dict.fromkeys(name for record in attributes.values() for name in record)
    summary = {}
    for name in names:
        raw = [record.get(name) for record in attributes.values()]
        present = [value for value in raw if value is not None]
        if present and all(isinstance(value, bool) for value in present):
            continue
        if any(not isinstance(value, Real) or isinstance(value, bool) for value in present):
            raise ValueError(f"Attribute {name!r} must contain numbers or None.")
        values = [_finite_number(value, name) for value in present]
        if not values:
            summary[name] = {"min": None, "max": None, "mean": None}
            continue
        scale = max(abs(value) for value in values)
        # Scaling avoids overflow when the sum of finite values is not finite.
        mean = 0.0 if scale == 0.0 else scale * min(
            1.0, max(-1.0, fsum(value / scale for value in values) / len(values))
        )
        summary[name] = {"min": min(values), "max": max(values), "mean": mean}
    return summary


def _mesh_centroid(mesh: Mesh) -> list[float] | None:
    try:
        centroid = list(mesh.centroid())
    except (ZeroDivisionError, OverflowError):
        return None
    return centroid if all(isfinite(value) for value in centroid) else None


def _face_normal(mesh: Mesh, face: int) -> list[float] | None:
    try:
        normal = list(mesh.face_normal(face))
        length = hypot(*normal)
    except (ZeroDivisionError, OverflowError, NotImplementedError):
        return None
    if not isfinite(length) or length == 0.0:
        return None
    return [value / length for value in normal]


def _curvature(mesh, key, neighbors, boundary, normals) -> float | None:
    if boundary:
        return None
    faces = mesh.vertex_faces(key)
    # A closed manifold fan must visit every neighboring vertex exactly once.
    ordered = mesh.vertex_neighbors(key, ordered=True)
    if len(faces) < 2 or len(faces) != len(neighbors) or len(ordered) != len(neighbors):
        return None
    if set(ordered) != set(neighbors) or any(normals[face] is None for face in faces):
        return None
    angles = []
    for first, second in combinations(faces, 2):
        dot = fsum(a * b for a, b in zip(normals[first], normals[second]))
        angles.append(acos(min(1.0, max(-1.0, dot))) / pi)
    return fsum(angles) / len(angles)


def _boundary_distances(neighbors: dict, boundaries: dict) -> dict:
    distances = {key: 0 if boundaries[key] else None for key in neighbors}
    queue = deque(key for key in neighbors if boundaries[key])
    while queue:
        key = queue.popleft()
        for neighbor in neighbors[key]:
            if distances[neighbor] is None:
                distances[neighbor] = distances[key] + 1
                queue.append(neighbor)
    return distances
