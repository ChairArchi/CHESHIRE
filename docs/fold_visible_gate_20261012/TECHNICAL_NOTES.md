# 본체와 이어진 디테일과 고정 기둥 게이트 기술 기록

기준 커밋은 `055c42f`이며 작업 브랜치는 `experiment/fold-visible-gate-20261012`다. 이 커밋은 이전 두 입력 region-fold 연구를 포함한다. 새 코드는 `experiments/fold_visible_gate_20261012`의 opt-in 실험이다. 일반 엔진, Rhino 진입점, 과거 체크포인트의 동작은 변경하지 않았다. 조형 판정은 [REPORT.md](REPORT.md)를 따른다.

## 두 실제 입력과 긴 면

SPAN과 COUNTER는 이전 연구에 포함된 실제 G2 제어망을 그대로 읽는다. 재료 좌표·위상·두 부모 탐색 seed를 공유하지만 실제 XYZ는 다르다. 부모 영역 자체의 완전 자동 탐지는 아니다. 기존 inactive refinement로 실제 native fan 표면을 이어받고 G3에서 새 변형을 적용한다. G3는 각 51,202개 실제 정점과 102,400개 삼각형이다.

`wall_fold.py`는 실제 G2 삼각형에서 측정한 구간을 따라 아래 어깨·중심·위 어깨의 세 레일을 샘플링한다. 삼각형 ID와 barycentric 가중치, 재료 좌표, XYZ를 함께 저장한다. 삼차 레일 근사에서 구간 접선과 법선을 구한다. 깊이는 접선에 수직인 두 어깨 폭 중 작은 값에 `tan(40°)`를 곱하며, 중심의 XY 반경 중앙값 절반으로 제한한다. 이 상한은 벽 두께나 안전한 관입 깊이가 아니다.

DEPTH는 같은 깊이와 envelope에서 법선 방향 V형 변위만 적용한다. WALL은 두 어깨와 새 골을 잇는 ruled 면으로 내부 형상을 다시 구성한다. 축 방향 중앙 60%, 횡 방향 정규 좌표 절댓값 0.65 이내에 plateau가 있고 나머지는 끝단으로 감쇠한다. 두 영역이 겹치면 가중 제안의 합을 `max(1, 가중치 합)`으로 나눈다. 충돌 해결이나 접힘 에너지 최소화가 아니다.

반사는 실제 XYZ의 절댓값 대신 재료 좌표 부호를 사용한다. 원래 면이 대칭 평면을 넘을 수 있기 때문이다. WALL/CHILD 단계에서는 새로운 fractal field를 적용하지 않고 원래 있던 field 이력을 유지한다. 아래 근접 디테일 단계에서는 새 유한 Mandelbulb 높이장을 적용한다. 모든 그림은 저장된 native 삼각형, flat geometric normals, 기존 uniform mineral 재질을 사용한다. 렌더용 subdivision·normal map은 없다.

## G6의 제한된 큰 면 완화

선택안 `detail_finish.py --mode RELAXED_G06`는 실제 WALL G3 quad-edge 이웃 그래프에서 Taubin 계수 `0.50`, `-0.53`을 6쌍 적용한다. 재료 높이 `0.10–0.90` 안쪽에만 움직임을 허용하고 양끝 `0.08` 폭에서 감쇠한다. 실제 carrier 이동 길이는 `0.04` 이하로 제한하고 재료 X/Y 반사로 맞춘다. 이후 세 번 inactive refinement한 G6에서 아래 INTEGRATED의 같은 atlas·colony frames·크기·collar를 평가한다. 원본 제어점도 움직이는 기하 연산이며 shading만 평활화한 것이 아니다.

G6는 제어점 1,638,402개, 제어 quad 1,638,400개, 실제 정점 3,276,802개, 실제 삼각형 6,553,600개다. SPAN/COUNTER의 추가 relief 최대값은 각각 `0.275590`, `0.30`이다. carrier 이동 `0.04`와 relief `0.30`은 별도 예산이며, 원래 G3에서의 총 이동이 `0.30` 이하라는 뜻이 아니다. 세분화는 부분 평면을 보존하므로 완전히 매끈한 곡면을 약속하지 않는다.

실제 native chart에서 정면 좌우 짝점을 구하고 involution, XYZ, 방향 있는 삼각형 집합을 검사한다. 선택한 두 입력의 최대 XYZ 오차는 `3.82e-15/4.24e-15`이며 모든 6,553,600개 삼각형이 반사에 대응한다. G6의 단일 연결·닫힘·방향은 별도 패키지 재생에서 실제 native edge incidence와 vertex 연결도 다시 검사한다. [선택안 전체 재생](review/finish_g6/compact_finish_g6_replay.json)

예비 G05 carrier 완화안은 별도 출력에 보존하며 최종 선택에서 제외했다. 최종안은 G03 carrier에서 완화했는지 metadata로 강제한다. G6 생성·검증은 Windows의 실제 가용 물리 메모리 8GB 이상을 확인하고 입력·안별로 순차 실행한다. streamed native 법선과 bulk Blender mesh import를 사용한다. 같은 G3의 bulk import 렌더는 이전 import와 픽셀 단위로 일치했다. 아래 실행은 다음 절의 G5 INTEGRATED를 먼저 생성한 뒤 수행한다.

```powershell
python -B experiments/fold_visible_gate_20261012/detail_finish.py --root output/MY_NEW_G06_SPAN --parent-root docs/fold_visible_gate_20261012/review --integrated-root output/MY_NEW_FINISH --case SPAN --mode RELAXED_G06
python -B experiments/fold_visible_gate_20261012/detail_finish.py --root output/MY_NEW_G06_COUNTER --parent-root docs/fold_visible_gate_20261012/review --integrated-root output/MY_NEW_FINISH --case COUNTER --mode RELAXED_G06
python -B experiments/fold_visible_gate_20261012/compactpackage_finish_g6.py --verify docs/fold_visible_gate_20261012/review/finish_g6
```

## 실제 표면의 유한 Mandelbulb 디테일

`bulb_detail.py`는 power 8, 10 iterations, bailout 4의 유한 점유 atlas를 계산한다. XY `[-1.2,1.2]`의 129×129 표본, Z `[0,1.4]`의 96개 표본에서 가장 위쪽 점유 높이를 구하고 정규화한다. 이는 완전한 입체 fractal 결합이 아닌 국소 높이 투영이다. 원래 WALL G3에서 inactive split을 두 번 해 G5로 만든 뒤 실제 제어 좌표를 변형한다. native fan 표면도 제어망에서 다시 생성한다.

표면 위치는 실제 삼각형 ID와 barycentric 좌표를 포함하는 결정론적 표본이다. INTEGRATED는 물리적 간격과 아직 비어 있는 영역을 기준으로 큰 돌기를 선택하고 각 큰 돌기에 두 작은 돌기를 놓는다. 실제 incoming native 법선을 모아 국소 방향을 구성한다. 반지름·진폭은 `0.30/0.22`, `0.14/0.07`, 뿌리 collar 진폭은 `-0.035`, 최종 변위 길이 상한은 `0.30`이다. 재료 X/Y 반사로 변위를 구성하며, 실제 XYZ 부호를 보고 대응을 고르지 않는다.

G5의 SPAN/COUNTER는 각각 제어점 409,602개, 실제 정점 819,202개, 실제 삼각형 1,638,400개다. 두 입력 모두 기존 연결을 유지하는 단일 닫힌 표면이다. 별도 가지 부품을 추가한 `tessellated_detail.py`는 본체에서 떨어져 보인다는 사용자 판단으로 제외한 진단안이다. 선택된 형상이나 패키지 재생에 사용하지 않는다. TISSUE는 도입하지 않았다.

`compactpackage_finish.py`는 큰 native·operation 사본을 생략하고 atlas·표면 위치·generation과 배열별 해시를 보관한다. 패키지의 WALL G3에서 inactive refinement, 실제 incoming 법선, 높이장, 반사를 다시 계산해 BOLD_DETAIL/INTEGRATED × SPAN/COUNTER의 모든 생략 배열과 matched CONTROL을 재현한다. [정확한 재생](review/finish/compact_finish_replay.json)

독립 대칭 검사에서는 saved native chart에서 반사 대응을 새로 구해 실제 좌표와 방향 있는 삼각형 cycle을 비교했다. G5 INTEGRATED의 정면 X/측면 Y 최대 오차는 두 입력 모두 `4.23e-15` 이하이고 삼각형 대응이 일치한다. [독립 실제 대칭 검사](review/finish/receipts/independent_native_symmetry.json)

```powershell
python -B experiments/fold_visible_gate_20261012/bulb_detail.py --root output/MY_NEW_FINISH --parent-root docs/fold_visible_gate_20261012/review --detail-generation 5 --variant INTEGRATED
python -B experiments/fold_visible_gate_20261012/compactpackage_finish.py --verify docs/fold_visible_gate_20261012/review/finish
```

## 부모에서 자식으로 이어지는 한 단계

`child_fold.py`는 실제 WALL G3 native 표면에서 부모 골과 바깥 어깨를 다시 측정한다. 중앙 25개 ray의 과반수에서 부모 골이 검출되어야 한다. prominence 임계값은 부모 깊이의 4%다. guide 가까운 골을 선택하며, 관련 없는 가장 깊은 골로 대체하지 않는다. 두 유효 ray 사이의 빠진 내부 위치만 보간하고 그 개수를 기록한다. 검출되지 않은 끝을 외삽하지 않는다.

자식의 세 레일은 부모 골에서 바깥 어깨로 가는 실제 호 길이의 35%, 55%, 75%에 놓인다. 부모 골 인근 25%를 제외하고, 각도 30°와 부모 깊이 40% 상한으로 같은 WALL 연산을 적용한다. 재료 좌표의 이차 fitting이 제외 구역을 침범한 안은 채택하지 않았다. 측정 재료 좌표는 piecewise linear로 유지하고 XYZ 레일만 cubic으로 근사한다.

이것은 G3에서 G4로 가는 유한한 한 단계다. 임의 메시 입력, 자동 분기·합류, 무제한 recurrence를 구현한 것은 아니다. 두 입력 각각 204,802개 실제 정점과 409,600개 삼각형이다. 부모 보존 진단은 같은 inactive G4 기준에서 비교한다. 첫 실행의 G3/G4 간 비교가 섞인 수치는 [교정 영수증](review/receipts/child_two_input_verification.json)으로 대체해 해석한다.

## 고정 기둥과 대칭 상인방

`symmetric_lintel.py`는 실제 SPAN G2의 재료 좌표에서 `s → 1-s`의 involutive 짝점을 구한다. 원본 좌표와 반사된 짝점의 평균으로 새 carrier를 구성하고, 고정된 단면·길이 변환을 한 번 적용한다. 새 carrier의 실제 native 표면에서 원래 두 부모 탐색 seed와 축 반사 seed 두 개를 측정한다. WALL 연산 뒤 XY 반사, 앞 절반의 변위 복사와 축 성분 반전으로 상인방의 길이 방향 대칭을 구성한다. 원본 G2, 짝점, 평균, 변환, raw/XY/최종 delta를 모두 저장한다.

기둥에는 `0.3071351841`의 공통 균일 축척과 이동만 사용한다. 상인방 회전은 local Z를 world X로, local X를 world Z로 보내는 proper rotation이다. 새 입력에만 단면·길이 변환과 rest 재설정을 적용했다. WALL 결과마다 별도 축척은 없다.

`review/fixed_gate`는 상인방 체크포인트와 변형, 조립 transform을 포함한다. 큰 조립 geometry 사본 세 개는 생략했다. `package_gate.py --verify`가 패키지의 실제 WALL SPAN 기둥, 상인방 실제 삼각형, 저장 transform으로 세 조립을 다시 구성해 원래 배열 해시와 비교한다. SOURCE 구성, CONTROL/WALL 변형, native, 생략 조립 배열 모두 정확히 재생됐다. [복사와 생략 해시](review/fixed_gate/COPY_RECEIPT.json) · [독립 재생](review/fixed_gate/compact_gate_replay.json)

단순 box 대조군도 실제 반사 삼각형 집합을 맞추기 위해 면 중심 fan을 사용한다. 두 삼각형의 대각선을 사용한 첫 box는 이 검증을 통과하지 못했고 `fixed_gate_attempt_001`에 보존했다. 이 기술적 수정은 조형 대조군의 외형을 바꾸지 않는다.

## 두껍게 붙인 게이트 머리

`gate_junctions.py`는 고정된 양쪽 기둥 근처에서 상인방 local X/Y 단면을 동일하게 1.65배 늘린다. 축 방향 station은 유지한다. 그 실제 삼각형을 3×3 수직 ray로 검사하고 공통 하강량 `0.163023065m`을 구해 양쪽 9/9곳의 실제 겹침을 만든다. 기둥 좌표·삼각형은 정확히 그대로다. 상인방 변형과 조립은 좌우 반사에 일치한다. 세 개의 독립된 닫힌 부재가 겹치며, 합체한 단일 표면이라고 주장하지 않는다.

`package_joined.py`는 이미 보관된 WALL 기둥과 대칭 상인방에서 두꺼운 좌석 변형을 다시 구성한다. 생략된 control/operation/native/assembly 배열 해시와 양쪽 18개 ray 결과를 재생한다. [재생 기록](review/gate_joined/compact_joined_replay.json)

```powershell
python -B experiments/fold_visible_gate_20261012/package_joined.py --verify docs/fold_visible_gate_20261012/review/gate_joined
```

## 검증과 작은 패키지

주 패키지의 WALL 두 상태에는 제어망·실제 삼각형·operation·guide·rail·측정 배열을 포함했다. CHILD 두 상태에는 제어망과 자식 레일을 포함하며, 큰 native/operation 배열을 다시 생성해 원래 저장 배열의 해시와 비교한다. 두 입력 모두 제어점 오차 0, 모든 생략 배열의 해시 일치를 확인했다. [복사 목록과 원본 해시](review/COPY_RECEIPT.json) · [CHILD 재생](review/compact_child_replay.json) · [패키지 WALL 재생](review/receipts/packaged_wall_verification.json)

원래 [16개 G3 변형 검증](review/receipts/verification.json)은 두 실제 입력의 8개 상태와, 초기 primitive gate 진단의 8개 상태 및 4개 assembly를 함께 포함한다. 변형·제어점·실제 삼각형 재생 오차는 0이었다. 그 기록을 현재 채택한 고정 기둥 게이트의 검증으로 사용하면 안 된다. primitive gate는 사용자가 정한 초기 매스가 아니므로 주 형상 패키지에서 제외했고, 거절된 입력의 일부 진단 영수증만 별도 보존했다.

기본 형상 검사는 finite XYZ, 닫힌 표면, winding, 연결체 수, 최소 삼각형 면적, 재료 좌표 기반 실제 XYZ 및 삼각형 반사다. 자기교차·접합 간섭·구조·제작 검증은 별도다. 렌더 픽셀 차이는 조명과 denoising 반응을 포함하므로 조형 품질 지표로 사용하지 않는다.

## 실행과 재생

관련 기존·새 테스트 53개를 실행해 모두 통과했다. streamed 법선의 실제 native 기준 비교, carrier 이동 상한과 고정 양끝, 실제 좌우 정점·면 손상 검출, 두 입력 누락 검출, native topology 손상 검출을 포함한다. G5·G6·게이트 패키지는 생성과 별도의 read-only 재생을 통과했다. [최종 검사 범위](review/receipts/QA_SUMMARY.json)

저장소 루트에서 Python 3.12와 기존 `task32`, `review`, `test` extra를 사용한다. 실제 환경은 NumPy 2.5.3, SciPy 1.18.1, trimesh 5.1.1, Pillow 11.3.0, pytest 9.1.1, Blender 4.5.4 LTS다. 의존 실험과 기존 Task36 도구를 재사용하므로 이 디렉터리만 떼어낸 독립 라이브러리는 아니다.

```powershell
python -B experiments/fold_visible_gate_20261012/study.py --root output/MY_NEW_VISIBLE --cases SPAN COUNTER
python -B experiments/fold_visible_gate_20261012/verify_columns.py --root output/MY_NEW_VISIBLE --output output/MY_NEW_VISIBLE/columns_verification.json
python -B experiments/fold_visible_gate_20261012/descend.py --root output/MY_NEW_VISIBLE --cases SPAN COUNTER
python -B experiments/fold_visible_gate_20261012/verify_child.py --root output/MY_NEW_VISIBLE --output output/MY_NEW_VISIBLE/children_verification.json
python -B experiments/fold_visible_gate_20261012/package_review.py --verify docs/fold_visible_gate_20261012/review
python -B experiments/fold_visible_gate_20261012/verify_columns.py --root docs/fold_visible_gate_20261012/review --modes WALL --output output/MY_NEW_PACKAGED_WALL_VERIFICATION.json
python -B experiments/fold_visible_gate_20261012/symmetric_lintel.py --root output/MY_NEW_FIXED_GATE --column docs/fold_visible_gate_20261012/review/WALL/SPAN/G03/geometry.npz
python -B experiments/fold_visible_gate_20261012/package_gate.py --verify docs/fold_visible_gate_20261012/review/fixed_gate
```

생성기는 기존 상태를 덮어쓰지 않는다. 항상 새 root를 사용한다. 검증 도구의 output도 새 경로를 지정해 과거 영수증을 보존한다. `verify_child.py`는 명시된 기대 입력을 모두 요구하므로 빈 디렉터리를 PASS로 처리하지 않는다. 초기 primitive gate의 회고 검증은 기존 `verify.py`로만 수행한다.

렌더 예시에서 `$blenderPath`를 실제 Blender 실행 파일로 지정한다. 기둥은 900×900 / 24 samples, 고정 기둥 게이트는 별도 영수증에 기록한 해상도와 samples를 사용한다.

```powershell
& $blenderPath --background --factory-startup --python experiments/fold_visible_gate_20261012/render.py -- output/MY_NEW_VISIBLE/CONTROL/SPAN/G03 output/MY_NEW_VISIBLE/WALL/SPAN/G03 output/MY_NEW_VISIBLE/CHILD/SPAN/G04 --views front oblique side front_detail side_detail
python -B experiments/fold_visible_gate_20261012/boards.py --root output/MY_NEW_VISIBLE --output output/MY_NEW_VISIBLE/images --case SPAN --modes CONTROL WALL CHILD
```

로컬 전체 결과는 `output/fold_visible_gate_20261012`에 있다. 기존 E 드라이브 결과와 다른 worktree의 완료 기록은 변경하지 않았다. 초기 probe, primitive gate, 좁은 간격의 첫 배치도 덮어쓰거나 삭제하지 않았다. 주 패키지와 새 소스는 scoped `.gitattributes`로 바이트를 보존하며 [MANIFEST.json](MANIFEST.json)에 SHA-256을 기록한다. 이전 보고서의 98개 해시는 기준 커밋 및 현재 파일과 모두 일치한다.
