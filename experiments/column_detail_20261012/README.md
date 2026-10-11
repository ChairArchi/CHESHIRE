# Column detail study

Actual column-only comparisons from the saved OVERLAP G3 lead. The study tests another existing subdivision/field cycle, selective E/F relief, and small continuous radial/axial returns. No gate, physical origami solver, new general engine or Tissue operation is implemented.

Results and aesthetic decisions: [REPORT](../../docs/column_detail_20261012/REPORT.md). Large geometry and original render frames remain on `E:/CHESHIRE_DATA/column_detail_20261012`; the compact repository package contains boards, recipes, source notes and logs. [INDEX](../../docs/column_detail_20261012/INDEX.json) lists actual paths.

## Saved branches

| Branch | Existing operation after G3 | Subdivision / field totals | Outcome |
|---|---|---|---|
| CONTINUED G4 | Task36 coupled split, then finite-18 field | 4 / 4 | More fine crust; stopped |
| NESTED G4 | Bilinear split, regional E/F relief | 4 / 3 | Too weak; stopped |
| NESTED_STRONG G4 | Same E/F operation, coefficient gain 3 | 4 / 3 | Cell stars and thorns; stopped |
| RETURN_DETAIL G4 | Bilinear split, two small PCHIP return events | 4 / 3 | Limited continuous lip/pocket improvement |
| RETURN_HYBRID G4 | Same saved post-return controls, one field pass only | 4 / 4 | Local survival, no overall improvement |

Every new stage has 204,802 physical vertices and 409,600 triangles, with a separate 102,402-vertex / 102,400-quad next-control mesh. Source G3 has 102,400 physical triangles. Triangle fans used for rendering are not fed back as the next quad controls. `gate.ply` is a legacy export filename containing a column. The float64 explicit triangles in `geometry.npz` are authoritative and drive Blender.

## Execution

Run from this worktree with the existing CHESHIRE Python environment. The generators refuse to overwrite existing nonempty result stages. Use a new E-drive `--root` directory for regeneration. Do not run these commands merely to repeat successful checks.

```powershell
& 'C:/Users/USER/CHESHIRE/.venv/Scripts/python.exe' experiments/column_detail_20261012/continued_probe.py --help
& 'C:/Users/USER/CHESHIRE/.venv/Scripts/python.exe' experiments/column_detail_20261012/nested_probe.py --help
& 'C:/Users/USER/CHESHIRE/.venv/Scripts/python.exe' experiments/column_detail_20261012/return_detail_probe.py --help
```

Generation recipes and operation arrays are preserved beside each actual mesh. The scripts import the existing fold-band ancestry, Task33/Task36, role-growth and smooth-deep operators without changing their source files. See each saved `generation.json` and recipe snapshot for the exact command parameters and provenance.

The existing `iaac_mandelbrot_20261011/column_render.py` provides the standard front/oblique/side views. This study's `detail_render.py` adds fixed scale/region cameras without modifying the mesh. `review.py` builds comparisons from those frames and reuses existing selected core validation records; `finalize.py` packages only the small review set.

```powershell
& 'C:/Users/USER/CHESHIRE/.venv/Scripts/python.exe' experiments/column_detail_20261012/review.py --validate RETURN_DETAIL/G04 RETURN_HYBRID/G04
& 'C:/Users/USER/CHESHIRE/.venv/Scripts/python.exe' experiments/column_detail_20261012/finalize.py
```

## Evidence limits

Core validation on the two return comparisons confirms symmetry and closed single-component connectivity but detects self-intersection in both. Generation-time JSON remains unchanged; later `core_validation.json` supersedes its pending intersection status. The other three weak branches were not given expensive intersection checks.

Guide protection is approximately 95% attenuation at its strongest, not a full crease lock. The exact-lock count is zero. Mean-fan resampling can change the physical surface even if old control coordinates stay fixed. Neither the extra polygon count nor local survival proves automatic multiscale ornament. No G5 was generated. Thickness, structural performance and fabrication are unverified.
