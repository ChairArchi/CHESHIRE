"""Task31 final evidence audit, reports, repository snapshot and sealed review ZIP."""
import argparse,gc,hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
from time import perf_counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
from task31_study import ROOT,PREVIOUS,REPO,read,write,load_mesh
from task30_views import sheet

BASELINE='e66324f63a956182f5808e5f412a77e65973b338'
BRANCH='experiment/task31-regional-depth-openings'
OWN=['src/cheshire/reference_subdivision.py','src/cheshire/polygon_dual_subdivision.py','src/cheshire/regional_generation.py',
    'tests/test_task31_regional_generation.py']+[str(p.relative_to(REPO)).replace('\\','/') for p in sorted((REPO/'tools').glob('task31_*'))]
POSTCOMMIT={'CHESHIRE_TASK31_REVIEW.zip','analysis/review_zip_validation.json',
    'analysis/repository_commit.json','analysis/repository_commit_payload.json'}
FIRST_BUNDLE='logs/review_bundle_first.zip'


def file_hash(path):
    """Bounded-memory hashing even for multi-GB review archives."""
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def visuals():
    lead=read(ROOT/'definitions/task31_lead_pipeline.json')['gate']['id']
    gate=read(ROOT/'renders/gate/manifest.json')['records']
    chosen=next(r for r in gate if r['label'].startswith(lead+' '))
    sheet(read(ROOT/'renders/gate_compare/manifest.json')['records'],ROOT/'renders/TASK30_vs_TASK31_gate.png',2,1500)
    sheet(read(ROOT/'renders/cube_compare/manifest.json')['records'],ROOT/'renders/TASK30_vs_TASK31_cube.png',2,1400)
    cube=read(ROOT/'renders/detail/manifest.json')['records'];detail=read(ROOT/'renders/gate_detail/manifest.json')['records']
    selected=[cube[i] for i in (0,6,10)]
    selected += [next(r for r in detail if r['label']==name+' lintel G8 front') for name in ('TASK30_GATE','FOLD_P8',lead)]
    # All three cube fronts share900 units; gate fronts share1800 units.
    sheet(selected,ROOT/'renders/TASK31_opening_depth_sheet.png',3,1300)
    target=ROOT/'references';target.mkdir(exist_ok=True)
    pictures=[(REPO/'output/task30_references/official_design_3.jpg','Official DGI detail / context; unmatched'),
        (REPO/'output/task30_references/R1/page_04.png','R1 p78 / tagged groups + early locks'),
        (REPO/'output/task30_references/R3/page_03.png','R3 Fig1 / control mesh before refinement'),
        (Path(cube[0]['image']),'Task30 G8 / actual flat / 900 units'),
        (Path(cube[10]['image']),'Task31 cube / actual flat / 900 units'),
        (Path(next(r for r in detail if r['label']==lead+' lintel G8 front')['image']),'Task31 gate lintel / flat / 1800 units')]
    out=Image.new('RGB',(3000,2410),(245,245,242));draw=ImageDraw.Draw(out)
    font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n);manifest=[]
    draw.text((35,25),'TASK31 / reference-grounded regional and spatial development',font=font(44),fill=(25,25,25))
    draw.text((35,95),'Original eight-panel user image reviewed inline; no local bitmap. These references are separately attributed.',font=font(27),fill=(45,45,45))
    for j,(path,label) in enumerate(pictures):
        x=j%3*1000;y=160+j//3*850
        im=ImageOps.contain(Image.open(path).convert('RGB'),(940,770));out.paste(im,(x+(1000-im.width)//2,y+(770-im.height)//2))
        draw.text((x+20,y+785),label,font=font(27),fill=(30,30,30))
        if j<3:shutil.copy2(path,target/path.name)
        manifest.append(dict(label=label,file=str(path),sha256=file_hash(path)))
    lines=[
        'R1: tagged spatial groups and differentiated weights; this is an implemented interpretation, not recovered DG code.',
        'R3: generate the coarse control topology, then refine; our bounded collars/tunnel are not its reflection/Boolean algorithm.',
        'Persistent exterior modes + CHANNEL walls maintain an exposed cube opening; edit-only control is occluded atG8.',
        'Regional contrast includes quieter areas. Independent non-repeating fine hierarchy and intersection-free solids remain unproved.',
        'Official context: michael-hansmeyer.com/digital-grotesque-I.html; paper hashes/pages and code sources in reference_sources.json.'
    ]
    for j,line in enumerate(lines):draw.text((35,1900+j*76),line,font=font(29),fill=(35,35,35))
    path=ROOT/'renders/TASK31_reference_relation_sheet.png';out.save(path)
    write(ROOT/'analysis/reference_relation_manifest.json',dict(images=manifest,sheet_sha256=file_hash(path),
        caveat='Reference scale/camera/normals unknown. Only generated comparisons are matched. User original is not fabricated.'))
    print('Final comparison, depth/opening and reference relation sheets saved.',flush=True)


def audit():
    started=perf_counter();records=[];parent_checks=0;region_checks=0
    testbytes=(REPO/'output/task31_full_tests_final.txt').read_bytes()
    text=testbytes.decode('utf-16' if testbytes.startswith(b'\xff\xfe') else 'utf-8-sig')
    assert '874 passed' in text and 'failed' not in text
    for group in ('candidates','controls','lead'):
        for p in sorted((ROOT/group).rglob('summary.json')):
            d=p.parent;s=read(p);m=load_mesh(d)
            assert file_hash(d/'mesh.npz')==s['mesh_sha256'],str(d)
            assert len(m.xyz)==s['vertices'] and len(m.faces)==s['faces'] and m.generation==s['generation']
            assert np.isfinite(m.xyz).all() and np.isfinite(m.rest).all() and s['zero_area_faces']==0
            assert s['Euler'] in (0,2) and np.array_equal(np.ptp(m.xyz,axis=0),s['extent'])
            if s.get('parent'):
                prior=Path(s['parent']);expected=s.get('parent_mesh_sha256',s.get('metadata',{}).get('parent_mesh_sha256'))
                assert file_hash(prior/'mesh.npz')==expected
                generation=read(prior/'summary.json')['generation'];assert generation+(0 if d.name=='G2_post_edit' else 1)==m.generation;parent_checks+=1
            if (d/'regional_state.npz').exists():
                if s.get('state_sha256'):assert file_hash(d/'regional_state.npz')==s['state_sha256']
                with np.load(d/'regional_state.npz') as z:
                    roles=z['face_roles'];assert roles.shape==(len(m.faces),) and np.isin(roles,[-1,0,1,2]).all()
                    if 'members' in z.files:
                        members=z['members'];assert members.shape==(len(m.faces),4) and np.isfinite(members).all() and (members>=0).all()
                        assert np.allclose(members.sum(1),1,rtol=0,atol=1e-12);region_checks+=1
            if (d/'operator_state.npz').exists():
                with np.load(d/'operator_state.npz') as z:
                    for k in z.files:
                        a=z[k];assert np.isfinite(a).all()
                        if k=='parent_faces':assert a.shape[0]==len(m.faces) and (a>=0).any(1).all() and (a<s['faces'] if not s.get('parent') else a<read(Path(s['parent'])/'summary.json')['faces']).all()
            records.append(dict(path=str(d.relative_to(ROOT)),generation=m.generation,vertices=len(m.xyz),faces=len(m.faces),Euler=s['Euler'],mesh_sha256=s['mesh_sha256']))
            del m;gc.collect()
    renders=[]
    for p in sorted((ROOT/'renders').glob('*/manifest.json')):
        for r in read(p)['records']:
            assert file_hash(Path(r['stage'])/'mesh.npz')==r['mesh_sha256'] and file_hash(r['image'])==r['image_sha256']
            assert r['flat_normals'] and not r['smoothing'] and r['occupied_pixels']>0
            if r.get('visibility_sha256'):assert file_hash(Path(r['image']).with_suffix('.visibility.npz'))==r['visibility_sha256']
            renders.append(dict(manifest=str(p.relative_to(ROOT)),label=r['label'],width=r['physical_width'],outside_frame=r['outside_frame']))
    for kind in ('cube','gate'):
        stages=read(ROOT/f'renders/{kind}_progression/manifest.json')['records'];assert len(stages)==9
        assert all(r['outside_frame']==0 for r in stages)
        assert len({json.dumps(r['camera_pose']) for r in stages})==1
        proof=read(ROOT/f'analysis/geometry_validation_{kind}.json');assert proof['exact_G0_to_G8_regeneration'] and proof['actual_G7_checkpoint_continuation']
        assert proof['definition_sha256']==file_hash(ROOT/f'definitions/verified_{kind}_pipeline.json')
        native=read(ROOT/f'dcc/TASK31_{kind.upper()}_LEAD_import_evidence.json')
        assert native['exact_XYZ_oriented_faces'] and native['headless_document_open']
        assert native['OBJ_sha256']==file_hash(ROOT/f'dcc/TASK31_{kind.upper()}_LEAD.obj')
        assert native['native_sha256']==file_hash(ROOT/f'dcc/TASK31_{kind.upper()}_LEAD.3dm')
    unchanged=[]
    for name in ('weighted_subdivision.py','generational_subdivision.py','sharp_subdivision.py','dual_subdivision.py','subdivision_pipeline.py','progressive_gates.py'):
        path='src/cheshire/'+name;old=subprocess.check_output(['git','show',BASELINE+':'+path],cwd=REPO)
        assert old.replace(b'\r\n',b'\n')==(REPO/path).read_bytes().replace(b'\r\n',b'\n');unchanged.append(path)
    (ROOT/'test_logs').mkdir(exist_ok=True);shutil.copy2(REPO/'output/task31_full_tests_final.txt',ROOT/'test_logs/full_tests.txt')
    jobs=[dict(job=p.parent.name,**read(p)) for p in sorted((ROOT/'logs').glob('*/process.json'))]
    successful=[j for j in jobs if j['exit_code']==0];failed=[j for j in jobs if j['exit_code']!=0]
    assert all(j['resource_stop'] is None for j in jobs)
    assert [j['job'] for j in failed]==['render_cube2']
    write(ROOT/'analysis/performance.json',dict(jobs=jobs,failed_attempts=failed,
        successful_guarded_seconds=sum(j['seconds'] for j in successful),peak_tree_plus_driver_bytes=max(j['sampled_peak_tree_plus_driver_bytes'] for j in successful),
        scope='Measured generation/render/verification/section jobs; native host separately measured; not total agent elapsed time.'))
    write(ROOT/'analysis/validation_summary.json',dict(status='PASS',tests_passed=874,skipped=0,saved_geometry_stages=len(records),
        parent_hash_checks=parent_checks,regional_state_checks=region_checks,records=records,flat_render_checks=len(renders),renders=renders,
        exact_baseline_replay=read(ROOT/'analysis/task30_exact_replay.json'),unchanged_sources=unchanged,seconds=perf_counter()-started,
        caveat='All generated-stage summaries were computed with closed opposite-oriented two-face incidence and finite/nonzero-area checks. This audit rereads geometry, hashes and region state; full deterministic replay independently verifies both leads. No intersection-free solid claim.'))
    print('All saved stages, actual renders, parent/state hashes, exact replays and native imports audited.',flush=True)


def bind():
    """Bind the already completed gate replay to an immutable per-specimen snapshot.
    Its original full-selection hash and every actual step definition must match.
    This changes no geometry evidence and does not claim another regeneration.
    """
    path=ROOT/'analysis/geometry_validation_gate.json';proof=read(path)
    assert proof['definition_sha256']==file_hash(ROOT/'definitions/task31_lead_pipeline.json')
    definition=read(ROOT/'definitions/task31_lead_pipeline.json')['gate']
    for g in range(1,9):
        summary=read(ROOT/'candidates/gate'/definition['id']/f'G{g}/summary.json')
        assert summary['metadata']['regional_definition']==definition
    snapshot=ROOT/'definitions/verified_gate_pipeline.json';assert not snapshot.exists()
    write(snapshot,dict(kind='gate',definition=definition,base_pipeline_sha256=file_hash(PREVIOUS/'definitions/final_selected_pipeline.json')))
    proof['original_complete_selection_sha256']=proof['definition_sha256'];proof['definition_sha256']=file_hash(snapshot)
    proof['binding']='Original replay used full selection hash; exact hash and8 saved actual step definitions checked before immutable per-specimen binding. No extra geometry replay claimed.'
    write(path,proof);print('Existing exact gate proof bound to immutable per-specimen definition.',flush=True)


def reports():
    selected=read(ROOT/'definitions/task31_lead_pipeline.json');cube=read(ROOT/'lead/cube/G8/summary.json');gate=read(ROOT/'lead/gate/G8/summary.json')
    decision=(ROOT/'analysis/final_decision.md').read_text(encoding='utf-8');validation=read(ROOT/'analysis/validation_summary.json')
    caveat='Combined versus tunnel-only changes exterior regional controls AND CHANNEL wall controls. Their coupled effect is demonstrated; CHANNEL alone is not independently isolated by this bounded family. The fold-based selected lead also has no matched remeasured-fold case; the memory ablation is axis-based, so persistent memory alone is not proved necessary.'
    if caveat not in decision:
        decision+='\n\nCausal attribution limit: '+caveat+'\n'
        (ROOT/'analysis/final_decision.md').write_text(decision,encoding='utf-8')
    response=(ROOT/'analysis/stageB_gate_transfer_decision.md').read_text(encoding='utf-8')
    table='\n'.join(f"| {kind} G{g} | {s['vertices']:,} | {s['faces']:,} | {s['Euler']} |" for kind in ('cube','gate') for g in range(9) for s in [read(ROOT/f'lead/{kind}/G{g}/summary.json')])
    report=f'''PARTIAL

# Task31 results — regional identity, depth and opening

Cube의 명시적 통로와 영역별 반응에서 Task30보다 의미 있는 개선을 확인하고,
같은 방법을 기존 기본 gate에 다시 도입했습니다. 디자인적 정체성과 비반복적인
미세 성장의 해결 여부는 아래 실제 비교 결과와 한계를 기준으로 판단합니다.

Baseline: `{BASELINE}`. Branch: `{BRANCH}`.
Exact local commit is recorded after commit in E:/CHESHIRE_DATA/task31/analysis/repository_commit.json.
No push, merge or Task32. Original Task30 artifacts and basic-gate source are unchanged.

{decision}

{response}

## Concrete implementation

One declared nonstationary Task30 schedule; G1–G5 CC with current-fold locks endingG4,
G6/G7 DS, G8 nonzero reference-coupled CC. Saved persistent four-mode face memberships
are born from actual G2 normals or local signed neighbour displacement. CC inherits the
real parent; DS averages every incident source face. Explicit G2 edit walls get CHANNEL.
Actual controls blend `(1-alpha)*Task30 resolved intrinsic + alpha*mode mixture`,
using current incident local scales. No random noise, surface texture, post-smoothing or
semantic body/neck/shoulder pipeline. Labels name intentions, not proven visual motifs.

Cube lead `{selected['cube']['id']}`: {cube['vertices']:,}V/{cube['faces']:,}quadF, Euler{cube['Euler']}.
Gate lead `{selected['gate']['id']}`: {gate['vertices']:,}V/{gate['faces']:,}quadF, Euler{gate['Euler']}.
Cube starts from the exact Task30 G0/G1/G2 checkpoints. Gate is exactly existing
`gate_input('RECT',False)`,74V/80F, original frame, same schedule control and treatments.
The designed tunnel adds one handle to the original closed surface. It is not spontaneous
porosity. Genus alone does not ensure an exposed or usable opening; visibility and sections
are compared separately. Recess edits retain Euler2 and are not through tunnels.

Polygon DS is a necessary compatibility enabler: original gate foot centres have valence8,
and tunnel collars create valence5. Tri/quad Eq5/6 preserve exact existing results; n>4 uses
the published standard positive cosine mask, plus declared local normal offset. Modified
Hansmeyer w1 is inactive on those polygons and its actual indices/counts are logged.
No unpublished n-gon modified mask is invented. All cyclic fans include complete parents;
disconnected vertex fans are explicitly rejected. No implicit triangulation of geometry.
The generic field's planarity diagnostic on n>4 remains a fourth-point proxy; this study
uses NORMAL_VARIATION, not that planarity diagnostic, as its intrinsic driver.
After DS, actual point classes are unknown for the CC Eq4 stencil: G8 falls back
to Eq1, so w3/w4 are explicitly inactive there, as in Task30. Other resolved controls
remain active; the final step is not an all-zero smoothing cleanup.

Reference-coupled CC adds an opt-in resolved-control argument and variable padding width.
Default behaviour is unchanged: exact Task30 G1..G8 coordinate/topology/rest/class/anchor
replay passed. Old bounded DS and legacy operators are untouched. This is mild opt-in
consolidation, not a default pipeline replacement.

## Evidence and reproducibility

StageA:18 new variants + unchanged Task30 cube control.
StageB:4 gate transfers + identical basic-gate Task30-schedule control.
All selected leads have actual G0..G8, separate G2_post_edit and complete parent arrays.
Both leads regenerated exactly including membership/control/operator state. ReloadedG7
continuation reproducesG8 exactly. Actual .17g OBJ reread and installed Rhino8.18 3DM
read/write/headless-document import preserve double XYZ and oriented polygons exactly.
{validation['tests_passed']} tests passed, zero skipped, actual HDMola1.0.0/coreclr backend.
{validation['saved_geometry_stages']} saved states audited, including controls and lead copies.

| Stage | Vertices | Polygons | Euler |
|---|---:|---:|---:|
{table}

Important images: `renders/TASK31_cube_variants.png`, `TASK30_vs_TASK31_cube.png`,
`TASK31_cube_detail_comparison.png`, `TASK31_opening_depth_sheet.png`,
`TASK31_cube_sections.png`, `TASK31_gate_sections.png`, `TASK31_gate_progression.png`,
`TASK30_vs_TASK31_gate.png`, `TASK31_reference_relation_sheet.png`.
Matched images use actual saved geometry, flat normals, fixed clay/light and physical
camera framing. Intentional close crops are logged; full progressions do not clip vertices.
Saved visibility masks measure rays where actual background is visible. They do not infer
genus from shadows. Analytical section segments come from saved polygon geometry;
display triangulation never changes checkpoints or exported polygons.

One early render attempt reached a still-writing NPZ and failed with EOFError. Geometry
generation completed intact; `cube2_complete` is the complete replacement comparison.
Failed logs and partial images are retained transparently. No resource-stop or invalid
geometry fallback occurred. See performance.json for actual sampled process memory/time.
The first3GB review bundle passed every payload CRC/SHA check, then failed when the
legacy whole-file SHA helper allocated the entire ZIP in RAM. Final packaging uses
4MiB streaming hashes; the initial archive is retained as logs/review_bundle_first.zip
and excluded from the final payload to prevent embedding a second full geometry bundle.
This packaging correction changes no geometry or generative assessment.

## Reference grounding

Three user PDFs were fully read in Task30; focused Task31 reread: Hansmeyer2010 p77–81
tagged groups/locks/nonlinear topology; Bader/Oxman2016 Fig1 and control-mesh refinement;
Blanco/Madrid2024 process/design interview context. These are evidence, not instructions.
Additional primary sources: Hansmeyer's official columns and Digital Grotesque pages,
OpenSubdiv face-uniform parent inheritance source, CGAL Euler operations documentation,
and COMPAS cosine DS source. New paper/image/code URLs, page locations and hashes are
in reference_sources.json and reference_research_matrix.md.

[Hansmeyer2010](https://doi.org/10.2312/COMPAESTH/COMPAESTH10/075-081)
supports differentiated tagged weights; [Bader/Oxman2016](https://doi.org/10.1016/j.cad.2016.09.002)
supports separating control topology from refinement. Our collar/annulus operation is
an independently implemented bounded interpretation, not their reflection/Boolean code,
not CGAL integration, and not the unpublished Digital Grotesque implementation.
[Official DGI](https://michael-hansmeyer.com/digital-grotesque-I.html) is context only;
the original user progression has no local bitmap and is not falsely reproduced.

The optional image-led atlas is deferred; `docs/TASK31_ARCHIVE_FOLLOWUP_PLAN.md` lists
categories, source paths, verification needs and reusable evidence.
Main geometry/replay/file-validation work is complete before packaging/local commit.
'''
    (ROOT/'docs').mkdir(exist_ok=True);(ROOT/'docs/TASK31_RESULTS.md').write_text(report,encoding='utf-8');(ROOT/'FINAL_REPORT.md').write_text(report,encoding='utf-8')
    handoff=f'''# Task31 handoff

Status PARTIAL. Baseline `{BASELINE}`; branch `{BRANCH}`. Exact final commit is external
`analysis/repository_commit.json`, stamped after local commit. No push/merge/Task32.
Cube lead `{selected['cube']['id']}`; gate lead `{selected['gate']['id']}`.
Read final_decision.md and stageB_gate_transfer_decision.md before changing recipes.

Canonical base remains exact Task30 U_67_LOCK_END4. All selected new controls are opt-in.
Use `cheshire.regional_generation.advance(mesh,roles,members,spec,definition)` with
actual persistent memberships. AtG2, create tags with birth() and the one declared
coarse_edit(); keep actual pre/post edit separately. Do not rebuild tags from face IDs
or pretend a multi-parent DS face has one ancestor. New wall CHANNEL controls are a
material part of the selected mechanism. Omitting them reproduced occluded openings.

`tools/task31_study.py` contains bounded18 cube definitions and exact basic_gate().
`task31_evidence.py` proves complete regeneration and actual checkpoint continuation;
it creates new lead directories and refuses an existing destination. For portable
reproduction call the API into a fresh directory. Do not rerun preparation/generation
in completed paths or delete the retained controls/negative cases. The selected
definitions include fullprecision Task30 base, modes, memory and coarse edit.

Selected states: E:/CHESHIRE_DATA/task31/lead/cube,G0..G8 and G2_post_edit;
same under lead/gate. regional_state.npz has actual face_roles/members. Operator state
has actual parent supports, local scales and resolved controls. mesh.npz preserves
double XYZ, full polygons, point classes, positive cage association and anchors.
Lead copies retain their original candidate parent paths explicitly, not invented chains.
Final output OBJ/3DM in dcc, original unresolved units/frame; native normals display-only.

General polygon DS is separate from Task30's bounded DS. It uses exact tri/quad Eq5/6
and standard cosine for n>4 with w1 deliberately inactive. Generation mismatch,
unknown scheme/memory and disconnected fans fail explicitly. Default reference CC
retains exact Task30 replay. No new default for other clients and no repository rewrite.

Tests:874 passed, zero skipped. Set CHESHIRE_MOLA_DLL to actual
C:/Users/USER/Libraries/HDMola/1.0.0/HDMola.dll and PYTHONNET_RUNTIME=coreclr.
Use fresh external --basetemp and -p no:cacheprovider. Native evidence uses installed
Rhino8.18 via tools/task31_native.ps1 under Windows PowerShell5.1, hidden headless core.

Image-led atlas deferred; follow TASK31_ARCHIVE_FOLLOWUP_PLAN.md if separately requested.
Research distinctions: exposed opening versus designed genus; differential suppression
versus novel fine hierarchy; image metrics versus style fidelity; topology/readability
versus intersection-free solid. The latter two remain unresolved, not implied passes.
'''
    (ROOT/'docs/TASK31_HANDOFF.md').write_text(handoff,encoding='utf-8')
    for name in ('TASK31_RESULTS.md','TASK31_HANDOFF.md'):shutil.copy2(ROOT/'docs'/name,REPO/'docs'/name)
    shutil.copy2(REPO/'docs/TASK31_ARCHIVE_FOLLOWUP_PLAN.md',ROOT/'docs/TASK31_ARCHIVE_FOLLOWUP_PLAN.md')
    print('Task31 results and handoff saved.',flush=True)


def publish(existing=False):
    dest=REPO/'studies/task31'
    if existing:assert read(dest/'ARTIFACTS.json')['root']==str(ROOT)
    dest.mkdir(exist_ok=existing)
    for group in ('analysis','definitions','docs'):
        for p in (ROOT/group).glob('*'):
            if p.is_file() and str(p.relative_to(ROOT)).replace('\\','/') not in POSTCOMMIT:
                d=dest/group/p.name;d.parent.mkdir(exist_ok=True);shutil.copy2(p,d)
    for p in (ROOT/'renders').glob('TASK*.png'):
        d=dest/'renders'/p.name;d.parent.mkdir(exist_ok=True);shutil.copy2(p,d)
    snapshot=ROOT/'source';snapshot.mkdir(exist_ok=True)
    for name in OWN:
        d=snapshot/name;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/name,d)
    manifest=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=file_hash(p)) for p in sorted(ROOT.rglob('*'))
        if p.is_file() and str(p.relative_to(ROOT)).replace('\\','/') not in POSTCOMMIT|{FIRST_BUNDLE}]
    write(dest/'ARTIFACTS.json',dict(root=str(ROOT),files=manifest,large_geometry='Actual checkpoints and OBJ/3DM retained externally, indexed by SHA256.',
        scope='Pre-commit artifact/source snapshot. Commit stamp and ZIP validation are added afterward; ZIP payload manifest independently indexes all bundled files.'))
    (dest/'README.md').write_text('PARTIAL\n\nTask31 regional/depth/opening research. See docs/TASK31_RESULTS.md and analysis/final_decision.md. Full actual geometry and native files are in E:/CHESHIRE_DATA/task31; ARTIFACTS.json indexes their hashes. Cube18 + gate4 transfers and unchanged controls. No push/merge/Task32.\n',encoding='utf-8')
    print('Repository review snapshot and exact source copies saved.',flush=True)


def refresh():
    publish(existing=True)


def bundle():
    started=perf_counter();path=ROOT/'CHESHIRE_TASK31_REVIEW.zip'
    assert not path.exists()
    excluded=POSTCOMMIT-{ 'analysis/repository_commit_payload.json' }|{FIRST_BUNDLE}
    payload=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and str(p.relative_to(ROOT)).replace('\\','/') not in excluded]
    assert shutil.disk_usage(ROOT).free>sum(p.stat().st_size for p in payload)+1024**3,'Insufficient measured disk capacity for retained ZIP.'
    index=[dict(path=str(p.relative_to(ROOT)).replace('\\','/'),bytes=p.stat().st_size,sha256=file_hash(p)) for p in payload]
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3,allowZip64=True) as z:
        z.writestr('REVIEW_PAYLOAD_MANIFEST.json',json.dumps(index,ensure_ascii=False,indent=2))
        for p in payload:z.write(p,str(p.relative_to(ROOT)).replace('\\','/'))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        expected=read(ROOT/'analysis/repository_commit.json');assert json.loads(z.read('analysis/repository_commit_payload.json'))['commit']==expected['commit']
        for item in index:
            h=hashlib.sha256();size=0
            with z.open(item['path']) as stream:
                for chunk in iter(lambda:stream.read(4*1024*1024),b''):h.update(chunk);size+=len(chunk)
            assert size==item['bytes'] and h.hexdigest()==item['sha256'],item['path']
    write(ROOT/'analysis/review_zip_validation.json',dict(path=str(path),bytes=path.stat().st_size,sha256=file_hash(path),entries=len(index)+1,
        full_CRC_pass=True,all_payload_SHA256_pass=True,commit=expected['commit'],seconds=perf_counter()-started,
        excluded='ZIP itself and its validation/postcommit live stamp; exact commit included as repository_commit_payload.json.'))
    print('Review ZIP: every CRC and payload SHA256 PASS.',flush=True)


def stamp():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=REPO,text=True).strip()
    status=subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip()
    assert branch==BRANCH and not status,status
    write(ROOT/'analysis/repository_commit.json',dict(commit=commit,branch=branch,clean_worktree=True,no_push_or_merge=True,baseline=BASELINE))
    shutil.copy2(ROOT/'analysis/repository_commit.json',ROOT/'analysis/repository_commit_payload.json')
    print(commit,branch,'clean',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['visuals','audit','reports','publish','refresh','bundle','stamp','bind']);a=p.parse_args()
    globals()[a.action]()
