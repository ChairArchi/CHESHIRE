# Task 17 results

Baseline: `bba4fd7d6e3a2af8c87c91fb9aeec70c4cd37b7b`. No push.

**PARTIAL SUCCESS:** weighted DS adds angular inset/frame vocabulary. No tested result clearly demonstrates stable macro → meso → micro hierarchy. Sixteen deterministic design schedules, a standard control and exactly two justified hybrid probes all reached G6. Completion describes numerical/topological execution, not clean geometry or design success.

## Capability checks

Both cyclic quad/triangle equations were independently verified. Three zero-weight generations match public COMPAS DS on closed quad and triangular fixtures within `1e-12`, with equal oriented topology/counts and deterministic output. The focused checks also verify family construction, immediate lineage, fallback, monitor independence, local budget, serialization, source immutability and unchanged C11 handoff. COMPAS remains 2.15.1. See [reference note](TASK17_REFERENCE.md).

The C0 carrier is exactly 24 V / 44 E / 22 F. Its vertex valences are 12 degree-three, eight degree-four and four degree-five. No carrier-resolution or CC parameter search was performed.

| G | Vertices | Edges | Faces | FACE | EDGE | VERTEX | Weighted fallback input faces |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 88 | 176 | 90 | 22 | 44 | 24 | 0 |
| 2 | 352 | 704 | 354 | 90 | 176 | 88 | 4 |
| 3 | 1408 | 2816 | 1410 | 354 | 704 | 352 | 4 |
| 4 | 5632 | 11264 | 5634 | 1410 | 2816 | 1408 | 4 |
| 5 | 22528 | 45056 | 22530 | 5634 | 11264 | 5632 | 4 |
| 6 | 90112 | 180224 | 90114 | 22530 | 45056 | 22528 | 4 |

Fallback is four pentagons from G2 onward: VERTEX_DERIVED at G2, FACE_DERIVED thereafter. It affects 4/90 input faces at G2 (4.44%) and 4/22,530 at G6 (0.0178%), and does not dominate. These faces keep actual standard COMPAS placement, including zero extrusion; they are never triangulated to obtain weighted stencils.

## Separate visual selections

- **MAX_CAPABILITY_CANDIDATE / BEST WEIGHTED DS:** `R13_restrained_insets`, **G3**, a clean partial checkpoint with large pointed support/shoulder masses and angular meso insets. No independent useful micro scale is claimed.
- **GATE_LEGIBLE_CANDIDATE:** `R15_restrained_edge_frames`, **G4**, a separate partial checkpoint with the opening, two support bodies and lintel clear, and weaker meso framing. This is a descriptive selection, without a gate threshold.
- **Best handoff comparison:** `HYBRID_B`, **G6**, C11 through G3 then unchanged global G4–G6 rows of R13. It preserves more C11 shoulder/lintel organization than A, but fails to add a convincing micro scale and retains warnings.

R13's strongest clean angular articulation occurs around G2–G3. Its G4/G5 each have 30 opposed-fan warnings; G6 returns to zero recorded local warnings while smoothing away meso detail. R15 has zero recorded fan/bilinear warnings and sampled contacts at every generation. Keeping all stages shows why the selected checkpoint need not be the highest generation.

## Read-only gate trajectories

Values below are G0-relative **descendant-landmark approximations**, not exact free opening clearance. Raw centers, normalized center drift, equal-anchor cloud spread, region relations and ground displacement are serialized in `raw_trajectories.json` and `selected_integrity_trajectories.csv`.

| Case/G | Opening W drift % | Opening H drift % | Outer W drift % | Outer H drift % | Outer D drift % | Mean base Z displacement |
|---|---:|---:|---:|---:|---:|---:|
| R13_restrained_insets G0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| R13_restrained_insets G1 | -7.54 | -31.77 | 18.27 | 20.88 | 146.18 | 506.52 |
| R13_restrained_insets G2 | -8.72 | -35.25 | 26.69 | 30.50 | 213.51 | 559.64 |
| R13_restrained_insets G3 **selected** | -9.47 | -35.89 | 29.95 | 34.23 | 239.60 | 566.30 |
| R13_restrained_insets G4 | -9.82 | -36.03 | 30.89 | 35.30 | 247.08 | 566.36 |
| R13_restrained_insets G5 | -9.93 | -36.06 | 31.14 | 35.59 | 249.16 | 566.15 |
| R13_restrained_insets G6 | -9.96 | -36.07 | 31.20 | 35.66 | 249.63 | 566.11 |
| R15_restrained_edge_frames G0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| R15_restrained_edge_frames G1 | -8.09 | -17.85 | 18.27 | 20.88 | 146.18 | 246.52 |
| R15_restrained_edge_frames G2 | -10.00 | -24.55 | 23.02 | 25.26 | 184.15 | 355.69 |
| R15_restrained_edge_frames G3 | -11.04 | -26.15 | 24.92 | 26.78 | 199.35 | 377.35 |
| R15_restrained_edge_frames G4 **selected** | -11.41 | -26.50 | 25.19 | 27.23 | 203.83 | 380.94 |
| R15_restrained_edge_frames G5 | -11.52 | -26.58 | 25.38 | 27.49 | 204.92 | 381.53 |
| R15_restrained_edge_frames G6 | -11.55 | -26.60 | 25.36 | 27.45 | 204.44 | 381.67 |

For both selected DS cases through G6, all 24 source anchors and all macro regions remain represented; left remains predominantly left of right, and lintel landmarks remain predominantly above support/opening relations. Opening center X stays at its source value; center Z and support-base displacement drift. Macro rounding/narrowing and pointed, displaced bases begin G1, before useful meso insets at G2–G3. No categorical gate-identity collapse was observed in these two cases; the monitor does not define an admissible range. Drift never stopped or modified recursion.

## Warnings and handoff outcome

All actual meshes remain finite, one component, closed and manifold, with no diagnostic degenerate fan faces. Several schedules nevertheless have nonadjacent transverse contact evidence and many local fold warnings. Their numerical SUCCESS is not a clean-geometry acceptance. Every weak/excluded reason and actual warning count remains in `outcomes.json`, the raw trajectories and per-generation lineage records.

Crossing audits reuse the existing COMPAS query on at most 4,096 evenly spaced actual faces per generation. They exclude adjacent/coplanar contacts and cap contacts at 30. Zero sampled contacts does not establish global collision freedom. Retained C11 audit results are explicitly the original Task16 scope.

The independent R13 angular inset vocabulary justified two handoff probes, without establishing hierarchy success. Hybrid A copies C11 G1/G2 exactly; B copies G1/G2/G3 exactly. DS uses the selected six-row R13 schedule at absolute generation numbers, reseeding the first DS input as SOURCE_FACE/FACE pair, without hybrid-specific tuning. Both reach G6. Neither produces a convincing third scale: they soften/replace narrow late CC ribs with broader panels and folds, rather than adding an independent micro vocabulary. Both histories retain local warnings; A has sampled contacts after handoff and B has three sampled contacts at G4.

**On actual evidence, Digital-Grotesque-level hierarchical complexity does not remain technically plausible within the tested CHESHIRE subdivision schedules.** This is a limitation of the tested framework, not proof that every future subdivision grammar is incapable. The single remaining limitation is stable independent later-scale differentiation: strong family pulses create folds/crossings or repeated angular relief, while restrained tails smooth away the meso structure. No Digital Grotesque reproduction, porosity or mathematical branching is claimed.

## Reproduction and Rhino

Recipes serialize all six values at every generation in `output/task17/study/recipes`. Normal extrusion ratios multiply the current global mean input edge length, along the unit current face normal. No fields or source attraction are applied. `outcomes.json` also retains the two exact hybrid recipes/prefixes.

Use the repository venv and a fresh task-local reproduction directory:

```powershell
.\.venv\Scripts\python.exe -E -s examples/subdivision_capability_study.py --study output/task17/reproduction --init
.\.venv\Scripts\python.exe -E -s examples/subdivision_capability_study.py --study output/task17/reproduction --run DS_STANDARD U01_early_expansion U02_interpolation_release U03_sign_change U04_contraction_pulse
# Run the eight F05–F12 cases, then four R13–R16 cases by their exact recipe IDs, with the same --study argument.
.\.venv\Scripts\python.exe -E -s examples/subdivision_capability_study.py --study output/task17/reproduction --run HYBRID_A --hybrid 2 --recipe output/task17/study/recipes/R13_restrained_insets.json
.\.venv\Scripts\python.exe -E -s examples/subdivision_capability_study.py --study output/task17/reproduction --run HYBRID_B --hybrid 3 --recipe output/task17/study/recipes/R13_restrained_insets.json
```

Attempted recipes are never overwritten. `--init` copies the existing exact C0/C11 evidence rather than rerunning or changing Task16. It uses the original Task16 evidence when present, otherwise the bundled Task17 C0/C11 copies. `examples/subdivision_capability_delivery.py --generate` serializes the already reviewed canonical study; it does not rank new reproduction results automatically.

Rhino entry: `rhino/CHESHIRE_Run.py` → **SubdivisionCapabilityStudy**. It loads SHA-verified reviewed outputs from `output/task17/study`, including the selected intermediate DS checkpoints and hybrid, instead of repeating a search within a 60-second interactive run. The C0 template and results are translated to the selected original gate bbox center/floor; scale/orientation stay fixed and the selection stays untouched. C0's established 500-depth template versus the original dense gate's 900 depth remains documented. Best DS and max-capability roles share one mesh/label to avoid duplicate output.

Existing environment isolation, timeout/cancellation, per-run directories, atomic response checkpoints, X-only display offsets, TextDots/layers, undo and failure cleanup remain in use. Other modes/default count ceilings are unchanged. Only this mode opts into 120k polygon exchange. Rhino display tessellates n-gons into an explicit fan and stores their original ordered boundaries as MeshNgon groups; calculation/OBJ polygons remain intact. The display approximation is labeled and never fed back into subdivision.

**Rhino host status:** no running Rhino host was available; no actual host insertion, MeshNgon API execution, UI cancellation or screenshots are claimed. A real isolated .venv subprocess smoke run validates the actual selected cached outputs and response path; standard-library display-plan/loader tests cover the new bridge branch. All images are headless approximate polygon projections, with fixed camera/scale/light and registered crop. `all_*` and `selected_*` plans share exact bounds. Geometry that leaves the detail crop is not recentered.

Verification ran the full 729-test suite once: 725 passed, and four legacy launcher tests exposed eager capability-only .NET imports. Those imports were moved into the new branch and the original call form restored for existing modes. All four affected checks and all nine Task17 checks then passed (13 passed in the focused follow-up); existing tests were not changed or weakened. Both logs are retained, and the full suite was not repeated.

Complete-suite/diff logs, final commit identity, archive size/hash and inventory are in the review manifest and delivery record. Semantic field lineage remains NOT IMPLEMENTED; constructive immediate parents and C0 anchor associations are retained separately.
