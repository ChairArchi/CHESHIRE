# Optional Mola tapered extrusion study

CHESHIRE uses the official [HDMolaGH 1.0.0 standalone assembly](https://github.com/dbt-ethz/HDMolaGH/tree/1.0.0/install) through one real `FaceSubdivision.ExtrudeTapered(Mola.Vec3[], Single, Single, Boolean)` call per selected face. Mola is attributed to its upstream ETH Zurich authors. These A/B/C settings are CHESHIRE study choices, not author parameters. Technical compatibility does not establish license approval or permission to redistribute; no Mola DLL/source is included.

Keep the official standalone `HDMola.dll` outside this repository. The installed `HDMolaGH.gha` embeds that assembly, but CHESHIRE does not load the Grasshopper plugin or change its installation. Our tested external DLL is `C:\Users\USER\Libraries\HDMola\1.0.0\HDMola.dll`, assembly `HDMola, Version=1.0.0.0`, SHA-256 `91c6863ee1bfe370dae028389b7d966f36fa58b321d6b2706e111084c8fba5de`, targeting .NET Standard 2.1. Its references include netstandard 2.1 and Newtonsoft.Json 13; the tested extrusion call and public-type inspection succeeded without separately resolving Newtonsoft.Json.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[mola]"
.\.venv\Scripts\python.exe examples\mola_taper_study.py --dll "C:\Users\USER\Libraries\HDMola\1.0.0\HDMola.dll"
```

The optional extra pins Python.NET 3.0.5. CLR imports stay inside the optional adapter. Ordinary mesh-grammar/core use needs neither Python.NET nor Mola. [Python.NET requires runtime selection before importing clr](https://pythonnet.github.io/pythonnet/python.html); the packaged runtime configuration selects CoreCLR .NET 8, permits installed 8.0 patch updates, and disallows switching to .NET 9 or Windows netfx. Tested runtime: 8.0.14, Python 3.12.10. No runtime installer runs automatically. [.NET Standard 2.1 needs a modern compatible runtime](https://learn.microsoft.com/en-us/dotnet/standard/net-standard).

In Rhino 8 ScriptEditor / Python 3, run `rhino/CHESHIRE_Run.py` on the UI thread (`async:true` disabled), select an **original existing Mesh**, choose **MolaTaperStudy**, and paste the exact standalone DLL path when prompted. This explicitly selects **all eligible planar convex triangles/quads**. Excluded faces remain unchanged and are reported with reasons. `MeshGrammar` keeps the existing Task 08 recipe available. The earlier user's G2 PARTIAL run stopped because G3 estimated 53,504 faces and 55,786 vertices exceeded the unchanged 50,000 limits; do not use that displaced G2 as the planar study input.

The study uses the same input and selection for exactly three independent variants:

| Variant | Height ratio | Fraction toward arithmetic face center |
| --- | ---: | ---: |
| A | 0.10 | 0.25 |
| B | 0.30 | 0.25 |
| C | 0.10 | 0.65 |

Height equals `height_ratio * sqrt(original face area)` in input coordinate units. A/B isolates height; A/C isolates taper. New run layers show original reference, selected-face subset preview, A/B/C. Empty selection shows a labeled original preview and three unchanged copies. Only display copies translate along world X, with identical scale/orientation. Source fingerprint checks, Undo, Esc cancellation, worker isolation (`-E -s` and sanitized environment), log diagnostics, and insertion rollback are retained. Selection/viewport/Undo/cancellation checks for this new mode remain **PENDING in Rhino**; the real headless worker has been tested.

Limits remain 5,000 input faces, 20,000 input vertices, 50,000 vertices/faces per result, 1,000 selected faces, and 60 seconds per worker. No truncation or automatic repair. Completed validated variants can be retained as PARTIAL if a later variant fails. Requests/results/logs go to unique ignored `output/task09/<run_id>/` directories. Responses include selected/excluded IDs, exact per-face parameters and height/normal offsets, roles, immediate lineage, fresh areas, DLL/runtime identity, counts, timings and warnings. The smoke exports a unit cube control and actual A/B/C OBJ results (12 vertices / 10 faces each for one selected cube face).

Direct API: `from cheshire.mola import extrude_tapered_once`. Supply explicit `selected_faces`, scalar or **exactly selected-keyed** `height_ratio` and `fraction`, and `dll_path`. Only `cap_top=True` is supported; `0 < height_ratio <= 0.5`, `0 < fraction < 0.9`. Selected nonplanar/concave/degenerate faces and invalid/non-manifold input topology are rejected. Original boundary coordinates and IDs, unselected face keys/connectivity, and shared base edges are preserved. Top IDs are shared within each parent only, never welded across parents. Nonempty output carries geometry/connectivity only; use explicit field inheritance for attributes.

Mola's float32 boundary is centered and uniformly scaled per face, with height scaled consistently. Side/cap ordering and expected interpolation/normal offset are verified at absolute tolerance `2e-6` in normalized local coordinates; original boundary XYZ stays exact. Upper XYZ comes from Mola. In-face inheritance weights are `fraction/n` for every parent corner plus `1-fraction` for its associated corner; the recorded normal offset is additional geometry, not explained by those weights. Categorical conflicts remain `None`; geometry fields are marked RECOMPUTE and measured afresh. Extreme/near-degenerate numerical controls may be rejected. No collision, global intersection, fabrication-readiness or recursive grammar claim.

Focused optional tests are separate and require explicit configuration:

```powershell
$env:CHESHIRE_MOLA_DLL = 'C:\Users\USER\Libraries\HDMola\1.0.0\HDMola.dll'
.\.venv\Scripts\python.exe -m pytest -q tests/test_mola_optional.py
.\.venv\Scripts\python.exe -m pytest -q
```

Without the configured optional backend, these six real-backend tests skip; ordinary tests remain active. No test assets are downloaded.
