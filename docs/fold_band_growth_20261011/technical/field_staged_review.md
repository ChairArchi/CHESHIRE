# Finite field-detail staging: FIELD_STAGED

## Implemented comparison

Same actual SPAN_SPARSE G00, n4 powers [4,4], centres [2.5,7.5], scale 1.6, axial 2.8, nearest-outside fraction .55, field budgets .35/.28/.22, target refinement factors 1/2/3, one bilinear quad split per growth cycle. Existing full_loop.full_cycle is called with role_depth=0; no role displacement occurs. No added return folds, XYZ smoothing, cap lock, legacy mask or random noise.

Only the finite classifier's internal escape-iteration schedule changes: FIELD_SEED uses 18,18,18; FIELD_STAGED uses 4,8,18. These are THREE actual growth cycles in both cases, not 4/8/18 folding generations. Each stage uses a separately matching outside grid bank: F02(iter4), F03(iter8), F01(iter18). The cache key and stored parameters are checked. No wrong-iteration outside grid is reused.

This is our declared hypothesis, not an IAAC disclosed schedule. Lower finite escape iterations change the occupancy volume and target surface; this is NOT a mathematically exact frequency filter that keeps the same macro field. It can therefore change initial mass as well as detail timing.

## Actual three-view result

G1 staged movement covers a visibly broader crown/body/cup area, rather than only creating local crust. It also creates broad faceted inflation. At G2/G3 the front upper/lower hollows develop more nested relief and the side recess rims remain less granular than the fixed18 control. The original two-body/cup/waist rhythm is still recognizable and largely unchanged. Broad facets at the waist and ends remain; no new macro node or independent folding logic has emerged.

G3 staged looks calmer and more legible in several broad regions, but the fixed18 control's dark lower puncture-like hole becomes a shallower-looking nested opening. This is not an across-the-board increase of deep grooves. G2 to G3 adds limited local relief; it is not a dramatic architectural development.

The operation is worth retaining as a PARTIAL detail-timing / field-path asset. It does not by itself solve the macro/meso hierarchy bottleneck or complete IAAC reproduction. No further branches were run.

## Actual measured path difference

Field-inside fractions: staged .77154 -> .37848 -> .20041; fixed18 .52247 -> .49656 -> .46821. Broader first-stage movement leaves fewer later inside samples eligible for attraction. Both finish with the SAME 18-iteration classifier, but the final control positions remain different (RMS .1254 model units, mean .09265; 21083/25602 vertices differ by >1e-9). The control connectivity and material charts are identical at each stage. These measurements show path dependence, not an explicit crease-memory implementation.

Physical sizes match the control: G1 3202 V / 6400 T; G2 12802 V / 25600 T; G3 51202 V / 102400 T.

## Minimal checks and limits

G3 single connected, watertight and winding consistent. Actual X/Y reflection and reflected triangle sets pass the existing checks. Minimum triangle area remains above the unchanged 1e-12 threshold. Self-intersection NOT CHECKED for this experimental comparison; thickness, structural behaviour and fabrication NOT CHECKED. No intersection repair was attempted.

Actual comparisons: review/field_staged_G01_comparison.png, field_staged_G02_comparison.png, field_staged_G03_comparison.png
Actual measured differences: review/field_staged_comparison_metrics.json
Actual meshes/checkpoints/operation fields: FIELD_STAGED/G01, G02, G03
Small wrapper: experiments/fold_band_growth_20261011/field_lod_probe.py

G3 reflection errors: [3.636721891222372e-15, 3.614624287906422e-15]; minimum triangle area: 2.9705663863996905e-06.
