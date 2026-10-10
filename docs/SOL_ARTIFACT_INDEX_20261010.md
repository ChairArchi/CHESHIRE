# CHESHIRE 보존 자료 인덱스

모든 상대 경로의 기준은 `C:/Users/USER/CHESHIRE/`다. 실제 파일 단위 목록은 `SOL_EXPERIMENT_INDEX_20261010.json`; 전체 아카이브 사본/원본 SHA256 대응은 `E:/CHESHIRE_DATA/archives/SOL_HANDOFF_20261010/files_verified_final.jsonl`이다. 아래는 **경로를 찾기 위한 지도**이며 과거 모든 실패안을 재검증했다는 뜻이 아니다.

## 기둥 연구

공통 root `scratch/column_reference_20261010/`.

| 작업 | 코드 / 설정 | 메시·기록 / 렌더 |
|---|---|---|
| 초기 저폴리/단면 발전 | build.py, reference_column.py, reference_proportion.py, reference_next_panel.py, reference_next_panel_v2.py | results, results_v2, reference_column_results, reference_proportion_results, reference_next_panel_results, reference_next_panel_v2_results |
| 문자 그대로 로켓을 만든 실패안 | rocket_build.py, wedge_build.py | rocket_results, wedge_results; 채택안 아님 |
| 플루팅 / Manifold | flute_column.py, regional_fluting.py | fluted_column_results, regional_results, regional_children_results |
| 플루팅 기반 세대 변화 | fluted_generation.py, generation_rules.py, column_pipeline.py | fluted_generation_results, fluted_mass_generation_results, fluted_mass_coherent_results, pipeline_runs |
| 독립 two-part extrusion | independent_extrusion.py | independent_extrusion_results, independent_extrusion_clearance_results |
| straight extrusion 비교 | straight_extrusion.py, large_extrusion.py | straight_child_results, straight_child_clear_results, large_straight_child_results, large_straight_clear_results |
| 부모–자식 / fin 가설들 | based_child_refinement.py, axial_parent_growth.py, coupled_cycle.py, neck_support_growth.py, fin_stencil_study.py | based_child_refinement_results, axial_parent_growth_results, coupled_cycle_results, neck_support_growth_results, fin_face_results, fin_edge_results, fin_noedge_results |
| DS 가족 / 재귀 분기 | ds_family_study.py, branched_column.py, recursive_strips.py, rule_growth.py | ds_family_results, branched_column_results, recursive_strip_results, rule_growth_recursive_results |
| 논문 PDF | paper075_study/extracted.txt, mirror_study/ | paper075_study/page_*.png 등 정확한 이름은 JSON 인덱스 |
| 단순 기둥 → 확장 CC/DS | published_column.py, paper075_sharp.json | published_column_sharp_results/g00…g06 |
| G4 wp 인과 비교 | paper075_vertex_growth.json, vertex_growth_ablation.json | published_column_vertex_results/g00…g06; wp .025→.32, .032 아님 |
| **복잡한 G7 성공 기준안** | paper075_vertex_growth_7.json | **published_column_vertex7_results/g00…g07**, g07/fixed_camera_wide/stage_01/{front,oblique}.png |
| **복잡한 G8 독립 보존안** | paper075_vertex_growth_8.json | **published_column_vertex8_results/g00…g08**, g08/fixed_camera_wide 및 fixed_detail |
| G8 CC 마지막 단계 대안 | paper075_vertex_growth_8cc.json | published_column_vertex8cc_results/g00…g08 |
| CGAL 교차 처리 | resolve_column_cgal.py, extract_column_body.py, check_cgal_body.py, validate_exported_column.py | published_column_vertex_cgal, published_column_vertex7_cgal의 full output; 아래 정확한 body 전달물 별도 |
| 동일 규칙 / 3 carrier | carrier_comparison/{uniform,area,aspect}.json, analyze_carriers.py | published_column_vertex7_results, carrier_area_results, carrier_aspect_results |
| G8만 팽창 제어 | expansion_control.py | repo outputs/expansion_control_20261010/{baseline,decay_025,reprocess_only,local_decay} |
| G1부터 성장량 배분 | paper075_hierarchy_control_8.json; 기존 published_column.py 재사용 | published_column_hierarchy8_results/g00…g08; 1개 추가 비교안, 완성된 ancestry hierarchy 아님 |
| 초기 성공안 + 후기 국소 배분 | paper075_regional_control_8.json; published_column.py opt-in late_geometry_control | published_column_regional8_results/g00…g08 및 g05…g08_growth_field.npz; g08/column_double.ply 권장 |

각 generation 폴더의 mesh.json/column.obj/column.ply와 validation/operator_metadata가 기준이다. 별도 standalone 초기 시험은 결과 형식이 다르므로 JSON 인덱스와 스크립트의 OUT 경로를 함께 확인한다. 일부 과거 스크립트는 import 실행/고정 output이라 **원본 폴더에서 무심코 재실행하지 않는다.**

### 전달용 메시 / 정면·사시

- `outputs/subdivision_column_20261010/vertex_column_06/{mesh.json,column.obj,column.ply}`
- `outputs/subdivision_column_20261010/vertex_column_07/{mesh.json,column.obj,column.ply}`
- `outputs/subdivision_column_20261010/vertex_column_07/fixed_camera_wide/stage_01/{front,oblique}.png`
- `outputs/carrier_comparison_20261010/{uniform,area,aspect}/generation_07_raw.{obj,ply}`
- `outputs/carrier_comparison_20261010/{carriers,results_front,results_oblique}.png`
- `outputs/expansion_control_20261010/*/{mesh.json,column.obj,column.ply}` 및 각 fixed_camera_wide/fixed_detail.

CGAL full output과 main-body selection을 혼동하지 않는다. Blender 렌더 좌표는 float32일 수 있으며 정확한 double master 파일과 다르다.

## 게이트 / Tissue

기본 root `scratch/generative_gate_20261010/`.

| 목적 | 실제 경로 |
|---|---|
| 범용 runner / 실제 연산 | run.py, gateflow/{pipeline,engine,input,symmetry,subdivision_worker,deform_worker,tessellate_worker,tissue_worker}.py |
| 초기 synthetic gate, 의미 role / opening | inputs/neutral/gate.json 및 같은 폴더 OBJ; make_input.py |
| 주요 config | configs/hierarchy_base.json, configs/micro_simple_tissue.json 및 configs 전체 |
| 원본 성공 TARGET | **runs/hierarchy_microfold23/19_crease_subdivide/**: mesh.obj/ply, state.npz, observations.npz, operator_state.npz, stage.json |
| 반복 접힘/국소 위계 | runs/hierarchy_base23, hierarchy_sixfold23, hierarchy_twist23, hierarchy_microfold23; 각 run.json/stage 기록 |
| 초기 porous / projection 기록 | runs/porous23*, projected23*, fiber23*, micro23, micro_simple_tissue23, micro_exposed_tissue23 |
| 단순 셀 | components/simple_micro_cell/component.json; components 전체 |
| LAST / UNUSED / 조직만 비교 | **runs/tissue_composition23/{01_overlay,02_replace_selected,03_tissue_only}**, comparison.json; compare_tissue.py, tissue_comparison.html |
| 원래 라이브러리 | external/tissue, external/blender-4.5.4-windows-x64; deps 및 environment.json, requirements.txt |

연속 조직 root `scratch/connected_tissue_20261010/`.

| 목적 | 실제 경로 |
|---|---|
| frozen TARGET / provenance | target.json, sources.json, frozen_reference/result.obj; 원본 state hash는 sources.json |
| topology 기반 연속 조직 | run.py, worker.py, strip_network.py, mirror_surface.py |
| 실제 Tissue 실험 | runs/patch_tissue_round4, patch_variable4, patch_variable_protected4, patch_collar4 |
| 선호한 local relief | **runs/patch_bundle4/frame_bundle/result.{obj,ply,json}**, midsurface.json, checks.json, operations.json, job.json |
| 넓은 다발형/슬릿형 결과 | **runs/wide_bundle4/frame_bundle/result.{obj,ply,json}**, renders/wide_bundle/{front,oblique}.png |
| 넓은 actual Tissue 결과 | **runs/wide_protected4/tissue_round/result.{obj,ply,json}**, renders/wide_protected |
| 인접 face chain | runs/patch_strips4/frame_strips; renders/strips |
| geometry 검증 | verification.json, audit/surface_audit.json, verify.py (기존 파일을 다시 쓰므로 보존 점검용으로 무조건 실행하지 않기) |
| 8/10 접힘 cycle 확장 | extension/fold8.json, fold10.json, extension/runs, renders/fold8, fold10 |
| 단면 mass / lowpoly 시험 | extension/section_mass_early.json, section_mass_full.json, lowpoly_*.json, five_stage_cage.json; extension/runs와 renders |

wide 조직 결과는 넓은 전면 shell이지 원래 모든 게이트 면과 용접한 단일 전체 solid가 아니다. 실패/진행중 폴더도 전체 보존되므로 각 run/checks와 README 판정을 확인한다.

## 기존 연구 / Git / 환경

- 기존 repo history, src, examples, studies, tests, tools, docs: 현재 저장소 + 최종 Git bundle.
- `archive-local/`, `archive-worktrees/`, `cleanroom/`, `output/`도 보존 대상이다. 외관상 임시 이름이라는 이유로 지우지 않는다.
- `E:/CHESHIRE_DATA/{task22…task36,astra,astra_freedom,astra_gate_grammar,astra_handoff,astra_research,research_archive,presentation,archives}`: 존재 확인, 기존 위치 유지. 외부 inventory는 파일 크기/mtime 기준이며 전체 SHA 재검증이나 중복 복사로 오해하지 않는다.
- `docs/TASK*_HANDOFF.md`, `TASK*_RESULTS.md`, `CURRENT_PATHS.md`: 기존 checkpoint 재사용법/제한. Task31 native mesh.npz와 regional_state.npz를 함께 로드해야 한다.
- `E:/CHESHIRE_DATA/archives/SOL_HANDOFF_20261010/workspace/`: local workspace 사본. `.git` 제외, Git bundle 별도. cache 제외/권한 실패 목록은 status JSON.
- 같은 archive의 `dependencies/CHESHIRE_ASTRA`, `dependencies/HDMola`, `references/`: 외부 코드/DLL/사용자 논문 사본.
- `outputs/sol_handoff_20261010/`: pip freeze, core test, 원본 TARGET hash, syntax 검사, Git 변경/미추적 목록, 최종 상태.

## Sol의 첫 실행

먼저 `SOL_EXTRA_HIGH_HANDOFF_20261010.md`를 읽고 다음 **읽기 중심 확인**을 실행한다.

```powershell
Set-Location C:/Users/USER/CHESHIRE
.\.venv\Scripts\python.exe -B -m pytest tests/test_weighted_subdivision.py tests/test_weighted_doosabin.py tests/test_generational_subdivision.py -q -p no:cacheprovider
Get-Content outputs/sol_handoff_20261010/FINAL_STATUS.json -Encoding utf8
```

그 뒤 사용자가 선택한 경로만 새 output으로 진행한다. 이미 확보한 Tissue를 다시 만들기 위한 연구나 모든 G8 전체 재생성으로 인수인계를 시작하지 않는다.
