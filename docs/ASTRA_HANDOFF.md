# CHESHIRE — Pre-Astra research handoff

작성일: 2026-10-10 KST. Task36의 실행·검증·복구·보존이 모두 끝난 **이후** 준비했다.
Task36 종료점은 `0b89c297647905023e49d029f611b26d7fecc6c4`, 브랜치는
`experiment/task36-neutral-recursive`다. 이 문서는 별도 `pre-astra-baseline` Worktree에 있다.
최종 handoff commit은 로컬 branch/tag와 외부 `HANDOFF_FINAL_STATE.json`을 기준으로 한다.

## 1. 독립 연구의 출발 조건

목표는 Hansmeyer의 Digital Grotesque에 가까운 깊은 수렴–발산 흐름과 다층적 내부 접힘이다.
최종 미적 판단과 작품 개념은 사용자에게 있다. 현재 아키텍처, carrier, 수식 또는 연속적인
Task 개선을 유지할 의무는 없다. 검증된 부분과 실패 자료는 새로운 설계를 판단하는 근거다.
프랙탈을 설계 논리로 다시 도입하는 것은 현재 사용자 의도와 다르다.

ALICE는 입력 해석·기초 형상/파라미터 생성, CHESHIRE는 subdivision/deformation을 담당한다.
두 프로젝트는 독립적이다. [최소 게이트 교환 규약](GATE_EXCHANGE_V1.md)은 초기 입력 경계이며
Task31 regional state 또는 후속 Task checkpoint의 continuation 계약을 대신하지 않는다.
전체 게이트/가구의 성공과 이번 단일 기둥 연구의 성과를 구분해야 한다.

**원격은 공개 상태다.** 공식 GitHub repository API가 `ChairArchi/CHESHIRE`,
`private=false`, `visibility=public`을 반환했다. 사용자 조건에 따라 이 handoff branch/tag는
Push하지 않았고 공개 설정도 바꾸지 않았다. 대표 이미지와 문서는 로컬 Git에 준비되어 있다.
현재 GitHub main은 이 handoff의 최신 상태가 아니다.

## 2. 지금 먼저 볼 자료

1. [최신 상태](LATEST_STATUS.md), [Task36 결과](TASK36_RESULTS.md).
2. [대표 원본 이미지](astra/IMAGES.md): V01/Q02 및 U01/W03 라벨을 구분했다.
3. [전체 Task 계보](astra/TASK_LINEAGE.md), [핵심 수식과 해석 경계](astra/FORMULAS.md).
4. 기존 상세 원장 `E:/CHESHIRE_DATA/research_archive/CHESHIRE_TASK01_31_MASTER_LEDGER.md`.
   주제별 변화는 같은 폴더의 `TECHNICAL_EVOLUTION.md`, 전환점은 `TURNING_POINTS.md`다.
5. [문헌·외부 구현](astra/REFERENCES.md), [중요 원본의 절대/상대 경로 CSV](astra/LOCAL_FILES.csv).

상세 Task01–31 원장을 새로 서술하지 않았다. [기계 판독 색인](astra/TASK01_31_INDEX.json)은
기존 원장의 implementation/limit 문장을 추출한 요약이며 recovery status를 그대로 둔다.
Task32–36은 아래 링크와 각 연구 root의 실제 request/source/checkpoint를 우선한다.

## 3. 구조와 현재 실행 경로

| 경로 | 코드 | 실제 역할 / 주의점 |
| --- | --- | --- |
| 초기 COMPAS API | `src/cheshire/{mesh_io,attributes,mapping,rules,execution,transforms,subdivision,lineage,inheritance}.py` | Mesh→Measure→Map→Rule→Budget→Transform→Inherit. 일반 Repeat engine은 미구현이다. |
| Rhino 호스트 | `rhino/CHESHIRE_Run.py`, `examples/` workers | 선택/UI와 외부 repo-local venv 계산을 분리. 모든 과거 host 동작이 검증된 것은 아니다. |
| Legacy modified CC/DS | `weighted_subdivision`, `generational_subdivision`, `weighted_doosabin`, `sharp_subdivision` | 기존 호환 동작과 zero-control 회귀. Task29와 같은 same-step coupling이라고 해석하지 않는다. |
| Crease/topology grammar | `creases`, `crease_folding`, `crease_routing`, `ornament`, `branching`, `vocabulary` | finite crease graph, 실제 event lineage, taper/inset/roof 등. 일부는 외부 HDMola가 필요하다. |
| Reference array 연구 | `reference_subdivision`, `dual_subdivision`, `polygon_dual_subdivision`, `subdivision_pipeline`, `regional_generation` | Task29–31의 corrected coupling, mixed CC/DS, actual multi-parent regional continuation. |
| Task32 | `task32_morphology`, `task32_patches`, `task32_spectral` | 성장 surrogate, intrinsic 좌표, connected disk grammar. 물리적 shell solver가 아니다. |
| Task33/34/35 | `task33_folds`, `task34_refolding`, `task35_columns` | carrier/material-chart 기반 deep fields, 생성된 crest feedback, 구간별 기둥 incision. 범용 arbitrary-mesh folding과 다르다. |
| Task36 | `task36_growth`; `tools/task36_*`; `tools/native/Task36Bounds.cs` | 중립 사각 carrier에서 매 세대 실제 V/E/F 배치, surface-exact inactive split, 국소 교차 repair, 보완 native 검사. |

`examples/`에는 연구 실행에 필요한 helper가 있다. 예를 들어 Task36은 Task29 state I/O,
Task33 views/contacts와 Task24/34 sheet, `hero_design_sprint.guarded`를 사용한다.
파일의 Task 번호가 오래됐다는 이유로 unused로 분류하면 재현이 깨진다.
의존 관계와 기존 명령은 [현재 실행 색인](CURRENT_PATHS.md)을 함께 읽는다.

Python 3.12, COMPAS 2.15.1과 선택 extras는 [pyproject.toml](../pyproject.toml)에 있다.
NumPy/SciPy, Trimesh/Pyrender/Pillow, Python.NET/CoreCLR 및 실제 HDMola DLL은
선택 경로에 필요하다. 새 외부 라이브러리/논문 코드를 Task35/36에서 반입하지 않았다.
설치 버전·license metadata·DLL SHA: `E:/CHESHIRE_DATA/task36/tests_final_body/result.json`.
Project license는 미결정이며 [재배포 경계](../THIRD_PARTY_NOTICES.md)를 존중한다.

## 4. 가장 유효했던 기술과 중단된 대안

“가장 유효”는 서로 다른 검증 목적의 기준이며 전체 작품의 자동 순위가 아니다.

| 성과 | 근거 / 관련 코드 | 한계 |
| --- | --- | --- |
| 깊은 부모 내부 골과 셀을 넘는 경로 | [Task33 V01](TASK33_RESULTS.md), `task33_folds` | 65개 절단에서 작은 split 315개, 깊이 15.01–115.82. 유한 추적이며 독립 연속 능선 315개가 아니다. prescribed chart/phase와 리본 반복이 남는다. |
| 생성된 형상이 다음 제어를 실제 변경 | [Task34 N04/M01](TASK34_RESULTS.md), `task34_refolding` | 같은 입력의 frozen/current 대조가 있다. 추가 fine split은 추적한 33개 위치 중 4개에 한정됐다. |
| 지역별 서로 다른 배열·방향과 실제 골 | [Task35 H01/H02](TASK35_RESULTS.md), `task35_columns` | 작은 골 47/47 material, 32/33 world 절단. front/side 종단의 새 fine는 0, 대각 4. 입력 profile은 미리 설정했다. |
| 중립 carrier의 재귀적 실제 세부 생성 | [Task36 U01](TASK36_RESULTS.md), `task36_growth` | G8까지 모든 세대가 active. 작은 child basin은 G8 3/13 material 높이에 한정. 네 판과 두 axial cell 반복, 외곽 상속이 남는다. |
| 재귀 coupling으로 큰 구성 변화 | Task36 W03, 같은 코드의 body/cap edge rule 분리 | U01보다 몸통·결속이 뚜렷하지만 G7/G8 새 prominence15 child basin은 0/13. fine 성과를 silhouette로 대체하지 않는다. |
| 실제 지역 상태·토폴로지 continuation | [Task31](TASK31_RESULTS.md), `regional_generation` | 실제 handle/genus edit와 multi-parent state를 보존. 자연발생 opening, 독립 micro identity나 무교차 solid 인증은 아니다. |

다음 기술은 현 최신 후보의 기본 경로에서는 쓰지 않지만 삭제·실패 확정하지 않았다.

- Task17/30 DS의 F/E/V face-origin 구분과 CC→DS handoff: inset/frame 구성이 달라졌다.
  독립 micro 계층이 부족했다는 이유만으로 DS 전체의 가능성이 부정된 것은 아니다.
- Task19/20 실제 topology event·sibling rule·quiet branch·mixed parent: ancestry가 풍부하다.
  block/panel scaffold와 visible differentiation의 한계가 남는다.
- Task21 directional roof/ridge와 context fragment: 실제 방향 제어를 얻었지만 셀 접합을
  재조직하지 못했고 lateral fin 강도는 교차했다.
- Task23 persistent cross-cell crease graph: 기존 점이 아니라 실제 descendant edge로 전파했다.
  sharpness/graph 연결이 깊은 조형 연결과 같은 성과는 아니다.
- Task25 curl backbone: terminal Frame 이전의 C11→Taper→standard CC에서 이미 말림이
  나타났다. normal offset을 중지하면 넓은 curl이 회복됐으나 강한 w3/w4는 fragmentation을 늘렸다.
- Task32 metric growth, spectral hierarchy, connected multi-face scope: 별도 연구 계열이다.
  물리적 성장·범용 접힘·emergent topology branching을 구현했다고 부르지 않는다.

## 5. 확인된 원인과 아직 남은 가설

| 상태 | 근거 | 해석 범위 |
| --- | --- | --- |
| 확인 | Task33 [진단](TASK33_DIAGNOSIS.md): 요청 제어와 잠금 후 실제 0, cell scale×generation attenuation | 특정 경로의 실제 변위가 축소됐다. 초기 smoothing이 모든 실패의 단일 원인이라는 결론은 없다. |
| 확인 | Task29 corrected face→edge→vertex 순서, Task33 방향 결합, Task35 growth/incision support 분리 | 이미 교정한 문제다. 오래된 legacy 코드만 보고 최신 코드의 신규 결함으로 반복하지 않는다. |
| 확인 | Task36 같은 입력의 component 대조, mean fan 대 VF inactive split | 평균화 성분, weighted stencil, normal 이동과 물리적 표면 재분할을 분리했다. `CC` 호출명이나 smoothstep만 보고 geometric smoothing으로 결론 내리면 안 된다. |
| 확인 | Task36 새 E/F의 실제 비영 변위와 current/rest 및 retained/new-point 대조 | 재귀는 곡면 sampling만은 아니다. 그러나 새 자유도가 충분한 전체 형상 분화로 이어졌다는 뜻은 아니다. |
| 확인 | Task36 원래 12점 이동/초기 bbox 이탈, 고정 world camera | 전역 bbox clamp나 원점 lock, per-frame scale fitting이 원인은 아니었다. 1:1은 정사각 외곽 보존 조건이 아니다. |
| 확인 | Task36 U01 G3 이후/W03 G2 이후 새 E/F는 직전 전체 XY bbox를 넘지 않음 | 초기 carrier를 벗어나는 점과 새로운 외곽 극값을 만드는 점을 구분한다. 최후 외곽은 retained 조상에 강하게 종속된다. |
| 확인 | T02 actual section trace의 7652 경고, strict edge predicate 반례 | 원래 strict 검사 0도 누락할 수 있다. T02 exchange 검증은 철회했다. U01/W03는 union interval + shared-pair 최종 검사 0이다. |
| 가설 | 반복된 root face, V/F diagonal, class sign, 두 axial cell | 초기 토폴로지/방향 상속이 판 반복과 late macro plateau의 병목일 수 있다. 모든 요소의 인과를 독립적으로 제거한 것은 아니다. |
| 가설 | shrinking support, 일부 평균 edge-normal 소멸, 국소 repair | late folding 거리가 줄고 일부 제어가 약해진다. 각 요인의 기여율, 대체 방향장이 깊이·연결을 동시에 개선할지는 미입증이다. |

Task36 W03는 body edge의 새 face 비중을 15%→75%로 바꾸되 cap rule은 유지했다.
전역 증폭을 먼저 쓰지 않고 S04 cap flip 원인을 분리한 결과다. 효과와 fine 손실이 함께 남는다.
모든 기존 결과의 옛 PASS/SUCCESS를 최신 보완 검사의 인증으로 소급 변경하지 않았다.

## 6. 대표 실험의 재현과 해석

최신 전체 재현은 별도 Git bundle clone + producer source overlay로 U01/W03 각각
G0–G8 50개 NPZ의 **byte-exact**를 확인했다. 실행 코드와 동일 호스트 의존성을 복구했으며
portable offline environment를 입증한 것은 아니다. 과거 Task는 해당 report의 정확한
source overlay·recipe·state를 사용한다. Git CRLF 변환도 source SHA를 바꿀 수 있다.

| 자료 | 실제 local root | 실행 / 입력 계약 |
| --- | --- | --- |
| Task17 DS/hybrid, Task23 crease, Task25 curl | 원장 IMPORTANT FILES 및 LOCAL_FILES/전체 catalogue | 당시 recipe와 source_history, early ignored output/review ZIP. 현재 code의 default로 대신 재현하지 않는다. |
| Task29/30 | `E:/CHESHIRE_DATA/task29/lead`, `task30/lead` | `tools/task29_*`, `tools/task30_*`, saved definitions와 input identity. |
| Task31 | `E:/CHESHIRE_DATA/task31/lead/{cube,gate}` | `mesh.npz`와 `regional_state.npz`, actual operator state, Task30 pipeline/Task31 selected definitions를 함께 load. 기존 prepare/--existing은 완료 폴더에 쓰므로 재실행 금지. |
| Task32 I01/I02 | `task32/candidates/I01_STRAIGHT_CHILD`, `I02_STRAIGHT_CHILD` | `tools/task32_research.py run --definition .../definitions/straight_children/I01_STRAIGHT_CHILD.json`; 정의의 write root는 새 공간으로 바꿔야 한다. |
| Task33 V01 | `task33/candidates/V01_COHERENT_TRANSPORT` | `tools/task33_research.py`, matching request/source overlay. mirrored triangle exchange와 원래 quad state는 별도 표면 계약이다. |
| Task34 N04 | `task34/candidates/N04_FINE_RADIAL` | `tools/task34_research.py --action run --request studies/task34/definitions/N04_FINE_RADIAL.json --tag FRESH_ID`; completed root에 직접 쓰지 않는다. |
| Task35 H01/H02 | `task35/candidates/H01_SHOULDER_GROWTH`, `H02_MILD_SHOULDERS` | 같은 방식의 `tools/task35_research.py`, matching definition; geometric preprofile 포함. |
| Task36 U01/W03 | `task36/candidates/U01_INTERVAL_SAFE_G8`, `W03_BODY_RECURSIVE_G8` | 아래 path-only replay adapter는 old root를 새 Astra experiment로 바꾸고 동일 guard/연산을 호출한다. |

기존 runner의 `E:/.../taskNN` 하드코딩은 그대로 보존했다. 원본을 무심코 다시 실행하지
않도록, Task36에만 출력 경로를 분리한 작은 [실행 어댑터](astra/REPLAY_TASK36.py)를 제공한다.
알고리즘·계수·검사 기준은 변경하지 않는다. 기본은 G8이며 낮은 비용의 먼저 확인용은 G2다.
어댑터의 새 output는 current Git source를 기록한다. 엄밀한 과거 byte provenance는 기존
producer overlay의 독립 복구 증명을 우선한다.

```powershell
Set-Location C:/Users/USER/CHESHIRE_ASTRA
# 매번 새 tag. G2 smoke는 전체 G8 성과의 재인증이 아니다.
.venv/Scripts/python.exe -B docs/astra/REPLAY_TASK36.py --candidate U01_INTERVAL_SAFE_G8 --tag ASTRA_MY_U01_G2 --generations 2
.venv/Scripts/python.exe -B docs/astra/REPLAY_TASK36.py --candidate W03_BODY_RECURSIVE_G8 --tag ASTRA_MY_W03_G8

$env:CHESHIRE_MOLA_DLL='C:/Users/USER/Libraries/HDMola/1.0.0/HDMola.dll'
$env:PYTHONNET_RUNTIME='coreclr'
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider
```

Task36 G8 사전 추정은 655360 operator quad / 2621440 native triangles, 약 5.26 GB다.
실제 U01/W03 생성 peak는 약 3.22/3.12 GB였으며 순간 최고값/VRAM의 완전 계측은 아니다.
G9의 약 19.41 GB 추정은 현재 12 GiB guard를 넘어서 실행하지 않았다.
시도 횟수·폴리곤 수·세대 수를 성공 지표로 삼지 않는다.

## 7. 메시·단면·렌더의 접근 계약

중요 원본 파일은 [LOCAL_FILES.csv](astra/LOCAL_FILES.csv)에 절대경로, root, 상대경로,
역할, 현재 존재 여부, 재확인 SHA256을 남겼다. 전체 출력의 metadata catalogue는
`E:/CHESHIRE_DATA/astra_handoff/pre-astra-baseline/ALL_LOCAL_FILES.csv`이며
[LOCAL_CATALOG.json](astra/LOCAL_CATALOG.json)이 SHA와 범위를 연결한다.
대용량 native·OBJ·전체 render/visibility sequence는 로컬에만 있다.

- 기존 전체 아카이브: `E:/CHESHIRE_DATA/research_archive/`, 모든 `task22`–`task36` roots,
  `E:/CHESHIRE_DATA/archives/`, `E:/CHESHIRE_DATA/presentation/`.
- 초기 원본: `C:/Users/USER/CHESHIRE/output/task07` 이후 및 살아 있는
  `C:/Users/USER/CHESHIRE_TASK*_REVIEW` 폴더. output 경로가 없는 Task는 원장의 ZIP/source mapping을 따른다.
- 새 독립 공간: `C:/Users/USER/CHESHIRE_ASTRA` 및 `E:/CHESHIRE_DATA/astra/{experiments,inputs,references,logs}`.
- Task36 완료 증명: `E:/CHESHIRE_DATA/task36/preservation/FINAL_STATE.json`,
  `FINAL_INVENTORY/inventory.json`, `repository_final.bundle`, root `FINAL_ARTIFACTS.json`.
- U01/W03의 교환 OBJ는 각각 `task36/deliverables/<candidate>/column.obj`다.
  원래 좌표/정점/삼각 순서가 정확하지만 operator state를 포함하지 않는 exchange다.

최신 column은 X/Y가 단면, Z가 수직, 높이 4000, mm 미확정이다. Task33 gate chart와
Task35 profile에 이 좌표를 자동 이식하지 않는다. 전체 렌더는 width5000/target(0,0,2000),
front(0,0)/oblique(28,22)/true side(90,0)의 같은 조건이며 per-stage fitting이 없다.
대표 Git 이미지는 원본 bytes/labels를 보존한다. IMAGE_MANIFEST가 native 관련 원본 manifest
경로와 실제 이미지 SHA를 따라갈 출발점이다. 정면·사선·측면에는 고정 조명의 차이가 있다.

## 8. 최종 검증과 남은 자료 공백

Task36 원래 작업 폴더의 전체 테스트: **979 passed, 59.58s**, skip/기준 완화 없음.
독립 Worktree 전체 테스트: **979 passed, 44.64s**. 최초 Worktree 실행의 2 failures는
physical COMPAS source 해시 경로와 실행기 repo import path의 환경 문제였다.
COMPAS 316개 실제 source 파일을 byte-exact 복사하고 실행기를 바로잡아 해결했으며
원본 source/test를 수정하지 않았다. 최초 실패 로그도 별도로 보존했다.

Worktree `.venv`는 자기 source를 우선 import하지만 나머지 설치 의존성은 원래 venv의
site-packages를 읽는다. 완전히 독립된 offline 환경은 아니며 원본 venv/DLL이 사라지면
새 설치가 필요하다. 이 환경은 Git에 올리지 않는다.

Task36 U01/W03 최종 native는 각각 전체 triangle/shared-pair 보완 교차 0, 실제 16개
단면 경고 0, 대칭 오차 약 3.18e-12/4.11e-12, 연결성/Euler/link/degeneracy 검사를 통과했다.
공면·경계만의 접촉·접선은 제외이며 제작 가능한 solid 인증은 아니다.
다가값 radial profile의 골 개수는 계산하지 않았다. finite material basin은 연속 ridge 인증이 아니다.

기존 아카이브의 저장 source 1515개와 선정 이미지 133개는 기존 SHA와 모두 일치했다.
Task36 완료의 869개 기존 tracked 파일/Task35 보호 7개/새 snapshot/render 증명도 연결했다.
전체 heavy historical archive의 모든 bytes를 새로 독립 재생성/복사한 것은 아니다.

누락/제한은 기존 `research_archive/MISSING_MATERIAL.md`와 [현재 경로 목록](astra/MISSING_PATHS.json)을
함께 읽는다. Task01–05의 개별 당시 test logs, Task01/12 최초 자연어 brief, Task01–09 원본
raster, 일부 Rhino interactive lifecycle, Hansmeyer 원작 source/production recipe는 미발견 또는 미검증이다.
Task01–21 표준 E:/taskNN 폴더 부재는 해당 Task의 소스/원본 전체 유실을 뜻하지 않는다.
현재 GitHub가 공개이므로 원격 handoff 업로드는 보류됐다. 로컬 접근과 GitHub 접근은 다르다.

## 9. Astra가 자유롭게 재검토할 질문

현재 결과는 국소 접힘/재귀 참여와 검증 체계를 확보했지만 풍부한 전체 조형은 PARTIAL이다.
초기 토폴로지의 반복 길이·네 방향·V/F diagonal과 생성된 형상의 방향 관계, 물리 스케일과
local support, 깊이·sharpness·공간 연결의 분리, 해상도에 덜 종속적인 검증을 다시 평가할 수 있다.
기존 방법을 유지하거나 전면 재구성할지는 Astra의 실험 근거로 결정한다. 특정 solver나
문헌을 미리 정답으로 지정하지 않는다. 새로운 결과는 원본 아카이브를 수정하지 않는
독립 공간에서 native state·실제 요청/적용 제어·실패·단면·재현 증거와 함께 남긴다.
