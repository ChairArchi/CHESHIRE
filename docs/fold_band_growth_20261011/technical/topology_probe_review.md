# Same actual surface: quad versus triangle subdivision

Input: original SPAN_SPARSE G00, 802 physical vertices / 1600 triangles. TRI input is a byte copy of checkpoint.npz; XYZ, faces and chart are identical. Original quad controls and source remain untouched.

Both paths reuse iaac_repeat.py: n4 powers [4,4], centres 2.5/7.5, scale 1.6, axial 2.8, 18 finite escape iterations, nearest-outside fraction .55, budgets G1 .35 / G2 .28. Both use the SAME fixed sampled coarse outside grid. This differs from FIELD_SEED/FULL_LOOP local target refinement at G2/G3.

- QUAD: original 402 V / 400 Q controls; one Q becomes four Q. Previous vertices, shared edge midpoints and face centres receive field displacement. Arithmetic render fan centres are added afterwards and do not become next-stage controls.
- TRI: original actual render fan centres become control vertices. Each physical triangle becomes four shared-midpoint triangles, then all old/new vertices receive field displacement. Fan lineage and sample placement are the intended differences.
- Physical counts match: G1 3202 V / 6400 T, G2 12802 V / 25600 T. G2 controls differ: QUAD 6402 V / 6400 Q, TRI 12802 V / 25600 T. Same physical counts do not imply same field-query positions or connectivity.

## Actual three-view reading

Macro silhouette, two expanded bodies, neck and cup relationships remain nearly identical. TRI introduces more oblique facets and irregular side recess walls. QUAD retains slightly calmer vertical strips. Both increase shallow roughness on field-active bulbs while broad terminal/waist facets remain. The visible difference at G2 is chiefly small-facet orientation and placement, not a new macro/meso event.

Triangular subdivision is actually implemented here, but topology change alone has not solved the design bottleneck. Both stop at G2: there is no observed reason to expect G3 to deliver missing hierarchy. Which original IAAC columns use which subdivision remains unconfirmed. No exact reproduction or physical folding claim.

## Lightweight checks

Both G2 models are single connected, watertight and winding consistent. Actual X/Y reflection error is below 3.63e-15; reflected triangle sets match. Minimum triangle area: QUAD 2.9247e-5, TRI 2.9082e-5, retaining the existing 1e-12 threshold. Self-intersection is NOT CHECKED for this intermediate comparison. Thickness, structural behaviour and fabrication are NOT CHECKED. No new smoothing, crease protection, section rebuilding or random noise.

Actual comparison: review/topology_G02_comparison.png
Meshes, checkpoints and generation logs: QUAD_NEAREST/G01,G02 and TRI_NEAREST/G01,G02
Small composition wrapper: experiments/fold_band_growth_20261011/topology_probe.py
