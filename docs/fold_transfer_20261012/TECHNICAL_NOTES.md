# Fold transfer — implementation record

Code: `experiments/fold_transfer_20261012`. Large artifacts: `E:/CHESHIRE_DATA/fold_transfer_20261012`. Parent: `442d641`. Original operators, inputs and earlier candidates are unchanged. No separate smoothing, noise texture, normal map, physical origami solver, Tissue or gate generation is used.

## Input boundary and reuse

Both G0 inputs use the existing 25-ring/16-sector carrier: 402 controls, 400 quads, common chart, classes and rest coordinates. SPAN reads the actual saved SPAN_SPARSE G0. COUNTER directly evaluates the existing `seed_mass.evaluate` COUNTER recipe on that chart. Its geometry differs from SPAN before any growth pass. Unsplit end fans remain coarse; no cap repair is claimed.

G1–G3 use the existing OVERLAP recipe: Task36 with averaging gain zero, then the finite spherical-power field; two existing macro PCHIP returns precede G2 only. SPAN reuses its exact stored lineage; COUNTER executes that recipe from its own G0. This is not an independent replay audit of SPAN. Field escape counts are 4/8/18, with movement budgets .35/.28/.22. Those counts are internal classifier iterations, not mesh generations or physical folds.

G4 uses one inactive Task36 split. The old G3 mean-fan surface is retained during the split by the existing native VF child fan option. Subsequent inactive VF splits sample the inherited V/F diagonal. An array-only check on actual source G3 found plane residual below 8.95e-16 with unchanged inherited controls. This statement applies before displacement; it does not promise preservation of a face after active deformation.

Two smaller PCHIP return events are derived from the same parent-event recipe, in material height/angle coordinates. They cross multiple cells. The original smooth_event fixed .05 angular height offset and end envelope remain; this is not a new scale-invariant law. Directions are reflected constructively in X/Y. No input-specific branch selects event positions, strengths or field parameters.

## Memory and the matched field comparison

Both baselines are unprotected through G3. G4 registers the same legacy event bank at the same chart stage. Profile bands have a true plateau, inner .003 and outer .010 normalized height. Tags follow Task36's actual sampling, including VF eligibility. Returns are multiplied by one minus inherited tags. The new event tags are stored only where return displacement is nonzero.

RETURN_ONLY is the post-return geometry. UNPROTECTED and PROTECTED evaluate exactly the same post-return geometry with the same field query: power-4 volumes, escape count18, fraction.55, budget.16, local target factor2. Raw field vectors are computed once per input. PROTECTED fixes all inherited controls and attenuates newborn vectors with propagated tags. No angle constraint, automatic crease extraction or mechanical memory is implemented.

The matched G4 array comparison confirms exact equality between inputs for chart, topology, lineage, tags, field weights and return vectors. Actual pre-return coordinates differ at 102,401 controls, max1.436713 and RMS.347057 model units. Raw field vectors differ because they query different actual geometry. For both inputs the inherited return core has1,190 controls, movement0. Field protection has1,816 feature-core controls: raw field moves414 in SPAN /488 in COUNTER, applied field moves0. All old controls have applied field movement0. This nonempty check replaces the vacuous zero-core claim identified in the previous study.

The initial COUNTER G4 run mixed carried G2 tags with fresh G3 registration, while reused SPAN had fresh registration only. That run is retained under `COUNTER/*/G04` as an invalid strict-transfer comparison. Corrected COUNTER outputs are under `COUNTER_MATCHED/*/G04`. No parameter was tuned for COUNTER; initialization was matched. SPAN already followed the matching initialization and was not rerun. Boards exclude the old diagnostic run.

## Interpretation and checks

Actual whole and meso renders favor RETURN_ONLY for clear shoulders and valleys. Protection retains central layers but introduces denser cell zigzags. A plausible mechanism is differential movement between pinned inherited points and active newborn points; this is an interpretation, not a separately isolated causal experiment. Small fixed front/side zone crops show little field response and do not demonstrate global crease preservation. Surface retention, numerical point protection and aesthetic success are distinct.

Two selected RETURN_ONLY meshes received core checks on authoritative float64 `geometry.npz`: one closed connected surface, consistent winding, no boundary/nonmanifold edges, exact reflected triangle sets X/Y, error<4.25e-15, minimum area>1e-12. CGAL detects self-intersection witnesses in both. `first_only` returns witnesses, not exhaustive totals. Other G4 variants have intermediate integrity/render checks only. Fabrication, thickness and structural performance remain unverified. No G5 was generated because the visual benefit was insufficient.

The small `--input` adapter accepts another G0 on the documented chart/topology/lineage. It does not remesh arbitrary inputs and has not been exercised on a third input. Height10 reference units, field placement, two-event schedule and the existing return kernel bound the demonstrated scope. The unused G5 schedule in recipe.json is a proposal, not an executed result.

IAAC's public subdivision/field loop remains the reference, not recovered executable code. Its exact equation/weights are not claimed here; see the preserved [primary-source comparison](../column_detail_20261012/SOURCE_NOTES.md). Current result images contain only CHESHIRE's saved triangle geometry with uniform material and flat geometric normals. Identical whole cameras and fixed close-up coordinates are recorded by the existing render scripts.
