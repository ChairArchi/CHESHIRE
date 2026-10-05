"""Pure scalar mappings and lightweight, explicit field metadata."""

from math import pi, sin

from .normalization import _finite_number, normalize_values


def linear(value: float | None) -> float | None:
    """Identity on [0, 1]; preserve None."""
    return _normalized_input(value)


def inverse(value: float | None) -> float | None:
    """Map x to 1 - x on [0, 1]; preserve None."""
    value = _normalized_input(value)
    return None if value is None else 1.0 - value


def smoothstep(value: float | None) -> float | None:
    """Map x to x*x*(3 - 2*x) on [0, 1]; preserve None."""
    value = _normalized_input(value)
    return None if value is None else value * value * (3.0 - 2.0 * value)


def power(value: float | None, exponent: float = 2.0) -> float | None:
    """Map x to x**exponent; exponent must be finite and positive."""
    exponent = _positive_exponent(exponent)
    value = _normalized_input(value)
    return None if value is None else value ** exponent


def sine(value: float | None) -> float | None:
    """Monotonic half-sine sin(x*pi/2) on [0, 1]; preserve None."""
    value = _normalized_input(value)
    return None if value is None else sin(value * pi / 2.0)


def map_attribute(
    attributes: dict,
    attribute_name: str,
    mapping: str = "linear",
    lower_percentile: float = 0.0,
    upper_percentile: float = 100.0,
    **mapping_parameters,
) -> dict:
    """Extract, normalize, and map one measured attribute, preserving keys.

    Missing attributes, unknown mappings/parameters, and invalid numbers raise
    ValueError. Constants normalize to 0.0 before applying the mapping. Inputs
    and mesh geometry are never modified.
    """
    function, parameters = _mapping_configuration(mapping, mapping_parameters)
    if not isinstance(attribute_name, str) or not attribute_name:
        raise ValueError("attribute_name must be a non-empty string.")
    extracted = {}
    for key, record in attributes.items():
        if attribute_name not in record:
            raise ValueError(f"Vertex {key!r} has no attribute {attribute_name!r}.")
        extracted[key] = record[attribute_name]
    normalized = normalize_values(extracted, lower_percentile, upper_percentile)
    return {key: function(value, **parameters) for key, value in normalized.items()}


def build_scalar_field(
    attributes: dict,
    attribute_name: str,
    mapping: str = "linear",
    lower_percentile: float = 0.0,
    upper_percentile: float = 100.0,
    **mapping_parameters,
) -> dict:
    """Build a field with its source attribute, mapping, parameters, and values.

    Records percentile settings and the effective power exponent, including
    defaults. This is field-generation metadata only, without semantic tags
    or provenance inheritance.
    """
    _, parameters = _mapping_configuration(mapping, mapping_parameters)
    values = map_attribute(
        attributes, attribute_name, mapping, lower_percentile, upper_percentile, **parameters
    )
    return {
        "attribute": attribute_name,
        "mapping": mapping,
        "parameters": {
            "lower_percentile": float(lower_percentile),
            "upper_percentile": float(upper_percentile),
            **parameters,
        },
        "values": values,
    }


def _normalized_input(value) -> float | None:
    if value is None:
        return None
    value = _finite_number(value, "Mapping input")
    if not 0.0 <= value <= 1.0:
        raise ValueError("Mapping input must be in [0, 1].")
    return value


def _positive_exponent(exponent) -> float:
    exponent = _finite_number(exponent, "exponent")
    if exponent <= 0.0:
        raise ValueError("Power exponent must be > 0.")
    return exponent


def _mapping_configuration(mapping, parameters):
    functions = {
        "linear": linear,
        "inverse": inverse,
        "smoothstep": smoothstep,
        "power": power,
        "sine": sine,
    }
    if not isinstance(mapping, str) or mapping not in functions:
        raise ValueError(f"Unknown mapping {mapping!r}; choose from {', '.join(functions)}.")
    allowed = {"exponent"} if mapping == "power" else set()
    unknown = set(parameters) - allowed
    if unknown:
        raise ValueError(f"Unsupported parameters for {mapping}: {', '.join(sorted(unknown))}.")
    effective = {"exponent": _positive_exponent(parameters.get("exponent", 2.0))} if allowed else {}
    return functions[mapping], effective
