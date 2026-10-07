"""Task29 final evidence assembly. No geometry cleanup or consolidation."""
import argparse, gzip, hashlib, json, shutil, subprocess, sys, zipfile
from pathlib import Path
from time import perf_counter
import importlib.metadata, platform

import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
from task29_search import ROOT,BASELINE,load_mesh,save_mesh
from cheshire.reference_subdivision import ArrayMesh
from cross_cell_crease_study import read,write,file_hash


def requests():
    """Create capture requests; all compared objects retain original XYZ."""
    old=Path('E:/CHESHIRE_DATA/task28/lead/G5/geometry.json.gz')
    d=json.loads(gzip.decompress(old.read_bytes()))
    ids={v['id']:i for i,v in enumerate(d['vertices'])}
    xyz=np.asarray([v['xyz'] for v in d['vertices']],float)
    q=np.asarray([[ids[v] for v in f['vertices']] for f in d['faces']],np.int64)
    stage=ROOT/'comparison/task28/G5'
    if not stage.exists():
        save_mesh(stage,ArrayMesh(xyz,q,np.full(len(xyz),-1,np.int8),xyz.copy(),np.full((len(q),3),-1,np.int64),5),
                  dict(source=str(old),source_sha256=file_hash(old),coordinate_changes='None; ID/index remapping only.'))
    # A single physical width covers all nine actual stages.
    write(ROOT/'definitions/render_final_progression.json',dict(resolution=1400,width=2600,target=[0,0,0],cols=3,size=900,pages=9,
        sheet_name='FINAL_LEAD_PROGRESSION.png',items=[dict(label=f'G{g}',stage=str(ROOT/f'lead/G{g}')) for g in range(9)]))
    write(ROOT/'definitions/render_task28_comparison.json',dict(resolution=1600,width=2600,cols=2,size=1100,pages=2,
        sheet_name='TASK28_VS_TASK29.png',items=[
            dict(label='Task28 P4 G5 / actual saved column',stage=str(stage),target=[0,0,900]),
            dict(label='Task29 FINAL_DX00 G8 / actual cube lineage',stage=str(ROOT/'lead/G8'),target=[0,0,0])]))
    write(ROOT/'definitions/render_lead_details.json',dict(resolution=1500,width=2600,cols=3,size=1000,pages=6,
        sheet_name='lead_details.png',items=[
            *[dict(label=f'G{g} / same 700-unit detail crop',stage=str(ROOT/f'lead/G{g}'),width=700,target=[0,-350,0],angles=[0,0]) for g in [3,5,8]],
            *[dict(label='G8 / '+name,stage=str(ROOT/'lead/G8'),target=[0,0,0],angles=angles)
              for name,angles in [('front',[0,0]),('oblique',[28,22]),('upper',[12,62])]]]))
    # Isolate the added rules on a common cube base at the same final resolution.
    same=[('Base C00 G8','round_C/C00_B000_0'),('Intrinsic D00_3 G8','intrinsic_final/DL_D00_3'),
          ('Intrinsic + locks DX00 G8','final_followups/FINAL_DX00'),
          ('D00_3 unchanged G8','intrinsic_final/DL_D00_3'),
          ('D00_3 + welded G4 / G8','final_followups/FINAL_E_D00_3_ADJACENT_4_0.45')]
    write(ROOT/'definitions/render_rule_isolation.json',dict(resolution=1400,width=2600,cols=3,size=900,pages=6,
        sheet_name='rule_contribution_isolation.png',items=[dict(label=label,stage=str(ROOT/f'candidates/{rel}/G8'),target=[0,0,0]) for label,rel in same]))
    from task29_views import sheet
    records=[]
    for tag in ['intrinsic_D','intrinsic_retention']:
        records.extend(read(ROOT/f'renders/{tag}/manifest.json')['records'])
    assert len(records)==64
    sheet(records,ROOT/'renders/intrinsic_variation_sheet.png',4,560)
    from progressive_gate_views import depth_order_check
    depth_order_check(ROOT/'analysis/depth_order_check.json')
    print('Final requests, 64-variant sheet and actual depth fixture saved.',flush=True)


def aggregate():
    broad=read(ROOT/'analysis/broad_search_log.json')
    # Preserve the original A log and add references to all continuation logs.
    if not (ROOT/'analysis/round_A_log.json').exists():write(ROOT/'analysis/round_A_log.json',broad)
    categories={'round_A':('round_A_log.json',256),'round_B':('round_B_log.json',128),'round_C':('round_C_log.json',8),
                'intrinsic':('intrinsic_log.json',32),'intrinsic_retention':('intrinsic_retention_log.json',32),'topology':('topology_log.json',24)}
    totals={}
    for category,(name,n) in categories.items():
        data=read(ROOT/'analysis'/name)
        records=data.get('results',data.get('round_A'));assert len(records)==n
        totals[category]=dict(definitions=len(records),completed=sum(r.get('status')!='REJECTED_EXPLICITLY' for r in records),log=name)
    extra={name:len(read(ROOT/'analysis'/name)['results']) for name in ['intrinsic_final_log.json','final_followups_log.json']}
    write(ROOT/'analysis/broad_search_log.json',dict(rounds=totals,base_search_definitions=480,
        additional_matrix_controls=3,additional_lock_ablation_controls=1,additional_continuation_records=sum(extra.values()),
        total_executed_definition_records=495,continuations=extra,G8_lineages=20,
        count_policy='A/B/C/D/E candidate definitions counted once; controls and later extensions reported separately. 32 A finalists each receive four late schedules. No count reduction.',
        visual_selection='Every A/B/C/D/E contact page and every final followup reviewed; selection manifests retain actual decisions. No metric threshold substitutes for visual judgment.'))
    write(ROOT/'analysis/intrinsic_variation_log.json',dict(variants=64,
        first_32=read(ROOT/'analysis/intrinsic_log.json'),additional_32=read(ROOT/'analysis/intrinsic_retention_log.json'),
        late_first_family=read(ROOT/'analysis/intrinsic_final_log.json'),late_final_followups=read(ROOT/'analysis/final_followups_log.json'),
        conclusion='Current geometry fields differentiate neighbouring descendants. Fold locks retain earlier vertices but leave angular clusters and repetitive fine cells. Exact rules/lock masks are saved; no unpublished DG algorithm equivalence claimed.'))
    performance=[]
    for p in sorted((ROOT/'logs').glob('*/process.json')):
        d=read(p);performance.append(dict(job=p.parent.name,**d))
    write(ROOT/'analysis/performance.json',dict(jobs=performance,
        measured_guarded_seconds=sum(p['seconds'] for p in performance),
        peak_sampled_tree_plus_driver_bytes=max(p['sampled_peak_tree_plus_driver_bytes'] for p in performance),
        exact_regeneration_OBJ_seconds=read(ROOT/'analysis/geometry_validation.json')['seconds'],
        native=read(ROOT/'dcc/TASK29_LEAD_import_evidence.json'),
        scope='Sum of measured job elapsed durations, including failed setup attempt; not total human/agent elapsed time. Guarded peak samples process tree plus driver. Native host peak separately measured. No resource guard stopped generation.'))
    print('Search counts and measured performance assembled.',flush=True)


def ablation():
    d=read(ROOT/'definitions/selected_nonstationary_schedule.json')
    d['id']='LOCK_ABLATION_DX00';d['parent']=str(ROOT/'candidates/round_A/A000/G2')
    del d['intrinsic']['lock_threshold']
    write(ROOT/'definitions/lock_ablation_selection.json',dict(definitions=[d],
        controlled_change='Only lock_threshold removed from FINAL_DX00; cube, actual G2 checkpoint, all eight base rows, intrinsic field and intervals remain identical.'))


def isolation_request():
    same=[('Base C00 G8 / no intrinsic','round_C/C00_B000_0'),
          ('DX00 same fields / no locks','lock_ablation/LOCK_ABLATION_DX00'),
          ('DX00 same fields / with locks','final_followups/FINAL_DX00'),
          ('D00_3 unchanged G8','intrinsic_final/DL_D00_3'),
          ('D00_3 welded G4 / G8','final_followups/FINAL_E_D00_3_ADJACENT_4_0.45')]
    write(ROOT/'definitions/render_rule_isolation_exact.json',dict(resolution=1600,width=2600,cols=3,size=1000,pages=6,
        sheet_name='rule_contribution_isolation.png',items=[dict(label=label,stage=str(ROOT/f'candidates/{rel}/G8'),target=[0,0,0]) for label,rel in same]))


def audit():
    start=perf_counter();records=[];parent_checks=0
    candidates=[ROOT/'input/G0/summary.json',*sorted((ROOT/'candidates').rglob('summary.json'))]
    for p in candidates:
        d=p.parent;s=read(p);m=load_mesh(d)
        assert file_hash(d/'mesh.npz')==s['mesh_sha256']
        assert len(m.xyz)==s['vertices'] and len(m.faces)==s['faces'] and m.generation==s['generation']
        assert np.isfinite(m.xyz).all() and np.isfinite(m.rest).all()
        assert np.array_equal(np.ptp(m.xyz,axis=0),s['extent'])
        assert m.faces.min()>=-1 and m.faces.max()<len(m.xyz)
        assert m.anchors.shape==(len(m.faces),3) and len(m.classes)==len(m.xyz)
        parent=s.get('parent');meta=s.get('metadata',{})
        if parent:
            parent=Path(parent);prior=read(parent/'summary.json')
            assert meta['parent_mesh_sha256']==prior['mesh_sha256']==file_hash(parent/'mesh.npz')
            assert prior['generation']+1==m.generation
            parent_checks+=1
        if meta.get('implementation')=='REFERENCE_COUPLED':
            with np.load(d/'operator_state.npz') as z:
                assert all(np.isfinite(z[k]).all() for k in z.files)
        records.append(dict(stage=str(d.relative_to(ROOT)),sha256=s['mesh_sha256'],generation=m.generation,
                            vertices=len(m.xyz),faces=len(m.faces),zero_area_faces=s['zero_area_faces'],Euler=s['Euler']))
    renders=[]
    for p in sorted((ROOT/'renders').glob('*/manifest.json')):
        for r in read(p)['records']:
            if r.get('rendered_geometry') is False:continue
            stage=Path(r['stage']);mesh=stage if stage.suffix=='.npz' else stage/'mesh.npz'
            assert file_hash(mesh)==r['mesh_sha256'] and file_hash(r['image'])==r['image_sha256']
            assert r['flat_normals'] and not r['smoothing'] and r['occupied_pixels']>0
            renders.append(dict(manifest=str(p.relative_to(ROOT)),image=Path(r['image']).name,
                                outside_frame=r['outside_frame'],physical_width=r['physical_width']))
    final=read(ROOT/'renders/final_progression/manifest.json')['records']
    assert len(final)==9 and all(r['outside_frame']==0 for r in final)
    assert len({json.dumps(r['camera_pose']) for r in final})==1
    assert len({r['physical_width'] for r in final})==1
    legacy=[]
    for name in ['weighted_subdivision.py','generational_subdivision.py','sharp_subdivision.py']:
        relative='src/cheshire/'+name;old=subprocess.check_output(['git','show',BASELINE+':'+relative],cwd=REPO)
        # Git blobs are LF; compare Python universal-newline source, preserving text content.
        now=(REPO/relative).read_bytes();same=old.replace(b'\r\n',b'\n')==now.replace(b'\r\n',b'\n');assert same
        legacy.append(dict(path=relative,baseline_blob_sha256=hashlib.sha256(old).hexdigest(),working_file_sha256=file_hash(REPO/relative),same_source_text=True))
    test=(REPO/'output/task29_backend_tests_verified.txt').read_text(encoding='utf-8-sig')
    assert '838 passed' in test and 'failed' not in test
    testdir=ROOT/'test_logs';testdir.mkdir(exist_ok=True)
    (testdir/'all_applicable_838.txt').write_text(test,encoding='utf-8')
    write(ROOT/'analysis/validation_summary.json',dict(status='PASS',applicable_tests=838,skipped=0,test_elapsed_seconds=45.76,
        backend='Actual HDMola.dll 1.0.0 under .NET coreclr; CHESHIRE_MOLA_DLL configured.',
        test_temp='A fresh external temp directory is required by the existing negative repository-identity test; workspace-contained tmp_path changes that fixture assumption.',
        all_candidate_stages=records,parent_checks=parent_checks,actual_generation_stage_count=len(records)-1,
        flat_render_hash_checks=len(renders),render_records=renders,final_fixed_camera_scale=True,
        unchanged_legacy_sources=legacy,seconds=perf_counter()-start,
        geometry=read(ROOT/'analysis/geometry_validation.json'),native=read(ROOT/'dcc/TASK29_LEAD_import_evidence.json'),
        limitations='Finite coordinates, combinatorial incidence and native readability do not establish self-intersection-free solid geometry or printability. All stages already passed generation-time closed oriented-edge checks.'))
    # Archive the setup/fixture failures transparently, rather than counting them as algorithm regressions.
    for name,encoding in [('task29_full_tests.txt','utf-16'),('task29_backend_tests.txt','utf-16'),('task29_backend_tests_final.txt','utf-8-sig')]:
        src=REPO/'output'/name
        if src.exists():(testdir/name).write_text(src.read_text(encoding=encoding),encoding='utf-8')
    print('All actual stage/parent hashes, flat renders, legacy sources and 838 tests verified.',len(records)-1,'generated stages',flush=True)


def reports():
    d=read(ROOT/'definitions/selected_nonstationary_schedule.json')
    summaries=[read(ROOT/f'lead/G{g}/summary.json') for g in range(9)]
    perf=read(ROOT/'analysis/performance.json');valid=read(ROOT/'analysis/validation_summary.json')
    seed=read(ROOT/'definitions/recovered_numeric_seeds.json')
    counts='\n'.join(f"| G{g} | {s['vertices']:,} | {s['faces']:,} | {s['mean_edge']:.3f} | {s['dihedral_median']:.2f} |" for g,s in enumerate(summaries))
    keys=['wf','w1','we','w2','wp','w3','w4','w6','w7']
    rows='\n'.join(f"| G{g} | "+' | '.join(str(r['weights'][k]) for k in keys)+' |' for g,r in enumerate(d['rows'],1))
    seedrows='\n'.join('| '+name+' | `'+','.join(str(seed[name]['weights'][k]) for k in keys)+'` | '+json.dumps(seed[name]['u_map'])+' |'
                       for name in ['C11A','C11B','C26','H1','H1B','CURVE','AMP','GENTLE','H1_NO_ATTR','T28_G3'])
    report=f'''PARTIAL

# Task29 results — actual reference audit and full staged search

기존 구현에서 발견한 같은 세대 점 의존성의 차이를 고쳤고, 단순 큐브에서 G8까지 실제 형상을 생성했다.
큰 방향 변화와 2차 접힘은 유지된다. 그러나 후기 형상은 반복되는 작은 비늘·주름과 날카로운 면이 강하다.
한스마이어 레퍼런스 수준의 지속되는 비반복 다중 스케일 구조와 평면 법선의 연속감을 증명하지 못했다.
이 판정은 A–C에 이어 D64, E24, 추가 G8 연장과 잠금 제거 대조까지 수행한 뒤 내렸다.

## Repository and verification

Baseline: `{BASELINE}`. Branch: `experiment/task29-reference-generative-search`.
The exact new local commit is recorded after committing in `analysis/repository_commit.json`;
this tracked report cannot include its own self-referential commit hash. No push or merge. Task30 is a plan only.

All applicable tests: **838 passed, zero skipped**, 45.76 seconds, with actual HDMola 1.0.0 configured under coreclr.
The preceding default run passed 816 and skipped 22 optional-backend tests. Two test environment attempts are retained:
an inaccessible old default pytest temp directory, then a workspace temp path that violated an existing negative
repository-identity fixture's outside-repository assumption. A fresh external temp directory resolved both.
No production behavior or existing tests were changed to pass those checks.
There are 20 new focused mathematical/topology cases. Passing tests establish implementation consistency,
not Digital Grotesque fidelity.

The actual G0–G8 lead regenerates with exact XYZ, oriented polygons, point classes, original-cage association,
ancestry and resolved operator state. Actual G7 reload continues to exact G8. Every generation's OBJ is reread exactly.
The installed Rhino 8.18 writes and rereads the final 3DM with exact coordinates and oriented polygons;
`RhinoDoc.OpenHeadless` opens its one actual mesh. Display normals only are computed in the native file.
No geometry welding, smoothing, triangulation, scaling or repair is applied to the lead export.
GPU depth ordering was independently verified on a two-triangle fixture.
All {valid['actual_generation_stage_count']} actual generated candidate stages, parent links and flat-render source/image hashes were audited.
Legacy weighted/generational/sharp source content matches the Task28 baseline. Original results coexist with the new path.

## Equations and scale decision

The actual [Bridges 2010 paper](https://archive.bridgesmathart.org/2010/bridges2010-167.pdf), including Figure 2,
was read rather than relying on Task28 summaries. Full transcription and the ambiguity analysis are in
`analysis/reference_equation_audit.md`.

The legacy path uses original face centroids for Eq2 and Eq3, and later moves faces separately using Eq4/10.
The reference path completes Eq1/4 then Eq10 faces, feeds those faces to Eq2 and Eq3, and completes Eq11 edges.
Eq3 uses **original endpoint midpoints**, not extruded Eq2 edges; this agrees with Figure 2 and the neutral CC mask.
Consequently face displacement propagates to edges and corners, except at coefficient cancellation;
edge extrusion does not feed the same-iteration corner. Eq4 uses previous-generation input point provenance.
Eq10's completion order is explicit because the paper does not publish executable scheduling code.
This is an audited published-equation implementation with documented conventions, not the unpublished DGII program.

Local Sf = mean current face-perimeter edge length; Se = mean the two incident Sf;
Sv = mean incident Sf. Global S = mean unique current edge length. wf/we/wp are ratios multiplied by S.
Face normals are unit area-vector normals; edge normals are arithmetic incident unit-normal means without
renormalization; vertex normals are normalized incident means. Local scalar and vertex-normal conventions
are deterministic choices where the paper does not specify a unique implementation.

## Mechanism matrix

Same cube and exact five-row schedule, same flat normals, clay, camera and 2600-unit frame:
M0 LEGACY_ISOLATED/GLOBAL_SCALE; M1 REFERENCE_COUPLED/GLOBAL_SCALE; M2 REFERENCE_COUPLED/LOCAL_INCIDENT_SCALE.
G0–G5 saved for all. M0 vs M1 already changes G1 extents from 1467.1 to 1579.1 units.
M1/M2 are exactly identical at G1/G2 while symmetric incident scales coincide. Their corresponding-coordinate
RMS differences at G3/G4/G5 are 4.9233/4.6358/5.1421 units. Local scale has a real later effect, but no convincing
hierarchy advantage large enough to claim success. Continue M2 as the reference/local hypothesis, not because a score proved it superior.

## Exact seed recovery and count policy

18 actual saved recipe/schedule records from Tasks20–28 were reread and SHA256 checked before sampling.
The inventory records originating commit, actual parameters, generation, implementation, visual behavior and known failure.
Historical gate support, crease-only wrappers, dynamic-profile semantics and Mola experiments remain evidence;
they are not smuggled into the cube. H1/H1B absolute offsets are divided by initial side1000 before use as ratios.
Old Task25 efficient/uncalibrated flow recipes were also recovered as sources without claiming they worked on the cube.

Weight order below: wf,w1,we,w2,wp,w3,w4,w6,w7. Ratios after explicit normalization:

| seed | exact round-trip decimal row | u map |
|---|---|---|
{seedrows}

The actual search reuses C11A/B, C26, H1, H1B, CURVE, AMP, GENTLE and exact Task28 G3;
it includes interpolation, 1.25/1.3 strength expansion, offset sign reversal and cross-generation combinations.
ZERO is retained only as historical reference and neutral mathematical calibration, never used in the lead.

**480 search candidate definitions**, plus three matrix controls, one exact locking ablation and eleven later
continuation definition records = **495 executed definition records**, **20 actual G8 lineages**.
Counts were not reduced for time or memory.

| phase | actual experiment |
|---|---|
| A | 256 deterministic 8×8×4 nonstationary schedules, all G1–G3 |
| B | 32 visually selected A finalists × four nonzero late schedules = 128, actual G4/G5 |
| C | eight visually selected B finalists, actual G6/G7/G8 |
| D | four bases × eight intrinsic rules = 32; another 32 field/threshold/sign retention rules = 64 total |
| E | three strongest initial D bases × two scopes × two timings × two thresholds = 24 |
| later extensions | four initial D, four additional D and three changed E paths to G8; these are eleven continuations |
| exact ablation | selected DX00 fields/rows without locking, same actual G2, actual G3–G8 |

All 256 A, 128 B, eight C late progressions, 64 D, 24 E and later G8 followups were viewed through contact pages.
Cheap extent/dihedral/normal/scale diagnostics assisted inspection. They did not decide the lead or success.

## Intrinsic and topology findings

D was required because globally scheduled modified subdivision continued to produce repeated cells and softened meso form.
Initial D tests NORMAL_VARIATION, ORIGINAL_EDGE_DISTANCE, PLANARITY, LOCAL_SCALE with two bounded strengths.
Additional D uses current geometry fields with vertex locking at normal-disagreement thresholds 0.12/0.28.
These are explicit CHESHIRE experiments motivated by the paper's attribute/tagged-vertex discussion.
Locking is evaluated again each generation; it preserves the current input position only where that step's mask is true.
It is not a permanent cage constraint or arbitrary ID-based displacement.

The exact ablation holds all eight base rows, intrinsic field and intervals constant and removes only locking.
`rule_contribution_isolation.png` isolates base vs intrinsic-only vs intrinsic-plus-locks, and separately compares
the same D00_3 lineage with/without the one G4 weld. The lock contribution is retention of sharper clusters,
with a substantial cost in persistent facet-angle discontinuity. Intrinsic-only variation also changes neighbouring development.
Neither establishes the requested sustained non-repeating small hierarchy.

E was required after D remained insufficient. The opt-in REFERENCE_COUPLED_LOCAL_TOPOLOGY path joins current
generated edge/face points at a threshold proportional to the smaller of their incident scales.
It deterministically selects disjoint pairs, logs coordinates and exact old/new indices, and rejects pinched polygons,
invalid oriented edge incidence, duplicate faces or disconnected vertex links. Pre-weld meshes survive every proposal.
24 proposals: **three valid changed connectivity, thirteen no eligible merges, eight explicit invalid rejections**.
The three changed paths have new valence distributions but all retain genus0/Euler2. No valid porosity or holes were produced.
At the final matching physical scale their visual difference is small; welding did not unlock new recursive motifs.
Some historical early rejection logs say PROPOSED with an invalid_reason; category outcomes record REJECTED_EXPLICITLY,
and no rejected mesh is continued. The later logging fix makes rejection status explicit without rewriting history.
The [official Digital Grotesque II description](https://michael-hansmeyer.com/digital-grotesque-II.html)
motivates a topology hypothesis; this bounded joining experiment does not reproduce its unpublished algorithm.

## Actual selected lineage and full schedule

Lead **FINAL_DX00**. Actual ancestry: input cube → A000 G1/G2 → DX00 G3/G4/G5 → FINAL_DX00 G6/G7/G8.
`lead/lineage_manifest.json` hashes the original candidate and copied actual lead mesh at each stage.
No alternate G3 and no reconstructed stage was substituted.

| generation | wf | w1 | we | w2 | wp | w3 | w4 | w6 | w7 |
|---|---|---|---|---|---|---|---|---|---|
{rows}

Every G1–G8 is REFERENCE_COUPLED + LOCAL_INCIDENT_SCALE, with genuine nonzero modified controls.
G3–G8 add the same declared intrinsic rule. No topology weld in the lead. No all-zero, standard-CC or smoothing generation.
G5–G8 repeat the exact nonzero base regime rather than trend toward zero; spatial weights remain recomputed from current geometry.
Exact intrinsic JSON:

```json
{json.dumps(d['intrinsic'],indent=2)}
```

Signal s = clip(3 × (1 − norm(mean incident unit face normals)), 0, 1).
Each specified effective control is base + low + (high−low)s; face/edge signals are the mean corner/endpoint signals.
Other controls are unchanged. Lock mask uses the unscaled current normal-disagreement ≥0.12.
Locked input vertices G3–G8: 74,242,926,2942,13382,55406. Actual per-step scales, signal, mask,
input edges, parent-face/corner mapping and original-cage association are saved, not inferred from renders.

| generation | vertices | original polygons | mean current edge | median adjacent normal angle (degrees) |
|---|---|---|---|---|
{counts}

G8 remains closed oriented combinatorial genus0: Euler2, zero zero-area faces, finite double-precision coordinates.
It is not certified self-intersection-free, watertight as a physical solid, or printable.

## Retention and visual judgment

First macro: G1. First meso: G2. G3 is the first intrinsic local variation; no generation conclusively demonstrates
the requested **persistent non-repeating** differentiated small scale. G5–G8 generate further facets and local folds,
but much of that information remains correlated with descendant cells.

Nine diagnostic patches (three born each at G1/G2/G3) follow saved face anchors to G8.
Fixed birth-normal depth ranges for representative equivalent patches are 19.999→169.741,
48.832→121.801 and 4.996→56.507 units. All tracked patches survive.
These depth ranges measure later geometry in an ancestral region, not the identity or retention ratio of a specific named ridge.
Normal/extent/RMS curves and three alternative lineages are saved. Increased amplitude may be new folding or drift;
it does not prove retained hierarchy. The actual progression shows persistent broad lobes and secondary directional changes,
while specific early sharp tips contract and fine motifs remain repetitive.

Final 700-unit identical detail crops reveal the repetitive fine folds directly.
There is partial apparent continuity along some silhouettes as facet size falls, but substantial angular clusters remain.
G8 mean edge is 6.551 units while median adjacent normal angle remains **37.83°**, p90 **91.26°**.
Dense topology by itself did not make the local normal changes small. Three qualifying scales and substantial flat-normal
continuity cannot be marked passed. Repeated fine motifs remain a major/dominant component of the small-scale surface.

Task28's actual chosen G5 column vs Task29's actual G8 cube are rendered at the same 2600-unit frame, clay,
light and oblique angles. Camera targets translate from old Z900 to new origin; neither model is scaled.
Task29 has visibly stronger retained angular secondary clusters and additional fine activity; Task28 is smoother
and loses earlier detail. The specimens differ, so this image is a contextual comparison, not a single-variable operator A/B.
The matrix and rule isolation are the controlled comparisons. Task29 improves evidence and retained activity,
but does not achieve the target Digital Grotesque quality.

## What is actually limiting

Hardware did not stop the experiment. The measured guarded generation/render jobs total
{perf['measured_guarded_seconds']:.3f}s; peak sampled tree plus driver is
{perf['peak_sampled_tree_plus_driver_bytes']:,} bytes ({perf['peak_sampled_tree_plus_driver_bytes']/2**30:.3f} GiB).
These are job-duration sums, not the entire task's elapsed time. Exact replay/OBJ validation took 10.225s;
native operation took 7.080s excluding RhinoCore cold startup, native host peak 564,768,768 bytes.
Resource/job logs contain each real stage/job time. No face-count or elapsed-time cap curtailed the requested search.

The original isolated dependencies were a material equation-fidelity problem and are now an explicit legacy mode.
Correcting them and local scale was necessary but not sufficient in the tested families.
Geometry-driven scalar rules retain cube symmetry for geometrically equivalent regions; they can differentiate
unequal neighbours but cannot create unique local treatment out of exact symmetry by themselves.
Repeated CC ancestry and broadly shared scalar weight regimes continue to seed cell motifs.
Keeping folds by freezing corner positions preserves sharp normal jumps and promotes dense angular texture.
The minimal valid edge collapses change valence without introducing a useful porous motif generator.
These are conclusions about this bounded experiment, not proof that every Hansmeyer-style system is incapable.

## Review files and next task

Open `renders/FINAL_LEAD_PROGRESSION.png` first, then `lead_details.png`, `rule_contribution_isolation.png`,
`mechanism_matrix.png`, and the search pages. All primary renders use flat normals.
Only the render's declared diagonal 0–2 display triangulation and float32 display conversion are used;
saved NPZ/OBJ/3DM retain double coordinates and original quads. Intentional detail crops disclose vertices outside frame.

Full root: `E:/CHESHIRE_DATA/task29/`. Review archive: `CHESHIRE_TASK29_REVIEW.zip`.
Model/continuation archive: `MODEL.zip`. Archive manifest/CRC/SHA verification is written in `analysis/archive_validation.json`.
Read `docs/TASK29_HANDOFF.md` for exact commands and `docs/TASK30_CONSOLIDATION_PLAN.md` for consolidation decisions.
Task30 has not started.
'''
    (ROOT/'docs').mkdir(exist_ok=True)
    (REPO/'docs').mkdir(exist_ok=True)
    for p in [ROOT/'FINAL_REPORT.md',ROOT/'docs/TASK29_RESULTS.md',REPO/'docs/TASK29_RESULTS.md']:
        p.write_text(report,encoding='utf-8')
    diagnosis='''PARTIAL

# Final diagnosis

Macro G1 and meso G2 survive in the actual G8 cube lineage. Small spatial variation begins G3,
but persistent non-repeating fine hierarchy and substantial flat-normal continuity remain unproved.
This verdict follows all A256/B128/C8, D64, E24 and 20 real G8 lineages, including exact locking ablation.

The reference equation audit found materially isolated legacy face dependencies.
The new coupled path and incident scales change real geometry. They alone do not eliminate the cell motif.
Intrinsic rules change local development; locks preserve more angular clusters but leave fine repeated texture.
Bounded welding changes three meshes validly, rejects eight proposals and creates no new genus or convincing holes.
Hardware was not the limiting factor. High face count and many passing tests do not establish reference fidelity.

| success criterion | verdict from saved flat-normal geometry |
|---|---|
| Simple G0 | PASS; eight-vertex six-face cube |
| Algorithmic G1 macro | PASS; eight input-corner protrusions and concave intervening faces |
| Later distinct meso | PASS; secondary folds within/across lobes |
| Nonuniform non-cell fine motif | INSUFFICIENT; different local development, still strongly cell-related |
| Earlier structure survives | PARTIAL; broad directions/meso survive, some sharp early tips shrink |
| Modified through late generations | PASS; all eight steps genuinely nonzero |
| No zero CC cleanup | PASS |
| Substantial flat-normal apparent continuity | INSUFFICIENT; small facets but persistent angular jumps |
| Three meaningful qualifying scales at G8 | INSUFFICIENT; macro/meso plus mostly repetitive small texture |
| Visibly more generative than Task28 | PARTIAL; sharper retained activity; different specimens disclosed |
| Added mechanism contribution isolated | PASS as experiment; matched intrinsic/lock ablation and same-base weld comparison |

Do not relabel PARTIAL because the result is dense or ugly. No claim of exact Digital Grotesque software,
solid printability or valid porosity. Keep the legacy path for exact compatibility, the new audited operator
for further use, and actual evidence. Consolidation decisions live in Task30's plan; no consolidation was performed.
'''
    (ROOT/'analysis/FINAL_DIAGNOSIS.md').write_text(diagnosis,encoding='utf-8')
    print('Full results and strict final diagnosis saved.',flush=True)


def publish():
    shutil.copy2(REPO/'studies/task29/analysis/reference_equation_audit.md',ROOT/'analysis/reference_equation_audit.md')
    for name in ['TASK29_HANDOFF.md','TASK30_CONSOLIDATION_PLAN.md']:
        shutil.copy2(REPO/'docs'/name,ROOT/'docs'/name)
    modes=read(ROOT/'definitions/mechanism_modes.json')
    modes['REFERENCE_COUPLED_LOCAL_TOPOLOGY']='Reference/local operator followed once by declared deterministic threshold join, with explicit rejection and pre-weld evidence.'
    modes['intrinsic_lock_extension']='Opt-in current normal-disagreement tag freezes input-vertex XYZ for that step only; new edge/face points remain modified.'
    write(ROOT/'definitions/mechanism_modes.json',modes)
    pdf=REPO/'output/task29_pdf/design_by_subdivision.pdf'
    write(ROOT/'analysis/primary_source_ledger.json',dict(paper=dict(
        title='Design by Subdivision',author='Michael Hansmeyer',year=2010,pages='167–174',
        URL='https://archive.bridgesmathart.org/2010/bridges2010-167.pdf',
        retrieval='Official same-host HTTP download after HTTPS returned465; no certificate bypass.',
        actual_PDF_sha256=file_hash(pdf),actual_bytes=pdf.stat().st_size,
        figure_checked='Actual rendered PDF page2 (printed168), Figure2. The paper itself is not redistributed in these packages.'),
        later_topology_URL='https://michael-hansmeyer.com/digital-grotesque-II.html'))
    versions={}
    for package in ['numpy','scipy','compas','pytest','pythonnet','pyrender','pillow','trimesh','pyglet']:
        versions[package]=importlib.metadata.version(package)
    write(ROOT/'analysis/runtime_environment.json',dict(Python=sys.version,platform=platform.platform(),
        executable=sys.executable,versions=versions,Rhino=read(ROOT/'dcc/TASK29_LEAD_import_evidence.json')['application'],
        Mola_DLL='C:/Users/USER/Libraries/HDMola/1.0.0/HDMola.dll',Mola_runtime='coreclr',
        display_GPU=read(ROOT/'renders/final_progression/manifest.json')['backend']))
    required=[*['analysis/'+n for n in ['reference_equation_audit.md','mechanism_matrix_metrics.json',
        'seed_parameter_inventory.json','seed_parameter_inventory.md','broad_search_log.json','retention_metrics.json',
        'intrinsic_variation_log.json','topology_variation_log.json','FINAL_DIAGNOSIS.md']],
        *['definitions/'+n for n in ['cube_specimen.json','mechanism_modes.json','broad_search_space.json',
        'selected_nonstationary_schedule.json','intrinsic_rules.json','topology_rules.json']],
        *['renders/'+n for n in ['mechanism_matrix.png','broad_search_contact_sheet.png','late_schedule_contact_sheet.png',
        'intrinsic_variation_sheet.png','topology_variation_sheet.png','FINAL_LEAD_PROGRESSION.png','TASK28_VS_TASK29.png','lead_details.png']],
        'dcc/TASK29_LEAD.obj','dcc/TASK29_LEAD.3dm','docs/TASK29_RESULTS.md','docs/TASK29_HANDOFF.md',
        'docs/TASK30_CONSOLIDATION_PLAN.md','FINAL_REPORT.md',*['lead/G'+str(g)+'/mesh.npz' for g in range(9)]]
    assert all((ROOT/n).is_file() for n in required)
    study=REPO/'studies/task29'
    for group,names in [('analysis',['reference_equation_audit.md','FINAL_DIAGNOSIS.md','broad_search_log.json',
        'seed_parameter_inventory.json','seed_parameter_inventory.md','retention_metrics.json',
        'performance.json','validation_summary.json','geometry_validation.json','primary_source_ledger.json','runtime_environment.json']),
        ('renders',['FINAL_LEAD_PROGRESSION.png','TASK28_VS_TASK29.png','lead_details.png','rule_contribution_isolation.png','mechanism_matrix.png'])]:
        target=study/group;target.mkdir(parents=True,exist_ok=True)
        for name in names:shutil.copy2(ROOT/group/name,target/name)
    (study/'definitions').mkdir(exist_ok=True)
    for p in (ROOT/'definitions').glob('*.json'):shutil.copy2(p,study/'definitions'/p.name)
    stable=[n for n in required if not n.startswith('docs/') and n!='FINAL_REPORT.md']
    write(study/'ARTIFACTS.json',dict(root=str(ROOT),verdict='PARTIAL',baseline=BASELINE,
        final_lead='FINAL_DX00',search_definitions=480,executed_definition_records=495,real_G8_lineages=20,
        files=[dict(path=n,bytes=(ROOT/n).stat().st_size,sha256=file_hash(ROOT/n)) for n in stable],
        archives=['CHESHIRE_TASK29_REVIEW.zip','MODEL.zip'],
        post_commit_proofs=['analysis/repository_commit.json','analysis/file_inventory.json','analysis/archive_validation.json'],
        scope='Large candidate checkpoint trees and all render pages remain external and in review archive; selected evidence, definitions and code are tracked here.'))
    (study/'README.md').write_text('''# Task29 — PARTIAL

Reference-coupled equations and incident scale were implemented without changing the legacy operator.
A256/B128/C8, D64/E24 and a matched locking ablation produced 480 search definitions,
495 executed definition records and 20 actual G8 lineages. The selected FINAL_DX00 has
393,218 vertices and 393,216 original quads. Macro/meso survive; fine cell patterns and sharp
normal changes remain. This is not a Digital Grotesque fidelity success.

Read [results](../../docs/TASK29_RESULTS.md), [handoff](../../docs/TASK29_HANDOFF.md),
and [Task30 plan](../../docs/TASK30_CONSOLIDATION_PLAN.md).
Start with [actual G0–G8 progression](renders/FINAL_LEAD_PROGRESSION.png)
and [exact rule isolation](renders/rule_contribution_isolation.png).
`ARTIFACTS.json` maps original external files and SHA256. Full data lives at
`E:/CHESHIRE_DATA/task29/` and in the review/model archives. No Task30 cleanup was executed.
''',encoding='utf-8')
    snapshot=ROOT/'source_snapshots/final';snapshot.mkdir(parents=True,exist_ok=True)
    own=['src/cheshire/reference_subdivision.py','examples/task29_search.py','examples/task29_topology.py',
         'tools/task29_views.py','tools/task29_select.py','tools/task29_evidence.py','tools/task29_native.ps1','tools/task29_finish.py',
         'tests/test_reference_subdivision.py','tests/test_task29_topology.py','pyproject.toml']
    for name in own:
        p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/name,p)
    write(ROOT/'analysis/final_source_hashes.json',dict(files=[dict(path=n,sha256=file_hash(REPO/n)) for n in own]))
    print('Required files, repository evidence and exact experiment source snapshot saved.',flush=True)


def package():
    """Post-commit archive sealing, streaming CRC and SHA checks."""
    start=perf_counter()
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=REPO).strip(), 'Commit final sources first.'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=REPO,text=True).strip()
    assert branch=='experiment/task29-reference-generative-search' and commit!=BASELINE
    write(ROOT/'analysis/repository_commit.json',dict(commit=commit,branch=branch,baseline=BASELINE,
        clean_worktree=True,local_only=True,pushed=False,merged=False,Task30_started=False))
    for p in [ROOT/'FINAL_REPORT.md',ROOT/'docs/TASK29_RESULTS.md']:
        content=p.read_text(encoding='utf-8')
        needle='Baseline: `'+BASELINE+'`.'
        content=content.replace(needle,'Task29 local commit: `'+commit+'`.\n\n'+needle)
        p.write_text(content,encoding='utf-8')
    source=ROOT/'source_snapshots/CHESHIRE_TASK29_SOURCE.zip'
    assert not source.exists(), 'Preserve completed source archive.'
    subprocess.run(['git','archive','--format=zip','--output='+str(source),'HEAD'],cwd=REPO,check=True)
    exclude={'analysis/file_inventory.json','analysis/archive_validation.json'}
    paths=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and p.relative_to(ROOT).as_posix() not in exclude
           and (p.suffix.lower()!='.zip' or p==source)]
    inventory=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=file_hash(p)) for p in paths]
    write(ROOT/'analysis/file_inventory.json',dict(commit=commit,files=inventory,
        scope='All Task29 payload files at seal time. Inventory itself and post-seal archive proofs excluded to avoid self hashes; review/model ZIPs excluded. Complete committed source ZIP is included.'))
    paths.append(ROOT/'analysis/file_inventory.json')
    model=[p for p in paths if p.relative_to(ROOT).parts[0] in ('lead','dcc','docs','source_snapshots') or
           p.relative_to(ROOT).as_posix() in ['definitions/selected_nonstationary_schedule.json',
                'definitions/cube_specimen.json','definitions/mechanism_modes.json','analysis/geometry_validation.json',
                'analysis/validation_summary.json','analysis/repository_commit.json','analysis/runtime_environment.json',
                'analysis/reference_equation_audit.md','analysis/FINAL_DIAGNOSIS.md','analysis/final_source_hashes.json',
                'renders/FINAL_LEAD_PROGRESSION.png','renders/lead_details.png','renders/rule_contribution_isolation.png','FINAL_REPORT.md']]
    expected={p.relative_to(ROOT).as_posix():file_hash(p) for p in paths}
    proofs=[]
    for name,payload in [('CHESHIRE_TASK29_REVIEW.zip',paths),('MODEL.zip',model)]:
        target=ROOT/name;assert not target.exists(), 'Preserve sealed archive.'
        with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
            for p in payload:z.write(p,p.relative_to(ROOT).as_posix())
        print('Written',name,target.stat().st_size,'bytes; checking actual payload',flush=True)
        with zipfile.ZipFile(target) as z:
            assert len(z.namelist())==len(payload)==len(set(z.namelist()))
            assert z.testzip() is None
            for n in z.namelist():
                h=hashlib.sha256()
                with z.open(n) as src:
                    for block in iter(lambda:src.read(1024*1024),b''):h.update(block)
                assert h.hexdigest()==expected[n], n
        proofs.append(dict(path=str(target),bytes=target.stat().st_size,sha256=file_hash(target),
                           entries=len(payload),CRC='PASS',every_payload_sha256='PASS'))
        print('CRC and every payload SHA256 PASS',name,flush=True)
    write(ROOT/'analysis/archive_validation.json',dict(status='PASS',commit=commit,archives=proofs,
        seconds=perf_counter()-start,actual_readback=True,all_payload_hashes_match=True,
        proof_is_outside_archives='Post-seal proof cannot hash itself; file inventory and committed source ZIP are inside review archive.'))
    print('Sealed local commit',commit,'and exact review/model packages.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--requests',action='store_true');p.add_argument('--aggregate',action='store_true');p.add_argument('--audit',action='store_true');p.add_argument('--ablation',action='store_true');p.add_argument('--isolation-request',action='store_true');p.add_argument('--reports',action='store_true');p.add_argument('--publish',action='store_true');p.add_argument('--package',action='store_true');a=p.parse_args()
    if a.requests:requests()
    if a.aggregate:aggregate()
    if a.audit:audit()
    if a.ablation:ablation()
    if a.isolation_request:isolation_request()
    if a.reports:reports()
    if a.publish:publish()
    if a.package:package()
