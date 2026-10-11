# Directional Fold Memory — finite A/B study

Read ../../docs/directional_fold_memory_20261011/REPORT.md for results and limits.
Output root: E:/CHESHIRE_DATA/directional_fold_memory_20261011.
Source baseline: c373e32; existing CHESHIRE operators are unchanged.

Run in an empty artifact root (saved checkpoints are never overwritten):

    python experiments/directional_fold_memory_20261011/study.py --phase A --root <empty-root>
    python experiments/directional_fold_memory_20261011/study.py --phase B --root <same-root> --source A_FOLD/G03

Render using the unchanged iaac_mandelbrot_20261011/batch_render.py, with
--root <same-root> --folders A_FOLD/G01 A_FOLD/G02 A_FOLD/G03 B_LOCAL/G01.
review.py creates actual sections, projected silhouettes, core validation and boards.
package_review.py saves a local compact review, with no network or raw geometry copy.

A/G* and A_REFINED/G* earlier recipe versions are preserved per checkpoint on E.
B/G01 is an unreviewed extra-refinement preliminary; B_LOCAL/G01 is the official B.
No origami solver, automatic crease detection, panel developability, physical
stability, thickness or fabrication certification is implemented.
