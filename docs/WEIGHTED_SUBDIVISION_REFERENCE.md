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
`w3`, `w4`. That extension is **not implemented**. Each generation here
reuses (1)–(3), with an explicit schedule. Point classes are recorded.

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
