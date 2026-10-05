from copy import deepcopy
from math import isfinite

import pytest

from cheshire import normalize_values


@pytest.mark.parametrize("values, expected", [
    ([10, 15, 20], [0.0, 0.5, 1.0]),
    ([-10, 0, 10], [0.0, 0.5, 1.0]),
    ([7, 7, 7], [0.0, 0.0, 0.0]),
    ([0], [0.0]),
    ([None, 10, 15, None, 20], [None, 0.0, 0.5, None, 1.0]),
    ([None, None], [None, None]),
    ([], []),
    ([False, True], [0.0, 1.0]),
    ([-1e308, 0, 1e308], [0.0, 0.5, 1.0]),
    ([0, 5e-324, 1e-323], [0.0, 0.5, 1.0]),
])
def test_normalization(values, expected):
    before = deepcopy(values)
    assert normalize_values(values) == expected
    assert values == before


def test_percentile_clipping_uses_linear_interpolation():
    assert normalize_values([0, 10, 20, 30, 100], 25, 75) == [0, 0, 0.5, 1, 1]
    # With three samples the 25th/75th percentiles interpolate to 5 and 15.
    assert normalize_values([0, 10, 20], 25, 75) == [0, 0.5, 1]


def test_percentiles_exclude_nulls():
    assert normalize_values([None, 0, 10, 20, None], 25, 75) == [None, 0, 0.5, 1, None]


def test_collapsed_percentile_interval_maps_to_zero():
    assert normalize_values([0, 5, 5, 5, 100], 25, 75) == [0, 0, 0, 0, 0]


def test_keyed_mapping_preserves_keys_and_order():
    values = {42: 20, "isolated": None, -7: 10, (1, 2): 15}
    before = deepcopy(values)
    result = normalize_values(values)
    assert result == {42: 1, "isolated": None, -7: 0, (1, 2): 0.5}
    assert list(result) == list(values)
    assert values == before
    assert normalize_values({}) == {}


def test_tuple_and_generator_inputs():
    assert normalize_values((2, 4, 6)) == [0, 0.5, 1]
    assert normalize_values(value for value in [2, 4, 6]) == [0, 0.5, 1]


@pytest.mark.parametrize("lower, upper", [
    (-1, 100), (0, 101), (50, 50), (75, 25),
    (float("nan"), 100), (0, float("inf")), ("0", 100),
])
def test_invalid_percentiles_are_rejected_even_for_empty_input(lower, upper):
    with pytest.raises(ValueError, match="Percentiles|percentile"):
        normalize_values([], lower, upper)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), "2", 2j, 10**400])
def test_invalid_values_are_rejected(value):
    with pytest.raises(ValueError, match="finite real number"):
        normalize_values([value])


@pytest.mark.parametrize("lower, upper", [(0, 100), (5, 95), (25, 75)])
def test_results_are_deterministic_finite_and_bounded(lower, upper):
    values = [-1e308, -100, None, 0, 0.001, 17, 100, 1e308]
    result = normalize_values(values, lower, upper)
    assert result == normalize_values(values, lower, upper)
    assert all(isfinite(value) and 0 <= value <= 1 for value in result if value is not None)
