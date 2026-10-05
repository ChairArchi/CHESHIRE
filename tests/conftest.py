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


@pytest.fixture
def grid_mesh():
    """5 by 5 vertices, with two interior edge-hop layers."""
    return Mesh.from_vertices_and_faces(
        [[column, row, 0] for row in range(5) for column in range(5)],
        [
            [row * 5 + column, row * 5 + column + 1,
             (row + 1) * 5 + column + 1, (row + 1) * 5 + column]
            for row in range(4) for column in range(4)
        ],
    )
