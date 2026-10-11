# Column detail: four supplied references

Read-only review, 2026-10-12. Page numbers below distinguish PDF pages from printed pages. This review adds no geometry, executable changes, or validated design result.

## Verified sources

1. **Michael Hansmeyer, _From Mesh to Ornament: Subdivision as a generative system_**, eCAADe 28 (2010), printed pp. 285-293. Local source: `C:/Users/USER/Downloads/ecaade2010_192.content.pdf`. PDF pp. 3-4 discuss nonstationary and nonuniform weights; pp. 6-7 / printed pp. 290-291 show motif-dependent compression/expansion, distance to original edges/vertices, and tagged locking. Figures 7-9 were visually inspected. Figure 7 starts with a differentiated 64-face column and varies intrinsic motif responses; it does not document Mandelbrot growth.

2. **Michael Hansmeyer, _Subdivision Beyond Smoothness_**, Computational Aesthetics (2010), pp. 75-81, DOI `10.2312/COMPAESTH/COMPAESTH10/075-081`. Local source: `C:/Users/USER/Downloads/075-081 (1).pdf`. PDF p. 3 / printed p. 77 separates face-, edge-, and vertex-derived Doo-Sabin families and defines iteration-dependent weights. PDF p. 4 / printed p. 78 specifies spatial influence sets, motif responses, and vertex/face groups; Figure 9 explicitly compares different locking durations. Figure 7-9 were visually inspected. This substantially overlaps source 1; these are not two independent replications.

3. **Christoph Bader and Neri Oxman, _Recursive symmetries for geometrically complex and materially heterogeneous additive manufacturing_**, Computer-Aided Design 81 (2016), pp. 39-47, DOI `10.1016/j.cad.2016.09.002`. Local source: `C:/Users/USER/Downloads/mirror.pdf`. PDF p. 2 / printed p. 40 describes cut, discard, reflect, Boolean union, largest-component selection, then Catmull-Clark refinement. Figure 1 on PDF p. 3 was visually inspected. Manifold output is conditional on the stated operations and nondegeneracy assumptions. This is a distinct coarse-form grammar, not a demonstrated solution to our crease-memory or repeated-grid problem.

4. **Sarah Mohammad Mansour, _Material's Perception Strategy in Terms of Adaptive Re-use Within the Computational, and Parametricism Context_**, IEREK (2019), DOI `10.21625/archive.v2i4.367`. Local source: `C:/Users/USER/Downloads/Materials_Perception_Strategy_in_Terms_of_Adaptiv.pdf`. PDF pp. 6-8 / printed pp. 270-272 discuss Digital Grotesque and fabrication. PDF p. 7, section 4.2.1 and Figure 7, was visually inspected. Its multiscale discussion is secondary description; it supplies no new subdivision recipe for this study.

## Consequences for the current column

CONTINUED G4 retained the large cavities but increased small grid/crust around necks and broad panels. More cycles alone did not demonstrate better hierarchy. Sources 1-2 support varying **where and when the weighting rules act**, rather than treating polygon count as progress. They do not prove that our finite Mandelbrot field, normal response, or crease preservation matches their implementations. None of these four papers establishes IAAC's exact equations.

Two bounded, untested next comparisons are justified:

1. Use existing regional controls with a nonstationary Task36 recipe: activate different shoulder/valley bands in successive cycles and leave quiet sectors. Compare against the identical input with the current repeated recipe. Changing response distribution, rather than only reducing its global amplitude, could interrupt repetitive cell growth; aesthetic benefit remains unverified.

2. Explicitly tag a small set of inherited fold bands and compare temporary protection with the same unprotected growth. Apply protection consistently across subdivision **and subsequent field movement**; `vertex_memory=1` during Task36 alone does not freeze vertices during the field pass. Source 1's graph-distance example and both papers' locking examples support this distinction. Selective protection is a proposal, not an implemented semantic crease-memory system.

Tooling: PyMuPDF 1.28.2 was installed only into `C:/Users/Public/Documents/ESTsoft/CreatorTemp/cheshire_pdf_deps`. Source PDFs were unchanged. Inspection PNGs remain in the private temporary `cheshire_pdf_review` directory; no copyrighted source figures or full text were copied into this repository.
