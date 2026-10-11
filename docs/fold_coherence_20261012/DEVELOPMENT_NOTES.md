# Close-view development: actual operations and comparison limits

This continues the preserved RESERVE/FLOW phase after the close-view critique. All new geometry is under `E:/CHESHIRE_DATA/fold_coherence_20261012`; original operators, inputs and candidates remain in place. No gate application, physical origami solver, implicit-fractal mesher or new topology engine was implemented.

## Operation diagnosis

`snapshot_probe.py` materializes the existing SPAN G2 arrays `interpolated_authored_xyz`, `post_task36_xyz` and `post_field_xyz` with the same control faces and mean-fan physical surface. The last array matches the saved actual G2. The interpolation slice is not an exact resampling claim for the incoming nonplanar surface. All slices retain G1's earlier field response. The Task36 slice adds short shelves; the field subsequently strengthens some cavities and adds angular variation. These observations do not isolate the stencil and normal components individually.

`field_slice.py --stage 4` materializes the saved CURVED G4 `pre_field_xyz`. Its topology, native VF surface and camera conditions match the final G4; only that stage's final field displacement differs. It still contains G3's field response. The extra fine facets in the after image can therefore be attributed to this G4 field operation. This is a local finding about the current mapping and recipe, not a proof that Mandelbulb fields are inherently noisy or unusable.

## Late activation and existing CC comparison

| Recipe | G1 / G2 | G3 onward | Status |
|---|---|---|---|
| LATE | Inactive surface-preserving split; original two returns before G2 split; no field | Derived returns, reduced Task36 placement, capped field | G1-G5 retained; long grooves improve, coarse facets and fine grain remain |
| CURVED | Existing CC component .7, vertex memory .2; original returns tagged before G2 placement; no field | Same LATE returns/field plus existing CC component | G1-G4 retained; G4 field grain stops this recurrence |
| RULED | Actual CURVED G2 source | One fixed existing Task36 kernel, no new authored return and no field displacement | Bounded G3-G6 comparison |

LATE stencil/normal gains at G3/G4/G5/G6 are `.15/.08`, `.10/.05`, `.08/.04`, `.06/.03`; its averaging gain is zero and vertex memory one. CURVED uses those same gains, averaging `.35` / vertex memory `.6` at G3, and averaging `.2` / vertex memory `.75` afterward. Both apply tag protection to the complete active-minus-inactive displacement before constructive reflection.

The late field classifier has 8 escape iterations at G3 and 18 afterward. Raw movement uses existing fraction `.55`, target factor 2 and absolute budgets `.14/.10/.07/.05`. After `1-tags`, its magnitude is additionally limited to `.25` times the mean length of incident control edges on the actual pre-field geometry. This averages scalar lengths, not vertex coordinates. There is no separate geometric smoothing pass.

CURVED enables the existing CC averaging component inside Task36. It is a geometry change, not smooth shading. Exact authored tag cores remain fixed during placement; surrounding walls and fold angles are not mechanically locked. Rounding therefore can still weaken a lip or alter a cavity. The LATE receipts' generic `composition_recipe` was inherited from the earlier helper; their explicit `late_activation_recipe` and scope define the actual schedule. Original receipts remain unchanged. CURVED stores its actual recipe in both named and generic fields.

## Repeated kernel control

RULED starts from actual CURVED/SPAN/G02, which has two authored macro returns and zero field passes. At every subsequent split it repeats the existing coupled Task36 kernel with averaging `.8`, stencil `.35`, normal `.75`, vertex memory `.35`, existing support-radius scaling and existing ancestry controls. It adds no new authored child return, random noise, field displacement, shell or topology replacement. Placement is weighted by `1-tags` and reflected in X/Y. The same kernel receives its preceding actual geometry as input.

RULED versus CURVED is a **design comparison with several changed settings**, not a one-variable field ablation. RULED demonstrates a more regular curved cell pattern, but repetition and increasing mesh density do not establish macro/meso/micro ornamental hierarchy. The latest G6 control was tested only on SPAN. The earlier two-input FLOW results do not certify transfer of this new recipe to arbitrary inputs.

G labels count subdivision passes. RULED G6 has six subdivision passes, two authored macro-return events inherited from G2 and zero fractal-field passes. CURVED G4 has four subdivision passes and two field passes. Escape iterations inside one classifier evaluation are a separate count. None of these counts is a physical folding count.

## Validation and rendering

Each saved generation reuses the quick finite/connected/closed/winding/triangle-area/X-Y-reflection checks, with unchanged area threshold `1e-12` and reflection tolerance `1e-9`. The rendered physical triangles are authoritative; the quad state is the next generation's control state. Subsequent LATE/CURVED/RULED self-intersections remain **unverified** by user direction. The earlier FLOW G5 pair has confirmed intersections in its separate core records; that result is not transferred to a different mesh.

Whole views are the same three 800-square cameras used in the initial phase. Fixed 1000-square meso views have orthographic scale 4; micro views scale 1.2. Uniform mineral material, actual flat geometric normals, no render subdivision modifier, bump/normal map or image-generated detail. Boards only resize complete renders and add labels.

A possible future stool-scale FDM capital fragment motivates close-view evaluation. No physical scale, cut location, minimum feature thickness, supports, strength, watertight union after intersection repair or printable model was established. High triangle count alone says nothing about printable detail.

## References retained separately

[RESEARCH_NOTE](RESEARCH_NOTE.md) distinguishes published source facts from our inference. [MIRROR_NOTE](MIRROR_NOTE.md) reviews the provided Bader/Oxman paper: recursive cutting/reflection/Boolean joining precedes final CC; this is not the current surface-displacement method. No mirror engine was implemented.

Existing Tissue component mapping and `frame_strips` are separate network/shell routes. Existing `ornament.topology_event` can replace a selected parent disk with an inset frame and tapered cap while preserving its boundary; it does not itself change genus. These are potential assets, not operations used in this development. No Tissue, DS, extrusion or topology-changing result is claimed here.

The ornament operator runs independently on each selected face, not on one merged multi-face patch. Its connected vocabulary option coordinates directions but does not stitch caps. TaperedExtrusion accepts positive height, so this asset cannot be presented as an existing inward-return or multi-face cavity solution. Adding it across the small G6 cells would repeat the texture problem; no such trial was run.
