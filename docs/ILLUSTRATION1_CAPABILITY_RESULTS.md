# Illustration 1: controlled capability result

Branch: `research/hansmeyer-cleanroom`. One fixed modified schedule, three
controls, all from the same single cube [-1,1]^3. Every control reached G8.
Existing checkpoint outputs are preserved. No DS, fusing, spatial weights,
locking, new subdivision engine or parameter search.

## Actual evidence

- `output/illustration1/comparison.png`: rows standard CC / modified weights /
  same modified weights plus vertex-normal extrusion; columns G0/G2/G4/G6/G8.
- `output/illustration1/onset.png`: G1/G3 from the same two modified runs.
- `output/illustration1/G8_details.png`: common 2x display scale, same camera/light.
- Each control directory has its PNGs and actual OBJ meshes for G0/G2/G4/G6/G8.
  NPZ meshes additionally retain every G0-G8, including CC corner provenance.
- `camera.json` fixes camera, light, origin and one absolute display scale.
  No per-object normalization, mesh smoothing or geometry repair for display.

## What appeared, and when

| generation | modified weights only | same weights + independent vertex-normal extrusion |
|---|---|---|
| G1 | broad inward edge regions and outward face centers; no rounded CC sphere | original vertex regions project farther; face/edge points unchanged from the other modified control |
| G2 | distinct small corner protrusions with broad grooves/inset face regions | stronger pointed protrusions and larger local volume |
| G3-G4 | additional repeated angular folds across original face regions | sharper, longer spikes and deeper folded regions |
| G6 | smaller repeated folds and serrated silhouettes appear within coarse face regions | coarse projections persist alongside finer folded clusters |
| G8 | still finer angular surface development; the cube-like envelope remains recognizable | denser small-scale folding with a more pronounced spiky envelope |

The standard control rounds toward a smooth sphere-like shape. All three have
identical connectivity and counts at each generation: the differences are
actual coordinate changes, not just denser meshes. The two modified controls
use exactly the same w1-w4; only w12 differs. At G1, this displacement affects
only the eight old-vertex points, as independently checked by the formula.

This demonstrates **CC-only generation of new local protrusions, grooves and
repeated smaller folds** with uniform, non-stationary weights. Vertex-normal
extrusion has an observable geometric effect. It does not demonstrate a match
to Illustration 1's more articulated multi-scale volumes or its original
parameters. The own recipe produces many angular, spike-like, tightly folded
features; these are not automatically useful architectural complexity.

## Exact own recipe, not unpublished original parameters

| G | w1 | w2 | w3 | w4 | w12 in extrusion control |
|---|---:|---:|---:|---:|---:|
| 1 | 1.4 | -1.2 | 0 | 0 | 0.06 |
| 2 | -1.25 | 2.4 | 1.25 | 1.15 | 0.10 |
| 3 | 1.6 | -1.4 | -1.1 | -1.05 | -0.06 |
| 4 | -1.15 | 2.3 | 1.2 | 1.1 | 0.12 |
| 5 | 1.35 | -1.1 | -1.1 | -0.95 | -0.08 |
| 6 | -1.05 | 2.2 | 1.15 | 1.05 | 0.12 |
| 7 | 1.2 | -1.0 | -1.05 | -0.9 | -0.08 |
| 8 | -1.1 | 2.1 | 1.1 | 0.95 | 0.12 |

w10=w11=0 in all controls; w12=0 in weights-only; all weights=0 in standard.
Same numerical row everywhere within each generation. Normals use the existing
perimeter-scaled face-normal mean at each input vertex. No normal replacement
or normalization was silently introduced. Exact machine-readable recipe:
`experiments/illustration1/recipe.json`; runner: `experiments/illustration1/run.py`.
See the experiment README for commands, scope and paper-based parameter rationale.

## Minimum mathematical checks and limits

Every G8 mesh: 393,218 vertices / 786,432 edges / 393,216 quads, Euler 2.
Finite positions, nonzero polygon normal vectors, opposite shared-edge winding,
expected counts, identical control connectivity, affine mask sums and the known
standard cube G1 vertex position passed. The independent G1 vertex displacement
equals w12*(8/3)*the input cube vertex; face/edge point equality also passed.
No previous full regression suite was run.

Supplementary G8 adjacent-face angle medians are 0.315 / 52.112 / 91.967 degrees
for the three controls. High angles may reflect severe folding and are not a
quality score. Nonzero net polygon normals do not prove that individual quads
are planar or simple. Self-intersection-free embedded surfaces, positive solid
volume and printability have not been established. No crossing was repaired.

**Decision supported:** a limited CC-only capability is directly demonstrated;
uniform modified subdivision is not restricted to smoothing in this test.
The useful quality and stronger volume hierarchy of Illustration 1 are not
demonstrated. This single recipe neither proves nor disproves the method's
overall limits. Stop here for user review; no additional schedule or research.
