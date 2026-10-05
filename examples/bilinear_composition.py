"""Fixed Cases A-D diagnostics; no production Repeat or surface evaluator.

Run from CHESHIRE with its .venv Python. OBJ files are diagnostic displays;
their triangulation by a viewer need not match the chosen bilinear patches.
"""

import argparse
from copy import deepcopy
import inspect
import json
from math import dist, fsum, hypot, isfinite
from pathlib import Path
import traceback

from compas.datastructures import Mesh
from compas.geometry import Box, cross_vectors, distance_point_plane

from cheshire import (
    ExecutionBudget, FieldSpec, analyze_vertex_attributes, build_scalar_field,
    displace_vertices_along_normals, estimate_quad_subdivision, identity_lineage,
    inherit_fields, save_mesh, subdivide_quad_once, validate_lineage_coverage,
)
from cheshire.subdivision import GEOMETRY_TOLERANCE


SPECS = [FieldSpec("confidence", "vertex", "scalar", "CONTINUOUS"),
         FieldSpec("part_type", "face", "categorical", "CATEGORICAL"),
         FieldSpec("height", "vertex", "scalar", "RECOMPUTE")]


def snapshot(mesh):
    return json.dumps(mesh.__data__, sort_keys=True, allow_nan=False)


def counts(mesh):
    return [mesh.number_of_vertices(), mesh.number_of_faces()]


def nonplanar_count(mesh):
    """Plane-distance diagnostic only; does not alter or accept geometry."""
    count = 0
    for face in mesh.faces():
        points = mesh.face_coordinates(face)
        offsets = [[x - y for x, y in zip(point, points[0])] for point in points]
        scale = max(hypot(*offset) for offset in offsets)
        local = [[value / scale for value in offset] for offset in offsets]
        normal = cross_vectors(local[-1], local[1])
        count += any(distance_point_plane(point, (local[0], normal)) > GEOMETRY_TOLERANCE for point in local)
    return count


def evaluate_patch(corners, u, v):
    """Independent diagnostic interpolation, outside production geometry."""
    weights = [(1 - u) * (1 - v), u * (1 - v), u * v, (1 - u) * v]
    return [sum(weight * point[axis] for weight, point in zip(weights, corners)) for axis in range(len(corners[0]))]


def patch_comparison_error(source, result):
    maximum = 0.0
    for child in result.mesh.faces():
        parent = result.lineage.face_parents[child][0].key
        keys = source.face_vertices(parent)
        if len(keys) != 4:
            continue
        uv = dict(zip(keys, [(0, 0), (1, 0), (1, 1), (0, 1)]))
        child_uv = [[sum(ref.weight * uv[ref.key][axis] for ref in result.lineage.vertex_parents[key]) for axis in range(2)]
                    for key in result.mesh.face_vertices(child)]
        for u, v in ((0, 0), (1, 0), (1, 1), (0, 1), (0.5, 0.5), (0.13, 0.79), (0.82, 0.21), (0.3, 0.6)):
            parent_u, parent_v = evaluate_patch(child_uv, u, v)
            expected = evaluate_patch(source.face_coordinates(parent), parent_u, parent_v)
            actual = evaluate_patch(result.mesh.face_coordinates(child), u, v)
            maximum = max(maximum, dist(actual, expected))
    return maximum


def original_fields(mesh):
    return {"confidence": {key: 0.2 if key == 0 else 0.8 if key == 1 else 0.5 for key in mesh.vertices()},
            "part_type": {key: "support" if key % 2 == 0 else "lintel" for key in mesh.faces()}}


def subdivide_stage(mesh, fields, generation, policy, records):
    before, fields_before = snapshot(mesh), deepcopy(fields)
    estimate = estimate_quad_subdivision(mesh, nonplanar_policy=policy)
    result = subdivide_quad_once(mesh, budget=ExecutionBudget(20000, max_vertices=20000, max_generation=4),
                                 current_generation=generation, nonplanar_policy=policy)
    coverage = validate_lineage_coverage(mesh, result.mesh, result.lineage)
    inherited = inherit_fields(result.lineage, fields, SPECS)
    current = build_scalar_field(analyze_vertex_attributes(result.mesh), "normalized_height", mapping="linear")
    error = patch_comparison_error(mesh, result)
    correct = all(abs(inherited.values["confidence"][child] -
                      fsum(ref.weight * fields["confidence"][ref.key] for ref in refs) / fsum(ref.weight for ref in refs)) < 1e-12
                  for child, refs in result.lineage.vertex_parents.items())
    correct = correct and all(inherited.values["part_type"][child] == fields["part_type"][refs[0].key]
                              for child, refs in result.lineage.face_parents.items())
    record = {"stage": "subdivision", "policy": result.nonplanar_policy, "generation": generation,
              "input_counts": counts(mesh), "predicted_counts": [estimate["estimated_output_vertices"], estimate["estimated_output_faces"]],
              "output_counts": counts(result.mesh), "input_unchanged": snapshot(mesh) == before,
              "source_fields_unchanged": fields == fields_before, "lineage_coverage": coverage,
              "inherited_fields_correct": correct, "recompute_fields": inherited.recompute_fields,
              "fresh_measurement_count": len(current["values"]), "nonplanar_faces": nonplanar_count(result.mesh),
              "finite_output": all(isfinite(value) for key in result.mesh.vertices() for value in result.mesh.vertex_coordinates(key)),
              "maximum_patch_comparison_error": error}
    records.append(record)
    assert not coverage and correct and record["input_unchanged"] and record["source_fields_unchanged"] and record["finite_output"]
    assert record["output_counts"] == record["predicted_counts"] and error < 1e-12
    return result.mesh, inherited.values


def displace_stage(mesh, fields, strength, records):
    before, fields_before = snapshot(mesh), deepcopy(fields)
    mapped = build_scalar_field(analyze_vertex_attributes(mesh), "normalized_height", mapping="linear")
    mapped_before = deepcopy(mapped)
    result = displace_vertices_along_normals(mesh, mapped["values"], strength=strength)
    lineage = identity_lineage(result.mesh)
    coverage = validate_lineage_coverage(mesh, result.mesh, lineage)
    inherited = inherit_fields(lineage, fields, SPECS)
    fresh = build_scalar_field(analyze_vertex_attributes(result.mesh), "normalized_height", mapping="linear")
    record = {"stage": "displacement", "strength": strength, "input_counts": counts(mesh),
              "output_counts": counts(result.mesh), "moved_vertices": result.moved_count,
              "nonplanar_faces": nonplanar_count(result.mesh), "input_unchanged": snapshot(mesh) == before,
              "source_fields_unchanged": fields == fields_before and mapped == mapped_before,
              "lineage_coverage": coverage, "inherited_fields_correct": inherited.values == fields,
              "recompute_fields": inherited.recompute_fields, "fresh_measurement_count": len(fresh["values"]),
              "finite_output": all(isfinite(value) for key in result.mesh.vertices() for value in result.mesh.vertex_coordinates(key))}
    records.append(record)
    assert record["input_unchanged"] and record["source_fields_unchanged"] and record["inherited_fields_correct"] and record["finite_output"]
    assert result.moved_count > 0 if strength else result.moved_count == 0
    assert not coverage and not result.topology_changed and counts(result.mesh) == counts(mesh)
    return result.mesh, inherited.values


def strict_rejection(mesh):
    before = snapshot(mesh)
    try:
        subdivide_quad_once(mesh, budget=ExecutionBudget(20000, max_vertices=20000, max_generation=4), current_generation=1)
    except ValueError as error:
        assert str(error).startswith("Nonplanar face ") and snapshot(mesh) == before
        return {"policy": "reject", "status": "EXPECTED_RESTRICTION", "exception_type": type(error).__name__,
                "exception_message": str(error), "input_unchanged": True, "nonplanar_faces": nonplanar_count(mesh)}
    raise AssertionError("Strict policy unexpectedly accepted the displaced nonplanar control")


def fixed_case(name, strength, third_step=False, output_directory=None):
    records = []
    mesh = Mesh.from_shape(Box(2, 2, 2))  # Unchanged fixture from Task 07 review.
    before = snapshot(mesh)
    fields = original_fields(mesh)
    try:
        first, fields = subdivide_stage(mesh, fields, 0, "reject", records)
        second_input = first
        rejection = None
        if strength is not None:
            second_input, fields = displace_stage(first, fields, strength, records)
            if strength:
                rejection = strict_rejection(second_input)
        second, fields = subdivide_stage(second_input, fields, 1, "bilinear" if strength else "reject", records)
        final = second
        if third_step:
            moved_again, fields = displace_stage(second, fields, 0.01, records)
            final, fields = subdivide_stage(moved_again, fields, 2, "bilinear", records)
        if output_directory is not None:
            for filename, item in (("initial.obj", mesh), ("first_subdivided.obj", first),
                                   ("displaced_nonplanar.obj", second_input), ("resubdivided_bilinear.obj", second),
                                   ("final_composition.obj", final)):
                save_mesh(item, output_directory / filename)
        assert snapshot(mesh) == before
        return {"case": name, "status": "SUCCESS", "final_counts": counts(final), "strict_rejection": rejection,
                "original_unchanged": True, "stages": records}
    except Exception as error:
        traceback.print_exc()
        return {"case": name, "status": "FAILURE", "exception_type": type(error).__name__,
                "exception_message": str(error), "original_unchanged": snapshot(mesh) == before, "stages": records}


def run_probe(output_directory=None):
    cases = [fixed_case("A", None), fixed_case("B", 0.01), fixed_case("C", 0.0),
             fixed_case("D", 0.01, third_step=True, output_directory=output_directory)]
    controls = []
    for name, points in (
        ("mild warp", [[0, 0, 0], [2, 0, 0], [2, 2, 0.2], [0, 2, 0]]),
        ("saddle", [[-1, -1, 0.4], [1, -1, -0.4], [1, 1, 0.4], [-1, 1, -0.4]]),
    ):
        source = Mesh.from_vertices_and_faces(points, [[0, 1, 2, 3]])
        records = []
        subdivide_stage(source, original_fields(source), 0, "bilinear", records)
        controls.append({"surface": name, "stages": records})
    return {"fixture": "closed Box(2,2,2)", "cases": cases, "surface_controls": controls,
            "maximum_patch_comparison_error": max(record["maximum_patch_comparison_error"]
                for item in cases + controls for record in item["stages"] if record["stage"] == "subdivision"),
            "scope": "Conservative local admissibility only; no global collision, fabrication, or volume guarantee. "
                     "Measurements remain COMPAS approximations, not exact bilinear-surface integrals. "
                     "Four fixed sequences in this example are not a production Repeat controller."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", type=Path, default=Path.cwd() / "output" / "task07_1")
    parser.add_argument("--json-path", type=Path)
    args = parser.parse_args()
    print("Actual public signatures:")
    for function in (estimate_quad_subdivision, subdivide_quad_once, displace_vertices_along_normals, inherit_fields):
        print(function.__name__ + str(inspect.signature(function)))
    result = run_probe(args.output_directory)
    print(json.dumps(result, indent=2))
    if args.json_path:
        with args.json_path.open("x", encoding="utf-8", newline="\n") as output:
            json.dump(result, output, indent=2)
            output.write("\n")
    return 0 if all(case["status"] == "SUCCESS" for case in result["cases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
