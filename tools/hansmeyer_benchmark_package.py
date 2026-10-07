"""Factual Task28 reports and checksum-verified actual-file review/model archives."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / 'examples'), str(REPO / 'tools')]
from cross_cell_crease_study import read, write, file_hash
from progressive_gate_package import archive
from hansmeyer_benchmark import BASELINE

TASK_FILES = ['examples/hansmeyer_benchmark.py', 'tools/hansmeyer_benchmark_views.py',
              'tools/hansmeyer_benchmark_evidence.py', 'tools/hansmeyer_benchmark_native.ps1',
              'tools/hansmeyer_benchmark_package.py', 'tests/test_hansmeyer_benchmark.py',
              'docs/TASK28_RESULTS.md', 'docs/TASK28_HANDOFF.md']


def reports(root):
    manifest = read(root / 'stage_manifest.json')
    perf = read(root / 'analysis/performance.json')
    native = read(root / 'dcc/lead_import_evidence.json')
    stages = [read(root / f'lead/G{g}/summary.json') for g in range(6)]
    assessment = dict(status='PARTIAL', lead='P4_C033_ZERO', reviewed_candidates=70,
        criteria=dict(simple_input=True, major_new_form=True, early_facets=True,
                      secondary_inside_old_folds=True, independent_smaller_hierarchy=False,
                      later_curvature=True, previous_research_material=True,
                      dominant_final_ornamental_grid=False),
        first_macro_generation=1, first_secondary_generation=2, smaller_cell_pleats_generation=3,
        clear_curvature_generation=4, strongest_curvature_generation=5,
        reason='G1 macro and G2 secondary folds survive. G3 smaller pleats remain strongly tied to repeated child-cell placement and are partly averaged away in G4/G5. Keeping strong late Eq4 preserves more pleats but also repeated kinks. A convincing independent third scale has not been proved.',
        motif_followup='Six current-valence3-only attraction trials change small original-pole neighborhoods but do not fix the hierarchy/curvature tradeoff. They are not promoted to lead.',
        scope='Observed result in this bounded search, not a proof that all possible modified subdivision configurations fail.')
    write(root / 'analysis/visual_assessment.json', assessment)
    count_table = '\n'.join(f"| G{g} | {s['statistics']['vertex_count']:,} | {s['statistics']['face_count']:,} | "
        + (f"{s['dihedral']['median']:.3f} / {s['dihedral']['p90']:.3f}" if g else '-') + ' |'
        for g,s in enumerate(stages))
    weight_table = '\n'.join('| G'+str(g)+' | '+s['declared']['offset_units']+' | '
        + ' | '.join(f"{s['declared']['weights'][k]:.12g}" for k in ['wf','w1','we','w2','wp','w3','w4','w6','w7'])+' |'
        for g,s in enumerate(stages[1:],1))
    resolved_table = '\n'.join(f"| G{g} | {s['normal_offset_scale']:.12g} | {s['resolved_weights']['wf']:.12g} | {s['resolved_weights']['we']:.12g} | {s['resolved_weights']['wp']:.12g} |"
        for g,s in enumerate(stages[1:],1))
    report = f'''# Task28 results: PARTIAL

The existing modified subdivision generates major angular form from a genuinely simple column, then secondary convergent folds, followed by curvature. It does not yet convincingly demonstrate a retained independent third scale. G3 small pleats still follow repeated child-cell placement; late relaxation removes part of them. The selected result is therefore PARTIAL, not SUCCESS. This is the conclusion of actual low-resolution experiments, not an inference from tests or polygon counts.

## Required report items 1-5: identity and input

1. Exact final local commit: authoritative post-commit `release.json` and `FINAL_REPORT.md` under `E:/CHESHIRE_DATA/task28/`. This tracked document cannot embed its own final commit hash without circularity. Baseline: `{BASELINE}`.
2. Branch: `experiment/task28-hansmeyer-benchmark`. Task-only local commit; no push or merge.
3. Tests: **818 passed in 42.93 s**, including the explicitly configured installed optional official Mola backend; **34 mechanism/benchmark tests passed in 2.24 s**. The three new tests check simple closed input vs genuine standard CC, exact saved-origin continuation, and actual nonstationary face-point geometry. Every actual lead child was independently reproduced from saved parent geometry/origins, with exact XYZ, oriented polygons and coarse face ancestry. All captured geometry/image hashes and candidate parent/source hashes passed. Installed RhinoCommon 8.18.25100.11001 reread the 3DM and opened it with RhinoDoc.OpenHeadless: exact double-precision XYZ and oriented faces, one object, no repair. Real GPU insertion-order/depth fixture passed. Logs: `test_logs/`, `analysis/geometry_validation.json`, `analysis/depth_order_check.json`, `dcc/lead_import_evidence.json`.
4. Input: one straight constant-ellipse 8-sided column; three rings at Z=0/650/1800, declared ellipse width900/depth500, angular offset pi/8. The two vertical bands differ only in length. Four coplanar quads per end cap use one center per cap. Frame T=+Z/U=+X/V=+Y. No prebuilt ornament, desired final silhouette, semantic gate route or manual folds. Actual sampled bounding box is 831.491579 x 461.939766 x 1800; declared ellipse diameters are not the octagon's bounding-box dimensions. Original unresolved coordinate units, no rescaling.
5. G0: **26 vertices, 48 edges, 24 quads**, connected closed manifold, Euler characteristic2.

## Items 6-8: machinery and recovered research

6. Confirmed: standard COMPAS CC topology with modified placement; Eq1 wf face-normal extrusion, Eq2 w1 interpolation/we mean edge-normal extrusion, Eq3 w2 corner interpolation/wp incident-normal extrusion; real previous V/F/E/E point classes and Eq4 w3/w4 face-point stencil; serializable origins; nonstationary finite schedules; nonuniform point-class overrides; literal unnormalized Eq10/11 motif attraction w6/w7. Existing crease/sharpness and optional official Mola compatibility are audited and covered by existing tests, but are not used in this lead. Source graph-distance/current normal-variation interpolation and corner locks are existing CHESHIRE additions, unused here. **The existing implementation uses original input centroids in Eq2/Eq3 and isolates same-generation face/edge displacement; this is a subset convention, not a verified complete Digital Grotesque implementation.** No equation was rewritten.

Primary source checked during audit: [Hansmeyer, Design by Subdivision, Bridges 2010](https://archive.bridgesmathart.org/2010/bridges2010-167.pdf). The paper supports the class of weighted interpolation, extrusion, nonstationary/nonuniform and motif mechanisms; it is not used to claim the entire published system has been reproduced. Exact local implementation details: `analysis/hansmeyer_implementation_audit.md`.

7. Fourteen recovered historical entries/control recipes are recorded with actual numbers, commits, generation, source file hash, surviving artifact, and Mola involvement in `analysis/previous_success_inventory.json/.md`. Key replays: Task20/21 C11 macro rows; Task22 C26 motif column; Task24 H1 macro/cleft; Task25 CURVE, AMP, convergence, flow/midgeneration normal-offset continuations. Task26 and Task27 are baseline controls. Old C07's first two CC rows are followed by a Mola Taper, zero CC and InsetFrame; Task25's fuller four-way curl is not attributed to subdivision alone. H1's exact numeric macro is replayed at CC3, original CC4 and CC5 after saved simple CC parents. Those are weight transplants on a new cage, not copies of the old whole gate context.
8. Material contribution: G1 adopts old H1 wf/we/wp=-280/320/520,w1=.8,w2=-2.8 with a matched removal of w6/w7. It changes all98 output points relative to same-parent standard CC (RMS379.766, maximum666.084). G2 uses **exact C11B** and changes all386 points (RMS167.617, maximum331.380), visibly producing secondary cuts within G1 lobes. G3 uses .70 of C11B's continuation plus the exact Task25 convergence Eq4 pair. The later pair is attenuated before zero-valued existing CC. C11/H1/convergence materially shape the progression rather than merely being listed as citations.

## Items 9-11: actual search and selected weights

9. **70 candidate definitions, {manifest['candidate_stage_count']} actual candidate stages.** Initial search:14 replay +32 nonstationary =46 definitions. Corrections:12 PASS3 +6 PASS4 +6 topology-motif follow-up. Duplicate early parents are intentional matched comparisons, not70 independent G1 shapes. Canonical unique geometries by generation: {manifest['unique_geometries_by_generation']}. All70 terminal thumbnails and parameter definitions are preserved.
10. Meaningful axes: recovered early/middle/later mechanism choices; G3 continuation factors0/.35/.70/1 x three exact old Eq4 pairs; G4 Eq4 factors0/1/3/1 x two G5 continuations; final motif face factors1/2/4 x edge factors1/2 with u3=1/u4=0. Declared numeric ranges: w1[-1.05,.8],w2[-2.8,0],w3[-3,0],w4[0,1.5],w6[-.9,1],w7[0,1.3]. Normal-offset ABSOLUTE ranges wf[-280,130],we[0,320],wp[0,520]; RATIO ranges wf[0,.30],we[-.08,0],wp[0,.10]. Current motif maps, where active, come from old actual topology signatures; declared u ranges[-1.5,2.5], and the final follow-up neutralizes new valence4 points. Offsets and dimensionless coefficients are not mixed.
11. Selected actual lineage: **P4_C033_ZERO, G0-G5**. Every stage is a byte-identical copy from this one candidate; no stages were assembled from different trials. Exact full definitions, resolved world offsets, units and original parent identities: `definitions/generation_weight_schedule.json`, `lead/lineage.json`, each `lead/Gn/request.json` and `state.json.gz`.

| Child | Offset units | wf | w1 | we | w2 | wp | w3 | w4 | w6 | w7 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{weight_table}

RATIO multiplies only wf/we/wp by the actual CURRENT GLOBAL mean edge length. ABSOLUTE uses the old coordinate units. G4 pair is exactly the binary-floating-point result of dividing the recovered Task25 pair by3. G5 all-zero placement matches mathematical standard CC within floating-point roundoff (RMS5.01e-14, maximum4.55e-13); it is a selected late call through the **same recursive backend**, not an external smooth modifier. G0-G3 were not automatically smoothed away.

| Child | Recorded offset scale | Resolved wf | Resolved we | Resolved wp |
|---|---:|---:|---:|---:|
{resolved_table}

## Items 12-18: progression and visual judgment

12. Actual counts and dihedral diagnostics:

| Stage | Vertices | Quads | Median / p90 adjacent-normal angle (degrees) |
|---|---:|---:|---:|
{count_table}

Angles measure geometric normal variation, not an automatic beauty or hierarchy score. The nonzero maximum near180degrees reflects locally folded/signed placement, not an asserted collision-free solid.

13. Every generation has `renders/lead/LEAD_Gn_front.png`, `_oblique.png`, `_wire.png`, n=0..5, with shared 4000-unit width, target[0,0,900], fixed camera pose, clay and lighting. Required sheet: `renders/lead_progression.png` (each generation side-by-side), plus `_front.png`. `renders/lead_detail.png` uses one fixed1500-unit crop throughout and does not hide cropping. Candidate gallery: `renders/candidate_contact_sheet.png`; readable pages and individual thumbnails: `candidates/thumbnails/`. Root details: `renders/task27_vs_task28.png`. All primary captures use original XYZ and **flat normals**; quads are split on diagonal0-2 for the GPU only. OBJ/checkpoints/3DM retain the original quads. Camera manifests record float32 display error, physical width, material, light and any clipped vertices. Historical CC4/5 diagnostic thumbnails use explicitly marked4800 width; all other searches use4000. There is no per-candidate fitting.
14. First major angular fold: **G1**, large vertical valleys and protruding lobes absent from G0.
15. Secondary articulation: **G2**, convergent shoulder/cap cuts within earlier lobes. G3 produces smaller pleats inside these regions, but their dependence on the repeated child cells remains visible. Genuine coarse-face ancestry is verified at each stage: every coarse quad has4^g descendant quads. This ancestry proves origin, not visual hierarchy by itself.
16. Curvature begins in parts during **G3** but becomes clear after formation in **G4** and stronger in **G5** (median angle33.280 ->12.740 ->5.823 degrees). Macro valley/shoulder structure remains while some G3 small pleats fade.
17. The selected final silhouette/read is dominated by large lobes/valleys rather than a decorative quad lattice. Nevertheless, **absence of a dominant final grid is insufficient for SUCCESS**: the third articulation scale is not convincingly independent and retained. The stronger late Eq4 alternatives leave repeated fine kinks; the smoother alternative loses some small structure.
18. Task27 accepted R4 G5 (165,888faces) reads as a shaped smooth gate with repeated local cell detail. Task28 creates large folds first from24quads, then secondary folds, then rounds them with24,576quads. This is a stronger macro-generation demonstration; it still does not establish the full required hierarchy. Comparison uses unchanged old accepted Task27 geometry and same clay/light/physical width per row, with camera translation to the respective model/column/fold. Inputs differ (gate vs simple column), so this is a visual mechanism baseline, not a controlled equal-cage contest.

## Items 19-23: limits, resources and classification

19. Mola operations outside modified subdivision in Task28 specimen/lead: **none**. No Taper/Frame/Extrude, noise, ALICE, manual fold, geometry repair, gate routing or generic ornament system.
20. No additional operation was required or used. Old Mola involvement is identified in the recovered inventory; optional Mola DLL usage in full regression tests is validation of existing compatibility and does not enter any Task28 candidate geometry.
21. Measured45 guarded geometry/render jobs: **{perf['sum_guarded_job_wall_seconds']:.3f} seconds summed job wall time**, peak sampled tree+driver **{perf['maximum_sampled_process_tree_plus_driver_bytes']/1024**2:.2f} MiB**, no resource stops. This excludes interactive audit/review/writing, test time, independent final replay audit and cold native-host startup, and is not the whole sprint elapsed time. Native read/write/open:{native['native_read_write_document_seconds']:.3f}s, native host peak{native['native_host_peak_working_set_bytes']/1024**2:.2f}MiB (separate scope). Maximum candidate mesh24,576faces; no >200k resolution rescue. Full tests42.93s. Detailed per-job evidence:`analysis/performance.json` and `logs/*/process.json`.
22. Current observed bottleneck: signed displacement readily generates macro/secondary geometry, but later class interpolation trades repeated small-cell kinks against loss of those details. Almost all newly generated vertices become valence4, leaving little intrinsic motif diversity; eight original valence3 neighborhoods do not solve the full hierarchy problem in the tested attraction ranges. Current same-generation offset isolation is an audited implementation limit worth distinguishing from complete published implementations, **not a demonstrated math bug**. RAM and polygon count were not the limiting factors. No claim is made that all possible parameter space is exhausted.
23. **PARTIAL**, under the prompt's original threshold. Simple input, new angular macro form, secondary structure, later curvature and historical reuse are demonstrated. A convincing macro->meso->independent smaller retained formation without dominant cell repetition is still unproved.

## Visual seven-question test

| Question | Answer from the saved progression |
|---|---|
| Simple G0? | Yes: straight unornamented column. |
| Major new G1/G2 geometry? | Yes: new lobes, deep valleys and shoulder/cap convergence. |
| Early angular/faceted? | Yes: G1-G3 preserved before late relaxation. |
| Later acts on existing folds? | Yes for macro/secondary; part of the small structure is lost. |
| New structures within earlier structures? | Yes at G2; G3 smaller pleats are cell-linked, not convincing independent hierarchy. |
| Curvature after formation? | Yes, particularly G4/G5 using same backend. |
| More than a repeated quad-grid? | Macro/secondary yes; full independent third scale remains unproved. |

The negative/incomplete answers are deliberately visible. They are not relabeled as SUCCESS after the experiment.
'''
    handoff = '''# Task28 handoff

Status: PARTIAL. Selected lineage P4_C033_ZERO, G0-G5. Read TASK28_RESULTS.md and analysis/visual_assessment.json first; the technology's full independent third scale remains unproved.

Baseline a9974d39f8e92c01c454e455399ca038fb8513cc; branch experiment/task28-hansmeyer-benchmark. Exact final local SHA is in release.json and FINAL_REPORT.md under E:/CHESHIRE_DATA/task28. No push/merge/Task29.

Start with renders/lead_progression.png, lead_detail.png and task27_vs_task28.png. Canonical state/geometry is lead/G0..G5, not the renderer's triangles or native display normals. dcc/lead.obj and lead.3dm retain exact final XYZ/quads; dcc/lead_import_evidence.json verifies actual reread and headless open. MODEL.zip is useful because it retains every lead checkpoint, origins, coarse-face ancestry, operator records, full schedule and native geometry, rather than only a final render.

Every candidate and intermediate failed visual alternative remains in candidates/; 70 definitions /253 actual stages. Initial46 candidates are followed by12+6 corrections and6 intrinsic-motif checks. Complete source/parent/capture identities: stage_manifest.json. Executed early source versions: source_snapshots/. A completed checkpoint is immutable; use fresh names/tags for further trials. A directory left by an incomplete worker is not a success: require summary.json plus geometry/state/OBJ and review process.json before resuming.

Recheck the complete original artifact root:

```powershell
.venv/Scripts/python.exe tools/hansmeyer_benchmark_evidence.py --output-root E:/CHESHIRE_DATA/task28 --audit
```

Replay a new candidate from the existing actual G0: copy a reviewed definition to definitions/candidates/NEW_ID.json, change its id, and call examples/hansmeyer_benchmark.py --output-root ROOT --names NEW_ID --generation 1, then each next generation separately. Each actual output must be inspected before further advancement. Keep all nine controls explicit, normal-offset units separate, and real prior origin classes. CLI uses saved current XYZ/origins, not manually reconstructed folds. --prepare reads the recovered inventory in the original E:/CHESHIRE_DATA/task28/analysis path; restoring the archived lead checkpoints does not require --prepare. Source code and pyproject.toml are included; third-party runtime DLLs/licenses are not distributed. Preserve original coordinate units.

Validation: 818 full tests /34 mechanism tests passed; all six actual lead checkpoints and every lead child exact-replay verified; native exact reread PASS. Weighted standard zero phase agrees within floating-point roundoff, not a bit-exact claim against a different summation implementation.

Interpretation limits: strong macro/secondary form is real. Increasing resolution or calling a fine cell lattice nested hierarchy would misstate the result. The most relevant remaining question is retention of independent smaller articulation through later curvature; previous four-way curling also involved Mola topology events. Task28 did not add those events or rewrite core equations. No next task has been started.
'''
    (root / 'docs').mkdir(exist_ok=True)
    (root / 'docs/TASK28_RESULTS.md').write_text(report, encoding='utf-8')
    (root / 'docs/TASK28_HANDOFF.md').write_text(handoff, encoding='utf-8')
    (REPO / 'docs/TASK28_RESULTS.md').write_text(report, encoding='utf-8')
    (REPO / 'docs/TASK28_HANDOFF.md').write_text(handoff, encoding='utf-8')
    study = REPO / 'studies/task28'; study.mkdir(exist_ok=True)
    for folder in ['definitions', 'analysis']:
        selected = list((root/folder).glob('*'))
        for p in selected:
            if p.is_file() and p.suffix in ('.json', '.md'):
                q = study / folder / p.name; q.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p,q)
    for p in (root/'definitions/candidates').glob('*.json'):
        q = study/'definitions/candidates'/p.name; q.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,q)
    for name in ['lead_progression.png','lead_detail.png','task27_vs_task28.png']:
        q=study/'evidence'/name; q.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(root/'renders'/name,q)
    shutil.copy2(root/'dcc/lead_import_evidence.json',study/'native_import_evidence.json')
    for p in (root/'test_logs').glob('*.txt'):
        q=study/'test_logs'/p.name; q.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,q)
    write(study/'artifact_location.json',dict(root=str(root),baseline=BASELINE,lead='P4_C033_ZERO',status='PARTIAL',
          policy='Large candidate/checkpoint/native files remain external. All actual stages retained. Final local identity is in external release.json.'))
    log = root / 'analysis/experiment_log.md'
    addition = '''
## PASS4 follow-up: existing topology motif discrimination (6 definitions)

After the global path already produced useful macro/secondary structure, keep G1/G2 and G3 continuation unchanged, then apply existing literal Eq10/11 at G3. Map only current (3,3) to1 and (4,4) to0; scale recovered C26 w6=.25 by1/2/4 and w7=.65 by1/2. This is a six-point deterministic two-axis comparison, not Task27 semantic routing. G4 is the attenuated convergence pair and G5 the zero-valued existing backend. Every actual G1-G5 and render is saved in candidates/P4B_* and renders/pass4b_*. The changes remain concentrated in eight original degree3 neighborhoods and do not make a convincing independent smaller hierarchy. Do not promote this follow-up over the simpler P4_C033_ZERO lead.

## Final selection and technical verification

P4_C033_ZERO is the selected real G0-G5 lineage, with PARTIAL classification explained in visual_assessment.json and TASK28_RESULTS.md. Curvature and macro/secondary retention are proven; an independent third scale remains unproved. Strong late class pairs leave repeated kinks; weak late pairs remove some G3 small folds. No Mola event or new equation is used.

All253 candidate stages completed finite/positive unsigned face-area diagnostics and OBJ reread; every lead child was independently reproduced from actual saved parent geometry/origins. Native export exact reread/open PASS. Full818 tests and34 relevant mechanism tests pass. One initial test collection used a non-exported COMPAS import and was corrected to the public Mesh.subdivided API. One reporting-key export error occurred after copying the lead stages; the corrected export resumed only after proving every copied byte matched its original. These were harness/report errors, not failed geometry candidates; no checkpoints were removed or silently repaired.
'''
    if '## PASS4 follow-up:' not in log.read_text(encoding='utf-8'):
        with log.open('a',encoding='utf-8') as f: f.write(addition)
    shutil.copy2(log, study/'analysis/experiment_log.md')
    print('Factual 23-item reports and tracked compact evidence saved', flush=True)


def package(root):
    sha = subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    status = subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True)
    if status:
        raise ValueError('Commit authorized Task28 changes before packaging; preserve exact clean identity.')
    branch = subprocess.check_output(['git','branch','--show-current'],cwd=REPO,text=True).strip()
    write(root/'release.json',dict(final_local_commit=sha,baseline=BASELINE,branch=branch,clean=True,
          lead='P4_C033_ZERO',status='PARTIAL',sources={p:file_hash(REPO/p) for p in TASK_FILES},
          OBJ=str(root/'dcc/lead.obj'),native=str(root/'dcc/lead.3dm'),no_push=True,no_merge=True))
    header=f'# Task28 final local release\n\nCommit: `{sha}`\n\nBranch: `{branch}`\n\nStatus: **PARTIAL**.\n\n'
    (root/'FINAL_REPORT.md').write_text(header+(root/'docs/TASK28_RESULTS.md').read_text(encoding='utf-8'),encoding='utf-8')
    review={}; model={}
    def add(target,p):
        if p.is_file(): target[p.relative_to(root).as_posix()]=p
    for name in ['FINAL_REPORT.md','release.json','stage_manifest.json']:
        add(review,root/name)
    for folder in ['analysis','definitions','docs','test_logs','brief','source_snapshots']:
        for p in (root/folder).rglob('*'):
            add(review,p)
            if folder in ('analysis','definitions','docs','source_snapshots'): add(model,p)
    for p in (root/'logs').glob('*/process.json'): add(review,p)
    for p in (root/'candidates').glob('*/G*/summary.json'): add(review,p)
    for p in (root/'candidates').glob('*/G*/request.json'): add(review,p)
    for p in (root/'candidates/thumbnails').glob('*'): add(review,p)
    for p in (root/'renders').glob('*.png'): add(review,p)
    for tag in ['lead','lead_detail','task27_comparison','task27_comparison_detail']:
        for p in (root/'renders'/tag).glob('*'): add(review,p)
    for p in (root/'renders').glob('*/camera_manifest.json'): add(review,p)
    for p in (root/'renders').glob('*/*contact_sheet.png'): add(review,p)
    for p in (root/'lead').rglob('*'): add(model,p)
    for p in (root/'dcc').glob('*'): add(model,p)
    for name in ['FINAL_REPORT.md','release.json']: add(model,root/name)
    add(review,root/'dcc/lead_import_evidence.json')
    # Include actual tracked Python dependencies of the small harness, not a DLL,
    # guessed import list or proprietary Rhino installation.
    tracked=subprocess.check_output(['git','ls-files'],cwd=REPO,text=True).splitlines()
    for name in tracked:
        p=REPO/name
        if ((p.suffix=='.py' and name.startswith(('src/','examples/','tools/','rhino/')))
            or name in TASK_FILES or name in ['pyproject.toml','README.md','THIRD_PARTY_NOTICES.md']):
            review['source/'+name]=p; model['source/'+name]=p
    a=archive(root/'CHESHIRE_TASK28_REVIEW.zip',review)
    b=archive(root/'CHESHIRE_TASK28_MODEL.zip',model)
    write(root/'deliverables.json',dict(review=a,model=b,final_local_commit=sha,branch=branch,status='PARTIAL',
          model_reason='Every actual lead geometry/origin/ancestry checkpoint and operator record plus exact native model; useful for direct inspection and continuation.'))
    print('Actual archive CRC and payload SHA256 PASS',a['bytes'],b['bytes'],flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--reports',action='store_true');p.add_argument('--package',action='store_true')
    a=p.parse_args()
    if a.reports: reports(a.output_root)
    if a.package: package(a.output_root)
