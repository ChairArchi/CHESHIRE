import pytest

from cheshire import ExecutionBudget, check_execution_budget


def _check(budget, **kwargs):
    parameters = dict(input_faces=6, input_vertices=8, estimated_output_faces=24, estimated_output_vertices=26)
    parameters.update(kwargs)
    return check_execution_budget(budget, **parameters)


def test_exact_explicit_estimates_and_independent_limits():
    result = _check(ExecutionBudget(24, max_vertices=26, max_generation=2), current_generation=1)
    assert result == {"status": "SAFE", "budget_checks": {"face": "SAFE", "vertex": "SAFE", "generation": "SAFE"}, "reasons": []}
    result = _check(ExecutionBudget(23, max_vertices=25, max_generation=1), current_generation=1)
    assert result["status"] == "BLOCKED"
    assert set(result["budget_checks"].values()) == {"BLOCKED"}
    assert len(result["reasons"]) == 3


def test_unknown_estimates_and_input_count_checks():
    unknown = _check(ExecutionBudget(100, max_vertices=100), estimated_output_faces=None, estimated_output_vertices=None)
    assert unknown["status"] == "WARNING"
    assert unknown["budget_checks"] == {"face": "WARNING", "vertex": "WARNING", "generation": None}
    blocked = _check(ExecutionBudget(5, max_vertices=7), estimated_output_faces=None, estimated_output_vertices=None)
    assert blocked["status"] == "BLOCKED" and len(blocked["reasons"]) == 2
    assert all("input count" in reason for reason in blocked["reasons"])


@pytest.mark.parametrize("name,value", [
    ("input_faces", -1), ("input_vertices", True), ("estimated_output_faces", 1.5),
    ("estimated_output_vertices", float("inf")), ("estimated_output_vertices", "26"),
])
def test_invalid_explicit_counts_rejected(name, value):
    with pytest.raises(ValueError, match=name):
        _check(ExecutionBudget(100), **{name: value})
