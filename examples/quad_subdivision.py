r"""Run from CHESHIRE: .\.venv\Scripts\python.exe examples\quad_subdivision.py"""

from pathlib import Path

from compas.datastructures import Mesh
from compas.geometry import Box

from cheshire import (
    ExecutionBudget, FieldSpec, analyze_vertex_attributes, check_execution_budget,
    estimate_quad_subdivision, inherit_fields, save_mesh, subdivide_quad_once,
    validate_lineage_coverage,
)


def main():
    mesh = Mesh.from_shape(Box(2, 3, 4))
    measurements = analyze_vertex_attributes(mesh)
    fields = {
        "confidence": {key: 0.2 if key == 0 else 0.8 if key == 1 else 0.5 for key in mesh.vertices()},
        "part_type": {key: "support" if key == 0 else "lintel" for key in mesh.faces()},
        "conflict": {key: 0.8 if key == 0 else 0.2 for key in mesh.faces()},
        "valence": {key: record["valence"] for key, record in measurements.items()},
        "approximate_curvature": {key: record["approximate_curvature"] for key, record in measurements.items()},
    }
    estimate = estimate_quad_subdivision(mesh)
    budget = ExecutionBudget(max_faces=24, max_vertices=26, max_generation=1)
    assessment = check_execution_budget(
        budget, input_faces=estimate["input_faces"], input_vertices=estimate["input_vertices"],
        estimated_output_faces=estimate["estimated_output_faces"],
        estimated_output_vertices=estimate["estimated_output_vertices"], current_generation=0,
    )
    print("Estimate:", estimate)
    print("Budget:", assessment)
    result = subdivide_quad_once(mesh, budget=budget, current_generation=0)
    problems = validate_lineage_coverage(mesh, result.mesh, result.lineage)
    if problems:
        raise ValueError("Lineage coverage failed: " + " ".join(problems))
    print(f"Actual: {result.output_vertices} vertices / {result.output_faces} faces; lineage complete")
    specs = [
        FieldSpec("confidence", "vertex", "scalar", "CONTINUOUS"),
        FieldSpec("part_type", "face", "categorical", "CATEGORICAL"),
        FieldSpec("conflict", "face", "scalar", "CONTINUOUS"),
        FieldSpec("valence", "vertex", "scalar", "RECOMPUTE"),
        FieldSpec("approximate_curvature", "vertex", "scalar", "RECOMPUTE"),
    ]
    inherited = inherit_fields(result.lineage, fields, specs)
    midpoint = next(key for key, refs in result.lineage.vertex_parents.items()
                    if {ref.key for ref in refs} == {0, 1})
    child = next(key for key, refs in result.lineage.face_parents.items() if refs[0].key == 0)
    print(f"Edge 0--1 midpoint {midpoint}: confidence={inherited.values['confidence'][midpoint]}")
    print(f"Child face {child}: part_type={inherited.values['part_type'][child]!r}, "
          f"conflict={inherited.values['conflict'][child]}")
    print("Recompute fields:", inherited.recompute_fields)
    output_measurements = analyze_vertex_attributes(result.mesh)  # Explicit, separate measurement step.
    recomputed = {name: {key: record[name] for key, record in output_measurements.items()}
                  for name in inherited.recompute_fields}
    print("Fresh midpoint measurements:", {name: values[midpoint] for name, values in recomputed.items()})
    output_directory = Path(__file__).resolve().parents[1] / "output" / "task07"
    save_mesh(mesh, output_directory / "input.obj")
    save_mesh(result.mesh, output_directory / "subdivided.obj")
    print("Diagnostic OBJ files:", output_directory)


if __name__ == "__main__":
    main()
