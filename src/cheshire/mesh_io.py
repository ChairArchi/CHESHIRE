"""Polygon OBJ I/O without welding, triangulation, or geometry repair."""

from math import floor, log10
from os import PathLike
from pathlib import Path

from compas.datastructures import Mesh
from compas.files import OBJReader

from .validation import validate_mesh


def load_mesh(path: str | PathLike[str]) -> Mesh:
    """Load OBJ vertex positions and polygon faces into a COMPAS Mesh.

    Raises FileNotFoundError for a missing file and ValueError for unsupported
    formats, malformed geometry, or basic validation problems. OBJ materials,
    texture coordinates, normals, groups, and standalone points/lines are not
    part of this mesh-only interface.
    """
    path = _obj_path(path)
    if not path.exists():
        raise FileNotFoundError(f"Mesh file does not exist: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"Mesh path is not a file: {path}")

    # OBJParser (used by Mesh.from_obj) welds vertices by geometric key.
    # Read the raw records instead to preserve distinct vertex identities.
    reader = _MeshOBJReader(str(path))
    reader.open()
    reader.pre()
    reader.read()
    reader.post()
    vertex_count = len(reader.vertices)
    for index, face in enumerate(reader.faces):
        if any(key < 0 or key >= vertex_count for key in face):
            raise ValueError(f"OBJ face {index} references a missing vertex.")

    mesh = Mesh.from_vertices_and_faces(reader.vertices, reader.faces)
    if [mesh.face_vertices(key) for key in mesh.faces()] != reader.faces:
        raise ValueError("COMPAS would alter or discard an OBJ face; no repair performed.")
    _require_valid(mesh)
    return mesh


def save_mesh(mesh: Mesh, path: str | PathLike[str]) -> None:
    """Write polygon geometry to OBJ, creating parent directories as needed.

    Only vertices and faces are exported. Basic validation runs before any
    output is created. Distinct vertices and polygon face cycles are preserved.
    """
    path = _obj_path(path)
    _require_valid(mesh)
    path.parent.mkdir(parents=True, exist_ok=True)
    # COMPAS uses fixed decimal places. Keep at least 17 significant digits,
    # increasing precision for small coordinates (up to subnormal floats).
    precision = 17
    for key in mesh.vertices():
        for value in mesh.vertex_coordinates(key):
            if value:
                precision = max(precision, min(324, 16 - floor(log10(abs(value)))))
    mesh.to_obj(str(path), precision=precision, unweld=False)


def _obj_path(path: str | PathLike[str]) -> Path:
    path = Path(path)
    if path.suffix.lower() != ".obj":
        raise ValueError(
            f"Unsupported mesh format {path.suffix or '(no extension)'}; only .obj is supported."
        )
    return path


def _require_valid(mesh: Mesh) -> None:
    problems = validate_mesh(mesh)
    if problems:
        raise ValueError("Invalid mesh: " + " ".join(problems))


class _MeshOBJReader(OBJReader):
    """Keep COMPAS reading, with explicit errors and OBJ relative face indices."""

    def _read_vertex_coordinates(self, data):
        if len(data) not in (3, 4):
            raise ValueError("OBJ vertex must contain three coordinates and an optional weight.")
        super()._read_vertex_coordinates(data)

    def _read_polygonal_geometry(self, name, data):
        if name != "f":
            return
        if len(data) < 3:
            raise ValueError("OBJ face must reference at least three vertices.")
        face = []
        for token in data:
            index = int(token.split("/")[0])
            if index == 0:
                raise ValueError("OBJ vertex indices cannot be zero.")
            key = index - 1 if index > 0 else len(self.vertices) + index
            if key < 0:
                raise ValueError("OBJ face references a missing vertex.")
            face.append(key)
        self.faces.append(face)
