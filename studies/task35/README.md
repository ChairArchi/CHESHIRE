# Task35 — finite sectional-column research

Height 4000 in unresolved project units. X width, Y depth, Z vertical. A closed octagonal column has common fixed original-material buffers 0–240 and 3760–4000. No lintel or gate connection is constructed.

`PREREGISTERED_EVALUATION_V2.json` records evaluation before model execution; V1 is retained with its pre-execution correction. Four initial comparisons are A01–04. A01/A02 retained a gate height-control copy and failed transverse geometry checks; corrected common recipes are B01/B02. B03/B04 independently remove the inherited longitudinal displacement to separate its effect. No old Task34 source is modified.

C01–04 remove one control at a time; C05 compares Task34's profile with amplitude-only regional modulation and is **not** a pure ablation of the new cut profile. C06 freezes the first generated features. D01/D02 separately test radius-relative longitudinal span and fan opening; D03 combines them. E01 refolds measured axial bulges, E02 combines confirmed mechanisms. E03/E06/E07 preserve thickness failures; E07 replays E03 once to retain rejected controls. E04 changes coarse-section contrast; E05 lowers only axial-notch strength. E08/E09 are a matched lower-strength current/frozen pair. F01 changes final angular resolution; F02 postpones first formation at fixed final sampling. Final acceptance and limitations belong in `docs/TASK35_RESULTS.md`, not this experiment index.

```powershell
# Every execution requires a fresh tag, under E:/CHESHIRE_DATA/task35/.
.\.venv\Scripts\python.exe -B tools/task35_research.py --action run --request studies/task35/definitions/E02_COUPLED_FOLDS.json --tag MY_NEW_COLUMN
```

Native mesh, rest/formation/material state, operator stencils, control vectors, feature source edges, producer overlay and source revision remain authoritative. OBJ alone is insufficient to continue the research. Feature filtering and scalar smoothstep do not smooth mesh positions. Geometry and aesthetic success must be evaluated separately; neither triangle counts nor native ancestry alone establishes success.

H01/H02 separate positive shoulder growth from the support of an inward incision.
They follow a same-incoming-mesh intervention after V01 exposed cancellation at
some upper-body sites. H01 is the final recommended research recipe and H02 the
reduced-contrast alternative; V01/V02 remain preserved intermediate candidates.
The four original comparisons are corrected B01/B02/A03/A04, not the failed A01/A02.
No recipe guarantees safety outside its recorded sampling and validation.
