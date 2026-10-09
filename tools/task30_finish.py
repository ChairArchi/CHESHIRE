"""Decision evidence, provenance audit, local reports and sealed review bundle."""
import argparse,hashlib,json,shutil,subprocess,sys,zipfile,platform
from pathlib import Path
from time import perf_counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
from task30_study import ROOT,PREVIOUS,REPO,BASELINE
from task29_search import load_mesh
from cross_cell_crease_study import read,write,file_hash

BRANCH='experiment/task30-reference-grounded-consolidation'
OWN=['src/cheshire/dual_subdivision.py','src/cheshire/subdivision_pipeline.py',
    'tools/task30_reference_read.py','tools/task30_study.py','tools/task30_views.py','tools/task30_evidence.py',
    'tools/task30_native.ps1','tools/task30_finish.py','tests/test_dual_subdivision.py','tests/test_subdivision_pipeline.py']
REQUIRED=[*['analysis/'+n for n in ['reference_insight_matrix.md','canonical_task29_pipeline.md',
    'primary_bottleneck_diagnosis.md','targeted_experiment_plan.md','targeted_experiment_log.json','final_decision.md']],
    *['definitions/'+n for n in ['retained_canonical_pipeline.json','task30_variant_definitions.json','final_selected_pipeline.json']],
    *['renders/'+n for n in ['TASK29_vs_TASK30_lead.png','TASK30_targeted_variants.png','TASK30_FINAL_LEAD_PROGRESSION.png',
        'TASK30_detail_comparison.png','TASK30_reference_relation_sheet.png']],
    'dcc/TASK30_LEAD.obj','dcc/TASK30_LEAD.3dm','docs/TASK30_RESULTS.md','docs/TASK30_HANDOFF.md','FINAL_REPORT.md',
    *[f'lead/G{g}/mesh.npz' for g in range(9)]]


def relation():
    target=ROOT/'references';target.mkdir(exist_ok=True)
    for i in range(1,6):shutil.copy2(REPO/f'output/task30_references/official_design_{i}.jpg',target/f'official_design_{i}.jpg')
    font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
    out=Image.new('RGB',(2800,1860),(245,245,242));draw=ImageDraw.Draw(out)
    draw.text((35,25),'TASK30 / Reference relation: different regional development',font=font(43),fill=(25,25,25))
    draw.text((35,90),"User's eight-panel attachment: observations only; original reviewed in chat, not reproduced here.",font=font(28),fill=(55,55,55))
    cards=['1 Coarse vertical envelope','2 Early local variation','3 Branching beside necks','4 Bulbs and bands',
        '5 Regions develop differently','6 Nested ribs + branching','7 Multi-scale regions persist','8 Denser regional hierarchy']
    for j,label in enumerate(cards):
        x=35+(j%4)*690;y=145+(j//4)*74
        draw.rounded_rectangle((x,y,x+660,y+60),radius=8,fill=(225,228,222));draw.text((x+15,y+13),label,font=font(27),fill=(35,40,35))
    draw.text((35,315),'Inference: persistent boundaries + different local modes. Pixels do not identify exact masks or generations.',font=font(27),fill=(35,35,35))
    rows=read(ROOT/'renders/detail/manifest.json')['records']
    # The contextual final reference is explicitly a different image/source.
    pictures=[(target/'official_design_3.jpg','Official DGI detail / context only'),
        (Path(rows[0]['image']),'Shared actual G3 / 700 units'),
        (Path(rows[2]['image']),'Task29 G8 / flat / 700 units'),
        (Path(rows[5]['image']),'Task30 G8 / flat / 700 units')]
    manifest=[]
    for j,(p,label) in enumerate(pictures):
        x=35+j*690;im=Image.open(p).convert('RGB');im=ImageOps.contain(im,(660,720));out.paste(im,(x+(660-im.width)//2,400+(720-im.height)//2))
        draw.text((x,1140),label,font=font(25),fill=(25,25,25));manifest.append(dict(file=str(p),sha256=file_hash(p),label=label))
    text=[
        'R1 (Hansmeyer 2010), p77: mixed CC / Doo-Sabin and face-origin groups are explicit published options.',
        'R1 p78: locks may apply only during starting iterations. R1 p80 also shows complex CC-only forms.',
        'R2 (2024 interview): custom design process and fabrication context; no reproducible weight schedule.',
        'R3 (Bader / Oxman 2016): recursive cut / reflect / union creates a control mesh BEFORE CC refinement.',
        'Task30: uniform DS at G6 / G7 + locks ending G4. Fold bands read more coherently; micro repetition remains.',
        'Face-origin contrast alone produces recurring boundary ridges. It does not create persistent regional identity.',
        'PARTIAL: continuity improved with some suppression. Independent non-repetitive small growth is not proven.',
        'DGI context: Michael Hansmeyer, digital-grotesque-design-3-m.jpg (official site); not the attached progression.',
        'Reference camera, scale and normals are unknown. Only Task29 / Task30 geometry images are matched.'
    ]
    for j,line in enumerate(text):draw.text((35,1240+j*56),line,font=font(27),fill=(40,40,40))
    path=ROOT/'renders/TASK30_reference_relation_sheet.png';out.save(path)
    write(ROOT/'analysis/reference_relation_manifest.json',dict(sheet_sha256=file_hash(path),images=manifest,
        original_user_progression='Reviewed inline; only observation cards reproduced, clearly labelled. No unavailable bitmap fabricated.',
        reference_URL='https://michael-hansmeyer.com/digital-grotesque-I.html',geometric_comparison='Actual same-scale flat-normal render records from renders/detail/manifest.json'))
    # Required targeted sheet includes all16 new meaningful variants and one control.
    from task30_views import sheet
    records=read(ROOT/'renders/primary/manifest.json')['records']+read(ROOT/'renders/secondary/manifest.json')['records'][1:]
    assert len(records)==17;sheet(records,ROOT/'renders/TASK30_targeted_variants.png',4,1000)
    for tag,name,cols,size in [('progression','TASK30_FINAL_LEAD_PROGRESSION.png',3,1000),
        ('comparison','TASK29_vs_TASK30_lead.png',2,1400),('detail','TASK30_detail_comparison.png',3,1300)]:
        sheet(read(ROOT/f'renders/{tag}/manifest.json')['records'],ROOT/'renders'/name,cols,size)
    print('Reference relation and complete16-variant decision sheet saved.',flush=True)


def audit():
    start=perf_counter();records=[];parents=0
    for group in ('candidates','controls','lead'):
        for p in sorted((ROOT/group).rglob('summary.json')):
            d=p.parent;s=read(p);m=load_mesh(d)
            assert file_hash(d/'mesh.npz')==s['mesh_sha256']
            assert len(m.xyz)==s['vertices'] and len(m.faces)==s['faces'] and m.generation==s['generation']
            assert np.isfinite(m.xyz).all() and np.isfinite(m.rest).all() and s['Euler']==2 and s['zero_area_faces']==0
            assert np.array_equal(np.ptp(m.xyz,axis=0),s['extent'])
            with np.load(d/'face_roles.npz') as z:
                roles=z['face_roles'];assert roles.shape==(len(m.faces),) and np.isin(roles,[-1,0,1,2]).all()
            if s.get('source_checkpoint'):
                assert file_hash(s['source_checkpoint']['path']+'/mesh.npz')==s['source_checkpoint']['sha256']==s['mesh_sha256']
            if s.get('parent'):
                prior=Path(s['parent']);assert file_hash(prior/'mesh.npz')==s['parent_mesh_sha256']
                assert read(prior/'summary.json')['generation']+1==m.generation;parents+=1
            if (d/'operator_state.npz').exists():
                if 'operator_state_sha256' in s:assert file_hash(d/'operator_state.npz')==s['operator_state_sha256']
                with np.load(d/'operator_state.npz') as z:
                    assert all(np.isfinite(z[k]).all() for k in z.files)
                    if 'parent_faces' in z:
                        pf=z['parent_faces'];assert pf.shape==(len(m.faces),4) and np.all((pf>=0).any(1))
                        assert np.all(pf<read(Path(s['parent'])/'summary.json')['faces'])
            records.append(dict(path=str(d.relative_to(ROOT)),mesh_sha256=s['mesh_sha256'],generation=m.generation,vertices=len(m.xyz),faces=len(m.faces)))
    assert len(records)==162
    renders=[]
    for p in sorted((ROOT/'renders').glob('*/manifest.json')):
        for r in read(p)['records']:
            assert file_hash(Path(r['stage'])/'mesh.npz')==r['mesh_sha256'] and file_hash(r['image'])==r['image_sha256']
            assert r['flat_normals'] and not r['smoothing'] and r['occupied_pixels']>0
            renders.append(dict(manifest=str(p.relative_to(ROOT)),image=r['image'],physical_width=r['physical_width'],outside_frame=r['outside_frame']))
    final=read(ROOT/'renders/progression/manifest.json')['records'];assert len(final)==9
    assert all(r['outside_frame']==0 for r in final) and len({json.dumps(r['camera_pose']) for r in final})==1
    unchanged=[]
    for name in ('weighted_subdivision.py','generational_subdivision.py','sharp_subdivision.py','reference_subdivision.py'):
        path='src/cheshire/'+name;old=subprocess.check_output(['git','show',BASELINE+':'+path],cwd=REPO)
        assert old.replace(b'\r\n',b'\n')==(REPO/path).read_bytes().replace(b'\r\n',b'\n')
        unchanged.append(dict(path=path,baseline_blob_sha256=hashlib.sha256(old).hexdigest(),unchanged_source=True))
    test=(REPO/'output/task30_full_tests_final.txt').read_text(encoding='utf-8-sig');assert '862 passed' in test and 'failed' not in test
    (ROOT/'test_logs').mkdir(exist_ok=True)
    for name in ('task30_full_tests.txt','task30_full_tests_final.txt'):shutil.copy2(REPO/'output'/name,ROOT/'test_logs'/name)
    native=read(ROOT/'dcc/TASK30_LEAD_import_evidence.json')
    assert native['OBJ_sha256']==file_hash(ROOT/'dcc/TASK30_LEAD.obj') and native['native_sha256']==file_hash(ROOT/'dcc/TASK30_LEAD.3dm')
    assert native['exact_XYZ_oriented_faces'] and native['headless_document_open']
    jobs=[dict(job=p.parent.name,**read(p)) for p in sorted((ROOT/'logs').glob('*/process.json'))]
    assert all(j['exit_code']==0 and j['resource_stop'] is None for j in jobs)
    write(ROOT/'analysis/performance.json',dict(jobs=jobs,measured_guarded_seconds=sum(j['seconds'] for j in jobs),
        sampled_peak_tree_plus_driver_bytes=max(j['sampled_peak_tree_plus_driver_bytes'] for j in jobs),native=native,
        scope='Measured guarded generation/render jobs only; native host has separate measurements. Not total agent elapsed time.'))
    write(ROOT/'analysis/validation_summary.json',dict(status='PASS',tests_passed=862,skipped=0,backend='Actual HDMola.dll1.0.0 / coreclr',
        saved_geometry_stages=len(records),new_generated_stages=80,candidate_definitions=16,parent_checks=parents,
        all_stage_checks=records,flat_render_checks=len(renders),renders=renders,unchanged_canonical_and_legacy=unchanged,
        exact_replay=read(ROOT/'analysis/geometry_validation.json'),native=native,seconds=perf_counter()-start,
        limits='Combinatorial checks and native readability do not establish embedded solid validity.'))
    print('162 states, all render hashes, exact native/OBJ hashes, unchanged kernels and862 tests audited.',flush=True)


def reports():
    spec=read(ROOT/'definitions/final_selected_pipeline.json');lead=[read(ROOT/f'lead/G{g}/summary.json') for g in range(9)]
    old=read(ROOT/'controls/task29/G8/summary.json');valid=read(ROOT/'analysis/validation_summary.json');perf=read(ROOT/'analysis/performance.json')
    decision=(ROOT/'analysis/final_decision.md').read_text(encoding='utf-8')
    extra='''

## Attribution limits and retained mechanisms

DS replacement also changes which later CC equations are eligible: the first CC
after DS cannot use Eq4. Thus the matched Task29 difference includes scheme geometry,
connectivity, Eq4 fallback and the declared lock lifetime. It does not isolate adjacency
alone. M/S vs U within a matched schedule isolates structural weights; END3/END4 vs
their unchanged parent isolates lock lifetime. Continuous DS is a detail-suppression
negative control. These limitations are part of the decision, not hidden implementation details.

G8's w3/w4 base/control values remain in the definition but are inactive for that step
because all98,306 input faces lack the real V/E/F vertex pattern. Other controls remain
modified and nonzero. The declared Eq1 fallback is part of the selected mechanism.
No fake point origins or silent all-zero standard-CC final step is used.
'''
    (ROOT/'analysis/final_decision.md').write_text(decision+extra,encoding='utf-8')
    rows='\n'.join(f"| G{g} | {r['vertices']:,} | {r['faces']:,} | {r['mean_edge']:.4f} | {r['dihedral_median']:.2f} |" for g,r in enumerate(lead))
    report=f'''PARTIAL

# Task30 — reference-grounded consolidation and targeted tests

세 논문31쪽과 첨부8단계 이미지를 읽고, Task29의 실제 G3에서16개 제한된 실험을 했다.
선택 리드 `{spec['id']}`는 큰 접힘과2차 형상을 유지하면서 평면 법선의 각진 미세 파편을 줄인다.
그러나 비반복적인 독립 미세 성장은 증명하지 못했다. DS의 면·모서리·꼭짓점 기원별 규칙도
반복되는 경계 띠를 만들었다. 후기 구조가 더 풍부해졌다고 판정하지 않는다.

Baseline: `{BASELINE}`. Branch: `{BRANCH}`.
Exact new local commit: post-commit `analysis/repository_commit.json` (a tracked report cannot hash itself).
No push, merge or Task31. Task29 artifacts and its source kernels are preserved.

## Reference-grounded decision

R1 Michael Hansmeyer, **Subdivision Beyond Smoothness**,2010,7pages,
DOI10.2312/COMPAESTH/COMPAESTH10/075-081: exact DS Eq5/6, F/E/V face origins and
scheme switching(p77); early-only locks(p78); complex CC-only example(p80).
R2 Blanco/Madrid,2024,15pages, DOI10.3991/ijet.v19i07.50845: design/interview/fabrication
context, no executable mask or recovered schedule. R3 Bader/Oxman,2016,9pages,
DOI10.1016/j.cad.2016.09.002: recursive cut/reflection/union makes a coarse control mesh,
then CC refines it; it is a separate generator, not Hansmeyer's subdivision equation.

The user image shows branching beside neck/bulb/rib regions and persistent large envelopes.
This is visual inference, not proof of the actual scheme/generation/normal treatment.
It was reviewed inline; its bitmap is unavailable on disk. The relation sheet therefore
labels observation cards explicitly and uses separately attributed official DGI context,
never another image presented as the attachment. PDF hashes and sources are recorded.
Official context: https://michael-hansmeyer.com/digital-grotesque-I.html
Paper publisher: https://doi.org/10.2312/COMPAESTH/COMPAESTH10/075-081

Initial primary D was connectivity vocabulary, tested by12 meaningful mixed-scheme variants.
It proved insufficient alone; the final PRIMARY working diagnosis is **C**, weak intrinsic
spatial differentiation and persistent regional/motif identity. This revision is explicit.
C is not a proven cure; D and schedule/locking interactions remain relevant.
Four secondary early-only-lock ablations completed the total16. No third direction.
This missing published DS mechanism was prioritized under the prompt's better-method clause;
the exact hypotheses, controls and negative evidence are saved, rather than another large sweep.

## Canonical base and exact selected mechanism

Retain **REFERENCE_COUPLED + LOCAL_INCIDENT_SCALE + exact nonzero nonstationary rows**,
with explicit optional intrinsic interpolation/locking. Task29 G1 H1_NO_ATTR, G2 C11B,
G3 T28_G3, G4 CURVE, G5–8 T28_G3 and all full-precision values are copied in
`definitions/retained_canonical_pipeline.json`. Eq3 uses original endpoint midpoints;
completed faces feed Eq2/3; Eq4 requires genuine previous V/E/F classes.
Sf is current mean perimeter edge length; Se incident two-Sf mean; Sv incident Sf mean.

Task30 actual G0–G3 exactly equal Task29. G4/G5 remain original CC rows; locks throughG4.
G6/G7: modified published DS, `w1=.6,wf=.03*Sf`, uniform groups. G8: original nonzero
CC row and NORMAL_VARIATION interpolation, without locks; explicit Eq1 fallback because
prior DS points have no CC V/E/F stencil provenance. F/E/V DS face roles persist as separate
state. Tested nonuniform face-origin weights are NOT in the final lead.
The original intrinsic gain3/threshold.12/control intervals are retained on CC;
locks apply atG3/G4 only. DS steps introduce new face-corner points and do not apply that
old-vertex locking extension. Exact per-step JSON is authoritative; values are not rounded.

DS changes combinatorial adjacency via F/E/V faces and cyclic fans. No welding, holes,
genus change or recursive boolean generator: Euler2. Exact multi-parent face supports
are stored. Shared G1/2/3 anchors are retained only when all parents agree, otherwise-1.
Retention proxies follow all actual parent supports; overlapping supports are disclosed.

## Actual comparison and decision

Same cube, unchanged coordinates/project units, clay/light, fixed2600-unit whole frames,
700-unit front crops, flat normals throughout. Whole three-view and G3/G5/G8 detail comparisons
are saved. No smoothing/remeshing/beauty-only evidence. Display uses0–2 quad triangulation
and float32 GPU positions only; NPZ/OBJ/3DM preserve double XYZ and original oriented polygons.

Task29 median adjacent-normal angle {old['dihedral_median']:.4f}deg → Task30 {lead[-1]['dihedral_median']:.4f}deg;
p90 {old['dihedral_p90']:.4f}deg → {lead[-1]['dihedral_p90']:.4f}deg.
Those are diagnostics, not a non-repetition score. Broad lobes and meso folds remain visible;
early tips shrink. Micro clutter recedes and narrow bands read more coherently, but small
patterns still recur. The all-DS control removes most fine development despite its lower
angle score. Task30 therefore remains **PARTIAL**, with a limited continuity/retention advance.
Mixed geometry plus Eq4 fallback is a coupled change; adjacency alone is not isolated.

| stage | vertices | polygons | mean edge | median normal angle deg |
|---|---:|---:|---:|---:|
{rows}

All80 new G4–G8 stages completed. There are144 saved candidate stages (64 exact prefix copies),
9 unchanged control stages and9 selected lead copies,162 audited states in total.
All16 definitions and actual checkpoints remain, including negative results. No face/time cap
stopped a job. Guarded sampled peak tree+driver RAM: {perf['sampled_peak_tree_plus_driver_bytes']:,}bytes;
guarded generation/render elapsed sum: {perf['measured_guarded_seconds']:.3f}s (not total task wall time).

## Verification and code consolidation

**862 passed, zero skipped**, with actual HDMola1.0.0/.NET coreclr. New focused cases check
independent published triangle/quad masks, oriented F/E/V fans, true CC fallback/recovery,
multi-parent anchors, deterministic groups, exact checkpoint continuation and lock lifetime.
Final cube replay matches all G0–G8 XYZ/faces/classes/rest/anchors/face roles and saved arrays;
actual G7 reload continues exactly toG8. Every lead OBJ is reread with exact double coordinates
and oriented polygons. Installed RhinoCommon8.18 rereads3DM exactly and OpenHeadless opens its
single mesh. Native sections use the actual reread file. Render hashes and source hashes pass.

After the technical decision, the small root-independent `subdivision_pipeline.py` makes
scheme, scale, generation and locking explicit; it saves/loads real structural state.
`dual_subdivision.py` is an opt-in bounded operator. Original reference, weighted, generational
and sharp kernels remain unchanged. Legacy boundary/crease clients still work; large Task29
sweep/weld scripts are archived research controls, not the default path. See handoff status table.

DS scope: closed oriented triangles/quads, input valence3/4. No general polygon/valence claim.
Finite/incidence/Euler/native checks do not certify a self-intersection-free solid or fabrication.
Exact DG masks beyond the published paper, unpublished parameters and region tags are unknown.
Reference symmetry cannot be broken by deterministic equivariant rules on identical states alone.

Open `renders/TASK30_FINAL_LEAD_PROGRESSION.png`, then `TASK30_detail_comparison.png`,
`TASK29_vs_TASK30_lead.png`, `TASK30_targeted_variants.png`, `TASK30_reference_relation_sheet.png`.
Final decision: `analysis/final_decision.md`. Complete payload: `CHESHIRE_TASK30_REVIEW.zip`.
Post-commit archive CRC/every-entry SHA proof: `analysis/archive_validation.json`.
'''
    handoff='''# Task30 handoff — PARTIAL

Root: E:/CHESHIRE_DATA/task30. Selected U_67_LOCK_END4. Read final_decision.md first.
The full-precision final_selected_pipeline.json and actual lead checkpoints are authoritative.
No push, merge or Task31. No new broad sweep is warranted by this result alone.

| path | status / responsibility |
|---|---|
| src/cheshire/reference_subdivision.py | Canonical audited CC base; unchanged Task29 behavior |
| src/cheshire/subdivision_pipeline.py | Small canonical explicit dispatch and checkpoint API, no research-root dependence |
| src/cheshire/dual_subdivision.py | Opt-in published bounded DS; face roles, multi-parent supports, no genus changes |
| weighted / generational / sharp modules | Historical replay/controls and existing boundary/crease clients; unchanged |
| examples/task29_search.py, task29_topology.py | Archived research sweep and pair-weld controls; not the minimal default workflow |
| tools/task29_* | Archived Task29 evidence tools; renderer/export codec reused without changing their historical defaults |
| tools/task30_study.py | Bounded16-definition experiment orchestrator; preserve saved outputs; refuses checkpoint overwrite |
| tools/task30_evidence.py | Actual lineage selection, exact cube/checkpoint replay, OBJ semantic verification |
| tools/task30_views.py | Actual mesh capture using unchanged fixed Task29 flat renderer |
| tools/task30_native.ps1 | Installed Rhino8 exact3DM reread/headless open; use Windows PowerShell5.1 |
| tools/task30_finish.py | Evidence/report publication and post-commit streaming archive checks |

Minimal portable continuation (from repository with .venv, using an unused output folder):

```python
import json
from pathlib import Path
from cheshire.subdivision_pipeline import load_checkpoint, step, save_checkpoint
root = Path('E:/CHESHIRE_DATA/task30')
definition = json.loads((root/'definitions/final_selected_pipeline.json').read_text())
state = load_checkpoint(root/'lead/G7')
state, metadata, arrays = step(state, definition['steps'][7])
save_checkpoint(Path('YOUR_UNUSED_OUTPUT_FOLDER/G8'), state, arrays)
```

For cube replay initialize SubdivisionState(cube(), full(6,-1,int8)), then run every
declared step. Definitions carry generation, scheme and scale; wrong generation or
unknown scheme is rejected. DS point classes are unknown for Eq4 intentionally.
Face origins are separate from vertex classes. Never reconstruct DS multi-parent
support from a guessed single anchor. Operator_state.npz contains all actual supports.
Rest is positive cage association, not an extra displacement or gate field.

Local exact lead verification command (rewrites same task-stamped OBJ bytes):
`.venv/Scripts/python.exe -X utf8 tools/task30_evidence.py --verify`.
For independent use, replay to a fresh destination via the portable API above.
Re-running --prepare / --primary / --secondary / --select in completed artifact folders
is intentionally refused by existing outputs. Review existing evidence instead.

Full tests require CHESHIRE_MOLA_DLL=C:/Users/USER/Libraries/HDMola/1.0.0/HDMola.dll
and PYTHONNET_RUNTIME=coreclr. Use a fresh external --basetemp directory; an existing
negative repository-identity fixture requires a path outside the repository.
Run `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp FRESH_EXTERNAL_PATH`.

Task29 original definition/control stays available in retained_canonical_pipeline.json
and controls/task29. The selected Task30 recipe is an opt-in study lead, not a silent
new default for all geometry clients. Grouped DS and continuous DS are negative results
for this target, retained as evidence rather than deleted. See reference matrix/source
ledger for PDF page/hash attribution; the inline image is not fabricated in the archive.
'''
    (ROOT/'docs').mkdir(exist_ok=True)
    for name,content in [('TASK30_RESULTS.md',report),('TASK30_HANDOFF.md',handoff)]:
        (ROOT/'docs'/name).write_text(content,encoding='utf-8');(REPO/'docs'/name).write_text(content,encoding='utf-8')
    (ROOT/'FINAL_REPORT.md').write_text(report,encoding='utf-8')
    print('Results, explicit epistemic limits and minimal-path handoff saved.',flush=True)


def publish():
    assert all((ROOT/p).is_file() for p in REQUIRED)
    study=REPO/'studies/task30'
    for group in ('analysis','definitions'):
        target=study/group;target.mkdir(parents=True,exist_ok=True)
        for p in sorted((ROOT/group).glob('*')):
            if p.is_file():shutil.copy2(p,target/p.name)
    target=study/'renders';target.mkdir(exist_ok=True)
    for name in [p.split('/')[-1] for p in REQUIRED if p.startswith('renders/')]:shutil.copy2(ROOT/'renders'/name,target/name)
    snapshot=ROOT/'source_snapshots/final'
    for name in OWN:
        target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/name,target)
    write(ROOT/'analysis/final_source_hashes.json',dict(files=[dict(path=p,sha256=file_hash(REPO/p)) for p in OWN]))
    write(study/'ARTIFACTS.json',dict(verdict='PARTIAL',root=str(ROOT),baseline=BASELINE,branch=BRANCH,
        final_lead='U_67_LOCK_END4',new_variants=16,new_geometry_stages=80,
        files=[dict(path=p,bytes=(ROOT/p).stat().st_size,sha256=file_hash(ROOT/p)) for p in REQUIRED if not p.startswith('docs/') and p!='FINAL_REPORT.md'],
        post_commit_stamped_reports=['docs/TASK30_RESULTS.md','FINAL_REPORT.md'],
        post_commit=['analysis/repository_commit.json','analysis/file_inventory.json','analysis/archive_validation.json'],archive='CHESHIRE_TASK30_REVIEW.zip'))
    (study/'README.md').write_text('''# Task30 — PARTIAL

Three supplied papers and the inline progression informed16 bounded real variants.
Published mixed CC/DS improves flat-normal continuity with early folds still legible;
independent non-repetitive fine development remains unproven. Initial D hypothesis
was insufficient; final primary working diagnosis isC, weak persistent differentiation.

Read [results](../../docs/TASK30_RESULTS.md), [handoff](../../docs/TASK30_HANDOFF.md),
[decision](analysis/final_decision.md), and [actual progression](renders/TASK30_FINAL_LEAD_PROGRESSION.png).
Exact definitions/selected evidence are tracked. Actual NPZ/OBJ/3DM and every targeted
variant are external at E:/CHESHIRE_DATA/task30 and in CHESHIRE_TASK30_REVIEW.zip.
ARTIFACTS.json records file hashes. Original Task29 kernels and artifacts are preserved.
''',encoding='utf-8')
    print('Required artifacts and selected repository/source snapshot evidence published.',flush=True)


def package():
    start=perf_counter();assert not subprocess.check_output(['git','status','--porcelain'],cwd=REPO).strip()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=REPO,text=True).strip()
    assert branch==BRANCH and commit!=BASELINE
    write(ROOT/'analysis/repository_commit.json',dict(commit=commit,branch=branch,baseline=BASELINE,local_only=True,
        clean_worktree=True,pushed=False,merged=False,Task31_started=False))
    for p in (ROOT/'FINAL_REPORT.md',ROOT/'docs/TASK30_RESULTS.md'):
        text=p.read_text(encoding='utf-8');text=text.replace('Baseline: `'+BASELINE+'`.','Task30 local commit: `'+commit+'`.\n\nBaseline: `'+BASELINE+'`.')
        p.write_text(text,encoding='utf-8')
    source=ROOT/'source_snapshots/CHESHIRE_TASK30_SOURCE.zip';assert not source.exists()
    subprocess.run(['git','archive','--format=zip','--output='+str(source),'HEAD'],cwd=REPO,check=True)
    excluded={'analysis/file_inventory.json','analysis/archive_validation.json'}
    paths=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and p.relative_to(ROOT).as_posix() not in excluded and (p.suffix.lower()!='.zip' or p==source)]
    inventory=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=file_hash(p)) for p in paths]
    write(ROOT/'analysis/file_inventory.json',dict(commit=commit,files=inventory,scope='All payload files except self/post-seal proofs and reviewZIP; complete committed sourceZIP included.'))
    paths.append(ROOT/'analysis/file_inventory.json');expected={p.relative_to(ROOT).as_posix():file_hash(p) for p in paths}
    target=ROOT/'CHESHIRE_TASK30_REVIEW.zip';assert not target.exists()
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    print('Written reviewZIP',target.stat().st_size,'bytes; reading every actual payload.',flush=True)
    with zipfile.ZipFile(target) as z:
        assert len(z.namelist())==len(paths)==len(set(z.namelist())) and z.testzip() is None
        for n in z.namelist():
            h=hashlib.sha256()
            with z.open(n) as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
            assert h.hexdigest()==expected[n],n
    write(ROOT/'analysis/archive_validation.json',dict(status='PASS',commit=commit,path=str(target),bytes=target.stat().st_size,
        sha256=file_hash(target),entries=len(paths),CRC='PASS',every_entry_sha256='PASS',actual_readback=True,seconds=perf_counter()-start,
        scope='Proof remains outside archive to avoid self hashes; payload inventory and committed source ZIP are inside.'))
    print('Local commit',commit,'reviewZIP CRC and every payload SHA256 PASS.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('relation','audit','reports','publish','package'):p.add_argument('--'+name,action='store_true')
    a=p.parse_args()
    for name in ('relation','audit','reports','publish','package'):
        if getattr(a,name):globals()[name]()
