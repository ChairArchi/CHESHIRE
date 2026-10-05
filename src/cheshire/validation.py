"""Read-only inspection and basic validation of COMPAS meshes."""

from math import isfinite

from compas.datastructures import Mesh


def validate_mesh(mesh: Mesh) -> list[str]:
    """Return explicit problems; an empty list means basic validation passed.

    This checks only non-empty geometry and finite XYZ coordinates, not
    degeneracy, self-intersection, or suitability for later transformations.
    The mesh is never modified.
    """
    problems = []
    if mesh.number_of_vertices() == 0:
        problems.append("Mesh has zero vertices.")
    if mesh.number_of_faces() == 0:
        problems.append("Mesh has zero faces.")
    for key in mesh.vertices():
        xyz = mesh.vertex_coordinates(key)
        if not all(isfinite(value) for value in xyz):
            problems.append(f"Vertex {key} has non-finite coordinates: {xyz}.")
    return problems


def inspect_mesh(mesh: Mesh) -> dict:
    """Return counts, COMPAS topology checks, and axis-aligned box dimensions.

    Bounding box dimensions are None for empty or non-finite coordinates.
    Topology checks are None if the COMPAS method is unavailable.
    """
    coordinates = [mesh.vertex_coordinates(key) for key in mesh.vertices()]
    dimensions = None
    if coordinates and all(isfinite(v) for xyz in coordinates for v in xyz):
        dimensions = [max(axis) - min(axis) for axis in zip(*coordinates)]

    return {
        "vertex_count": mesh.number_of_vertices(),
        "face_count": mesh.number_of_faces(),
        "edge_count": mesh.number_of_edges(),
        "boundary_edge_count": sum(
            mesh.is_edge_on_boundary(edge) for edge in mesh.edges()
        ),
        "is_manifold": _topology_property(mesh, "is_manifold"),
        "is_closed": _topology_property(mesh, "is_closed"),
        "bounding_box": dimensions,
    }


def _topology_property(mesh: Mesh, name: str) -> bool | None:
    method = getattr(mesh, name, None)
    if not callable(method):
        return None
    try:
        return method()
    except NotImplementedError:
        return None
