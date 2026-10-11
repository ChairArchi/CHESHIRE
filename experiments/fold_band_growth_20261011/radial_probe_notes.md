# Radial sparse probe — stopped at G2

Actual outputs: `E:/CHESHIRE_DATA/fold_band_growth_20261011/RADIAL_SPARSE`.
Same `inputs/SPAN_SPARSE/G00` as FIELD_SEED and FULL_LOOP; no new input design.

## Implemented

`radial_probe.py` imports the preserved terminal-fold `iaac_repeat.py` without
editing it. Only the radial recipe powers change from [5,6] to [4,4]. Thus
centres [2.5,7.5], axial 2.8, scales [1.6,1.6], 18 finite escape iterations
and .35/.28/.22 maximum step budgets match FIELD_SEED. Each generation makes
one bilinear quad split, reclassifies all old/new control points, and moves
inside points away from the XY column axis and outside points toward it.
Z is unchanged by this field movement. The signed coefficient is the existing
.22; FIELD_SEED uses .55 times its nearest-outside target vector. This compares
two reconstructed response laws, not isolated equal-amplitude effects.
No geometric smoothing, role offsets, added return events, cap locks or repair.
The interpretation of centre and numeric coefficient are not disclosed IAAC
original source. The process corresponds to its separate radial public flow,
not the nearest-outside flow used in FIELD_SEED.

## Actual results

| Stage | Physical vertices / triangles | Control quads | Maximum step | Minimum triangle area |
|---|---:|---:|---:|---:|
| G1 | 3,202 / 6,400 | 1,600 | .348615 | 4.61183e-4 |
| G2 | 12,802 / 25,600 | 6,400 | .280000 | 6.12496e-5 |

All front/oblique/side PNGs are saved in each stage's `preview` folder; the
Blender scene is each stage's `column.blend`. The actual saved mesh passed finite-coordinate, watertight,
winding and X/Y reflected-triangle checks performed by the reused generator.
G2 maximum reflection error is 3.627e-15. Component count and self-intersection
were not separately checked because the candidate visibly failed; thickness,
structure and fabrication remain unverified.

## Visual evaluation and stop decision

G1 already changes the broad returns into polygonal terraces. G2 moves the
silhouette more than nearest-outside FIELD_SEED/G2, but sawtooth edges and
sharp ribbon-like fragments dominate the shoulders, neck and ends in all
three views. Broad cup surfaces remain comparatively plain: large faces and
rough boundaries coexist without persuasive multi-scale folded continuity.
This is a failed direction for the current fold objective, not a technical
run failure. G3 was deliberately not generated.

The hard inside/outside sign sends adjacent samples to opposite radial
directions at classifier boundaries; this discontinuity is a plausible
mechanism for the serration. It is an interpretation from the implemented
equation and actual images, not a proved reconstruction of IAAC's original
artefacts. No claim of physical folding or IAAC aesthetic reproduction.
