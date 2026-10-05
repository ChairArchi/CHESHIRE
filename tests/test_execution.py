from copy import deepcopy
from dataclasses import asdict
import json
from math import isfinite
from numbers import Real

import pytest
from compas.datastructures import Mesh

from cheshire import (
    ExecutionBudget, Rule, analyze_vertex_attributes, build_scalar_field,
    evaluate_face_rule, plan_execution,
)


def _all_vertices(mesh, value=1.0):
    return {"test": {key: value for key in mesh.vertices()}}


def _rule(target="face", threshold=0.5, operator="hypothetical_refine"):
    return Rule("test", "test", target, "greater_than", threshold, operator=operator)


def test_topology_preserving_estimate_and_exact_count_budget(box_mesh):
    plan = plan_execution(
        box_mesh, _all_vertices(box_mesh), _rule("vertex"),
        ExecutionBudget(6, max_vertices=8, max_generation=4),
        current_generation=2, cost_profile={"topology_preserving": True},
    )
    assert plan["dry_run"] is True
    assert plan["generation"] == 2
    assert plan["input_faces"] == plan["estimated_output_faces"] == 6
    assert plan["input_vertices"] == plan["estimated_output_vertices"] == 8
    assert plan["selected_vertices"] == list(box_mesh.vertices())
    assert plan["selected_faces"] == []
    assert plan["selected_fraction"] == 1.0
    assert plan["face_budget"] == 6
    assert plan["vertex_budget"] == 8
    assert plan["generation_budget"] == 4
    assert plan["budget_checks"] == {"face": "SAFE", "vertex": "SAFE", "generation": "SAFE"}
    assert plan["status"] == "SAFE"
    assert plan["reasons"] == []


@pytest.mark.parametrize("replacement", [1, 2, 4, 7])
def test_explicit_growth_is_used_without_assuming_four(box_mesh, replacement):
    values = {key: (box_mesh.vertex_coordinates(key)[2] + 2) / 4 for key in box_mesh.vertices()}
    plan = plan_execution(
        box_mesh, {"test": values}, _rule(), ExecutionBudget(100),
        cost_profile={"topology_preserving": False, "replacement_faces_per_selected_face": replacement},
    )
    assert len(plan["selected_faces"]) == 1
    assert plan["estimated_output_faces"] == 5 + replacement
    assert plan["estimated_output_vertices"] is None
    assert plan["status"] == "SAFE"
    assert "estimate" in plan["estimate_note"].lower()


def test_growth_face_budget_blocks_and_reports_the_estimate(box_mesh):
    plan = plan_execution(
        box_mesh, _all_vertices(box_mesh), _rule(), ExecutionBudget(23, max_generation=4),
        current_generation=2,
        cost_profile={"topology_preserving": False, "replacement_faces_per_selected_face": 4},
    )
    assert plan["estimated_output_faces"] == 24
    assert plan["budget_checks"] == {"face": "BLOCKED", "vertex": None, "generation": "SAFE"}
    assert plan["status"] == "BLOCKED"
    assert plan["reasons"] == ["Face budget: estimated output 24 exceeds limit 23."]


@pytest.mark.parametrize("generation", [4, 5])
def test_at_or_beyond_generation_limit_is_blocked(box_mesh, generation):
    plan = plan_execution(
        box_mesh, _all_vertices(box_mesh), _rule(), ExecutionBudget(100, max_generation=4),
        current_generation=generation, cost_profile={"topology_preserving": True},
    )
    assert plan["budget_checks"]["face"] == "SAFE"
    assert plan["budget_checks"]["generation"] == "BLOCKED"
    assert plan["status"] == "BLOCKED"
    assert plan["reasons"] == [f"Generation budget: {generation} >= limit 4."]


def test_face_and_generation_failures_are_reported_separately(box_mesh):
    plan = plan_execution(
        box_mesh, _all_vertices(box_mesh), _rule(), ExecutionBudget(23, max_generation=4),
        current_generation=4,
        cost_profile={"topology_preserving": False, "replacement_faces_per_selected_face": 4},
    )
    assert plan["budget_checks"]["face"] == plan["budget_checks"]["generation"] == "BLOCKED"
    assert len(plan["reasons"]) == 2
    assert plan["reasons"][0].startswith("Face budget:")
    assert plan["reasons"][1].startswith("Generation budget:")


def test_optional_vertex_budget_blocks_independently(box_mesh):
    plan = plan_execution(
        box_mesh, _all_vertices(box_mesh), _rule(), ExecutionBudget(6, max_vertices=7),
        cost_profile={"topology_preserving": True},
    )
    assert plan["budget_checks"] == {"face": "SAFE", "vertex": "BLOCKED", "generation": None}
    assert plan["status"] == "BLOCKED"
    assert plan["reasons"][0].startswith("Vertex budget:")


def test_unknown_vertex_growth_warns_when_vertex_budget_is_requested(box_mesh):
    plan = plan_execution(
        box_mesh, _all_vertices(box_mesh), _rule(), ExecutionBudget(24, max_vertices=100),
        cost_profile={"topology_preserving": False, "replacement_faces_per_selected_face": 4},
    )
    assert plan["estimated_output_vertices"] is None
    assert plan["budget_checks"] == {"face": "SAFE", "vertex": "WARNING", "generation": None}
    assert plan["status"] == "WARNING"
    assert plan["reasons"][0].startswith("Vertex budget:")


@pytest.mark.parametrize("operator", [None, "subdivide", "Catmull-Clark", "any_future_operator"])
def test_missing_profile_never_infers_growth_from_operator_name(box_mesh, operator):
    plan = plan_execution(box_mesh, _all_vertices(box_mesh), _rule(operator=operator), ExecutionBudget(100))
    assert plan["operator"] == operator
    assert plan["estimated_output_faces"] is None
    assert plan["estimated_output_vertices"] is None
    assert plan["status"] == "WARNING"
    assert "No cost profile" in plan["estimate_note"]
    assert plan["budget_checks"]["face"] == "WARNING"


def test_vertex_selection_does_not_invent_face_refinement_cost(box_mesh):
    plan = plan_execution(
        box_mesh, _all_vertices(box_mesh), _rule("vertex"), ExecutionBudget(100),
        cost_profile={"topology_preserving": False, "replacement_faces_per_selected_face": 4},
    )
    assert len(plan["selected_vertices"]) == 8
    assert plan["estimated_output_faces"] is None
    assert plan["status"] == "WARNING"
    assert "Selected vertices" in plan["estimate_note"]


def test_blocked_status_takes_precedence_over_unknown_estimates(box_mesh):
    plan = plan_execution(
        box_mesh, _all_vertices(box_mesh), _rule(), ExecutionBudget(100, max_generation=1),
        current_generation=1,
    )
    assert plan["budget_checks"]["face"] == "WARNING"
    assert plan["budget_checks"]["generation"] == "BLOCKED"
    assert plan["status"] == "BLOCKED"


def test_input_already_over_budget_is_blocked_even_without_estimates(box_mesh):
    plan = plan_execution(box_mesh, _all_vertices(box_mesh), _rule(), ExecutionBudget(5))
    assert plan["status"] == "BLOCKED"
    assert "input count 6" in plan["reasons"][0]


def test_no_selection_keeps_the_face_count_under_explicit_growth_profile(box_mesh):
    plan = plan_execution(
        box_mesh, _all_vertices(box_mesh, value=0), _rule(), ExecutionBudget(6),
        cost_profile={"topology_preserving": False, "replacement_faces_per_selected_face": 4},
    )
    assert plan["selected_faces"] == []
    assert plan["selected_fraction"] == 0
    assert plan["estimated_output_faces"] == 6
    assert plan["status"] == "SAFE"


def test_zero_budgets_are_explicit_limits(box_mesh):
    plan = plan_execution(
        box_mesh, _all_vertices(box_mesh), _rule(),
        ExecutionBudget(0, max_vertices=0, max_generation=0),
        cost_profile={"topology_preserving": True},
    )
    assert plan["status"] == "BLOCKED"
    assert set(plan["budget_checks"].values()) == {"BLOCKED"}
    assert len(plan["reasons"]) == 3


@pytest.mark.parametrize("name", ["max_faces", "max_vertices", "max_generation"])
@pytest.mark.parametrize("value", [-1, 1.5, float("inf"), float("nan"), True, "10"])
def test_invalid_budgets(name, value):
    arguments = {"max_faces": 100, name: value}
    with pytest.raises(ValueError, match=name):
        ExecutionBudget(**arguments)


def test_face_budget_is_required():
    with pytest.raises(ValueError, match="max_faces"):
        ExecutionBudget(None)


@pytest.mark.parametrize("profile", [
    {}, [], {"topology_preserving": 1}, {"topology_preserving": "true"},
    {"topology_preserving": False},
    {"topology_preserving": False, "replacement_faces_per_selected_face": 0},
    {"topology_preserving": False, "replacement_faces_per_selected_face": -4},
    {"topology_preserving": False, "replacement_faces_per_selected_face": 4.0},
    {"topology_preserving": False, "replacement_faces_per_selected_face": True},
    {"topology_preserving": False, "replacement_faces_per_selected_face": float("inf")},
    {"topology_preserving": False, "replacement_faces_per_selected_face": float("nan")},
    {"topology_preserving": True, "replacement_faces_per_selected_face": 4},
    {"topology_preserving": True, "assumed_factor": 4},
])
def test_invalid_profiles_are_rejected(profile, box_mesh):
    with pytest.raises(ValueError):
        plan_execution(box_mesh, _all_vertices(box_mesh), _rule(), ExecutionBudget(100), cost_profile=profile)


@pytest.mark.parametrize("generation", [-1, 1.5, float("inf"), float("nan"), True, "2"])
def test_invalid_generation_is_rejected(generation, box_mesh):
    with pytest.raises(ValueError, match="current_generation"):
        plan_execution(box_mesh, _all_vertices(box_mesh), _rule(), ExecutionBudget(100), current_generation=generation)


@pytest.mark.parametrize("fields, message", [
    ({}, "unavailable"),
    ({"test": []}, "mapping"),
    ({"test": {"values": None}}, "mapping"),
    ({"test": {100: 0.5}}, "absent from the mesh"),
    ({"test": {0: float("nan")}}, "finite real number"),
    ({"test": {0: float("inf")}}, "finite real number"),
])
def test_invalid_field_registry(fields, message, box_mesh):
    with pytest.raises(ValueError, match=message):
        plan_execution(box_mesh, fields, _rule(), ExecutionBudget(100))


def test_invalid_rule_and_budget_types(box_mesh):
    with pytest.raises(ValueError, match="Rule"):
        plan_execution(box_mesh, {}, None, ExecutionBudget(100))
    with pytest.raises(ValueError, match="ExecutionBudget"):
        plan_execution(box_mesh, _all_vertices(box_mesh), _rule(), {"max_faces": 100})


def test_invalid_mesh_is_reported(open_mesh):
    open_mesh.vertex_attribute(0, "z", float("inf"))
    with pytest.raises(ValueError, match="non-finite"):
        plan_execution(open_mesh, _all_vertices(open_mesh), _rule(), ExecutionBudget(100))


def test_partial_vertex_field_counts_missing_vertices_as_null(box_mesh):
    plan = plan_execution(
        box_mesh, {"test": {0: 1.0}}, _rule("vertex"), ExecutionBudget(100),
        cost_profile={"topology_preserving": True},
    )
    assert plan["selected_vertices"] == [0]
    assert plan["selection"]["eligible_count"] == 1
    assert plan["selection"]["null_count"] == 7
    assert plan["selected_fraction"] == 1.0


def test_rule_parameters_and_profile_are_copied_into_plan(box_mesh):
    parameters = {"future_setting": {"amount": 2}}
    rule = Rule("test", "test", "face", "greater_than", 0.5, parameters=parameters)
    profile = {"topology_preserving": True}
    plan = plan_execution(box_mesh, _all_vertices(box_mesh), rule, ExecutionBudget(100), cost_profile=profile)
    plan["rule"]["parameters"]["future_setting"]["amount"] = 99
    plan["cost_profile"]["topology_preserving"] = False
    assert rule.parameters == parameters == {"future_setting": {"amount": 2}}
    assert profile == {"topology_preserving": True}


def _assert_finite(value):
    if isinstance(value, dict):
        for item in value.values():
            _assert_finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_finite(item)
    elif isinstance(value, Real):
        assert isfinite(value)


def test_measure_map_rule_plan_integration_preserves_serialized_geometry(grid_mesh, monkeypatch):
    grid_mesh.vertex_attribute(0, "custom", {"label": "retain"})
    before_data = deepcopy(grid_mesh.__data__)
    before_bytes = json.dumps(grid_mesh.__data__, sort_keys=True, allow_nan=False).encode()
    before_geometry = grid_mesh.to_vertices_and_faces()

    def forbidden(*args, **kwargs):
        pytest.fail("Dry-run planning attempted to execute a geometry operator.")

    for method in ("transform", "add_vertex", "add_face", "delete_vertex", "delete_face"):
        monkeypatch.setattr(Mesh, method, forbidden)
    attributes = analyze_vertex_attributes(grid_mesh)
    field = build_scalar_field(attributes, "boundary_distance")
    fields = {"custom_interior": field}
    before_fields = deepcopy(fields)
    rule = Rule("interior", "custom_interior", "face", "greater_than", 0.5,
                operator="subdivide", parameters={"future_setting": 2})
    budget = ExecutionBudget(30, max_generation=4)
    before_budget = asdict(budget)
    profile = {"topology_preserving": False, "replacement_faces_per_selected_face": 4}
    before_profile = deepcopy(profile)
    selection = evaluate_face_rule(grid_mesh, field["values"], rule)
    plan = plan_execution(grid_mesh, fields, rule, budget, current_generation=2, cost_profile=profile)
    assert selection["selected_keys"] == [5, 6, 9, 10]
    assert plan["selected_faces"] == selection["selected_keys"]
    assert plan["selected_fraction"] == 0.25
    assert plan["input_faces"] == 16
    assert plan["input_vertices"] == 25
    assert plan["estimated_output_faces"] == 28
    assert plan["estimated_output_vertices"] is None
    assert plan["status"] == "SAFE"
    assert plan == plan_execution(grid_mesh, fields, rule, budget, current_generation=2, cost_profile=profile)
    assert grid_mesh.__data__ == before_data
    assert json.dumps(grid_mesh.__data__, sort_keys=True, allow_nan=False).encode() == before_bytes
    assert grid_mesh.to_vertices_and_faces() == before_geometry
    assert fields == before_fields
    assert asdict(budget) == before_budget
    assert profile == before_profile
    _assert_finite(attributes)
    _assert_finite(field)
    _assert_finite(plan)


@pytest.mark.parametrize("fixture", ["box_mesh", "open_mesh", "grid_mesh"])
@pytest.mark.parametrize("target", ["vertex", "face"])
def test_both_targets_are_deterministic_and_read_only(fixture, target, request):
    mesh = request.getfixturevalue(fixture)
    before = deepcopy(mesh.__data__)
    fields = {"height": build_scalar_field(analyze_vertex_attributes(mesh), "normalized_height")}
    rule = Rule("height", "height", target, "greater_equal", 0.5)
    plan = plan_execution(mesh, fields, rule, ExecutionBudget(100), cost_profile={"topology_preserving": True})
    assert plan == plan_execution(mesh, fields, rule, ExecutionBudget(100), cost_profile={"topology_preserving": True})
    assert mesh.__data__ == before
    _assert_finite(plan)
