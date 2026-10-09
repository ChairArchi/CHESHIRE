# Illustration 1: three controlled CC runs

This is a capability test, not reconstruction of the unpublished original
parameters or a fit to the illustration's silhouette. Exactly one modified
w1-w4 schedule is tested, with/without independent w12; the third control is
standard CC. All inputs are the identical undecorated cube [-1,1]^3.

From the worktree root, using Python with NumPy and Pillow:

```powershell
python experiments/illustration1/run.py generate
python experiments/illustration1/run.py render
```

Recorded interpreter: `C:/Users/USER/CHESHIRE/.venv/Scripts/python.exe`.
Output: `output/illustration1/`. Generation refuses to overwrite a completed
run. To reproduce without altering saved evidence, use a separate checkout
of this branch with only this experiment's output directory absent.

## What is fixed

- The existing `src/subdivision.py:cc` implements Eqs.1-4 unchanged. Its only
  addition is an optional weight-provider argument; default behavior remains
  the old G0-G3 checkpoint behavior. No second engine is introduced.
- `recipe.json` contains every numerical weight for G1-G8.
- One uniform row is returned for every face, edge and vertex of a generation.
  No position-dependent weights, face groups, locks, random values, DS or fusing.
- Standard: all weights zero. Weights only: scheduled w1-w4, w10=w11=w12=0.
  Vertex-normal control: identical w1-w4, w10=w11=0, independently scheduled w12.
- The original normal convention is preserved and explicitly recorded in the
  recipe. Uniform weights do not mean equal displacements: incident normals
  and perimeters depend on actual geometry. No radial replacement of normals.

## Why these own values are permitted

Hansmeyer 2010 pp.76-77 specifies affine masks and iteration-dependent values,
without a numerical admissible interval or a convexity restriction. Figure 6
also examines w1 near 3, outside a convex interpolation interval. Negative
mask coefficients are therefore relevant to this limited capability test.
No claim of numerical stability follows from permission to extrapolate.

The fixed schedule alternates extrapolating masks instead of returning every
generation to positive averaging. The exact w1=3 coincidence is avoided. w12
is independently selected, not derived from w1-w4. These are test choices,
not original Illustration 1 settings. No tuning after seeing G8 is intended.

## Evidence and minimum checks

- NPZ meshes for every G0-G8, retaining coordinates, faces and CC corner types.
- OBJ meshes and same-camera PNGs for G0/G2/G4/G6/G8.
- `generation_results.json`: counts, actual bounds, face-normal angles and
  same-connectivity vertex displacements from standard CC.
- `camera.json`: one camera, light, center and absolute scale for the full board.
  The optional center detail images explicitly use a common 2x magnification.
- Checks: affine mask sums; known standard G1 cube corner; the G1 vertex-only
  displacement formula; zero G1 change in face/edge points when only w12 differs;
  finite coordinates/nonzero polygon normals, closed oriented edges, Euler 2,
  expected CC counts and identical connectivity between controls.

These checks do not establish absence of self-intersections, positive enclosed
volume or printability. No mesh repair, smoothing or density-based success claim.
No previous regression suite is run. Stop for user review after the results.
