import pytest
from compas.datastructures import Mesh

from cheshire import inspect_mesh, validate_mesh


def test_inspect_box(box_mesh):
    assert inspect_mesh(box_mesh) == {
        "vertex_count": 8,
        "face_count": 6,
        "edge_count": 12,
        "boundary_edge_count": 0,
        "is_manifold": True,
        "is_closed": True,
        "bounding_box": [2.0, 3.0, 4.0],
    }


def test_inspect_open_mesh(open_mesh):
    assert inspect_mesh(open_mesh) == {
        "vertex_count": 4,
        "face_count": 1,
        "edge_count": 4,
        "boundary_edge_count": 4,
        "is_manifold": True,
        "is_closed": False,
        "bounding_box": [2.0, 3.0, 0.0],
    }


@pytest.mark.parametrize("fixture", ["box_mesh", "open_mesh"])
def test_valid_mesh(fixture, request):
    assert validate_mesh(request.getfixturevalue(fixture)) == []


def test_empty_mesh():
    mesh = Mesh()
    assert validate_mesh(mesh) == ["Mesh has zero vertices.", "Mesh has zero faces."]
    assert inspect_mesh(mesh)["bounding_box"] is None


def test_vertices_without_faces():
    mesh = Mesh.from_vertices_and_faces([[1, 2, 3]], [])
    assert validate_mesh(mesh) == ["Mesh has zero faces."]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("axis", ["x", "y", "z"])
def test_non_finite_coordinates(open_mesh, value, axis):
    open_mesh.vertex_attribute(0, axis, value)
    problems = validate_mesh(open_mesh)
    assert len(problems) == 1
    assert "Vertex 0 has non-finite coordinates" in problems[0]
    assert inspect_mesh(open_mesh)["bounding_box"] is None


def test_inspection_and_validation_do_not_mutate(open_mesh):
    before = open_mesh.to_vertices_and_faces()
    inspect_mesh(open_mesh)
    validate_mesh(open_mesh)
    assert open_mesh.to_vertices_and_faces() == before


def test_unavailable_topology_properties_return_none(open_mesh, monkeypatch):
    monkeypatch.setattr(Mesh, "is_manifold", None)

    def unavailable(self):
        raise NotImplementedError

    monkeypatch.setattr(Mesh, "is_closed", unavailable)
    report = inspect_mesh(open_mesh)
    assert report["is_manifold"] is None
    assert report["is_closed"] is None
