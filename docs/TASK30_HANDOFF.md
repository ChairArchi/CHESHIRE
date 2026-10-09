# Task30 handoff — PARTIAL

Root: E:/CHESHIRE_DATA/task30. Selected U_67_LOCK_END4. Read final_decision.md first.
The full-precision final_selected_pipeline.json and actual lead checkpoints are authoritative.
No push, merge or Task31. No new broad sweep is warranted by this result alone.

| path | status / responsibility |
|---|---|
| src/cheshire/reference_subdivision.py | Canonical audited CC base; unchanged Task29 behavior |
| src/cheshire/subdivision_pipeline.py | Small canonical explicit dispatch and checkpoint API, no research-root dependence |
| src/cheshire/dual_subdivision.py | Opt-in published bounded DS; face roles, multi-parent supports, no genus changes |
| weighted / generational / sharp modules | Historical replay/controls and existing boundary/crease clients; unchanged |
| examples/task29_search.py, task29_topology.py | Archived research sweep and pair-weld controls; not the minimal default workflow |
| tools/task29_* | Archived Task29 evidence tools; renderer/export codec reused without changing their historical defaults |
| tools/task30_study.py | Bounded16-definition experiment orchestrator; preserve saved outputs; refuses checkpoint overwrite |
| tools/task30_evidence.py | Actual lineage selection, exact cube/checkpoint replay, OBJ semantic verification |
| tools/task30_views.py | Actual mesh capture using unchanged fixed Task29 flat renderer |
| tools/task30_native.ps1 | Installed Rhino8 exact3DM reread/headless open; use Windows PowerShell5.1 |
| tools/task30_finish.py | Evidence/report publication and post-commit streaming archive checks |

Minimal portable continuation (from repository with .venv, using an unused output folder):

```python
import json
from pathlib import Path
from cheshire.subdivision_pipeline import load_checkpoint, step, save_checkpoint
root = Path('E:/CHESHIRE_DATA/task30')
definition = json.loads((root/'definitions/final_selected_pipeline.json').read_text())
state = load_checkpoint(root/'lead/G7')
state, metadata, arrays = step(state, definition['steps'][7])
save_checkpoint(Path('YOUR_UNUSED_OUTPUT_FOLDER/G8'), state, arrays)
```

For cube replay initialize SubdivisionState(cube(), full(6,-1,int8)), then run every
declared step. Definitions carry generation, scheme and scale; wrong generation or
unknown scheme is rejected. DS point classes are unknown for Eq4 intentionally.
Face origins are separate from vertex classes. Never reconstruct DS multi-parent
support from a guessed single anchor. Operator_state.npz contains all actual supports.
Rest is positive cage association, not an extra displacement or gate field.

Local exact lead verification command (rewrites same task-stamped OBJ bytes):
`.venv/Scripts/python.exe -X utf8 tools/task30_evidence.py --verify`.
For independent use, replay to a fresh destination via the portable API above.
Re-running --prepare / --primary / --secondary / --select in completed artifact folders
is intentionally refused by existing outputs. Review existing evidence instead.

Full tests require CHESHIRE_MOLA_DLL=C:/Users/USER/Libraries/HDMola/1.0.0/HDMola.dll
and PYTHONNET_RUNTIME=coreclr. Use a fresh external --basetemp directory; an existing
negative repository-identity fixture requires a path outside the repository.
Run `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp FRESH_EXTERNAL_PATH`.

Task29 original definition/control stays available in retained_canonical_pipeline.json
and controls/task29. The selected Task30 recipe is an opt-in study lead, not a silent
new default for all geometry clients. Grouped DS and continuous DS are negative results
for this target, retained as evidence rather than deleted. See reference matrix/source
ledger for PDF page/hash attribution; the inline image is not fabricated in the archive.
