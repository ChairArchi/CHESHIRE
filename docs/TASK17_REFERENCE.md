# Task 17: weighted Doo-Sabin capability

Baseline: `bba4fd7d6e3a2af8c87c91fb9aeec70c4cd37b7b`. COMPAS remains
2.15.1, Python remains 3.12; no dependency or existing CC stencil changes.

## Reference-grounded

Michael Hansmeyer, *Subdivision Beyond Smoothness*, Computational Aesthetics
2010, pp. 75–81, [publisher DOI](https://doi.org/10.2312/COMPAESTH/COMPAESTH10/075-081).
Page 77, equations (5) and (6), establishes the modified quad and triangle
Doo-Sabin corner placements, interpolation control and normal extrusion.
The publisher-indexed text was checked against the task's equations; direct
publisher PDF requests returned HTTP 403. The Bridges 2010 paper used in
Task 14 is not the source of these DS equations.

For cyclic corners, the quad rule is

`[P1*(2.25+2*w1) + (P2+P4)*(.75-w1) + .25*P3]/4 + nf*w10`.

The triangle rule is

`(2/3)*P1*(1+w1/2) + (1/6)*(P2+P3)*(1-w1) + nf*w10`.

The same reference distinguishes faces produced from prior faces, edges and
vertices; it discusses differentiating their later weights, non-stationary
weights and changing subdivision schemes between iterations. It does not
publish CHESHIRE's six exposed controls, recipes, gate monitor or selections.

## CHESHIRE experimental choices

- `src/cheshire/weighted_doosabin.py` is separate from all CC implementations.
  Public `Mesh.subdivided(scheme="doosabin", k=1)` supplies the trusted standard
  positions and topology at the installed pinned version.
- Quad/triangle coefficients above are literal. `weighted_corner` receives
  extrusion in coordinate units. Study schedules express `w10` as a ratio of
  current **global mean input edge length**; the operator uses COMPAS's unit
  current face normal. This scaling is a CHESHIRE choice, without local fields.
- Each generation serializes all six controls: `w1_face`, `w10_face`,
  `w1_edge`, `w10_edge`, `w1_vertex`, `w10_vertex`. They apply to the
  **immediately preceding generation's** face creation classes.
- C0 has no DS classes. Its first DS step uses the explicit FACE pair for all
  source faces. A CC handoff also reseeds the current CC faces this way; it does
  not relabel CC point classes as DS face classes.
- Returned F/E/V faces are constructed from known source face corners,
  adjacent edge corners and ordered incident vertex corners. Their oriented
  cycles are verified against COMPAS topology. No coordinate matching assigns
  families. Immediate vertex/face parents and source-corner identities are
  serialized at every DS checkpoint.
- Existing `LineageMap` stores positive **standard control-cage associations**,
  separately from signed weighted geometry. It is not a reconstruction of
  extrapolated geometry. Semantic field inheritance remains **NOT IMPLEMENTED**.
- Only closed, finite, valid oriented manifolds with vertex degree at least
  three are supported. Open boundaries and crease semantics are rejected
  explicitly; no new boundary algorithm or topology repair is invented.
- Unsupported face valences keep the **actual standard COMPAS DS positions**,
  with both effective weights zero. Generation, input face, valence, family,
  requested parameters and aggregate fallback counts remain in metadata.
  Polygons are not triangulated to obtain a weighted formula.
- The study budget alone is 120,000 vertices / 120,000 faces / six generations.
  Global defaults and old modes remain unchanged. Existing 60-second worker,
  30-second crossing audit, 4 GiB process-memory and available-memory guards
  are reused. Study storage remains bounded at 3 GiB. Technical stops retain
  completed checkpoints; geometry or identity drift never weakens a recipe.

## GateIntegrityMonitor: evidence only

The explicit 24 C0 vertex identities define opening sides/head/foot, supports,
lintel and ground landmarks. DS carries each generated corner's source-corner
association back to C0; clouds are averaged with equal influence per original
anchor. CC retains original corner IDs, leaving new edge/face points unassociated.
Hybrids therefore monitor a subset, with tracked and total vertex counts shown.
Cloud spread and all missing anchors are also recorded.

The opening dimensions are descendant-landmark approximations, **not actual
free aperture clearance**. Raw width/height/center, G0-normalized values,
normalized center drift, bbox dimensions and percentage drift, regional
relations, source-base displacement, all anchor displacements, components,
boundaries and manifold status are separate. A zero original center makes its
ratio null; center drift remains defined against source width/height.

There is no gate score, admissible threshold or monitor input to subdivision.
MAX_CAPABILITY and GATE_LEGIBLE are descriptive visual selections after review,
not automatic rankings or changes to geometry.

## Verification and visual limits

Focused tests independently evaluate cyclic coefficients and extrusion. Three
zero-weight steps on a closed quad box and triangle tetrahedron match public
COMPAS geometry (absolute tolerance `1e-12`), oriented topology and counts, and
repeat deterministically. Actual zero positions are taken directly from the
backend; the separate formula regression establishes the literal stencils.
Tests also cover pentagon fallback, construction lineage, source immutability,
six-row serialization, local budgets and exact unchanged C11 hybrid prefixes.

Existing fan-normal / bilinear diagnostics operate on actual polygon meshes;
their fan triangles are diagnostic approximations. Crossing audits reuse the
existing query on at most 4,096 evenly spaced actual faces per generation.
They exclude adjacent/coplanar contacts and stop after 30 transverse contacts.
Zero sampled contacts is **not a global collision certificate**. Quad-only
bilinear checks do not apply to triangles or unsupported polygons.

Headless contact sheets use actual saved polygons, the existing fixed
orthographic projection and gray light, shared bounds and registered detail
crop. A task-local System.Drawing implementation accelerates that presentation
without changing geometry. Polygon painter ordering and first-three-corner
shading are approximate; these images are not Rhino captures.

See `docs/TASK17_RESULTS.md` and the review archive for actual schedules,
checkpoint outcomes, warning counts, drift trajectories and host status.
