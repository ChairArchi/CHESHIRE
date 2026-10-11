# Fold return / anchor comparison — implementation record

## Scope and lineage

The current adapter reuses existing CHESHIRE operations. It implements no new general engine, physical origami solver, Tissue pass, DS pass, topology replacement or gate application. It stops at G4 for ANCHOR and at G3 for the two diagnostic alternatives. The former whole-column cut/reflect/Boolean trial remains a separate stopped experiment: [scope failure](../structural_fold_20261012/STOPPED.md).

Two distinct lineages must remain distinct:

| Lineage | Actual source | Generated stages | New operations |
|---|---|---|---|
| CONTROL | `fold_coherence_20261012/CURVED/SPAN/G02` | G3 | Existing CC component, tag mask; no new return or field |
| RETURN | Same CURVED G2 | G3 | Two authored broad counter-swept meso events, then same CC recipe with resulting feature tags; no field |
| ANCHOR | `directional_growth_20261012/OVERLAP/G02` | G3, G4 | Existing CC component and tags; zero new authored events or field passes |

CONTROL versus RETURN includes both the added events and their resulting tag/CC response. It is not an isolated displacement-only ablation. ANCHOR versus CONTROL is a different-input design comparison, not a controlled single-variable experiment. The original OVERLAP G2 front image is the exact saved render identified from the supplied column image; it was not reconstructed from appearance.

## Source OVERLAP G2: existing creation path

Original code: [`overlap_probe.py`](../../experiments/directional_growth_20261012/overlap_probe.py). Parent: `E:/CHESHIRE_DATA/fold_band_growth_20261011/ANCESTRY_STAGED/G01`.

1. Apply two overlapping authored PCHIP radial/axial return events to the existing G1 controls, with constructive reflected vectors. Lower event: direction `.35`, height `.39`, span `.12`, expansion `.48`, constriction `.28`, reexpansion `.38`, return depth `.72`, overlap width `.46`, sweep `.28`. Upper: direction `1.18`, height `.61`, span `.12`, expansion `.46`, constriction `.26`, reexpansion `.36`, return depth `.68`, width `.46`, sweep `.28`.
2. Existing coupled Task36: averaging `0`, stencil/normal `1`, vertex memory `1`; face/edge gain `.65/.18`, feedback `1`, inherited bias `.8`, diagonal/edge/vertex tension `-.65/.5/-.8`, ancestry gain `1`, cap `plane_only`, physical surface `mean`.
3. Existing finite Mandelbulb nearest-outside mapping: powers `[4,4]`, centres `[2.5,7.5]`, axial scale `2.8`, radial scales `[1.6,1.6]`, Z orientation, polar convention, 8 escape iterations, movement fraction `.55`, budget `.28`, local target factor `2`.

G2's total history is two subdivision passes, two field applications and two authored return events. Eight classifier iterations are not eight mesh folds. Authored returns are not fractal-emergent folds. The public source generation receipt is preserved with the small input asset.

## New adapter

Code: [`study.py`](../../experiments/fold_return_20261012/study.py), importing existing `fold_coherence`, `fold_transfer`, profile, memory and Task36 implementations. The source quad chart/state is loaded without rebuilding the mesh. OVERLAP G2 uses its original `mean` surface; the new output uses native `vf`. The existing inactive interpolating refinement uses the input face means and preserves the original mean-fan geometry in the refined VF representation. The representation change is not a separate deformation; the new shape change is the tag-weighted CC displacement relative to that inactive reference. Input and output do not have identical triangle arrays. G3 and G4 both use `vf`.

An inactive interpolating split provides the matched topology and reference coordinates. The active existing Task36 result uses averaging gain `.65`, vertex memory `.25`, stencil/normal gain `0`. The difference from the inactive result is weighted by `1-tags` and constructively reflected in X/Y. This is geometric CC placement, not smooth shading; there is no separate geometric smoothing pass. The inherited coupled recipe's other values remain recorded in each receipt, rather than being silently replaced.

RETURN G3 derives two events from the two CURVED source parents. Height shifts are `+.20/- .20` times parent span; angular shifts are `+.25/- .25` times parent overlap width. Each event has span `.085`, expansion `.10`, constriction `.23`, reexpansion `.20`, return depth `.50`, width `.52`, sweep `-.24`, bend height `.035`, sweep span `.26`. Their deformation is masked against inherited tags; newly affected profile tags are registered before CC. Result: side pockets and an extra cuff, not a compelling connected meso hierarchy. No G4 was generated for this variant.

ANCHOR adds no event. Its two source events and two source field applications remain inherited at both G3 and G4. `field_enabled=false` and `added_field_passes=0` describe the **new stage**, not a field-free origin. No field cache is needed to run this continuation. The saved operation arrays separate raw/applied return, inactive reference, raw/applied CC placement and carried tags.

At ANCHOR G3, 60 inherited exact-core controls have zero total movement in that stage; at G4, 286 inherited exact-core controls have zero total movement in that stage. This does not lock all old controls, complete cavity walls or fold angles. Rounding can still weaken a lip. The new G4 output has 1,190 exact tag-core controls. These counts are technical memory checks, not proof of aesthetic success.

## Actual geometry and quick validation

| Output | Physical vertices / triangles | Max X/Y reflection error | Minimum triangle area | Closed / components / winding |
|---|---:|---:|---:|---|
| CONTROL G3 | 51,202 / 102,400 | 3.73e-15 | 1.62e-5 | Yes / 1 / consistent |
| RETURN G3 | 51,202 / 102,400 | 3.81e-15 | 2.41e-5 | Yes / 1 / consistent |
| ANCHOR G3 | 51,202 / 102,400 | 3.73e-15 | 2.33e-6 | Yes / 1 / consistent |
| ANCHOR G4 | 204,802 / 409,600 | 3.81e-15 | 3.94e-7 | Yes / 1 / consistent |

All four have finite coordinates and identical reflected triangle sets. Existing thresholds were retained: area `>1e-12`, reflection error `<1e-9`. Full receipts: [generation_records.json](technical/generation_records.json). No unrelated regression suite, repeated full reproduction or broad historical hash audit was run.

The original OVERLAP G2 has **confirmed self-intersections** in its [previous core record](../directional_growth_20261012/technical/OVERLAP_G02_core.json). The current four outputs have **not been checked for self-intersection**, by the user's exploration priority. No repair or intersection reduction is claimed. Earlier FLOW intersections are documented separately and are not measurements of these meshes. Thickness, minimum feature size, strength, physical dimensions, supports and FDM fabrication remain unverified.

## Rendering and review

[`render.py`](../../experiments/fold_return_20261012/render.py) uses saved `geometry.npz` triangles, Blender 4.5.4, Cycles, the existing uniform mineral material and flat geometric normals. No render subdivision, smoothing modifier, bump/normal maps, added shells or AI-generated geometry. Whole images are 800 square / 16 samples; detail images 1000 square / 32 samples.

| View | Camera | Target | Orthographic span |
|---|---|---|---:|
| front | `(0,32,5)` | `(0,0,5)` | 12 |
| oblique | `(-18,28,16)` | `(0,0,5)` | 12 |
| side | `(-32,0,5)` | `(0,0,5)` | 12 |
| front_meso | `(0,32,2.8)` | `(0,0,2.8)` | 4 |
| side_meso | `(-32,0,5)` | `(0,0,5)` | 4 |
| front_upper | `(0,32,6.1)` | `(0,0,6.1)` | 4 |
| side_upper | `(-32,0,6.1)` | `(0,0,6.1)` | 4 |

Original G2 whole views were reused; near views were newly rendered from the preserved original geometry into separate reference folders. [`boards.py`](../../experiments/fold_return_20261012/boards.py) only arranges saved renders with labels. All four boards and the underlying G4 views were visually reviewed; no missing panels or identified label clipping. Independent review agrees that the G4 walls read more continuously while the side shelf repetition and short jagged branches remain. This is a visual assessment, not a curvature or groove-depth measurement.

## Reference facts versus interpretation

[IAAC's public page](https://www.iaacblog.com/programs/mesh-subdivision/) combines subdivision and Mandelbrot-based spatial tests, and shows multiple volume/attractor and parameter variations. Its public pseudocode does not supply the complete executable implementation and weights. The inspected catalogue titled “MANDELBROT ATTRACTORS + 1 LEVEL SUBDIVISION” shows alternatives, not five successive generations. We do not claim exact IAAC reproduction or infer a generation schedule from those five columns.

[Hansmeyer's Subdivided Columns description](https://michael-hansmeyer.com/subdivided-columns.html) discusses one process across scales and parameter variation in tagged input parts. In the official close-up we inspected, sharp facets coexist with changing scale/direction along deep grooves and shoulders. The latter is our visual interpretation, not a recovered equation. The useful target is related local formations, not merely smoothing every facet or increasing polygon count.

Neither reference proves that the current CC-only continuation solves multi-scale growth. No reference image or provided private document is republished in this review package; locally downloaded reference images remain under the E output root.

## Files, portable continuation and limits

Large output root: `E:/CHESHIRE_DATA/fold_return_20261012`. Each candidate has authoritative `geometry.npz`, exported `column.ply`, quad continuation state, operation arrays, recipe/code snapshots and actual renders. Reference renders are in `REFERENCE_G02` and `REFERENCE_ANCHOR_G02`. All earlier outputs remain intact.

Small public assets: original OVERLAP G2 `control_quad.npz` + `generation.json`, and final ANCHOR G4 `geometry.npz` + `generation.json`, approximately 4.52 MB combined. [MANIFEST](MANIFEST.json) records their paths, source paths and SHA256 hashes, computed only for these selected assets. The final geometry contains float64 `xyz` and triangle `faces`; it is an actual 3D mesh, not a preview proxy. Full G4 continuation state and PLY remain on E. The original quad input is a control state: arbitrary diagonal triangulation would not reproduce its native mean-fan physical surface.

From the repository root with the existing Python dependencies available:

```powershell
python -B experiments/fold_return_20261012/study.py --variant ANCHOR --stage 3 --source-g2 docs/fold_return_20261012/review_assets/OVERLAP_G02 --root output/fold_return_review
python -B experiments/fold_return_20261012/study.py --variant ANCHOR --stage 4 --root output/fold_return_review
```

These are sequential one-stage calls. Existing result directories are refused. G4 inherits the saved G3 origin; a conflicting `--source-g2` is rejected. The packaged input has every field required by the existing loader; missing optional `surface`/`memory` are the original format and correctly default to `mean`/zero before authored tag registration. This is a continuation of the documented chart/topology, not an arbitrary-mesh API or a standalone two-file program. It requires the reused modules in this repository. The packaged input supports ANCHOR, not the different CURVED input used by CONTROL/RETURN; those source files remain on E. The final triangle mesh alone is for inspection and cannot resume growth without quad control state.

The actual four generations were run in the recorded local environment. The later portable path options were reviewed and `--help` checked; a fresh-environment reproduction was **not** rerun. Python/package versions are in the manifest. Blender is needed only for rendering. The current board adapter expects the saved rendered folder layout; the small public package does not include every individual render or historical checkpoint needed to rebuild all boards.

### Remaining implementation targets

1. Develop connected groove/shoulder regions rather than independently offsetting every tiny face; retain direction and parent-fold relationships across the region. This is a proposed next experiment, not implemented here.
2. Compare a field used for coherent region/direction selection, then test the selected rule on another initial form with the same documented chart. Earlier two-input transfer exists in [fold_transfer](../fold_transfer_20261012/REPORT.md), but it does not certify this new recipe or free-topology inputs. Gate transfer remains a hypothesis; no gate trial was run.

This bounded study ends after ANCHOR G4. G5/G6 refinement alone is not justified as a solution to the remaining hierarchy problem.
