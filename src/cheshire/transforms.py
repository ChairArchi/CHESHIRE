"""A single topology-preserving, field-driven normal displacement transform."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import dist, hypot, isfinite

from compas.datastructures import Mesh

from .normalization import _finite_number
from .validation import validate_mesh


@dataclass(frozen=True)
class TransformResult:
    """New geometry and deterministic metadata for one displacement call.

    selected_count counts unique candidate vertices (all mesh vertices when
    selection is None). skipped_count counts candidates whose coordinates did
    not change, including zero/null input and unsafe normals. skipped_vertices
    records reasons. max_displacement is the largest actual coordinate change.
    """

    mesh: Mesh
    operator: str
    selected_count: int
    moved_count: int
    skipped_count: int
    strength: float
    scale_mode: str
    direction: str
    base_scale: float
    max_displacement: float
    topology_changed: bool
    skipped_vertices: dict


def displace_vertices_along_normals(
    mesh: Mesh,
    field_values: Mapping,
    selected_vertices: Iterable | None = None,
    strength: float = 0.01,
    scale_mode: str = "bbox_diagonal",
    direction: str = "outward",
) -> TransformResult:
    """Displace selected vertices on a new Mesh; never mutate the input.

    Distance = field value * strength * input bounding-box diagonal. Field
    values must be finite in [0, 1]; None/missing values mean no movement.
    Strength must be finite and non-negative. Only bbox_diagonal is supported.
    Outward follows the original vertex normal; inward follows its negative.
    These labels follow face winding and do not correct mesh orientation.

    COMPAS vertex_normal averages non-unit incident polygon normals (area
    weighted), then unitizes the result. All normals are computed on the input
    geometry, so earlier moves cannot affect later vertices. Incomplete face
    fans and zero, non-finite, or unavailable normals are skipped, never repaired.
    Boundary vertices may move when their available normal is valid.

    Unknown vertex keys, invalid geometry/parameters, or unrepresentable scales
    and output coordinates raise ValueError. Zero displacement and changes too
    small to alter a coordinate are reported as skips. Vertex/face keys, face
    connectivity, and existing attributes are retained by COMPAS Mesh.copy().
    Rules and budget checks are the caller's responsibility.
    """
    strength = _finite_number(strength, "strength")
    if strength < 0.0:
        raise ValueError("strength must be >= 0.")
    if scale_mode != "bbox_diagonal":
        raise ValueError("scale_mode must be 'bbox_diagonal'.")
    if direction not in ("outward", "inward"):
        raise ValueError("direction must be 'outward' or 'inward'.")
    problems = validate_mesh(mesh)
    if problems:
        raise ValueError("Invalid mesh: " + " ".join(problems))
    if not mesh.is_valid():
        raise ValueError("Mesh has inconsistent COMPAS topology; no repair performed.")

    keys = list(mesh.vertices())
    values = _field_values(field_values, keys)
    selected = _selected_keys(selected_vertices, keys)
    coordinates = {key: mesh.vertex_coordinates(key) for key in keys}
    extents = [max(axis) - min(axis) for axis in zip(*coordinates.values())]
    base_scale = hypot(*extents)
    if not isfinite(base_scale):
        raise ValueError("Bounding-box diagonal exceeds finite float range.")

    updates = {}
    skipped = {}
    max_displacement = 0.0
    sign = 1.0 if direction == "outward" else -1.0
    for key in selected:
        value = values.get(key)
        if value is None:
            skipped[key] = "unavailable_field"
            continue
        if value == 0.0 or strength == 0.0 or base_scale == 0.0:
            skipped[key] = "zero_displacement"
            continue
        normal = _vertex_normal(mesh, key)
        if normal is None:
            skipped[key] = "unsafe_normal"
            continue
        distance = value * strength * base_scale
        if not isfinite(distance):
            raise ValueError(f"Displacement distance exceeds finite float range at vertex {key}.")
        xyz = coordinates[key]
        displaced = [coordinate + sign * distance * component for coordinate, component in zip(xyz, normal)]
        if not all(isfinite(coordinate) for coordinate in displaced):
            raise ValueError(f"Displaced coordinates would be non-finite at vertex {key}.")
        actual_distance = dist(xyz, displaced)
        if not isfinite(actual_distance):
            raise ValueError(f"Coordinate change exceeds finite float range at vertex {key}.")
        if actual_distance == 0.0:
            skipped[key] = "coordinate_precision"
            continue
        updates[key] = displaced
        max_displacement = max(max_displacement, actual_distance)

    output = mesh.copy()
    for key, xyz in updates.items():
        output.vertex_attributes(key, names=["x", "y", "z"], values=xyz)
    return TransformResult(
        mesh=output,
        operator="normal_displacement",
        selected_count=len(selected),
        moved_count=len(updates),
        skipped_count=len(skipped),
        strength=strength,
        scale_mode=scale_mode,
        direction=direction,
        base_scale=base_scale,
        max_displacement=max_displacement,
        topology_changed=False,
        skipped_vertices=skipped,
    )


def _field_values(field_values: Mapping, keys: list) -> dict:
    if not isinstance(field_values, Mapping):
        raise ValueError("field_values must be a mapping of vertex keys to scalars or None.")
    if set(field_values) - set(keys):
        raise ValueError("Field contains vertex keys absent from the mesh.")
    values = {}
    for key, value in field_values.items():
        if value is None:
            values[key] = None
            continue
        value = _finite_number(value, f"Field value at {key!r}")
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Field value at {key!r} must be in [0, 1].")
        values[key] = value
    return values


def _selected_keys(selected_vertices: Iterable | None, keys: list) -> list:
    if selected_vertices is None:
        return keys
    try:
        requested = set(selected_vertices)
    except TypeError as error:
        raise ValueError("selected_vertices must be an iterable of vertex keys or None.") from error
    if requested - set(keys):
        raise ValueError("Selection contains vertex keys absent from the mesh.")
    # Use mesh order even when a caller passes a set or duplicates.
    return [key for key in keys if key in requested]


def _vertex_normal(mesh: Mesh, key: int) -> list[float] | None:
    neighbors = mesh.vertex_neighbors(key)
    if not mesh.vertex_faces(key) or not neighbors:
        return None
    ordered = mesh.vertex_neighbors(key, ordered=True)
    if len(ordered) != len(neighbors) or set(ordered) != set(neighbors):
        return None
    try:
        normal = list(mesh.vertex_normal(key))
        if len(normal) != 3:
            return None
        length = hypot(*normal)
    except (TypeError, ValueError, ZeroDivisionError, OverflowError, NotImplementedError):
        return None
    if length == 0.0 or not isfinite(length):
        return None
    return [component / length for component in normal]
