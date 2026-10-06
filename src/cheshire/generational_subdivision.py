"""Opt-in Hansmeyer equation (4); Task 14's operator stays unchanged."""
from collections import Counter
from dataclasses import dataclass
from math import isfinite
from time import perf_counter

from compas.datastructures import Mesh

from .validation import inspect_mesh
from .weighted_subdivision import STANDARD, _extrude, weighted_subdivide_once

VERTEX_DERIVED = "VERTEX_DERIVED"
EDGE_DERIVED = "EDGE_DERIVED"
FACE_DERIVED = "FACE_DERIVED"
ORIGIN_CLASSES = {"corner": VERTEX_DERIVED, "edge": EDGE_DERIVED, "face": FACE_DERIVED}


@dataclass(frozen=True)
class GenerationalResult:
    mesh: Mesh
    metadata: dict
    sampling_parents: dict
    origin_lineage: dict


def classify_child_quad(mesh, face, origin_lineage, generation):
    """Return canonical V/F/E/E IDs or an explicit reason; never use XYZ.

    Classes refer to the immediately preceding call. Parent-edge incidence
    and the recorded parent-face cycle verify that these form a real corner
    child, rather than accepting four arbitrary labels with the right counts.
    Edge order is by ID; the equation is symmetric in these two edge points.
    """
    vertices = mesh.face_vertices(face)
    if len(vertices) != 4:
        return None, "not_quad"
    if generation == 0:
        return None, "first_generation_no_previous_origins"
    origins = origin_lineage or {}
    if any(v not in origins for v in vertices):
        return None, "missing_origin"
    rows = [origins[v] for v in vertices]
    if any(not isinstance(row, dict) or type(row.get("generation")) is not int or row["generation"] != generation for row in rows):
        return None, "origin_generation_mismatch"
    if any(not isinstance(row.get("class"), str) for row in rows) or Counter(row.get("class") for row in rows) != {VERTEX_DERIVED: 1, FACE_DERIVED: 1, EDGE_DERIVED: 2}:
        return None, "origin_class_pattern"
    v = next(k for k in vertices if origins[k]["class"] == VERTEX_DERIVED)
    f = next(k for k in vertices if origins[k]["class"] == FACE_DERIVED)
    edges = sorted(k for k in vertices if origins[k]["class"] == EDGE_DERIVED)
    if vertices[(vertices.index(v)+2) % 4] != f:
        return None, "V_and_F_not_opposite"
    corner = origins[v].get("source")
    cycle = origins[f].get("source_vertices")
    if type(corner) is not int or not isinstance(cycle, list) or len(cycle) not in (3, 4) or any(type(k) is not int for k in cycle) or len(set(cycle)) != len(cycle) or corner not in cycle:
        return None, "parent_face_incidence_missing"
    index = cycle.index(corner)
    expected = {frozenset((corner, cycle[(index-1) % len(cycle)])),
                frozenset((corner, cycle[(index+1) % len(cycle)]))}
    actual = []
    for e in edges:
        source = origins[e].get("source")
        if not isinstance(source, list) or len(source) != 2 or any(type(k) is not int for k in source) or source[0] == source[1]:
            return None, "parent_edge_incidence_missing"
        actual.append(frozenset(source))
    if len(set(actual)) != 2 or set(actual) != expected:
        return None, "parent_edge_incidence_mismatch"
    return dict(V=v, F=f, E1=edges[0], E2=edges[1]), None


def later_generation_face_stencil(V, F, E1, E2, normal, *, w3, w4, wf):
    """Equation (4), using actual input XYZ and the unchanged wf extrusion.

    Paper wf corresponds to task notation w10; w3/w4 are dimensionless.
    Geometry coefficients may be negative; sampling/semantic weights stay
    separate. The zero-regression fast path is in the caller, not this formula.
    """
    point = [((V[i]*(1+w3) + F[i]*(1-w3))*(1+w4)
              + (E1[i]+E2[i])*(1-w4))/4 for i in range(3)]
    return _extrude(point, normal, wf)


def generational_subdivide_once(mesh, weights=None, *, origin_lineage=None,
                               point_weights=None, budget=None, current_generation=0):
    """Task 14 topology/edge/corner rules plus opt-in later face stencil.

    Every output point receives a new generation-local origin record and
    mesh attributes. Bad/missing quad ancestry falls back to Task 14, with
    a per-face reason. With both new weights zero, original face placement
    is retained exactly, including arithmetic summation order.
    """
    started = perf_counter()
    values = {**STANDARD, "w3": 0.0, "w4": 0.0}
    if weights is not None:
        if not isinstance(weights, dict) or set(weights)-set(values):
            raise ValueError("Unknown generational-subdivision parameter.")
        if any(type(w) not in (int, float) or not isfinite(w) for w in weights.values()):
            raise ValueError("Generational weights must be finite real numbers.")
        values.update(weights)
    base = weighted_subdivide_once(mesh, {k: values[k] for k in STANDARD},
        point_weights=point_weights, budget=budget, current_generation=current_generation)
    w3, w4 = values["w3"], values["w4"]
    fallbacks, applications, origins = [], [], {}
    for point in base.metadata["points"]:
        key, kind, source = point["id"], point["point_class"], point["source"]
        origin = dict(class_=ORIGIN_CLASSES[kind], generation=current_generation+1, source=source)
        origin["class"] = origin.pop("class_")
        if kind == "face":
            origin["source_vertices"] = mesh.face_vertices(source)
            pattern, reason = classify_child_quad(mesh, source, origin_lineage, current_generation)
            if pattern is None:
                fallbacks.append(dict(face=source, point=key, reason=reason))
            else:
                coefficients = dict(V=(1+w3)*(1+w4)/4, F=(1-w3)*(1+w4)/4,
                                    E1=(1-w4)/4, E2=(1-w4)/4)
                if w3 != 0 or w4 != 0:
                    xyz = later_generation_face_stencil(*(mesh.vertex_coordinates(pattern[k]) for k in ("V", "F", "E1", "E2")),
                        mesh.face_normal(source), w3=w3, w4=w4, wf=point["weights"]["wf"])
                    if not all(isfinite(x) for x in xyz):
                        raise ValueError("Later-generation face stencil produced non-finite geometry.")
                    base.mesh.vertex_attributes(key, "xyz", xyz)
                applications.append(dict(face=source, point=key, canonical=pattern, w3=w3, w4=w4,
                    wf=point["weights"]["wf"], geometry_coefficients=coefficients,
                    zero_weight_exact_path=w3 == 0 and w4 == 0))
        origins[key] = origin
        base.mesh.vertex_attribute(key, "origin_class", origin["class"])
        base.mesh.vertex_attribute(key, "origin_generation", current_generation+1)
    metadata = {**base.metadata, "name": "CHESHIRE opt-in later-generation face stencil",
        "backend_before_face_stencil_output": base.metadata["output"], "output": inspect_mesh(base.mesh),
        "equations_1_2_3": "Unchanged Task 14; only eligible face positions use equation 4",
        "later_generation_face_stencil": dict(w3=w3,w4=w4,eligible_faces=len(applications),fallback_faces=len(fallbacks),
            fallback_counts=dict(Counter(row["reason"] for row in fallbacks)),fallbacks=fallbacks,applications=applications),
        "origin_classes": dict(Counter(row["class"] for row in origins.values())),
        "elapsed_seconds": perf_counter()-started}
    return GenerationalResult(base.mesh, metadata, base.sampling_parents, origins)
