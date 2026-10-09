# CHESHIRE

**Computational Hybrid Exploration for Surface Handling, Iteration & Rule-based Engine**

CHESHIRE is a standalone deterministic computational design engine for transforming arbitrary polygon meshes through explicit, traceable rules. Its long-term aim is to measure geometric and topological attributes, map them into scalar fields, select and apply transformation rules, inherit provenance and tags, and iterate. It is independent from ALICE and has no dependency on it.

**Status:** experimental research software. The latest frozen study is Task31
regional growth/depth/opening control, with a **PARTIAL** result. Existing algorithms,
legacy replay and research verdicts remain unchanged.

Task32 adds opt-in relational morphology experiments, native checkpoint recovery,
and geometry contact audits. Its [research results](docs/TASK32_RESULTS.md) are
**PARTIAL**: controlled parent–child geometry is demonstrated, while rich
Macro–Meso–Micro ornament remains unresolved. The full Task31 state is preserved.

Start with [current execution paths](docs/CURRENT_PATHS.md),
[the small ALICE gate exchange](docs/GATE_EXCHANGE_V1.md), and
[preservation/consolidation results](docs/CONSOLIDATION_20261009.md).
Task31 runs through its separate research tools/API, not a new Rhino launcher default.
The earlier Task17 **SubdivisionCapabilityStudy** remains supported; its
[results](docs/TASK17_RESULTS.md) and [reference choices](docs/TASK17_REFERENCE.md)
are historical records.

Compatibility API pipeline (Tasks 01–08; later reference studies are separate):

**Mesh → Measure → Map → Rule → Budget → Transform → Inherit → Repeat**

```text
Mesh        [implemented]
Measure     [implemented]
Map         [implemented]
Rule        [implemented]
Budget      [implemented]
Transform   [normal displacement + one-step global quad subdivision]
Inherit     [verified on a real topology-changing operation]
Repeat      [not implemented]
```

Tasks 01–07.1 implement mesh infrastructure, measurement, scalar mapping, rule selection, budgeting, normal displacement, and one global COMPAS quad-subdivision step with verified lineage and field inheritance. Task 07.1 adds explicit bilinear support for locally admissible nonplanar quads. Task 08 adds a thin Rhino entry point for four fixed experimental rule applications. Input meshes remain unchanged. CHESHIRE separates geometry execution from semantic continuity. A general Repeat engine remains unimplemented.

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

`TransformResult.mesh` is an independent COMPAS Mesh with the same vertex/face keys and connectivity. Metadata records operator, direction, selected/moved/skipped counts, strength, scale, actual maximum displacement, skip reasons, and `topology_changed=False`. Selection defaults to all mesh vertices; explicit selections restrict candidates. Zero/null candidates count as skipped. Rules and budget checks remain separate from the displacement transform.

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

`LineageMap(vertex_parents, face_parents)` maps arbitrary hashable child keys to ordered `ParentRef(key, weight)` sequences. Children retain mapping insertion order; parents retain sequence order, without sorting keys. Maps and parent records are read-only snapshots. `validate_lineage()` returns a list of problems (`[]` when valid); construction rejects invalid lineage. Weights must be finite, non-negative, and sum to one within absolute tolerance `1e-9` (zero relative tolerance). Stored weights are never changed. Duplicate parents and empty parent sequences are rejected; `None` explicitly represents unknown parents. Keys must keep stable hash/equality behavior.

`FieldSpec(name, domain, kind, inheritance_mode)` uses arbitrary names, domains `vertex`/`face`, and kinds `scalar`/`categorical`. `CONTINUOUS` requires scalar kind and computes finite weighted values without a `[0, 1]` restriction. `CATEGORICAL` requires categorical kind and inherits hashable labels (strings, enums, or other semantic labels) only when every parent agrees; conflicting labels return `None`. Labels are treated as immutable atomic values and retained directly, so callers must keep their hash/equality and content stable. Numeric labels must be finite. `RECOMPUTE` omits the field from output values and flags its name without reading stale source data or measuring geometry. Geometry-derived fields such as height, valence, boundary status, and curvature should normally use `RECOMPUTE`; the engine makes no choices based on field names.

`inherit_fields(lineage, fields, specs)` accepts named raw mappings or scalar-field metadata with a `values` mapping. Exactly zero-weight parents do not participate in resolution. Every positive-weight parent is required: missing fields/keys, null parent values, unknown lineage, and label conflicts return `None`; incomplete data is never renormalized. Complete continuous weights are normalized for evaluation only, leaving stored lineage unchanged; constant fields remain exactly constant. All supplied values for inherited fields are validated, including unused entries, so NaN/inf still raises an error even at zero weight. `InheritedFieldSet` returns fresh `values`, ordered `recompute_fields`, per-inherited-field `unresolved_counts`, and `warnings`. Ordinary floating-point rounding applies; non-finite inputs/results are rejected. Lineage, source fields, and meshes remain unchanged. Inheritance needs no mesh access.

## Future backend contract

Any future topology-changing backend (COMPAS, Mola, or another implementation) must return both the resulting mesh and lineage sufficient for CHESHIRE inheritance, identifying child vertex/face keys and their weighted parent keys in the input mesh. A topology-preserving transform can use `identity_lineage(output_mesh)` when keys remain unchanged. CHESHIRE uses lineage to inherit semantic and continuous fields while marking geometry-derived measurements for recomputation. The COMPAS quad adapter below implements one such operation; this original adapter does not supply a backend framework or general Repeat loop. Optional Mola and later study implementations are indexed in docs/CURRENT_PATHS.md.

## One-step global quad subdivision

```python
from cheshire import ExecutionBudget, estimate_quad_subdivision, subdivide_quad_once

estimate = estimate_quad_subdivision(mesh)  # Also checks operator-specific input restrictions.
result = subdivide_quad_once(
    mesh, budget=ExecutionBudget(max_faces=24, max_vertices=26, max_generation=1),
    current_generation=0,
)
# For an 8-vertex, 6-face cube: exactly 26 vertices and 24 quad faces.
# result.mesh is new; result.lineage covers every output vertex and face.
```

The adapter calls the installed **COMPAS 2.15.1** public API `Mesh.subdivided(scheme="quad", k=1)`. It executes exactly one global level, without smoothing or displacement. It has no face-selection parameter and does not perform local refinement. `estimate_quad_subdivision()` predicts `3*T + 4*Q` faces and `V + E + F` vertices, where `E` counts unique input edges. `check_execution_budget()` checks explicit counts with the same semantics as `plan_execution()`, whose API and behavior remain unchanged. A blocked budget prevents backend-copy allocation and execution. Actual counts and geometry are checked before returning `SubdivisionResult`, which records the estimates, actual counts, backend/version, `levels=1`, `topology_changed=True`, and `nonplanar_policy`.

By default, `nonplanar_policy="reject"` requires nondegenerate planar strictly convex triangles/quads, preserving the Task 07 contract. Both subdivision APIs accept the keyword-only alternative `nonplanar_policy="bilinear"`; unknown policies raise `ValueError`. The selected policy validates both input and output. Triangles retain their existing restrictions in either mode.

All modes require finite XYZ, valid connectivity, distinct corners, consistently oriented manifold vertex fans, and nonzero edges and corner areas. Open, closed, disconnected, and sparse/nonconsecutive COMPAS integer-key meshes are supported. Isolated vertices, unsupported face sizes, concave/self-crossing controls, and non-manifold topology are rejected only by this adapter; OBJ I/O restrictions are unchanged. Geometric tolerance remains `1e-9` relative to each face's largest distance from its first vertex: faces are translated and scaled before checking geometry. Nearly collinear corners are rejected. Extreme coordinates that cause unrepresentable backend arithmetic/results are rejected without returning output. Self-intersection/collision analysis between separate faces is outside this validation.

Installed source inspection and triangle/quad/adjacent-quad/cube probes verified original vertex keys/XYZ retention, one shared midpoint per original edge at `t=0.5`, arithmetic vertex-mean `face_centroid()` (not area-weighted `face_center()`), and child `path=[parent_face_key, corner_index]`. Recovery verifies each path against its retained corner, adjacent midpoint connectivity, and opposite face-center vertex. It requires one midpoint per input edge, one center per input face, every expected corner child, and complete unambiguous output coverage. Coordinates only verify topology-derived roles; they never identify ancestry. Original vertices inherit weight 1, edge endpoints 0.5 each, face vertices `1/n` each, and child faces weight 1 from their parent. Backend `path` describes this single call and is not a full provenance history; a second manual call references its own immediate input faces.

`validate_lineage_coverage(input_mesh, output_mesh, lineage)` reports missing/extra children, explicit unknown ancestry, invalid parent references, and normal lineage errors separately. Unknown ancestry is not accepted for this operator. Only XYZ and connectivity enter the backend; custom/default vertex, face, edge, and mesh attributes are discarded on the output, while returned child `path` metadata remains. Input attributes are untouched. Semantic fields use explicit `inherit_fields()` mappings. Mark old geometry-derived fields `RECOMPUTE`, then call `analyze_vertex_attributes(result.mesh)` explicitly to obtain fresh measurements.

Run the complete cube example from the repository root on Windows:

```powershell
.\.venv\Scripts\python.exe examples\quad_subdivision.py
```

It demonstrates estimate → SAFE budget → subdivision → coverage → continuous/categorical inheritance → explicit measurement recomputation. Confidence `0.2`/`0.8` at an original edge inherits `0.5` at its midpoint; child face labels remain tied to their distinct parents. Diagnostic OBJ files go to ignored `output/task07/`. No subdivision algorithm was reimplemented, and no dependency was added or upgraded. Local/adaptive subdivision, smoothing wrappers, Mola/Rhino integration, and Repeat remain outside the implemented scope.

## Explicit bilinear policy and composition

An ordered quad `p0, p1, p2, p3` denotes parameter corners `(0,0), (1,0), (1,1), (0,1)` under the bilinear policy:

```text
P(u,v) = (1-u)(1-v)p0 + u(1-v)p1 + uv p2 + (1-u)v p3
```

This uses the [bilinear patch definition described in PBRT](https://pbr-book.org/4ed/Shapes/Bilinear_Patches), with corners listed in boundary order. The installed COMPAS implementation retains the original corners, creates half-edge midpoints and the arithmetic corner mean, and connects four child quads. Independent parent/child evaluations verify that these represent the four half-parameter regions of the chosen patch. No vertices are projected or flattened, and no automatic triangulation occurs.

Acceptance uses a conservative local regularity test. In translated/scaled coordinates, write `P=a*u+b*v+c*u*v`, where `a=p1`, `b=p3`, and `c=p2-p1-p3`. Its area vector is `J=a×b + u(a×c) + v(c×b)`. A nonzero center Jacobian supplies a unit reference normal. Each corner's signed projection onto it must exceed `1e-9`; the affine projection has its minimum at a domain corner, so this bounds the interior away from singularities and orientation flips. Collapsed, folded, singular, near-degenerate, or otherwise unsupported controls are rejected. The criterion respects rigid rotation, cyclic corner order, consistent winding reversal, and uniform scaling away from numerical thresholds.

Run the four fixed composition cases:

```powershell
.\.venv\Scripts\python.exe examples\bilinear_composition.py
```

Using the original `Box(2,2,2)` and freshly mapped normalized height, Case A (two subdivisions) and Case C (zero displacement between them) finish at 98 vertices / 96 faces. Case B's strength `0.01` displacement moves 17 vertices and produces 20 nonplanar quads: strict mode still rejects face 10, while explicit bilinear subdivision succeeds at 98/96. Case D adds fresh measurement/mapping, a second strength `0.01` displacement moving 73 vertices, and another bilinear subdivision, reaching 386/384. Every stage checks immutable inputs, finite output, immediate-parent coverage, continuous/categorical inheritance, and fresh measurements. The example reports policies, strengths, counts, rejection reasons, nonplanarity, and maximum sampled parent/child patch comparison error. It exports five small OBJ files to ignored `output/task07_1/`.

This policy certifies only conservative local admissibility. It does not certify intersections between faces, global collision freedom, fabrication suitability, or enclosed volume. A viewer's triangulated OBJ display may differ from the chosen bilinear surface. Measurements and displacement normals still use the existing COMPAS methods, without exact bilinear-surface integration. These four explicit sequences are Task 07.1 diagnostic examples. This Task07.1 example is not a general Repeat engine. Optional Mola paths and the Task08 Rhino entry point are described below.

## Rhino mesh-grammar experiment (Task 08)

Run `rhino/CHESHIRE_Run.py` in **Rhino 8 ScriptEditor / Python 3**, select one existing Mesh, and choose strength (default `0.01`, allowed `0–0.03` of the bounding-box diagonal). Selection/display stay in Rhino; a small external JSON worker uses the existing repository `.venv`. Rhino imports stay outside the core, and no dependencies change. See [the English quickstart](rhino/QUICKSTART.md) for launch, colors, cancellation, partial results, limits and host checks.

Four fixed steps use existing APIs: bilinear quad subdivision → fresh normal-variation proxy measurement → power(2) mapping without percentile clipping → positive-value rule selection → outward displacement at `strength / 2**step_index` → validation and explicit inheritance. New run layers show ORIGINAL REFERENCE, the actual pre-displacement G1 driver in grayscale (magenta means unavailable), and G1/G2/G4 where reached. Display copies move only along world X; the original and calculation coordinates are preserved. Later budget/geometry failures retain completed results as PARTIAL. This is our Mesh-Grammars-inspired recipe; no modified Catmull-Clark, Digital Grotesque reproduction, or general Repeat engine is implemented.

The real-worker control can also run without Rhino:

```powershell
.\.venv\Scripts\python.exe examples\mesh_grammar_demo.py
```

It retains real control geometry, aligned driver values and step diagnostics in a unique ignored `output/task08/` directory. The user has since confirmed actual Task 08 selection/calculation/insertion in Rhino; broader viewport/color, Undo and cancellation checks remain **PENDING**. Results may be subtle; there is no ornament, collision-free or fabrication-ready claim.

## Optional Mola tapered extrusion study (Task 09)

The Rhino launcher offers `MeshGrammar` and `MolaTaperStudy`. The latter calls the official external HDMola 1.0.0 face operator through optional Python.NET 3.0.5 and explicitly selected .NET 8 CoreCLR. It compares the same original input/planar selection at A `(height_ratio=0.10, fraction=0.25)`, B `(0.30, 0.25)`, and C `(0.10, 0.65)` without subdivision. Mola generates the upper geometry; CHESHIRE preserves base IDs, assembles verified side/cap roles, checks budgets and complete lineage, and explicitly inherits/recomputes fields. See [Mola quickstart](rhino/MOLA_QUICKSTART.md) for the external DLL requirement, real-worker example, limits, numerical tolerances and attribution. No Mola files are distributed. The user has confirmed MolaTaperStudy works in Rhino on their gate; broader Undo/cancellation checks remain **PENDING**.

## Field-driven cap recursion (Task 10)

`MolaFieldStudy` maps original face-centroid world Z into height and XZ distance from the input bounding-box center into taper, separately. The existing real Mola operator produces G1, then extrudes only new caps for G2/G3 with height scales `1.00/0.65/0.40` and explicit original-fraction offsets `0/+0.10/-0.05`. Drivers stay associated with original faces through lineage; current cap areas are measured afresh. The Rhino comparison shows two original-face driver previews and reached generations at unchanged scale/orientation. DLL preferences live only in ignored local settings. See [field-study quickstart](rhino/MOLA_FIELD_QUICKSTART.md) for exact mappings, cap rules, unchanged budgets, real gate outputs and limitations. This is a fixed three-generation experiment, with no new operator/dependency or general Repeat engine. The user has confirmed original/driver/G1/G2/G3 display; broader Undo/cancellation checks remain **PENDING**.

## Recursive relief surface comparison (Task 11)

`MolaSurfaceStudy` retains that raw recipe and compares G1/G3 with independent terminal copies after exactly one public COMPAS Catmull-Clark level. Existing naked-boundary vertices are fixed and only boundary edges receive crease 2; no welding occurs. Raw fields, roles and lineage remain intact; derivative semantic lineage is explicitly **NOT IMPLEMENTED**, with source-stage association recorded instead. Both saved-gate comparisons pass the unchanged 50,000-count budgets. See [surface-study quickstart](rhino/MOLA_SURFACE_QUICKSTART.md) for the exact Rhino launch, count/boundary/displacement results, retained geometry and limitations. The previous MolaFieldStudy display is user-confirmed; the new surface mode's Rhino host verification remains **PENDING**. Dependencies and runtime versions are unchanged.

## Consolidated visual prototype (Task 12)

Choose **VisualPrototype** in the existing Rhino launcher to compare three independent studies on the same original gate: continuous curved ribs, clustered crown fans with perimeter side growth, and refined diagonal terraces. Fixed spatial recipes combine existing CHESHIRE fields/displacement, COMPAS subdivision and Mola extrusion; no core refactor or dependency change. Available lineage is retained, with A's terminal CC lineage explicitly unimplemented. See [prototype quickstart](rhino/VISUAL_PROTOTYPE_QUICKSTART.md) for recipes, real outputs, limits and launch. Their organization differs, but the grotesque-like design target remains weak: subtle rib detail, tiled cluster interiors and pixelated terrace bands remain. Headless checks are available; the new mode's Rhino host verification is pending.

## Bounded morphology atlas (Task 13)

The isolated [batch runner and quickstart](tools/MORPHOLOGY_QUICKSTART.md) repeat the original gate baseline, screen actual recipe controls, retain every checkpoint/field/lineage in compressed records, and build an offline fixed-camera atlas. Each candidate uses a fresh environment-isolated worker; time, counts, memory and storage stay bounded. Experiment IDs remain separate from A/B/C dispatch IDs. The B cap-only ablation is opt-in; existing Rhino modes and defaults remain unchanged. Execution, sampled crossing checks, duplicate geometry and visual observations are reported separately. Read the delivered `output/task13/study/START_HERE.md` and `atlas/index.html`; these headless comparisons do not establish Rhino-host behavior or global collision freedom.

## Weighted subdivision experiment (Task 14)

**WeightedSubdivisionStudy** compares standard, uniformly scheduled and field-modulated point placement through one new experimental operator. See the [reference/formula note](docs/WEIGHTED_SUBDIVISION_REFERENCE.md) and [study quickstart and limitations](docs/WEIGHTED_SUBDIVISION_STUDY.md). The exact saved mixed-face gate and six-face column are retained at matching comparison generations. Spatial modulation is visible, but the gate still shows repetitive relief and the target hierarchy remains weak. Stronger intersecting/fold-prone attempts are retained. No dependencies change; semantic lineage and actual new-mode Rhino-host verification remain unimplemented/pending respectively.

## Coarse gate carrier study (Task 15)

The [carrier and schedule study](docs/CARRIER_SCALE_STUDY.md) compares connected 22/88/352-face carriers with the exact 936-face saved gate, using unchanged Task 14 weighted subdivision. C0 reaches G5 and creates broader forms, but ten subsequent schedules still round those forms or add repetitive/unsafe detail. Clear macro → meso → micro hierarchy was not achieved. Under the revised schedule-first gate, spatial modulation and the conditional Rhino mode remain unimplemented. All attempts, checkpoints, fixed-camera views and diagnostic limitations are retained in the Task 15 review bundle; no dependency or existing mode changes.

## Generational point-class choreography (Task 16)

The [C0 study](docs/GENERATIONAL_WEIGHT_STUDY.md) adds only the verified later-generation face stencil and explicit immediate point origins. Sixteen deterministic schedules retain G0-G5 and exact zero-weight regression. The best partial result, C11, preserves secondary support lobes and lintel ridges better than L4, but fine detail remains repetitive; no first hierarchical gate candidate is designated. **GenerationalWeightStudy** shows the useful partial comparison in the existing Rhino bridge. Regional modulation and C1 transfer were skipped. Real isolated-worker checks pass; actual Rhino host checks remain pending. Dependencies, existing modes, core rules and budgets stay unchanged.

## Source-space spatial activity stress test (Task 18)

Frozen C0 graph fields now modulate the existing CC/DS schedules through
positive sampling associations. The 48-case screen and 12 deep comparisons
are reproducible from tracked source/seed/recipe definitions. They establish
regional control, but do not establish convincing macro-to-meso-to-micro
hierarchy or an advantage for ordered diffusion. See
[the experiment and negative controls](docs/SPATIAL_ACTIVITY_STUDY.md).
Existing Rhino modes, geometry equations and dependencies are unchanged.

## Nested topology ornament study (Task 19, experimental branch)

The isolated [ornament grammar study](docs/ORNAMENT_CAPABILITY_STUDY.md) combines
the existing C11/R13/R15 subdivision vocabulary with two real external Mola face
events. Serialized selectors and constructive cap/side ancestry control nesting;
subdivision alone never increases ornament depth. The study retains matched
actual geometry views, stopped boundaries and explicit local budgets. Its
comparative labels do not automatically establish a grotesque gate milestone.
Existing Rhino modes and global defaults remain unchanged.

## Differentiated branching (Task 20, experimental branch)

The [branching study](docs/DIFFERENTIATED_BRANCHING_STUDY.md) freezes the saved
C07 backbone and routes constructive cap/side descendants with serialized,
ordered branch tables. It compares role, depth, orientation and quiet pruning,
with explicit no-finish or single-finish policies and positive mixed-path
signatures. Geometry operators, dependencies and global budgets are unchanged;
branch metrics alone do not establish visual hierarchy.

## Subdivision beyond smoothness (Task 22, experimental branch)

The isolated [sharp-subdivision study](docs/BEYOND_SMOOTHNESS_STUDY.md) tests
literal motif attraction, finite Eq7 schedules and temporary corner locking
over the unchanged weighted-CC backend. Actual control and gate evidence
separates sharp geometry from collapse and from visual hierarchy. Heavy meshes
and checkpoints use an explicit portable external output root; compact recipes
and diagnostics remain in Git. Existing Rhino modes and dependencies stay unchanged.

## Persistent cross-cell creases (Task 23, experimental branch)

The [reference contract](docs/CROSS_CELL_CREASE_REFERENCE.md) separates exact
COMPAS integer creases and finite Uniform semi-sharp transitions from experimental
graph routing and point-placement composition. The [completed study](docs/CROSS_CELL_CREASE_STUDY.md)
retains 16 finalists, actual fixed-camera evidence and an independently reproduced
partial gate grammar. Sampled contacts, including the 256-count cap, remain
diagnostic and do not veto compatible evolution. No convincing Grotesque gate
emerged: a coherent meso fold that replaces the panel scaffold is still missing.
Standalone research freezes with that limitation; no production rescue or new
Rhino Hero mode was added.
