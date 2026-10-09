# ASTRA 독립 대조 — dual 면 내부, 실제 기원 역할, CC/DS 교대

**dual 대조 판정: 국소적인 발생 원리는 확인했지만, 이 규칙을 주 설계 경로로 채택하지 않는다.**
현재 형상의 폭 관계를 읽으면 단순 기둥에서 두 개의 팽창부와 가운데 결속부가
발생한다. 새 EDGE/VERTEX 기원 면은 다음 단계에서 각각 안쪽/바깥쪽으로 접힐 수 있다.
그러나 확인한 결과는 넓은 중심 판과 테두리의 반복이 지배한다. 실제 CC/DS 교대도
깊은 다층 접힘을 확보하지 못했다. 이는 **시험한 규칙의 한계이며 DS 일반의 불가능성
증명이 아니다.** 게이트 제작이나 전체 Digital Grotesque 달성을 주장하지 않는다.

## 구현과 비교 조건

- 코드: [astra_dual.py](../src/cheshire/astra_dual.py),
  [astra_dual_probe.py](../tools/astra_dual_probe.py),
  [test_astra_dual.py](../tests/test_astra_dual.py).
- 입력은 `task36_growth.carrier()`의 **1000 × 1000 × 4000**, Z 수직,
  수직 방향 두 셀을 가진 닫힌 정사각기둥이다. 초기 목·장식·난수는 없다.
  두 셀이라는 초기 면 배치는 이미 형상 발생의 조건이다.
- 모든 비교의 끝단 정책은 `none`이다. 끝단 고정이나 크기 정규화를 하지 않으므로
  최종 Z 길이가 커질 수 있다. 렌더는 동일 입력 단위와 공통 카메라를 쓴다.
- 기존 `dual_subdivision.doo_sabin()`의 정확한 F/E/V 연결 및 다중 부모 상태를 재사용한다.
  기존 연산 파일은 수정하지 않았다. published mask의 출처와 역사적 실행 조건은
  [Task30 보고서](TASK30_RESULTS.md), 이전 dual 실패는 [Task17](TASK17_RESULTS.md),
  곡률 stencil의 원래 적용 맥락은 [Task25](TASK25_RESULTS.md)를 참조한다.
- **새 실험 규칙**은 현재 면의 중심에서 경계 직선까지의 최소 거리 `s`와 인접 면의
  평균 `s`를 비교한다. `c = log(s / mean(s_neighbor))`,
  `w1 = tension + 0.12 × feedback × tanh(c)`이다. 법선 변위는
  `s × [fold_gain × (tanh(2c) + corner_gain × tanh(2b)) + role_gain × r]`이다.
  `b`는 해당 코너의 인접 법선 차이와 면 평균의 차이, `r`은 실제 직전 세대 기원에
  따라 FACE=0, EDGE=−1, VERTEX=+1이다. `b`는 **부호 없는 법선 차이**이며
  주곡률이나 수송된 접힘 방향장이 아니다. 이 수정은 논문의 원래 수식으로 주장하지 않는다.
- `source=rest`는 양의 중립 DS/CC 보간으로 전달된 기준점에서 **특징만** 읽는다.
  실제 배치와 법선은 현재 메시를 사용한다. 전체 형상을 최초 입력에 고정한 대조가 아니다.
- `operator_state.npz`에 실제 `parent_faces`, `input_corner_face/vertex`, F/E/V 역할,
  특징, 적용된 계수와 코너 변위를 저장했다. CC 직전 DS 꼭짓점에 가짜 V/E/F 분류를
  부여하지 않았다. 즉시 뒤따른 CC의 Eq4는 fallback이며, 두 번째 연속 CC에서만
  유효한 계보가 회복된다.

## 적응적으로 진행한 6회 실험과 23개 실행

23개는 대조군·깊이 연장·강도 후속을 포함한 **실행 수**다. 서로 다른 23개 연구 원리나
23회의 독립 성공을 뜻하지 않는다. 모든 실행의 G0부터 마지막 실제 메시와 실패 메시를
`E:/CHESHIRE_DATA/astra_research/dual_probe/`에 보존했다.

| 회차 | 실행 수 | 원인 분리와 결과 |
|---|---:|---|
| P01_INTRINSIC | 6 | 중립 DS / 폭 특징 / 코너 특징 / rest 특징 / 강한 변위 / 높은 tension. 현재 특징은 팽창과 결속을 만들지만 판·프레임 반복. 높은 tension은 G4 교차 256건 이상으로 실패. |
| P02_INTERIOR_SAMPLING | 4 | DS 사이에 실제 삼각 표면을 보존하는 fan 분할을 삽입. G6까지 모두 검사 교차 0. 내부 표본이 늘어도 직사각 패널과 격자 구성이 남음. G6 자체는 변형 없는 분할 단계다. |
| P03_PUBLISHED_CC_DUAL | 5 | published DS/CC 및 현재/rest 특징 DS/CC 교대. 온건한 비교는 G6 유효하지만 둥근 판 구조. 강한 특징군은 G5 교차 132건. Task25 계수를 전역 CC로 옮긴 대조는 G3 교차 112건. |
| P04_VALID_PRIMAL_PROVENANCE | 3 | DS/CC/CC 반복으로 두 번째 CC의 실제 V/E/F 계보와 Eq4를 활성화. 세 비교 모두 G6 검사 교차 0이지만 깊은 다층 장식 확보에는 실패. |
| P05_NEWBORN_ROLES | 3 | 스칼라 특징만 / 실제 기원 역할만 / 두 규칙 결합. `role_gain=.3`은 역할만 G3 48건, 결합 G3 128건 교차. 스칼라만 G5 검사 교차 0. |
| P06_BOUNDED_ROLES | 2 | 위 역할 계수를 `.1`로 낮춘 후속. 역할만·결합 모두 G5 검사 교차 0. 안쪽 EDGE 프레임과 바깥쪽 VERTEX 강조는 생기지만 판 지배는 유지. |

핵심 수치와 전체 실행 경로는
[DUAL_FINDINGS.json](E:/CHESHIRE_DATA/astra_research/dual_probe/FINAL_EVIDENCE/DUAL_FINDINGS.json)에 있다.

## 확인한 사실과 남은 가설

**현재 형상 반응은 작동한다.** P01 D02 현재 특징의 G4 외곽은
1464.07 × 1464.07 × 4426.06이고 D03 rest 특징은
1088.71 × 1088.71 × 4014.89다. 단순히 세대 번호를 바꿔 같은 형상을 반복한 결과는 아니다.
그러나 이 차이만으로 접힘의 질이나 위계가 개선됐다고 판단하지 않았다.

**순수 dual의 중심 면은 계속 하나의 중심 면으로 남는다.** P01 D02에서 처음 10개 면의
직계 중심 후손은 G4에도 10개다. 전체 2562개 면 중 이 10개가 실제 centroid-fan 표면
면적의 23.33%를 차지한다. 주변의 새 면 수 증가는 큰 중심 판의 내부 분화와 다르다.
이는 저장된 실제 토폴로지와 면적으로 확인했다. 다만 fan 분할로 내부 표본을 제공해도
현재 규칙은 격자 모양을 만들었으므로, 내부 표본 부족만이 원인이라는 가설은 충분하지 않다.

**현재 특징과 실제 기원 역할은 서로 다른 제어다.** P06의 역할만 대조는 폭 특징이 없어도
새 EDGE 면에서 안쪽 프레임을 만들었다. 역할은 단순 보존용 메타데이터가 아니다.
그러나 `.3`의 결함과 `.1`의 얕은 프레임 사이에서 원하는 깊고 연속적인 주름은
확보하지 못했다. 더 강한 변위가 해결책이라는 근거도 없다.

**과거 성공 계수의 맥락이 중요하다.** P03의 전역 CC 실패는 Task25의 성공을 반박하지 않는다.
Task25에는 기존 큰 접힘, 지역 적용 범위와 crease 조건이 있었다. 여기서는 같은 숫자 일부를
새 중립 기둥 전체에 사용했다. 이식을 위해서는 입력과 적용 범위까지 검토해야 한다.

공간적으로 이어지는 방향장, 접힘의 부호와 주변 구조 관계가 부족하다는 설명은
**다음 연구 가설**이다. 이번 실험은 그 해결법을 구현하거나 검증하지 않았다.

## 실제 메시·비교 이미지·재현

- [P01 전체 비교](E:/CHESHIRE_DATA/astra_research/dual_probe/P01_INTRINSIC/renders_fullframe/comparison.png)
- [P02 내부 분할 비교](E:/CHESHIRE_DATA/astra_research/dual_probe/P02_INTERIOR_SAMPLING/renders_fullframe/comparison.png)
- [P03 published CC/DS 비교](E:/CHESHIRE_DATA/astra_research/dual_probe/P03_PUBLISHED_CC_DUAL/renders/comparison.png)
- [P04 실제 Eq4 계보 회복 비교](E:/CHESHIRE_DATA/astra_research/dual_probe/P04_VALID_PRIMAL_PROVENANCE/renders/comparison.png)
- [P05 강한 역할 제어 실패](E:/CHESHIRE_DATA/astra_research/dual_probe/P05_NEWBORN_ROLES/renders/comparison.png)
- [P06 약한 역할 제어 비교](E:/CHESHIRE_DATA/astra_research/dual_probe/P06_BOUNDED_ROLES/renders/comparison.png)

각 후보의 `recipe.json`, 세대별 `mesh.npz`, `quad_state.npz`, `operator_state.npz`,
`summary.json`, `validation.json`이 원본이다. 각 회차 `source/`와 `source_identity.json`은
실행 시점의 핵심 소스 사본을 보존한다. `renders/manifest.json`은 원본 메시·이미지 해시,
카메라와 라벨을 연결한다. 초기 P01의 4800 폭 렌더는 강한 후보를 일부 자를 수 있으므로
**6000 공통 폭의 `renders_fullframe`을 사용한다.** 기존 이미지는 삭제하지 않았다.

`FINAL_EVIDENCE/`의 6개 선택 후보에는 실제 삼각 표면의 Z=500/1000/2000/3000/3500
(각각 +0.12345)의 횡단, X=0/Y=0 종단 절단이 있다. NPZ에는 원래 삼각형 ID와
원시 교차 선분이 있으며, 유한한 절단을 연속 능선이나 부모 내부 골의 인증으로 해석하지 않는다.

아래 명령은 CHESHIRE_ASTRA에서 실행한다. 결과 경로를 덮어쓰지 않으므로 `--tag`는 새 이름이어야 한다.

```powershell
.venv/Scripts/python.exe -B tools/astra_dual_probe.py --tag REPLAY_INTRINSIC --generations 4 --render
.venv/Scripts/python.exe -B tools/astra_dual_probe.py --tag REPLAY_FAN --generations 6 --hybrid --render
.venv/Scripts/python.exe -B tools/astra_dual_probe.py --tag REPLAY_CC_DS --generations 6 --published-mix --render
.venv/Scripts/python.exe -B tools/astra_dual_probe.py --tag REPLAY_CC_CC_DS --generations 6 --published-mix --double-primal --render
.venv/Scripts/python.exe -B tools/astra_dual_probe.py --tag REPLAY_ROLES --generations 5 --roles --role-gain 0.1 --render
```

이 명령은 최종 구현의 재실행이다. 초기 소스와 최종 소스 사이에 동치 식의 부동소수점
연산 순서 변경이 있으므로, **모든 과거 NPZ의 바이트 일치 복구를 확인했다고 주장하지 않는다.**
각 실행의 저장된 소스 사본을 기준으로 역사적 결과를 해석한다.

## 검증과 자원 한계

새 테스트 8개와 기존 dual 테스트 16개, **24개 통과(0.19초)**.
중립 설정의 published mask 정확 일치, 실제 다중 부모와 Euler 상태,
현재/rest 특징 반응, 강체·스케일 공변성, nonplanar fan의 표면 면적·일차 모멘트 보존,
기원별 다음 변위의 방향을 검증했다. 기존 테스트를 완화하지 않았다.

모든 저장 단계는 공유 꼭짓점 쌍을 포함하는 Task36의 비공면 양의 내부 교차 검사를 실행했다.
실패는 그대로 보존하고 이후 세대를 진행하지 않았다. **공면·경계 전용·접선 접촉은 제외**한다.
0건은 완전한 solid/fabrication 인증이 아니다. 대칭 수치는 좌표 최근접 대응이며,
Task36의 강한 material bijection 인증과 같지 않다. 선택한 6개 표면은 각각 연결 성분 1,
watertight, winding-consistent다.

실제 표면은 명시적인 centroid-fan 삼각 표면이다. 역사적 Task30의 0–2 대각 분할과
다르므로 이번 결과를 Task25/30 전체 파이프라인의 정확한 재현으로 제시하지 않는다.

이번 도구는 **G6 이하의 작은 판별 실험 전용**이다. 할당 전 예측은
`512 MiB + 40 × 4^G × 1800 bytes`, 상한은 12 GiB와 측정 가용 메모리의 55% 중 작은 값이다.
실제 실행별 정점·면 수와 시간은 `history.json`에 있다. 이 소규모 도구는 별도의
프로세스군 peak-RAM 계측이나 기존 장시간 실행 감시 래퍼를 사용하지 않았으며,
대규모 연구 실행기로 승격하려면 그 감시를 연결해야 한다. G6 제한을 프로젝트 전체의
성능 상한이나 조형적 완료 기준으로 삼지 않는다.

## 추가 복원: 과거의 강한 초기 형상 발생은 유효한 별도 출발점이다

앞의 보수적인 dual 대조만으로 과거 연구 전체의 한계를 결론 내릴 수 없다.
후속 지시에 따라 [astra_recovered_probe.py](../tools/astra_recovered_probe.py)로
**두 회차, 8개 실행**을 추가했다. 이 수는 앞의 dual 23개 실행과 별도다.
이번에는 기존 `hero_design_sprint.guarded`의 프로세스군 RAM 감시를 연결했다.

정확한 출처는 Task28 `P4_C033_ZERO`의
`studies/task28/definitions/generation_weight_schedule.json`과 Task29 `FINAL_DX00`를
보존한 `E:/CHESHIRE_DATA/task30/definitions/retained_canonical_pipeline.json`이다.
새로운 유사 계수를 추측하지 않고 이 JSON을 읽어 사용했다.

첫 회차 [P01_RECOVERED_MACRO 비교](E:/CHESHIRE_DATA/astra_research/recovered_probe/P01_RECOVERED_MACRO/renders/comparison.png):

- **K00_EXACT_CUBE:** 원래 Task29 G0와 정확한 6개 행, 기존 intrinsic/잠금 규칙으로
  G6까지 재실행했다. G0–G6의 `xyz`, `faces`, `classes`, `rest`, `anchors`가 원래
  저장된 operator 배열과 **모두 정확히 일치**했다. 물리적 검사 표면은 이번의 centroid-fan이다.
- **K01_COLUMN_LOCKED / K02_COLUMN_UNLOCKED:** 같은 Task29 스케줄을 중립 기둥에
  옮겼다. G1에서 2217.09 × 2217.09 × 4645.93의 큰 돌출·결속 형상이 발생한다.
  G2에는 교차 64건이 검출되며 G6은 각각 1024건 이상이다. 이후를 중단하지 않고
  진단용으로 진행하여 `INVALID LINEAGE`로 렌더했다. 잠금 해제의 매끈한 외관은
  메시 유효성의 회복을 뜻하지 않는다.
- **K03_TASK28_TRANSFER:** Task28의 정확한 5행을 ABS/GLOBAL 단위 그대로,
  수정된 coupled array 연산에 적용했다. **G0–G5 전 단계 검사 교차 0**이다.
  G1의 큰 각진 수렴·발산, G2/G3의 추가 형상, G4/G5의 곡률 발생을 확인했다.
  최종 작은 접힘은 대부분 약해진다. 따라서 유효한 거대 형상 발생 출발점이며 완성 장식은 아니다.

K03의 G1은 `wf=-280, we=320, wp=520, w1=.8, w2=-2.8`의 절대 거리이다.
현재 전역 평균 unique-edge 길이로 wf/we/wp를 나누어 `GLOBAL_SCALE`로 실행하므로
실제 적용 거리는 그대로다. G2는 정확한 C11B,
G3은 정확한 `.7 × C11B` 및 Task25 GENTLE의 Eq4 쌍이다. 입력은 계속 같은
1000 × 1000 × 4000 중립 정사각기둥이다. Task28 원래의 타원형 팔각기둥과
legacy isolated 연산을 사용한 것은 아니므로 **Task28 전체의 정확 재현이 아닌 수치 레시피 전이**다.

두 번째 회차는 이 유효한 K03의 **실제 G3**에서 시작한다.
[P02_MACRO_CONTINUATIONS 비교](E:/CHESHIRE_DATA/astra_research/recovered_probe/P02_MACRO_CONTINUATIONS/renders/comparison.png):

| 후속 규칙 | 실제 결과 |
|---|---|
| T00_ORIGINAL_ZERO | 기존 G4 약한 Eq4 → G5/G6 zero CC. 전 단계 검사 교차 0. 기존 G4/G5 operator 배열과 정확 일치. 곡면화하면서 작은 접힘 소실. |
| T01_C11B | 정확한 C11B 반복. G4 교차 352건, G5/G6 1024건 이상. 후기 촘촘함을 유효한 성과로 채택하지 않음. |
| T02_T28_G3 | 정확한 T28 G3 행 반복. **G4는 교차 0이고 각진 작은 주름이 추가로 읽힘.** G5 720건, G6 1024건 이상. G4를 유효한 후속 실험 출발점으로 남김. |
| T03_ORIGIN_DS | 보존된 Task30 modest groups를 사용. 첫 DS G4는 UNKNOWN 역할로 uniform 실행하여 교차 0. 새 실제 F/E/V 역할이 적용되는 G5/G6은 1024건 이상. 작은 결정형 면이 증가하지만 유효한 장식으로 채택하지 않음. |

DS 그룹은 `task30_variant_definitions.json`의 `/6/steps/3/groups`를 직접 읽었다.
FACE `w1=.85,wf=.03`, EDGE `w1=-.1,wf=-.02`, VERTEX `w1=.5,wf=.065`다.
정확한 출처 해시, 부모 G3의 native/operator 해시, 실제 적용 스케줄은 각 회차의
`provenance.json`, `recipe.json`, 소스 사본과 세대별 상태에 있다.

추가 회차의 판단은 **큰 형상의 발생 자체가 부족했던 것은 아니며, 검증된 초기 발생과
후기 내부 접힘을 다시 연결할 가치가 있다**는 것이다. 단, T02 G4의 시각적 작은 주름을
깊이·연속성·독립적 세 번째 규모의 인증으로 확대하지 않는다. 조형적으로 흥미로운
후기 INVALID 결과도 모두 남겼으며, 교환용 유효 출력으로 내보내지 않았다.

첫 회차 자원 기록은 **15.69초 / sampled peak tree+driver 431,210,496 bytes**, 두 번째는
**28.04초 / 505,819,136 bytes**, 자원 중단 없음이다. `logs/process.json`이 근거다.
이는 두 실행의 시간이며 전체 연구·검토 시간은 아니다. 첫 비교 폭 8500, 두 번째 비교 폭
6000을 각 회차 내 모든 후보·세대에 공통 적용했으므로 두 회차 이미지를 픽셀 크기만으로
비교하면 안 된다. 실제 좌표 크기는 세대별 검증 JSON에 있다.

```powershell
.venv/Scripts/python.exe -B tools/astra_recovered_probe.py --tag REPLAY_RECOVERED_MACRO
.venv/Scripts/python.exe -B tools/astra_recovered_probe.py --tag REPLAY_MACRO_TAILS --continue-macro
```

후속 명령의 부모는 의도적으로 보존된 `P01_RECOVERED_MACRO/K03_TASK28_TRANSFER/G3`에
고정되며, 새 태그의 다른 결과를 암묵적으로 부모로 선택하지 않는다.
