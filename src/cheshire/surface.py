"""One terminal COMPAS Catmull-Clark comparison, without semantic inheritance."""

from dataclasses import dataclass
from math import dist, isfinite
from statistics import median
from time import perf_counter

import compas
from compas.datastructures import Mesh

from .execution import ExecutionBudget, check_execution_budget
from .validation import inspect_mesh, validate_mesh


BOUNDARY_POLICY = "Fix existing naked-boundary vertices; crease only naked-boundary edges at 2; k=1."


@dataclass(frozen=True)
class SurfaceResult:
    mesh: Mesh
    metadata: dict


def assess_catmull_clark(*, vertices, edges, faces, corners, budget=None):
    """Exact one-level tri/quad estimate; callable before materializing a copy."""
    budget = budget if budget is not None else ExecutionBudget(50000, 50000)
    return {"estimated_output_vertices": vertices + edges + faces,
            "estimated_output_faces": corners,
            **check_execution_budget(budget, input_vertices=vertices, input_faces=faces,
                estimated_output_vertices=vertices + edges + faces, estimated_output_faces=corners)}


def catmull_clark_once(mesh: Mesh, *, budget=None) -> SurfaceResult:
    """Smooth an independent geometry-only copy using the installed public API.

    No welding, planar-face restriction, semantic fields, roles or lineage.
    Original vertex keys are used only to measure retained-point displacement.
    COMPAS 2.15.1 skips edge-point movement for nonzero input creases and
    decrements child creases; fixed vertices bypass vertex smoothing.
    """
    start = perf_counter()
    corners = sum(len(mesh.face_vertices(k)) for k in mesh.faces())
    assessment = assess_catmull_clark(vertices=mesh.number_of_vertices(), edges=mesh.number_of_edges(),
                                    faces=mesh.number_of_faces(), corners=corners, budget=budget)
    if assessment["status"] != "SAFE":
        raise ValueError("Catmull-Clark blocked before copying/subdivision: " + " ".join(assessment["reasons"]))
    _check_geometry(mesh)
    before = inspect_mesh(mesh)
    boundary = [edge for edge in mesh.edges() if mesh.is_edge_on_boundary(edge)]
    fixed = sorted({key for edge in boundary for key in edge})
    components = len(mesh.connected_vertices())
    # Preserve keys/ordered corners, but transfer no source attributes/fields.
    copy = Mesh()
    for key in mesh.vertices():
        x, y, z = mesh.vertex_coordinates(key)
        copy.add_vertex(key=key, x=x, y=y, z=z)
    for key in mesh.faces():
        copy.add_face(mesh.face_vertices(key), fkey=key)
    for edge in boundary:
        copy.edge_attribute(edge, "crease", 2)
    output = copy.subdivided(scheme="catmullclark", k=1, fixed=fixed)
    _check_geometry(output)
    after = inspect_mesh(output)
    if (after["vertex_count"], after["face_count"]) != (
        assessment["estimated_output_vertices"], assessment["estimated_output_faces"]
    ):
        raise ValueError("COMPAS Catmull-Clark counts disagree with the one-level estimate.")
    output_components = len(output.connected_vertices())
    if output_components != components or after["boundary_edge_count"] != 2 * len(boundary):
        raise ValueError("Catmull-Clark changed components or unexpected boundary connectivity.")
    displacement = [dist(mesh.vertex_coordinates(k), output.vertex_coordinates(k)) for k in mesh.vertices()]
    tolerance = max(max(before["bounding_box"]) * 1e-10,
                    max(abs(v) for k in mesh.vertices() for v in mesh.vertex_coordinates(k)) * 2e-14, 1e-14)
    boundary_displacement = max((dist(mesh.vertex_coordinates(k), output.vertex_coordinates(k)) for k in fixed), default=0.0)
    segment_error = 0.0
    originals = set(mesh.vertices())
    for u, v in boundary:
        # Topological verification only: the new boundary midpoint must connect
        # both original endpoints. This is not a semantic ancestry map.
        candidates = (set(output.vertex_neighbors(u)) & set(output.vertex_neighbors(v))) - originals
        candidates = [w for w in candidates if output.is_edge_on_boundary((u, w)) and output.is_edge_on_boundary((w, v))]
        if len(candidates) != 1:
            raise ValueError("An original boundary segment did not become exactly two boundary edges.")
        midpoint = [a / 2 + b / 2 for a, b in zip(mesh.vertex_coordinates(u), mesh.vertex_coordinates(v))]
        segment_error = max(segment_error, dist(midpoint, output.vertex_coordinates(candidates[0])))
    if boundary_displacement > tolerance or segment_error > tolerance:
        raise ValueError("Catmull-Clark did not preserve the original boundary vertices/segments.")
    if not all(isfinite(d) for d in displacement):
        raise ValueError("Non-finite retained-vertex displacement.")
    return SurfaceResult(output, {
        "backend": {"name": "COMPAS", "version": compas.__version__, "operation": "Mesh.subdivided"},
        "scheme": "catmullclark", "level": 1, "terminal_derivative": True,
        "semantic_lineage": "NOT IMPLEMENTED", "boundary_policy": BOUNDARY_POLICY,
        "fixed_vertex_count": len(fixed), "creased_edge_count": len(boundary), "boundary_crease": 2,
        "components_before": components, "components_after": output_components,
        "input": before, "output": after, "budget": assessment,
        "retained_vertex_displacement": {"count": len(displacement), "median": median(displacement), "maximum": max(displacement)},
        "boundary_preservation": {"status": "PASS", "maximum_vertex_displacement": boundary_displacement,
                                  "maximum_midpoint_error": segment_error, "checked_segments": len(boundary), "tolerance": tolerance},
        "elapsed_seconds": perf_counter() - start,
    })


def _check_geometry(mesh):
    problems = validate_mesh(mesh)
    if problems:
        raise ValueError("Invalid comparison mesh: " + " ".join(problems))
    if not mesh.is_valid() or not mesh.is_manifold():
        raise ValueError("Comparison requires valid manifold connectivity; open boundaries are allowed.")
    if any(len(mesh.face_vertices(k)) not in (3, 4) or len(set(mesh.face_vertices(k))) != len(mesh.face_vertices(k))
           for k in mesh.faces()) or any(mesh.vertex_degree(k) == 0 for k in mesh.vertices()):
        raise ValueError("Comparison requires connected triangle/quad corners and no isolated vertices.")
