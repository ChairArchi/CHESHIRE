import pytest
from compas.datastructures import Mesh
from compas.geometry import Box


@pytest.fixture
def box_mesh():
    return Mesh.from_shape(Box(2, 3, 4))


@pytest.fixture
def open_mesh():
    return Mesh.from_vertices_and_faces(
        [[0, 0, 0], [2, 0, 0], [2, 3, 0], [0, 3, 0]],
        [[0, 1, 2, 3]],
    )
