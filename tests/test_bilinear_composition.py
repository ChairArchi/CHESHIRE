from copy import deepcopy
import json
from math import fsum, isfinite

import pytest
from compas.datastructures import Mesh
from compas.geometry import Box

from cheshire import (
    ExecutionBudget, FieldSpec, analyze_vertex_attributes, build_scalar_field,
    displace_vertices_along_normals, estimate_quad_subdivision, identity_lineage,
    inherit_fields, subdivide_quad_once, validate_lineage_coverage,
)


SPECS = [FieldSpec("confidence", "vertex", "scalar", "CONTINUOUS"),
         FieldSpec("part_type", "face", "categorical", "CATEGORICAL"),
         FieldSpec("height", "vertex", "scalar", "RECOMPUTE")]


def _snapshot(mesh):
    return json.dumps(mesh.__data__, sort_keys=True, allow_nan=False)


def _initial():
    mesh = Mesh.from_shape(Box(2, 2, 2))  # Exact fixture from the external Task 07 diagnostic.
    values = {"confidence": {key: (key + 1) / 8 for key in mesh.vertices()},
              "part_type": {key: "support" if key % 2 == 0 else "lintel" for key in mesh.faces()}}
    return mesh, values


def _subdivide(source, source_fields, generation, policy="reject"):
    before, fields_before = _snapshot(source), deepcopy(source_fields)
    estimate = estimate_quad_subdivision(source, nonplanar_policy=policy)
    result = subdivide_quad_once(source, budget=ExecutionBudget(20000, max_vertices=20000, max_generation=4),
                                 current_generation=generation, nonplanar_policy=policy)
    assert result.output_vertices == estimate["estimated_output_vertices"]
    assert result.output_faces == estimate["estimated_output_faces"]
    assert validate_lineage_coverage(source, result.mesh, result.lineage) == []
    lineage_before = (dict(result.lineage.vertex_parents), dict(result.lineage.face_parents))
    inherited = inherit_fields(result.lineage, source_fields, SPECS)
    assert inherited.recompute_fields == ["height"] and "height" not in inherited.values
    for child, refs in result.lineage.vertex_parents.items():
        expected = fsum(ref.weight * source_fields["confidence"][ref.key] for ref in refs) / fsum(ref.weight for ref in refs)
        assert inherited.values["confidence"][child] == pytest.approx(expected)
    for child, refs in result.lineage.face_parents.items():
        assert inherited.values["part_type"][child] == source_fields["part_type"][refs[0].key]
    current_measurements = analyze_vertex_attributes(result.mesh)
    current_height = build_scalar_field(current_measurements, "normalized_height")
    assert set(current_height["values"]) == set(result.mesh.vertices())
    assert all(isfinite(value) for key in result.mesh.vertices() for value in result.mesh.vertex_coordinates(key))
    assert source_fields == fields_before and _snapshot(source) == before
    assert (dict(result.lineage.vertex_parents), dict(result.lineage.face_parents)) == lineage_before
    return result.mesh, inherited.values


def _displace(source, source_fields, strength):
    before, fields_before = _snapshot(source), deepcopy(source_fields)
    measurements = analyze_vertex_attributes(source)  # Fresh after every geometry change.
    height = build_scalar_field(measurements, "normalized_height", mapping="linear")
    height_before = deepcopy(height)
    result = displace_vertices_along_normals(source, height["values"], strength=strength)
    assert result.moved_count > 0 if strength else result.moved_count == 0
    assert not result.topology_changed
    assert result.mesh.number_of_vertices() == source.number_of_vertices()
    assert result.mesh.number_of_faces() == source.number_of_faces()
    lineage = identity_lineage(result.mesh)
    assert validate_lineage_coverage(source, result.mesh, lineage) == []
    inherited = inherit_fields(lineage, source_fields, SPECS)
    assert inherited.values == source_fields and inherited.recompute_fields == ["height"]
    fresh = analyze_vertex_attributes(result.mesh)
    assert set(fresh) == set(result.mesh.vertices())
    assert all(isfinite(value) for key in result.mesh.vertices() for value in result.mesh.vertex_coordinates(key))
    assert _snapshot(source) == before and source_fields == fields_before and height == height_before
    return result.mesh, inherited.values, result.moved_count


def test_case_a_two_strict_subdivision_steps():
    mesh, fields = _initial()
    first, fields = _subdivide(mesh, fields, 0)
    second, fields = _subdivide(first, fields, 1)
    assert (second.number_of_vertices(), second.number_of_faces()) == (98, 96)


def test_case_b_strict_rejection_and_explicit_bilinear_success():
    mesh, fields = _initial()
    first, fields = _subdivide(mesh, fields, 0)
    moved, fields, count = _displace(first, fields, 0.01)
    assert count == 17
    before = _snapshot(moved)
    with pytest.raises(ValueError, match="Nonplanar face 10; relative tolerance is 1e-09"):
        _subdivide(moved, fields, 1)
    assert _snapshot(moved) == before
    second, fields = _subdivide(moved, fields, 1, "bilinear")
    assert (second.number_of_vertices(), second.number_of_faces()) == (98, 96)


def test_case_c_zero_strength_control_remains_strictly_supported():
    mesh, fields = _initial()
    first, fields = _subdivide(mesh, fields, 0)
    moved, fields, count = _displace(first, fields, 0)
    assert count == 0 and _snapshot(moved) == _snapshot(first)
    second, fields = _subdivide(moved, fields, 1)
    assert (second.number_of_vertices(), second.number_of_faces()) == (98, 96)


def test_case_d_two_nonzero_displacements_and_three_subdivision_steps():
    mesh, fields = _initial()
    original = _snapshot(mesh)
    first, fields = _subdivide(mesh, fields, 0)
    moved, fields, count = _displace(first, fields, 0.01)
    assert count == 17
    second, fields = _subdivide(moved, fields, 1, "bilinear")
    moved_again, fields, second_count = _displace(second, fields, 0.01)
    assert second_count == 73
    final, fields = _subdivide(moved_again, fields, 2, "bilinear")
    assert (final.number_of_vertices(), final.number_of_faces()) == (386, 384)
    assert _snapshot(mesh) == original
