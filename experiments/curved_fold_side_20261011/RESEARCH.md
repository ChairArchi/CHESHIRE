# Side-view fold study: principles used

This is an independent CHESHIRE geometry experiment. We have no evidence that IAAC used these algorithms. No external implementation is copied or installed.

1. [Mitani & Igarashi, 2011, Interactive Design of Planar Curved Folding by Reflection](https://www.jst.go.jp/erato/igarashi/publications/001/PG2011.pdf). A plane cuts a developable surface; reflecting one connected part fixes the section curve and preserves each patch's intrinsic geometry. Their system requires a developable initial surface and explicitly does not check self collisions. We implement conforming triangle cuts and cumulative reflections, not their interactive UI or selection system. Four ordered cut planes select successive connected material bands. Cylinder/cone side patches supply developable inputs; caps and a sculpted-input control are not claimed to be single-sheet origami. Closed reflected shapes can intersect.

2. [Sasaki & Mitani, Ruling-aware Triangulation](https://www.cgg.cs.tsukuba.ac.jp/projects/2020/RulingAwareTriangulation/index.html). Curved-fold simulation benefits from mesh edges that follow crease polylines and estimated rulings. We test only the geometric sampling lesson: explicitly include crease curves as mesh boundaries, connect them with generators, and compare to uniform samples of the identical continuous surface. We do not implement their ruling estimator or simulator. Our generic ruled patches are not automatically developable.

3. [Tachi & Epps, 2011, Rationalizing Curved Folding](https://tsg.ne.jp/TT/cg/RigidOrigamiCurvedFoldingTachiEppsALGODE2011.pdf). Ruling geometry and panel bending matter alongside crease rotation. A surface with straight generators alone is insufficient: developability imposes compatibility. We record the scalar-triple-product diagnostic det(C', D, D'); nonzero values disprove developability of a straight ruled patch. The analytically bent variants are not ruled. No planarity/developability optimization is implemented.

4. [OrigamiSimulator](https://origamisimulator.org/), [official source](https://github.com/amandaghassaei/OrigamiSimulator). A constrained compliant solver handles edge, face and crease forces together. Simultaneous activation of all directions does not mathematically imply averaging. That earlier CHESHIRE hypothesis concerns our displacement recipe, not a general law of folding. A physical solver is a possible future comparison, not a prerequisite or a delivered feature here.

## Implemented distinction

- **C family:** prescribed 3D boundaries + piecewise panels. Genuine ridges, valleys and axial return in an actual mesh; not an inextensible folding solver. Legacy boundary positions persist, while fold angles may change.
- **R family:** actual reflection folding with patch metric preserved. Mechanical feasibility, collision-free motion and closed solid validity are separate questions.
- The initial C/R/P controls contain no Mandelbulb displacement. The later F comparisons reuse the previous finite field. No branch uses separate geometric smoothing or CC/DS coordinate averaging. Real meshes and actual front/oblique/side renders are authoritative.

## Later design stages and the marked striations

- P06 retains the P02 continuous displacement formula, but inserts mesh edges on authored profile breaks. S/T construct the reflected front/back geometry explicitly. W06 keeps the front of the rounded, deep-valley W01 and corrects the valley map's Y reflection discrepancy. Old failed trials remain intact.
- W01/W06 use shape-preserving cubic Hermite section interpolation through the same extrema. This changes the authored curve; it does not filter or average mesh vertices. PCHIP does not guarantee developability or collision avoidance.
- The marked thin stripes are not an implemented buckling model. The exact W06 formula reproduces its stored vertices within 9.75e-16, while triangle interpolation has oscillatory between-sample Y errors up to about .0163 in the measured material sections. This supports a tessellation contribution; it does not assign every rendered stripe to a single cause.
- W04/W05 instead contain an explicit signed alternating section. GEO01/GEO02 place three tapered fans in selected direction/height bands. Their local amplitudes, phase and axial return are prescribed. They do not claim spontaneous subdivision-induced folding. Legacy core coordinates persist; fold angles and intrinsic lengths are not constrained.

## IAAC public flow and ASTRA boundary

[IAAC Mesh Subdivision](https://www.iaacblog.com/programs/mesh-subdivision/) publishes two process diagrams: one moves vertices in/out relative to a fractal domain; the other searches an outside grid and attracts interior samples. They also discuss attractor curves and subdivision variants. The diagrams do not specify a complete executable implementation. The public process images are cached on E for inspection, not republished in our review package.

F reuses CHESHIRE's existing finite Mandelbulb classifier and nearest-outside grid. Its chosen powers, transforms, step budgets and feature masks are our parameters. One exact midpoint subdivision precedes two field passes; the second pass uses fixed topology. This is a bounded reconstruction of a published principle, not the IAAC original equations recovered verbatim.

The preserved `CHESHIRE_ASTRA/docs/ASTRA_RESEARCH_RESULTS.md`, `astra_dual.py`, and `astra_rotating.py` were read. That study already reports later-generation stagnation, and distinguishes interpolation from the weighted-minus-neutral-CC offset. ASTRA is retained, not rerun or claimed to power these new candidates. Its warning is relevant: more subdivision and surviving macro landmarks alone do not establish new deep child folds.
