FINE DIAGONAL FACET FINISH / 2026-10-14

USER DIRECTION
The user explicitly selected the small diagonal comb/scale pattern in the
saved REVISED FLAT macro, rather than its larger descending return shape.
Original WIDE_ROOT_FINISHED remains the separate design baseline.
This trial does not adopt every changed end of the prior source-rule study.

ONE TRIAL
measure.py measures the actual saved source and constructs one deterministic
fine anisotropic warped-cell mask with actual face-pair symmetry. Thresholds
and global/macro distributions are recorded in MEASUREMENT.json on E.
run.py changes only existing native quad-center vertices: a small normal lift
and shorter-width bias toward one long edge. Controls/edges/native indices are
unchanged. An orbit-wide safety rejection keeps positive projected fan areas
and positive old/new triangle normal dot products in the changed cells.

This is an explicit native finish of G7, not G8 or another control subdivision.
The finished native centers are not arithmetic control-quad centers; their
actual displacements and geometry are saved. A future control subdivision
does not automatically preserve this finish. No global collision or fabrication
certificate is claimed. No Mandelbulb, ornaments, Boolean or remesh is added.

SHADING COMPARISON
Source/candidate reuse the EXACT source-derived flat_quads mask. Selected fine
cells use flat triangle shading; other cells use normal interpolation. This
separates coarse faceting from the user-selected fine facet language. Geometry
change must be assessed within that same shading condition, not against the
previous all-flat or all-smooth render.

FILES
E:/CHESHIRE_DATA/experiments/diagonal_facet_finish_20261014/trial01
MASK.npz; MEASUREMENT.json; ACCENT/geometry.npz;
ACCENT/native_center_delta.npz; RECEIPT.json; rendered receipts and comparisons.
Original source data and prior preserved experiments remain read-only.

EXECUTION
python measure.py --help
python run.py --root NEW_E_ROOT
blender --background --python render.py -- --phase source_only --root NEW_E_ROOT
blender --background --python render.py -- --phase candidate_only --root NEW_E_ROOT
python boards.py --root NEW_E_ROOT
Use the existing venv/Blender4.5.4; TEMP/TMP on E. Never overwrite a candidate.

DEFERRED USER SUGGESTION (NOT AUTHORIZED FOR EXPERIMENT)
The user proposed covering only very small awkward overlapping ornaments with
flower-like Mandelbulb micro-clusters, treating the region as one local cluster.
They explicitly asked not to experiment with it now. Record only; do not launch
that experiment. Continue only the already-running diagonal-facet comparison.
