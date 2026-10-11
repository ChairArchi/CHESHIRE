# Directional meso growth — 2026-10-12

Separate branch: `experiment/directional-growth-20261012`.
Output: `E:/CHESHIRE_DATA/directional_growth_20261012`.
Review: `docs/directional_growth_20261012/REPORT.md`.

Preserved input is actual `fold_band_growth_20261011/ANCESTRY_STAGED/G01`.
No original source/operator/checkpoint is overwritten. This study uses existing
Task36 placement, nearest-outside finite field, PCHIP radial/axial return, guide
distance and reflected displacement helpers. It is not an origami solver or
an original IAAC executable-code reproduction.

- CORRIDOR: one G2 cycle, new placement and field vectors only in two compact
  legacy-surface corridors; fixed narrow guide cores attenuate movement.
  No automatically detected crease or durable crease-angle memory claim.
- OVERLAP: two narrow-angular, axially overlapping PCHIP events on G1 controls
  BEFORE G2 Task36 and field. G3 continues the actual G2 once; no new return.
- FACE_RESPONSE / SIGNED_RESPONSE: same actual OVERLAP G2 and same G3 field;
  only existing Task36 `normal_response` changes to `face_geometry` or
  `all_geometry`. Direct vertex-normal gain stays zero. Old Task36 vertices
  are retained by vertex_memory=1, but subsequent field may move them.

Task36 standard CC averaging gain remains zero; weighted stencils still
combine coordinates. No separate XYZ smoothing, cap redesign, random noise,
image synthesis, or new general engine. Mean render fan centres do not become
next-generation controls; holding old controls is not a proof that a refined
nonplanar physical surface stays unchanged.

## Commands from this worktree

```powershell
python -B experiments/directional_growth_20261012/corridor_probe.py --stage 2
python -B experiments/directional_growth_20261012/overlap_probe.py --stage 2
python -B experiments/directional_growth_20261012/overlap_probe.py --stage 3
python -B experiments/directional_growth_20261012/response_probe.py --response face_geometry
python -B experiments/directional_growth_20261012/response_probe.py --response all_geometry
python -B experiments/iaac_mandelbrot_20261011/batch_render.py --root E:/CHESHIRE_DATA/directional_growth_20261012 --folders CORRIDOR/G02 OVERLAP/G02 OVERLAP/G03 FACE_RESPONSE/G03 SIGNED_RESPONSE/G03 --workers 1
python -B experiments/directional_growth_20261012/review.py --compare CORRIDOR/G02 OVERLAP/G02 --progression CORRIDOR OVERLAP
python -B experiments/directional_growth_20261012/review.py --compare OVERLAP/G02 OVERLAP/G03 --baseline-stage G03 --board-name final_comparison
python -B experiments/directional_growth_20261012/review.py --compare FACE_RESPONSE/G03 SIGNED_RESPONSE/G03 --baseline-root E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP --baseline-stage G03 --baseline-label 'Uniform normal sign' --board-name response_comparison
python -B experiments/directional_growth_20261012/finalize.py
```

Existing candidates refuse overwriting (some permit exact-signature reuse).
`review.py --validate OVERLAP/G02 OVERLAP/G03` is explicit core checking,
not a required repeat: both saved checks already exist. It reuses saved checks.
Intersections are confirmed, not repaired. Other variants have only quick
checks; no full regressions, exhaustive intersection count or hash audit.

The first-growth input already has authored large folds. THREE growth cycles
and the internal classifier schedule 4/8/18 are different counts; neither is
a count of physical origami folds.
