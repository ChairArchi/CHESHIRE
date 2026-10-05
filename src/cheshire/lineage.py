"""Geometry-independent child-to-parent lineage; no geometry operations."""

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from math import fsum, isclose
from types import MappingProxyType

from .normalization import _finite_number


WEIGHT_SUM_TOLERANCE = 1e-9


@dataclass(frozen=True)
class ParentRef:
    """A hashable parent key and finite, non-negative contribution weight."""

    key: Hashable
    weight: float

    def __post_init__(self):
        try:
            hash(self.key)
        except TypeError as error:
            raise ValueError("Parent key must be hashable.") from error
        weight = _finite_number(self.weight, "Parent weight")
        if weight < 0:
            raise ValueError("Parent weight must be non-negative.")
        object.__setattr__(self, "weight", weight)


@dataclass(frozen=True)
class LineageMap:
    """Ordered vertex/face lineage, independent of any mesh backend.

    None explicitly means unknown parents; an empty parent sequence is invalid.
    Children follow mapping insertion order, parents follow sequence order.
    Keys are preserved without sorting or copying, including mixed key types.
    Supplied mappings/sequences are copied into read-only maps and tuples.
    Weight sums use absolute tolerance 1e-9, zero relative tolerance. Accepted
    weights are stored unchanged, never normalized or clipped in this map.
    """

    vertex_parents: Mapping[Hashable, Sequence[ParentRef] | None] = field(default_factory=dict)
    face_parents: Mapping[Hashable, Sequence[ParentRef] | None] = field(default_factory=dict)

    def __post_init__(self):
        problems = validate_lineage(self)
        if problems:
            raise ValueError("Invalid lineage: " + " ".join(problems))
        for domain in ("vertex_parents", "face_parents"):
            parents = getattr(self, domain)
            snapshot = {key: None if refs is None else tuple(refs) for key, refs in parents.items()}
            object.__setattr__(self, domain, MappingProxyType(snapshot))


def validate_lineage(lineage: LineageMap) -> list[str]:
    """Report invalid keys, parent sets, duplicates, weights, and sums; [] is valid."""
    if not isinstance(lineage, LineageMap):
        return ["Expected a LineageMap."]
    problems = []
    for domain in ("vertex_parents", "face_parents"):
        mapping = getattr(lineage, domain)
        if not isinstance(mapping, Mapping):
            problems.append(f"{domain} must be a mapping.")
            continue
        for child, refs in mapping.items():
            label = f"{domain}[{child!r}]"
            try:
                hash(child)
            except TypeError:
                problems.append(f"{label}: child key must be hashable.")
            if refs is None:
                continue
            if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes)) or not refs:
                problems.append(f"{label}: use a non-empty ordered parent sequence or None for unknown.")
                continue
            seen, weights = set(), []
            for ref in refs:
                if not isinstance(ref, ParentRef):
                    problems.append(f"{label}: every parent must be a ParentRef.")
                    continue
                try:
                    if ref.key in seen:
                        problems.append(f"{label}: duplicate parent key {ref.key!r}.")
                    seen.add(ref.key)
                except TypeError:
                    problems.append(f"{label}: parent key must be hashable.")
                try:
                    weight = _finite_number(ref.weight, "Parent weight")
                    if weight < 0:
                        raise ValueError("Parent weight must be non-negative.")
                    weights.append(weight)
                except ValueError as error:
                    problems.append(f"{label}: {error}")
            if len(weights) == len(refs):
                try:
                    valid_sum = isclose(fsum(weights), 1.0, rel_tol=0.0, abs_tol=WEIGHT_SUM_TOLERANCE)
                except OverflowError:
                    valid_sum = False
                if not valid_sum:
                    problems.append(f"{label}: weights must sum to 1 within {WEIGHT_SUM_TOLERANCE:g}.")
    return problems


def identity_lineage(mesh) -> LineageMap:
    """Map each mesh vertex/face key to itself with weight 1; never mutate mesh."""
    return LineageMap(
        vertex_parents={key: [ParentRef(key, 1.0)] for key in mesh.vertices()},
        face_parents={key: [ParentRef(key, 1.0)] for key in mesh.faces()},
    )
