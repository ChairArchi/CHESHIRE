# Task01–36 research lineage

Task01–31의 상세 기술·원래 요청·수식·성공/실패·commit·그림·복원 한계는 기존
`E:/CHESHIRE_DATA/research_archive/CHESHIRE_TASK01_31_MASTER_LEDGER.md#taskNN`을 따른다.
[추출 색인](TASK01_31_INDEX.json), 기존 TECHNICAL_EVOLUTION/REFERENCE_TRACE를 함께 읽는다.
아래 표는 탐색용이며 과거 결과를 최신 검사 수준으로 재인증하지 않는다.

| Task | 핵심 기술·전환점 | 실제 성과와 한계 / 코드·보고서 |
| --- | --- | --- |
| 01 | 원본 index/cycle을 보존하는 OBJ I/O | `mesh_io`, `validation`; 초기 brief/개별 실행 log 미발견. |
| 02 | valence/boundary/height/normal variation 측정 | `attributes`; normal-angle proxy는 differential curvature가 아니다. 03과 요청·commit 공유. |
| 03 | percentile/normalize와 linear/inverse/smoothstep/power/sine | `mapping`, `normalization`; scalar smoothstep은 geometry smoothing이 아니다. |
| 04 | deterministic selection/aggregation·dry-run budget | `rules`, `execution`; 비용 통과는 기하 품질 인증이 아니다. |
| 05 | field×strength×bbox-diagonal normal displacement | `transforms`; 최초 실제 이동. source 보존, topology 변경 없음. |
| 06/06.1 | positive ParentRef, lineage/field inheritance | `lineage`, `inheritance`; signed geometric coefficients와 semantic weights 분리. |
| 07/07.1 | one-step COMPAS quad split, bilinear opt-in | `subdivision`, `surface`; V/E/F parents. local patch admissibility와 triangle/global 유효성 분리. |
| 08/08.1 | Rhino selection→external worker→display | `rhino/`, sanitized Python environment. 일부 Undo/Esc/host lifecycle은 미검증. |
| 09 | 실제 HDMola tapered extrusion, normalized float32 bridge | `mola`; cap/side 역할과 constructive inheritance. 원본 raster 없음. |
| 10/10.1 | cap-only 후손 recursion과 field 제어 | 새 후손 선택/역할은 확인, 반복 box/tile 장식 한계. |
| 11 | raw와 terminal CC1 직접 비교 | [실제 비교 이미지](images/T11_RAW_CC.png); 매끈함이 새로운 큰 fold를 만들지 않음. |
| 12 | ribbons/crown/clusters/diagonal masks 시각 프로토타입 | 세 공간 배치. 최초 자연어 brief/terminal CC semantic lineage 한계. |
| 13 | immutable recipe/hash·morphology atlas 36개 | bounded experiment·registered camera. tiled/pinched/grid 결과와 무교차 sample 한계. |
| 14 | modified CC Eq1–3, F/E/V normal·interpolation weights | [수식 계약](../WEIGHTED_SUBDIVISION_REFERENCE.md), `weighted_subdivision`; input-centroid legacy coupling. |
| 15 | carrier C0/C1/C2/dense와 generation schedules | [carrier](../CARRIER_SCALE_STUDY.md); coarse form 개선, late smoothing/detail과 scale confound. |
| 16 | V/E/F creation class, Eq4 later face placement | `generational_subdivision`; 실제 adjacency 검증. 같은 세대 edge에 face 변화 미전달. |
| 17 | DS Eq5/6·F/E/V face origins·CC/DS handoff | [결과](../TASK17_RESULTS.md), `weighted_doosabin`; inset/frame 차이, 독립 micro 부족. |
| 18 | source graph diffusion·ordered broad/medium/fine | [결과](../SPATIAL_ACTIVITY_STUDY.md), `activity`; ordered 우월성 미입증, 당시 RAM peak counter 한계. |
| 19 | 실제 taper/inset topology events·roles·depth | [결과](../ORNAMENT_CAPABILITY_STUDY.md), `ornament`; depth4 constructive records, panel scaffold. |
| 20 | sibling별 first-match rule·quiet·branch signatures | [결과](../DIFFERENTIATED_BRANCHING_STUDY.md), `branching`; signature 다양성≠조형 분화. |
| 21 | directional extrusion/roof·local frame/ridge | [결과](../VOCABULARY_SANDBOX_STUDY.md), `vocabulary`; 방향 vocabulary는 확보, 강한 fin 교차/셀 접합 한계. |
| 22 | literal SUM attraction·nonstationary sharpness·corner lock | [결과](../BEYOND_SMOOTHNESS_STUDY.md), `sharp_subdivision`; spikes/pinching/collapse 실패 보존. |
| 23 | persistent finite-sharpness cross-cell crease graph | [결과](../CROSS_CELL_CREASE_STUDY.md), `creases`, `crease_folding`; 연결 graph 확보, 깊은 조형·무교차는 별도. |
| 24 | fold/roof/frame/taper 조합으로 design-first Hero | [결과](../TASK24_RESULTS.md); H1/H2/H3 비교, 세 완성 Hero로 판정하지 않음. |
| 25 | 네 갈래 curl의 backbone 추적·full continuation | [결과](../TASK25_RESULTS.md), `fold_continuation`; normal-offset 중지의 curl 회복, 강한 weights fragmentation. |
| 26 | whole gate material coords/reflection·GPU depth review | [결과](../TASK26_RESULTS.md), `progressive_gates`; 실제 대칭/100만face, cell-periodic fine. STOP 기록 보존. |
| 27 | 현재 단면 재측정·STATIC/DYNAMIC·R4 area correction | [결과](../TASK27_RESULTS.md), `dynamic_sections`; folded area의 cycle/reflection 오류 교정. R3는 superseded. |
| 28 | simple column benchmark·legacy coupling audit | [결과](../TASK28_RESULTS.md); macro/meso 가능, G4/5 세부 약화와 cell 반복. |
| 29 | corrected face→edge→vertex reference array path | [결과](../TASK29_RESULTS.md), `reference_subdivision`; current local scale/classes/locks·G8, 전체 DG 재현은 아님. |
| 30 | array DS·명시 CC/DS transition·finite lock-end4 | [결과](../TASK30_RESULTS.md), `subdivision_pipeline`, `dual_subdivision`; continuity/micro tradeoff, DS 필수 가설 미지지. |
| 31 | G2-born persistent regional state + explicit annulus handle | [결과](../TASK31_RESULTS.md), `regional_generation`; actual multi-parent/genus/CHANNEL. 독립 micro와 feedback 필수성 미입증. |
| 32 | metric-growth/spectral hierarchy/multi-face disk grammar | [결과](../TASK32_RESULTS.md), [문헌](../TASK32_RESEARCH.md); I01/I02 기술 기준, block/attached ornament 인상, 일부 전체 contact 반증. |
| 33 | physical-scale chart fields·parent interior notch·direction coupling | [결과](../TASK33_RESULTS.md), [진단](../TASK33_DIAGNOSIS.md), `task33_folds`; V01 실제 깊은 세 규모, ribbon 반복 PARTIAL. G7는 sampling. |
| 34 | 현재 crest의 폭/prominence/방향을 읽는 refolding | [결과](../TASK34_RESULTS.md), `task34_refolding`; N04 current/frozen 인과, fine 추가4/33, panels PARTIAL. |
| 35 | 단일 기둥 four controls·구간 관계·growth/incision 분리 | [결과](../TASK35_RESULTS.md), `task35_columns`; H01 47/47 material 골, longitudinal 한계 PARTIAL. coarse profile은 predefined. |
| 36 | neutral square recursive V/E/F·component/boundary audits·interval contacts | [결과](../TASK36_RESULTS.md), `task36_growth`; U01 fine·W03 macro tradeoff, 외곽 상속/다중스케일 전체 조형 PARTIAL. |

## 전환점의 해석

geometry infrastructure→실제 topology event→modified subdivision→carrier/class schedules→
cross-cell crease→현재 geometry feedback→reference coupling 교정→persistent region/topology→
physical-scale fields→생성된 crest 재판독→구간 기둥→neutral recursive carrier 순서다.
이 흐름은 항상 성능이 증가한 단일 알고리즘의 계보가 아니다. 독립 대안·유지된 legacy·
새 원본 입력·검증 수준 변경을 구분한다. 같은 Task 이름의 여러 stage도 source overlay가 다를 수 있다.
