# Task33 — 깊은 접힘과 수렴–발산 연구 결과

**판정: PARTIAL.** 깊은 큰 접힘, 그 안의 중간 골과 작은 골, 여러 셀을 지나는 수렴–발산 경로를 실제 메시에서 확보했다. 그러나 전체 시점에는 길게 늘어진 리본·주름진 게이트의 반복이 남는다. 이를 풍부한 디지털 그로테스크 장식의 완성으로 바꾸어 부르지 않는다. 최종 미적 선정과 작품 개념은 사용자가 결정한다.

2026-10-09 실행 결과다. 토요일까지 연구를 계속한 것처럼 서술하지 않는다. 원래 Task31 G5는 조형 비교 기준으로 보존하고, 새 생성은 **동일한 Task31 RECT G0의 74V/80F 원본**에서 시작했다. 최신 Task31 G1–G5의 exact replay와 원인 분리 결과는 [진단 보고서](TASK33_DIAGNOSIS.md)에 있다.

## 실제로 확보한 형상

주 후보는 **V01_COHERENT_TRANSPORT**다. T01_DEPTH_BINDING은 방향 혼합이 없는 검증 대조군이며, Q02_DEEP_NOTCH는 높이가 일정한 대조군이다. 세 후보 모두 독립 native 체크포인트와 명시적인 좌우 대응 삼각 표면을 보존했다.

| 동일 material 절단 q | 큰 접힘 성분의 깊이 | 중간 골 깊이 | 중간 → 최종 능선 수 |
|---:|---:|---:|---:|
| 0.06531, 넓은 하부 | 432.44 | 212.6–249.3 | 6 → 12 |
| 0.15031, 첫 결속부 | 174.77 | 75.0–89.8 | 8 → 11 |
| 0.24531, 재확장부 | 461.76 | 254.2–287.0 | 6 → 12 |
| 0.31531, 넓은 상부 | 485.26 | 221.9–271.8 | 6 → 12 |

모든 거리는 **기존 프로젝트 단위**다. mm라고 확정하지 않았다. 실제 triangle과 material 절단의 교점에서 XYZ를 보간해 측정했다. 중간 골 깊이는 같은 부모의 반높이 영역 안에서 측정한 능선–내부 골 차이다. 능선 수의 prominence 50/25/15는 기술적 합격 기준이 아니라 설명용 고정값이다. 면 수·ancestry 수·높은 dihedral로 성공을 선언하지 않았다.

세 개의 안쪽 큰 능선 간 실제 tangent 방향 간격은 대표 절단에서 **약 447 → 182 → 509 → 139**로 변한다. 넓음–결속–재확장–다음 결속의 관계가 셀 경계를 넘어 이어진다. 65개 실제 절단에서 부모를 추적하고 부모 영역의 중간 능선 및 그 내부 작은 split을 기록했다. V01에서는 **315개의 절단별 작은 split**, 깊이 **15.01–115.82**를 확인했다. 이 수는 독립 장식 개수나 정확한 differential ridge 개수가 아니다. 같은 경로를 여러 절단에서 다시 측정한 수이며, 작은 골이 없는 경우도 그대로 기록했다.

큰 접힘 성분은 inherited vertex에서 처음 생성한 단계와 최종 단계의 좌표 차이가 **0**이다. 최종 표면의 저주파 형태도 별도로 비교했다. 이는 최종 XYZ가 처음 형상과 같다는 뜻이 아니다. 중간·작은 접힘으로 표면과 저주파 진폭은 변한다. 또한 고정 σ=0.06 lowpass에서는 좁은 상부 결속부의 여러 큰 능선이 하나로 읽힌다. 모든 부위에서 세 규모가 똑같이 분리된다고 주장하지 않는다.

## 연산과 실행 흐름

1. 원래 U carrier의 연속 material chart `(s,u,v)`와 입력 identity를 보존한다. `s`는 고정 원본 centreline의 정규화된 누적 길이이며 현재 표면의 geodesic 좌표가 아니다.
2. base carrier **state에만** 두 번 neutral CC를 적용한다. 초기 native G1/G2 XYZ는 bilinear 경로이며, 준비한 carrier는 첫 field 재구성에서 반영된다. 이후 topology sampling도 bilinear로 수행해 이전 정점을 계속 geometric averaging하지 않는다.
3. G4에서 큰 접힘을 생성한다. Gaussian 결속 위치 `[0.15,0.43]`, fan 폭, section twist와 연속 위상으로 여러 셀에 걸친 능선 경로를 만든다.
4. G5에서 부모 위상 내부의 중간 접힘을 생성한다. child 위상 π 반전은 중심을 단순히 높이는 결과와 구분되는 내부 골을 만든다.
5. G6에서 생성된 중간 depth field의 기울기 영점 주변에 작은 notch를 구성한다. fine 진폭은 meso 진폭을 넘지 못한다. 큰 성분을 다시 평균화하지 않는다.
6. T01/V01의 `depth_convergence=0.65`는 결속부에서 접힘의 높이도 낮추고 넓은 곳에서 다시 깊게 만든다. Q02의 일정한 높이 때문에 생기는 긴 판의 인상을 완화한다.
7. V01은 `child_direction_mix=0.15`로 부모 depth field의 방향을 일부 반영한다. `transport_fine_with_child=true`는 중간 접힘과 작은 골을 같은 변위 방향으로 이동시킨다. meso 기울기는 원래 material 좌표의 field에서 계산하며 arbitrary-mesh normal solver가 아니다.
8. G7은 같은 세 규모를 더 충분히 sampling한다. **새 네 번째 규모나 새 장식 세대가 아니다.** 원래 입력의 chart·carrier에서 동일한 physical-scale field를 재구성하므로 late edge 축소가 깊이를 자동으로 줄이지 않는다.

각 refinement와 field 재구성의 직전/직후 `G*_PRE`, `G*_FOLD`를 남겼다. mesh, point class, rest, anchors, 실제 parent face/corner, operator state, material state, fold controls, 원본 source overlay, request, SHA-linked 부모를 포함한다. OBJ와 이미지로 checkpoint를 대신하지 않는다.

좌우 대응은 입력에만 적용하지 않았다. scalar 제어를 **변형 전** 좌우 대응시키고, chart의 reflection involution과 반대로 정렬된 실제 face cycle까지 확인했다. 정점 XYZ를 사후 평균화하지 않았다. V01의 최대 구성적 반사 오차는 **2.572×10⁻¹²**, scalar 제어 오차와 native quad cycle 불일치는 **0**이다.

## 효과가 없거나 실패한 방향

| 비교 | 확인한 효과와 처리 |
|---|---|
| 실제 smoothing vs bilinear, B03/B04 | 자식 적용 전 큰 깊이가 절단에 따라 약 9–28% 감쇠했다. Task31 전체 실패의 단일 원인으로 확대하지 않았다. |
| 일정한 셀별 detail 강화, 초기 A–E | 깊이는 커졌지만 사각 carrier, 반복 curtain, 중심 sharpening이 남았다. 여러 control을 함께 바꾼 탐색은 단일 인과 대조로 서술하지 않았다. |
| section만 더 촘촘하게 한 F01 | final contact 105쌍 검출. 같은 map의 full sampling F02는 0이었다. section resolution만 높이면 충분하다는 가설을 폐기했다. |
| 강한 결속 H03와 K01 | 저해상도에서는 contact 7쌍, full sampling에서는 0. 파라미터 자체의 불가능과 sampling 실패를 구분했다. |
| J01/J02 위상 반전 | 중간 골이 생겼다. fine 위상만 바꾸면 일부 위치는 여전히 sharpening에 머물렀다. |
| M01/M02/M03 fine 진폭·coupling | fine을 단순히 높여도 모든 부위에서 새 골이 생기지는 않았다. |
| N01/N02 기울기 양의 response | 일부 새 작은 골은 생겼지만 톱니 인상과 결속부의 약한 효과가 남았다. 동일 진폭 S01 notch 대조로 mechanism과 진폭 증가를 분리했다. |
| O01 전체 recess | 기준 표면을 낮추지만 상대 접힘 깊이나 위계 자체를 해결하지 못했다. 주 후보에서 제외했다. |
| Q01/Q02/Q03 notch 진폭·폭 | 부모 내부에 실제 작은 골이 생긴다. Q02에서 안정적인 세 규모의 단면을 확인하고 T01의 기준으로 삼았다. |
| R01 compact sampling | 720,896 quad, 마지막 PRE/FOLD 전체 contact 0. G4–G6 native 파일은 Q02와 byte-identical. 다만 실제 절단의 fine 깊이가 Q02와 최대 약 135 달라지므로 동등한 고해상도 대체로 선정하지 않았다. |
| T02 높이 수렴 0.85 | 결속부 큰 깊이가 약 75로 낮아지고 고정 lowpass에서 큰 능선 구분이 약해진다. T01보다 우수한 것으로 선정하지 않았다. |
| U01/U02 부모 방향 response | mix 0.15/0.30 모두 final 횡단 교차 상한 256에 도달했다. 선택·OBJ 배포에서 제외하고 하부 접촉 위치를 기록했다. |
| U03/U04 원인 분리 | 같은 U01의 meso-only U03은 같은 해상도 전체 교차 0이었다. mix 0.03 U04도 0. 부모 방향 변위 자체만으로 실패를 확정할 수 없었다. |
| V01/V02 방향 결합 | fine도 meso와 같은 변위 ray로 옮긴 V01은 주요 단계 및 명시적 triangle 전체 교차 0. 같은 결합의 mix 0.30 V02는 256 상한으로 실패했다. 방향 결합 개선의 효과와 강도 한계를 구분했다. |

단일 조건 대조에서 효과를 확인한 뒤 선택적으로 결합했다. 현재 가능한 성과와 손실이 명확해진 경로를 남겼으며, 교차를 허용하거나 판정을 완화해 더 화려한 후보를 선택하지 않았다.

## 기술적 검증과 한계

V01의 원본 carrier, G4 PRE/FOLD, G5 PRE는 T01과 SHA256이 동일하다. T01 G4 PRE는 전체 검사를 마친 Q02 G4 PRE와도 동일하다. 공유하는 이전 단계와 V01 G5 FOLD, G6 PRE/FOLD, G7 PRE/FOLD를 통해 큰 접힘 이후 각 직전·직후의 전체 검사 근거를 확보했다. 모든 삼각형을 사용하는 strict transverse-contact 진단은 **0**이다. 같은 조건의 Q01/Q02/Q03 final도 0이다. Task31 G5 기준은 전체 fan 검사에서 검출 상한 256에 도달했다. 기준 원본을 수리하거나 결과를 감추지 않았다.

비평면 quad의 첫 꼭짓점 fan은 반사된 쪽과 같은 diagonal을 선택하지 않을 수 있다. 별도 `V01_MIRRORED_TRIANGLES`는 **모든 XYZ를 그대로 유지**하면서 실제 diagonal을 좌우 대응시킨 명시적 삼각 표면이다. 원래 quad checkpoint를 덮어쓰지 않았다. 이 표면도 독립적으로 전체 검사했다. triangle cycle은 정확히 반사 대응하며 정점/면 수는 **1,245,186 / 2,490,368**이다. 원본 quad에는 G7에서 opposed fan normal 경고 **10,362개**가 남는다. triangle 출력의 quad 경고 0은 quad가 없기 때문이며 수리 성과나 새로운 합격 기준이 아니다.

Z=650/1300/2200의 실제 planar cut은 각각 두 개의 닫힌 cycle이며 crossing/touch/overlap 및 영길이 segment가 0이다. 중앙 U 개구부의 해당 X 간격은 약 **2048.55 / 2431.34 / 1918.89**이다. Z=3050에는 접힌 상부의 여러 독립 절단 cycle이 생긴다. 이를 단순 portal 개수로 해석하지 않는다. 이 U 개구부와 Task31의 optional internal CHANNEL은 서로 다르다.

검사의 한계도 유지한다. 전체 transverse 진단은 공유 정점, 공면, 경계·접선 접촉을 제외한다. 몇 개의 planar cut이 그 사이의 3D solid를 인증하지 않는다. closed/manifold graph, positive triangle area, algebraic volume도 제작 가능한 solid의 보증은 아니다. 비평면 material cut과 고정 lowpass/peak cutoff에는 resolution 의존성이 있다. renderer의 float32 표시 오차와 native double 대칭 오차를 구분했다.

큰 실행은 face/RAM/disk forecast를 통과한 후 기존 measured-RAM guard에서 실행했다. 시간 제한이나 과거 face cap을 새로 설정하지 않았다. 예를 들어 V01 생성은 **68.09초 / 1.36 GiB**, 명시적 triangle 전체 검사는 **240.95초 / 3.11 GiB**의 process-family peak를 기록했다. 실제 시간·메모리, 요청/적용 field 범위, 정점/면 수는 `resources/`, checkpoint metadata와 로그에 있다. contact checker 최적화는 동일한 narrow-phase tolerance를 유지했고 양성 접촉·극단적인 radius 비율·2,000개 random/degenerate 대조로 기존 판정과 비교했다.

## 재현과 검토 파일

외부 연구 root는 `E:/CHESHIRE_DATA/task33`이다.

| 목적 | 실제 산출물 |
|---|---|
| 전체 정면·사선, 같은 부위 G4–G7 | `renders/V01_NATIVE_PROGRESS.png` |
| 기준과 명시적 triangle, 동일 raking light 및 측면 | `renders/V01_FINAL_RAKING.png` |
| 실제 material/world 단면 | `renders/V01_SECTIONS.png` 및 `.pdf` |
| 연산 직전·직후 실제 단면 | `renders/V01_PROGRESSION.png` 및 `.pdf` |
| sampled 능선·골 관계와 수축–팽창 | `renders/V01_TRACKS.png` 및 `.pdf` |
| 조명/카메라/mesh/depth SHA | 각 render job의 `manifest.json`, visibility NPZ |
| 형상 checkpoint | `candidates/V01_COHERENT_TRANSPORT/G*_PRE`, `G*_FOLD` |
| 명시적 대칭 triangle | `exports/V01_MIRRORED_TRIANGLES` |
| 설계 교환 | `deliverables/V01_DESIGN_EXCHANGE/gate.obj`, `exchange.json` |
| 수치/실패/원인 분리 | `analysis/`, `validation/`, `definitions/`, `logs/` |

전체 view는 같은 정면/사선/측면 camera, width=5600, target을 사용했다. 지지부 확대도 같은 width=1600과 같은 physical target이다. 전체 framing 밖 정점은 0이다. material 위치 추적과 fixed physical crop을 함께 제공했다. 기본 flat-normal 조명군을 보존하고, 별도 raking 조명군도 기준·후보 사이 동일하게 적용했다. optional directional shadow는 현재 PyOpenGL handler에서 실패해 로그·실패 소스를 보존하고 shadow map 없이 별도 재실행했다. dependency를 바꾸거나 geometry를 보정하지 않았다. 첫 V01 OBJ worker는 live-descendant 자원 식별에 실패해 안전장치가 중단했다. 그 기록을 남기고 동일 안전장치의 새 실행으로 내보냈다. 최초 section plot의 clipping도 삭제하지 않고 수정된 축의 새 figure를 만들었다.

```powershell
.\.venv\Scripts\python.exe -B tools/task33_research.py --action run --request studies/task33/definitions/coherent_transport_gate.json --tag MY_NEW_GATE
```

최종 recipe만 사용한 별도 `V01_PARAM_REPLAY`를 원본 G0부터 G7까지 재실행했다. 모든 단계의 mesh/operator/material/fold native NPZ **35개가 원 후보와 SHA256까지 동일**하다. request도 canonical recipe와 일치한다. `preservation/V01_PARAMETER_REPLAY.json`에 비교를 남겼다.

항상 새 tag를 사용한다. source revision은 정확한 producer file overlay의 SHA256으로 보존했다. 일부 실험은 local commit 사이 working source로 실행했으므로 Git HEAD만으로 producer를 재현했다고 주장하지 않는다. 최종 Git bundle과 해당 source overlay를 함께 사용한다. 별도 checkout의 native continuation proof는 `preservation/`에 있다. Git bundle에서 새 폴더로 clone하고 producer overlay SHA를 검증했으며, 복구 폴더의 소스가 실제 import되는지도 확인했다. 복구용 venv는 기존 설치 dependency를 읽기 전용으로 참조한다. **독립적인 dependency/offline 배포 백업을 검증한 것은 아니다.** OBJ의 모든 double XYZ와 oriented triangle도 streaming round-trip으로 원본과 비교했다. Rhino GUI import를 검증한 것은 아니다.

## 실제 변경 파일과 범위

| 새 파일 / 현재 안내 | 변경 이유 |
|---|---|
| `src/cheshire/task33_folds.py` | carrier 전용 유한 3규모 field, averaging 없는 sampling, 좌우 제어, 깊이 수렴과 방향 결합. 기존 Task 연산을 대체하지 않는다. |
| `tools/task33_research.py`, `task33_control_diagnosis.py`, `task33_diagnose.py` | 자원 예측·기존 guard, 불변 실행 경로, 최신 로컬 exact replay와 요청/적용 원인 분리. |
| `tools/task33_contacts.py`, `task33_measure.py`, `task33_planar.py`, `task33_tracks.py`, `task33_progression.py`, `task33_evidence.py` | 전체 접촉 검사와 실제 XYZ 단면, 단계 추적·native 재개 검증. |
| `tools/task33_export.py`, `task33_deliver.py`, `task33_views.py`, `task33_plot.py` | 원래 좌표를 보존한 명시적 대칭 표면·검증된 OBJ, 고정 비교 그림. |
| `tools/task33_preserve.py`, `task33_recover.py` | 과거 파일 SHA 확인과 외부 bundle의 독립 소스/상태 복구 검증. |
| `tests/test_task33_*.py`, `studies/task33/definitions/*.json` | 24개 새 검증과 검증 후보·분리 대조의 재현 recipe. |
| `docs/TASK33_DIAGNOSIS.md`, `docs/TASK33_RESULTS.md`, `README.md`, `docs/CURRENT_PATHS.md` | 확인 사실·가설·실패·제약·현재 진입점을 구분한다. |

작업 전 추적 파일 779개 가운데 **777개의 SHA256이 그대로**다. 나머지 두 파일은 현재 안내인 README/CURRENT_PATHS뿐이며 전후 hash도 남겼다. source/test/recipe의 과거 연구 기준은 바뀌지 않았다. 최종 원본부터의 파라미터 재실행을 포함한 52개 실험 폴더 중 51개가 생성 완료이고, 최초 설정 오류 A01도 남겼다. 생성 완료는 교차 검사 통과나 조형적 성공을 뜻하지 않는다. 모든 후보를 full audit했다고 주장하지 않으며 개별 validation 유무를 inventory에 기록한다.

## 보존·테스트·다음 단계

- 브랜치 `experiment/task33-deep-folds`, 출발 HEAD `993818e0308eb92270b9032da48cc77588d0e05f`.
- 핵심 local 보존 단계 `f67f7d5`, `2045e5d`, `bbcbfd1`, `b0b08f2`, `a6db03a`; 최종 보존 HEAD/bundle/독립 복구 결과는 `preservation/`의 최종 기록에 있다. remote push/force push 없음.
- 기존 Task31 **1,539개**, Task32 **4,033개** 외부 파일의 크기·SHA256이 전후 동일하다. Task01–32 코드·원본 연구 문서·테스트 기준을 수정하지 않았다. README와 CURRENT_PATHS의 현재 안내만 갱신했다.
- 전체 회귀 **928 passed**, MOLA DLL/CoreCLR 포함, skip/기준 완화 없음. 904개 기존 테스트에 24개 Task33 검증을 추가했다. 926/927개 통과한 이전 상태와 최종 928개 통과 상태의 로그·source SHA를 모두 보존했다. 원래 904개 테스트는 모두 통과했다.
- ALICE HEAD `6fcfc42736e60dbd9254a368c06d99c2b2c403a0`, 기존 `notify.ps1` 미추적 상태를 유지했다. ALICE 소스·환경을 변경하지 않았다.

이번 선택의 근거는 검증된 Task31/32를 대규모 재작성하지 않고, 같은 원본에서 **큰 성분을 유지하는 연속 경로와 실제 내부 골**을 독립적으로 확보할 수 있다는 점이다. 모든 old Task를 새 pipeline으로 합치거나 새 arbitrary-mesh solver를 만들지 않았다.

다음 설계 비교에는 검증된 V01, 방향 혼합이 없는 T01, 일정 높이 Q02를 함께 사용한다. 깊이·결속 위치·section twist의 변화를 소수의 설계 의도로 선택하고 동일 camera의 실제 단면을 함께 확인하는 것이 우선이다. 더 큰 normal transport나 fine 진폭 증가는 교차·톱니를 만들 수 있어 검증된 개선으로 추천하지 않는다. 전체 형상에서 판·리본 인상을 줄이는 문제는 남았으며, 다음 연구는 이번 방향 결합을 출발점으로, 실제 부모 표면의 clearance와 방향을 함께 다루는 작은 검증부터 시작해야 한다. 현재 성공 범위를 넘어 강도를 높이는 것을 권장하지 않는다. ALICE 입력은 이번 carrier의 chart 가정을 그대로 만족한다고 가정하지 말고, 기존 최소 교환 규약과 입력 identity·단위 검증을 유지한다.
