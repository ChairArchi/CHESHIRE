# Task27 continuation handoff

Status: PARTIAL design; implementation, true feedback, exact symmetry and full export verification passed. Task27 is finished at a saved G5. No Task28, push or merge was performed.

Branch: experiment/task27-dynamic-sections. Starting HEAD: 53bea0fda2779cb63a6ef31f5b7eb9c5eeff7392. Task26 preservation: 846112578d269b765f1b0b0f395d0cae4dfeadf0. Task25 reference: b4000cf85bc0768821976bab4b454ca35b8ccca3. These older states and reports remain untouched. The committed version is recorded in E:/CHESHIRE_DATA/task27/release.json; consult its exact SHA and clean status before continuation.

Primary root: E:/CHESHIRE_DATA/task27/
Accepted parent-child lineage: G0_PROFILE → R4_PROFILE_DYNAMIC_G1 → G2 → G3 → G4 → G5.
Lead checkpoint directory: stages/R4_PROFILE_DYNAMIC_G5/
Complete current geometry: geometry.json.gz
Complete continuation state: state.json.gz
Original polygon export: R4_PROFILE_DYNAMIC_G5.obj
Native full mesh: dcc/R4_PROFILE_DYNAMIC_G5.3dm
Prior generation input: descriptors.json.gz
Consumed numeric map: rules.json.gz
Current actual output descriptors: observations.json.gz
Actual point/face ancestry audit: operator.json.gz
Source/parent identities: request.json
Stats, symmetry, sections, times and resource preflight: summary.json / resource_preflight.json

R4 config is offset_ratio=.08, face_gain=3, edge_gain=1, curvature_gain=.65. Read definitions/mapping_definition.json and configuration.json rather than inventing a generation-strength factor. Use load_state then cheshire.dynamic_sections.restore; reread geometry through raw_mesh. STATIC's section.frozen_rules is a different control and must not be consumed as dynamic state. Origin/history/material/part/paired-rule correspondence and actual mesh must travel together.

Next dynamic action is to reread actual G5, intersect its current part sections and remap current descriptors. The full next mapping has been reconstructed and verified without allocating a G6 mesh. Exact smaller-checkpoint saved/unsaved next-generation geometry/state equality is tested. G6 has not been generated. Further geometry work needs a new explicit task; this handoff does not automatically start it.

To reproduce the accepted saved sequence in a new writable artifact root:

```powershell
.venv/Scripts/python.exe examples/dynamic_section_gates.py --output-root <fresh-root> --initialize
# Copy the exact saved R4 entry from configuration.json to the fresh configuration.
.venv/Scripts/python.exe examples/dynamic_section_gates.py --output-root <fresh-root> --run PROFILE_STATIC PROFILE_DYNAMIC --to-generation 3 --revision R4
# Inspect actual coarse feedback/geometry before advancing one generation at a time.
```

Existing stage names are immutable to this CLI: it rereads successful checkpoints and refuses to overwrite or resume a failed stage. Actual request source SHA256 and source_snapshots/R4 establish executed code. R1/R2/R3 remain separate recorded trials. In particular R3 G3–G5 have unacceptable physical symmetry despite paired topology. Do not choose old renders/lead or renders/progression as final: both show R3. Correct final folders are renders/lead_R4, renders/progression_R4 and renders/R4_G4_comparison. The R3 failure's exact coordinates/areas are in analysis/symmetry_failure_R3.json.

Use the same existing standard-CC controls R1_CONTROL_CC_G4 and R1_PROFILE_CC_G4 for the matched R4 G4 comparison. These are true standard CC and have identical input topology. Final accepted STATIC is R4_PROFILE_STATIC_G4; primary G5 is not a fictional same-generation four-path comparison.

Focused tests: .venv/Scripts/python.exe -m pytest tests/test_dynamic_sections.py -q
Full suite: set CHESHIRE_MOLA_DLL=C:/Users/USER/Libraries/HDMola/1.0.0/HDMola.dll and PYTHONNET_RUNTIME=coreclr, then run pytest -q. Final results were 11 focused and 815 full passing. Keep official Mola compatibility checks enabled.

Current bottleneck is local rule mapping and repetitive CC point-class organization. The explicit profile/joint and actual feedback are functioning; increasing resolution alone is not supported as the next solution. No actual RAM hard stop occurred. Preserve all existing artifacts and choose a fresh revision/stage root for any authorized later work.
