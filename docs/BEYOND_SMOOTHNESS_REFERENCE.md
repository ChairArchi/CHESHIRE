# Task22 reference contract

Michael Hansmeyer, [Subdivision Beyond Smoothness](https://doi.org/10.2312/COMPAESTH/COMPAESTH10/075-081), Computational Aesthetics 2010, pp.75–81. Publisher [PDF](https://diglib.eg.org/server/api/core/bitstreams/fc2488ef-6bb2-4a15-b775-619c7ddeec14/content).

Michael Hansmeyer, [From Mesh to Ornament: Subdivision as a Generative System](https://doi.org/10.52842/conf.ecaade.2010.285), eCAADe 2010, pp.285–293. Publisher [proceedings](https://ecaade.org/current/wp-content/uploads/2022/03/eCAADe_2010.pdf), particularly pp.289–291.

Access: exact equation/section text was checked through indexed primary publisher PDFs. Direct Eurographics fetching returned HTTP403; the complete eCAADe volume exceeded the browser size limit. No paper, image, third-party code or upstream library is redistributed. This is not an exact implementation of Digital Grotesque.

## REFERENCE-GROUNDED

Eq.(7), with iteration starting at one:

`w_i^n = a + b * (i - 1)^q`

Eq.(10), applied after the existing face point has been calculated:

`F_attracted = F_base + w6 * SUM_i[(P_i - F_base) * u(P_i)]`

Eq.(11), applied after the existing edge point:

`E_attracted = E_base + w7 * [(P1 - E_base)*u(P1) + (P2 - E_base)*u(P2)]`

The sums are literal and unnormalized. The input face corners/edge endpoints supply `P`. Topological properties can specify weights; grouped input vertices can keep fixed positions for several initial iterations. The eCAADe intrinsic-weight section proposes traversed-edge distance to original entities and local planarity/curvature for weight interpolation.

## CHESHIRE-DEFINED

`src/cheshire/sharp_subdivision.py` wraps the existing Task14/16 implementation; it does not change Eq.(1)–(4) or weighted Doo-Sabin. Existing points are calculated first, including eligible later-generation Eq.(4). Eq.(10)/(11) then reposition those points. Modified face/edge points are not fed back into the unchanged same-generation corner/edge equations. Original XYZ is never repaired, flattened, normalized or triangulated.

Nine named controls have explicit finite horizons. DISCRETE values must cover exactly that horizon. EQ7_TREND serializes `a/b/q`, weight name and every evaluated value. CHESHIRE restricts `q>0` so iteration1 is exactly `a`; undefined `0^0`, negative powers and nonfinite results are rejected. `wf/we/wp` retain the established ratio-of-current-global-mean-edge convention in study recipes; the operator receives world-unit offsets.

MotifSignature is `(vertex_valence, incident_face_count)`, computed only from connectivity. Canonical map keys are strings such as `(3,3)`; absent keys receive zero. The geometric effect depends on both `w` and `u`: positive products pull a point toward active input corners/endpoints; negative products reverse the vectors. Symmetric sums can cancel. Large products can overshoot. There is no universal sign-to-aesthetic label.

Literal locking tags the two endpoints of one deterministic input edge. Only persistent CC **corner descendants** carry those tags. For the first L sharp-stage iterations their XYZ remains fixed; L=0 disables locking. Newly generated edge/face points are never tagged. After L the corner moves by the existing rule. This descendant convention is a CHESHIRE choice, not a reconstruction of the publication's Figure9. No stronger edge-descendant lock is silently substituted.

Source-space distance is BFS edge hops on the frozen input control graph, divided by its maximum reachable hop count. Subsequent samples retain positive control-cage associations. This interpolation convention is CHESHIRE-defined; it is neither Euclidean distance nor diffusion. The planarity experiment reuses CHESHIRE's verified incident-face-normal variation divided by pi, not a new differential curvature or the paper's exact planarity formula. Existing controls interpolate linearly between serialized min/max values using face-corner/edge-endpoint averages or corner values. Undefined samples are rejected.

Regional experiments may multiply motif u by explicit original-source-face support. This changes the application scope, not topology motif classification. Source groups and support averaging are CHESHIRE choices.

Signed geometry coefficients and motif attraction never become semantic lineage weights. Existing positive face ancestry, role/event history, branch signatures and construction sampling remain separate and are preserved where available. The new operator does not invent a generic semantic inheritance contract. For frozen gates, the last actual CC point origins are recovered by replaying unchanged standard CC on saved S03 and exactly matching S04's ordered polygon hash. These known origins persist through old event stages; event-created vertices receive no invented CC class. Further eligible Eq.(4) classes come from actual new subdivision.

Existing constructive corner landmarks are also recovered from stored parent records using only the verified CC/Inset/Tapered/Roof corner rules. They are checked against Task21's exact monitor outputs at S05/S10/S12. No nearest-coordinate assignment, general dominant-parent heuristic or invented CC edge/face landmark is used.

## EXPERIMENTAL RECIPE

All u maps, trends, lock durations, regional groups, old interpolation magnitudes and optional verified Mola finishes are study hypotheses. Their actual serialized per-generation values live in `studies/task22/recipes.json`; geometry and complete operator records use relative artifact references under the explicit external output root.

The 45-degree sharp-edge threshold, diagnostic fan/bilinear warnings, sampled crossing cap and connected cross-cell chains are comparative CHESHIRE observations. They are not an aesthetic score, a collision certificate or proof of hierarchical ornament. A technically admissible result may remain visually weak.
