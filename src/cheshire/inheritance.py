"""Semantic/continuous field inheritance without mesh or measurement access."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import fsum, isfinite
from numbers import Real

from .lineage import LineageMap, validate_lineage
from .normalization import _finite_number


@dataclass(frozen=True)
class FieldSpec:
    """An arbitrary field name, vertex/face domain, scalar/categorical kind,
    and CONTINUOUS/CATEGORICAL/RECOMPUTE mode (case-sensitive).
    """

    name: str
    domain: str
    kind: str
    inheritance_mode: str

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Field name must be a non-empty string.")
        if self.domain not in ("vertex", "face"):
            raise ValueError("Field domain must be vertex or face.")
        if self.kind not in ("scalar", "categorical"):
            raise ValueError("Field kind must be scalar or categorical.")
        if self.inheritance_mode not in ("CONTINUOUS", "CATEGORICAL", "RECOMPUTE"):
            raise ValueError("Unsupported inheritance mode.")
        required_kind = {"CONTINUOUS": "scalar", "CATEGORICAL": "categorical"}.get(self.inheritance_mode)
        if required_kind is not None and self.kind != required_kind:
            raise ValueError(f"{self.inheritance_mode} requires kind={required_kind!r}.")


@dataclass(frozen=True)
class InheritedFieldSet:
    """Fresh output mappings; recompute fields are omitted from values/counts."""

    values: dict
    recompute_fields: list[str]
    unresolved_counts: dict[str, int]
    warnings: list[str]


def inherit_fields(
    lineage: LineageMap,
    fields: Mapping,
    specs: Iterable[FieldSpec],
) -> InheritedFieldSet:
    """Inherit only specified fields, preserving child/spec/parent order.

    Fields are named parent-value mappings, or build_scalar_field metadata
    with a 'values' mapping. Exactly zero-weight parents do not participate
    in resolution; every positive-weight parent is required. Unknown lineage,
    missing fields/keys, null parents, and conflicting
    labels produce None, counted and reported in warnings. No incomplete-data
    renormalization occurs. Complete continuous weights are normalized for
    evaluation only; stored lineage stays unchanged. Scalars need not be
    normalized to [0, 1]. Constant fields remain exactly constant.

    All supplied values of inherited fields are validated, including unused
    parent entries. Categorical labels must be hashable; numeric labels must
    be finite. Labels are treated as immutable atomic values and retained
    directly, preserving enum and identity-label semantics.
    RECOMPUTE does not read source values and never measures output geometry.
    """
    problems = validate_lineage(lineage)
    if problems:
        raise ValueError("Invalid lineage: " + " ".join(problems))
    if not isinstance(fields, Mapping):
        raise ValueError("fields must be a mapping of field names to parent values.")
    specs = list(specs)
    seen = set()
    for spec in specs:
        if not isinstance(spec, FieldSpec):
            raise ValueError("Each specification must be a FieldSpec.")
        # Also validate records if a caller bypassed their frozen constructor.
        spec.__post_init__()
        if spec.name in seen:
            raise ValueError(f"Duplicate field specification: {spec.name!r}.")
        seen.add(spec.name)

    values, recompute, counts, warnings = {}, [], {}, []
    for spec in specs:
        if spec.inheritance_mode == "RECOMPUTE":
            recompute.append(spec.name)
            continue
        if spec.name not in fields:
            warnings.append(f"{spec.name}: source field is missing.")
        source = fields.get(spec.name, {})
        if not isinstance(source, Mapping):
            raise ValueError(f"{spec.name}: source field must be a mapping.")
        if isinstance(source.get("values"), Mapping):
            source = source["values"]
        source = {key: _source_value(value, spec) for key, value in source.items()}
        parents = lineage.vertex_parents if spec.domain == "vertex" else lineage.face_parents
        inherited = {}
        for child, refs in parents.items():
            refs = None if refs is None else tuple(ref for ref in refs if ref.weight > 0)
            if refs is None or any(source.get(ref.key) is None for ref in refs):
                inherited[child] = None
                continue
            samples = [source[ref.key] for ref in refs]
            if spec.inheritance_mode == "CONTINUOUS":
                inherited[child] = _weighted_scalar(refs, samples, spec.name)
            else:
                agreed = all(value == samples[0] for value in samples[1:])
                inherited[child] = samples[0] if agreed else None
        values[spec.name] = inherited
        counts[spec.name] = sum(value is None for value in inherited.values())
        if counts[spec.name]:
            warnings.append(
                f"{spec.name}: {counts[spec.name]} unresolved children "
                "(unknown lineage, missing/null parent data, or conflicting labels)."
            )
    return InheritedFieldSet(values, recompute, counts, warnings)


def _source_value(value, spec):
    if value is None:
        return None
    if spec.inheritance_mode == "CONTINUOUS":
        return _finite_number(value, f"{spec.name} parent value")
    if isinstance(value, Real):
        _finite_number(value, f"{spec.name} categorical value")
    try:
        hash(value)
    except TypeError as error:
        raise ValueError(f"{spec.name}: categorical labels must be hashable.") from error
    return value


def _weighted_scalar(refs, samples, name):
    # Preserve constant fields, including subnormal floats. Otherwise fsum
    # retains small contributions when larger positive/negative ones cancel.
    try:
        if all(value == samples[0] for value in samples[1:]):
            result = samples[0]
        else:
            total = fsum(ref.weight for ref in refs)
            result = fsum((ref.weight / total) * value for ref, value in zip(refs, samples))
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name}: inherited scalar is not finite.") from error
    if not isfinite(result):
        raise ValueError(f"{name}: inherited scalar is not finite.")
    return result
