"""Deterministic min-max normalization with optional percentile clipping."""

from collections.abc import Iterable, Mapping
from math import floor, isfinite
from numbers import Real


def normalize_values(
    values: Iterable[Real | None] | Mapping,
    lower_percentile: float = 0.0,
    upper_percentile: float = 100.0,
) -> list[float | None] | dict:
    """Normalize finite real numbers to [0, 1], preserving None and keys.

    Percentiles use linear interpolation between sorted non-null samples.
    Values outside the percentile interval are clipped to its endpoints.
    Constant values (including collapsed percentile intervals) map to 0.0.
    Empty inputs stay empty; all-null inputs stay null. Booleans are treated
    as 0/1. Invalid numbers or percentile parameters raise ValueError.
    """
    lower = _finite_number(lower_percentile, "lower_percentile")
    upper = _finite_number(upper_percentile, "upper_percentile")
    if not 0.0 <= lower < upper <= 100.0:
        raise ValueError("Percentiles must satisfy 0 <= lower < upper <= 100.")

    keyed = isinstance(values, Mapping)
    samples = list(values.values() if keyed else values)
    samples = [None if value is None else _finite_number(value, "value") for value in samples]
    ordered = sorted(value for value in samples if value is not None)
    if ordered:
        low = _percentile(ordered, lower)
        high = _percentile(ordered, upper)
        result = [None if value is None else _normalize(value, low, high) for value in samples]
    else:
        result = samples
    return dict(zip(values, result)) if keyed else result


def _finite_number(value, name: str) -> float:
    if not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number.")
    try:
        number = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be a finite real number.") from error
    if not isfinite(number):
        raise ValueError(f"{name} must be a finite real number.")
    return number


def _percentile(ordered: list[float], percentile: float) -> float:
    position = (len(ordered) - 1) * (percentile / 100.0)
    index = floor(position)
    weight = position - index
    left = ordered[index]
    right = ordered[min(index + 1, len(ordered) - 1)]
    if left == right:
        return left
    # A weighted sum avoids overflowing right - left for opposite extremes.
    return left * (1.0 - weight) + right * weight


def _normalize(value: float, low: float, high: float) -> float:
    if low == high or value <= low:
        return 0.0
    if value >= high:
        return 1.0
    span = high - low
    if isfinite(span):
        result = (value - low) / span
    else:
        result = (value / 2.0 - low / 2.0) / (high / 2.0 - low / 2.0)
    return min(1.0, max(0.0, result))
