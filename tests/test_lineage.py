from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from cheshire import LineageMap, ParentRef, identity_lineage, validate_lineage
from cheshire.lineage import WEIGHT_SUM_TOLERANCE


def test_identity_lineage_preserves_mesh_keys_and_data(box_mesh):
    before = box_mesh.__data__
    lineage = identity_lineage(box_mesh)
    assert list(lineage.vertex_parents) == list(box_mesh.vertices())
    assert list(lineage.face_parents) == list(box_mesh.faces())
    for mapping in (lineage.vertex_parents, lineage.face_parents):
        assert all(refs == (ParentRef(key, 1.0),) for key, refs in mapping.items())
    assert validate_lineage(lineage) == []
    assert box_mesh.__data__ == before


def test_identity_lineage_needs_only_key_iterators():
    unique_key = object()

    class KeyOnlyMesh:
        def vertices(self):
            return iter(["A", ("v", 900), unique_key, -4])

        def faces(self):
            return iter([("face", 27), "roof"])

    lineage = identity_lineage(KeyOnlyMesh())
    assert list(lineage.vertex_parents) == ["A", ("v", 900), unique_key, -4]
    assert lineage.vertex_parents[unique_key][0].key is unique_key
    assert list(lineage.face_parents) == [("face", 27), "roof"]


def test_lineage_copies_parent_sequences_and_mappings_without_sorting():
    refs = [ParentRef("B", 0.75), ParentRef("A", 0.25)]
    source = {("child", 5): refs, "unknown": None, 100: [ParentRef(800, 1)]}
    lineage = LineageMap(vertex_parents=source)
    refs.clear()
    source.clear()
    assert list(lineage.vertex_parents) == [("child", 5), "unknown", 100]
    assert lineage.vertex_parents[("child", 5)] == (ParentRef("B", 0.75), ParentRef("A", 0.25))
    assert validate_lineage(lineage) == []
    with pytest.raises(TypeError):
        lineage.vertex_parents["new"] = None
    with pytest.raises(FrozenInstanceError):
        lineage.face_parents = {}
    with pytest.raises(FrozenInstanceError):
        lineage.vertex_parents[100][0].weight = 0


@pytest.mark.parametrize("weight", [-1, -0.001, nan, inf, -inf, "1", None, complex(1, 0)])
def test_invalid_parent_weights(weight):
    with pytest.raises(ValueError, match="weight"):
        ParentRef("parent", weight)


def test_unhashable_parent_key_rejected():
    with pytest.raises(ValueError, match="hashable"):
        ParentRef([1, 2], 1)


@pytest.mark.parametrize("domain", ["vertex_parents", "face_parents"])
@pytest.mark.parametrize("weights", [(0.3, 0.3), (0, 0), (1, 1), (1e308, 1e308)])
def test_weight_sum_must_be_one(domain, weights):
    with pytest.raises(ValueError, match="sum to 1"):
        LineageMap(**{domain: {"child": [ParentRef("A", weights[0]), ParentRef("B", weights[1])]}})


@pytest.mark.parametrize("delta", [-5e-10, 0, 5e-10])
def test_documented_absolute_tolerance_does_not_normalize_weights(delta):
    weight = 1 + delta
    lineage = LineageMap(vertex_parents={"child": [ParentRef("parent", weight)]})
    assert WEIGHT_SUM_TOLERANCE == 1e-9
    assert lineage.vertex_parents["child"][0].weight == weight
    assert validate_lineage(lineage) == []


@pytest.mark.parametrize("delta", [-2e-9, 2e-9])
def test_outside_tolerance_rejected(delta):
    with pytest.raises(ValueError, match="sum to 1"):
        LineageMap(face_parents={"child": [ParentRef("parent", 1 + delta)]})


@pytest.mark.parametrize("domain", ["vertex_parents", "face_parents"])
def test_duplicate_references_rejected(domain):
    with pytest.raises(ValueError, match="duplicate parent"):
        LineageMap(**{domain: {"child": [ParentRef("A", 0.5), ParentRef("A", 0.5)]}})


@pytest.mark.parametrize("parents", [[], (), "A", {ParentRef("A", 1)}, [("A", 1)], [1]])
def test_empty_unordered_or_non_reference_parents_rejected(parents):
    with pytest.raises(ValueError):
        LineageMap(vertex_parents={"child": parents})


def test_unknown_and_empty_domains_are_explicitly_valid():
    assert validate_lineage(LineageMap()) == []
    lineage = LineageMap(vertex_parents={"unknown": None}, face_parents={400: None})
    assert lineage.vertex_parents["unknown"] is None
    assert lineage.face_parents[400] is None
    assert validate_lineage(lineage) == []


@pytest.mark.parametrize("domain", ["vertex_parents", "face_parents"])
@pytest.mark.parametrize("mapping", [None, [], "mesh"])
def test_invalid_mapping(domain, mapping):
    with pytest.raises(ValueError, match="mapping"):
        LineageMap(**{domain: mapping})


def test_validation_reports_bypassed_invalid_record():
    lineage = LineageMap()
    bad_ref = ParentRef("A", 1)
    object.__setattr__(bad_ref, "weight", nan)
    object.__setattr__(lineage, "vertex_parents", {"bad": [bad_ref], "empty": []})
    problems = validate_lineage(lineage)
    assert len(problems) == 2
    assert "finite" in problems[0]
    assert "non-empty" in problems[1]
    assert validate_lineage(None) == ["Expected a LineageMap."]
