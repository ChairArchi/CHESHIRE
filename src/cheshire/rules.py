"""Deterministic scalar-field selection without geometry mutation."""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from math import fsum

from compas.datastructures import Mesh

from .normalization import _finite_number


@dataclass(frozen=True)
class Rule:
    """Explicit selection rule; field and operator names are arbitrary labels.

    Thresholds must be finite real numbers. ``between`` includes both ends
    and requires upper_threshold >= threshold. Other comparisons do not use
    upper_threshold. Parameters are copied metadata, never executed.
    """

    name: str
    field: str
    target: str
    comparison: str
    threshold: float
    upper_threshold: float | None = None
    operator: str | None = None
    parameters: dict | None = None
    face_reduction: str = "mean"

    def __post_init__(self):
        for label in ("name", "field"):
            value = getattr(self, label)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Rule {label} must be a non-empty string.")
        if self.target not in ("vertex", "face"):
            raise ValueError("Rule target must be 'vertex' or 'face'.")
        if self.comparison not in (
            "greater_than", "greater_equal", "less_than", "less_equal", "between"
        ):
            raise ValueError(f"Invalid rule comparison: {self.comparison!r}.")
        if self.face_reduction not in ("mean", "min", "max"):
            raise ValueError("face_reduction must be 'mean', 'min', or 'max'.")
        threshold = _rule_number(self.threshold, "threshold")
        object.__setattr__(self, "threshold", threshold)
        if self.comparison == "between":
            upper = _rule_number(self.upper_threshold, "upper_threshold")
            if upper < threshold:
                raise ValueError("upper_threshold must be >= threshold for 'between'.")
            object.__setattr__(self, "upper_threshold", upper)
        elif self.upper_threshold is not None:
            raise ValueError("upper_threshold is only supported for 'between'.")
        if self.operator is not None and (
            not isinstance(self.operator, str) or not self.operator.strip()
        ):
            raise ValueError("Rule operator must be a non-empty string or None.")
        if self.parameters is not None:
            if not isinstance(self.parameters, Mapping):
                raise ValueError("Rule parameters must be a mapping or None.")
            object.__setattr__(self, "parameters", deepcopy(dict(self.parameters)))


def evaluate_vertex_rule(field_values: Mapping, rule: Rule) -> dict:
    """Select keys from finite scalar values; None is always ineligible.

    Results preserve input key order. selected_fraction uses eligible_count
    as its denominator (zero when none are eligible). rejected_count counts
    eligible values failing the comparison; null_count counts ineligible values.
    Empty inputs return zero counts and fraction. Inputs are never modified.
    """
    _require_target(rule, "vertex")
    return _selection(_validated_values(field_values), rule)


def evaluate_face_rule(mesh: Mesh, field_values: Mapping, rule: Rule) -> dict:
    """Reduce each face's available vertex scalars with mean/min/max, then select.

    Missing keys are unavailable, like None; no values are filled in. A face
    with no available scalars is ineligible. Partially populated faces use only
    their available values. Results preserve mesh face order. Unknown vertex
    keys are rejected to avoid evaluating a field against the wrong mesh.
    """
    _require_target(rule, "face")
    values = _mesh_field_values(mesh, field_values)
    face_values = {}
    for face in mesh.faces():
        available = [values[key] for key in mesh.face_vertices(face) if values[key] is not None]
        if not available:
            face_values[face] = None
        elif rule.face_reduction == "min":
            face_values[face] = min(available)
        elif rule.face_reduction == "max":
            face_values[face] = max(available)
        else:
            scale = max(abs(value) for value in available)
            face_values[face] = 0.0 if scale == 0.0 else scale * min(
                1.0, max(-1.0, fsum(value / scale for value in available) / len(available))
            )
    return _selection(face_values, rule)


def _require_target(rule, target: str) -> None:
    if not isinstance(rule, Rule):
        raise ValueError("rule must be a Rule.")
    if rule.target != target:
        raise ValueError(f"This evaluator requires a {target!r} rule target.")


def _rule_number(value, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"Rule {name} must be a finite real number, not a boolean.")
    return _finite_number(value, f"Rule {name}")


def _validated_values(field_values: Mapping) -> dict:
    if not isinstance(field_values, Mapping):
        raise ValueError("field_values must be a mapping of keys to scalars or None.")
    return {
        key: None if value is None else _finite_number(value, f"Field value at {key!r}")
        for key, value in field_values.items()
    }


def _mesh_field_values(mesh: Mesh, field_values: Mapping) -> dict:
    values = _validated_values(field_values)
    keys = list(mesh.vertices())
    if set(values) - set(keys):
        raise ValueError("Field contains vertex keys absent from the mesh.")
    return {key: values.get(key) for key in keys}


def _selection(values: dict, rule: Rule) -> dict:
    selected = []
    eligible = 0
    for key, value in values.items():
        if value is None:
            continue
        eligible += 1
        if _matches(value, rule):
            selected.append(key)
    return {
        "target": rule.target,
        "selected_keys": selected,
        "selected_count": len(selected),
        "total_count": len(values),
        "eligible_count": eligible,
        "selected_fraction": len(selected) / eligible if eligible else 0.0,
        "rejected_count": eligible - len(selected),
        "null_count": len(values) - eligible,
    }


def _matches(value: float, rule: Rule) -> bool:
    if rule.comparison == "greater_than":
        return value > rule.threshold
    if rule.comparison == "greater_equal":
        return value >= rule.threshold
    if rule.comparison == "less_than":
        return value < rule.threshold
    if rule.comparison == "less_equal":
        return value <= rule.threshold
    return rule.threshold <= value <= rule.upper_threshold
