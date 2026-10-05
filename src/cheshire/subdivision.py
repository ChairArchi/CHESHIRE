"""One global COMPAS quad-subdivision step with checked immediate lineage.

Verified against installed COMPAS 2.15.1, Mesh.subdivided(scheme='quad', k=1).
It retains original keys/XYZ, splits unique edges at t=0.5, uses arithmetic
face_centroid(), and assigns child path=[input_face_key, corner_index]. All
these assumptions are checked against returned topology/geometry per call.
The backend's path is adapter metadata, not multi-generation provenance.
"""

from dataclasses import dataclass
from math import dist, hypot, isfinite

import compas
from compas.datastructures import Mesh
from compas.geometry import cross_vectors, distance_point_plane, is_polygon_convex

from .execution import ExecutionBudget, check_execution_budget
from .lineage import LineageMap, ParentRef
from .validation import validate_lineage_coverage, validate_mesh


GEOMETRY_TOLERANCE = 1e-9


@dataclass(frozen=True)
class SubdivisionResult:
    """New geometry, verified lineage, and deterministic one-step metadata."""

    mesh: Mesh
    lineage: LineageMap
    operator: str
    backend: str
    backend_version: str
    levels: int
    input_vertices: int
    input_faces: int
    estimated_output_vertices: int
    estimated_output_faces: int
    output_vertices: int
    output_faces: int
    topology_changed: bool
    nonplanar_policy: str = "reject"


def estimate_quad_subdivision(mesh: Mesh, *, nonplanar_policy: str = "reject") -> dict:
    """Validate operator inputs and return exact one-step V+E+F / 3T+4Q counts."""
    _require_supported_mesh(mesh, nonplanar_policy)
    sizes = [len(mesh.face_vertices(face)) for face in mesh.faces()]
    vertices, edges, faces = mesh.number_of_vertices(), mesh.number_of_edges(), mesh.number_of_faces()
    triangles, quads = sizes.count(3), sizes.count(4)
    return {
        "input_vertices": vertices, "input_edges": edges, "input_faces": faces,
        "triangle_count": triangles, "quad_count": quads,
        "estimated_output_vertices": vertices + edges + faces,
        "estimated_output_faces": 3 * triangles + 4 * quads,
    }


def subdivide_quad_once(
    mesh: Mesh,
    *,
    budget: ExecutionBudget,
    current_generation: int = 0,
    nonplanar_policy: str = "reject",
) -> SubdivisionResult:
    """Execute exactly one global level only after an explicit SAFE budget.

    Supports oriented manifold planar strictly convex triangles/quads, open
    or closed, including disconnected components and sparse COMPAS keys.
    Isolated vertices and invalid/degenerate faces are rejected, never fixed.
    Default 'reject' retains the planar contract. Explicit 'bilinear' treats
    quads as ordered bilinear patches passing a conservative local Jacobian
    test; it does not project or triangulate geometry. Triangles stay unchanged.
    No selection, smoothing, welding, triangulation, or displacement occurs.

    Only XYZ and connectivity are carried into the backend. Custom/default
    vertex, face, edge, and mesh attributes are discarded on the new mesh;
    backend child 'path' is retained. Explicit fields use inherit_fields;
    geometry-derived fields must be recomputed separately. Input is untouched.
    """
    estimate = estimate_quad_subdivision(mesh, nonplanar_policy=nonplanar_policy)
    assessment = check_execution_budget(
        budget, input_faces=estimate["input_faces"], input_vertices=estimate["input_vertices"],
        estimated_output_faces=estimate["estimated_output_faces"],
        estimated_output_vertices=estimate["estimated_output_vertices"],
        current_generation=current_generation,
    )
    if assessment["status"] != "SAFE":
        raise ValueError("Quad subdivision blocked by budget: " + " ".join(assessment["reasons"]))
    # A geometry-only copy avoids stale measurements and protects all input
    # attributes even if a backend changes its argument internally.
    control = Mesh()
    for key in mesh.vertices():
        x, y, z = mesh.vertex_coordinates(key)
        control.add_vertex(key=key, x=x, y=y, z=z)
    for face in mesh.faces():
        control.add_face(list(mesh.face_vertices(face)), fkey=face)
    output = control.subdivided(scheme="quad", k=1)
    if not isinstance(output, Mesh):
        raise ValueError("COMPAS quad subdivision did not return a Mesh.")
    if (output.number_of_vertices(), output.number_of_faces()) != (
        estimate["estimated_output_vertices"], estimate["estimated_output_faces"],
    ):
        raise ValueError("COMPAS quad subdivision counts differ from the exact estimate.")
    _require_supported_mesh(output, nonplanar_policy)
    if any(len(output.face_vertices(face)) != 4 for face in output.faces()):
        raise ValueError("COMPAS quad subdivision returned a non-quad face.")
    lineage = _recover_lineage(mesh, output)
    problems = validate_lineage_coverage(mesh, output, lineage)
    if problems:
        raise ValueError("Incomplete subdivision lineage: " + " ".join(problems))
    return SubdivisionResult(
        mesh=output, lineage=lineage, operator="quad_subdivision", backend="COMPAS",
        backend_version=compas.__version__, levels=1,
        input_vertices=estimate["input_vertices"], input_faces=estimate["input_faces"],
        estimated_output_vertices=estimate["estimated_output_vertices"],
        estimated_output_faces=estimate["estimated_output_faces"],
        output_vertices=output.number_of_vertices(), output_faces=output.number_of_faces(),
        topology_changed=True,
        nonplanar_policy=nonplanar_policy,
    )


def _require_supported_mesh(mesh, nonplanar_policy="reject"):
    if nonplanar_policy not in ("reject", "bilinear"):
        raise ValueError("nonplanar_policy must be 'reject' or 'bilinear'.")
    if not isinstance(mesh, Mesh):
        raise ValueError("Quad subdivision requires a COMPAS Mesh.")
    try:
        problems = validate_mesh(mesh)
        if problems:
            raise ValueError("Invalid subdivision mesh: " + " ".join(problems))
        if not mesh.is_valid():
            raise ValueError("Invalid connectivity or inconsistent face orientation; no repair performed.")
        incident = {key: set() for key in mesh.vertices()}
        edges = {}
        for face in mesh.faces():
            keys = mesh.face_vertices(face)
            if len(keys) not in (3, 4):
                raise ValueError(f"Unsupported face size at {face!r}; only triangles and quads are supported.")
            if len(set(keys)) != len(keys) or any(key not in incident for key in keys):
                raise ValueError(f"Invalid connectivity at face {face!r}.")
            _require_supported_face(mesh.face_coordinates(face), face, nonplanar_policy)
            for u, v in mesh.face_halfedges(face):
                incident[u].add(face)
                edges.setdefault(frozenset((u, v)), []).append((face, u, v))
        # Explicit incidence and connected vertex fans also catch closed
        # disconnected fans that COMPAS is_manifold() alone can overlook.
        fans = {key: {face: set() for face in faces} for key, faces in incident.items()}
        for edge, entries in edges.items():
            if len(entries) > 2:
                raise ValueError("Unsupported non-manifold edge topology.")
            if len(entries) == 2:
                (a, u, v), (b, x, y) = entries
                if (u, v) != (y, x):
                    raise ValueError("Inconsistent face orientation at a shared edge.")
                for key in edge:
                    fans[key][a].add(b)
                    fans[key][b].add(a)
            else:
                _, u, v = entries[0]
                if mesh.halfedge[v][u] is not None:
                    raise ValueError("Invalid boundary halfedge connectivity.")
        if set(edges) != {frozenset(edge) for edge in mesh.edges()}:
            raise ValueError("Invalid connectivity: halfedges include edges absent from faces.")
        for key, graph in fans.items():
            if not graph:
                raise ValueError(f"Unsupported isolated vertex {key!r}.")
            pending, visited = [next(iter(graph))], set()
            while pending:
                face = pending.pop()
                if face not in visited:
                    visited.add(face)
                    pending.extend(graph[face] - visited)
            if visited != incident[key]:
                raise ValueError(f"Unsupported non-manifold vertex fan at {key!r}.")
    except (KeyError, TypeError, IndexError, ZeroDivisionError, OverflowError) as error:
        raise ValueError("Invalid subdivision geometry or connectivity; no repair performed.") from error


def _local_face(points):
    origin = points[0]
    offsets = [[value - base for value, base in zip(point, origin)] for point in points]
    scale = max(hypot(*offset) for offset in offsets)
    if not isfinite(scale) or scale == 0:
        raise ValueError("Degenerate or unrepresentable face extent.")
    return [[value / scale for value in offset] for offset in offsets], scale


def _require_supported_face(points, face, nonplanar_policy="reject"):
    local, _ = _local_face(points)
    normals = []
    for i in range(len(local)):
        a, b, c = local[i - 1], local[i], local[(i + 1) % len(local)]
        ab = [x - y for x, y in zip(a, b)]
        cb = [x - y for x, y in zip(c, b)]
        normal = cross_vectors(ab, cb)
        if min(hypot(*ab), hypot(*cb), hypot(*normal)) <= GEOMETRY_TOLERANCE:
            raise ValueError(f"Degenerate or nearly collinear face {face!r}.")
        normals.append(normal)
    if len(local) == 4 and nonplanar_policy == "bilinear":
        _require_bilinear_quad(local, face)
        return
    if any(distance_point_plane(point, (local[0], normals[0])) > GEOMETRY_TOLERANCE for point in local):
        raise ValueError(f"Nonplanar face {face!r}; relative tolerance is {GEOMETRY_TOLERANCE:g}.")
    if not is_polygon_convex(local):
        raise ValueError(f"Concave or self-crossing face {face!r} is unsupported.")


def _require_bilinear_quad(local, face):
    """Conservative local regularity, not global intersection certification.

    Ordered corners are P(0,0), P(1,0), P(1,1), P(0,1). After the existing
    local translation/scaling, write P=a*u+b*v+c*u*v (P(0,0)=0).
    J=(a+v*c) x (b+u*c)=a x b+u*(a x c)+v*(c x b).
    J and its projection on a fixed reference normal are affine in (u,v).
    Thus corner projections bound the entire unit square; strictly positive
    projections above 1e-9 exclude local singularities and orientation flips.
    A center Jacobian supplies the unit reference without a world-axis bias.
    """
    a, b = local[1], local[3]
    c = [local[2][i] - a[i] - b[i] for i in range(3)]

    def jacobian(u, v):
        du = [a[i] + v * c[i] for i in range(3)]
        dv = [b[i] + u * c[i] for i in range(3)]
        return cross_vectors(du, dv)

    center = jacobian(0.5, 0.5)
    magnitude = hypot(*center)
    if not isfinite(magnitude) or magnitude <= GEOMETRY_TOLERANCE:
        raise ValueError(f"Singular or near-degenerate bilinear face {face!r}.")
    reference = [value / magnitude for value in center]
    projections = [sum(value * axis for value, axis in zip(jacobian(u, v), reference))
                   for u, v in ((0, 0), (1, 0), (1, 1), (0, 1))]
    if any(not isfinite(value) or value <= GEOMETRY_TOLERANCE for value in projections):
        raise ValueError(
            f"Folded, singular, or unsupported bilinear face {face!r}; "
            f"corner Jacobian projection must exceed {GEOMETRY_TOLERANCE:g}."
        )


def _recover_lineage(source, output):
    originals = set(source.vertices())
    if not originals <= set(output.vertices()):
        raise ValueError("COMPAS did not retain original vertex keys.")
    for key in source.vertices():
        if output.vertex_coordinates(key) != source.vertex_coordinates(key):
            raise ValueError("COMPAS moved a retained original vertex.")
    edges = {frozenset(edge): edge for edge in source.edges()}
    midpoints, centers, seen_corners, face_parents = {}, {}, set(), {}
    for child in output.faces():
        path = output.face_attribute(child, "path")
        if not isinstance(path, list) or len(path) != 2:
            raise ValueError(f"Missing or invalid COMPAS child path at face {child!r}.")
        try:
            parent_exists = path[0] in source.face
        except TypeError as error:
            raise ValueError(f"Invalid COMPAS parent-face key in child path at {child!r}.") from error
        if not parent_exists:
            raise ValueError(f"Invalid COMPAS parent-face key in child path at {child!r}.")
        parent, corner = path
        vertices = source.face_vertices(parent)
        if type(corner) is not int or not 0 <= corner < len(vertices) or (parent, corner) in seen_corners:
            raise ValueError("Ambiguous COMPAS child path/corner metadata.")
        seen_corners.add((parent, corner))
        quad = output.face_vertices(child)
        original = vertices[corner]
        if [key for key in quad if key in originals] != [original]:
            raise ValueError("Child path does not match retained-corner connectivity.")
        position = quad.index(original)
        for candidate, edge in (
            (quad[(position - 1) % 4], frozenset((vertices[corner - 1], original))),
            (quad[(position + 1) % 4], frozenset((original, vertices[(corner + 1) % len(vertices)]))),
        ):
            if edge not in edges or (edge in midpoints and midpoints[edge] != candidate):
                raise ValueError("Ambiguous or inconsistent shared-edge midpoint lineage.")
            midpoints[edge] = candidate
        center = quad[(position + 2) % 4]
        if parent in centers and centers[parent] != center:
            raise ValueError("Ambiguous face-center lineage.")
        centers[parent] = center
        face_parents[child] = [ParentRef(parent, 1)]
    expected_corners = {(face, i) for face in source.faces() for i in range(len(source.face_vertices(face)))}
    if seen_corners != expected_corners or set(midpoints) != set(edges) or set(centers) != set(source.faces()):
        raise ValueError("Incomplete COMPAS corner/edge/face lineage.")
    vertex_parents = {key: [ParentRef(key, 1)] for key in source.vertices()}
    for edge, candidate in midpoints.items():
        u, v = edges[edge]
        _assign_vertex(vertex_parents, candidate, [ParentRef(u, 0.5), ParentRef(v, 0.5)])
        _verify_position(output.vertex_coordinates(candidate), source.edge_point((u, v)), dist(*source.edge_coordinates((u, v))))
    for face, candidate in centers.items():
        vertices = source.face_vertices(face)
        _assign_vertex(vertex_parents, candidate, [ParentRef(key, 1 / len(vertices)) for key in vertices])
        _, scale = _local_face(source.face_coordinates(face))
        _verify_position(output.vertex_coordinates(candidate), source.face_centroid(face), scale)
    # Return children in output order, without assuming generated key ranges.
    if set(vertex_parents) != set(output.vertices()):
        raise ValueError("Incomplete output vertex lineage.")
    return LineageMap({key: vertex_parents[key] for key in output.vertices()}, face_parents)


def _assign_vertex(mapping, child, refs):
    if child in mapping:
        raise ValueError("Ambiguous output vertex lineage: multiple vertex roles or parents.")
    mapping[child] = refs


def _verify_position(actual, expected, scale):
    # Coordinates verify already-recovered topology; they never identify parents.
    if not all(isfinite(value) for value in expected) or dist(actual, expected) > GEOMETRY_TOLERANCE * scale:
        raise ValueError("COMPAS vertex position disagrees with recovered midpoint/centroid lineage.")
