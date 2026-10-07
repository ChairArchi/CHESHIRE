"""Bounded Task30 reference study. Preserve Task29 and actual lineage."""
import argparse,hashlib,json,shutil,sys,copy
from time import perf_counter
import numpy as np
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
from cross_cell_crease_study import read,write,file_hash
from task29_search import load_mesh,save_mesh
from cheshire.reference_subdivision import subdivide,LOCAL_INCIDENT_SCALE
from cheshire.dual_subdivision import doo_sabin,REFERENCE_DOO_SABIN
from cheshire.subdivision_pipeline import SubdivisionState,step
from hero_design_sprint import guarded
ROOT=Path('E:/CHESHIRE_DATA/task30')
PREVIOUS=Path('E:/CHESHIRE_DATA/task29')
BASELINE='c71ac1f9961a45a16dd454dcf2d9f624153a8e6a'


def definitions():
    old=read(PREVIOUS/'definitions/selected_nonstationary_schedule.json')
    groups=dict(moderate=dict(FACE=dict(w1=.85,wf=.03),EDGE=dict(w1=-.1,wf=-.02),VERTEX=dict(w1=.5,wf=.065)),
        strong=dict(FACE=dict(w1=1.1,wf=.035),EDGE=dict(w1=-.3,wf=-.04),VERTEX=dict(w1=.6,wf=.09)))
    def make(name,ds,group=None):
        steps=[]
        for g,row in enumerate(old['rows'],1):
            steps.append(dict(generation=g,scheme=REFERENCE_DOO_SABIN,weights=dict(w1=.6,wf=.03),groups=groups.get(group,{}),scale=LOCAL_INCIDENT_SCALE) if g in ds else
                dict(generation=g,scheme='REFERENCE_COUPLED',row=copy.deepcopy(row),intrinsic=copy.deepcopy(old['intrinsic']),scale=LOCAL_INCIDENT_SCALE))
        return dict(id=name,steps=steps,ds_generations=ds,group_policy=group or 'uniform',prefix_source=str(PREVIOUS/'lead/G3'),
            justification='Matched structural face-origin policy' if group else 'Isolate early/late/consecutive/interleaved scheme roles')
    variants=[make('U_'+''.join(map(str,ds)),ds) for ds in ([4],[6],[4,5],[6,7],[4,6,8],[4,5,6,7,8])]
    variants += [make(('M_' if group=='moderate' else 'S_')+''.join(map(str,ds)),ds,group) for ds in ([4,5],[6,7],[4,5,6,7,8]) for group in groups]
    return variants


def experimental_step(m,roles,spec):
    current,meta,state=step(SubdivisionState(m,roles),spec)
    return current.mesh,current.face_roles,meta,state


def prefix(dest,last):
    for g in range(last+1):
        src=PREVIOUS/f'lead/G{g}';d=dest/f'G{g}';shutil.copytree(src,d)
        m=load_mesh(d);roles=np.full(len(m.faces),-1,np.int8)
        np.savez_compressed(d/'face_roles.npz',face_roles=roles)
        summary=read(d/'summary.json');summary['source_checkpoint']=dict(path=str(src),sha256=file_hash(src/'mesh.npz'))
        summary['parent']=str(dest/f'G{g-1}') if g else None
        summary['parent_mesh_sha256']=file_hash(dest/f'G{g-1}/mesh.npz') if g else None
        write(d/'summary.json',summary)
    return m,roles


def generate(variants,tag):
    log=[]
    for spec in variants:
        dest=ROOT/'candidates'/spec['id'];m,roles=prefix(dest,3);times=[]
        for step in spec['steps'][3:]:
            start=perf_counter();parent=dest/f'G{m.generation}'
            m,roles,meta,state=experimental_step(m,roles,step)
            d=dest/f'G{m.generation}';summary=save_mesh(d,m,meta,state,parent)
            np.savez_compressed(d/'face_roles.npz',face_roles=roles)
            summary.update(seconds=perf_counter()-start,parent_mesh_sha256=file_hash(parent/'mesh.npz'),definition=step,
                operator_state_sha256=file_hash(d/'operator_state.npz'),face_roles_sha256=file_hash(d/'face_roles.npz'))
            write(d/'summary.json',summary);times.append(summary['seconds'])
        log.append(dict(id=spec['id'],definition=spec,stage_seconds=times,final=summary))
        write(ROOT/f'analysis/{tag}_experiment_log.json',log)
        print(spec['id'],summary['vertices'],summary['faces'],round(summary['dihedral_median'],2),flush=True)
    return log


def primary():
    prefix(ROOT/'controls/task29',8)
    v=definitions();write(ROOT/'definitions/task30_variant_definitions.json',v)
    generate(v,'primary')


def requests(tag,ids=None):
    variants=read(ROOT/'definitions/task30_variant_definitions.json')
    ids=ids or [v['id'] for v in variants]
    items=[dict(label='TASK29 G8 / control',stage=str(ROOT/'controls/task29/G8'))]
    items += [dict(label=i+' G8',stage=str(ROOT/f'candidates/{i}/G8')) for i in ids]
    write(ROOT/f'definitions/render_{tag}.json',dict(resolution=1400,width=2600,items=items,cols=4,size=850,pages=20,
        sheet_name='TASK30_targeted_variants.png' if tag=='primary' else f'TASK30_{tag}_variants.png'))


def detail_request(ids,tag):
    roots=[('TASK29',ROOT/'controls/task29')]+[(i,ROOT/'candidates'/i) for i in ids]
    items=[dict(label=f'{name} G{g} / 700 units',stage=str(path/f'G{g}'),width=700,target=[0,-350,0],angles=[0,0]) for name,path in roots for g in (3,5,8)]
    write(ROOT/f'definitions/render_{tag}.json',dict(resolution=1600,width=2600,items=items,cols=3,size=1000,pages=24,
        sheet_name=f'TASK30_{tag}.png'))


def decision():
    observations={
        'U_4':'Early dual step changes the meso outline slightly; later CC restores dense repeated angular micro texture.',
        'U_6':'One late dual step modestly reduces clutter; subsequent CC still repeats small folded cells.',
        'U_45':'Two early dual steps round meso tips; fine CC texture returns.',
        'U_67':'Two late dual steps preserve more of the prefix while reducing facet clutter; no independent fine hierarchy.',
        'U_468':'Interleaving further suppresses fine texture; recurring larger boundaries remain.',
        'U_45678':'Continuous uniform dual nearly removes new small structure; low angles are not generative success.',
        'M_45':'Origin contrast seeds busier surface texture, still cell-associated.',
        'S_45':'More angular early motifs and repeated dense descendants; no convincing non-repetition.',
        'M_67':'Matched U_67 gets sharper narrow ridges, not meaningfully richer independent regions.',
        'S_67':'Strong late origin contrast increases angular clutter.',
        'M_45678':'Broad facets joined by repeated narrow boundary ridges; distinct group response but poor fine development.',
        'S_45678':'Amplified spikes and broad facets; excessive contrast, not nested growth.',
        'CC_LOCK_END3':'Rounds early tips but retains spiky repeating fine cells.',
        'CC_LOCK_END4':'Preserves more prefix detail than END3; still dense angular fine repetition.',
        'U_67_LOCK_END3':'Less angular micro clutter, but more early rounding than END4.',
        'U_67_LOCK_END4':'Selected limited-advance lead: legible macro/meso, calmer fine facets and connected narrow fold bands; repeated descendants remain.'}
    logs=read(ROOT/'analysis/primary_experiment_log.json')+read(ROOT/'analysis/secondary_experiment_log.json')
    for r in logs:r['visual_assessment']=observations[r['id']]
    write(ROOT/'analysis/targeted_experiment_log.json',dict(primary_direction='Published CC/DS mixing + matched F/E/V origins',
        secondary_direction='Finite lifetime of current-fold locking',new_variant_count=16,control_count=1,new_geometry_stages=80,
        prefix='All variants reuse exact actual Task29 G0..G3, copies separately hashed; no regenerated alternative prefix.',records=logs,
        reviewed='All whole-view contact cards and individually enlarged promising/negative cases; common G3/G5/G8 700-unit details for five primary and all four secondary variants.'))
    final='''PARTIAL

# Final decision — targeted mechanism and limits

Selected actual lead: **U_67_LOCK_END4**, G0..G8. G0..G3 are byte-identical
Task29 states. G4/G5 retain exact base CC rows with original intrinsic interpolation;
current-fold locks apply through G4 only. G6/G7 use modified published Doo–Sabin
Eq5/6 (w1=.6,wf=.03*current local Sf), uniform, no external relaxation.
G8 returns to the exact Task29 nonzero row and intrinsic interpolation with no locks.
Its prior DS corners deliberately lack CC V/E/F vertex classes, so Eq4 falls back
to Eq1 for that step. No fake provenance. F/E/V face origins and every multi-parent
support are saved; grouped DS weighting was tested, but is not in the selected lead.

The primary direction was D: connectivity vocabulary, tested by12 mixed/structural
variants. It did NOT establish non-repetitive micro growth. After this controlled
negative result the FINAL PRIMARY working diagnosis is **C — insufficient intrinsic
spatial differentiation**, especially missing persistent region/motif distinctions.
D is a useful missing operator but not demonstrated as the main remaining cause;
E (periodic role weights) and current-lock lifetime interact. This is a diagnosis
from bounded negative evidence, not a proof that a particular unimplemented descriptor
would solve the target. No third direction was attempted. Initial D diagnosis is retained
verbatim for audit; this explicit revision supersedes it for the current project state.

R1 p77 supports mixing and origins; p78 supports early-only locks. R1 p80's CC-only
example rules out declaring DS necessary. R3 separates a motif-producing control-mesh
operation from CC refinement; no such boolean generator is claimed here. R2 supplies
process context rather than exact parameters. The eight-panel user image shows regionally
different development; exact schemes, generations and display normals are unavailable.

Compared with Task29, the selected fixed-scale flat-normal crop has fewer dense angular
micro clusters and clearer continuous narrow fold bands. Broad protrusions and G2/G3-scale
articulation remain legible, though early tips shrink and sharp small creases are subdued.
Small-cell repetition is visually reduced in prominence, NOT broken as a generative
mechanism. Persistent non-repetitive fine hierarchy and genuinely richer late local
development remain UNPROVEN. Lower normal angles cannot distinguish richer development
from suppression; the continuous-DS negative control demonstrates this directly.

Keep reference-coupled CC + local incident scales + exact nonzero nonstationary schedule
as the canonical base. Keep Task29 lead as an immutable control. Add explicit opt-in
scheme dispatch and face-origin/multi-parent state for reproducible mixed lineages.
Do not replace every client with the selected recipe. Legacy boundary/crease kernels
remain compatible; Task29's large orchestration and tested pair weld are archived research.
Task30 has16 new meaningful variants plus one unchanged control,80 actual new G4..G8
steps. No broad sweep, gate, random noise, smoothing cleanup or Task31.

Validity scope: finite double coordinates; closed oriented two-face incidence and
cyclic DS fans; Euler2 throughout. DS changes combinatorial adjacency, not genus:
no pores, vertex fusion or cut/reflect/union operation. The bounded DS implementation
accepts only triangles/quads and input valence3/4, rejects other cases explicitly.
Native readability is not a proof of an intersection-free solid or fabrication readiness.
See actual progression, matched detail/ablation images and validation logs for evidence.
'''
    (ROOT/'analysis/final_decision.md').write_text(final,encoding='utf-8')
    p=ROOT/'analysis/primary_bottleneck_diagnosis.md'
    p.write_text(p.read_text(encoding='utf-8')+'\n\n## Post-experiment revision\n\nFinal PRIMARY: **C**, superseding tentative D after the bounded mixed-scheme tests failed to produce independent fine hierarchy. Structural origins alone are periodic and insufficient. See final_decision.md for the evidence and epistemic limits.\n',encoding='utf-8')


def secondary(best):
    (ROOT/'analysis/primary_visual_decision.md').write_text('''# Primary-family decision before secondary tests

All 12 actual G8 whole views were reviewed. Common 700-unit G3/G5/G8 crops
were reviewed for U_67, U_468, M_67, M_45678 and U_45678 with Task29.
Uniform G6/G7 DS (U_67) retains the broad envelope and meso folds with less
angular clutter; fine folds still track recurring cells. U_468 suppresses more
detail; continuous uniform DS nearly removes micro growth. M/S continuous DS
produce large facets and narrow repeated boundary ridges; more extreme groups
amplify spikes, not independent nested development. Matched M_67 vs U_67 adds
fine ridges but does not establish a qualitatively richer motif hierarchy.

Primary D hypothesis is NOT sufficient in this tested family. No success claimed
from angle reduction. Select U_67 as the controlled mixed base for the one allowed
secondary direction: stop re-evaluated current-fold locks after G3 or G4, retaining
the intrinsic interpolation and nonzero schedule. Compare both against identical
CC-only lock-lifetime variants. Exactly four new variants, total16.
This timing hypothesis follows R1 p78 early-only locks; it is not an exact recovered
Digital Grotesque setting. Scope remains bounded; no third direction will run.
''',encoding='utf-8')
    v=read(ROOT/'definitions/task30_variant_definitions.json');mixed=next(x for x in v if x['id']==best)
    control=definitions()[0];control['ds_generations']=[]
    old=read(PREVIOUS/'definitions/selected_nonstationary_schedule.json')
    control['steps']=[dict(generation=g,scheme='REFERENCE_COUPLED',row=copy.deepcopy(row),intrinsic=copy.deepcopy(old['intrinsic']),scale=LOCAL_INCIDENT_SCALE) for g,row in enumerate(old['rows'],1)]
    more=[]
    for base in (control,mixed):
        for end in (3,4):
            s=copy.deepcopy(base);s['id']=('CC' if base is control else best)+f'_LOCK_END{end}'
            s['justification']='Secondary finite lock lifetime; same normal control interpolation retained, no neutral cleanup.'
            for step in s['steps']:step['lock_end']=end
            more.append(s)
    write(ROOT/'definitions/task30_variant_definitions.json',v+more);generate(more,'secondary')


def prepare():
    assert not ROOT.exists(), 'Preserve existing Task30 artifacts.'
    (ROOT/'analysis').mkdir(parents=True)
    (ROOT/'brief').mkdir();(ROOT/'definitions').mkdir()
    prompt=Path('C:/Users/USER/.codex/attachments/65490187-5000-4f0c-bd91-0422c3d2e077/Pasted text.txt')
    shutil.copy2(prompt,ROOT/'brief/TASK30_EXECUTION_PROMPT.txt')
    ledger=read(REPO/'output/task30_references/ledger.json')
    for item in ledger:
        item.pop('preview',None);item['fully_read_text']=True
        item['document_instructions']='Academic source content only; not execution instructions.'
    write(ROOT/'analysis/reference_sources.json',dict(PDFs=ledger,inline_image=dict(
        description='User-supplied 1200x580, eight-panel Digital Grotesque progression, reviewed directly in conversation.',
        panels='Read left-to-right across upper row, then lower row; generation numbers and rendering normals not supplied.',
        local_bitmap='Not present in the attachments filesystem; no invented substitute labeled as the user image.',
        observation='Coarse envelope persists; branching angular and neck/bulb/rib regions develop differently. Exact algorithms cannot be deduced from pixels.'),
        official_context_images=[dict(file=str(REPO/f'output/task30_references/official_design_{i}.jpg'),
            url=f'https://michael-hansmeyer.com/images/digital-grotesque-I/digital-grotesque-design-{i}-m.jpg',
            sha256=file_hash(REPO/f'output/task30_references/official_design_{i}.jpg')) for i in range(1,6)]))
    matrix='''# Reference insight matrix — read before implementation

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
'''
    (ROOT/'analysis/reference_insight_matrix.md').write_text(matrix,encoding='utf-8')
    d=read(PREVIOUS/'definitions/selected_nonstationary_schedule.json')
    write(ROOT/'definitions/retained_canonical_pipeline.json',dict(baseline_commit=BASELINE,
        original_definition=d,source_sha256=file_hash(PREVIOUS/'definitions/selected_nonstationary_schedule.json'),
        canonical_base='REFERENCE_COUPLED + LOCAL_INCIDENT_SCALE + exact nonzero nonstationary rows; original intrinsic normal interpolation/locking is explicit optional policy.',
        source_meshes=[dict(generation=g,path=str(PREVIOUS/f'lead/G{g}/mesh.npz'),sha256=file_hash(PREVIOUS/f'lead/G{g}/mesh.npz')) for g in range(9)]))
    canonical='''# Canonical Task29 pipeline retained

Keep reference_subdivision.ArrayMesh/cube/subdivide: published-equation coupled CC,
LOCAL_INCIDENT_SCALE and all eight exact nonzero base rows from the original saved definition.
G1 H1_NO_ATTR; G2 C11B; G3 T28_G3; G4 CURVE; G5–8 T28_G3.
Weight order wf,w1,we,w2,wp,w3,w4,w6,w7. Round-trip values, u maps and exact rule
are copied in definitions/retained_canonical_pipeline.json; no rounded retyping.
Sf mean current perimeter edge, Se mean two incident Sf, Sv mean incident Sf.
Original endpoint midpoints feed Eq3; completed faces feed Eq2/3; Eq4 uses actual prior classes.

For exact Task29 lead reproduction retain its optional G3+ NORMAL_VARIATION rule,
gain3, threshold.12 and all declared control intervals. It is required for exact replay of
FINAL_DX00, not established as essential for every useful generated form.
The basic audited operator and nonzero schedule are canonical; locking is an optional
retention policy with a known sharp-facet tradeoff. Preserve every actual state and flat render.

Legacy weighted/generational/sharp kernels remain unchanged for historical replay and controls;
their boundary/crease clients still have legitimate uses outside this cube benchmark.
The 480-definition Task29 orchestration is archived research tooling, not the minimal pipeline.
The tested minimal pair weld is a dead end for this particular porosity/micro-motif hypothesis;
keep its evidence, keep it opt-in, and do not call every future topology mechanism disproven.
No Task29 source recipe, checkpoint or rejected proposal is discarded.

Smallest path: exact cube → exact eight-step definition → reference/local kernel plus
declared optional policy → hashed actual checkpoints → flat fixed framing → exact OBJ/3DM reread.
Task30 will add one explicit operator selection and its actual face-origin state if justified;
it will not silently change reference_subdivision's existing default results.
'''
    (ROOT/'analysis/canonical_task29_pipeline.md').write_text(canonical,encoding='utf-8')
    diagnosis='''# Primary bottleneck diagnosis, before targeted tests

PRIMARY: **D — insufficient differentiation of connectivity motifs**.
This means the combinatorial vocabulary used by the current CC-only lineage,
not a claim that genus change is mandatory. C (weak descriptor diversity) and E
(same late regime) are interacting secondary factors. A/B were addressed in Task29;
the new references provide no direct evidence that its checked CC dependency/scalar
interpretation is the primary remaining error.

Task29: macro/meso persist, all eight modified steps are nonzero, but G8 fine texture is
strongly cell-related and median adjacent-normal angle is37.83°. Its three accepted
welds alter valence without useful porosity or visibly new nested motifs.

R1 p77 explicitly permits scheme switching and weights by Doo–Sabin face/edge/vertex
origin; pp80–81 show mixed-scheme results. These are missing from the canonical path.
The user progression shows adjacent regions with different modes of development:
angular branching alongside converging necks/ribbed bulges. This supports the question
of differentiated local development, but cannot identify its exact implementation.
R3's separate recursive cut/reflection generator demonstrates a distinct way to change
motifs before refinement; it is an alternative, not evidence that Hansmeyer used it.
R2 provides context rather than mathematical proof.

Hypothesis: a bounded CC↔DS schedule, with persistent structural F/E/V face-origin
groups and exact published DS corner masks, can create more meaningful differences
between neighbouring descendant regions than continuously changing scalar offsets
on the same CC lattice. DS is not inherently required (R1 p80 has CC-only results).
A changed appearance alone will not verify the hypothesis. Flat same-scale whole
views, same physical detail crops, actual progression and matched uniform/grouped
ablations must show less uniform small structure with earlier folds still readable.
'''
    (ROOT/'analysis/primary_bottleneck_diagnosis.md').write_text(diagnosis,encoding='utf-8')
    plan='''# Targeted experiment plan — bounded before implementation

Primary direction: published mixed Catmull–Clark / Doo–Sabin subdivision, with
actual DS F/E/V face-origin groups as the optional differentiating rule.
This prioritizes a missing published mechanism over another scalar-field sweep.
It is allowed under the prompt's better-reference-grounded-method clause.

All variants start from the exact Task29 G3, preserving G0/G1/G2/G3 and its scale.
Untouched Task29 G0–G8 is the control. Existing CC rows and normal/lock policy
remain identical whenever a step is CC. No all-zero CC cleanup or external smoothing.

12 meaningful variants: six uniform DS schedules (G4, G6, G4–5, G6–7,
G4/6/8, G4–8), plus six matched face-origin schedules (G4–5, G6–7,
G4–8; each with moderate/strong declared contrast).
Uniform DS uses w1=.6 and wf=.03 times current local face scale.
Moderate F/E/V groups: (.85,.03),(-.1,-.02),(.5,.065).
Strong groups: (1.1,.035),(-.3,-.04),(.6,.09).
The first DS step has unknown face origin, so uses the same uniform default.
Matched grouped/uniform pairs therefore isolate later structural-origin effects.
The intervals bracket the neutral published DS masks and add bounded alternating
extrusion signs; they are hypotheses, not recovered unpublished DG settings.

DS Eq5/6 are checked independently on closed skew cubes/tetrahedra. Actual F/E/V
connectivity is validated for opposite edge orientation, closed vertex fans and Euler2.
The bounded implementation rejects input valence outside3/4; no hidden polygon conversion.
After DS, CC Eq4 lacks V/E/F vertex provenance and must explicitly use Eq1 for
that first CC step, then restore real provenance for the next; never fake eligibility.
Multi-parent DS face ancestry is saved rather than fabricated as a single parent.

Actual G4–G8 states, fields and times are saved for every candidate. First render all
G8 candidates with one physical scale and flat normals; inspect promising candidates'
G4/G5/G6/G7 progression and 700-unit common crops before selecting.
If the primary family does not visibly improve the target, at most one secondary
direction is allowed: finite lifetime of current-fold locking (R1 p78 §3.2.3),
four exact ablations with lock endings G3/G4 on CC-only and the best mixed schedule.
Total new variants cannot exceed16 without an explicitly revised bounded rationale.
No recursive mirror/boolean system, broad random search or gate semantics is introduced.
'''
    (ROOT/'analysis/targeted_experiment_plan.md').write_text(plan,encoding='utf-8')
    print('References and pre-experiment canonical/diagnosis/plan saved FIRST.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--primary',action='store_true');p.add_argument('--secondary');p.add_argument('--requests');p.add_argument('--details');p.add_argument('--decision',action='store_true');p.add_argument('--ids',nargs='+');p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.prepare:prepare()
    elif a.requests:requests(a.requests,a.ids)
    elif a.details:detail_request(a.ids,a.details)
    elif a.decision:decision()
    elif a.worker:
        if a.primary:primary()
        elif a.secondary:secondary(a.secondary)
    else:
        args=['--primary'] if a.primary else ['--secondary',a.secondary]
        r=guarded(args+['--worker'],ROOT/'logs'/('primary' if a.primary else 'secondary'),worker_script=Path(__file__))
        print(r,flush=True);sys.exit(r['exit_code'])
