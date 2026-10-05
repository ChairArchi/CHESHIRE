from dataclasses import replace

import pytest

from cheshire import LineageMap, ParentRef, identity_lineage, validate_lineage_coverage


def test_identity_coverage_is_complete_and_read_only(box_mesh):
    before = box_mesh.__data__
    lineage = identity_lineage(box_mesh)
    assert validate_lineage_coverage(box_mesh, box_mesh, lineage) == []
    assert box_mesh.__data__ == before


@pytest.mark.parametrize("domain", ["vertex", "face"])
@pytest.mark.parametrize("problem", ["missing", "extra", "parent", "unknown"])
def test_coverage_distinguishes_child_and_parent_problems(open_mesh, domain, problem):
    lineage = identity_lineage(open_mesh)
    name = domain + "_parents"
    mapping = dict(getattr(lineage, name))
    key = next(iter(mapping))
    expected = {"missing": "Missing", "extra": "Extra", "parent": "Invalid", "unknown": "Unknown"}[problem]
    if problem == "missing":
        del mapping[key]
    elif problem == "extra":
        mapping[999] = [ParentRef(key, 1)]
    elif problem == "parent":
        mapping[key] = [ParentRef(999, 1)]
    else:
        mapping[key] = None
    altered = replace(lineage, **{name: mapping})
    problems = validate_lineage_coverage(open_mesh, open_mesh, altered)
    assert len(problems) == 1
    assert expected in problems[0] and domain in problems[0]


def test_normal_lineage_validation_is_required(open_mesh):
    assert validate_lineage_coverage(open_mesh, open_mesh, None) == ["Expected a LineageMap."]
    lineage = LineageMap()
    object.__setattr__(lineage, "vertex_parents", {0: []})
    assert "non-empty" in validate_lineage_coverage(open_mesh, open_mesh, lineage)[0]
