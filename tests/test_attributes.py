from copy import deepcopy
from math import dist, isfinite, sqrt

import pytest
from compas.datastructures import Mesh

from cheshire import analyze_vertex_attributes, attribute_summary


def test_box_measurements(box_mesh):
    attributes = analyze_vertex_attributes(box_mesh)
    assert set(attributes) == set(box_mesh.vertices())
    for key, record in attributes.items():
        assert record["valence"] == 3
        assert record["boundary"] is False
        assert record["normalized_height"] == (box_mesh.vertex_coordinates(key)[2] + 2) / 4
        assert record["centroid_distance"] == pytest.approx(sqrt(29) / 2)
        assert record["normalized_centroid_distance"] == 0.0
        assert record["approximate_curvature"] == pytest.approx(0.5)
        assert record["boundary_distance"] is None


def test_open_quad_measurements(open_mesh):
    for record in analyze_vertex_attributes(open_mesh).values():
        assert record["valence"] == 2
        assert record["boundary"] is True
        assert record["normalized_height"] == 0.0
        assert record["centroid_distance"] == pytest.approx(sqrt(13) / 2)
        assert record["normalized_centroid_distance"] == 0.0
        assert record["approximate_curvature"] is None
        assert record["boundary_distance"] == 0


def test_grid_valence_boundaries_and_breadth_first_distances(grid_mesh):
    attributes = analyze_vertex_attributes(grid_mesh)
    for row in range(5):
        for column in range(5):
            record = attributes[row * 5 + column]
            hops = min(row, column, 4 - row, 4 - column)
            assert record["valence"] == 4 - (row in (0, 4)) - (column in (0, 4))
            assert record["boundary"] is (hops == 0)
            assert record["boundary_distance"] == hops
            assert record["normalized_height"] == 0.0
            assert record["centroid_distance"] == pytest.approx(dist([column, row, 0], [2, 2, 0]))
            assert record["normalized_centroid_distance"] == pytest.approx(
                record["centroid_distance"] / sqrt(8)
            )
            if hops:
                assert record["approximate_curvature"] == 0.0
            else:
                assert record["approximate_curvature"] is None


def test_constant_nonzero_height(grid_mesh):
    for key in grid_mesh.vertices():
        grid_mesh.vertex_attribute(key, "z", 7.0)
    assert all(record["normalized_height"] == 0.0
               for record in analyze_vertex_attributes(grid_mesh).values())


def test_centroid_uses_compas_surface_area_weighting():
    mesh = Mesh.from_vertices_and_faces(
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
         [10, 0, 0], [13, 0, 0], [13, 1, 0], [10, 1, 0]],
        [[0, 1, 2, 3], [4, 5, 6, 7]],
    )
    assert analyze_vertex_attributes(mesh)[0]["centroid_distance"] == pytest.approx(
        dist([0, 0, 0], [8.75, 0.5, 0])
    )


def test_sparse_vertex_keys_are_preserved():
    mesh = Mesh.from_vertices_and_faces(
        {10: [0, 0, 0], 30: [1, 0, 0], 80: [1, 1, 0], 120: [0, 1, 0]},
        [[10, 30, 80, 120]],
    )
    attributes = analyze_vertex_attributes(mesh)
    assert list(attributes) == [10, 30, 80, 120]
    assert all(record["valence"] == 2 and record["boundary_distance"] == 0
               for record in attributes.values())


def test_folded_grid_has_positive_normal_variation(grid_mesh):
    grid_mesh.vertex_attribute(12, "z", 1.0)
    result = analyze_vertex_attributes(grid_mesh)
    assert 0 < result[12]["approximate_curvature"] <= 1
    assert result[12]["normalized_height"] == 1.0
    assert result[0]["normalized_height"] == 0.0


def test_unavailable_normals_return_null(box_mesh, monkeypatch):
    centroid = list(box_mesh.centroid())

    def unavailable(self, face, unitized=True):
        raise NotImplementedError

    monkeypatch.setattr(Mesh, "face_normal", unavailable)
    # COMPAS face_area also uses face_normal; isolate the curvature fallback.
    monkeypatch.setattr(Mesh, "centroid", lambda self: centroid)
    assert all(record["approximate_curvature"] is None
               for record in analyze_vertex_attributes(box_mesh).values())


def test_degenerate_faces_return_null_curvature_and_centroid(grid_mesh):
    for key in grid_mesh.vertices():
        grid_mesh.vertex_attribute(key, "y", 0.0)
    for record in analyze_vertex_attributes(grid_mesh).values():
        assert record["approximate_curvature"] is None
        assert record["centroid_distance"] is None
        assert record["normalized_centroid_distance"] is None
        assert record["normalized_height"] == 0.0


def test_disconnected_closed_component_has_no_boundary_distance(grid_mesh, box_mesh):
    vertices, faces = grid_mesh.to_vertices_and_faces()
    box_vertices, box_faces = box_mesh.to_vertices_and_faces()
    offset = len(vertices)
    mesh = Mesh.from_vertices_and_faces(
        vertices + [[x + 20, y, z] for x, y, z in box_vertices],
        faces + [[key + offset for key in face] for face in box_faces],
    )
    attributes = analyze_vertex_attributes(mesh)
    assert attributes[12]["boundary_distance"] == 2
    for key in range(offset, offset + len(box_vertices)):
        assert attributes[key]["boundary_distance"] is None


def test_isolated_vertex_does_not_invent_curvature_or_boundary_distance(box_mesh):
    key = box_mesh.add_vertex(x=10, y=10, z=10)
    attributes = analyze_vertex_attributes(box_mesh)
    assert attributes[key]["valence"] == 0
    assert attributes[key]["boundary"] is False
    assert attributes[key]["approximate_curvature"] is None
    assert attributes[key]["boundary_distance"] is None
    assert attributes[0]["approximate_curvature"] == pytest.approx(0.5)


def test_disconnected_face_fans_return_null_curvature():
    vertices, faces = Mesh.from_polyhedron(4).to_vertices_and_faces()
    # Two closed tetrahedra share only vertex 0: its face fan is disconnected.
    mesh = Mesh.from_vertices_and_faces(
        vertices + [[x + 5, y, z] for x, y, z in vertices[1:]],
        faces + [[0 if key == 0 else key + 3 for key in face] for face in faces],
    )
    assert mesh.is_valid()
    attributes = analyze_vertex_attributes(mesh)
    assert attributes[0]["boundary"] is False
    assert attributes[0]["approximate_curvature"] is None


@pytest.mark.parametrize("fixture", ["box_mesh", "open_mesh", "grid_mesh"])
def test_measurement_is_deterministic_finite_and_read_only(fixture, request):
    mesh = request.getfixturevalue(fixture)
    mesh.vertex_attribute(0, "custom", {"label": "retain", "items": [1, 2]})
    before = deepcopy(mesh.__data__)
    attributes = analyze_vertex_attributes(mesh)
    assert attributes == analyze_vertex_attributes(mesh)
    assert mesh.__data__ == before
    normalized = {"normalized_height", "normalized_centroid_distance", "approximate_curvature"}
    for record in attributes.values():
        for name, value in record.items():
            if value is not None:
                assert isfinite(value)
                if name in normalized:
                    assert 0 <= value <= 1


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_measurement_rejects_non_finite_coordinates(value, open_mesh):
    open_mesh.vertex_attribute(0, "x", value)
    with pytest.raises(ValueError, match="non-finite coordinates"):
        analyze_vertex_attributes(open_mesh)


@pytest.mark.parametrize("mesh", [Mesh(), Mesh.from_vertices_and_faces([[0, 0, 0]], [])])
def test_measurement_rejects_empty_geometry(mesh):
    with pytest.raises(ValueError, match="zero"):
        analyze_vertex_attributes(mesh)


def test_inconsistent_topology_is_reported():
    mesh = Mesh.from_vertices_and_faces(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, -1, 0]],
        [[0, 1, 2], [0, 1, 3]],
    )
    with pytest.raises(ValueError, match="inconsistent COMPAS topology"):
        analyze_vertex_attributes(mesh)


def test_summary_ignores_nulls_and_excludes_booleans():
    attributes = {
        7: {"value": 2, "missing": None, "boundary": True},
        9: {"value": None, "missing": None, "boundary": False},
        20: {"value": 8, "missing": None, "boundary": True},
    }
    before = deepcopy(attributes)
    assert attribute_summary(attributes) == {
        "value": {"min": 2, "max": 8, "mean": 5},
        "missing": {"min": None, "max": None, "mean": None},
    }
    assert attributes == before
    assert attribute_summary({}) == {}


def test_summary_of_measured_attributes(box_mesh):
    summary = attribute_summary(analyze_vertex_attributes(box_mesh))
    assert summary["valence"] == {"min": 3, "max": 3, "mean": 3}
    assert summary["normalized_height"] == {"min": 0, "max": 1, "mean": 0.5}
    assert summary["boundary_distance"] == {"min": None, "max": None, "mean": None}


def test_summary_handles_large_finite_values():
    assert attribute_summary({0: {"x": 1e308}, 1: {"x": 1e308}})["x"]["mean"] == 1e308
    assert attribute_summary({0: {"x": -1e308}, 1: {"x": 1e308}})["x"]["mean"] == 0


@pytest.mark.parametrize("value", [float("nan"), float("inf"), "invalid"])
def test_summary_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        attribute_summary({0: {"value": value}})
