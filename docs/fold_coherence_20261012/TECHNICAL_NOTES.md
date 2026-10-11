# Fold coherence — implementation record

## Scope and lineage

- Parent commit: `d57e679`; isolated branch: `experiment/fold-coherence-20261012`.
- SPAN source: `E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G02`.
- COUNTER source: `E:/CHESHIRE_DATA/fold_transfer_20261012/COUNTER/G02`.
- Both are actual saved G2 controls, not post-deformed copies of one final mesh. They share the existing 25-ring/16-sector material chart and height 10. This is a two-input transfer study, not arbitrary-mesh generalization.
- Outputs: `E:/CHESHIRE_DATA/fold_coherence_20261012/{RESERVE,FLOW}/{SPAN,COUNTER}/Gxx`.
- All prior sources, code and checkpoints remain in place. No original operator was edited.

## Two bounded compositions

RESERVE stops at G3: lower existing Task36 stencil and normal components, preserve the existing mean-fan surface through the VF split, and apply the finite field with authored-tag protection. It has no new authored return event. The generic `operation` string in its generation record mentions continuous returns; the authoritative `new_authored_events=[]` distinguishes it from FLOW.

FLOW uses the same placement/field policy and adds two continuous PCHIP return events before each split. Child direction, height, span, radial amplitude and return depth derive from the preceding authored pair. Existing `.05` angular height bend and `.32` sweep wavelength scale with the child span. This is a finite composition of existing geometry operators, not a new folding solver.

| Stage | Task36 stencil / normal gain | Field movement budget | Field target factor |
|---|---|---|---|
| G3 | .25 / .25 | .22 | 3 |
| G4 | .18 / .15 | .14 | 2 |
| G5 | .10 / .08 | .10 | 2 |

Task36 averaging gain stays zero. No additional XYZ smoothing, remeshing, image-generated detail, displacement texture or render subdivision modifier is applied. Reduced cell components do not remove all cell-scale placement: FLOW/SPAN G3 still moves 72.7% of outgoing controls in that step.

The field is the existing finite power-4 spherical Mandelbulb reconstruction, with 18 escape iterations per query and fraction .55. It is not a recovered IAAC equation. Each new G3/G4/G5 has one actual split and one field pass. Including its two source passes, new FLOW G5 therefore has five subdivision passes and five field applications. The escape-iteration count is a different quantity. Prior TAG_ONLY G5 had five subdivisions but four field applications.

## Memory and comparison limits

Both inputs receive the same fresh registration of the two original macro-profile tags at G2. Subsequent profile-tag widths scale with event span. Applied placement and field displacement use `1-tags`; the field may move untagged old controls as well as new ones. There is no blanket old-control field pin.

Tags protect authored ridge/valley trajectories. Exact tag-core samples remain fixed during placement and field steps. This does not prove that every intervening fold angle or entire band is preserved. No mechanical origami constraints, isometry, automatic crease extraction or dihedral-angle memory is implemented.

FLOW/SPAN G3 received nonzero return displacement at 1,804 of 6,402 incoming controls, with maximum .42844. Maximum placement was .04678 and field movement .22. The 422 exact outgoing tag-core controls had zero placement and zero field movement. Strong incoming return samples retained their return-direction displacement through the field step. These are operation observations, not aesthetic success metrics.

RESERVE vs FLOW is a matched-source design comparison, not a pure additive-return ablation: FLOW's new geometry and tags also change the subsequent field query and its permitted movement. Old TAG_ONLY G5 vs new FLOW G5 changes the lineage, returns, placement gains and field-pass count. Do not attribute the final difference to one isolated parameter.

## Rendering and core checks

Whole views reuse the established cameras, uniform mineral material and flat geometric normals: front `(0,32,5)`, oblique `(-18,28,16)`, side `(-32,0,5)`, target `(0,0,5)`, orthographic scale 12, 800 square, Cycles 16 samples. Meso views reuse the saved front z=2.8 and side z=5.0 cameras, orthographic scale 4, 1000 square, Cycles 32 samples. Boards resize entire actual renders and add labels only.

Intermediate stages use the original quick finite/reflection/area/connected/closed/winding checks. Only the two new FLOW G5 meshes receive the existing core checker, once: float64 `geometry.npz`, geometric and triangle-set X/Y reflection, edge incidence, face connectivity, winding, area threshold `1e-12`, and CGAL `detect_only=True, first_only=True` self-intersection query. Positive pairs are witnesses, not exhaustive counts or comparable intersection totals. Nothing is repaired or hidden.

Thickness, loads, material, structural stability and fabrication remain unverified. The original coarse cap fans are retained. This initial RESERVE/FLOW phase generates no gate mesh or G6. The subsequent close-view development is recorded separately in [NEAR_VIEW_REPORT](NEAR_VIEW_REPORT.md) and [DEVELOPMENT_NOTES](DEVELOPMENT_NOTES.md).

Actual saved-stage receipts: [generation summary](technical/generation_summary.json). Final core records: [core validation](technical/core_validation.json). Asset paths: [INDEX](INDEX.json).
