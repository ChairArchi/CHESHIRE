# Existing dual subdivision + finite field — G1 to G3

Outputs: `E:/CHESHIRE_DATA/fold_band_growth_20261011/DUAL_FIELD_LOOP`.
All three stages have actual `geometry.npz`, `gate.ply`, `checkpoint.npz`,
mixed-face `control_poly.npz`, `ds_lineage.npz`, operation fields, operator
log, Blender `column.blend`, and `preview/{front,oblique,side}.png`.

## Implemented, without original-source edits

`dual_probe.py` calls the existing `weighted_doosabin_once` backed by installed
COMPAS 2.15.1. It creates face-corner controls and genuine face/edge/vertex
connecting faces, rather than reusing the quad V/E/F point-offset topology.
The exact same SPAN_SPARSE input is used; no new input-design variation.

Each cycle is one weighted DS step followed by one existing n4 finite
nearest-outside field pass. Field powers [4,4], centres [2.5,7.5], axial 2.8,
scales [1.6,1.6], 18 internal iterations, fraction .55, step budgets
.35/.28/.22 and local target factors 1/2/3 match FIELD_SEED. This is not an
isolated topology-only comparison: DS intrinsically changes corner positions
and adds signed family-specific normal offsets.

Weights, all three generations:

| Incoming face family | w1 | w10, model units |
|---|---:|---:|
| FACE_DERIVED | .65 | -.12 |
| EDGE_DERIVED | .35 | +.10 |
| VERTEX_DERIVED | .35 | +.06 |

G1 has no previous DS families, so every source face explicitly uses the face
pair. Later cycles use actual topology-derived immediate-generation family
labels. These labels are not semantic crease-memory tags. Material chart is
propagated by the operator's existing positive STANDARD DS lineage weights,
separately from weighted geometry. No angle reparameterization or posthoc
coordinate averaging is used. Intrinsic weighted DS corner averaging is
present; separate geometric smoothing is absent. No authored return event,
cap lock, noise or physical fold solver.

Mixed polygons are stored padded with explicit valid sizes. The field queries
only actual controls; their symmetric edge graph supplies its topology check.
The authoritative physical surface is explicit arithmetic polygon-centre
triangle fans, checked separately for reflection. Fan centres are never
subsequent controls. This fixes a concrete triangulation, without claiming
an intrinsic unique surface for nonplanar polygons.

## Actual geometry and limited checks

| Stage | Control vertices / faces | Physical vertices / triangles | Minimum triangle area | Maximum X/Y reflection error |
|---|---:|---:|---:|---:|
| G1 | 1,600 / 1,602 | 3,202 / 6,400 | 1.91629e-6 | 3.093e-15 |
| G2 | 6,400 / 6,402 | 12,802 / 25,600 | 2.92700e-7 | 1.860e-14 |
| G3 | 25,600 / 25,602 | 51,202 / 102,400 | 2.07941e-7 | 1.672e-13 |

The unchanged area threshold is 1e-12; all pass. Actual rendered triangles
pass reflected-triangle-set, watertight and consistent-winding checks. The
existing DS operator records one connected component before and after.
Each stage has 16 triangles, two 8-gons and otherwise quads in its CONTROL
mesh. G2/G3 encounter the two incoming 8-gons: the original operator explicitly
falls back to COMPAS STANDARD placement and zero extrusion for these, with
logs preserved. No unsupported weighted n-gon rule was invented.
Self-intersection, thickness, physical structure and fabrication are untested.

## Visual outcome and stopping point

G2 offers a useful independent geometric-cell direction: thick connected
inset borders appear across the body, not only along isolated rims; front
and side share the same logic. However, broad curved returns become armoured
polygon panels. Large-scale folded continuity is weaker. This is not a
demonstrated improvement of deep folds or a successful IAAC reproduction.

G3 retains the large panels while their surroundings subdivide into a denser
crust, especially at the neck and ends. It does not recover the lost curved
continuity. Keep G2 as the clearer comparison, G3 as the limit record. Stop
after G3 with no additional tuning or generations.

Public IAAC frame/void variation motivates testing another connectivity;
there is no claim that IAAC's original Mandelbrot project used Doo-Sabin or
these weights. The implemented algorithm, observed appearance and unknown
original method remain separate.
