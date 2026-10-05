# CHESHIRE

**Computational Hybrid Exploration for Surface Handling, Iteration & Rule-based Engine**

CHESHIRE is a standalone deterministic computational design engine for transforming arbitrary polygon meshes through explicit, traceable rules. Its long-term aim is to measure geometric and topological attributes, map them into scalar fields, select and apply transformation rules, inherit provenance and tags, and iterate. It is independent from ALICE and has no dependency on it.

**Status:** early experimental research software.

Pipeline:

**Mesh → Measure → Map → Rule → Budget → Transform → Inherit → Repeat**

```text
Mesh        [implemented]
Measure     [implemented]
Map         [implemented]
Rule        [implemented]
Budget      [implemented]
Transform   [partially implemented — normal displacement]
Inherit     [implemented — lineage + field inheritance foundation]
Repeat      [not implemented]
```

Tasks 01–06 implement mesh infrastructure, measurement, scalar mapping, rule selection, budgeting, normal displacement, and the lineage/field inheritance foundation. Input meshes remain unchanged. CHESHIRE now separates geometry execution from semantic continuity.

## Setup and tests

Use Python 3.12 on Windows. In VS Code, select `.venv\Scripts\python.exe` as the Python interpreter.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
```

Direct dependencies are pinned in `pyproject.toml`: COMPAS 2.15.1 and pytest 9.1.1 (test extra). Their required transitive dependencies are installed automatically.

## Usage

```python
from cheshire import load_mesh, inspect_mesh, validate_mesh, save_mesh

mesh = load_mesh("input.obj")
print(inspect_mesh(mesh))
print(validate_mesh(mesh))  # List of problems; [] means basic checks passed.
save_mesh(mesh, "output/mesh.obj")
```

Only OBJ is supported. I/O rejects zero vertices, zero faces, and non-finite XYZ coordinates with `ValueError`; inspection and validation never modify the mesh. `bounding_box` contains axis-aligned dimensions `[x, y, z]`, or `None` for empty/non-finite geometry. Topology flags use COMPAS methods and return `None` when unavailable.

Loading uses COMPAS's raw `OBJReader` because `Mesh.from_obj()` welds vertices. Original vertex indices, unused vertices, and polygon faces are retained; malformed faces that COMPAS would change are rejected. Positive and relative negative face indices are supported. Saving uses `Mesh.to_obj(unweld=False)` with at least 17 decimal places, increasing precision for small coordinates (up to 324) to preserve Python floats. Very small coordinates produce larger text files. No welding, triangulation, or repair occurs.

This interface preserves vertex positions and polygon connectivity only. OBJ materials, textures, normals, grouping, standalone points/lines, and custom mesh attributes are not preserved. Basic validation does not certify manifoldness, degeneracy, or absence of self-intersections; topology flags describe COMPAS's mesh representation.

## Measurements and scalar fields

```python
from cheshire import analyze_vertex_attributes, attribute_summary, build_scalar_field

attributes = analyze_vertex_attributes(mesh)
print(attribute_summary(attributes))
field = build_scalar_field(
    attributes, "approximate_curvature", mapping="power", exponent=2.0,
    lower_percentile=5.0, upper_percentile=95.0,
)
```

Measurements include valence, boundary status, normalized Z height, centroid distance (raw and normalized), approximate curvature, and boundary distance. Distances use COMPAS's surface-area-weighted centroid; undefined centroids or unrepresentable distances return `None`. Boundary distance counts shortest edge hops from any boundary vertex; components without a boundary return `None`.

Curvature is a simple normal-variation proxy: the mean pairwise angle between incident unit face normals, divided by pi. Consistently oriented coplanar faces give zero. Boundary vertices, incomplete face fans, and degenerate/unavailable normals return `None`. It depends on winding and tessellation and is not differential curvature.

`normalize_values()` accepts sequences or keyed mappings, preserves `None`, and clips using linearly interpolated percentiles (`0 <= lower < upper <= 100`). Constants normalize to zero; non-finite inputs are rejected. `map_attribute()` applies `linear`, `inverse`, `smoothstep`, `power` (finite exponent > 0, default 2), or monotonic half-`sine` to normalized values. Fields stay in `[0, 1]` or `None`. `build_scalar_field()` adds source/mapping metadata and effective parameters. Numeric summaries report min/max/mean, ignore nulls, and exclude booleans. All functions leave input mesh data unchanged.

## Rule selection and dry-run budgets

```python
from cheshire import Rule, ExecutionBudget, plan_execution

fields = {"height": build_scalar_field(attributes, "normalized_height")}
rule = Rule(
    "upper faces", "height", "face", "greater_than", 0.65,
    operator="hypothetical_refine", face_reduction="mean",
)
plan = plan_execution(
    mesh, fields, rule, ExecutionBudget(max_faces=50_000, max_generation=4),
    current_generation=2,
    cost_profile={"topology_preserving": False, "replacement_faces_per_selected_face": 4},
)
print(plan["status"], plan["estimated_output_faces"], plan["reasons"])
```

Field names are arbitrary labels. Rules target vertices or faces and support `greater_than`, `greater_equal`, `less_than`, `less_equal`, and inclusive `between`. Thresholds and field scalars must be finite. `evaluate_vertex_rule()` and `evaluate_face_rule()` return selected keys/counts, eligible counts, fractions, threshold rejections, and null exclusions. Fractions use non-null eligible elements as the denominator. Face reductions (`mean`, `min`, `max`) ignore unavailable vertex values; completely null faces are ineligible. Missing vertex keys stay unavailable, and keys absent from the mesh are rejected.

`plan_execution()` accepts named raw value mappings or field metadata. Operator names/parameters are descriptive only. A `topology_preserving=True` cost profile estimates unchanged counts; otherwise the positive integer replacement rate must be supplied explicitly. The face estimate is `input_faces - selected_faces + selected_faces * replacement_rate`. Refinement vertex counts remain unknown; face growth cannot be inferred from vertex selections. No profile means unknown output counts.

Budgets check face, optional vertex, and optional generation limits separately. Counts equal to a limit are allowed; `current_generation >= max_generation` is blocked. Plans report `SAFE` when supplied estimates fit, `WARNING` when a configured count budget cannot be verified, or `BLOCKED` when any limit is exceeded. Estimates describe the supplied assumptions, not guaranteed operator costs. Planning never moves vertices, changes faces, or executes transformations.

## First transform: normal displacement

```python
from cheshire import displace_vertices_along_normals

rule = Rule("high vertices", "height", "vertex", "greater_than", 0.65,
            operator="normal_displacement")
plan = plan_execution(
    mesh, fields, rule,
    ExecutionBudget(max_faces=50_000, max_vertices=50_000, max_generation=4),
    current_generation=0, cost_profile={"topology_preserving": True},
)
if plan["status"] == "SAFE":
    result = displace_vertices_along_normals(
        mesh, fields["height"]["values"], selected_vertices=plan["selected_vertices"],
        strength=0.02, direction="outward",
    )
    save_mesh(result.mesh, "output/displaced.obj")
```

Distance is `field_value * strength * input_bbox_diagonal`; strength is a dimensionless fraction, not an absolute distance. For example, `0.8 * 0.02 * 5000 = 80` model units. Only `scale_mode="bbox_diagonal"` is supported. Strength must be finite and non-negative, and all supplied field values must be finite in `[0, 1]` or `None`.

COMPAS vertex normals average incident polygon normals with area weighting, then unitize the result. They are evaluated on the original geometry. `outward` follows these normals, and `inward` follows their negatives; winding determines orientation. Missing/null fields, zero distances, and unsafe normals leave vertices fixed. Incomplete face fans and degenerate, cancelling, non-finite, or unavailable normals are reported as skips. Invalid mesh topology or unrepresentable scales/output coordinates are rejected, without repair.

`TransformResult.mesh` is an independent COMPAS Mesh with the same vertex/face keys and connectivity. Metadata records operator, direction, selected/moved/skipped counts, strength, scale, actual maximum displacement, skip reasons, and `topology_changed=False`. Selection defaults to all mesh vertices; explicit selections restrict candidates. Zero/null candidates count as skipped. Rules and budget checks remain separate from the transform. No subdivision or repetition is implemented.

## Lineage and field inheritance

```python
from cheshire import FieldSpec, LineageMap, ParentRef, identity_lineage, inherit_fields

# Synthetic lineage only; this does not create or split geometry.
lineage = LineageMap(vertex_parents={
    "C": [ParentRef("A", 0.25), ParentRef("B", 0.75)],
})
inherited = inherit_fields(
    lineage,
    {"confidence": {"A": 0.2, "B": 0.8},
     "part_type": {"A": "support", "B": "support"}},
    [FieldSpec("confidence", "vertex", "scalar", "CONTINUOUS"),
     FieldSpec("part_type", "vertex", "categorical", "CATEGORICAL"),
     FieldSpec("approximate_curvature", "vertex", "scalar", "RECOMPUTE")],
)
# confidence[C] is approximately 0.65; part_type[C] is "support".
# inherited.recompute_fields == ["approximate_curvature"]

# After the SAFE normal-displacement example above:
# lineage = identity_lineage(result.mesh)
# inherited = inherit_fields(lineage, fields, specs)
```

`LineageMap(vertex_parents, face_parents)` maps arbitrary hashable child keys to ordered `ParentRef(key, weight)` sequences. Children retain mapping insertion order; parents retain sequence order, without sorting keys. Maps and parent records are read-only snapshots. `validate_lineage()` returns a list of problems (`[]` when valid); construction rejects invalid lineage. Weights must be finite, non-negative, and sum to one within absolute tolerance `1e-9` (zero relative tolerance). Weights are never renormalized. Duplicate parents and empty parent sequences are rejected; `None` explicitly represents unknown parents. Keys must keep stable hash/equality behavior.

`FieldSpec(name, domain, kind, inheritance_mode)` uses arbitrary names, domains `vertex`/`face`, and kinds `scalar`/`categorical`. `CONTINUOUS` requires scalar kind and computes finite weighted values without a `[0, 1]` restriction. `CATEGORICAL` requires categorical kind and inherits hashable labels (strings, enums, or other semantic labels) only when every parent agrees; conflicting labels return `None`. Labels are treated as immutable atomic values and retained directly, so callers must keep their hash/equality and content stable. Numeric labels must be finite. `RECOMPUTE` omits the field from output values and flags its name without reading stale source data or measuring geometry. Geometry-derived fields such as height, valence, boundary status, and curvature should normally use `RECOMPUTE`; the engine makes no choices based on field names.

`inherit_fields(lineage, fields, specs)` accepts named raw mappings or scalar-field metadata with a `values` mapping. All declared parents are required, including zero-weight parents. Missing fields/keys, null parent values, unknown lineage, and label conflicts return `None`; incomplete data is never renormalized. All supplied values for inherited fields are validated, including unused entries. `InheritedFieldSet` returns fresh `values`, ordered `recompute_fields`, per-inherited-field `unresolved_counts`, and `warnings`. Ordinary floating-point rounding applies; non-finite inputs/results are rejected. Lineage, source fields, and meshes remain unchanged. Inheritance needs no mesh access.

## Future backend contract

Any future topology-changing backend (COMPAS, Mola, or another implementation) must return both the resulting mesh and lineage sufficient for CHESHIRE inheritance, identifying child vertex/face keys and their weighted parent keys in the input mesh. A topology-preserving transform can use `identity_lineage(output_mesh)` when keys remain unchanged. CHESHIRE uses lineage to inherit semantic and continuous fields while marking geometry-derived measurements for recomputation. No backend framework, external backend integration, topology-changing operator, or Repeat loop is implemented yet.
