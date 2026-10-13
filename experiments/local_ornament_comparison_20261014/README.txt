LOCAL ORNAMENT COMPARISON / 2026-10-14

Authorization: the user requested immediate trials after the separate technical
comparison. This supersedes the research-only stopping point for this new trial.

Original body: WIDE_ROOT_FINISHED / SPAN / G07, unchanged.
Heavy data: E:/CHESHIRE_DATA/experiments/local_ornament_comparison_20261014/trial01

Two actual additions, one common placement recipe:
A: finite power-8 Mandelbulb, 10 iterations, continuous escape-count isolevel9.5,
   193^3 sampling, largest closed connected component, no smoothing.
B: three authored closed lanceolate leaves, central rib and small tip turns.

Six canonical original-surface anchors in the user-marked diagonal band, each
reflected into four X/Y orbits. Equal maximum root-relative footprint and normal
height. An actual interior point at prototype z=.22 is placed on each original
surface vertex; this verifies local overlap without claiming a Boolean union.
The saved original selection and normals are reused from volume_junction_target
PREPARATION only. No rejected volumetric candidate geometry is used.

These are independent ornament meshes, not G8, source topology subdivision,
source geometry smoothing, fabrication-ready fusion or a new universal operator.
Matching bounding envelopes do not equalize occupied volume or perceptual density.

Commands (use a new E output root to preserve the recorded trial):
  python mandel_prototype.py --root NEW_ROOT
  python leaf_prototype.py --root NEW_ROOT
  python run.py --root NEW_ROOT
  blender --background --python render.py -- --root NEW_ROOT
  python boards.py --root NEW_ROOT

Run from this folder or supply script paths. Use the existing CHESHIRE venv.
scikit-image0.26.0 and lazy_loader0.6 are task-owned on E in
E:/CHESHIRE_DATA/python_packages/local_ornament_20261014 (not installed on C).
Set TEMP and TMP to E:/CHESHIRE_DATA/tmp for Blender and package operations.

Prototype integrity is checked at creation. Assembly checks actual source hashes,
source-point identity, actual interior parity, positive triangle area and exact
constructed mirror correspondence. Matched rendering loads the original body
once, retains its mesh pointer, and rehashes actual Blender body arrays after
each candidate. Source views are reused under the same camera/material conditions.
No additional whole-column topology replay or parameter sweep is required.

See docs/local_ornament_comparison_20261014 for actual saved receipts, comparisons
and the bounded visual assessment. Trial status is determined there after renders.
