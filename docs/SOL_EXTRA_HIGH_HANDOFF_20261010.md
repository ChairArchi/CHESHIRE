# CHESHIRE → Sol Extra High 인수인계

이 문서는 이전 채팅 없이 작업을 이어가기 위한 시작점이다. 기준 작업 폴더는 `C:/Users/USER/CHESHIRE`다. 파일별 보존 증거는 `E:/CHESHIRE_DATA/archives/SOL_HANDOFF_20261010/files_verified_final.jsonl`, 예외는 같은 폴더의 `preservation_final_status.json`을 먼저 확인한다. **기둥, 이전 게이트 TARGET, Tissue 조직화는 서로 다른 성공 경로이며 어느 하나로 대체하지 않는다.**

## 1. 목표와 현재 요청

초기 메시와 반복 규칙으로 복잡한 그로테스크 기하를 생성하는 재사용 시스템이다. 단순 기둥은 메커니즘 시험 입력이고 최종 적용 대상은 게이트다. 이후 ALICE 입력을 받을 가능성을 유지하되 이번 작업에는 실제 ALICE 데이터나 신규 연동이 없다.

사용자가 마지막으로 요청한 것은 8세대 팽창 제어와 전체 성과 보존이었다. 이후 **1세대부터 위계를 반영하는 비교안 하나**를 추가 요청했으므로, 기존 연산의 세대별 법선 돌출 계수만 조절한 G1–G8 시험을 추가했다. 이것을 새로운 완성형 위계 알고리즘이라고 부르면 안 된다. 최종 수치/이미지는 `outputs/expansion_control_20261010/REPORT.txt` 및 `outputs/sol_handoff_20261010`의 검증 기록을 본다.

보존 이후 자동으로 새 대규모 탐색을 시작하지 않는다. 후속 우선순위는 (1) 세대 간 성장 위계/비대화 제어 (2) carrier 반응성 (3) 기존 게이트 적용 (4) 기존 Tissue와 연결 (5) 설계/렌더 발전이다.

추가 대화에서 선택적 후기 성장도 시험 요청하여 `paper075_regional_control_8.json` 한 안을 더 실행했다. G0–G4는 성공안과 mesh 바이트 동일, G5–G8은 현재 face perimeter와 이웃 normal bend에 따라 돌출 예산을 재배분한다. 기본 동작은 바꾸지 않은 opt-in 설정이며, 실제 field는 NPZ로 저장된다. 최종 결과: G8만 .25 감쇠는 폭 -0.554% / 정면 점유 -1.442%; G1부터 schedule은 -8.277% / -12.249%; 성공 초기형상+후기 국소 제어는 -1.553% / -5.415%. 면적은 고정 카메라 투영 점유이며 물리 체적 아님. 국소안과 일괄안은 초기 schedule도 달라 국소 mask의 단독 인과 효과를 증명하지 않는다.

초기 schedule안의 기본 float32 PLY에 8개 퇴화 삼각형이 재로드 때 발견됐다. `published_column_hierarchy8_results/g08/column_double.ply`는 정확한 좌표 roundtrip/퇴화 0으로 별도 검증했다. 국소안 `published_column_regional8_results/g08/column_double.ply`도 동일 검증 통과. 기존 파일을 삭제하거나 이 실패를 숨기지 않았다. 재귀 기둥, 새 control 모두 자기교차 solid 인증은 별개다.

## 2. 우선 열 파일

- `docs/SOL_ARTIFACT_INDEX_20261010.md`: 작업군과 실제 경로.
- `docs/SOL_EXPERIMENT_INDEX_20261010.json`: 발견된 실험 폴더, 메시/렌더/설정/검증 파일 목록. 전체 파일은 외부 JSONL manifest.
- `outputs/expansion_control_20261010/REPORT.txt`: 이번 제한된 비교 결과와 결론.
- `outputs/carrier_comparison_20261010/REPORT.txt`: 같은 규칙을 3 carrier에 적용한 결과.
- `scratch/connected_tissue_20261010/README.txt`, `design_selection.json`, `verification.json`: 이미 확보한 연속 조직 구현. 다시 처음부터 개발하지 않는다.
- `docs/CURRENT_PATHS.md`: Task01–36 계열의 별도 라이브러리/연구 경로. 이 계열과 scratch 기둥을 혼동하지 않는다.

## 3. 현재 재귀 기둥: 실제 작동하는 경로

`scratch/column_reference_20261010/published_column.py`는 3개 축방향 셀을 가진 단순 사각 기둥(16 vertices / 14 faces)으로 시작한다. COMPAS topology와 `src/cheshire/{weighted_subdivision,generational_subdivision,weighted_doosabin}.py`의 확장 CC/DS를 사용한다. 기존 fluted_generation에서 가져오는 것은 공통 저장/삼각화 유틸리티이며, 이전 수작업 플루팅 형상을 seed로 사용하지 않는다.

각 세대에서 현재 면의 perimeter, face normal, 실제 이웃 면, 현재 높이 위치를 다시 측정한다. CC face/edge/old-vertex의 위치 계수와 법선 돌출을 분리한다. 연속 DS에서는 바로 앞 세대의 FACE/EDGE/VERTEX_DERIVED 가족에 다른 계수를 적용한다. CC Eq4는 실제 직전 CC lineage가 있을 때만 사용한다. DS→CC에서는 해당 식을 억지로 적용하지 않는다. 후처리 smoothing이나 원래 부모 좌표 복원은 없다.

Hansmeyer 2010 “Subdivision Beyond Smoothness”, 식 1–6이 연산 근거다. 논문 최종 기둥의 숫자 schedule은 공개되어 있지 않으므로 여기 계수는 실험값이다. perimeter scaling의 edge/vertex incident-mean 확장은 구현 선택이다. mirror.pdf의 cut/mirror/join은 별도 연구이며 현재 분기 기둥 생성식이라고 주장하지 않는다.

### 성공안과 정확한 계수

- `paper075_sharp.json`: 4세대 CC `wp=0.025`.
- `paper075_vertex_growth.json`: 같은 항목만 **`wp=0.32`**로 변경. **0.032가 아니다.** `vertex_growth_ablation.json`으로 확인된다. G0–G3 동일, G4 실제 896개 old-vertex 위치 변화. 문맥에서 w12라고 부르지만 코드 값은 perimeter/height-field를 곱하기 전 계수다.
- `paper075_vertex_growth_7.json`: 성공안의 7세대.
- `paper075_vertex_growth_8.json`: 동일한 DS 가족 규칙을 한 번 더 적용한 8세대. 복잡성과 곡선처럼 읽히는 정도 증가, 별형 모듈의 반복/중첩/비대화 문제.
- `paper075_vertex_growth_8cc.json`: 마지막 CC 대안. 별도 실험 자료이며 주 성공안 대체 아님.
- 모든 g00…gNN의 `mesh.json`, OBJ/PLY, `operator_metadata.json`, `validation.json`, config가 각 결과 폴더에 보존된다. 재시작 가능한 전체 의미 state와 단순 전시 mesh를 구분한다. 이 runner는 기본적으로 seed부터 재실행한다.

G7: 229,376 vertices / 229,378 polygon faces. G8 DS: 917,504 / 917,506, 삼각화 1,835,004개. 많은 면 자체는 조형 성공이나 출력 유효성의 증거가 아니다.

### 최소 실행 및 전체 재현

PowerShell, repo root:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_weighted_subdivision.py tests/test_weighted_doosabin.py tests/test_generational_subdivision.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B scratch/column_reference_20261010/published_column.py --config scratch/column_reference_20261010/paper075_vertex_growth_7.json --output SOL_NEW_VERTEX7
```

**매번 새 output 이름을 사용한다.** 역사적 standalone script 일부는 동일 이름을 덮어쓸 수 있다. 이전 extrusion/rocket script를 import하는 것만으로 실행될 수도 있으므로 검토 없이 import하지 않는다. `.venv`와 repo 경로를 유지한 현재 Windows 환경에서 확인했으며 새 OS 이식은 검증하지 않았다.

`outputs/subdivision_column_20261010/run_experiment.ps1`은 새 timestamp 경로에서 G7→CGAL→main body→검사→렌더를 연결한다. CGAL G7만 수 분이 필요하다. 정리 작업을 위해 모든 고밀도 결과를 재생성하지 않는다.

## 4. 메시 정확도와 한계

raw 기둥은 closed/winding/finite이고도 자기교차가 있다. raw signed volume은 실제 재료 체적이 아니다. 자기교차를 허용하면 solid boolean, 내부/외부 판정, 슬라이싱에 문제가 생길 수 있다.

`resolve_column_cgal.py`의 libigl CGAL mesh_boolean union으로 교차를 절단/해소했다. `extract_column_body.py`는 최대 절대체적 연결 성분을 선택한다. 이때 음의 체적을 가진 내부 cavity shell도 제거되어 내부 공동이 메워질 수 있다. 모든 버려진 성분을 단순 파편이라고 설명하면 안 된다. full CGAL output도 보존되어 있다.

정확한 검증된 G6/G7 body는 `outputs/subdivision_column_20261010/vertex_column_06`, `vertex_column_07`다. double `mesh.json`, 17-digit OBJ, double-coordinate ASCII PLY가 원본이다. `validate_exported_column.py`는 실제 OBJ/PLY 재로드와 CGAL 검사까지 수행했다. source surface까지의 vertex distance는 one-way 표본 검사이며 Hausdorff 보증이 아니다.

CGAL이 만든 매우 작은 삼각형은 Blender float32에서 붕괴할 수 있다. renderer는 이를 precision_note로 기록하며 미세 면이 없어졌다고 원본을 수정하지 않는다. 이전 렌더 하위 폴더에 남은 9-digit/float OBJ/PLY는 display용 구버전이며, 전달용 원본으로 사용하지 않는다. 현재 `render_published.py`는 추가 메시 export를 제거했다. **G8 및 새 팽창 제어 raw는 CGAL 해소 완료/제작 가능이라고 주장하지 않는다.**

## 5. carrier 비교

`carrier_comparison/{uniform,area,aspect}.json`은 동일한 G7 schedule, 같은 높이/초기 topology, 초기 체적 32를 사용한다. area station 값 `[1,.55,1.45,1]`, aspect ratio `[1,2,2,1]`. 네 station 사이 선형 면 때문에 aspect안의 단면적이 모든 높이에서 완벽히 일정한 것은 아니다.

결과: 단면에 따른 규모/방향/실루엣 차이는 생겼지만 별형 조직의 지배가 강하다. aspect 중앙 비율은 입력 2에서 출력 약 1.243으로 약화된다. 면 perimeter에 의존하는 현재 성장과 높이 field가 carrier 위계를 압도할 수 있다. 면적 변화안은 게이트 위계 실험에, aspect안은 스툴 방향성 실험에 잠재력이 있으나 구조적 적합성을 시험한 것은 아니다.

## 6. 이전 게이트 생성 파이프라인 — 회수된 별도 성공 경로

`scratch/generative_gate_20261010/run.py` + `gateflow/`가 실제 runner다. `inputs/neutral/gate.json`은 synthetic input이며 ALICE 실제 데이터가 아니다. mesh와 Opening profile, support_left/right/upper face role을 읽어 사용한다. 개구부 거리/상부-기둥 인접 경계, 현재 curvature/normal variation, harmonic fields를 계산한다.

CC/DS → pleat_flow → 독립 normal_extrude → crease_subdivide/fold-lock → 더 작은 규모의 반복 → 선택 Tissue → opening Boolean 순서의 설정들이 있다. pleat_flow는 normal displacement + tangential convergence/divergence이며 모두 강체 종이접기인 것은 아니다. 역할별 강도, 현재 곡률, opening/transition/lintel/deformation mask는 `operator_state.npz`, `observations.npz`, `state.npz`에 보존된다. 양측 대칭은 단계별 half clip / seam-weld reflection으로 유지한다.

**성공 TARGET:** `runs/hierarchy_microfold23/19_crease_subdivide` 및 이어진 frozen `scratch/connected_tissue_20261010/target.json`. `sources.json`이 원본 state와 run hash를 지정한다. 별도 `hierarchy_sixfold23`, `hierarchy_twist23`, `hierarchy_base23`와 초기 실패/전개안도 보존한다. 이 TARGET을 새 기둥 결과로 바꾸지 않는다.

```powershell
Set-Location C:/Users/USER/CHESHIRE/scratch/generative_gate_20261010
..\..\.venv\Scripts\python.exe -B run.py --input inputs/neutral --config configs/hierarchy_base.json --output runs/SOL_NEW_BASE
```

microfold/Tissue 설정과 seed는 config 및 각 run.json이 정확한 근거다. seed 기본값 23이 기록된 실행들을 재현할 때 원래 설정을 유지한다. 모든 알고리즘이 seed 변화만으로 다른 형상을 만들지는 않는다.

Libigl은 geometry observations, SciPy는 graph fields, Manifold3D는 opening Boolean, Tissue는 actual component tessellation, Blender는 headless deform/crease/render에 사용됐다. MOLA/Astra/Freedom/SDF는 다른 recipe에 있고 최신 성공 TARGET에 전부 사용됐다고 말하지 않는다. Voxel fuse는 미세 접힘 손실 때문에 최신 조직안에서 제외했다.

## 7. Tissue / 연속 조직화 — 반드시 재사용

초기 단순 porous INPUT은 `generative_gate_20261010/components/simple_micro_cell/component.json` 등이다. `runs/tissue_composition23`은 같은 TARGET/INPUT/선택으로 overlay(LAST+원본), replace_selected(UNUSED), tissue_only(LAST)의 3안 비교다. 전체 688,128면 중 6,000면(0.87%)만 선택해 sparse decoration에 그쳤고 셀 간/원 TARGET과의 weld가 없었다. UNUSED의 열린 경계는 검사 누락이 아닌 삭제의 결과다. 구멍 높이만 키우는 시험을 반복하지 않는다.

PATCH는 마지막 Subdivision/Multires modifier와 앞단 quad cage를 요구한다. baked TARGET에 옵션만 켜는 것으로 구현됐다고 주장하지 않는다. 기존 비교는 QUAD이며 PATCH 연결은 미구현이다.

`scratch/connected_tissue_20261010/run.py` + `worker.py`는 frozen TARGET에서 UNSUBDIV로 적정 quad scale을 회수하고 실제 면-모서리 인접 graph에서 연속 patch를 선택한다. scale4가 권장되고 scale6은 non-quad로 거부했다.

- 실제 Tissue QUAD/LAST + seam merge: tissue_round, tissue_variable. tissue_collar는 실제 UNUSED와 coarse boundary collar를 연결한다.
- 자체 Weaverbird식 Frame/Window: 공유 index/edge, elongated window, raised crown relief; Weaverbird 플러그인 자체를 실행한 것은 아니다.
- CC/SIMPLE refinement + angle crease + TARGET reprojection + SOLIDIFY. 단순 projection은 계곡을 가로지르는 면을 막지 못하므로 audit에 bridging 한계가 남는다.
- `frame_bundle`은 aspect에 맞춘 길쭉한 slit/raised rail로, 기공처럼 읽히는 두꺼운 연속 조직이다. `frame_strips`는 방향/normal이 맞는 실제 이웃 quad를 짧은 사슬로 연결한다. local variation은 균일 타공의 규칙성을 줄이는 용도다.
- 성공 local baseline: `runs/patch_bundle4/frame_bundle` (design_selection에 사용자 선호 기록).
- 넓은 적용: `runs/wide_bundle4/frame_bundle`, `runs/wide_protected4/tissue_round`; renders/wide_bundle, wide_protected. closed one-component shell이지만 원본 전체 TARGET에 용접된 gate solid는 아니다. 넓은 전면 조직이며 모든 뒷면까지 대체한 출력이라고 과장하지 않는다.
- 초기 `wide_symmetric4` 실패, `wide_tissue_round4`와 `wide_symmetric_v2` symmetry 문제는 실패 기록으로 남긴다.

```powershell
Set-Location C:/Users/USER/CHESHIRE/scratch/connected_tissue_20261010
..\..\.venv\Scripts\python.exe -B run.py --scale 4 --methods frame_bundle --refinement 2 --protect-folds --thickness .0036 --output runs/SOL_NEW_PATCH
..\..\.venv\Scripts\python.exe -B run.py --scale 4 --wide --methods frame_bundle --refinement 1 --protect-folds --thickness .0036 --output runs/SOL_NEW_WIDE
```

`extension/`은 원래 생성기를 보존 복사해 fold8/fold10 및 section-mass 실험을 수행한 경로다. fold8/fold10은 같은 해상도에서 pleat/extrude cycle을 추가한 것이며 CC/DS 세대 증가와 동일하지 않다. 저폴리/날개/단면 변형 시험도 이곳과 column_reference에 각각 있다.

### 마지막 첨부 게이트: section_mass 경로 회수

첨부 이미지에 대응하는 section_mass 계열을 실제 렌더에서 확인했다. crop의 바이트 동일성은 확인하지 않았으므로 mid/full 모두 보존한다.

- `renders/section_mass_mid/front.png`의 source는 `extension/runs/section_mass_full/16_normal_extrude/state.npz`.
- `renders/section_mass_full/front.png`의 source는 같은 run의 `21_crease_subdivide/state.npz`.
- 입력 `extension/inputs/neutral`, seed 23. `section_mass_early.json`: CC → 실제 MOLA → CC → section_articulate → DS → pleat_flow → normal_extrude → support_twist → CC.
- `section_mass_full.json`: early `09_cc`에서 재개해 pleat/extrude 5쌍과 crease_subdivide 추가. 실제 run에는 prefix state SHA와 source run SHA가 있다.
- full 최종 opening 처리 후 739,264 vertices / 1,478,524 triangles, closed 1 component / zero-area 0의 기존 OBJ/PLY 재로드 기록. 렌더는 opening guard 이전 normalized checkpoint이므로 최종 result.obj와 좌표·처리가 동일하지 않다.
- `section_target.json` / `section_target.source.json`은 이 TARGET의 조직화 입력과 provenance. 이어진 `runs/section_wide_bundle4/frame_bundle`, `runs/section_wide_collar4/frame_bundle`, `renders/section_bundle`도 기본 frozen TARGET 조직과 별도로 보존한다.

```powershell
Set-Location C:/Users/USER/CHESHIRE/scratch/connected_tissue_20261010/extension
..\..\..\.venv\Scripts\python.exe -B run.py --input ../../generative_gate_20261010/inputs/neutral --config section_mass_early.json --output runs/SOL_SECTION_EARLY
..\..\..\.venv\Scripts\python.exe -B run.py --input ../../generative_gate_20261010/inputs/neutral --config section_mass_full.json --output runs/SOL_SECTION_FULL --resume-stage runs/SOL_SECTION_EARLY/09_cc
```

사용자는 이 기본 게이트+외부 연산 경로, Tissue 시험, 현재 재귀 생성까지 모두 회수한 뒤 **확보한 기능을 연결하고 미세 값을 조정하는 것**을 원한다. 현재 기둥의 재귀 schedule을 이 게이트와 Tissue에 연결한 완성 파이프라인은 아직 없으며, 그것이 다음 통합 작업이다.

## 8. 설계 판단과 다음 작업

복잡성은 표면 장식만 붙이는 것으로 대체하지 않는다. 현재 기하가 다음 연산에 참여해야 한다. 큰 carrier, 중간 분기, 미세 접힘의 위계를 구분하고 smoothing 수렴과 과도한 팽창을 함께 피한다. FDM 때문에 이번 단계에서 디테일을 임의로 줄이지 않는다. 레퍼런스는 관찰과 가설의 근거이며 원본 기둥을 정확히 복제했다는 주장은 하지 않는다. 사용자의 'fin/날개/로켓'은 비유였으며 문자 그대로 로켓 부품을 붙이는 방식은 거절됐다.

현재 DS 가족은 **직전 topology origin**이지 지속되는 부모 부위/나이 의미가 아니다. 진짜 다세대 위계 제어에는 coarse carrier 및 생성된 중간 구조의 연관을 보존하는 별도 설계가 필요하다. 단순 감쇠를 이를 구현한 것으로 포장하지 않는다. 기존 Task31 regional memberships/lineage는 참고 가능한 구현이지만 현재 scratch runner에 자동 연결돼 있지 않다.

다음 모델은 이번 controlled result를 확인하고 사용자와 모양을 선택한 뒤, 먼저 낮은 세대에서 위계와 carrier 차이를 검증하는 것이 좋다. 이미 성공한 G7/G8는 독립 기준안으로 유지한다. 그 뒤 gate의 support/lintel/transition 제어와 접속하고 마지막에 기존 Tissue 조직화를 재사용한다. 새로운 도구를 무조건 모두 넣는 것이 목적이 아니다.

## 9. 보존 / 환경 / 남은 확인 범위

아카이브 `workspace/`는 로컬 workspace의 확인 가능한 파일 사본, dependencies/는 CHESHIRE_ASTRA와 HDMola, references/는 사용자 PDF/이미지다. .git은 bundle로 보존하며 __pycache__/.pytest_cache는 제외한다. 일부 오래된 pytest 임시 폴더의 ACL 거부는 `preservation_final_status.json`에 기록한다. 원본은 삭제/초기화하지 않았다.

기존 E:/CHESHIRE_DATA task22–36, astra 계열, research_archive는 **기존 위치에 보존 + external_inventory.jsonl로 목록화**한다. 이 전체를 새 아카이브에 중복 백업했다고 주장하지 않는다. 기존 Git bundle/zip/checkpoint도 inventory에 포함한다.

`outputs/sol_handoff_20261010/pip_freeze.txt`, 기존 environment.json/requirements.txt와 vendored deps/external을 같이 보존한다. Python 3.12, COMPAS 2.15.1, headless Blender 4.5.4, libigl 2.6.3 CGAL, manifold3d 3.5.4. 환경별 실제 import 경로는 gateflow/runtime.py를 확인한다. HDMola는 Python.NET/CoreCLR 및 외부 DLL 경로가 필요하다. 복사한 .venv는 로컬 복구 보조이며 다른 경로에서 그대로 이동 실행을 보장하지 않는다.

원격 push 없음. 최종 Git ID/검증 상태는 `outputs/sol_handoff_20261010/FINAL_STATUS.json`을 본다. 자신의 커밋 ID를 같은 커밋 문서에 넣으려는 순환은 만들지 않는다.
