# A: actual G0-G3 results, stop for review

- `output/G0.png`: simple unornamented column.
- `output/checkpoint_A.png`: rows standard CC, modified CC, modified DS,
  CC->DS->CC; columns G0,G1,G2,G3, common orthographic camera and scale.
- Each cell also has its own PNG and editable OBJ in `output/`.
- `output/checkpoint.json`: counts, bounds, test settings and checks.

| sequence | G1 V/F | G2 V/F | G3 V/F |
|---|---:|---:|---:|
| standard CC | 74/72 | 290/288 | 1154/1152 |
| modified CC | 74/72 | 290/288 | 1154/1152 |
| modified DS | 72/74 | 288/290 | 1152/1154 |
| CC/DS/CC | 74/72 | 288/290 | 1154/1152 |

Standard CC rounds the shaft. Modified CC develops shallow horizontal
undulations. DS makes sharper caps and narrow transverse ribs; the mixed
sequence makes local ridges before partial smoothing. These are changes to
coordinates and local volume, not only additional polygons.

At G3 the reference's persistent long structural pleats and strong
macro/meso/micro hierarchy have **not** been demonstrated. The shaft remains
simple and some DS features are angular or pinched. No comparison with any
historical CHESHIRE success or failure was made. No visual reconstruction
success is claimed from execution or counts.

Minimum checks passed: finite vertices, nonzero polygon normals, opposite
edge orientation, exactly two incident faces per edge, Euler characteristic 2
for all 16 meshes. Known standard cube CC and DS corner coordinates and
translation equivariance passed. These check combinatorial consistency;
self-intersections and printability were not established. Saved PNGs were
visually reviewed. Four fixed G0-G3 sequences only; no search, fusing or G4+.

**Status: awaiting user review before any larger experiment.**
