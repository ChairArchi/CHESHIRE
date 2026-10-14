RIM ORNAMENT ADAPTATION / 2026-10-14

The user delegated technically feasible visualizations after the initial two
local ornament comparisons. This trial does not depend on a further motif vote.
It preserves that first trial and the original WIDE_ROOT_FINISHED SPAN G7.

Data: E:/CHESHIRE_DATA/experiments/rim_ornament_adaptation_20261014/trial01
Inputs: the two actual closed prototypes from local_ornament_comparison trial01.
No AI-generated design image, normal map, new body subdivision, whole-body
smoothing or rejected volumetric finish is used.

One fixed candidate per direction:
MANDEL_RIBBON: low/long 3D finite Mandelbulb surface along a source-derived guide.
LEAF_FAN: rotate leaf growth into the guide tangent and rib/thickness into normal.
HYBRID: the same fan plus two smaller actual Mandelbulb pieces rooted on its upper
surface. These are independent intentionally overlapping closed meshes.

placement.py derives three actual source roots per marked group using original
control-edge connectivity and records the actual path, normals, patch extent,
local PCA evidence and macro camera. Six groups are retained. Group3's genuinely
small support causes a fixed .38 size factor for all its ornaments.
The run uses PCHIP through the three key roots and interpolated source normals.
Parameter distance is the key-root chord distance, not exact curve arc length.
Endpoint extrapolation uses straight tangents with constant endpoint normals.
Guides are not certified fold crests or exact surface projections. Actual query
extent and extrapolation distance are recorded per group.

Each transformed piece must retain positive triangle area and contain its actual
body/leaf attachment point by ray parity. This proves local overlap only, not a
weld, Boolean union, collision repair, tangent continuity, or fabrication status.
X/Y copies are constructed with reflected coordinates and corrected winding.
Original G7 generation/control/native files are hashed before and after assembly.

Replay into a NEW output root to preserve this checkpoint:
  python placement.py --root NEW_ROOT
  python run.py --root NEW_ROOT
  blender --background --python render.py -- --root NEW_ROOT
  python boards.py --root NEW_ROOT

Use the existing CHESHIRE venv and Blender4.5.4. TEMP/TMP belong on E.
The existing prototype NPZ files remain shared read-only dependencies.

Renderer loads original native body once, produces a new real original macro,
then three candidates with four cameras each. Old front/body/close references are
reused and matched. Original Blender vertex/index arrays are checked unchanged
after each candidate; no renderer geometry modifier or shading smoothing is used.
Boards preserve all source images900x900 without crop/resize, four columns3600x1020.
Only the inline conversation preview is compressed/cropped for presentation.

See docs/rim_ornament_adaptation_20261014 for actual receipts and visual assessment.
