from copy import deepcopy
from dataclasses import fields as dataclass_fields
import json
from math import isfinite
from unittest.mock import Mock

import compas
from compas.datastructures import Mesh
from compas.geometry import Box, Frame
import pytest

from cheshire import (
    ExecutionBudget, FieldSpec, LineageMap, ParentRef, SubdivisionResult,
    analyze_vertex_attributes, estimate_quad_subdivision, inherit_fields,
    subdivide_quad_once, validate_lineage_coverage,
)
import cheshire.subdivision as adapter


@pytest.fixture
def triangle():
    return Mesh.from_vertices_and_faces([[0, 0, 0], [2, 0, 0], [0, 3, 0]], [[0, 1, 2]])


@pytest.fixture
def adjacent_quads():
    return Mesh.from_vertices_and_faces(
        [[0, 0, 0], [1, 0, 0], [2, 0, 0], [0, 1, 0], [1, 1, 0], [2, 1, 0]],
        [[0, 1, 4, 3], [1, 2, 5, 4]],
    )


@pytest.fixture
def mixed_mesh():
    return Mesh.from_vertices_and_faces(
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [2, 0, 0]],
        [[0, 1, 2, 3], [1, 4, 2]],
    )


def _run(mesh, **kwargs):
    return subdivide_quad_once(mesh, budget=ExecutionBudget(10_000, max_vertices=10_000), **kwargs)


def _metadata(result):
    return {field.name: getattr(result, field.name) for field in dataclass_fields(result) if field.name not in ("mesh", "lineage")}


def _vertex_with_parents(result, parents):
    matches = [key for key, refs in result.lineage.vertex_parents.items() if {ref.key for ref in refs} == set(parents)]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.parametrize("fixture,vertices,faces,triangles,quads", [
    ("triangle", 7, 3, 1, 0), ("open_mesh", 9, 4, 0, 1),
    ("adjacent_quads", 15, 8, 0, 2), ("mixed_mesh", 13, 7, 1, 1),
    ("box_mesh", 26, 24, 0, 6),
])
def test_verified_native_counts_and_metadata(fixture, vertices, faces, triangles, quads, request):
    mesh = request.getfixturevalue(fixture)
    estimate = estimate_quad_subdivision(mesh)
    before = json.dumps(mesh.__data__, sort_keys=True, allow_nan=False)
    result = _run(mesh)
    assert isinstance(result, SubdivisionResult)
    assert isinstance(result.mesh, Mesh) and result.mesh is not mesh
    assert estimate["triangle_count"] == triangles and estimate["quad_count"] == quads
    assert estimate["estimated_output_vertices"] == vertices == result.estimated_output_vertices == result.output_vertices
    assert estimate["estimated_output_faces"] == faces == result.estimated_output_faces == result.output_faces
    assert result.input_vertices == mesh.number_of_vertices() and result.input_faces == mesh.number_of_faces()
    assert result.operator == "quad_subdivision" and result.backend == "COMPAS"
    assert result.backend_version == compas.__version__ == "2.15.1" and result.levels == 1
    assert result.topology_changed
    assert all(len(result.mesh.face_vertices(face)) == 4 for face in result.mesh.faces())
    assert result.mesh.is_valid() and result.mesh.is_manifold()
    assert result.mesh.is_closed() == mesh.is_closed()
    assert validate_lineage_coverage(mesh, result.mesh, result.lineage) == []
    assert all(result.mesh.vertex_coordinates(key) == mesh.vertex_coordinates(key) for key in mesh.vertices())
    assert all(isfinite(value) for key in result.mesh.vertices() for value in result.mesh.vertex_coordinates(key))
    assert json.dumps(mesh.__data__, sort_keys=True, allow_nan=False) == before


@pytest.mark.parametrize("fixture", ["triangle", "open_mesh", "adjacent_quads", "mixed_mesh", "box_mesh"])
def test_identity_midpoint_center_and_child_face_lineage(fixture, request):
    mesh = request.getfixturevalue(fixture)
    result = _run(mesh)
    for key in mesh.vertices():
        assert result.lineage.vertex_parents[key] == (ParentRef(key, 1),)
    for edge in mesh.edges():
        midpoint = _vertex_with_parents(result, edge)
        refs = result.lineage.vertex_parents[midpoint]
        assert {ref.key for ref in refs} == set(edge)
        assert [ref.weight for ref in refs] == [0.5, 0.5]
        assert result.mesh.vertex_coordinates(midpoint) == pytest.approx(mesh.edge_point(edge))
    for parent in mesh.faces():
        vertices = mesh.face_vertices(parent)
        center = _vertex_with_parents(result, vertices)
        assert result.lineage.vertex_parents[center] == tuple(ParentRef(key, 1 / len(vertices)) for key in vertices)
        assert result.mesh.vertex_coordinates(center) == pytest.approx(mesh.face_centroid(parent))
        children = [key for key, refs in result.lineage.face_parents.items() if refs == (ParentRef(parent, 1),)]
        assert len(children) == len(vertices)
        for child in children:
            path = result.mesh.face_attribute(child, "path")
            assert path[0] == parent and vertices[path[1]] in result.mesh.face_vertices(child)
            assert center in result.mesh.face_vertices(child)


def test_adjacent_quads_share_one_common_edge_midpoint(adjacent_quads):
    result = _run(adjacent_quads)
    midpoint = _vertex_with_parents(result, (1, 4))
    assert set(result.mesh.vertex_neighbors(1)) & set(result.mesh.vertex_neighbors(4)) == {midpoint}
    child_parents = {result.lineage.face_parents[key][0].key for key in result.mesh.vertex_faces(midpoint)}
    assert child_parents == {0, 1}


def test_irregular_quad_uses_vertex_mean_not_polygon_area_center():
    mesh = Mesh.from_vertices_and_faces([[0, 0, 0], [3, 0, 0], [2, 2, 0], [0, 1, 0]], [[0, 1, 2, 3]])
    assert mesh.face_centroid(0) != mesh.face_center(0)
    result = _run(mesh)
    center = _vertex_with_parents(result, (0, 1, 2, 3))
    assert result.mesh.vertex_coordinates(center) == pytest.approx([1.25, 0.75, 0])


@pytest.mark.parametrize("fixture", ["triangle", "open_mesh", "adjacent_quads", "mixed_mesh"])
def test_planar_shape_area_and_extent_are_preserved(fixture, request):
    mesh = request.getfixturevalue(fixture)
    result = _run(mesh)
    assert sum(mesh.face_area(face) for face in mesh.faces()) == pytest.approx(sum(result.mesh.face_area(face) for face in result.mesh.faces()))
    assert all(result.mesh.vertex_coordinates(key)[2] == 0 for key in result.mesh.vertices())
    assert result.mesh.aabb().__data__ == mesh.aabb().__data__


def test_rotated_planar_surface_is_supported(open_mesh):
    open_mesh.transform(Frame([10, -5, 2], [1, 1, 0], [0, 0, 1]).to_transformation())
    result = _run(open_mesh)
    assert sum(result.mesh.face_area(face) for face in result.mesh.faces()) == pytest.approx(open_mesh.face_area(0))


def test_sparse_keys_and_reversed_key_insertion_are_not_array_indices():
    mesh = Mesh()
    for key, xyz in [(900, [0, 0, 0]), (10, [2, 0, 0]), (77, [2, 3, 0]), (-4, [0, 3, 0])]:
        mesh.add_vertex(key=key, x=xyz[0], y=xyz[1], z=xyz[2])
    mesh.add_face([900, 10, 77, -4], fkey=800)
    result = _run(mesh)
    assert set(mesh.vertices()) <= set(result.mesh.vertices())
    assert all(refs == (ParentRef(800, 1),) for refs in result.lineage.face_parents.values())
    assert _vertex_with_parents(result, [900, 10]) not in mesh.vertex
    assert validate_lineage_coverage(mesh, result.mesh, result.lineage) == []


@pytest.mark.parametrize("coincident", [False, True])
def test_disconnected_components_are_not_welded(coincident):
    shift = 0 if coincident else 10
    mesh = Mesh.from_vertices_and_faces(
        [[0, 0, 0], [2, 0, 0], [2, 2, 0], [0, 2, 0],
         [shift, 0, 0], [shift + 2, 0, 0], [shift + 2, 2, 0], [shift, 2, 0]],
        [[0, 1, 2, 3], [4, 5, 6, 7]],
    )
    result = _run(mesh)
    assert result.output_vertices == 18 and result.output_faces == 8
    assert len(result.mesh.connected_vertices()) == 2
    first = {key for key, refs in result.lineage.vertex_parents.items() if all(ref.key < 4 for ref in refs)}
    second = set(result.mesh.vertices()) - first
    assert len(first) == len(second) == 9
    assert not first & second
    assert all(set(result.mesh.vertex_neighbors(key)) <= first for key in first)
    if coincident:
        assert result.mesh.vertex_coordinates(_vertex_with_parents(result, [0, 1])) == result.mesh.vertex_coordinates(_vertex_with_parents(result, [4, 5]))


def test_all_custom_attributes_are_discarded_only_on_output(open_mesh):
    open_mesh.attributes["custom"] = {"project": "test"}
    open_mesh.default_vertex_attributes["old_curvature"] = 99
    open_mesh.default_face_attributes["label"] = "stale"
    open_mesh.default_edge_attributes["old_length"] = 9
    open_mesh.vertex_attribute(0, "external", {"nested": [1, 2]})
    open_mesh.face_attribute(0, "path", ["prior", "history"])
    open_mesh.face_attribute(0, "semantic", "support")
    open_mesh.edge_attribute((0, 1), "custom", 3)
    before = json.dumps(open_mesh.__data__, sort_keys=True, allow_nan=False)
    result = _run(open_mesh)
    assert json.dumps(open_mesh.__data__, sort_keys=True, allow_nan=False) == before
    assert "custom" not in result.mesh.attributes
    assert set(result.mesh.default_vertex_attributes) == {"x", "y", "z"}
    assert result.mesh.default_face_attributes == result.mesh.default_edge_attributes == {}
    assert all(set(result.mesh.vertex_attributes(key)) == {"x", "y", "z"} for key in result.mesh.vertices())
    assert all(set(result.mesh.face_attributes(key)) == {"path"} for key in result.mesh.faces())
    result.mesh.vertex_attribute(0, "x", 999)
    assert json.dumps(open_mesh.__data__, sort_keys=True, allow_nan=False) == before


def test_continuous_face_and_vertex_and_categorical_inheritance(adjacent_quads):
    mesh = adjacent_quads
    mesh_before = json.dumps(mesh.__data__, sort_keys=True, allow_nan=False)
    result = _run(mesh)
    output_before = json.dumps(result.mesh.__data__, sort_keys=True, allow_nan=False)
    sources = {"confidence": {0: 0.2, 1: 0.8, 2: 0.6, 3: 0.4, 4: 0.5, 5: 0.9},
               "part_type": {0: "support", 1: "lintel"}, "conflict": {0: 0.8, 1: 0.1}}
    before = deepcopy(sources)
    lineage_before = (dict(result.lineage.vertex_parents), dict(result.lineage.face_parents))
    specs = [FieldSpec("confidence", "vertex", "scalar", "CONTINUOUS"),
             FieldSpec("part_type", "face", "categorical", "CATEGORICAL"),
             FieldSpec("conflict", "face", "scalar", "CONTINUOUS")]
    inherited = inherit_fields(result.lineage, sources, specs)
    assert all(inherited.values["confidence"][key] == value for key, value in sources["confidence"].items())
    assert inherited.values["confidence"][_vertex_with_parents(result, [0, 1])] == 0.5
    center = _vertex_with_parents(result, [0, 1, 4, 3])
    assert inherited.values["confidence"][center] == pytest.approx((0.2 + 0.8 + 0.5 + 0.4) / 4)
    for child, refs in result.lineage.face_parents.items():
        assert inherited.values["part_type"][child] == sources["part_type"][refs[0].key]
        assert inherited.values["conflict"][child] == sources["conflict"][refs[0].key]
    assert inherited == inherit_fields(result.lineage, sources, specs)
    assert sources == before
    assert (dict(result.lineage.vertex_parents), dict(result.lineage.face_parents)) == lineage_before
    assert json.dumps(mesh.__data__, sort_keys=True, allow_nan=False) == mesh_before
    assert json.dumps(result.mesh.__data__, sort_keys=True, allow_nan=False) == output_before


@pytest.mark.parametrize("fixture", ["triangle", "mixed_mesh", "box_mesh"])
def test_constant_continuous_fields_remain_exactly_constant(fixture, request):
    mesh = request.getfixturevalue(fixture)
    result = _run(mesh)
    specs = [FieldSpec("constant", "vertex", "scalar", "CONTINUOUS")]
    inherited = inherit_fields(result.lineage, {"constant": {key: 0.8 for key in mesh.vertices()}}, specs)
    assert all(value == 0.8 for value in inherited.values["constant"].values())


def test_positive_weight_missing_parent_values_remain_unresolved(triangle):
    result = _run(triangle)
    specs = [FieldSpec("confidence", "vertex", "scalar", "CONTINUOUS")]
    values = inherit_fields(result.lineage, {"confidence": {0: 0.2, 1: 0.8}}, specs).values["confidence"]
    assert values[_vertex_with_parents(result, [0, 1])] == 0.5
    assert values[2] is None
    assert values[_vertex_with_parents(result, [1, 2])] is None
    assert values[_vertex_with_parents(result, [0, 1, 2])] is None


def test_geometry_fields_are_explicitly_recomputed(adjacent_quads):
    before = json.dumps(adjacent_quads.__data__, sort_keys=True, allow_nan=False)
    old = analyze_vertex_attributes(adjacent_quads)
    result = _run(adjacent_quads)
    old_before = deepcopy(old)
    specs = [FieldSpec(name, "vertex", "scalar", "RECOMPUTE") for name in ("valence", "boundary", "approximate_curvature")]
    old_fields = {spec.name: {key: record[spec.name] for key, record in old.items()} for spec in specs}
    inherited = inherit_fields(result.lineage, old_fields, specs)
    assert inherited.values == {}
    assert inherited.recompute_fields == [spec.name for spec in specs]
    new = analyze_vertex_attributes(result.mesh)
    midpoint = _vertex_with_parents(result, [1, 4])
    assert new[midpoint]["valence"] == 4 and not new[midpoint]["boundary"]
    assert new[midpoint]["approximate_curvature"] == 0.0
    assert set(new) == set(result.mesh.vertices()) != set(old)
    assert old == old_before
    assert json.dumps(adjacent_quads.__data__, sort_keys=True, allow_nan=False) == before


@pytest.mark.parametrize("budget,generation,reason", [
    (ExecutionBudget(23, max_vertices=26), 0, "Face budget"),
    (ExecutionBudget(24, max_vertices=25), 0, "Vertex budget"),
    (ExecutionBudget(24, max_vertices=26, max_generation=1), 1, "Generation budget"),
    (ExecutionBudget(24, max_generation=0), 0, "Generation budget"),
])
def test_blocked_budgets_prevent_backend_call(box_mesh, monkeypatch, budget, generation, reason):
    backend = Mock(side_effect=AssertionError("Blocked budget executed the backend"))
    monkeypatch.setattr(Mesh, "subdivided", backend)
    with pytest.raises(ValueError, match=reason):
        subdivide_quad_once(box_mesh, budget=budget, current_generation=generation)
    backend.assert_not_called()


def test_exact_limits_allow_one_native_call(box_mesh, monkeypatch):
    native = Mesh.subdivided
    calls = []

    def spy(mesh, **options):
        calls.append(options)
        return native(mesh, **options)

    monkeypatch.setattr(Mesh, "subdivided", spy)
    result = subdivide_quad_once(box_mesh, budget=ExecutionBudget(24, max_vertices=26, max_generation=2), current_generation=1)
    assert calls == [{"scheme": "quad", "k": 1}]
    assert result.output_faces == 24 and result.output_vertices == 26


@pytest.mark.parametrize("generation", [-1, 1.5, True, None])
def test_invalid_generation_rejected_before_backend(open_mesh, monkeypatch, generation):
    backend = Mock()
    monkeypatch.setattr(Mesh, "subdivided", backend)
    with pytest.raises(ValueError, match="current_generation"):
        subdivide_quad_once(open_mesh, budget=ExecutionBudget(100), current_generation=generation)
    backend.assert_not_called()


def test_invalid_budget_and_partial_selection_are_not_executed(open_mesh, monkeypatch):
    backend = Mock()
    monkeypatch.setattr(Mesh, "subdivided", backend)
    with pytest.raises(ValueError, match="ExecutionBudget"):
        subdivide_quad_once(open_mesh, budget=None)
    with pytest.raises(TypeError):
        subdivide_quad_once(open_mesh, budget=ExecutionBudget(100), selected_faces=[0])
    backend.assert_not_called()


@pytest.mark.parametrize("mesh", [Mesh(), Mesh.from_vertices_and_faces([[0, 0, 0]], []), None])
def test_empty_or_non_mesh_input_rejected(mesh, monkeypatch):
    backend = Mock()
    monkeypatch.setattr(Mesh, "subdivided", backend)
    with pytest.raises(ValueError):
        _run(mesh)
    backend.assert_not_called()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_input_rejected(open_mesh, value, monkeypatch):
    open_mesh.vertex_attribute(0, "x", value)
    backend = Mock()
    monkeypatch.setattr(Mesh, "subdivided", backend)
    with pytest.raises(ValueError, match="non-finite"):
        _run(open_mesh)
    backend.assert_not_called()


@pytest.mark.parametrize("points,faces,message", [
    ([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0.5, 2, 0], [0, 1, 0]], [[0, 1, 2, 3, 4]], "face size"),
    ([[0, 0, 0], [1, 0, 0], [2, 0, 0]], [[0, 1, 2]], "Degenerate"),
    ([[0, 0, 0], [0, 0, 0], [1, 1, 0]], [[0, 1, 2]], "Degenerate"),
    ([[0, 0, 0], [1, 0, 0], [1, 1, 0.1], [0, 1, 0]], [[0, 1, 2, 3]], "Nonplanar"),
    ([[0, 0, 0], [2, 0, 0], [0.3, 0.3, 0], [0, 2, 0]], [[0, 1, 2, 3]], "Concave"),
    ([[0, 0, 0], [1, 1, 0], [0, 1, 0], [1, 0, 0]], [[0, 1, 2, 3]], "Concave"),
])
def test_unsupported_face_geometry_rejected_before_backend(points, faces, message, monkeypatch):
    mesh = Mesh.from_vertices_and_faces(points, faces)
    backend = Mock()
    monkeypatch.setattr(Mesh, "subdivided", backend)
    with pytest.raises(ValueError, match=message):
        _run(mesh)
    backend.assert_not_called()


@pytest.mark.parametrize("scale", [1e-6, 1, 1e6])
def test_nonplanarity_tolerance_scales_with_face_extent(scale):
    mesh = Mesh.from_vertices_and_faces([[0, 0, 0], [scale, 0, 0], [scale, scale, 1e-7 * scale], [0, scale, 0]], [[0, 1, 2, 3]])
    with pytest.raises(ValueError, match="Nonplanar"):
        _run(mesh)


@pytest.mark.parametrize("corrupt", ["missing_vertex", "missing_halfedge", "duplicate_corner"])
def test_invalid_connectivity_is_not_repaired(open_mesh, corrupt):
    if corrupt == "missing_vertex":
        del open_mesh.vertex[0]
    elif corrupt == "missing_halfedge":
        del open_mesh.halfedge[0][1]
    else:
        open_mesh.face[0] = [0, 1, 1, 3]
    with pytest.raises(ValueError, match="connectivity|orientation"):
        _run(open_mesh)


def test_inconsistent_orientation_rejected(adjacent_quads):
    points, faces = adjacent_quads.to_vertices_and_faces()
    faces[1].reverse()
    mesh = Mesh.from_vertices_and_faces(points, faces)
    with pytest.raises(ValueError, match="orientation"):
        _run(mesh)


def test_three_faces_on_edge_rejected():
    mesh = Mesh.from_vertices_and_faces([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1]], [[0, 1, 2], [1, 0, 3], [0, 1, 4]])
    with pytest.raises(ValueError):
        _run(mesh)


def test_disconnected_open_vertex_fans_rejected():
    mesh = Mesh.from_vertices_and_faces([[0, 0, 0], [1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0]], [[0, 1, 2], [0, 3, 4]])
    assert mesh.is_valid()
    with pytest.raises(ValueError, match="non-manifold vertex fan"):
        _run(mesh)


def test_disconnected_closed_vertex_fans_rejected():
    mesh = Mesh.from_vertices_and_faces(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [-1, 0, 0], [0, -1, 0], [0, 0, -1]],
        [[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3], [0, 5, 4], [0, 4, 6], [4, 5, 6], [5, 0, 6]],
    )
    assert mesh.is_valid() and mesh.is_manifold()  # COMPAS alone misses the disconnected closed fan.
    with pytest.raises(ValueError, match="non-manifold vertex fan"):
        _run(mesh)


def test_isolated_vertices_rejected_only_by_operator(open_mesh):
    open_mesh.add_vertex(x=5, y=5, z=5)
    with pytest.raises(ValueError, match="isolated"):
        _run(open_mesh)


@pytest.mark.parametrize("fault", ["counts", "path_missing", "path_duplicate", "parent_unhashable", "parent_missing", "corner_wrong", "moved_original", "nonfinite", "midpoint_wrong"])
def test_unexpected_backend_output_is_rejected_without_mutating_input(open_mesh, monkeypatch, fault):
    native = Mesh.subdivided
    before = deepcopy(open_mesh.__data__)

    def corrupt(mesh, **options):
        result = native(mesh, **options)
        face = next(result.faces())
        if fault == "counts":
            result.add_vertex(x=99, y=99, z=99)
        elif fault == "path_missing":
            result.unset_face_attribute(face, "path")
        elif fault == "path_duplicate":
            child = list(result.faces())[1]
            result.face_attribute(child, "path", result.face_attribute(face, "path"))
        elif fault == "corner_wrong":
            result.face_attribute(face, "path", [0, 2])
        elif fault == "parent_unhashable":
            result.face_attribute(face, "path", [[], 0])
        elif fault == "parent_missing":
            result.face_attribute(face, "path", [999, 0])
        elif fault == "moved_original":
            result.vertex_attribute(0, "x", 0.1)
        elif fault == "nonfinite":
            result.vertex_attribute(0, "x", float("nan"))
        else:
            midpoint = next(key for key in result.vertices() if key not in mesh.vertex)
            result.vertex_attribute(midpoint, "x", result.vertex_attribute(midpoint, "x") + 0.1)
        return result

    monkeypatch.setattr(Mesh, "subdivided", corrupt)
    with pytest.raises(ValueError):
        _run(open_mesh)
    assert open_mesh.__data__ == before


def test_backend_argument_mutation_does_not_mutate_source(open_mesh, monkeypatch):
    native = Mesh.subdivided
    before = deepcopy(open_mesh.__data__)

    def mutate_control(mesh, **options):
        result = native(mesh, **options)
        mesh.vertex_attribute(0, "x", 100)
        mesh.attributes["backend_only"] = [1, 2, 3]
        return result

    monkeypatch.setattr(Mesh, "subdivided", mutate_control)
    result = _run(open_mesh)
    assert result.mesh.vertex_coordinates(0) == open_mesh.vertex_coordinates(0)
    assert open_mesh.__data__ == before


def test_non_mesh_backend_output_is_rejected(open_mesh, monkeypatch):
    monkeypatch.setattr(Mesh, "subdivided", Mock(return_value=None))
    with pytest.raises(ValueError, match="did not return a Mesh"):
        _run(open_mesh)


def test_invalid_boundary_halfedge_not_accepted_as_valid_mesh(open_mesh):
    open_mesh.halfedge[1][0] = 0
    assert open_mesh.is_valid()  # COMPAS's validity check does not catch this.
    with pytest.raises(ValueError, match="boundary halfedge"):
        _run(open_mesh)


def test_unknown_ancestry_cannot_escape_operator(open_mesh, monkeypatch):
    def unknown(source, output):
        return LineageMap({key: None for key in output.vertices()}, {key: None for key in output.faces()})

    monkeypatch.setattr(adapter, "_recover_lineage", unknown)
    with pytest.raises(ValueError, match="Unknown"):
        _run(open_mesh)


def test_repeat_calls_are_deterministic_and_second_call_uses_immediate_parents(box_mesh):
    first, duplicate = _run(box_mesh), _run(box_mesh)
    assert first.mesh.__data__ == duplicate.mesh.__data__
    assert first.lineage == duplicate.lineage
    assert _metadata(first) == _metadata(duplicate)
    first_before = deepcopy(first.mesh.__data__)
    second = _run(first.mesh, current_generation=1)
    assert second.output_faces == 96 and second.output_vertices == 98
    assert validate_lineage_coverage(first.mesh, second.mesh, second.lineage) == []
    assert first.mesh.__data__ == first_before
    assert all(ref.key in first.mesh.vertex for refs in second.lineage.vertex_parents.values() for ref in refs)
    assert all(ref.key in first.mesh.face for refs in second.lineage.face_parents.values() for ref in refs)
    assert all(second.mesh.face_attribute(key, "path")[0] in first.mesh.face for key in second.mesh.faces())
