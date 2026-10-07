# Task29 reference equation audit (before search)

Primary source: Michael Hansmeyer, *Design by Subdivision*, Bridges 2010,
pp.167–174, https://archive.bridgesmathart.org/2010/bridges2010-167.pdf .
The actual PDF text and the rendered p.168 diagrams were checked, including
Figure 2. PDF retrieval used the same official server's HTTP endpoint because
the HTTPS download returned HTTP465; no certificate verification was disabled.

## Equations and actual dependencies

Here P denotes the current iteration's input coordinates; n denotes normals
of that input. Introduce S explicitly because the prose describes dimensional
scaling without specifying a unique scalar formula.

1. F' = sum(P_j)/k + n_f wf S_f.
2. E' = [(F'_a+F'_b)(1+w1)+(P_a+P_b)(1-w1)]/4 + n_e we S_e.
3. V' = [Fbar(1+w2) + 2 Rbar(1-w2/2) + (i-3)P]/i + n_p wp S_v.
4. Later F'' = [(V'(1+w3)+F'(1-w3))(1+w4)+(E'_1+E'_2)(1-w4)]/4 + n_f wf S_f.
10. F* = F' + w6 sum_j (P_j-F') u_j.
11. E* = E' + w7 [(P_a-E')u_a+(P_b-E')u_b].

In Eq4 the primed quantities are the **actual input descendants from the prior
iteration**, not points being computed concurrently. Each canonical child
quad has one previous-vertex point opposite one face point and two edge points.
Triangles or edited quads without that provenance fall back to Eq1 explicitly.

Eq2's prose unambiguously refers to new face points. Eq3 calls E an average of
edge midpoints without a prime and thus has a notation ambiguity if read alone.
Figure2's trivalent vertex stencil has neighbour coefficient 6 independent of
w1; substituting newly generated Eq2 edges would introduce w1 and change that
coefficient. Its central coefficient is 15-3w2 and opposite face-corner
coefficient 1+w2, agreeing with **original endpoint midpoints R**. This reading
also yields standard closed Catmull–Clark at zero controls. Consequently this
implementation uses completed new face points Fbar and original midpoints
Rbar in Eq3. We do not implement an all-new-edge interpretation under the
reference name. Face extrusion changes faces, edges and original-vertex
descendants unless a downstream coefficient (e.g. 1+w2=0) cancels it. Edge
extrusion does not move same-iteration vertex descendants in this reading.

Dependency graph: current P -> input normals and scales; P/prior provenance ->
Eq1 or Eq4 -> Eq10 complete faces -> Eq2 -> Eq11 complete edges. Complete
faces + original endpoint midpoints + original P -> Eq3. Then connect new
quad children. Eq10/11's position in that completion sequence is an explicit
implementation decision: the later paper section introduces the attraction
terms but does not supply executable scheduling code. Unmodified Eq1–4 have
direct diagram and neutral-mask checks; we do not claim access to unpublished
Digital Grotesque software.

## Existing CHESHIRE / material differences

`weighted_subdivision.py` computes original centroids, then independently
places faces, edges and corners. Edges and corner Fbar use original centroids.
`generational_subdivision.py` changes only face points after those other
classes have already been calculated. `sharp_subdivision.py` then applies
Eq10/11 without downstream propagation. Thus wf, Eq4 and Eq10 face movements
cannot affect same-iteration legacy edge/corner positions. This can materially
change folds. The actual legacy functions are called unchanged for M0; the
new array path is opt-in, not a replacement or a generic kernel rewrite.

Global scale previously means current mean unique edge length. Paper extrusion
uses incident face dimensions. Task29 defines face S as arithmetic mean current
perimeter edge length, edge S as mean of its two incident face S, and vertex S
as mean incident face S. This is a deterministic interpretation, not a uniquely
mandated paper formula. M1/M2 use identical rows, cube and topology; only scale
changes. wf/we/wp are ratios; recovered historical absolute H1 offsets are
explicitly divided by initial cube side1000 before transfer. This changes
their subsequent scale policy and is never called an exact old-world replay.

Face normal is unit input polygon area-vector normal. Edge normal is the
arithmetic mean of two unit face normals, **not renormalized**, as the prose
defines. Vertex normal is normalized incident face mean; the paper does not
specify its computational convention. Vanishing normals become zero, logged
through area diagnostics; finite geometry is required. Standard-neutral
agreement is tested on skew closed cubes, not assumed from test counts.

## Generations, intrinsic and topology

Nonstationary discrete weights are directly supported by the paper. Eq7
trends are optional and unnecessary for the finite deterministic schedules.
Current legacy u maps only (valence,incident face count), which conflates
different arrangements. Paper motifs are more general; we make no equivalence
claim. Intrinsic interpolation is a CHESHIRE experimental rule using specified
current normal variation/planarity, local scale, or positive original-cage
association. It is not arbitrary ID noise or gate semantics.

Fixed CC connectivity alone preserves combinatorial genus. The paper discusses
joining vertices at coincidence/distance thresholds; later Digital GrotesqueII
describes topology changes and porosity, but does not publish the full algorithm:
https://michael-hansmeyer.com/digital-grotesque-II.html . A bounded, audited
weld experiment, if needed after A–D, is an extension, not exact DGII.

Numerical tests independently evaluate Eq1/2/3/4/10/11 with scalar loops on
tiny closed fixtures, check downstream propagation/cancellation, finite XYZ,
neutral COMPAS CC, deterministic intrinsic state, and explicit rejection of
open input. These tests establish equation consistency only. Visual hierarchy
and retention require the saved actual geometry and flat-normal renders.

## Post-search extensions and results

The initial 32 intrinsic variants use current normal disagreement, planarity,
current local scale or positive original-cage association to interpolate declared
control intervals. Another 32 variants introduce an opt-in geometric vertex lock:
where current unscaled normal disagreement exceeds a declared threshold, the
input corner keeps its exact current XYZ. The mask is reevaluated each iteration;
new face and edge points still undergo modified subdivision. This is an explicit
CHESHIRE rule motivated by tagged/locked vertices, not a missing paper equation.
No permanent original-position constraint or arbitrary vertex-ID field is added.
The selected FINAL_DX00 locks at disagreement >=0.12 from G3 onward.
A full G3–G8 ablation removes only locking while keeping all other controls and
the exact saved G2 input. It confirms more retained angular clusters with locks,
but persistent sharp normal jumps and repeated fine motifs remain.

The 24 bounded joining experiments accepted three actual connectivity changes,
accepted thirteen no-merge cases and rejected eight invalid proposals. Pair maps,
valence distributions, before/after incidence and pre-weld XYZ are saved. Valid
changes preserve genus0; they did not generate valid porosity or unlock convincing
nested motifs. The chosen lead does not use topology change.
Both extensions remain opt-in. Neither is claimed equivalent to unpublished
Digital Grotesque II algorithms. Final generative verdict is PARTIAL after the
complete experiment, despite exact replay/file checks and 838 passing tests.
