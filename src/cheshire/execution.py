"""Dry-run execution estimates and explicit computational budget checks."""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from numbers import Integral

from compas.datastructures import Mesh

from .rules import Rule, _mesh_field_values, evaluate_face_rule, evaluate_vertex_rule
from .validation import validate_mesh


@dataclass(frozen=True)
class ExecutionBudget:
    """Maximum counts and an exclusive generation limit; None means no limit.

    Limits are non-negative integers. Counts equal to their limits are allowed;
    current_generation >= max_generation is blocked. Zero is a valid budget.
    """

    max_faces: int
    max_vertices: int | None = None
    max_generation: int | None = None

    def __post_init__(self):
        for name in ("max_faces", "max_vertices", "max_generation"):
            value = getattr(self, name)
            if value is None and name != "max_faces":
                continue
            object.__setattr__(self, name, _count(value, name))


def plan_execution(
    mesh: Mesh,
    fields: Mapping,
    rule: Rule,
    budget: ExecutionBudget,
    current_generation: int = 0,
    cost_profile: Mapping | None = None,
) -> dict:
    """Select from a named field and estimate costs; never execute an operator.

    fields maps arbitrary field names to vertex-value mappings or scalar-field
    metadata returned by build_scalar_field(). Missing vertex values remain
    unavailable. Unknown field names or invalid profiles raise ValueError.

    A topology-preserving profile keeps both counts. A non-preserving profile
    needs an explicit positive integer replacement_faces_per_selected_face.
    Its face estimate applies only to face selections; vertex counts remain
    unknown. No cost is inferred from an operator's name. Missing cost profiles
    or incompatible selections leave estimates None.

    Status is BLOCKED when any budget is exceeded, WARNING when a configured
    count budget cannot be verified, otherwise SAFE. Face/vertex/generation
    checks are independent. None in budget_checks means no limit was requested.
    SAFE is a budget assessment of supplied assumptions, not permission to
    transform geometry or a guarantee of an operator's actual cost.
    """
    if not isinstance(rule, Rule):
        raise ValueError("rule must be a Rule.")
    if not isinstance(budget, ExecutionBudget):
        raise ValueError("budget must be an ExecutionBudget.")
    generation = _count(current_generation, "current_generation")
    profile = _cost_profile(cost_profile)
    problems = validate_mesh(mesh)
    if problems:
        raise ValueError("Invalid mesh: " + " ".join(problems))
    if not isinstance(fields, Mapping) or rule.field not in fields:
        raise ValueError(f"Scalar field {rule.field!r} is unavailable.")
    source = fields[rule.field]
    if not isinstance(source, Mapping):
        raise ValueError(f"Scalar field {rule.field!r} must be a mapping.")
    if "values" in source:
        source = source["values"]
    values = _mesh_field_values(mesh, source)
    selection = (
        evaluate_vertex_rule(values, rule) if rule.target == "vertex"
        else evaluate_face_rule(mesh, values, rule)
    )
    input_faces = mesh.number_of_faces()
    input_vertices = mesh.number_of_vertices()
    output_faces, output_vertices, estimate_note = _estimate(
        input_faces, input_vertices, selection, profile
    )
    assessment = check_execution_budget(
        budget, input_faces=input_faces, input_vertices=input_vertices,
        estimated_output_faces=output_faces, estimated_output_vertices=output_vertices,
        current_generation=generation,
    )
    return {
        "dry_run": True,
        "generation": generation,
        "input_faces": input_faces,
        "input_vertices": input_vertices,
        "rule": asdict(rule),
        "selection": selection,
        "selected_faces": selection["selected_keys"].copy() if rule.target == "face" else [],
        "selected_vertices": selection["selected_keys"].copy() if rule.target == "vertex" else [],
        "selected_fraction": selection["selected_fraction"],
        "operator": rule.operator,
        "cost_profile": profile,
        "estimated_output_faces": output_faces,
        "estimated_output_vertices": output_vertices,
        "estimate_note": estimate_note,
        "face_budget": budget.max_faces,
        "vertex_budget": budget.max_vertices,
        "generation_budget": budget.max_generation,
        **assessment,
    }


def check_execution_budget(
    budget: ExecutionBudget,
    *,
    input_faces: int,
    input_vertices: int,
    estimated_output_faces: int | None,
    estimated_output_vertices: int | None,
    current_generation: int = 0,
) -> dict:
    """Check explicit counts using the same semantics as plan_execution.

    Returns status, budget_checks, and reasons. None means an unknown estimate;
    a configured count limit then produces WARNING. Never executes geometry.
    """
    if not isinstance(budget, ExecutionBudget):
        raise ValueError("budget must be an ExecutionBudget.")
    generation = _count(current_generation, "current_generation")
    input_faces = _count(input_faces, "input_faces")
    input_vertices = _count(input_vertices, "input_vertices")
    output_faces = None if estimated_output_faces is None else _count(estimated_output_faces, "estimated_output_faces")
    output_vertices = None if estimated_output_vertices is None else _count(estimated_output_vertices, "estimated_output_vertices")
    checks, reasons = {}, []
    for label, current, estimated, maximum in (
        ("face", input_faces, output_faces, budget.max_faces),
        ("vertex", input_vertices, output_vertices, budget.max_vertices),
    ):
        check, reason = _count_budget(label, current, estimated, maximum)
        checks[label] = check
        if reason:
            reasons.append(reason)
    if budget.max_generation is None:
        checks["generation"] = None
    elif generation >= budget.max_generation:
        checks["generation"] = "BLOCKED"
        reasons.append(f"Generation budget: {generation} >= limit {budget.max_generation}.")
    else:
        checks["generation"] = "SAFE"
    status = "BLOCKED" if "BLOCKED" in checks.values() else (
        "WARNING" if "WARNING" in checks.values() else "SAFE"
    )
    return {"budget_checks": checks, "status": status, "reasons": reasons}


def _count(value, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}.")
    return int(value)


def _cost_profile(profile: Mapping | None) -> dict | None:
    if profile is None:
        return None
    if not isinstance(profile, Mapping):
        raise ValueError("cost_profile must be a mapping or None.")
    profile = deepcopy(dict(profile))
    allowed = {"topology_preserving", "replacement_faces_per_selected_face"}
    if set(profile) - allowed:
        raise ValueError("Cost profile contains unsupported parameters.")
    if not isinstance(profile.get("topology_preserving"), bool):
        raise ValueError("Cost profile requires a boolean topology_preserving.")
    if profile["topology_preserving"]:
        if "replacement_faces_per_selected_face" in profile:
            raise ValueError("A topology-preserving profile cannot specify face replacement growth.")
    else:
        name = "replacement_faces_per_selected_face"
        profile[name] = _count(profile.get(name), name, minimum=1)
    return profile


def _estimate(input_faces, input_vertices, selection, profile):
    if profile is None:
        return None, None, "No cost profile supplied; output counts are unknown."
    if profile["topology_preserving"]:
        return input_faces, input_vertices, "Count estimate assumes the supplied topology-preserving profile."
    if selection["target"] != "face":
        return None, None, "Selected vertices do not determine face replacement counts."
    selected = selection["selected_count"]
    output_faces = input_faces - selected + selected * profile["replacement_faces_per_selected_face"]
    return output_faces, None, "Face estimate uses the explicit replacement profile; output vertex count is unknown."


def _count_budget(label, current, estimated, maximum):
    if maximum is None:
        return None, None
    if current > maximum:
        return "BLOCKED", f"{label.capitalize()} budget: input count {current} exceeds limit {maximum}."
    if estimated is None:
        return "WARNING", f"{label.capitalize()} budget: output count is unknown; limit {maximum} cannot be verified."
    if estimated > maximum:
        return "BLOCKED", f"{label.capitalize()} budget: estimated output {estimated} exceeds limit {maximum}."
    return "SAFE", None
