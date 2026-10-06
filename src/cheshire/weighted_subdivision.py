"""CHESHIRE Extended-CC Experimental Subset; see the reference note.

Public COMPAS supplies topology. Input stencils supply geometry; sampling
associations are explicitly separate from semantic/geometric coefficients.
"""
from dataclasses import dataclass
from math import dist, fsum, hypot, isfinite
from time import perf_counter

from compas.datastructures import Mesh

from .execution import ExecutionBudget, check_execution_budget
from .validation import inspect_mesh, validate_mesh


STANDARD = dict(wf=0.0, w1=0.0, we=0.0, w2=0.0, wp=0.0)
PARAMETERS = {"face": ("wf",), "edge": ("w1", "we"), "corner": ("w2", "wp")}


@dataclass(frozen=True)
class WeightedResult:
    mesh: Mesh
    metadata: dict
    sampling_parents: dict


def mean(points):
    points = list(points)
    return [fsum(p[i] for p in points) / len(points) for i in range(3)]


def _extrude(point, normal, amount):
    if amount and hypot(*normal) == 0:
        raise ValueError("Nonzero extrusion has an undefined/cancelling normal.")
    return [p + amount * n for p, n in zip(point, normal)]


def _weights(values, allowed):
    if not isinstance(values, dict) or set(values) - set(allowed):
        raise ValueError("Unknown weighted-subdivision parameter.")
    if any(type(v) not in (int, float) or not isfinite(v) for v in values.values()):
        raise ValueError("Weights must be finite real numbers.")
    return values


def weighted_subdivide_once(mesh, weights=None, *, point_weights=None,
                            budget=None, current_generation=0):
    """Return a fresh mesh and exact point records; never repair geometry.

    Global weights default to zero. Optional point overrides are keyed by
    original face ID, original edge tuple (either orientation), or vertex ID.
    Boundary suppression is recorded in effective, rather than requested,
    weights. A count/generation block occurs before subdivision or copying.
    """
    start = perf_counter()
    budget = budget or ExecutionBudget(50000, 50000)
    before = inspect_mesh(mesh)
    estimate = dict(estimated_output_vertices=before["vertex_count"] + before["edge_count"] + before["face_count"],
                    estimated_output_faces=sum(len(mesh.face_vertices(f)) for f in mesh.faces()))
    assessment = {**estimate, **check_execution_budget(budget,
        input_vertices=before["vertex_count"], input_faces=before["face_count"],
        current_generation=current_generation, **estimate)}
    if assessment["status"] != "SAFE":
        raise ValueError("Weighted subdivision blocked: " + " ".join(assessment["reasons"]))
    problems = validate_mesh(mesh)
    if problems or not mesh.is_valid() or not mesh.is_manifold():
        raise ValueError("Requires finite, nonempty, valid manifold input: " + " ".join(problems))
    if any(len(mesh.face_vertices(f)) not in (3, 4) for f in mesh.faces()) or any(mesh.vertex_degree(v) == 0 for v in mesh.vertices()):
        raise ValueError("Only triangle/quad input without isolated vertices is supported.")
    if any(mesh.edge_attribute(e, "crease") for e in mesh.edges() if not mesh.is_edge_on_boundary(e)):
        raise ValueError("Interior crease semantics are unsupported by this experimental subset.")
    global_weights = {**STANDARD, **_weights(weights or {}, STANDARD)}
    overrides = point_weights or {}
    if set(overrides) - set(PARAMETERS):
        raise ValueError("Unknown generated point class.")
    edges = list(mesh.edges())
    known = {"face": set(mesh.faces()), "corner": set(mesh.vertices()),
             "edge": {tuple(sorted(e)) for e in edges}}
    prepared = {}
    for kind, rows in overrides.items():
        prepared[kind] = {}
        for key, values in rows.items():
            key = tuple(sorted(key)) if kind == "edge" else key
            if key not in known[kind] or key in prepared[kind]:
                raise ValueError("Unknown/duplicate source point override.")
            prepared[kind][key] = _weights(values, PARAMETERS[kind])
    xyz = {v: mesh.vertex_coordinates(v) for v in mesh.vertices()}
    centres = {f: mean(xyz[v] for v in mesh.face_vertices(f)) for f in mesh.faces()}
    normals = {f: list(mesh.face_normal(f)) for f in mesh.faces()}
    if any(not all(isfinite(x) for x in n) for n in normals.values()):
        raise ValueError("Undefined input face normal.")
    boundary = {tuple(sorted(e)) for e in edges if mesh.is_edge_on_boundary(e)}
    fixed = {v for e in boundary for v in e}
    cage = Mesh()
    for v, p in xyz.items():
        cage.add_vertex(key=v, x=p[0], y=p[1], z=p[2])
    for f in mesh.faces():
        cage.add_face(mesh.face_vertices(f), fkey=f)
    for e in boundary:
        cage.edge_attribute(e, "crease", 2)
    output = cage.subdivided(scheme="catmullclark", k=1, fixed=sorted(fixed))
    # Verify structural correspondence; no coordinate proximity or assumed IDs.
    originals = set(xyz)
    edge_ids = {}
    for u, v in edges:
        children = (set(output.vertex_neighbors(u)) & set(output.vertex_neighbors(v))) - originals
        if len(children) != 1:
            raise ValueError("COMPAS edge-point correspondence is ambiguous.")
        edge_ids[tuple(sorted((u, v)))] = children.pop()
    signatures = {frozenset(edge_ids[tuple(sorted(e))] for e in mesh.face_halfedges(f)): f for f in mesh.faces()}
    if len(signatures) != mesh.number_of_faces():
        raise ValueError("Duplicate face edge cycles are unsupported.")
    face_ids = {}
    for child in set(output.vertices()) - originals - set(edge_ids.values()):
        parent = signatures.get(frozenset(output.vertex_neighbors(child)))
        if parent is None or parent in face_ids:
            raise ValueError("COMPAS face-point correspondence is ambiguous.")
        face_ids[parent] = child
    records, sampling = [], {}

    def place(kind, key, child, point, normal, amount_name, boundary_point=False):
        used = {p: global_weights[p] for p in PARAMETERS[kind]}
        used.update(prepared.get(kind, {}).get(key, {}))
        requested = used.copy()
        if boundary_point:
            used = {p: 0.0 for p in used}
        point = point(used) if callable(point) else point
        point = _extrude(point, normal, used[amount_name])
        if not all(isfinite(p) for p in point):
            raise ValueError("Weighted point placement produced non-finite coordinates.")
        output.vertex_attributes(child, "xyz", point)
        records.append(dict(id=child, point_class=kind, source=list(key) if isinstance(key, tuple) else key,
                            requested_weights=requested, weights=used, boundary=boundary_point))

    for f, child in face_ids.items():
        place("face", f, child, centres[f], normals[f], "wf")
        vertices = mesh.face_vertices(f)
        sampling[child] = [(v, 1 / len(vertices)) for v in vertices]
    for (u, v), child in edge_ids.items():
        faces = [f for f in (mesh.halfedge[u][v], mesh.halfedge[v][u]) if f is not None]
        on_boundary = (u, v) in boundary
        def edge_point(w):
            if on_boundary:
                return mean([xyz[u], xyz[v]])
            a, b = faces
            return [((centres[a][i] + centres[b][i]) * (1+w["w1"]) +
                     (xyz[u][i] + xyz[v][i]) * (1-w["w1"])) / 4 for i in range(3)]
        place("edge", (u, v), child, edge_point, mean(normals[f] for f in faces), "we", on_boundary)
        sampling[child] = [(u, 0.5), (v, 0.5)]
    for v in mesh.vertices():
        faces = mesh.vertex_faces(v)
        neighbours = mesh.vertex_neighbors(v)
        n = len(neighbours)
        F = mean(centres[f] for f in faces)
        E = mean(mean([xyz[v], xyz[u]]) for u in neighbours)
        normal = mean(normals[f] for f in faces)
        length = hypot(*normal)
        normal = [x / length for x in normal] if length else [0.0] * 3
        def corner_point(w):
            return xyz[v] if v in fixed else [(F[i]*(1+w["w2"]) + E[i]*(2-w["w2"]) + xyz[v][i]*(n-3))/n for i in range(3)]
        place("corner", v, v, corner_point, normal, "wp", v in fixed)
        sampling[v] = [(v, 1.0)]
    face_sources = []
    reverse_faces = {child: parent for parent, child in face_ids.items()}
    face_point_keys = set(reverse_faces)
    for f in output.faces():
        corners = output.face_vertices(f)
        parent_points = set(corners) & face_point_keys
        old_corners = set(corners) & originals
        if len(parent_points) != 1 or len(old_corners) != 1:
            raise ValueError("Unexpected COMPAS child face cycle.")
        face_sources.append(dict(id=f, source_face=reverse_faces[parent_points.pop()], source_corner=old_corners.pop()))
    after = inspect_mesh(output)
    components = len(mesh.connected_vertices())
    if after["vertex_count"] != estimate["estimated_output_vertices"] or after["face_count"] != estimate["estimated_output_faces"] or not output.is_valid() or not output.is_manifold():
        raise ValueError("Unexpected subdivision counts/connectivity.")
    if len(output.connected_vertices()) != components or after["boundary_edge_count"] != 2*len(boundary):
        raise ValueError("Subdivision changed components or boundary connectivity.")
    return WeightedResult(output, dict(name="CHESHIRE Extended-CC Experimental Subset", generation=current_generation+1,
        backend="COMPAS 2.15.1 Mesh.subdivided topology", semantic_lineage="NOT IMPLEMENTED",
        source_association="immediate topology; positive control-cage sampling only",
        boundary_policy="fixed naked corners, exact naked-edge midpoints, zero boundary extrusion",
        input=before, output=after, components_before=components, components_after=components,
        budget=assessment, points=records, face_sources=face_sources,
        elapsed_seconds=perf_counter()-start), sampling)


def local_lengths(mesh):
    """Current incident mean edge lengths, in coordinate units (study scaling)."""
    return {
        "face": {f: fsum(dist(mesh.vertex_coordinates(u), mesh.vertex_coordinates(v)) for u, v in mesh.face_halfedges(f)) / len(mesh.face_vertices(f)) for f in mesh.faces()},
        "edge": {tuple(sorted((u, v))): dist(mesh.vertex_coordinates(u), mesh.vertex_coordinates(v)) for u, v in mesh.edges()},
        "corner": {v: fsum(dist(mesh.vertex_coordinates(v), mesh.vertex_coordinates(u)) for u in mesh.vertex_neighbors(v)) / mesh.vertex_degree(v) for v in mesh.vertices()},
    }
