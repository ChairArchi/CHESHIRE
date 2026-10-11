# Column development / preserved comparison

Branch: `experiment/column-fold-development-20261011`.
Actual large data: `E:/CHESHIRE_DATA/column_development_20261011`.
Small review: `docs/column_development_20261011/REPORT.md`.

`seed_mass.py` creates nine separately retained inputs. The first six are direct
event/proportion trials; R2 reuses the proven deep-cup construction. R2 changes
the axial material map, radius profile and end return. Two bilinear carrier
splits before folding provide cap interior samples. `--coarse-input` uses one
split with the same analytic recipe; it is a sampling comparison, not the
same physical input mesh. These are geometric design operations, not origami.

`target_repeat.py` reuses actual quad splitting, finite Mandelbulb classification,
sampled nearest-outside movement and CHESHIRE PCHIP return events. Refined targets
use a bounded local lattice around used coarse targets; no global fine volume,
continuous distance solver, XYZ smoothing or legacy holdout is introduced.

```powershell
& C:/Users/USER/CHESHIRE/.venv/Scripts/python.exe -B experiments/column_development_20261011/target_repeat.py --source E:/CHESHIRE_DATA/column_development_20261011/inputs/SPAN_R2/G00 --name NEW_FINE --variant n4 --target-mode refined --fraction .18 --fold-schedule --stages 3
```

Use a new output name for changed settings. Existing completed outputs require
matching signatures and are not overwritten. `control_quad.npz` is the next
generation input; `geometry.npz` contains the explicit triangle fans used by
both the renderer and checker. Raw field, applied field, return and total
displacement are stored separately. Field budgets do not limit the summed
authored return displacement.

`--staged-field` uses actual classifier iterations [4,8,18]. [2,4,8] was not run:
at 2 iterations the existing 161 axis grid samples have no outside member.
No axis grid/domain extension was added. Lower iteration is not a guaranteed
frequency filter and may enlarge finite occupancy; inside-only updates can
retain earlier displacement. This alternative showed little aesthetic gain.

Render with the unchanged `iaac_mandelbrot_20261011/batch_render.py` and the new
E root. `review_development.py` only reads saved previews/JSON by default.
`finalize.py --validate CANDIDATE/G03` invokes existing core checks only on named
selections, then copies small artifacts and file pointers. No repeat hash audit.

Both selected FINE/COARSE G3 have confirmed self-intersections. They are closed
single components with exact reflected topology, but thickness, physical fold
mechanics, structure and fabrication are not checked. No OBJ export was added.

Sources: [IAAC project](https://www.iaacblog.com/programs/mesh-subdivision/),
[depth comparison](https://www.iaacblog.com/wp-content/uploads/2020/12/pres112.png).
Our formulas/coefficients, initial mass, target refinement and return schedule
are explicit reconstructions/compositions, not recovered IAAC executable code.
