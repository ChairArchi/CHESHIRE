from copy import deepcopy
from dataclasses import FrozenInstanceError
from math import isfinite

import pytest
from compas.datastructures import Mesh

from cheshire import Rule, evaluate_face_rule, evaluate_vertex_rule


@pytest.mark.parametrize("comparison, threshold, upper, expected", [
    ("greater_than", 0.5, None, [30]),
    ("greater_equal", 0.5, None, [20, 30]),
    ("less_than", 0.5, None, [10]),
    ("less_equal", 0.5, None, [10, 20]),
    ("between", 0.5, 1.0, [20, 30]),
    ("between", 0.5, 0.5, [20]),
])
def test_vertex_comparisons_and_null_exclusion(comparison, threshold, upper, expected):
    values = {10: 0.0, 20: 0.5, 30: 1.0, 40: None}
    rule = Rule("test", "arbitrary_external_field", "vertex", comparison, threshold, upper)
    before = deepcopy(values)
    result = evaluate_vertex_rule(values, rule)
    assert result == {
        "target": "vertex",
        "selected_keys": expected,
        "selected_count": len(expected),
        "total_count": 4,
        "eligible_count": 3,
        "selected_fraction": len(expected) / 3,
        "rejected_count": 3 - len(expected),
        "null_count": 1,
    }
    assert result == evaluate_vertex_rule(values, rule)
    assert values == before


@pytest.mark.parametrize("values, null_count", [({}, 0), ({7: None, 9: None}, 2)])
def test_empty_or_null_vertex_field(values, null_count):
    rule = Rule("empty", "any", "vertex", "greater_equal", 0)
    result = evaluate_vertex_rule(values, rule)
    assert result["selected_keys"] == []
    assert result["selected_fraction"] == 0.0
    assert result["eligible_count"] == 0
    assert result["rejected_count"] == 0
    assert result["null_count"] == null_count


@pytest.mark.parametrize("reduction, threshold", [("mean", 0.5), ("min", 0.0), ("max", 1.0)])
def test_face_reductions(reduction, threshold, open_mesh):
    values = {0: 0, 1: 0.5, 2: 0.5, 3: 1}
    rule = Rule("face", "any", "face", "between", threshold, threshold, face_reduction=reduction)
    assert evaluate_face_rule(open_mesh, values, rule)["selected_keys"] == [0]


@pytest.mark.parametrize("reduction, threshold", [("mean", 0.6), ("min", 0.3), ("max", 0.9)])
def test_partial_null_and_missing_face_values_are_not_filled_in(reduction, threshold, open_mesh):
    values = {0: None, 1: 0.3, 2: 0.9}  # Vertex 3 is unavailable, not zero.
    rule = Rule("partial", "any", "face", "greater_equal", threshold - 1e-15,
                face_reduction=reduction)
    before = deepcopy(values)
    result = evaluate_face_rule(open_mesh, values, rule)
    assert result["selected_keys"] == [0]
    assert result["eligible_count"] == 1
    assert result["null_count"] == 0
    assert values == before


@pytest.mark.parametrize("values", [{}, {0: None, 1: None, 2: None, 3: None}])
def test_completely_null_face_is_ineligible(values, open_mesh):
    rule = Rule("null", "any", "face", "greater_equal", 0)
    result = evaluate_face_rule(open_mesh, values, rule)
    assert result["selected_keys"] == []
    assert result["eligible_count"] == 0
    assert result["null_count"] == 1
    assert result["selected_fraction"] == 0.0


def test_face_selection_counts_and_fraction_with_null_faces():
    mesh = Mesh.from_vertices_and_faces(
        [[column, row, 0] for row in range(2) for column in range(6)],
        [[0, 1, 7, 6], [2, 3, 9, 8], [4, 5, 11, 10]],
    )
    values = {key: None if key % 6 < 2 else (0.25 if key % 6 < 4 else 0.75)
              for key in mesh.vertices()}
    rule = Rule("faces", "any", "face", "greater_than", 0.5)
    result = evaluate_face_rule(mesh, values, rule)
    assert result["selected_keys"] == [2]
    assert result["total_count"] == 3
    assert result["eligible_count"] == 2
    assert result["selected_count"] == 1
    assert result["selected_fraction"] == 0.5
    assert result["rejected_count"] == 1
    assert result["null_count"] == 1


@pytest.mark.parametrize("comparison, threshold, upper, selected", [
    ("greater_than", 0.5, None, False),
    ("greater_equal", 0.5, None, True),
    ("less_than", 0.5, None, False),
    ("less_equal", 0.5, None, True),
    ("between", 0.5, 0.5, True),
])
def test_face_comparison_boundaries(comparison, threshold, upper, selected, open_mesh):
    rule = Rule("face", "any", "face", comparison, threshold, upper)
    result = evaluate_face_rule(open_mesh, {key: 0.5 for key in open_mesh.vertices()}, rule)
    assert result["selected_keys"] == ([0] if selected else [])


@pytest.mark.parametrize("field_name", [
    "conflict", "variance", "overlap_density", "distance_to_opening", "user-defined-field",
])
def test_rule_does_not_restrict_field_names(field_name):
    rule = Rule("custom", field_name, "vertex", "greater_than", 0.5)
    assert evaluate_vertex_rule({1: 0.75}, rule)["selected_keys"] == [1]


@pytest.mark.parametrize("changes, message", [
    ({"name": ""}, "name"),
    ({"name": None}, "name"),
    ({"field": " "}, "field"),
    ({"target": "edge"}, "target"),
    ({"target": None}, "target"),
    ({"comparison": "equals"}, "comparison"),
    ({"comparison": None}, "comparison"),
    ({"threshold": None}, "threshold"),
    ({"threshold": float("nan")}, "threshold"),
    ({"threshold": float("inf")}, "threshold"),
    ({"threshold": float("-inf")}, "threshold"),
    ({"threshold": "0.5"}, "threshold"),
    ({"threshold": True}, "threshold"),
    ({"comparison": "between"}, "upper_threshold"),
    ({"comparison": "between", "upper_threshold": float("inf")}, "upper_threshold"),
    ({"comparison": "between", "upper_threshold": 0.25}, "upper_threshold"),
    ({"upper_threshold": 1.0}, "upper_threshold"),
    ({"face_reduction": "median"}, "face_reduction"),
    ({"operator": ""}, "operator"),
    ({"parameters": []}, "parameters"),
])
def test_invalid_rule_configuration(changes, message):
    arguments = dict(name="test", field="any", target="vertex", comparison="greater_than", threshold=0.5)
    arguments.update(changes)
    with pytest.raises(ValueError, match=message):
        Rule(**arguments)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), "invalid", 1j])
def test_non_finite_or_non_numeric_fields_are_rejected(value, open_mesh):
    with pytest.raises(ValueError, match="finite real number"):
        evaluate_vertex_rule({0: value}, Rule("bad", "any", "vertex", "greater_than", 0))
    with pytest.raises(ValueError, match="finite real number"):
        evaluate_face_rule(open_mesh, {0: value}, Rule("bad", "any", "face", "greater_than", 0))


def test_evaluator_target_mismatches_and_invalid_types(open_mesh):
    vertex_rule = Rule("vertex", "any", "vertex", "greater_than", 0)
    face_rule = Rule("face", "any", "face", "greater_than", 0)
    with pytest.raises(ValueError, match="vertex.*target"):
        evaluate_vertex_rule({}, face_rule)
    with pytest.raises(ValueError, match="face.*target"):
        evaluate_face_rule(open_mesh, {}, vertex_rule)
    with pytest.raises(ValueError, match="Rule"):
        evaluate_vertex_rule({}, None)
    with pytest.raises(ValueError, match="mapping"):
        evaluate_vertex_rule([], vertex_rule)


def test_face_evaluation_rejects_vertex_keys_absent_from_mesh(open_mesh):
    with pytest.raises(ValueError, match="absent from the mesh"):
        evaluate_face_rule(open_mesh, {99: 0.5}, Rule("face", "any", "face", "greater_than", 0))


def test_rule_copies_parameter_metadata_and_is_frozen():
    parameters = {"future_setting": {"amount": 2}}
    rule = Rule("test", "any", "vertex", "greater_than", 0.5,
                operator="future_operator", parameters=parameters)
    parameters["future_setting"]["amount"] = 99
    assert rule.parameters == {"future_setting": {"amount": 2}}
    with pytest.raises(FrozenInstanceError):
        rule.threshold = 0.9


def test_sparse_keys_and_input_order_are_preserved():
    values = {100: 0.75, -10: 1, 33: 0}
    rule = Rule("sparse", "any", "vertex", "greater_than", 0.5)
    assert evaluate_vertex_rule(values, rule)["selected_keys"] == [100, -10]
    mesh = Mesh.from_vertices_and_faces(
        {10: [0, 0, 0], 30: [1, 0, 0], 70: [1, 1, 0], 99: [0, 1, 0]},
        {42: [10, 30, 70, 99]},
    )
    face_rule = Rule("sparse", "any", "face", "greater_than", 0.5)
    assert evaluate_face_rule(mesh, {key: 0.75 for key in mesh.vertices()}, face_rule)["selected_keys"] == [42]


def test_face_mean_does_not_overflow_for_large_finite_scalars(open_mesh):
    rule = Rule("large", "any", "face", "greater_than", 1e307)
    result = evaluate_face_rule(open_mesh, {key: 1e308 for key in open_mesh.vertices()}, rule)
    assert result["selected_keys"] == [0]
    assert isfinite(result["selected_fraction"])


def test_face_selection_is_deterministic_and_read_only(box_mesh):
    values = {key: (box_mesh.vertex_coordinates(key)[2] + 2) / 4 for key in box_mesh.vertices()}
    before_mesh = deepcopy(box_mesh.__data__)
    before_values = deepcopy(values)
    rule = Rule("upper", "height", "face", "greater_than", 0.5)
    first = evaluate_face_rule(box_mesh, values, rule)
    assert first["selected_count"] == 1
    assert first == evaluate_face_rule(box_mesh, values, rule)
    assert box_mesh.__data__ == before_mesh
    assert values == before_values
