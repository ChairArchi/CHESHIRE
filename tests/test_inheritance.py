from copy import deepcopy
from dataclasses import FrozenInstanceError
from enum import Enum
import json
from math import inf, nan
import sys

import pytest

from cheshire import (
    ExecutionBudget, FieldSpec, InheritedFieldSet, LineageMap, ParentRef, Rule,
    analyze_vertex_attributes, build_scalar_field, displace_vertices_along_normals,
    identity_lineage, inherit_fields, plan_execution,
)


def _spec(name="signal", domain="vertex", mode="CONTINUOUS"):
    kind = "categorical" if mode == "CATEGORICAL" else "scalar"
    return FieldSpec(name, domain, kind, mode)


def _edge_lineage(weights=(0.5, 0.5)):
    return LineageMap(vertex_parents={"C": [ParentRef("A", weights[0]), ParentRef("B", weights[1])]})


@pytest.mark.parametrize("weights, expected", [((0.5, 0.5), 0.5), ((0.25, 0.75), 0.65), ((1, 0), 0.2)])
def test_weighted_continuous_interpolation(weights, expected):
    result = inherit_fields(_edge_lineage(weights), {"signal": {"A": 0.2, "B": 0.8}}, [_spec()])
    assert isinstance(result, InheritedFieldSet)
    assert result.values["signal"]["C"] == pytest.approx(expected)
    assert result.unresolved_counts == {"signal": 0}
    assert result.recompute_fields == result.warnings == []


def test_synthetic_face_split_continuous_and_categorical():
    lineage = LineageMap(face_parents={key: [ParentRef(10, 1)] for key in [100, 101, 102]})
    result = inherit_fields(
        lineage, {"part_type": {10: "support"}, "conflict": {10: 0.8}},
        [_spec("part_type", "face", "CATEGORICAL"), _spec("conflict", "face")],
    )
    assert result.values == {
        "part_type": {100: "support", 101: "support", 102: "support"},
        "conflict": {100: 0.8, 101: 0.8, 102: 0.8},
    }
    assert result.unresolved_counts == {"part_type": 0, "conflict": 0}


@pytest.mark.parametrize("values, expected", [
    ({"A": "support", "B": "support"}, "support"),
    ({"A": "support", "B": "lintel"}, None),
    ({"A": "support", "B": None}, None),
    ({"A": "support"}, None),
])
def test_categorical_agreement_and_conflict(values, expected):
    result = inherit_fields(_edge_lineage(), {"signal": values}, [_spec(mode="CATEGORICAL")])
    assert result.values["signal"]["C"] == expected
    assert result.unresolved_counts["signal"] == int(expected is None)
    assert bool(result.warnings) == (expected is None)


def test_categorical_conflict_does_not_choose_largest_or_zero_weight_parent():
    result = inherit_fields(
        _edge_lineage((1, 0)), {"signal": {"A": "support", "B": "lintel"}},
        [_spec(mode="CATEGORICAL")],
    )
    assert result.values["signal"]["C"] is None


def test_enum_and_tuple_labels_are_preserved():
    class Label(Enum):
        SUPPORT = "support"

    lineage = _edge_lineage()
    for label in [Label.SUPPORT, ("support", 17), 0, False]:
        result = inherit_fields(lineage, {"signal": {"A": label, "B": label}}, [_spec(mode="CATEGORICAL")])
        assert result.values["signal"]["C"] == label
        assert type(result.values["signal"]["C"]) is type(label)


def test_single_categorical_parent_and_unknown_lineage():
    lineage = LineageMap(face_parents={"known": [ParentRef(77, 1)], "unknown": None})
    result = inherit_fields(lineage, {"tag": {77: "support"}}, [_spec("tag", "face", "CATEGORICAL")])
    assert result.values == {"tag": {"known": "support", "unknown": None}}
    assert result.unresolved_counts == {"tag": 1}


def test_identity_labels_are_not_copied_or_made_to_conflict():
    label = object()
    result = inherit_fields(
        _edge_lineage(), {"signal": {"A": label, "B": label}}, [_spec(mode="CATEGORICAL")],
    )
    assert result.values["signal"]["C"] is label


def test_recompute_never_inherits_or_reads_stale_source():
    result = inherit_fields(
        _edge_lineage(), {"approximate_curvature": {"A": nan, "B": inf}},
        [_spec("approximate_curvature", mode="RECOMPUTE"), _spec("boundary", mode="RECOMPUTE")],
    )
    assert result.values == result.unresolved_counts == {}
    assert result.recompute_fields == ["approximate_curvature", "boundary"]
    assert result.warnings == []


@pytest.mark.parametrize("parents", [{"A": 0.2}, {"B": 0.8}, {"A": None, "B": 0.8}, {"A": 0.2, "B": None}, {}])
def test_missing_null_parent_values_are_unresolved_without_renormalizing(parents):
    result = inherit_fields(_edge_lineage(), {"signal": parents}, [_spec()])
    assert result.values == {"signal": {"C": None}}
    assert result.unresolved_counts == {"signal": 1}
    assert len(result.warnings) == 1


def test_missing_zero_weight_parent_is_still_unresolved():
    result = inherit_fields(_edge_lineage((1, 0)), {"signal": {"A": 0.2}}, [_spec()])
    assert result.values["signal"]["C"] is None


def test_missing_field_and_unknown_lineage_reported():
    lineage = LineageMap(vertex_parents={"C": None, "D": [ParentRef("A", 1)]})
    result = inherit_fields(lineage, {}, [_spec()])
    assert result.values == {"signal": {"C": None, "D": None}}
    assert result.unresolved_counts == {"signal": 2}
    assert any("missing" in warning for warning in result.warnings)


@pytest.mark.parametrize("value", [nan, inf, -inf, "0.5", [0.5], complex(1, 0)])
@pytest.mark.parametrize("key", ["A", "unused"])
def test_invalid_continuous_parent_values_rejected_even_if_unused(value, key):
    fields = {"signal": {"A": 0.2, "B": 0.8, key: value}}
    with pytest.raises(ValueError, match="finite real"):
        inherit_fields(_edge_lineage(), fields, [_spec()])


@pytest.mark.parametrize("value", [nan, inf, -inf, ["support"], {"label": "support"}])
def test_invalid_categorical_values_rejected(value):
    with pytest.raises(ValueError):
        inherit_fields(_edge_lineage(), {"signal": {"A": value, "B": value}}, [_spec(mode="CATEGORICAL")])


@pytest.mark.parametrize("samples, expected", [
    ((-20, 40), 10), ((0, 0), 0),
    ((sys.float_info.max, sys.float_info.max), sys.float_info.max),
    ((sys.float_info.max, -sys.float_info.max), 0),
    ((5e-324, 5e-324), 5e-324),
])
def test_finite_scalar_range_is_not_restricted_to_normalized_values(samples, expected):
    result = inherit_fields(_edge_lineage(), {"signal": dict(zip(["A", "B"], samples))}, [_spec()])
    assert result.values["signal"]["C"] == expected


def test_tolerated_weights_are_not_renormalized_and_overflow_is_rejected():
    weight = 1 + 5e-10
    lineage = LineageMap(vertex_parents={"C": [ParentRef("A", weight)]})
    result = inherit_fields(lineage, {"signal": {"A": 2}}, [_spec()])
    assert result.values["signal"]["C"] == weight * 2
    with pytest.raises(ValueError, match="not finite"):
        inherit_fields(lineage, {"signal": {"A": sys.float_info.max}}, [_spec()])


def test_zero_weight_extreme_does_not_erase_tiny_contribution():
    result = inherit_fields(
        _edge_lineage((1, 0)), {"signal": {"A": 5e-324, "B": sys.float_info.max}}, [_spec()],
    )
    assert result.values["signal"]["C"] == 5e-324


def test_cancellation_retains_small_finite_contributions():
    lineage = LineageMap(vertex_parents={"D": [ParentRef("A", 0.25), ParentRef("B", 0.25), ParentRef("C", 0.5)]})
    result = inherit_fields(
        lineage, {"signal": {"A": 1e308, "B": -1e308, "C": 1e-100}}, [_spec()],
    )
    assert result.values["signal"]["D"] == 5e-101


@pytest.mark.parametrize("field, value", [
    ("name", ""), ("name", None), ("domain", "edge"), ("domain", None),
    ("kind", "vector"), ("inheritance_mode", "MAJORITY"), ("inheritance_mode", None),
    ("kind", "categorical"),
])
def test_invalid_field_specs(field, value):
    kwargs = dict(name="signal", domain="vertex", kind="scalar", inheritance_mode="CONTINUOUS")
    kwargs[field] = value
    with pytest.raises(ValueError):
        FieldSpec(**kwargs)


def test_categorical_mode_requires_categorical_kind_and_specs_are_frozen():
    with pytest.raises(ValueError):
        FieldSpec("label", "face", "scalar", "CATEGORICAL")
    with pytest.raises(FrozenInstanceError):
        _spec().domain = "face"


def test_duplicate_and_non_spec_entries_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        inherit_fields(LineageMap(), {}, [_spec(), _spec()])
    with pytest.raises(ValueError, match="FieldSpec"):
        inherit_fields(LineageMap(), {}, ["signal"])


@pytest.mark.parametrize("fields", [None, [], {"signal": None}, {"signal": [1, 2]}])
def test_invalid_field_collections(fields):
    with pytest.raises(ValueError, match="mapping"):
        inherit_fields(_edge_lineage(), fields, [_spec()])


def test_invalid_lineage_is_rejected_before_inheritance():
    with pytest.raises(ValueError, match="LineageMap"):
        inherit_fields(None, {}, [])


def test_empty_fields_domains_and_spec_iterators():
    result = inherit_fields(LineageMap(), {}, iter([_spec()]))
    assert result.values == {"signal": {}}
    assert result.unresolved_counts == {"signal": 0}
    assert inherit_fields(LineageMap(), {}, []).values == {}


def test_metadata_input_arbitrary_keys_order_determinism_and_immutability():
    lineage = LineageMap(
        vertex_parents={7: [ParentRef("B", 0.75), ParentRef(("A", 4), 0.25)], "unknown": None},
        face_parents={("face", 3): [ParentRef(990, 1)]},
    )
    fields = {
        "external.signal": {"values": {("A", 4): 0.2, "B": 0.8}, "mapping": "linear"},
        "label": {990: "support"},
    }
    before = deepcopy(fields)
    lineage_before = (dict(lineage.vertex_parents), dict(lineage.face_parents))
    specs = [_spec("external.signal"), _spec("label", "face", "CATEGORICAL")]
    first = inherit_fields(lineage, fields, specs)
    second = inherit_fields(lineage, fields, specs)
    assert first == second
    assert list(first.values) == ["external.signal", "label"]
    assert list(first.values["external.signal"]) == [7, "unknown"]
    assert first.values["external.signal"][7] == pytest.approx(0.65)
    assert fields == before
    assert (dict(lineage.vertex_parents), dict(lineage.face_parents)) == lineage_before
    first.values["label"][("face", 3)] = "changed"
    assert fields == before
    assert second.values["label"][("face", 3)] == "support"


def test_task05_displacement_measure_map_rule_budget_identity_inherit(box_mesh):
    before = json.dumps(box_mesh.__data__, sort_keys=True, allow_nan=False)
    attributes = analyze_vertex_attributes(box_mesh)
    fields = {
        "height": build_scalar_field(attributes, "normalized_height"),
        "confidence": {key: (key + 1) / 8 for key in box_mesh.vertices()},
        "part_type": {key: "support" for key in box_mesh.faces()},
    }
    fields_before = deepcopy(fields)
    plan = plan_execution(
        box_mesh, fields, Rule("upper vertices", "height", "vertex", "greater_than", 0.5),
        ExecutionBudget(max_faces=6, max_vertices=8, max_generation=1),
        cost_profile={"topology_preserving": True},
    )
    assert plan["status"] == "SAFE"
    transform = displace_vertices_along_normals(
        box_mesh, fields["height"]["values"], selected_vertices=plan["selected_vertices"], strength=0.02,
    )
    assert transform.moved_count == 4
    assert transform.mesh.to_vertices_and_faces()[0] != box_mesh.to_vertices_and_faces()[0]
    assert transform.mesh.to_vertices_and_faces()[1] == box_mesh.to_vertices_and_faces()[1]
    assert list(transform.mesh.vertices()) == list(box_mesh.vertices())
    assert list(transform.mesh.faces()) == list(box_mesh.faces())
    assert not transform.topology_changed
    transformed_before = json.dumps(transform.mesh.__data__, sort_keys=True, allow_nan=False)
    lineage = identity_lineage(transform.mesh)
    specs = [_spec("confidence"), _spec("part_type", "face", "CATEGORICAL"), _spec("height", mode="RECOMPUTE")]
    inherited = inherit_fields(lineage, fields, specs)
    assert inherited.values == {"confidence": fields["confidence"], "part_type": fields["part_type"]}
    assert inherited.recompute_fields == ["height"]
    assert inherited.unresolved_counts == {"confidence": 0, "part_type": 0}
    assert inherited == inherit_fields(lineage, fields, specs)
    assert fields == fields_before
    assert json.dumps(box_mesh.__data__, sort_keys=True, allow_nan=False) == before
    assert json.dumps(transform.mesh.__data__, sort_keys=True, allow_nan=False) == transformed_before
