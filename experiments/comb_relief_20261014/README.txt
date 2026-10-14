INTEGRAL DIAGONAL COMB RELIEF / 2026-10-14

One stronger native finishing study authorized after the previous center accent
proved visually weak and selective shading hid the user's preferred broad comb.
Source: same REVISED saved body as the user's attached reference image.
Original WIDE_ROOT_FINISHED design checkpoint remains read-only and separate.
Heavy data: E:/CHESHIRE_DATA/experiments/comb_relief_20261014/trial01

PRINCIPLE
Small source nonplanar quad cells receive a short diagonal ridge, with two
interior vertices and six triangles. Ridge direction follows the higher actual
source diagonal. All four original boundary edges and control corners remain
unchanged. The old native center becomes one ridge endpoint; one vertex and
two triangles are added per selected disk. This is an integral surface, not
separate attached ornament, another control subdivision or G8.

R0=.4*A+.6*O+h*N; R1=.4*C+.6*O+h*N
h=min(.65*weight*minimum_positive_projected_source_fan_altitude,H*.0006).
Six triangles: (A,B,R0),(B,R1,R0),(B,C,R1),(C,D,R1),(D,R0,R1),(D,A,R0).
One safety exclusion requires all six projected signed areas to be positive.
No amplitude sweep or automatic trial retuning is used.

BROAD SUPPORT
measure.py imports frozen source measurement functions read-only. It removes
the failed aspect/world-direction restrictions and keeps physical fine-cell
size, actual source warpage, body-height support and positive fan safety.
The mask is actual-face-orbit symmetric. It changes no shading flags.

SYMMETRY AND TOPOLOGY
Generate canonical face orbits, reflect both ridge positions and actual source
corner IDs, reverse triangle winding for odd reflections. Fixed face orbits
remain original. Each local roof is an oriented disk with the exact original
boundary; internal edges have reciprocal incidence. Source native four-fan
indices are checked against actual source controls before replacement.
Controls and unselected native centers/face rows are checked unchanged.
This certifies the local disk replacement and inherited connectivity; it does
not certify global intersection freedom or fabrication readiness.

PRESENTATION
render.py reuses four actual source all-flat images and renders one candidate
with identical four cameras, mineral material, lights, Blender4.5.4 and samples.
Native coordinates/indices/all-flat flags are read back unchanged. No selective
normal interpolation hides coverage. boards.py verifies and composes pairs.
Numerical geometry checks are separate from visible and aesthetic assessment.

EXECUTION
python measure.py --root NEW_E_ROOT
python run.py --root NEW_E_ROOT
blender --background --python render.py -- --root NEW_E_ROOT
python boards.py --root NEW_E_ROOT
Use existing venv and Blender. TEMP/TMP on E. Existing trials never overwritten.

No Mandelbulb experiment is included: the user's flower-covering suggestion is
recorded in the preceding checkpoint and explicitly deferred by the user.
