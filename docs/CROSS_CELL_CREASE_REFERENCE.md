# Cross-cell crease reference contract

## REFERENCE-GROUNDED CREASE RULES

Tony DeRose, Michael Kass and Tien Truong, [Subdivision Surfaces in Character
Animation](https://doi.org/10.1145/280814.280826), SIGGRAPH 1998, pp.85-94.
The [primary Pixar PDF](https://research.pixar.com/docs/1998.SiggraphPapers.DKT.pdf)
was checked through indexed primary text: direct fetching exceeds the browser's
32MB limit; ACM PDF fetching returned 403. No paper is redistributed.

Integer sharp edges use `(A+B)/2`; a vertex with two sharp neighbors uses
`(A+6V+B)/8`; three or more retain V; zero/one use the smooth rule.
Sharpness counts initial sharp refinements and then transitions to smooth.
Fractional sharpness blends neighboring integer behaviors. The paper's variable
crease appendix additionally uses Chaikin averaging; CHESHIRE does not claim
to implement that appendix or its vertex transition convention.

Hansmeyer's [Subdivision Beyond Smoothness](https://doi.org/10.2312/COMPAESTH/COMPAESTH10/075-081)
supplies the existing Task22 motif substrate, not the integer crease stencil.

## INSTALLED COMPAS EVIDENCE

The actual installed version is **2.15.1**. The inspected implementation is
`compas/datastructures/mesh/subdivision.py`, `mesh_subdivide_catmullclark`, accessed
through `Mesh.subdivided(scheme="catmullclark", k=1)`; the function is not exported
from the top-level datastructures namespace. The runtime verification manifest
records its installed file SHA256, without copying the source.

`crease` is an optional edge attribute. A truthy value selects the sharp midpoint
and counts as an incident sharp edge. Children receive `crease-1`. The documented
domain is integer sharpness; a fractional value is not a fractional blend and can
become a negative truthy child value. CHESHIRE therefore never passes fractions
to this COMPAS attribute. Finite nonnegative integers give the required decay.
Zero/one incident creases use smooth vertex placement; two use the crease rule;
three or more retain the corner. A listed `fixed` vertex overrides movement,
independently of the crease count. The trusted study contract is closed manifold
input; it does not invent a boundary policy from this implementation.

## MODERN UNIFORM FRACTIONAL COMPARISON

The actual tagged OpenSubdiv **v3_6_0** sources were checked:
[sharpness transitions](https://github.com/PixarAnimationStudios/OpenSubdiv/blob/v3_6_0/opensubdiv/sdc/crease.cpp),
[mask combinations](https://github.com/PixarAnimationStudios/OpenSubdiv/blob/v3_6_0/opensubdiv/sdc/scheme.h),
[Catmark masks](https://github.com/PixarAnimationStudios/OpenSubdiv/blob/v3_6_0/opensubdiv/sdc/catmarkScheme.h).

For `0<s<1`, an edge blends smooth and midpoint with sharp weight s. Vertex masks
are determined from parent positive edges and child positive edges. Equal rules
keep the parent mask. A rule transition blends the parent and child masks using
the mean sharpness of incident edges that disappear (`0<s<=1`), clamped to one.
Smooth/dart use smooth placement. This handles corner-to-crease and
crease-to-smooth separately; a naive maximum incident sharpness is not used.

## CHESHIRE NETWORK ROUTING / DESIGN COMPOSITION

`INTEGER_COMPAS` delegates actual integer geometry to installed COMPAS, preserving
its exact arithmetic and oriented ordering. `UNIFORM_FRACTIONAL` implements the
finite modern Uniform subset: `child_s=max(s-1,0)`, including spatially varying
initial profiles. It does not implement Chaikin neighbor averaging, vertex
sharpness tags, OpenSubdiv's infinite sentinel, limits or an OpenSubdiv backend.
All-integer values use the exact COMPAS path in either mode.

Creases are authoritative immutable serialized connected graphs of actual mesh
edges. Overlapping networks use maximum sharpness for geometry while retaining
each network's own ancestry and descendants. After refinement implicit COMPAS
attributes are cleared; exact sharpness state lives in the explicit networks.
This separates state from the old weighted operator's unsupported-crease guard.

Structural incidence identifies new edge/face points; no nearest-coordinate
lineage is assigned. A declared edge has exactly two CC child edges, including
zero-sharpness descendants for survival comparisons. Signed/mixed geometry is
separate from existing positive construction associations and face histories;
generic semantic inheritance is not invented.

Source architectural targets, graph routing costs, sparse junctions, profiles,
visibility thresholds and composition selectors are CHESHIRE design choices.
They do not alter the reference stencil or move vertices outside its rules.
Mola remains downstream. Affected terminal crease semantics are reported
explicitly, rather than inferred from face IDs or nearby coordinates.

## DESIGN-FIRST OVERRIDE AND ADDITIVE FOLD COMPOSITION

The user's subsequent Task23 override makes **contact counts diagnostic only**.
The sampler stops counting at 256; it never stops compatible finite evolution.
Positive sampled contacts are labeled `SELF_INTERSECTING_CAPABILITY`. The clean
sample preference remains separate from finite/topological/operator usability.
Historical pre-override results retain their original recorded policy.

`crease_folding.py` adds an explicitly experimental placement after the trusted
crease mask: `P = P_crease + alpha*(P_existing_sharp_weighted - P_standard_smooth)`.
Alpha is the mean input support of the corresponding construction point;
support falls linearly with mesh-edge hops from the declared current network.
The existing weighted CC and literal Eq10/11 compute the second term. Points
match by original corner/edge/face identity, never nearest geometry. This
additive composition is a CHESHIRE design choice, **not a published DeRose or
OpenSubdiv stencil**. Zero weights return the exact reference crease path.
All weights are serialized for each generation. `wf/we/wp` are absolute model
units; the interpolation and Eq10/11 controls are dimensionless. No later
point-origin stencil is invented in this composition; `w3/w4` stay zero.

The standard tapered-event height ceiling remains 0.5. Task23 explicitly passes
`allow_large_taper=True` to admit finite positive heights above that experimental
ceiling. The DLL call, ordering/oracle checks, fraction domain, local polygon
eligibility, budgets and all default callers remain unchanged. A real official
HDMola unit quad with height ratio 1.0 succeeds; float32 output is recorded rather
than rounded into false exactness. This is an opt-in parameter-domain extension,
not a new geometry algorithm or a modification to the external library.
