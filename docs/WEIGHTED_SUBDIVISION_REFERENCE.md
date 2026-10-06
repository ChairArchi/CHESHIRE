# CHESHIRE Extended-CC Experimental Subset

Reference gate completed before operator implementation (2026-10-06).
Baseline: `7ece1afa00774a42251f202c106cdb2d6dacd350`; COMPAS 2.15.1.

## REFERENCE-GROUNDED

[Hansmeyer, From Mesh to Ornament (2010), p. 286, equations 1–3](https://ecaade.org/current/wp-content/uploads/2022/03/eCAADe_2010.pdf)
defines these stencils. The publisher's indexed equation page was inspected;
its 28 MB proceedings exceeded the browser fetch limit. The formulas were
cross-checked against [Hansmeyer, Design by Subdivision (2010), p. 168](https://archive.bridgesmathart.org/2010/bridges2010-167.pdf).
PDF screenshots were unavailable. No equations were inferred from pictures.

With input corners P, face centres C, incident-face mean F, incident-edge
midpoint mean E, and vertex valence n:

```text
face:   Qf = mean(P around face) + nf * wf                         (1)
edge:   Qe = ((C1+C2)*(1+w1) + (P1+P2)*(1-w1))/4 + ne * we        (2)
corner: Qp = (F*(1+w2) + E*(2-w2) + P*(n-3))/n + np * wp         (3)
```

`w1`, `w2` change interpolation; `wf`, `we`, `wp` change normal
extrusion. Zero weights give the standard interior CC stencil. The same
paper's equation (4) distinguishes earlier corner/face/edge classes using
`w3`, `w4`. Task 14 continues to reuse (1)–(3) unchanged. Task 16 adds the
opt-in later-generation face stencil documented below; existing modes do
not automatically enable it.

[Mesh Grammars (2013)](https://doi.org/10.52842/conf.caadria.2013.821)
provides conceptual context, not additional equations used here. Its PDF
endpoint returned HTTP 429; this implementation makes no claim to reproduce it.

## CHESHIRE-DEFINED

The reference notation leaves evaluation order and normal normalization
insufficiently precise for an exact reproduction claim. CHESHIRE uses input
face centroids and original edge midpoints in all interpolation stencils,
without cascading same-step extrusions into other classes. Face normals are
COMPAS unit normals; edge normals are their arithmetic mean, and corner
normals are the normalized incident-face mean. Undefined/cancelling normals
reject a requested nonzero extrusion, rather than inventing a direction.

For triangle/quad input, a face centre is the arithmetic mean of its actual
corners; valence n and all incident means remain explicit. This is an affine
mixed-face generalization, not a quad-only reference replication. The public
COMPAS CC implementation supplies topology; only point positions change.
No welding, triangulation or repair occurs. Creased interior edges are
unsupported and rejected, rather than silently discarding crease semantics.

Naked original vertices stay fixed. Naked edge points remain exact original
midpoints. Boundary edge/corner extrusion is zero. This conservative policy
is CHESHIRE's, not a claimed Hansmeyer boundary rule. Closed zero-weight
controls match public COMPAS CC; open controls intentionally differ from its
unconstrained boundary smoothing, but match the existing conservative wrapper.

Operator extrusion weights have coordinate units. Study recipes specify ratios
of the current global mean input edge length and record the resulting actual
coordinate-unit weights at every point. U therefore uses identical weights
everywhere, including identical extrusion lengths before boundary suppression.
This explicit scale convention
is not asserted to be the reference's unspecified face-dimension scaling.

F keeps two drivers separate: source Z normalized once, transported through
positive control-cage associations (corner identity, edge endpoint halves,
face equal-corner means); and current incident-face normal variation measured
by existing `analyze_vertex_attributes`. The latter is mean pairwise unit
normal angle divided by pi, unavailable at boundaries, **not differential
curvature nor the paper's planarity measure**. Existing smoothstep mappings
control extrusion amplitude (Z) and interpolation offset (normal variation).

Control-cage associations are sampling coordinates only, not exact semantic
interpolation of displaced geometry. Geometry coefficients can be negative;
they never enter semantic inheritance. Full semantic lineage is explicitly
**NOT IMPLEMENTED**. Each generated point records its immediate source class
and IDs; each child face records its parent face/corner. No old fields or face
IDs are copied onto new topology.

## Task 16: verified later-generation face stencil

The equation was independently checked against the publisher's text of
[Hansmeyer, Design by Subdivision (2010), p. 168, equation (4)](https://archive.bridgesmathart.org/2010/bridges2010-167.pdf#page=2).
The large eCAADe proceedings again exceeded the browser fetch limit, and
the screenshot endpoint failed; the accessible primary paper's equation
text and the supplied Task 16 equation agree. No stencil was inferred from
a visual design example. Non-stationary weights are described on p. 169.

For a child quad from the immediately preceding Catmull-Clark generation:

```text
V'  = immediately previous-vertex-derived point
F'  = immediately face-derived point
E1', E2' = immediately edge-derived points

F'' = ((V'*(1+w3) + F'*(1-w3))*(1+w4)
       + (E1'+E2')*(1-w4))/4 + nf*wf                       (4)
```

The task calls the unchanged face-normal extrusion `w10`; the primary
paper and existing code call it `wf`. Similarly task `w11/w12` correspond
to existing `we/wp`. These are notation aliases, not extra controls. `w3`
and `w4` are dimensionless. The coefficients of V/F/E1/E2 are respectively
`(1+w3)(1+w4)/4`, `(1-w3)(1+w4)/4`, `(1-w4)/4`, `(1-w4)/4`, summing to one.
They may be negative and never become semantic/sampling weights.

The opt-in implementation is `cheshire.generational_subdivision`.
It calls the unchanged Task 14 operator, then changes **only** eligible
face-point XYZ. Edge and corner equations (2)/(3), their input-centroid
evaluation, boundary suppression, normals, COMPAS topology, count budget
checks and positive control-cage associations stay unchanged. Same-step
equation (4) face extrusions do not feed into edge/corner stencils.

Every generated vertex receives `VERTEX_DERIVED`, `EDGE_DERIVED` or
`FACE_DERIVED` and its creation generation, both as mesh attributes and
explicit origin records. Classes reset each step: a retained earlier face
point becomes vertex-derived when created as the next corner point.
Source IDs come from Task 14's verified topology correspondence, never
coordinates. Origin records are serialized alongside exchange geometry;
OBJ itself carries only geometry/connectivity.

Eligibility requires one V, one F and two E classes from the immediately
preceding generation, opposite V/F in the actual face cycle, and parent
edge incidence matching the recorded parent-face corner neighborhood.
Canonical V/F identities follow class/ancestry; E1/E2 are sorted by integer
ID, and their formula is symmetric. Cyclic rotations and reversed cycles
therefore classify identically. Missing, stale, wrong-pattern or mismatched
ancestry falls back to equation (1) with a recorded per-face reason.
G1 has no previous generated origins and intentionally uses equation (1).

With both new weights zero, an explicit fast path retains the old face
point exactly, including summation order. Focused independent coefficient
tests verify nonzero equation (4), while multigeneration regression verifies
ordered XYZ and connectivity identity. A real C0 pre-study gate also compares
G1–G5 against the saved Task 15 B/C0 checkpoints exactly. New origin metadata
means complete attributed COMPAS objects are not byte-identical; geometry is.

Reference-grounded here are equation (4), immediate creation-class distinction
and generation-varying weights. CHESHIRE's exact schedules, candidate families,
global edge-length extrusion scale, incidence/fallback contract, 50k budgets,
diagnostic interpretations, visual selection and any optional regional study
are experimental choices, not schedules published by Hansmeyer.
Full semantic lineage remains **NOT IMPLEMENTED**. Immediate origins and
topological original-face chains are diagnostic geometric associations.
