# Task36 — neutral carrier and recursive growth

Task35 baseline: `f3a0642`, with H01/H02 retained in `E:/CHESHIRE_DATA/task35`.
Task36 data root: `E:/CHESHIRE_DATA/task36`. Existing research directories are read only.

All new runs use a closed, constant 1000 × 1000 × 4000 square column, X/Y cross-section,
Z vertical, two equal axial cells. No neck, shoulder, sinusoidal profile or random seed
is supplied. Units remain unresolved project units. Every comparison keeps the same
carrier and physical render scale. Quarter-turn and X/Y reflection symmetry are retained.

`definitions/PREREGISTERED.json` records initial planes and camera conditions.
The two subsequent user instructions require separate curvature-component and boundary
inheritance controls. J01–J06 decompose standard CC displacement, weighted stencil
displacement and propagated normal displacement. L01–L04 separate cap XY constraints
and ancestry-diagonal bias. These IDs do not establish success by themselves.

The native triangle surface matters: `mean` fan refinement changes nonplanar surfaces;
`vf` samples the incoming physical fan centre and splits the inherited V/F diagonal.
Inactive `vf` refinement preserves that triangle surface. Operator quads and actual
native fan triangles are both stored; auxiliary fan points are not independent operators.

N compares strong/shallow and smaller/deeper iteration on the explicit surface. Q compares
global collision reduction with symmetry-closed local collision reduction. Mandatory
full transverse, cap orientation, topology and regression criteria are retained.
Requested controls, actual geometry and local safety masks are distinct records.

Some definitions were prepared but not run. The external candidate's `completed.json`,
`failed.json`, source identity and resource log determine its actual execution status.
Never infer completion from a definition filename. Use a new tag for every execution:

```powershell
.\.venv\Scripts\python.exe -B tools/task36_research.py --action run --request studies/task36/definitions/Q02_LOCAL_SAFETY_G8.json --tag MY_FRESH_RUN
```

Final selection, limitations and exact preservation identities belong in
`docs/TASK36_RESULTS.md`. No Task35 operator, historical record or test is replaced.
