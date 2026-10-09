PARTIAL

# Task30 — reference-grounded consolidation and targeted tests

세 논문31쪽과 첨부8단계 이미지를 읽고, Task29의 실제 G3에서16개 제한된 실험을 했다.
선택 리드 `U_67_LOCK_END4`는 큰 접힘과2차 형상을 유지하면서 평면 법선의 각진 미세 파편을 줄인다.
그러나 비반복적인 독립 미세 성장은 증명하지 못했다. DS의 면·모서리·꼭짓점 기원별 규칙도
반복되는 경계 띠를 만들었다. 후기 구조가 더 풍부해졌다고 판정하지 않는다.

Baseline: `c71ac1f9961a45a16dd454dcf2d9f624153a8e6a`. Branch: `experiment/task30-reference-grounded-consolidation`.
Exact new local commit: post-commit `analysis/repository_commit.json` (a tracked report cannot hash itself).
No push, merge or Task31. Task29 artifacts and its source kernels are preserved.

## Reference-grounded decision

R1 Michael Hansmeyer, **Subdivision Beyond Smoothness**,2010,7pages,
DOI10.2312/COMPAESTH/COMPAESTH10/075-081: exact DS Eq5/6, F/E/V face origins and
scheme switching(p77); early-only locks(p78); complex CC-only example(p80).
R2 Blanco/Madrid,2024,15pages, DOI10.3991/ijet.v19i07.50845: design/interview/fabrication
context, no executable mask or recovered schedule. R3 Bader/Oxman,2016,9pages,
DOI10.1016/j.cad.2016.09.002: recursive cut/reflection/union makes a coarse control mesh,
then CC refines it; it is a separate generator, not Hansmeyer's subdivision equation.

The user image shows branching beside neck/bulb/rib regions and persistent large envelopes.
This is visual inference, not proof of the actual scheme/generation/normal treatment.
It was reviewed inline; its bitmap is unavailable on disk. The relation sheet therefore
labels observation cards explicitly and uses separately attributed official DGI context,
never another image presented as the attachment. PDF hashes and sources are recorded.
Official context: https://michael-hansmeyer.com/digital-grotesque-I.html
Paper publisher: https://doi.org/10.2312/COMPAESTH/COMPAESTH10/075-081

Initial primary D was connectivity vocabulary, tested by12 meaningful mixed-scheme variants.
It proved insufficient alone; the final PRIMARY working diagnosis is **C**, weak intrinsic
spatial differentiation and persistent regional/motif identity. This revision is explicit.
C is not a proven cure; D and schedule/locking interactions remain relevant.
Four secondary early-only-lock ablations completed the total16. No third direction.
This missing published DS mechanism was prioritized under the prompt's better-method clause;
the exact hypotheses, controls and negative evidence are saved, rather than another large sweep.

## Canonical base and exact selected mechanism

Retain **REFERENCE_COUPLED + LOCAL_INCIDENT_SCALE + exact nonzero nonstationary rows**,
with explicit optional intrinsic interpolation/locking. Task29 G1 H1_NO_ATTR, G2 C11B,
G3 T28_G3, G4 CURVE, G5–8 T28_G3 and all full-precision values are copied in
`definitions/retained_canonical_pipeline.json`. Eq3 uses original endpoint midpoints;
completed faces feed Eq2/3; Eq4 requires genuine previous V/E/F classes.
Sf is current mean perimeter edge length; Se incident two-Sf mean; Sv incident Sf mean.

Task30 actual G0–G3 exactly equal Task29. G4/G5 remain original CC rows; locks throughG4.
G6/G7: modified published DS, `w1=.6,wf=.03*Sf`, uniform groups. G8: original nonzero
CC row and NORMAL_VARIATION interpolation, without locks; explicit Eq1 fallback because
prior DS points have no CC V/E/F stencil provenance. F/E/V DS face roles persist as separate
state. Tested nonuniform face-origin weights are NOT in the final lead.
The original intrinsic gain3/threshold.12/control intervals are retained on CC;
locks apply atG3/G4 only. DS steps introduce new face-corner points and do not apply that
old-vertex locking extension. Exact per-step JSON is authoritative; values are not rounded.

DS changes combinatorial adjacency via F/E/V faces and cyclic fans. No welding, holes,
genus change or recursive boolean generator: Euler2. Exact multi-parent face supports
are stored. Shared G1/2/3 anchors are retained only when all parents agree, otherwise-1.
Retention proxies follow all actual parent supports; overlapping supports are disclosed.

## Actual comparison and decision

Same cube, unchanged coordinates/project units, clay/light, fixed2600-unit whole frames,
700-unit front crops, flat normals throughout. Whole three-view and G3/G5/G8 detail comparisons
are saved. No smoothing/remeshing/beauty-only evidence. Display uses0–2 quad triangulation
and float32 GPU positions only; NPZ/OBJ/3DM preserve double XYZ and original oriented polygons.

Task29 median adjacent-normal angle 37.8302deg → Task30 10.4146deg;
p90 91.2604deg → 37.8642deg.
Those are diagnostics, not a non-repetition score. Broad lobes and meso folds remain visible;
early tips shrink. Micro clutter recedes and narrow bands read more coherently, but small
patterns still recur. The all-DS control removes most fine development despite its lower
angle score. Task30 therefore remains **PARTIAL**, with a limited continuity/retention advance.
Mixed geometry plus Eq4 fallback is a coupled change; adjacency alone is not isolated.

| stage | vertices | polygons | mean edge | median normal angle deg |
|---|---:|---:|---:|---:|
| G0 | 8 | 6 | 1000.0000 | 90.00 |
| G1 | 26 | 24 | 681.6612 | 77.73 |
| G2 | 98 | 96 | 331.6375 | 43.92 |
| G3 | 386 | 384 | 157.9266 | 42.42 |
| G4 | 1,538 | 1,536 | 81.0890 | 42.91 |
| G5 | 6,146 | 6,144 | 39.2867 | 32.42 |
| G6 | 24,576 | 24,578 | 19.2928 | 22.97 |
| G7 | 98,304 | 98,306 | 9.6289 | 14.42 |
| G8 | 393,218 | 393,216 | 4.9647 | 10.41 |

All80 new G4–G8 stages completed. There are144 saved candidate stages (64 exact prefix copies),
9 unchanged control stages and9 selected lead copies,162 audited states in total.
All16 definitions and actual checkpoints remain, including negative results. No face/time cap
stopped a job. Guarded sampled peak tree+driver RAM: 1,506,340,864bytes;
guarded generation/render elapsed sum: 203.667s (not total task wall time).

## Verification and code consolidation

**862 passed, zero skipped**, with actual HDMola1.0.0/.NET coreclr. New focused cases check
independent published triangle/quad masks, oriented F/E/V fans, true CC fallback/recovery,
multi-parent anchors, deterministic groups, exact checkpoint continuation and lock lifetime.
Final cube replay matches all G0–G8 XYZ/faces/classes/rest/anchors/face roles and saved arrays;
actual G7 reload continues exactly toG8. Every lead OBJ is reread with exact double coordinates
and oriented polygons. Installed RhinoCommon8.18 rereads3DM exactly and OpenHeadless opens its
single mesh. Native sections use the actual reread file. Render hashes and source hashes pass.

After the technical decision, the small root-independent `subdivision_pipeline.py` makes
scheme, scale, generation and locking explicit; it saves/loads real structural state.
`dual_subdivision.py` is an opt-in bounded operator. Original reference, weighted, generational
and sharp kernels remain unchanged. Legacy boundary/crease clients still work; large Task29
sweep/weld scripts are archived research controls, not the default path. See handoff status table.

DS scope: closed oriented triangles/quads, input valence3/4. No general polygon/valence claim.
Finite/incidence/Euler/native checks do not certify a self-intersection-free solid or fabrication.
Exact DG masks beyond the published paper, unpublished parameters and region tags are unknown.
Reference symmetry cannot be broken by deterministic equivariant rules on identical states alone.

Open `renders/TASK30_FINAL_LEAD_PROGRESSION.png`, then `TASK30_detail_comparison.png`,
`TASK29_vs_TASK30_lead.png`, `TASK30_targeted_variants.png`, `TASK30_reference_relation_sheet.png`.
Final decision: `analysis/final_decision.md`. Complete payload: `CHESHIRE_TASK30_REVIEW.zip`.
Post-commit archive CRC/every-entry SHA proof: `analysis/archive_validation.json`.
