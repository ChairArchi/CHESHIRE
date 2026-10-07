# Task28 handoff

Status: PARTIAL. Selected lineage P4_C033_ZERO, G0-G5. Read TASK28_RESULTS.md and analysis/visual_assessment.json first; the technology's full independent third scale remains unproved.

Baseline a9974d39f8e92c01c454e455399ca038fb8513cc; branch experiment/task28-hansmeyer-benchmark. Exact final local SHA is in release.json and FINAL_REPORT.md under E:/CHESHIRE_DATA/task28. No push/merge/Task29.

Start with renders/lead_progression.png, lead_detail.png and task27_vs_task28.png. Canonical state/geometry is lead/G0..G5, not the renderer's triangles or native display normals. dcc/lead.obj and lead.3dm retain exact final XYZ/quads; dcc/lead_import_evidence.json verifies actual reread and headless open. MODEL.zip is useful because it retains every lead checkpoint, origins, coarse-face ancestry, operator records, full schedule and native geometry, rather than only a final render.

Every candidate and intermediate failed visual alternative remains in candidates/; 70 definitions /253 actual stages. Initial46 candidates are followed by12+6 corrections and6 intrinsic-motif checks. Complete source/parent/capture identities: stage_manifest.json. Executed early source versions: source_snapshots/. A completed checkpoint is immutable; use fresh names/tags for further trials. A directory left by an incomplete worker is not a success: require summary.json plus geometry/state/OBJ and review process.json before resuming.

Recheck the complete original artifact root:

```powershell
.venv/Scripts/python.exe tools/hansmeyer_benchmark_evidence.py --output-root E:/CHESHIRE_DATA/task28 --audit
```

Replay a new candidate from the existing actual G0: copy a reviewed definition to definitions/candidates/NEW_ID.json, change its id, and call examples/hansmeyer_benchmark.py --output-root ROOT --names NEW_ID --generation 1, then each next generation separately. Each actual output must be inspected before further advancement. Keep all nine controls explicit, normal-offset units separate, and real prior origin classes. CLI uses saved current XYZ/origins, not manually reconstructed folds. --prepare reads the recovered inventory in the original E:/CHESHIRE_DATA/task28/analysis path; restoring the archived lead checkpoints does not require --prepare. Source code and pyproject.toml are included; third-party runtime DLLs/licenses are not distributed. Preserve original coordinate units.

Validation: 818 full tests /34 mechanism tests passed; all six actual lead checkpoints and every lead child exact-replay verified; native exact reread PASS. Weighted standard zero phase agrees within floating-point roundoff, not a bit-exact claim against a different summation implementation.

Interpretation limits: strong macro/secondary form is real. Increasing resolution or calling a fine cell lattice nested hierarchy would misstate the result. The most relevant remaining question is retention of independent smaller articulation through later curvature; previous four-way curling also involved Mola topology events. Task28 did not add those events or rewrite core equations. No next task has been started.
