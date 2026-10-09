# Task34 — 생성된 형상을 다시 읽는 게이트 접힘 연구

**종합 판정: PARTIAL.** 큰 돌출부가 생긴 뒤 그 능선이 두 어깨와 가운데 골로 갈라지고, 다음 연산이 실제로 생긴 어깨의 폭·방향·prominence를 다시 읽도록 구현했다. 일부 어깨 내부에는 그 다음의 작은 골도 생겼다. 그러나 이 발전이 게이트 전체에 고르게 이어지지는 않았고, 넓고 각진 판과 반복된 세로 능선이 남았다. 풍부한 디지털 그로테스크 장식의 완성으로 판단하지 않는다.

최종 연구 후보는 **N04_FINE_RADIAL**, 실제 인접 삼각형 normal까지 읽는 별도 유효 후보는 **M01_RESPONSIVE_GATE**다. 최종 미적 판단과 작품 개념은 사용자가 결정한다. 모든 거리는 기존 프로젝트 단위이며 mm로 확정하지 않았다.

## 새로 발생한 형상과 다음 단계의 변화

N04는 다음의 **실제 native 메시**를 남긴다. G5는 접힘을 추가하는 단계가 아니다.

| 단계 | 실제 연산과 형상 | 삼각형 수 |
|---|---|---:|
| G0_CARRIER | 기둥–분산된 연결부–상인방, 단면 폭/깊이가 다른 거친 U carrier | 272 |
| G3_PRE → G3_FORM | 결속 구간을 남기며 6방향의 큰 돌출부와 능선 생성 | 16,512 |
| G4_PRE → G4_FOLD | 직전 형상의 실제 능선 폭·prominence를 읽어 중앙을 넣고 양 어깨를 돌출 | 65,792 |
| G5_PRE | 기존 생성 메시를 보간하여 샘플링만 증가 | 262,656 |
| G6_PRE → G6_FOLD | G4에서 생긴 어깨를 실제 입력으로 다시 읽어 내부 접힘 시도 | 1,049,600 |

같은 물질 위치에서 측정한 결과다. ‘큰 성분의 최대 높이’는 원래 rest 단면 대비 projected radius의 최대 차이이며, 전체 골 깊이와 같은 측정량이 아니다. 중간 골은 같은 부모 각도 영역 안의 양쪽 자식 peak 중 낮은 쪽과 내부 valley의 raw radius 차이다.

| 고정 물질 단면 | G3 큰 성분 최대 | G4 내부 골 깊이 | G6 큰 성분 최대 | G6에서 추가 분할된 작은 골 |
|---|---:|---:|---:|---:|
| 아래 덩어리 q≈0.05955 | 490.08 | 122.26–134.25 | 486.57 | 이 단면에서는 확인하지 못함 |
| 첫 결속 q≈0.15880 | 42.83 | 14.15 | 47.95 | 확인하지 못함 |
| 기둥 덩어리 q≈0.28131 | 498.17 | 119.28–141.57 | 510.03 | 확인하지 못함 |
| 연결부 덩어리 q≈0.36260 | 490.69 | 128.11–150.33 | 491.23 | 확인하지 못함 |
| 위 결속 q≈0.42149 | 83.63 | 18.16–27.49 | 87.72 | 확인하지 못함 |
| 상인방 중앙 q=0.5 | 490.42 | 161.01–176.73 | 412.99 | 38.54–46.12 |

첫 형상 발생 시점의 왼쪽 33개 grid ring을 마지막까지 추적하면 G3→G4에서 32개 위치, G4→G6에서 **4개 위치**에 부모 영역 내부의 추가 peak 분할이 관찰됐다. 후자의 24개 **단면별 부모 사례**에서 작은 골 깊이는 **15.89–46.12**였다. 이는 24개의 독립된 연속 능선을 인증한 수가 아니다. 좌우·앞뒤 반사 사례와 named 단면 중복을 별도 성과로 합산하지 않았다.

큰 덩어리와 잘록한 연결은 유지되지만 상인방 중앙의 큰 성분 최대는 약 16% 감소했다. 기둥·연결부의 named 단면에서는 중간 골이 충분히 생겼어도 그 내부의 다음 골은 아직 부족하다. 날카로운 면 증가를 깊은 작은 주름의 발전으로 대신 평가하지 않았다.

고정 카메라의 PRE/FORM 비교에서는 넓은 기본 평면이 이미 G0에 있고, 반복된 큰 판/능선 조직은 **G3_FORM에서 처음 뚜렷해진다**. G4는 그 끝을 갈라놓지만 넓은 판 전체를 다시 조직하지 못하며 이후 sampling만으로 이 인상이 없어지지 않는다. 이는 실제 시퀀스의 관찰이다. 단면 배치·고정 guide·발생 방향 각각의 기여 비율까지 단일 원인으로 입증한 것은 아니다.

## Task33에서 출발하며 확인한 사실

출발점은 `experiment/task33-deep-folds`, `767c5e1ce3b4521e1cf160c90c4c0f1183d0c86a`의 **V01_COHERENT_TRANSPORT**다. `TASK33_RESULTS.md`, 실제 구현·레시피·검증 기록, `V01_FINAL_RAKING.png`, `V01_NATIVE_PROGRESS.png`와 native 단계들을 확인했다. Q02 라벨의 이미지를 V01로 사용하지 않았다.

Task33의 내부 골과 계층은 유효한 비교 기준으로 유지했다. 이미 교정한 coupling과 연산 순서를 새로운 문제인 것처럼 다시 교정하지 않았다. 초기 smoothing을 단일 원인으로 잡지 않았다.

새 진단에서 Task33 `evaluate`의 입력 XYZ를 최대 74.9992 단위 바꿔도 같은 chart/carrier/recipe로 계산한 출력 XYZ 차이는 **0**이었다. 이 경로는 고정 carrier와 analytic field를 재구성한다. 부모 field의 방향 결합은 있지만, 직전 단계에서 우연히 생긴 실제 면·어깨·골을 다시 측정하는 경로는 아니다. 기존 접근의 명시적 한계이며 Task33의 성과가 없다는 뜻은 아니다. 근거는 `analysis/V01_input_response.json`이다.

V01은 좌우 대칭이지만 앞뒤 반사 XYZ 최대 오차는 **631.7628**이었다. Task34의 양면 대칭 요구에 맞추기 위해 초기 생성과 후속 제어 모두 앞뒤 대칭으로 구성했다. 별도 `TASK33_NO_TWIST`는 기존 Task33 알고리즘에 twist=0만 요청한 비교이며 앞뒤 XYZ 오차는 약 2.24e-9로 줄었다. 이 대조의 quad 교차/교환용 유효성을 인증한 것은 아니다. V01과 Task34의 시각 차이를 모두 feedback 효과로 귀속하지 않는다.

## 연산의 범위와 실제 판단 기준

새 구현은 `src/cheshire/task34_refolding.py`에 격리했다. 기존 Task01–33 알고리즘을 대체하지 않는다. 유한하게 예약한 큰 형상 발생 1회와 후속 접힘 2회이며 프랙탈 설계 논리를 도입하지 않았다.

1. **Carrier.** Task31 원본의 9개 ring 중심을 시작점으로 삼되 새 8각 elliptical 단면을 구성한다. 폭·깊이 전이와 연결부 위치를 명시한다. 원래 RECT carrier에 CC를 적용하는 V01과 입력 생성부터 다르다. 따라서 V01 대비 전체 향상은 단일 조건 실험으로 주장하지 않는다.
2. **큰 형상 발생.** 고정 물질 좌표의 결속/팽창 envelope로 큰 radial 돌출부를 만든다. 전체를 처음부터 자유롭게 탐색하는 topology 발생기는 아니다.
3. **실제 형상 읽기.** incoming native edge polyline에서 실제 XYZ, projected crest의 prominence와 양쪽 arc 폭, projected curvature, 주변 valley를 읽는다. 현재 ring 중심의 실제 길이 방향 arc에서 팽창과 결속도 측정한다. 모든 feature는 source mesh SHA, native edge 두 정점과 보간 weight에 연결된다.
4. **접힘 선택.** `split`은 측정한 crest 안의 중앙을 넣고 어깨를 내민다. 같은 rule과 같은 계수를 다음 단계에도 적용한다. 세대 번호는 `refold`의 입력이 아니다. 다음 signed distance는 현재 feature prominence와 폭으로 결정된다. cell edge 길이에 곱하지 않는다.
5. **방향.** profile 방향, 실제 incident triangle의 면적 가중 normal, 고정 guide tangent와 현재 생성 중심선 tangent를 각각 대조했다. N04는 radial 방향과 실제 중심선 tangent를 사용한다. M01은 실제 triangle normal을 0.05 혼합한다. 물질 chart와 radial projection의 좌표 guide 자체는 초기 carrier 기준으로 남는다. 모든 방향이 자유롭게 재추정되는 solver라고 주장하지 않는다.
6. **대칭과 적용.** canonical 좌측/앞쪽에서 scalar 및 displacement를 정한 뒤 반사 parity를 적용한다. 결과 XYZ의 사후 평균화는 없다. 별도 vertex lock, 자동 거리 축소, 후속 geometric smoothing을 넣지 않았다. 제어 범위는 유효성 보증이 아니며 실패는 그대로 보존한다.

측정용 scalar Gaussian filter와 macro envelope의 smoothstep은 XYZ smoothing이 아니다. renderer는 flat normal을 사용하며 smooth shading도 하지 않았다. `read_features`는 projected ring curvature 추정이며 mesh 전체의 principal curvature tensor가 아니다. 제어는 512각도, axial feature는 1,025표본과 80 프로젝트 단위 폭을 사용한다. 작은 특징이 제어용 필터에서 합쳐질 수 있는 한계가 있다.

`requested_signed_fold_distance`/`applied_signed_fold_distance`는 선택된 unit 방향의 **접힘 성분**이다. 길이 방향 성분이 더해진 실제 XYZ vector와 norm은 별도 field다. 두 성분이 직교하지 않으면 전체 norm이 signed fold distance보다 작을 수도 있다. 초반 실행의 `requested_radial`/`applied_radial`도 같은 접힘 성분을 뜻하며 과거 NPZ를 고치지 않고 분석기가 이 이름을 구분한다.

| 후보/연산 | 요청된 signed fold distance 범위 | 실제 전체 XYZ 최대 이동 |
|---|---:|---:|
| N04 G4 | -266.91…+71.17 | 266.91 |
| N04 G6 | -82.80…+28.97 | 80.75 |
| M01 G4 | -266.91…+71.17 | 266.91 |
| M01 G5 | -79.13…+28.18 | 77.56 |

실제 refinement의 vertex stencil은 이전 native XYZ에서 PRE grid를 재구성한다. 옛 grid 정점뿐 아니라 옛 quad 중심도 계승한다. 새 quadrant는 옛 centre-fan 삼각형 **두 개**에 걸치므로 하나의 가짜 부모 face로 축약하지 않았다. refinement 이후에도 기존 위치를 평균화하지 않지만, 비평면 quad의 새 centre fan은 이전 piecewise-linear 면 전체와 완전히 같은 표면이라고 보장할 수 없다. 해상도를 바꾼 결과는 다시 검증해야 한다.

## 원인을 분리한 대조와 실패

아래 0은 해당 전체 native triangle 횡단 검사에서 검출 0이다. `≥256`은 실패 기록의 검출 상한에 도달한 값으로 정확한 전체 개수나 전체 pair 완료를 뜻하지 않는다. 연구 생성 46조건과 별도 Task33 twist0 기준을 보존했고, 생성 완료와 검증 통과를 구분한 inventory를 남겼다. 복구 재실행은 연구 조건 수에 합산하지 않는다.

| 대조 | 확인한 결과와 해석 |
|---|---|
| A02의 큰 형상 발생 직전/직후 | G0/G1/G2/G3_PRE는 0, G3_FORM부터 ≥256. 초기 실패는 child 연산 이전에 생김. |
| 같은 초기 형상의 XZ 성장 D01/D02/D05 | XZ gain 0.30도 macro contact 220, 0.55는 ≥256, Y-only 0은 0. 같은 입력에서도 가능한 범위가 다름. |
| D03/D04의 분산된 연결부 | 같은 macro 계수에서 uniform/jointed 두 coarse 입력 모두 G3_FORM 0. 급격한 연결부 회전을 나누는 것이 이 조건의 radial 성장 공간을 확보함. 보편적 안전 보증은 아님. |
| E01/G01/G02 | 같은 curved jointed 입력의 notch에서 normal mix 0.15는 ≥256, normal만 0으로 바꾸면 0, 길이 방향만 0이면 ≥256. 이 계열의 새 실패에 normal 성분이 관여. |
| F01/F03 | 양 어깨를 돌출하는 split에서 fraction 0.60은 ≥256, 0.45는 0. 실제 새 돌출을 만들지만 강도 한계가 있음. |
| H00/H01/H02/H04 | actual-axis metric을 맞춘 axial off/current 비교를 별도 보존. axial mix 0.5/current는 0, 같은 frozen은 ≥256, 0.8/current도 ≥256. F03과 H01의 차이를 한 조건 효과라고 쓰지 않음. |
| I00/I01/I02/I03, K01/K02 | profile 기준은 0, surface normal 0.15는 232, measured tangent까지 쓴 0.15는 236, profile+measured tangent는 0. surface mix 0.05로 내린 K01/K02는 0. 실제 normal 추가만으로 조형/안전 향상을 보장하지 못함. |
| **J01/J02 유효 인과 대조** | current/frozen 모두 0. G3_FORM부터 G5_PRE까지 mesh NPZ가 byte-identical. 같은 마지막 rule에서만 차이가 발생. 아래 수치 참조. |
| M01/M02/M03/M04 | 같은 최종 104만 tri. M01 0, formation을 G4로 늦긴 M02 180, uniform 단면 역할의 M03 104, normal mix만 0인 M04 0. 전체 크기/최종 면 수가 같아도 발생 시점과 coarse 단면 역할이 결과를 바꿈. |
| N01/N02/N03 | 다음 접힘을 G6로 늦긴 N01은 28. fraction을 0.30으로 내린 N02도 100. G3 형성 뒤 G5/G6 접힘인 N03은 ≥256. 낮은 계수나 높은 해상도가 자동으로 안전하지 않음. |
| **N04/N05/N06** | N01에서 normal만 0인 N04는 0, 길이 방향 성분만 0인 N05도 0, 폭만 0.8로 늘린 N06은 28. N04/N05의 fine split은 모두 33개 단면 중 4개 위치에 한정. 더 많은 무작위 sweep으로 전면 발전을 주장하지 않음. |

J01/J02는 계수·스케줄·carrier가 같고 source criterion만 다르다. 첫 G4 접힘은 동일하다. 그 결과를 다시 읽는 G5에서 current feature 수는 1,806, frozen은 1,530이며 실제 control이 달라졌다. 최종 XYZ 최대 차이는 **177.9409**, RMS는 **18.3279**다. 이 수와 source SHA, 동일 접두 NPZ 증거는 `analysis/VALID_CAUSAL_V3/comparison.json`에 있다. 이는 **새로 생성된 형상이 다음 판단에 실질적으로 영향을 줬다**는 대조 근거다. current가 언제나 더 아름답다는 증거는 아니다.

고정 coarse bounds는 모든 주요 비교에서 **4000×500×3500**이다. curved 계열은 연결부 중심을 분산하고 정규화된 centreline arc도 다시 계산하므로 q 위치의 실제 공간 대응이 변한다. 이 변화도 입력 기하 변화의 일부다. 단면 역할 비교 M01/M03은 같은 curved 중심과 같은 레시피를 쓴다. macro amplitude는 500 프로젝트 단위, 후속 강도는 측정한 parent prominence에 대한 비율이다. 입력별/단계별 자동 렌더 정규화나 cell-size 배율은 없다.

## 조형 평가와 Task33 대비 잃은 점

| 목표 | 현재 평가 |
|---|---|
| 큰 덩어리의 팽창–결속–재발산 | 실제 형상과 front/oblique/90° side에서 확인. 반복된 6방향 조직은 여전히 강함. |
| 큰 돌출부 안의 중간 실제 골 | 여러 부위에서 확인. named 덩어리의 내부 골 약 119–177 단위. |
| 새 중간 형상 안의 작은 골 | 국소적으로 확인. 33개 표본 중 4개 위치. 기둥·연결부의 대표 named 단면에는 부족함. |
| 연결부에서 흐름이 모이고 방향이 바뀜 | coarse 전이와 guide/현재 중심선 반응은 생김. 넓은 면 전체를 따라 유기적으로 방향이 바뀌는 연속 crease 망은 인증하지 못함. |
| 생성 형상이 다음 변형을 바꿈 | 유효한 current/frozen 대조로 확인. 세대별 계수 변경과 구분함. |
| 전체 입체 구성 발전 | V01보다 각진 팽창 덩어리와 어깨의 실루엣 변화가 큼. 반면 넓은 평면과 판 반복이 남고 매끈한 연속성은 약해짐. 전체 목표는 PARTIAL. |

Task33의 중간 골 약 75–287, 작은 골 약 15–116과 비교하면 Task34의 새 ‘실제 기하 feedback’이 더 깊고 풍부한 장식을 전면적으로 확보했다고 할 수 없다. 서로 다른 carrier와 측정 좌표의 깊이 수치를 직접 순위로 삼지 않고 동일 world-plane cut과 동일 카메라도 함께 제공한다. V01의 twist를 양면 대칭 때문에 제거한 효과도 분리했다. 입력을 바꾼 것만으로 문제를 해결했다고 주장하지 않는다.

확인된 새 한계는 **현재 crest prominence 자체가 작아지고 tip 폭이 좁아지면 다음 변형도 작아진다**는 점이다. cell length/세대 계수 감소를 제거해도 같은 문제가 모두 해결되지는 않았다. 좁은 어깨가 한두 angular cell에서만 움직이는 경우와 제어용 filter가 작은 특징을 합치는 경우가 있다. N 계열은 더 많은 샘플링이 일부 새 골을 드러내지만 contact와 전면적 발전을 동시에 해결하지는 못했다.

## 검증 범위와 개구부 변화

N04의 G0, G3 PRE/FORM, G4 PRE/FOLD, G6 PRE/FOLD 및 최종 교환 표면은 전체 횡단 검사 0이다. M01도 G0, G3/G4/G5 연산 전후와 G6 최종 0이다. 최종 두 후보는 각각 **524,802 정점 / 1,049,600 native 삼각형**, 단일 연결 성분, Euler=2, invalid vertex link·orphan·퇴화 삼각형 0이다. N04의 최소 삼각형 면적은 약 1.4553이다.

N04 최종 LR/FB XYZ 반사 오차는 각각 약 **1.85e-12 / 1.03e-12**, 양쪽 oriented triangle cycle 불일치는 **0**이다. 대칭은 제어와 실제 topology 모두 검사했다. native가 처음부터 explicit triangle이므로 quad triangulation을 사후 수정하지 않았다.

world Z=650/1300/2200/2750/3050, Y 중앙, X 기둥, 사선 joint plane의 실제 삼각 표면 단면도 기록했다. N04의 해당 cut graph는 non-cycle node, zero-length segment, crossing/touch/overlap 검출 0이다. Z2200에는 돌출부 때문에 6개 단면 cycle이 생긴다. 이것을 6개의 게이트 개구부로 해석하지 않는다. 중앙 Y-plane의 U 단면은 하나의 cycle이다.

원래의 단일 주요 U 개구부는 보이지만 **크기와 headroom은 유지되지 않았다**. 실제 중앙 Y 단면에서 고정 Z+0.12345 probe의 중앙 air interval은 다음과 같다.

| 실제 중앙 Y 단면 | Z≈650 | Z≈1300 | Z≈2200 |
|---|---:|---:|---:|
| Task34 G0 | 2335.03 | 2469.98 | 1976.80 |
| Task33 V01 | 2219.34 | 2438.23 | 2129.94 |
| N04 최종 | 1620.52 | 2402.99 | 956.46 |

LR 대칭선에서 +0.12345 X offset의 중앙 headroom probe는 G0 **2599.96**, V01 **2666.50**, N04 **2375.88**이다. 정확한 대칭선이 native edge와 일치한 첫 probe는 불확정 기록으로 남기고, 같은 명시적 offset으로 재측정했다. 기존 `main_portal_gap_X`는 모든 Y의 X extrema를 사용해 N04 Z2200에서 26.28로 나오는데, 이는 투영 gap proxy이며 실제 중앙 깊이의 통과 폭으로 쓰면 안 된다. 두 지표와 한계를 모두 보존했다. 단일 주요 개구부의 시각/단면 조건과 건축적 전 깊이 clearance 인증은 구분한다.

전체 3D contact 검사는 기존 Task32/33와 동일하게 shared vertex, 공면, 경계·접선 접촉을 제외한다. 0은 완전한 solid 인증이 아니다. 유한 plane 검사도 그 사이 공간의 인증이 아니다. feature peak의 finite matching은 연속 differential ridge 인증이 아니다. renderer float32 오차는 native double 검사와 별도 기록한다. Rhino GUI import/Undo나 제작 가능성은 검증하지 않았다.

## 재현, 파일과 보존

모든 새 실험은 `E:/CHESHIRE_DATA/task34/`에 격리했다. 주요 산출물은 다음과 같다.

| 목적 | 외부 연구 root 기준 경로 |
|---|---|
| N04 전체 native 단계, V01 동일 조건 4view | `renders/N04_NATIVE_PROGRESSION.png` |
| M01 전체 native 단계 | `renders/M01_NATIVE_PROGRESSION.png` |
| V01 / Task33 twist0 / M01 비교 | `renders/V01_TASK34_COMPARISON.png` |
| 실제 90° 측면 비교 | `renders/TRUE_SIDE_90.png` |
| 실제 삼각 표면 단면 PNG/PDF | `analysis/N04_MEASURE/figures/ACTUAL_TRIANGLE_CUTS.*` |
| 동일 native edge의 단계별 깊이·확대 | `analysis/N04_MEASURE/figures/MATERIAL_EDGE_DEPTHS.*`, `SAME_SHOULDER_DETAIL.png` |
| raw XYZ 단면·feature 및 finite 관계 | `analysis/N04_MEASURE/*_cuts.npz`, `*_material_edges.npz`, `measurements.json` |
| 유효 current/frozen 인과 대조 | `analysis/VALID_CAUSAL_V3/comparison.json` |
| 실제 operator/feature-source 검증 | `analysis/N04_LINEAGE/lineage.json`, `M01_LINEAGE/lineage.json` |
| 교환용 OBJ와 모든 좌표/면 round-trip | `deliverables/N04_VERIFIED_OBJ/`, `M01_VERIFIED_OBJ/` |
| 모든 요청·소스 snapshot·실패·측정·자원 | `definitions/`, `candidates/`, `validation/`, `logs/`, `resources/`, `analysis/experiment_inventory.json` |
| 과거 보존 및 새 복구 증거 | `preservation/`, 최종 `FINAL_ARTIFACTS.json` |

전체 front/oblique/62° side는 공통 width=5600, target=(-400.036865,-18.533447,1750), 각도 (0,0)/(28,22)/(62,15)다. 추가 true side는 (90,0)이다. 연결부는 모든 단계에 같은 width=1700과 target=(-1950.036865,-18.533447,2900)을 적용한다. 같은 clay, key/fill/ambient와 flat normal을 사용하고 그림자·per-stage 자동 framing은 쓰지 않았다. 각 manifest가 native SHA, 이미지 SHA, camera, stage label, framing을 묶는다. joint crop은 의도한 고정 부분 crop이다.

```powershell
# 항상 새 tag. 기존 완성 연구 경로에 재실행하지 않는다.
.\.venv\Scripts\python.exe -B tools/task34_research.py --action run --request studies/task34/definitions/refold_gate.json --tag MY_NEW_TASK34_GATE
```

`surface_normal_gate.json`은 M01, `current_control.json`/`frozen_control.json`은 J01/J02, 두 `failed_*.json`은 검증된 실패 조건이다. `--action audit/render`는 `{"items":[...]}`의 명시적 stage를, `planar/deliver`는 `{"candidate":"..."}`를 받는다. 교환 표면 audit tag는 `<candidate>_EXPORT_FULL`, item ID는 `TRIANGLES`여야 하며 `deliver`는 그 SHA와 전체 검증을 확인한 뒤 진행한다. native 형상과 모든 상태를 계속 작업의 기준으로 사용한다.

양 후보 OBJ는 모든 double 좌표와 oriented triangle의 정확한 17자리 round-trip을 검사했다. source revision만으로 중간 연구를 복구한다고 가정하지 않고 각 실행의 정확한 producer file overlay를 함께 남겼다. 독립 bundle clone은 checkout-local 새 venv에서 복구한 소스의 실제 import 경로를 확인하고 G0부터 최종까지 native mesh/operator/formation/material/control NPZ의 byte-exact 재실행을 검사한다. 설치된 dependency는 원래 환경을 읽기 전용으로 참조하므로 완전한 offline dependency 백업과는 다르다. 최종 실행 결과·HEAD·bundle SHA는 `preservation/`에 기록한다.

최종 전체 회귀는 기존 MOLA DLL/CoreCLR 경로와 기준을 유지한 **935 passed**다. 기존 928개에 Task34의 7개 검증을 추가했고 skip/기준 완화는 없다. 최종 로그·exit code·source SHA·dependency/DLL 버전과 SHA는 `tests_final/`에 있다. 분석기의 초기 field-name/formation-log 혼동과 정확한 대칭선 probe 실패도 삭제하지 않고 교정한 새 tag의 결과와 구분했다.

Task31 **1,539**, Task32 **4,033**, Task33 **5,278**개 기존 외부 파일을 전후 size/SHA256으로 검증했다. 과거 데이터 전체를 다시 복제하지 않았다. 출발 tracked 파일 805개 중 현재 안내 README/CURRENT_PATHS 이외 **803개**의 SHA를 유지한다. Task01–33의 코드·테스트·레시피·원본 연구 보고서는 바꾸지 않았다. branch는 `experiment/task34-generated-folds`; 첫 구현 보존은 `d570f9d`이며 최종 보존 commit과 bundle은 preservation 기록을 따른다. remote push/force push, 기존 이력 삭제, 자료 이동·폐기는 없다. ALICE 코드/환경은 수정하지 않았다.

G6 실행 전 예상 native 삼각형 1,049,600, 보수적 working RAM forecast 약 3.43 GiB와 실측 가용 RAM/disk를 확인했다. 기존 process-family RAM guard를 유지했고 연구 시간을 채우기 위한 강제 runtime이나 과거 face cap을 새로 만들지 않았다. N04 생성은 약 **26.32초 / 1.04 GiB sampled peak**, M01은 **16.25초 / 0.97 GiB**였다. 실제 전후 검사·렌더·replay의 시간과 RAM은 별도 `resources/`에 남긴다.

## 변경 파일과 기술적 선택

| 파일 | 이유 |
|---|---|
| `src/cheshire/task34_refolding.py` | 유한 형상 발생, 실제 기하 기반 crest/axial feature 읽기, 다음 접힘과 양면 대칭 |
| `tools/task34_research.py` | 독립 immutable 경로, 비용 예측/기존 guard, 전후 state, 검증·동일 렌더 |
| `tools/task34_analyze.py`, `task34_plot.py` | 실제 삼각 단면과 raw edge, finite 부모/자식 관찰, 인과/계보 검증, 고정 도표 |
| `tools/task34_exchange.py`, `task34_recover.py` | 기존 Task33 writer를 고치지 않은 올바른 Task34 라벨의 OBJ 및 독립 source/state 복구 |
| `tests/test_task34_refolding.py`, `studies/task34/definitions/` | 실제 source 반응·부모 stencil·대칭/적용 거리 검증과 선택/실패 레시피 |
| `docs/TASK34_RESULTS.md`, README/CURRENT_PATHS | 결과/미달성/현재 opt-in 실행 경로 안내 |

완성된 V01을 단순 후처리하는 대신 거친 carrier부터 유한 발생 과정을 다시 구성했다. 실제 생성된 기하의 영향을 대조하기 쉽고 기존 Task33를 보존할 수 있기 때문이다. 원래 급격한 연결부는 큰 radial 성장이 child 이전부터 교차하므로 분산된 연결부를 채택했다. 범용 topology solver나 전체 프로젝트 refactor로 확대하지 않았다. 실제 normal 혼합은 강하게 쓰지 않고 유효한 낮은 값의 별도 후보로 남겼다.

## 참고 연구와 라이선스

사용자가 첨부한 8단계 이미지의 4→5→후반 변화를 ‘큰 돌출부 자체가 다음 단계에서 변형된다’는 **시각적 가설**로 사용했다. 노즐/날개는 관찰 표현이며 원본 알고리즘이 확인됐다는 뜻이 아니다. 특정 작품이나 동일 알고리즘 재현을 주장하지 않는다.

- [Botsch & Sorkine, *On Linear Variational Surface Deformation Methods*](https://igl.ethz.ch/projects/deformation-survey/deformation_survey.pdf): detail 전달과 변형 방향/곡률의 관계를 참고했다. 논문의 variational/prism-volume 방법을 구현한 것은 아니다.
- [Rusinkiewicz, *Estimating Curvatures and Their Derivatives on Triangle Meshes*](https://pixl.cs.princeton.edu/pubs/Rusinkiewicz_2004_ECA/curvpaper.pdf): 실제 기하에서 방향을 읽는 추정의 범위와 filtering을 검토했다. 그 논문의 full tensor 알고리즘 대신 본 연구는 제한된 ring projection을 사용한다.

두 논문은 저자 공개 원문 PDF를 출처/SHA와 함께 `references/`에 보존한 연구 참고 자료다. 코드 복사나 재라이선싱은 하지 않았다. 외부 구현을 새로 vendor하지 않았다. 실제 사용한 기존 Python 패키지의 버전/라이선스 metadata는 `tests_final/result.json`에 있다.

## 아직 가설인 부분과 다음 실험

반복 판 인상의 어느 비율이 6방향 초기 organization, 고정 guide frame, 각진 carrier와 narrow-crest response 때문인지는 전부 분리해서 입증하지 못했다. 그 원인을 smoothing 하나로 환원하지 않는다. 실제 surface normal 비율을 올리는 해결책은 현재 실패했다. 높은 면 수와 ancestry 기록 자체도 해결책이 아니었다.

다음은 N04의 **국소 실제 작은 골이 생긴 위치와 생기지 않은 위치를 나란히** 놓고, 새로운 좁은 tip의 chord 대비 높이와 필요한 안쪽 이동을 측정하는 작은 진단이 우선이다. 현재 prominence 비율만으로는 tip 내부 valley 발생을 보장하지 않는다. 이를 기존 큰 골의 깊이 손실 및 clearance와 함께 제한된 조각에서 검증한 뒤 전체 게이트에 적용해야 한다. 연결부의 넓은 면을 가로지르는 방향장/crease 연속성은 별도 과제로 남는다. ALICE 최소 입력 경계나 기존 Task31/32 구조를 확장하기보다, 검증된 native 후보에서 설계 비교와 이 작은 원인 실험을 이어가는 것을 권한다.
