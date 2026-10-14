LOCAL LARGE-SCALE REFINEMENT / 2026-10-14

User choice: keep the accepted clear, broad diagonal scale language; make only
oversized scales smaller. Source is comb_relief_20261014/trial01/RELIEF.
All earlier source data and executed experiment code remain read-only.
Heavy data: E:/CHESHIRE_DATA/experiments/comb_scale_refinement_20261014/trial01

SELECTION
measure.py records one actual physical footprint cutoff maxedge>H*.0012 on
accepted roof quads, with exact source face-orbit symmetry. The coarse plate
and preferred fine macro regions are measured separately. No direction/aspect
gate or shading filter is introduced. Original support and height data remain
frozen. COARSE_QUADS.npz contains coarse_quad_ids; source bindings and physical
size distributions are in MEASUREMENT.json.

LOCAL REPLACEMENT
Only coarse roof cells are replaced with four child roof cells. Their base
uses original source corners, original-edge midpoints and the original source
arithmetic parent center. The large raised roof is replaced, not merely refined
while retaining its old coarse shape. The accepted ridge recipe is applied to
each child, inheriting parent weight. Child height is limited by child scale
and half of the actual accepted parent height.

CONFORMITY
A shared midpoint registry is keyed by actual original control edges.
Unrefined neighbor triangles on those edges are split into two coplanar
triangles. Their geometry is unchanged. Original small-roof vertex positions
remain exact; connectivity at the refinement collar can change. Two private
parent ridge IDs are reused; no global native index compaction is needed.
Canonical face-orbit construction, reflected IDs and odd winding reversal
preserve the existing symmetry. Safety rejection applies to an entire parent
orbit. This is one local native G7 finish, not whole-column G8 or control growth.

PRESENTATION
Same four actual cameras, material, lighting and all-flat shading as accepted
comb_relief. Existing accepted source renders are reused with exact hashes.
New candidate coordinates/indices/shading flags are read back unchanged.
Visible size reduction is assessed separately from numerical/topology checks.

EXECUTION
python measure.py --root NEW_E_ROOT
python run.py --root NEW_E_ROOT
blender --background --python render.py -- --root NEW_E_ROOT
python boards.py --root NEW_E_ROOT
Use existing venv/Blender; TEMP/TMP on E. Existing trial outputs never overwritten.
No Mandelbulb, external ornament, smoothing, Boolean, remesh or variation is
introduced by this stage. Global intersection/fabrication checks are outside
this local surface-conformity verification.
