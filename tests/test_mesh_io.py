import pytest
from compas.datastructures import Mesh

from cheshire import load_mesh, save_mesh


@pytest.mark.parametrize("fixture", ["box_mesh", "open_mesh"])
def test_obj_round_trip(fixture, request, tmp_path):
    mesh = request.getfixturevalue(fixture)
    before = mesh.to_vertices_and_faces()
    path = tmp_path / "nested" / "mesh.obj"
    assert save_mesh(mesh, path) is None
    assert path.is_file()
    lines = path.read_text().splitlines()
    assert sum(line.startswith("v ") for line in lines) == mesh.number_of_vertices()
    assert sum(line.startswith("f ") for line in lines) == mesh.number_of_faces()
    reloaded = load_mesh(path)
    assert isinstance(reloaded, Mesh)
    assert reloaded.number_of_vertices() == mesh.number_of_vertices()
    assert reloaded.number_of_faces() == mesh.number_of_faces()
    assert reloaded.to_vertices_and_faces() == before
    assert mesh.to_vertices_and_faces() == before


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="does not exist"):
        load_mesh(tmp_path / "missing.obj")


def test_directory_is_not_a_file(tmp_path):
    path = tmp_path / "directory.obj"
    path.mkdir()
    with pytest.raises(IsADirectoryError, match="not a file"):
        load_mesh(path)


@pytest.mark.parametrize("suffix", [".ply", ".stl", ".off", ".txt", ""])
def test_unsupported_format(suffix, open_mesh, tmp_path):
    path = tmp_path / ("mesh" + suffix)
    with pytest.raises(ValueError, match="only .obj is supported"):
        save_mesh(open_mesh, path)
    assert not path.exists()
    with pytest.raises(ValueError, match="only .obj is supported"):
        load_mesh(path)


def test_string_path_and_uppercase_extension(open_mesh, tmp_path):
    path = str(tmp_path / "mesh.OBJ")
    save_mesh(open_mesh, path)
    assert load_mesh(path).to_vertices_and_faces() == open_mesh.to_vertices_and_faces()


def test_distinct_coincident_close_and_unused_vertices(tmp_path):
    mesh = Mesh.from_vertices_and_faces(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0], [1e-8, 0, 0], [5, 5, 5]],
        [[0, 1, 2], [3, 4, 2]],
    )
    path = tmp_path / "unwelded.obj"
    save_mesh(mesh, path)
    assert load_mesh(path).to_vertices_and_faces() == mesh.to_vertices_and_faces()


def test_float_precision_round_trip(tmp_path):
    mesh = Mesh.from_vertices_and_faces(
        [[0.12345678901234567, 5e-324, -1e-30], [1e100, 0, 0], [0, 1, 0]],
        [[0, 1, 2]],
    )
    path = tmp_path / "precise.obj"
    save_mesh(mesh, path)
    assert load_mesh(path).to_vertices_and_faces() == mesh.to_vertices_and_faces()


def test_relative_obj_indices_and_texture_normal_references(tmp_path):
    path = tmp_path / "relative.obj"
    path.write_text(
        "v 0 0 0\nv 1 0 0\nv 0 1 0\n"
        "vt 0 0\nvn 0 0 1\nf -3/1/1 -2/1/1 -1/1/1\n"
        "v 10 10 10\n"
    )
    mesh = load_mesh(path)
    assert mesh.number_of_vertices() == 4
    assert mesh.face_vertices(0) == [0, 1, 2]


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_load_rejects_non_finite_coordinates(value, tmp_path):
    path = tmp_path / "invalid.obj"
    path.write_text(f"v {value} 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
    with pytest.raises(ValueError, match="non-finite coordinates"):
        load_mesh(path)


@pytest.mark.parametrize("content, message", [
    ("", "zero vertices"),
    ("v 0 0 0\n", "zero faces"),
    ("v 0 0\n", "three coordinates"),
    ("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2\n", "at least three"),
    ("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 0 2 3\n", "cannot be zero"),
    ("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 4\n", "missing vertex"),
    ("v 0 0 0\nv 1 0 0\nv 0 1 0\nf -4 -2 -1\n", "missing vertex"),
    ("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 2 3\n", "alter or discard"),
])
def test_load_reports_invalid_geometry(content, message, tmp_path):
    path = tmp_path / "invalid.obj"
    path.write_text(content)
    with pytest.raises(ValueError, match=message):
        load_mesh(path)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_save_rejects_non_finite_before_creating_output(value, open_mesh, tmp_path):
    open_mesh.vertex_attribute(0, "z", value)
    path = tmp_path / "uncreated" / "invalid.obj"
    with pytest.raises(ValueError, match="non-finite coordinates"):
        save_mesh(open_mesh, path)
    assert not path.parent.exists()


def test_save_rejects_empty_mesh(tmp_path):
    path = tmp_path / "empty.obj"
    with pytest.raises(ValueError, match="zero vertices.*zero faces"):
        save_mesh(Mesh(), path)
    assert not path.exists()
