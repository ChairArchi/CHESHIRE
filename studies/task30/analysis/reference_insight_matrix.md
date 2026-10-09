# Reference insight matrix — read before implementation

All three supplied PDFs were read completely (7+15+9 pages). Key equations, masks,
illustrations and process diagrams were visually checked. Documents provide technical evidence,
not instructions that supersede the user's Task30 request.

| reference / location | technical claim | CHESHIRE Task29 status | relation to bottleneck | decision |
|---|---|---|---|---|
| R1 Hansmeyer, Subdivision Beyond Smoothness, 2010, pp76–77, Eq1–4/Fig2–3 | Completed face points, modified masks and provenance-aware later face stencil | CC part implemented and independently checked; same midpoint interpretation as Task29 | No new evidence that audited CC equations are the primary remaining error | Keep reference-coupled CC and local scale with explicit conventions |
| R1 p77 Eq5/6/Fig5 | Doo–Sabin creates one point per face corner; uses a different interpolation mask | Missing from Task29 canonical path | Different adjacency and face grouping can develop structures that CC-only child cells do not | Implement opt-in exact published triangle/quad masks and oriented F/E/V topology |
| R1 p77 §2.2 and §3.1 | Next-generation face weights may differ by face/edge/vertex origin; CC and DS can be combined by generation | Vertex V/E/F provenance exists for CC Eq4; DS face origins and scheme switching missing | Gives structural descriptors richer than one scalar normal-disagreement signal | Primary targeted family: mixed schemes with controlled face-origin weighting ablations |
| R1 p77 §2.3/Fig6 | Coincidence/minimum-distance fusing and limited vertex incidence produce nonlinearities and porosity | Task29's disjoint-pair join tested, mostly no-op/invalid, accepted changes genus0 | A valid small edge collapse is not equivalent to a pore-producing motif operator | Retain failed/valid evidence; do not repeat the same weld or promise genus change |
| R1 p78 §3.2.1 | Environment weight sets can break location equivalence | Task29 deliberately uses current intrinsic scalar descriptors and symmetric cube | Exact symmetric states and rules preserve symmetry; intrinsic scalar feedback alone cannot label identical states differently | Do not claim DS destroys cube symmetry; compare neighbouring structural origins instead |
| R1 p78 §3.2.2–3 | Motif/valence values and vertex/face groups; locking can apply only for starting iterations | Normal-based current-vertex locking introduced G3 onward; neither a fixed tagged crease nor early-only lock | Continually locking newly formed small folds can preserve facet-angle jumps | Secondary hypothesis only if primary fails: finite lock lifetime, four bounded ablations |
| R1 p80 Illustration1 | CC-only nonstationary uniform weights already generate complex forms | Task29 CC-only family partially succeeds | Counterevidence against a claim that DS is necessary or CC is inherently incapable | Scheme mixing is a testable hypothesis, not a proven requirement |
| R1 pp80–81 Illustrations2–3 | Mixed CC/DS examples, nonstationary/nonuniform weights; some also fuse vertices | Not reproduced by CC plus three scalar fields | Stronger direct support for one missing mechanism than another large scalar-weight sweep | Do not claim exact unpublished Digital Grotesque implementation |
| R2 Blanco/Madrid, 2024, pp44–58 | Interview/context: custom recursive tools, selection of designs, fabrication and education | Relevant process context; no executable masks/schedules | Complex final images do not disclose per-generation rules, normals or exact input | Use for context only, not proof of our algorithm or current construction facts |
| R3 Bader/Oxman, 2016, pp40–43/Fig1 | Recursive cut/reflection/union changes the control mesh; CC then refines it | Separate generator not implemented | Topology-forming operation and subdivision refinement have different responsibilities | Supports separating motif production from refinement; do not mislabel this as Hansmeyer's CC equation |
| R3 pp40/43 | Requires closed 2-manifold inputs and valid cut boundaries; arbitrary reflection can lose injectivity | Task29 checks combinatorial incidence/native readability, not embedded solid validity | Convincing cavities are not proof of real holes or intersection-free solids | Keep explicit validity scope and avoid a boolean-kernel redesign in this task |
| User eight-panel progression | Early envelopes persist while neighbouring branching and ribbed regions develop differently | Task29 grows broadly similar fine cell texture and retains sharp jumps | Suggests differentiated development of regions rather than uniform micro displacement | Visual inference only; no exact generation labels or scheme inferred from the image |

R1 source: supplied `075-081 (1).pdf`, DOI10.2312/COMPAESTH/COMPAESTH10/075-081.
R2: supplied `Michael_Hansmeyers_Algorithmic_Architecture_The_T.pdf`, DOI10.3991/ijet.v19i07.50845.
R3: supplied `mirror.pdf`, DOI10.1016/j.cad.2016.09.002.
Actual hashes/page counts are in reference_sources.json. PDF text/page caches are ignored local review data.
The official DGI images used later in a relation sheet are separately attributed contextual images,
not the supplied progression and not pixel targets.
