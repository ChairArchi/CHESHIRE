from copy import deepcopy
from dataclasses import fields
import json
from math import dist
from unittest.mock import Mock

import pytest
from compas.datastructures import Mesh
from compas.geometry import Point, Rotation, Scale, Translation

from cheshire import (
    ExecutionBudget, ParentRef, SubdivisionResult, estimate_quad_subdivision,
    subdivide_quad_once, validate_lineage_coverage,
)


WARPED = [[0, 0, 0], [2, 0, 0], [2, 2, 0.2], [0, 2, 0]]
SADDLE = [[-1, -1, 0.4], [1, -1, -0.4], [1, 1, 0.4], [-1, 1, -0.4]]


def _mesh(points, order=(0, 1, 2, 3)):
    return Mesh.from_vertices_and_faces(points, [list(order)])


def _run(mesh, policy="bilinear"):
    return subdivide_quad_once(mesh, budget=ExecutionBudget(10000, max_vertices=10000), nonplanar_policy=policy)


def _evaluate(corners, u, v):
    """Independent interpolation oracle; no production validation helpers."""
    coefficients = [(1 - u) * (1 - v), u * (1 - v), u * v, (1 - u) * v]
    return [sum(coefficient * corner[axis] for coefficient, corner in zip(coefficients, corners))
            for axis in range(len(corners[0]))]


def _patch_error(source, result):
    maximum = 0.0
    samples = [(0, 0), (1, 0), (1, 1), (0, 1), (0.5, 0.5), (0.13, 0.79), (0.82, 0.21), (0.3, 0.6)]
    for child in result.mesh.faces():
        parent = result.lineage.face_parents[child][0].key
        original = source.face_vertices(parent)
        parameters = dict(zip(original, [(0, 0), (1, 0), (1, 1), (0, 1)]))
        child_keys = result.mesh.face_vertices(child)
        child_parameters = []
        for key in child_keys:
            refs = result.lineage.vertex_parents[key]
            assert all(ref.key in parameters for ref in refs)
            child_parameters.append([sum(ref.weight * parameters[ref.key][axis] for ref in refs) for axis in range(2)])
        assert max(p[0] for p in child_parameters) - min(p[0] for p in child_parameters) == 0.5
        assert max(p[1] for p in child_parameters) - min(p[1] for p in child_parameters) == 0.5
        for u, v in samples:
            parent_u, parent_v = _evaluate(child_parameters, u, v)
            expected = _evaluate(source.face_coordinates(parent), parent_u, parent_v)
            actual = _evaluate(result.mesh.face_coordinates(child), u, v)
            maximum = max(maximum, dist(actual, expected))
    return maximum


def _roles(result):
    return {frozenset(ref.key for ref in refs): result.mesh.vertex_coordinates(key)
            for key, refs in result.lineage.vertex_parents.items()}


def test_planar_strict_and_bilinear_outputs_and_lineage_are_identical(open_mesh):
    strict, bilinear = _run(open_mesh, "reject"), _run(open_mesh)
    assert strict.mesh.__data__ == bilinear.mesh.__data__
    assert strict.lineage == bilinear.lineage
    assert strict.nonplanar_policy == "reject" and bilinear.nonplanar_policy == "bilinear"
    assert estimate_quad_subdivision(open_mesh) == estimate_quad_subdivision(open_mesh, nonplanar_policy="bilinear")
    # The added result field has a default: old constructor calls still work.
    original_arguments = {field.name: getattr(strict, field.name) for field in fields(strict) if field.name != "nonplanar_policy"}
    assert SubdivisionResult(**original_arguments).nonplanar_policy == "reject"


@pytest.mark.parametrize("points", [WARPED, SADDLE])
def test_warped_and_saddle_quad_semantics_and_complete_lineage(points):
    mesh = _mesh(points)
    before = json.dumps(mesh.__data__, sort_keys=True, allow_nan=False)
    with pytest.raises(ValueError, match="Nonplanar"):
        _run(mesh, "reject")
    with pytest.raises(ValueError, match="Nonplanar"):
        estimate_quad_subdivision(mesh)
    estimate = estimate_quad_subdivision(mesh, nonplanar_policy="bilinear")
    result = _run(mesh)
    assert result.output_vertices == estimate["estimated_output_vertices"] == 9
    assert result.output_faces == estimate["estimated_output_faces"] == 4
    assert validate_lineage_coverage(mesh, result.mesh, result.lineage) == []
    for key in mesh.vertices():
        assert result.mesh.vertex_coordinates(key) == mesh.vertex_coordinates(key)
        assert result.lineage.vertex_parents[key] == (ParentRef(key, 1),)
    for edge in mesh.edges():
        midpoint = next(key for key, refs in result.lineage.vertex_parents.items() if {ref.key for ref in refs} == set(edge))
        assert [ref.weight for ref in result.lineage.vertex_parents[midpoint]] == [0.5, 0.5]
        assert result.mesh.vertex_coordinates(midpoint) == pytest.approx([(points[edge[0]][axis] + points[edge[1]][axis]) / 2 for axis in range(3)])
    center = next(key for key, refs in result.lineage.vertex_parents.items() if len(refs) == 4)
    assert result.mesh.vertex_coordinates(center) == pytest.approx([sum(point[axis] for point in points) / 4 for axis in range(3)])
    assert all(ref.weight == 0.25 for ref in result.lineage.vertex_parents[center])
    assert all(refs == (ParentRef(0, 1),) for refs in result.lineage.face_parents.values())
    assert _patch_error(mesh, result) < 1e-12
    assert json.dumps(mesh.__data__, sort_keys=True, allow_nan=False) == before


@pytest.mark.parametrize("points", [WARPED, SADDLE])
@pytest.mark.parametrize("transform", [
    Translation.from_vector([17, -9, 5]),
    Scale.from_factors([1e-4] * 3), Scale.from_factors([1e4] * 3),
    Rotation.from_axis_and_angle([1, 2, 3], 0.63),
])
def test_acceptance_and_patch_geometry_are_coordinate_system_independent(points, transform):
    base = _run(_mesh(points))
    mesh = _mesh(points)
    mesh.transform(transform)
    transformed = _run(mesh)
    assert transformed.lineage == base.lineage
    for key in base.mesh.vertices():
        expected = Point(*base.mesh.vertex_coordinates(key)).transformed(transform)
        assert transformed.mesh.vertex_coordinates(key) == pytest.approx(expected, abs=1e-10)
    assert _patch_error(mesh, transformed) < 1e-10


@pytest.mark.parametrize("points", [WARPED, SADDLE])
@pytest.mark.parametrize("order", [(0, 1, 2, 3), (1, 2, 3, 0), (2, 3, 0, 1), (3, 0, 1, 2), (0, 3, 2, 1)])
def test_cyclic_order_and_consistent_reversal_preserve_surface(points, order):
    source = _mesh(points, order)
    result = _run(source)
    assert _roles(result) == _roles(_run(_mesh(points)))
    assert _patch_error(source, result) < 1e-12


@pytest.mark.parametrize("points", [
    [[0, 0, 0], [1, 1, 0], [0, 1, 0], [1, 0, 0]],  # Bow-tie, center J=0.
    [[0, 0, 0], [0, 0, 0], [1, 1, 0.2], [0, 1, 0]],  # Collapsed edge.
    [[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]],  # Collinear.
    [[0, 0, 0], [1, 0, 0], [1, 1e-12, 0], [0, 1e-12, 0]],  # Nearly degenerate.
    [[0, 0, 0], [1, 0, 0], [-1, -1, 0.1], [0, 1, 0]],  # Folded projection.
    [[0, 0, 0], [1, 0, 0], [0, 0, 1], [0, 1, 0]],  # Zero corner projection.
    [[0, 0, 0], [2, 0, 0], [0.3, 0.3, 0], [0, 2, 0]],  # Concave.
])
def test_invalid_or_uncertain_patches_rejected_before_backend(points, monkeypatch):
    mesh = _mesh(points)
    before = deepcopy(mesh.__data__)
    backend = Mock()
    monkeypatch.setattr(Mesh, "subdivided", backend)
    with pytest.raises(ValueError):
        _run(mesh)
    backend.assert_not_called()
    assert mesh.__data__ == before


@pytest.mark.parametrize("corruption", ["repeated_corner", "missing_vertex", "nonmanifold", "nonfinite", "face_size"])
def test_bilinear_policy_keeps_topology_and_basic_geometry_restrictions(corruption, monkeypatch):
    mesh = _mesh(WARPED)
    if corruption == "repeated_corner":
        mesh.face[0] = [0, 1, 1, 3]
    elif corruption == "missing_vertex":
        del mesh.vertex[0]
    elif corruption == "nonmanifold":
        mesh = Mesh.from_vertices_and_faces(
            [[0, 0, 0], [1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0]], [[0, 1, 2], [0, 3, 4]],
        )
    elif corruption == "nonfinite":
        mesh.vertex_attribute(0, "x", float("inf"))
    else:
        mesh = Mesh.from_vertices_and_faces([[0, 0, 0], [1, 0, 0], [2, 1, 0], [1, 2, 0], [0, 1, 0]], [[0, 1, 2, 3, 4]])
    backend = Mock()
    monkeypatch.setattr(Mesh, "subdivided", backend)
    with pytest.raises(ValueError):
        _run(mesh)
    backend.assert_not_called()


@pytest.mark.parametrize("policy", [None, "flatten", "BILINEAR", True])
def test_invalid_policy_rejected_for_estimation_and_execution(open_mesh, monkeypatch, policy):
    backend = Mock()
    monkeypatch.setattr(Mesh, "subdivided", backend)
    for call in (lambda: estimate_quad_subdivision(open_mesh, nonplanar_policy=policy), lambda: _run(open_mesh, policy)):
        with pytest.raises(ValueError, match="nonplanar_policy"):
            call()
    backend.assert_not_called()


def test_triangles_remain_unchanged_and_mixed_counts_are_exact():
    triangle = Mesh.from_vertices_and_faces([[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[0, 1, 2]])
    strict, bilinear = _run(triangle, "reject"), _run(triangle)
    assert strict.mesh.__data__ == bilinear.mesh.__data__ and strict.lineage == bilinear.lineage
    mixed = Mesh.from_vertices_and_faces(WARPED + [[3, 0, 0]], [[0, 1, 2, 3], [1, 4, 2]])
    result = _run(mixed)
    assert result.output_vertices == 13 and result.output_faces == 7
    assert validate_lineage_coverage(mixed, result.mesh, result.lineage) == []


def test_adjacent_warped_quads_share_one_midpoint():
    mesh = Mesh.from_vertices_and_faces(
        [[0, 0, 0], [1, 0, 0], [2, 0, 0], [0, 1, 0], [1, 1, 0.1], [2, 1, -0.1]],
        [[0, 1, 4, 3], [1, 2, 5, 4]],
    )
    result = _run(mesh)
    midpoint = next(key for key, refs in result.lineage.vertex_parents.items() if {ref.key for ref in refs} == {1, 4})
    assert set(result.mesh.vertex_neighbors(1)) & set(result.mesh.vertex_neighbors(4)) == {midpoint}
    assert {result.lineage.face_parents[face][0].key for face in result.mesh.vertex_faces(midpoint)} == {0, 1}
    assert _patch_error(mesh, result) < 1e-12


def test_coincident_disconnected_warped_quads_and_sparse_keys_are_not_welded():
    mesh = Mesh()
    groups = [(900, 10, -4, 77), (300, 400, 500, 600)]
    for keys, face in zip(groups, [700, 900]):
        for key, point in zip(keys, WARPED):
            mesh.add_vertex(key=key, x=point[0], y=point[1], z=point[2])
        mesh.add_face(list(keys), fkey=face)
    result = _run(mesh)
    assert result.output_vertices == 18 and result.output_faces == 8
    assert len(result.mesh.connected_vertices()) == 2
    assert validate_lineage_coverage(mesh, result.mesh, result.lineage) == []
    assert _patch_error(mesh, result) < 1e-12


@pytest.mark.parametrize("budget,generation", [
    (ExecutionBudget(3, max_vertices=9), 0), (ExecutionBudget(4, max_vertices=8), 0),
    (ExecutionBudget(4, max_vertices=9, max_generation=1), 1),
])
def test_bilinear_budget_blocks_before_backend_copy_allocation(budget, generation, monkeypatch):
    mesh = _mesh(WARPED)
    before = deepcopy(mesh.__data__)
    backend, allocation = Mock(), Mock(side_effect=AssertionError("Backend copy allocated vertices"))
    monkeypatch.setattr(Mesh, "subdivided", backend)
    monkeypatch.setattr(Mesh, "add_vertex", allocation)
    with pytest.raises(ValueError, match="budget"):
        subdivide_quad_once(mesh, budget=budget, current_generation=generation, nonplanar_policy="bilinear")
    backend.assert_not_called()
    allocation.assert_not_called()
    assert mesh.__data__ == before


def test_bilinear_policy_also_validates_backend_output(monkeypatch):
    mesh = _mesh(WARPED)
    native = Mesh.subdivided

    def folded_output(control, **options):
        output = native(control, **options)
        center = next(key for key in output.vertices() if key not in control.vertex and len(output.vertex_neighbors(key)) == 4)
        output.vertex_attributes(center, ["x", "y", "z"], [10, 10, 0.2])
        return output

    monkeypatch.setattr(Mesh, "subdivided", folded_output)
    with pytest.raises(ValueError, match="bilinear face"):
        _run(mesh)


def test_affine_jacobian_projection_corner_bound_has_an_independent_oracle():
    from compas.geometry import cross_vectors, dot_vectors, normalize_vector

    def jacobian(points, u, v):
        # Interpolate opposite boundary tangents, independently of the
        # production a,b,c expansion used to validate the face.
        du = [(1 - v) * (points[1][i] - points[0][i]) + v * (points[2][i] - points[3][i]) for i in range(3)]
        dv = [(1 - u) * (points[3][i] - points[0][i]) + u * (points[2][i] - points[1][i]) for i in range(3)]
        return cross_vectors(du, dv)

    for points in (WARPED, SADDLE):
        normal = normalize_vector(jacobian(points, 0.5, 0.5))
        corners = [jacobian(points, u, v) for u, v in ((0, 0), (1, 0), (1, 1), (0, 1))]
        projections = [dot_vectors(value, normal) for value in corners]
        assert min(projections) > 0
        for u, v in ((0.1, 0.7), (0.3, 0.8), (0.5, 0.5), (0.9, 0.2)):
            actual = jacobian(points, u, v)
            affine = [corners[0][i] + u * (corners[1][i] - corners[0][i]) + v * (corners[3][i] - corners[0][i]) for i in range(3)]
            assert actual == pytest.approx(affine)
            assert dot_vectors(actual, normal) >= min(projections) - 1e-12


def test_bilinear_neighbors_still_require_consistent_winding():
    points = [[0, 0, 0], [1, 0, 0], [2, 0, 0], [0, 1, 0], [1, 1, 0.1], [2, 1, -0.1]]
    consistent = _run(Mesh.from_vertices_and_faces(points, [[3, 4, 1, 0], [4, 5, 2, 1]]))
    assert consistent.output_faces == 8
    with pytest.raises(ValueError, match="orientation"):
        _run(Mesh.from_vertices_and_faces(points, [[0, 1, 4, 3], [4, 5, 2, 1]]))
