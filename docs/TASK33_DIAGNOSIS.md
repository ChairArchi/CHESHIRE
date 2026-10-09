# Task33 — 최신 로컬 실행의 원인 진단

2026-10-09. Task31/32 원본 소스·기록을 수정하지 않고 별도 Task33 경로에서 확인했다. 최종 후보와 검증 결과는 [결과 보고서](TASK33_RESULTS.md)에 정리한다. 아래의 관찰을 모든 조형적 한계의 단일 원인으로 확대하지 않는다.

## 확인한 사실

| 항목 | 실제 근거와 해석 |
|---|---|
| 최신 실행 경로 | 현재 `reference_subdivision`과 `regional_generation`으로 Task31 G1–G5의 XYZ·faces를 저장 checkpoint와 정확히 재현했다. GitHub의 과거 코드로 추정한 결과가 아니다. |
| 초기 smoothing | Task31 G1–G5는 모두 weighted `REFERENCE_COUPLED`다. 별도의 zero-weight smoothing prefix가 없다. G1의 `w2=-2.8` 같은 비볼록 가중치도 존재한다. 호출명 CC만으로 초기 둥글어짐을 확정할 수 없다. |
| 이미 교정된 순서 | 완료된 face point → edge, 완료된 face point와 **원래 edge midpoint** → vertex라는 실제 순서를 확인했다. 과거 coupling 교정을 새 수정으로 반복하지 않았다. |
| 실제 거리의 감소 | 입력 edge 중앙값 G1–G5는 약 450 / 478.55 / 226.56 / 101.28 / 49.32다. `wf × current incident scale × normal` 항의 거리 중앙값은 217 / 84.61 / 19.01 / 7.34 / 3.81이다. 계수와 현재 셀 크기가 함께 작용한다. 이 항은 전체 결합 변위가 아니므로 이 수치만으로 모든 깊이 부족의 인과를 확정하지 않는다. |
| 요청과 적용의 차이 | G3의 이전 정점 1,226개 중 800개, G4의 4,904개 중 1,821개가 lock된다. 해당 `vp`는 계산 후 원래 위치로 덮어쓴다. 저장된 입력/출력의 실제 이동도 0이다. 잠긴 정점의 요청 `wp` 거리 중앙값은 각각 약 2.86 / 1.16이지만 적용되지 않는다. 새 edge/face point의 변형은 계속된다. |
| 지역 제어의 의미 | contrast 0.8은 기본 제어 20% + 지역 모드 제어 80%의 혼합이다. face 제어는 직접, edge/vertex 제어는 인접 face의 평균을 받는다. persistent CC membership은 모드 라벨을 물려주며 부모 능선·골의 접선 방향을 저장하거나 자식 좌표식에 직접 전달하지 않는다. |
| crease와 lock | 활성 Task31 recipe에 별도 explicit crease가 없다. variation-based vertex lock을 crease 연산이나 깊은 접힘 생성과 혼동하면 안 된다. |
| 대칭 분류 오류 | G2의 실제 좌우 대응 face 4개가 quantile 경계의 약 10⁻¹⁸–10⁻¹⁷ 차이로 서로 다른 모드가 된다. opening edit를 제외한 G3 대조에서, 분류값만 좌우 대응시키면 구성적 정점 오차가 109.41486 → 1.383×10⁻¹²로 줄어든다. XYZ 평균화·계수 변경·연산 순서 변경은 하지 않았다. 기존 최근접 진단값 90.79와 구성적 대응값 109.41은 서로 다른 측정이다. |
| 별도 opening 선택 문제 | 기존 G2 mouth 선택 `[490,412]`의 반사 대응은 `[612,530]`이다. 선택 집합이 반사에 닫혀 있지 않다. opening edit만으로 입력 대칭의 최근접 오차가 약 55.62가 된다. 분류 경계 문제와 별개다. |
| 기준 메시의 기술적 상태 | Task31 G5의 전체 fan triangle 검사에서 transverse pair 검출 상한 256에 도달했다. **최소 256쌍**이라는 진단이며 정확한 총수가 아니다. 공유 정점·공면·접선 접촉을 제외하는 검사다. 비평면 quad의 fan이라는 표면 정의 한계도 있다. 기존 메시를 수리·폐기하지 않았다. |

주요 근거: `E:/CHESHIRE_DATA/task33/analysis/task31_exact_diagnosis.json`, `task31_constructive_symmetry_diagnosis.json`, `control_causality_measured/results.json`, `validation/Q_FULL/TASK31_G5.json`. 진단용 소스와 native 대조도 같은 Task33 경로에 보존했다.

## 인과 대조와 남은 가설

실제 geometric CC averaging과 bilinear refinement를 동일한 G3 큰 접힘 이후에 비교했다. **자식 연산 직전** G4 PRE의 세 고정 절단에서 깊이는 381.46→345.54, 333.26→240.99, 373.47→322.05로 줄었다. 약 9–28% 감쇠다. 이는 해당 Task33 대조의 실제 smoothing 효과다. Task31의 모든 weighted generation을 동일한 smoothing으로 단정하는 증거는 아니다.

Task33의 bilinear 경로는 CC를 topology 생성에 사용하되 **모든 XYZ를 이전 정점 그대로 / 원래 edge midpoint / face centroid로 덮어쓴다.** 따라서 CC 호출 자체가 geometric smoothing의 증거가 아니다. 별도 carrier preparation은 carrier state에만 두 번 neutral CC를 적용한다. 초기 native `G1_PRE/G2_PRE`의 XYZ가 그 carrier와 같다고 주장하지 않는다. 첫 field 재구성 때 준비한 carrier가 실제 형상에 반영된다.

Geometric smoothing은 정점 위치의 평균화다. Smooth shading은 렌더 normal의 보간이며 이번 비교는 flat normal을 쓴다. Foot/twist envelope의 `smoothstep`은 scalar 제어값의 연속 연결이다. 셋을 같은 연산이나 같은 깊이 변화의 원인으로 취급하지 않았다.

아직 분리하지 못한 인과는 다음과 같다.

- Task31의 여러 결합 항 중 어느 항이 큰 접힘을 가장 많이 약화시키는지.
- 초기 weighted rounding이 조형적 깊이 부족의 지배적 원인인지. 이번 연구에서는 두 단계의 둥근 carrier 준비가 오히려 날카로운 사각 단면을 완화했다.
- 지역 모드 vocabulary와 incident 평균화가 균일한 튜브 인상을 각각 얼마나 만드는지.
- Task31의 cell scale 감소를 단독 변경했을 때 전체 결합 변형과 교차가 어떻게 달라지는지. 물리 거리 감소는 확인했지만 독립적인 전체 Task31 scale-factor 개입으로 증명하지 않았다.

입력이 단순해서 불가능하다는 가설은 지지하지 않는다. 원래의 74V/80F RECT gate G0에서 깊은 연속 접힘과 그 내부 골을 만들 수 있었다. Task31 G5의 optional internal CHANNEL은 이 원본 G0에 없으며, Task33 경로는 중앙 U 개구부를 유지하는 별도 생성 경로다. Task31 G5의 Euler 0과 Task33의 Euler 2를 동일한 topology로 취급하지 않는다.

## 선택한 기술적 대안

셀별 normal displacement를 계속 늘리는 대신, 원래 U carrier의 유한 material chart 위에 큰 접힘의 연속 위치·위상을 두고 그 내부에 두 세부 규모를 구성했다. 세 규모는 유한한 명시적 구성이다. 프랙탈 설계 논리나 물리 buckling solver가 아니다. 기존 Task31/32 알고리즘은 그대로 남는다.

초기 양의 child phase는 부모 중심을 더 높이는 경우가 많았다. child 위상을 π 반전한 J 대조는 실제 부모 내부에 약 210–310 깊이의 중간 골을 만들었다. 작은 양의 phase/detail 또는 slope-response는 일부 구간에서 새 골 대신 sharpening·톱니를 만들었다. 같은 100 진폭에서 N01과 S01의 fine mechanism만 바꾼 native 절단 대조를 별도로 남겼다. 최종 notch 계열은 생성된 중간 depth field의 기울기 영점 주변에 골을 만들며, fine 진폭이 meso 진폭을 넘지 못하게 한다.

여기서 기울기는 **생성된 depth field의 고정 material-u 유한차분**과 명목 section scale에서 계산한다. 임의 메시의 실제 곡률·완전한 deformation Jacobian·물리적 수렴을 측정했다고 주장하지 않는다. 실제 XYZ/단면 측정은 이 field 계산과 별도로 수행한다.

## Task33 내부의 추가 coupling 진단

부모 기울기에 반응해 child 변위 방향을 바꾼 U01/U02는 최종 전체 검사에서 256쌍 검출 상한에 도달했다. 접촉은 하부의 넓은 구간에 집중됐다. 원인을 부모 방향 변위 자체로 확정하지 않고 같은 U01의 **meso-only U03**을 같은 해상도에서 실행했으며 전체 횡단 교차가 0이었다. 약한 혼합 0.03의 U04도 0이었다.

U01에서는 meso가 부모 방향으로 이동한 뒤 fine notch가 원래 Y 방향으로 추가됐다. **V01은 fine도 같은 macro→meso 변위 방향으로 이동시키는 조건만 바꿨다.** G5 meso 결과는 그대로이며, G6 이후 fine의 방향 결합만 달라진다. V01의 주요 PRE/FOLD와 명시적 triangle의 전체 횡단 교차가 0이었다. 단위 테스트는 fine 변위가 같은 ray 위에 있고 meso 단계는 바뀌지 않음을 확인한다. 이는 이번 새 Task33 구성의 coupling 문제이며 이미 교정된 Task31 face/edge/vertex 순서와 다른 문제다.

같은 방향 결합에서도 혼합을 0.15→0.30으로 높인 **V02는 다시 256 상한**에 도달했다. 방향 일치는 충분한 일반 안전 조건이 아니다. V02 실패를 fine 방향 불일치 하나로 설명하지 않는다. 임의 메시 normal transport나 Jacobian의 유효성을 검증한 것도 아니다. 후보별 원본·실패 로그·접촉 위치·전체 검사 결과는 보존했다.

## 문헌과 적용 범위

| 원출처 | 확인·적용 범위 |
|---|---|
| [Barr, 1984, Global and Local Deformations of Solid Primitives](https://webhome.cs.uvic.ca/~blob/downloads/473/barr.pdf), pp.1–5 | 연속 변형의 합성과 section rotation을 검토했다. 이번 수식은 독립적으로 구성했고 논문의 전체 Jacobian/normal 처리나 동일 알고리즘을 구현했다고 주장하지 않는다. ACM 저작권 논문, 연구 참고. |
| [Botsch & Kobbelt, 2004, A Remeshing Approach to Multiresolution Modeling](https://graphics.stanford.edu/courses/cs164-10-spring/Handouts/remeshing_approach.pdf), 방법·base/detail 부분 | base와 detail의 분리 관점을 참고했다. 논문의 remeshing, Laplacian solver, Phong-normal detail encoding을 구현하지 않았다. Eurographics 저작권 논문, 연구 참고. |
| [Hansmeyer, Subdivided Columns](https://michael-hansmeyer.com/subdivided-columns.html), 공식 프로젝트 설명 | 깊이와 여러 규모의 연속성을 시각적 참고로 삼았다. 작품 복제·동일 연산·비공개 Digital Grotesque 구현 재현을 주장하지 않는다. 이미지·외부 코드를 복제하지 않았다. |

다운로드 원문·SHA256·라이선스·설치된 dependency의 전체 license metadata는 `E:/CHESHIRE_DATA/task33/references/`에 보존했다. 외부 구현을 가져와 실행하거나 새 패키지를 설치하지 않았다. plotting만 기존 ALICE 환경의 Matplotlib를 읽기 전용으로 사용하며 cache는 CreatorTemp로 분리했다. CHESHIRE 실행에 ALICE 패키지 의존성을 추가하지 않았다.
