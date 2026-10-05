from copy import deepcopy
import json
from math import dist, isfinite, sqrt

import pytest
from compas.datastructures import Mesh
from compas.geometry import Box, Frame

from cheshire import (
    ExecutionBudget, Rule, TransformResult, analyze_vertex_attributes,
    build_scalar_field, displace_vertices_along_normals, evaluate_vertex_rule,
    load_mesh, plan_execution, save_mesh,
)


@pytest.fixture
def control_mesh():
    """A consistently oriented XY quad with diagonal 5 and +Z normals."""
    return Mesh.from_vertices_and_faces(
        [[0, 0, 0], [3, 0, 0], [3, 4, 0], [0, 4, 0]], [[0, 1, 2, 3]],
    )


@pytest.fixture
def gate_mesh():
    """Two vertical support boxes and one horizontal lintel; no welding."""
    vertices, faces = [], []
    for sizes, center in [
        ((1, 1, 3), [-1.5, 0, 1.5]),
        ((1, 1, 3), [1.5, 0, 1.5]),
        ((4, 1, 1), [0, 0, 3.5]),
    ]:
        box = Mesh.from_shape(Box(*sizes, frame=Frame(center, [1, 0, 0], [0, 1, 0])))
        box_vertices, box_faces = box.to_vertices_and_faces()
        offset = len(vertices)
        vertices.extend(box_vertices)
        faces.extend([[key + offset for key in face] for face in box_faces])
    return Mesh.from_vertices_and_faces(vertices, faces)


def _uniform_field(mesh, value=1.0):
    return {key: value for key in mesh.vertices()}


def _metadata(result):
    return {name: value for name, value in vars(result).items() if name != "mesh"}


def _topology(mesh):
    return {
        "vertices": list(mesh.vertices()),
        "faces": {key: mesh.face_vertices(key).copy() for key in mesh.faces()},
        "vertex_count": mesh.number_of_vertices(),
        "face_count": mesh.number_of_faces(),
        "edge_count": mesh.number_of_edges(),
    }


def _assert_finite(result):
    for key in result.mesh.vertices():
        assert all(isfinite(value) for value in result.mesh.vertex_coordinates(key))
    for name in ("strength", "base_scale", "max_displacement"):
        assert isfinite(getattr(result, name))


def test_zero_strength_returns_independent_identical_mesh(control_mesh):
    before = deepcopy(control_mesh.__data__)
    before_bytes = json.dumps(before, sort_keys=True).encode()
    result = displace_vertices_along_normals(control_mesh, _uniform_field(control_mesh), strength=0)
    assert isinstance(result, TransformResult)
    assert isinstance(result.mesh, Mesh)
    assert result.mesh is not control_mesh
    assert result.mesh.__data__ == control_mesh.__data__ == before
    assert json.dumps(result.mesh.__data__, sort_keys=True).encode() == before_bytes
    assert result.moved_count == 0
    assert result.selected_count == result.skipped_count == 4
    assert result.max_displacement == 0.0
    result.mesh.vertex_attribute(0, "z", 99)
    assert control_mesh.__data__ == before


def test_zero_field_does_not_move_vertices(control_mesh):
    result = displace_vertices_along_normals(control_mesh, _uniform_field(control_mesh, 0))
    assert result.mesh.to_vertices_and_faces() == control_mesh.to_vertices_and_faces()
    assert result.moved_count == 0
    assert result.skipped_count == 4
    assert set(result.skipped_vertices.values()) == {"zero_displacement"}


@pytest.mark.parametrize("direction, sign", [("outward", 1), ("inward", -1)])
def test_unit_field_moves_expected_distance_along_normals(control_mesh, direction, sign):
    result = displace_vertices_along_normals(
        control_mesh, _uniform_field(control_mesh), strength=0.02, direction=direction,
    )
    for key in control_mesh.vertices():
        x, y, _ = control_mesh.vertex_coordinates(key)
        assert result.mesh.vertex_coordinates(key) == pytest.approx([x, y, sign * 0.1])
    assert result.base_scale == 5.0
    assert result.max_displacement == pytest.approx(0.1)
    assert result.selected_count == result.moved_count == 4
    assert result.skipped_count == 0
    assert result.operator == "normal_displacement"
    assert result.direction == direction
    assert result.topology_changed is False


def test_intermediate_field_values_scale_motion_using_original_normals(control_mesh):
    values = {0: 0.0, 1: 0.25, 2: 0.5, 3: 1.0}
    before = deepcopy(values)
    result = displace_vertices_along_normals(control_mesh, values, strength=0.02)
    for key, value in values.items():
        x, y, _ = control_mesh.vertex_coordinates(key)
        assert result.mesh.vertex_coordinates(key) == pytest.approx([x, y, value * 0.1])
    assert values == before
    assert result.moved_count == 3
    assert result.skipped_vertices == {0: "zero_displacement"}


def test_only_explicit_selected_vertices_move(control_mesh):
    selected = [2, 0]
    result = displace_vertices_along_normals(
        control_mesh, _uniform_field(control_mesh), selected_vertices=selected, strength=0.02,
    )
    for key in control_mesh.vertices():
        before = control_mesh.vertex_coordinates(key)
        after = result.mesh.vertex_coordinates(key)
        if key in selected:
            assert dist(before, after) == pytest.approx(0.1)
        else:
            assert after == before
    assert selected == [2, 0]
    assert result.selected_count == result.moved_count == 2


def test_null_and_missing_fields_produce_zero_movement(control_mesh):
    result = displace_vertices_along_normals(control_mesh, {0: None, 1: 0.5}, strength=0.02)
    for key in (0, 2, 3):
        assert result.mesh.vertex_coordinates(key) == control_mesh.vertex_coordinates(key)
    assert result.mesh.vertex_coordinates(1)[2] == pytest.approx(0.05)
    assert result.selected_count == 4
    assert result.moved_count == 1
    assert result.skipped_count == 3
    assert result.skipped_vertices == {0: "unavailable_field", 2: "unavailable_field", 3: "unavailable_field"}


def test_empty_selection_and_field_return_unchanged_copies(control_mesh):
    empty_selection = displace_vertices_along_normals(
        control_mesh, _uniform_field(control_mesh), selected_vertices=[],
    )
    empty_field = displace_vertices_along_normals(control_mesh, {})
    assert empty_selection.selected_count == empty_selection.moved_count == empty_selection.skipped_count == 0
    assert empty_field.moved_count == 0
    assert empty_field.skipped_count == 4
    for result in (empty_selection, empty_field):
        assert result.mesh is not control_mesh
        assert result.mesh.__data__ == control_mesh.__data__


def test_selection_sets_duplicates_and_generators_are_deterministic(control_mesh):
    results = [
        displace_vertices_along_normals(control_mesh, _uniform_field(control_mesh), selected_vertices=selection)
        for selection in ([2, 0, 2], {2, 0}, (key for key in [0, 2]))
    ]
    for result in results:
        assert result.selected_count == 2
        assert result.mesh.__data__ == results[0].mesh.__data__
        assert _metadata(result) == _metadata(results[0])


@pytest.mark.parametrize("direction, offset", [("outward", 0.05), ("inward", -0.05)])
def test_cube_motion_has_known_normal_direction(direction, offset):
    mesh = Mesh.from_shape(Box(1, 1, 1))
    result = displace_vertices_along_normals(mesh, _uniform_field(mesh), strength=0.05, direction=direction)
    for key in mesh.vertices():
        xyz = mesh.vertex_coordinates(key)
        expected = [value + (offset if value > 0 else -offset) for value in xyz]
        assert result.mesh.vertex_coordinates(key) == pytest.approx(expected)
    assert result.max_displacement == pytest.approx(sqrt(3) * 0.05)


def test_native_normals_use_incident_face_area_weights():
    mesh = Mesh.from_vertices_and_faces(
        [[0, 0, 0], [2, 0, 0], [2, 1, 0], [0, 1, 0], [2, 0, 3], [0, 0, 3]],
        [[0, 1, 2, 3], [1, 0, 5, 4]],
    )
    # At vertex 0: area 2 in +Z, area 6 in +Y -> unit normal (0, 3, 1)/sqrt(10).
    result = displace_vertices_along_normals(mesh, {0: 1.0}, selected_vertices=[0], strength=0.02)
    distance = sqrt(14) * 0.02
    assert result.mesh.vertex_coordinates(0) == pytest.approx([0, distance * 3 / sqrt(10), distance / sqrt(10)])


def test_outward_follows_face_winding_without_repair(control_mesh):
    mesh = Mesh.from_vertices_and_faces(
        control_mesh.to_vertices_and_faces()[0], [[3, 2, 1, 0]],
    )
    result = displace_vertices_along_normals(mesh, _uniform_field(mesh), strength=0.02)
    assert all(result.mesh.vertex_coordinates(key)[2] == pytest.approx(-0.1) for key in mesh.vertices())
    assert result.mesh.face_vertices(0) == [3, 2, 1, 0]


@pytest.mark.parametrize("fixture", ["control_mesh", "box_mesh", "grid_mesh"])
def test_topology_and_input_data_are_preserved(fixture, request):
    mesh = request.getfixturevalue(fixture)
    before = deepcopy(mesh.__data__)
    topology = _topology(mesh)
    result = displace_vertices_along_normals(mesh, _uniform_field(mesh))
    assert _topology(result.mesh) == topology
    assert _topology(mesh) == topology
    assert mesh.__data__ == before
    assert result.topology_changed is False
    _assert_finite(result)


def test_sparse_keys_and_custom_attributes_survive_without_aliasing():
    mesh = Mesh.from_vertices_and_faces(
        {10: [0, 0, 0], 30: [3, 0, 0], 70: [3, 4, 0], 99: [0, 4, 0]},
        {42: [10, 30, 70, 99]},
    )
    mesh.name = "control"
    mesh.attributes["custom"] = {"items": [1, 2]}
    mesh.vertex_attribute(10, "custom", {"items": [3, 4]})
    mesh.face_attribute(42, "custom", {"items": [5, 6]})
    mesh.edge_attribute((10, 30), "custom", {"items": [7, 8]})
    before = deepcopy(mesh.__data__)
    result = displace_vertices_along_normals(mesh, _uniform_field(mesh))
    assert _topology(result.mesh) == _topology(mesh)
    assert result.mesh.name == mesh.name
    assert result.mesh.attributes["custom"] == {"items": [1, 2]}
    assert result.mesh.vertex_attribute(10, "custom") == {"items": [3, 4]}
    assert result.mesh.face_attribute(42, "custom") == {"items": [5, 6]}
    assert result.mesh.edge_attribute((10, 30), "custom") == {"items": [7, 8]}
    result.mesh.vertex_attribute(10, "custom")["items"].append(99)
    result.mesh.attributes["custom"]["items"].append(99)
    assert mesh.__data__ == before


@pytest.mark.parametrize("factor", [0.001, 0.5, 10.0, 1000.0])
def test_scaled_geometry_produces_proportional_displacement(control_mesh, factor):
    vertices, faces = control_mesh.to_vertices_and_faces()
    scaled = Mesh.from_vertices_and_faces([[value * factor for value in xyz] for xyz in vertices], faces)
    original_result = displace_vertices_along_normals(control_mesh, _uniform_field(control_mesh, 0.8), strength=0.02)
    scaled_result = displace_vertices_along_normals(scaled, _uniform_field(scaled, 0.8), strength=0.02)
    assert scaled_result.base_scale == pytest.approx(5 * factor)
    assert scaled_result.max_displacement == pytest.approx(original_result.max_displacement * factor)
    for key in scaled.vertices():
        assert scaled_result.mesh.vertex_coordinates(key) == pytest.approx(
            [value * factor for value in original_result.mesh.vertex_coordinates(key)]
        )


@pytest.mark.parametrize("strength", [-0.01, float("nan"), float("inf"), float("-inf"), "0.01", None])
def test_invalid_strength_is_rejected(strength, control_mesh):
    with pytest.raises(ValueError, match="strength"):
        displace_vertices_along_normals(control_mesh, {}, strength=strength)


@pytest.mark.parametrize("scale_mode", ["absolute", "mean_edge_length", "unknown", None])
def test_invalid_scale_mode_is_rejected(scale_mode, control_mesh):
    with pytest.raises(ValueError, match="scale_mode"):
        displace_vertices_along_normals(control_mesh, {}, scale_mode=scale_mode)


@pytest.mark.parametrize("direction", ["up", "normal", "unknown", None])
def test_invalid_direction_is_rejected(direction, control_mesh):
    with pytest.raises(ValueError, match="direction"):
        displace_vertices_along_normals(control_mesh, {}, direction=direction)


@pytest.mark.parametrize("value", [-0.01, 1.01, float("nan"), float("inf"), float("-inf"), "0.5", 1j])
def test_invalid_field_values_are_rejected_even_if_unselected(value, control_mesh):
    before = deepcopy(control_mesh.__data__)
    with pytest.raises(ValueError, match="Field value"):
        displace_vertices_along_normals(control_mesh, {0: value}, selected_vertices=[])
    assert control_mesh.__data__ == before


def test_invalid_field_mapping_and_unknown_vertex_key(control_mesh):
    with pytest.raises(ValueError, match="mapping"):
        displace_vertices_along_normals(control_mesh, [])
    with pytest.raises(ValueError, match="absent from the mesh"):
        displace_vertices_along_normals(control_mesh, {99: 1.0})


@pytest.mark.parametrize("selection", [[99], 2, [[0]], "unknown"])
def test_invalid_selection_is_rejected(selection, control_mesh):
    with pytest.raises(ValueError, match="Selection|selected_vertices"):
        displace_vertices_along_normals(control_mesh, {}, selected_vertices=selection)


def test_degenerate_faces_do_not_fabricate_normals():
    mesh = Mesh.from_vertices_and_faces([[0, 0, 0], [1, 0, 0], [2, 0, 0]], [[0, 1, 2]])
    result = displace_vertices_along_normals(mesh, _uniform_field(mesh))
    assert result.mesh.__data__ == mesh.__data__
    assert result.moved_count == 0
    assert result.skipped_count == 3
    assert set(result.skipped_vertices.values()) == {"unsafe_normal"}
    _assert_finite(result)


def test_zero_diagonal_is_a_reported_noop():
    mesh = Mesh.from_vertices_and_faces([[0, 0, 0]] * 3, [[0, 1, 2]])
    result = displace_vertices_along_normals(mesh, _uniform_field(mesh))
    assert result.base_scale == 0.0
    assert result.moved_count == 0
    assert result.skipped_count == 3
    assert result.mesh.__data__ == mesh.__data__
    _assert_finite(result)


def test_isolated_vertex_is_skipped_without_removal(control_mesh):
    key = control_mesh.add_vertex(key=100, x=2, y=2, z=2)
    result = displace_vertices_along_normals(control_mesh, _uniform_field(control_mesh))
    assert result.mesh.vertex_coordinates(key) == [2, 2, 2]
    assert result.skipped_vertices == {100: "unsafe_normal"}
    assert result.moved_count == 4
    assert _topology(result.mesh) == _topology(control_mesh)


def test_cancelling_normals_are_skipped():
    mesh = Mesh.from_vertices_and_faces(
        [[0, 0, 0], [3, 0, 0], [3, 4, 0], [0, 4, 0]],
        [[0, 1, 2, 3], [3, 2, 1, 0]],
    )
    result = displace_vertices_along_normals(mesh, _uniform_field(mesh))
    assert result.moved_count == 0
    assert result.skipped_count == 4
    assert set(result.skipped_vertices.values()) == {"unsafe_normal"}
    assert result.mesh.__data__ == mesh.__data__


def test_disconnected_face_fan_is_skipped():
    vertices, faces = Mesh.from_polyhedron(4).to_vertices_and_faces()
    mesh = Mesh.from_vertices_and_faces(
        vertices + [[x + 5, y, z] for x, y, z in vertices[1:]],
        faces + [[0 if key == 0 else key + 3 for key in face] for face in faces],
    )
    result = displace_vertices_along_normals(mesh, _uniform_field(mesh))
    assert result.skipped_vertices[0] == "unsafe_normal"
    assert result.mesh.vertex_coordinates(0) == mesh.vertex_coordinates(0)
    assert _topology(result.mesh) == _topology(mesh)


@pytest.mark.parametrize("unsafe_normal", [[0, 0, 0], [float("nan"), 0, 1], [0, float("inf"), 1], None, [0, 1]])
def test_unusable_native_normal_is_reported_and_never_applied(control_mesh, unsafe_normal, monkeypatch):
    native = Mesh.vertex_normal

    def normal(self, key):
        return unsafe_normal if key == 1 else native(self, key)

    monkeypatch.setattr(Mesh, "vertex_normal", normal)
    result = displace_vertices_along_normals(control_mesh, _uniform_field(control_mesh))
    assert result.mesh.vertex_coordinates(1) == control_mesh.vertex_coordinates(1)
    assert result.skipped_vertices == {1: "unsafe_normal"}
    assert result.moved_count == 3
    _assert_finite(result)


@pytest.mark.parametrize("exception", [ZeroDivisionError, NotImplementedError, OverflowError])
def test_unavailable_native_normals_are_reported(control_mesh, exception, monkeypatch):
    def normal(self, key):
        raise exception

    monkeypatch.setattr(Mesh, "vertex_normal", normal)
    result = displace_vertices_along_normals(control_mesh, _uniform_field(control_mesh))
    assert result.moved_count == 0
    assert result.skipped_count == 4
    assert result.mesh.__data__ == control_mesh.__data__
    _assert_finite(result)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_input_geometry_is_rejected(control_mesh, value):
    control_mesh.vertex_attribute(0, "z", value)
    with pytest.raises(ValueError, match="non-finite coordinates"):
        displace_vertices_along_normals(control_mesh, {})


def test_empty_and_inconsistent_meshes_are_not_repaired():
    with pytest.raises(ValueError, match="zero vertices"):
        displace_vertices_along_normals(Mesh(), {})
    mesh = Mesh.from_vertices_and_faces(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, -1, 0]], [[0, 1, 2], [0, 1, 3]],
    )
    with pytest.raises(ValueError, match="inconsistent COMPAS topology"):
        displace_vertices_along_normals(mesh, {})


def test_unrepresentable_bounding_diagonal_is_rejected():
    mesh = Mesh.from_vertices_and_faces(
        [[-1e308, 0, 0], [1e308, 0, 0], [0, 1, 0]], [[0, 1, 2]],
    )
    with pytest.raises(ValueError, match="Bounding-box diagonal"):
        displace_vertices_along_normals(mesh, _uniform_field(mesh))


def test_distance_overflow_fails_without_modifying_input(control_mesh):
    before = deepcopy(control_mesh.__data__)
    with pytest.raises(ValueError, match="Displacement distance"):
        displace_vertices_along_normals(control_mesh, {0: 0.01, 1: 1.0}, strength=1e308)
    assert control_mesh.__data__ == before


def test_coordinate_overflow_is_rejected(control_mesh, monkeypatch):
    for key in control_mesh.vertices():
        control_mesh.vertex_attribute(key, "z", 1.79e308)
    before = deepcopy(control_mesh.__data__)
    monkeypatch.setattr(Mesh, "vertex_normal", lambda self, key: [0, 0, 1])
    with pytest.raises(ValueError, match="coordinates would be non-finite"):
        displace_vertices_along_normals(control_mesh, _uniform_field(control_mesh), strength=1e307)
    assert control_mesh.__data__ == before


def test_unrepresentably_small_coordinate_change_is_reported(control_mesh):
    for key in control_mesh.vertices():
        control_mesh.vertex_attribute(key, "z", 1.0)
    result = displace_vertices_along_normals(control_mesh, _uniform_field(control_mesh), strength=1e-300)
    assert result.moved_count == 0
    assert result.max_displacement == 0.0
    assert set(result.skipped_vertices.values()) == {"coordinate_precision"}
    assert result.mesh.__data__ == control_mesh.__data__


def test_deterministic_coordinates_and_metadata(box_mesh):
    field = {key: key / 7 for key in box_mesh.vertices()}
    first = displace_vertices_along_normals(box_mesh, field, strength=0.02)
    second = displace_vertices_along_normals(box_mesh, field, strength=0.02)
    assert first.mesh.__data__ == second.mesh.__data__
    assert _metadata(first) == _metadata(second)


def test_displaced_mesh_can_be_saved_and_reloaded(box_mesh, tmp_path):
    result = displace_vertices_along_normals(box_mesh, _uniform_field(box_mesh))
    path = tmp_path / "displaced.obj"
    save_mesh(result.mesh, path)
    assert load_mesh(path).to_vertices_and_faces() == result.mesh.to_vertices_and_faces()


def test_gate_measure_map_rule_budget_transform_integration(gate_mesh):
    before = deepcopy(gate_mesh.__data__)
    before_bytes = json.dumps(before, sort_keys=True, allow_nan=False).encode()
    topology = _topology(gate_mesh)
    attributes = analyze_vertex_attributes(gate_mesh)
    field = build_scalar_field(attributes, "normalized_height")
    before_field = deepcopy(field)
    rule = Rule("high gate vertices", "height", "vertex", "greater_equal", 0.5,
                operator="normal_displacement", parameters={"strength": 0.02})
    selection = evaluate_vertex_rule(field["values"], rule)
    plan = plan_execution(
        gate_mesh, {"height": field}, rule,
        ExecutionBudget(max_faces=18, max_vertices=24, max_generation=1),
        current_generation=0, cost_profile={"topology_preserving": True},
    )
    assert plan["status"] == "SAFE"
    assert plan["estimated_output_faces"] == plan["input_faces"] == 18
    assert plan["estimated_output_vertices"] == plan["input_vertices"] == 24
    assert plan["selected_vertices"] == selection["selected_keys"]

    result = displace_vertices_along_normals(
        gate_mesh, field["values"], selected_vertices=selection["selected_keys"], strength=0.02,
    )
    assert result.selected_count == result.moved_count == 16
    assert result.skipped_count == 0
    assert result.base_scale == pytest.approx(sqrt(33))
    assert result.max_displacement == pytest.approx(0.02 * sqrt(33))
    for key in gate_mesh.vertices():
        original = gate_mesh.vertex_coordinates(key)
        displaced = result.mesh.vertex_coordinates(key)
        if key in selection["selected_keys"]:
            assert displaced != original
            assert dist(original, displaced) == pytest.approx(field["values"][key] * 0.02 * sqrt(33))
        else:
            assert displaced == original
    assert {value for value in field["values"].values()} == {0.0, 0.75, 1.0}
    assert _topology(result.mesh) == topology
    assert gate_mesh.__data__ == before
    assert json.dumps(gate_mesh.__data__, sort_keys=True, allow_nan=False).encode() == before_bytes
    assert field == before_field
    _assert_finite(result)
