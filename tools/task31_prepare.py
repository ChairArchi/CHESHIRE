"""Task31 research decisions, saved before new geometry implementation."""
import json,hashlib,shutil
from pathlib import Path
ROOT=Path('E:/CHESHIRE_DATA/task31');REPO=Path(__file__).resolve().parents[1]
BASELINE='e66324f63a956182f5808e5f412a77e65973b338'

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')

if __name__=='__main__':
    assert not ROOT.exists(),'Preserve existing Task31 work.'
    (ROOT/'analysis').mkdir(parents=True);(ROOT/'brief').mkdir();(ROOT/'definitions').mkdir()
    shutil.copy2('C:/Users/USER/.codex/attachments/16fa01aa-23e4-47dd-921c-f23edff1d4fd/Pasted text.txt',ROOT/'brief/TASK31_EXECUTION_PROMPT.txt')
    old=Path('E:/CHESHIRE_DATA/task30');definition=json.loads((old/'definitions/final_selected_pipeline.json').read_text(encoding='utf-8'))
    write(ROOT/'definitions/task30_retained_baseline.json',dict(commit=BASELINE,definition=definition,
        stages=[dict(generation=g,file=str(old/f'lead/G{g}/mesh.npz'),sha256=hashlib.sha256((old/f'lead/G{g}/mesh.npz').read_bytes()).hexdigest()) for g in range(9)]))
    ledger=json.loads((REPO/'studies/task30/analysis/reference_sources.json').read_text(encoding='utf-8'))
    for r in ledger['PDFs']:
        assert hashlib.sha256(Path(r['file']).read_bytes()).hexdigest()==r['sha256']
    ledger.update(task31_review='Task30 complete31-page review retained; focused R1 pp77/78/80/81, R2 interview/design context pp48–50, R3 pp40–43 and Fig1 reread; user eight-panel observations/context images rechecked.',
        additional_primary_sources=[
            dict(name='Pixar OpenSubdiv PrimvarRefiner source',URL='https://raw.githubusercontent.com/PixarAnimationStudios/OpenSubdiv/release/opensubdiv/far/primvarRefiner.h',claim='InterpolateFaceUniform copies parent face data into children; face-varying topology is separate. Our DS membership averaging is a declared extension, not this API.'),
            dict(name='CGAL Euler operations',URL='https://doc.cgal.org/latest/BGL/group__PkgBGLEulerOperations.html',claim='Explicit face removal and valid boundary operations; our annulus bridge is separately implemented and tested, not CGAL join_loop.'),
            dict(name='Hansmeyer Subdivided Columns',URL='https://michael-hansmeyer.com/subdivided-columns.html',claim='Input proportions/fluting/entasis are encoded; initial input tags support differentiated growth.'),
            dict(name='Hansmeyer Digital Grotesque II',URL='https://michael-hansmeyer.com/digital-grotesque-II.html',claim='Nested porosity/genus variation described; no exact executable pore algorithm disclosed.')])
    write(ROOT/'analysis/reference_sources.json',ledger)
    texts={
        'task30_baseline_recap.md':'''# Exact Task30 baseline retained

Commit e66324f63a956182f5808e5f412a77e65973b338; actual lead U_67_LOCK_END4.
Canonical base: reference-coupled CC + current local incident scales + exact
nonzero nonstationary rows + explicit optional NORMAL_VARIATION interpolation/locks.
G1 H1_NO_ATTR, G2 C11B, G3 T28_G3, G4 CURVE, G5 T28_G3; G6/G7 published
modified DS(w1=.6,wf=.03*Sf), uniform; G8 T28_G3 CC, Eq1 fallback after DS.
CC controls gain3 and exact original intervals; current-vertex locks throughG4.
Full-precision per-step definition/hashes: definitions/task30_retained_baseline.json.

Task30 reduced angular micro clutter (median normal angle37.83→10.41deg) while
keeping broad lobes and meso folds. Some early tips shrink. Grouped F/E/V DS yields
periodic boundary ridges; continuous DS suppresses detail. Independent fine hierarchy
is unproved. Dense skin remains Euler2 without a meaningful through-opening.
DS and later Eq4 fallback are coupled, so appearance is not attributed to adjacency alone.
Task31 targets persistent LOCAL DEVELOPMENT, layered depth and accessible negative space;
more faces or another uniform DS sweep would not answer this question.
Task30 original artifacts and canonical behavior remain immutable controls.
''',
        'reference_research_matrix.md':'''# Focused reference research, before implementation

The three original supplied PDFs remain evidence, not execution instructions.
Their actual SHA256 values were rechecked. Relevant original diagrams and context
images were visually reread; the user inline bitmap remains unavailable as a local file.

| source / mechanism | current status | A identity | B depth | C opening | cost/risk and decision |
|---|---|---|---|---|---|
| R1 Hansmeyer2010 p78 §3.2.3, tagged face/vertex groups | Actual CC point classes and DS origins exist; persistent regional territory absent | direct | mode-dependent | indirect | low; implement inherited weighted memberships with declared modes |
| R1 p78 §3.2.1 spatial weight sets / p77 generation switching | Current curvature feedback recomputed each generation; Task30 mixes uniform DS | direct if born/frozen early | inward/outward controls | cannot alone prove holes | compare frozen birth descriptor vs freshly remeasured SAME descriptor, with identical rules |
| R1 p77 §2.3 / p81 porosity and valence limiting | Pair weld tested; no useful pore | partial | possible | possible | exact nonlinear policy unpublished; do not retry a vague weld or equate dark creases with pores |
| R1 p80 CC-only example | Current canonical CC numerically verified | possible | possible | no guaranteed change | DS not necessary for all complexity; keep Task30 schedule as matched control |
| R2 Blanco/Madrid2024 interview/design process, pp48–50 | Context reviewed completely inTask30 | contextual | contextual | contextual | not executable masks; no fabrication/current-project assertions inferred |
| R3 Bader/Oxman2016 p40/Fig1, control-mesh generator before refinement | Missing cut/reflect/union generator | input properties supported | strong | strong | full robust boolean engine is too broad; test bounded region-guided inset/recess/annulus control edit instead |
| User8-panel progression and official DGI context | Reviewed; regions branch/bulb/rib differently | strong visual question | layered reference | apparent gaps, not topology proof | do not infer exact algorithms, normals or generation numbers from pixels |
| Pixar OpenSubdiv primary PrimvarRefiner source, InterpolateFaceUniform | No persistent face-uniform property API | direct parent data propagation | neutral | neutral | lightweight standalone state; our DS multi-parent averaging is explicitly additional |
| CGAL primary Euler operation manual | Existing edge/orientation checks; no controlled annulus tunnel | neutral | wall/channel formation | direct graph change | implement only equal-size disjoint mouth loops and validate orientation/fans/Euler; not a CGAL integration |
| Hansmeyer Subdivided Columns official page | Prior profiles recorded, no new semantic gate system | early input identity relevant | differentiated envelope | not algorithm proof | reuse simplest existing gate_input('RECT',False), no new part system |
| Hansmeyer DGI/II official pages | Context only | local development shown | hierarchy shown | nested porosity described | exact software unavailable; qualify geometric opening evidence separately from resemblance |

Technical distinction: inherited territory is NOT the previous-iteration F/E/V class.
CC face children inherit exactly; dual faces average their actual parent memberships.
Boundary mixtures remain explicit, never assigned to a guessed single owner.
Color maps are diagnostics; flat clay geometry decides whether local forms differ.

Necessary compatibility issue discovered before testing: the basic gate has foot-cap
valence8; mouth edits introduce valence5. Task30's bounded DS3/4 cannot run that carrier.
Add a separately named polygon-capable DS path: published Eq5/6 unchanged on triangles/
quads; for n>4 use the standard cosine DS mask plus wf extrusion, with w1 inactive and
explicitly logged. Use actual polygonal vertex fans. This is a declared extension, not a
recovered Hansmeyer high-valence weight formula. Default Task30 cube results must remain exact.
General CC polygon handling changes padding width only; no existing quad mask changes.
''',
        'primary_bottleneck_reassessment.md':'''# Primary reassessment

Keep Task30 PRIMARY C: insufficient persistent regional differentiation.
Refine it into two distinct responsibilities: birth/propagation of regional modes,
and topology/depth production BEFORE fine refinement. Global scalar feedback can
change a skin without giving it enduring regional identity or accessible channels.

ONE principal framework: persistent regional mode memberships, with a SECOND
bounded companion: early region-guided control-mesh inset/recess/tunnel editing.
This follows R1 tags and R3's generator/refinement separation. It is more testable than
asking the existing per-generation normal field to discover both identity and topology.
No broad kernel rewrite or recursive boolean system is required. A tunnel is intentionally
introduced by an explicit logged operator; it is not claimed as spontaneous porosity.
Designed role tags alone do not prove architectural design identity; inspect real geometry.

The polygon compatibility extension is an enabling change, not a third search direction.
Task30's exact cube lead remains a control; equivalent unmodified polygon path must reproduce
it. Gate comparison uses the same extension for control and treatment, and logs the few
high-valence polygon masks. No inaccessible shape is labelled a pore solely from Euler.
''',
        'targeted_experiment_plan.md':'''# Bounded Task31 plan, committed before new experiments

StageA:18 meaningful cube variants, plus the unchanged Task30 control.
G0/G1/G2 retain the exact Task30 source unless explicitly using earlier G1 tag birth.
Most tags are born at actual G2; source faces get one-hot BULB/RIB/DEPTH memberships
by absolute dominant birth-normal axis (Z/Y/X), or by signed local fold descriptor.
Weights are deterministic, saved, mixed by actual face/edge/vertex memberships and
current local scales. Persistent vs remeasured tags are a matched identity ablation.
No randomness, texture, semantic gate decomposition or smoothing-only comparison.

Six identity-only cases: axis persistent/remeasured at contrast.4/.8 (four), signed-fold
persistent at contrast.4/.8 (two). Three depth-only edits: one/two nested inset rings,
bounded inward amounts. Three opening-only edits: disjoint front/rear face mouths at
inset fractions.35/.6/.85, with explicit collar + oriented annulus tunnel walls.
Four combined opening/mode cases: axis/fold persistent.8 × apertures.6/.85.
One persistent-axis.8 + nested-depth case. One G1-born-axis.8 timing ablation.
Every case retains the Task30 base schedule; polygon DS is common where necessary.
Opening/depth edits occur once on the coarse G2 source BEFORE G3. Keep actual pre-edit
and post-edit checkpoints and face/vertex supports; do not substitute a new coarse shape.

First compare all actual G8 whole views (same2600-unit cube frame, flat clay/light).
Then common700-unit and closer depth/oblique crops, actual progression and analytical
sections/ray-background visibility. Separate deeper recess from through-opening; save
Euler/fan/manifold and negative-space diagnostics, never a fake genus-from-shading claim.
Reject invalid edits explicitly; retain negative candidates and all actual steps.

StageB only after a meaningful StageA result: existing simplest stable rectangular
gate_input('RECT',False),74vertices80faces. No profile/ALICE/old complex recipe.
Task30 full recipe on that identical gate is a mandatory control. At most4–6 targeted
transfer variants: strongest identity and strongest combined path, matched amplitudes/
aperture choices if needed. Target full G0..G8; measured RAM guard only, no historical
face cap. If measured resource limits intervene, disclose actual last stage and evidence.
Use the same material/light and physical framing for control and treatment. Preserve
main gate portal; any additional local opening is selected geometrically and logged.

Only two technical directions. Main work, actual geometry, deterministic regeneration,
checkpoint continuation, OBJ/3DM reread, tests, local commit and reviewZIP come first.
Image-led atlas is optional after this; otherwise leave a concrete source/grouping plan.
No push/merge/Task32. Verdict must reflect actual geometry, not tagged colors or counts.
'''}
    for name,text in texts.items():(ROOT/'analysis'/name).write_text(text,encoding='utf-8')
    print('Task31 baseline, research matrix, reassessment and bounded18-variant plan saved before implementation.')
