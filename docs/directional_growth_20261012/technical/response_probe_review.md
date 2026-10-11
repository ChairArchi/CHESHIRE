# Existing geometry normal-response comparison - G3 only

Actual common source: OVERLAP/G02. Each candidate inherits TWO growth cycles and adds exactly ONE existing Task36 split plus unchanged escape18 finite nearest-outside pass (.55 fraction, .22 field budget, target factor3, old F01 cache). No new authored fold, amplification, shape warp, smoothing or original-operator change. Preserved class_signed OVERLAP/G03 is the baseline.

FACE_RESPONSE uses the existing face_geometry option: face-normal coefficient responds to current signed face contrast, while the direct edge-normal response keeps its previous sign policy. SIGNED_RESPONSE uses existing all_geometry: face response is the same, with direct edge-normal coefficients additionally responding to signed edge contrast. Existing vertex_gain=0 and vertex_memory=1 mean BOTH have exactly zero direct vertex-normal displacement; all_geometry does not activate vertex deformation in this recipe. Standard averaging remains zero and other ancestry stencils remain unchanged.

Actual front/oblique/side review: both new paths soften small nested lips and expose somewhat broader, calmer face patches compared with the baseline. The large two-body/cup/waist silhouette and deep side recesses persist. Neither produces a new meso event. FACE versus SIGNED differs only subtly in the edges of small cells. This reduces some fine cell insistence but also weakens the folded articulation; it is not a stronger aesthetic lead. The wider panels reproduce part of the known flattening/under-articulation concern. Retain the baseline OVERLAP G3 as lead and stop both alternatives at G3. No G4 and no extra branches generated.

The geometry-dependent coefficient response is actually working: both have1736 positive/4408 negative nonzero face coefficients; FACE edge coefficients remain positive12224, SIGNED has4590 positive/7634 negative edges. Resolved vertex coefficients are all zero. These are coefficient signs, not a claim that the complete coupled displacement follows only the local normal. Relative to baseline, final control RMS change is .02362 for FACE and .02147 for SIGNED model units. Same control connectivity/chart. The changes are real but mainly local relief rather than architectural development.

Both outputs:51202 actual vertices /102400 triangles, one connected, watertight and winding consistent. Actual X/Y reflection error below5.38e-15. Minimum triangle areas1.1834e-6 and1.2074e-6 exceed unchanged1e-12. Self-intersection NOT CHECKED for either alternative. Thickness, structure and fabrication NOT CHECKED. No repairs or high-cost checks run. Existing old controls are fixed during Task36 but may move during the following field; no crease-memory guarantee.

Actual comparison: review/response_G3_comparison.png
Actual measured differences and coefficient records: review/response_metrics.json
Meshes, controls, checkpoints, operation arrays and exact recipes: FACE_RESPONSE/G03 and SIGNED_RESPONSE/G03
Adapter: experiments/directional_growth_20261012/response_probe.py
