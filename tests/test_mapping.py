from copy import deepcopy
from math import isfinite, sqrt

import pytest

from cheshire import (
    analyze_vertex_attributes, build_scalar_field, inverse, linear,
    map_attribute, normalize_values, power, sine, smoothstep,
)


FUNCTIONS = [linear, inverse, smoothstep, power, sine]


@pytest.mark.parametrize("function, expected", [
    (linear, [0, 0.25, 0.5, 1]),
    (inverse, [1, 0.75, 0.5, 0]),
    (smoothstep, [0, 0.15625, 0.5, 1]),
    (power, [0, 0.0625, 0.25, 1]),
    (sine, [0, 0.3826834323650898, sqrt(2) / 2, 1]),
])
def test_mapping_formulas(function, expected):
    assert [function(value) for value in [0, 0.25, 0.5, 1]] == pytest.approx(expected)


@pytest.mark.parametrize("function", FUNCTIONS)
def test_mappings_preserve_null(function):
    assert function(None) is None


def test_power_accepts_positive_fractional_exponents():
    assert power(0.25, exponent=0.5) == 0.5
    assert power(0.5, exponent=3) == 0.125


@pytest.mark.parametrize("exponent", [0, -1, float("nan"), float("inf"), float("-inf"), "2", 2j])
@pytest.mark.parametrize("value", [0.5, None])
def test_invalid_power_exponents(value, exponent):
    with pytest.raises(ValueError, match="exponent"):
        power(value, exponent)


@pytest.mark.parametrize("function", FUNCTIONS)
@pytest.mark.parametrize("value", [-0.01, 1.01, float("nan"), float("inf"), "0.5", 1j])
def test_mappings_reject_invalid_inputs(function, value):
    with pytest.raises(ValueError, match="Mapping input"):
        function(value)


@pytest.mark.parametrize("function", FUNCTIONS)
def test_mappings_are_deterministic_monotonic_and_bounded(function):
    inputs = [index / 1000 for index in range(1001)]
    results = [function(value) for value in inputs]
    assert results == [function(value) for value in inputs]
    assert all(isfinite(value) and 0 <= value <= 1 for value in results)
    assert results == sorted(results, reverse=(function is inverse))


@pytest.mark.parametrize("mapping", ["linear", "inverse", "smoothstep", "power", "sine"])
def test_map_attribute_normalizes_preserves_nulls_and_keys(mapping):
    attributes = {8: {"value": 10}, -1: {"value": 15}, 42: {"value": 20}, 99: {"value": None}}
    before = deepcopy(attributes)
    result = map_attribute(attributes, "value", mapping=mapping)
    function = dict(zip(["linear", "inverse", "smoothstep", "power", "sine"], FUNCTIONS))[mapping]
    assert result == {8: function(0), -1: function(0.5), 42: function(1), 99: None}
    assert list(result) == list(attributes)
    assert attributes == before
    assert result == map_attribute(attributes, "value", mapping=mapping)


def test_map_attribute_combines_clipping_and_mapping():
    attributes = {key: {"value": value} for key, value in enumerate([0, 10, 20, 30, 100])}
    assert map_attribute(attributes, "value", "power", 25, 75, exponent=2) == {
        0: 0, 1: 0, 2: 0.25, 3: 1, 4: 1,
    }


def test_empty_all_null_constant_and_boolean_attributes():
    assert map_attribute({}, "value") == {}
    assert map_attribute({2: {"value": None}}, "value", mapping="sine") == {2: None}
    assert map_attribute({2: {"value": 7}, 3: {"value": 7}}, "value") == {2: 0, 3: 0}
    assert map_attribute({2: {"value": 7}, 3: {"value": 7}}, "value", "inverse") == {2: 1, 3: 1}
    assert map_attribute({2: {"boundary": False}, 3: {"boundary": True}}, "boundary") == {2: 0, 3: 1}


@pytest.mark.parametrize("api", [map_attribute, build_scalar_field])
@pytest.mark.parametrize("mapping", ["unknown", None, ["linear"]])
def test_invalid_mapping_name(api, mapping):
    with pytest.raises(ValueError, match="Unknown mapping"):
        api({}, "value", mapping=mapping)


@pytest.mark.parametrize("api", [map_attribute, build_scalar_field])
@pytest.mark.parametrize("exponent", [0, -2, float("inf"), float("nan")])
def test_high_level_invalid_exponent(api, exponent):
    with pytest.raises(ValueError, match="exponent"):
        api({}, "value", mapping="power", exponent=exponent)


@pytest.mark.parametrize("api", [map_attribute, build_scalar_field])
def test_unknown_parameters_are_reported(api):
    with pytest.raises(ValueError, match="Unsupported parameters"):
        api({}, "value", mapping="linear", exponent=2)
    with pytest.raises(ValueError, match="Unsupported parameters"):
        api({}, "value", mapping="power", frequency=2)


@pytest.mark.parametrize("api", [map_attribute, build_scalar_field])
def test_missing_attribute_and_invalid_percentile_are_reported(api):
    with pytest.raises(ValueError, match="no attribute"):
        api({7: {"other": 1}}, "missing")
    with pytest.raises(ValueError, match="non-empty string"):
        api({}, "")
    with pytest.raises(ValueError, match="Percentiles"):
        api({}, "value", lower_percentile=90, upper_percentile=10)
    with pytest.raises(ValueError, match="finite real number"):
        api({7: {"value": float("nan")}}, "value")


def test_field_metadata_records_effective_parameters():
    attributes = {3: {"value": 0}, 7: {"value": 10}, 9: {"value": None}}
    assert build_scalar_field(attributes, "value", "power", 5, 95, exponent=3) == {
        "attribute": "value",
        "mapping": "power",
        "parameters": {"lower_percentile": 5.0, "upper_percentile": 95.0, "exponent": 3.0},
        "values": {3: 0, 7: 1, 9: None},
    }
    assert build_scalar_field(attributes, "value", "power")["parameters"]["exponent"] == 2.0
    assert build_scalar_field(attributes, "value")["parameters"] == {
        "lower_percentile": 0.0, "upper_percentile": 100.0,
    }


def test_grid_integration_measures_normalizes_maps_and_records_metadata(grid_mesh):
    before = deepcopy(grid_mesh.__data__)
    attributes = analyze_vertex_attributes(grid_mesh)
    extracted = {key: record["boundary_distance"] for key, record in attributes.items()}
    normalized = normalize_values(extracted)
    mapped = map_attribute(attributes, "boundary_distance", mapping="power", exponent=2)
    field = build_scalar_field(attributes, "boundary_distance", mapping="power", exponent=2)
    assert [extracted[key] for key in (0, 6, 12)] == [0, 1, 2]
    assert [normalized[key] for key in (0, 6, 12)] == [0, 0.5, 1]
    assert [mapped[key] for key in (0, 6, 12)] == [0, 0.25, 1]
    assert field["values"] == mapped
    assert field == build_scalar_field(
        analyze_vertex_attributes(grid_mesh), "boundary_distance", mapping="power", exponent=2
    )
    assert grid_mesh.__data__ == before


@pytest.mark.parametrize("fixture", ["box_mesh", "open_mesh", "grid_mesh"])
@pytest.mark.parametrize("mapping", ["linear", "inverse", "smoothstep", "power", "sine"])
def test_every_measured_attribute_maps_to_a_stable_bounded_field(fixture, mapping, request):
    mesh = request.getfixturevalue(fixture)
    before = deepcopy(mesh.__data__)
    attributes = analyze_vertex_attributes(mesh)
    before_attributes = deepcopy(attributes)
    for name in next(iter(attributes.values())):
        field = build_scalar_field(attributes, name, mapping=mapping)
        assert field == build_scalar_field(attributes, name, mapping=mapping)
        assert set(field["values"]) == set(mesh.vertices())
        for key, value in field["values"].items():
            if attributes[key][name] is None:
                assert value is None
            else:
                assert isfinite(value) and 0 <= value <= 1
    assert attributes == before_attributes
    assert mesh.__data__ == before
