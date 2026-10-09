# TASK36 — Neutral carrier, recursive growth, and boundary inheritance

## 판정과 실제 발생한 형상

**전체 조형 판정: PARTIAL.** 직선 정사각기둥에서 큰 면의 수축과 외부 능선,
그 내부의 부채꼴 접힘이 순차적으로 발생했다. 이후 세대는 새로 생긴 면·모서리·정점을
다시 사용해 작은 실제 골을 추가했다. 미리 굽힌 곡면을 촘촘하게 표시한 결과는 아니다.
그러나 네 방향의 긴 판과 반복되는 두 몸통 구성이 여전히 강하다. Task35보다 촘촘한
세부 구조를 얻었지만, 전체가 풍부하게 분화하는 깊은 장식의 완성으로 판정하지 않는다.

이번 연구는 실제 G8 고밀도 메시까지 생성했다. 동시에 최종 단면 추적에서 **기존
횡단 교차 검사에 누락 사례가 있음**을 발견했다. `T02_VERIFIED_BVH_G8`의 기존
검사 0건은 안전성 인증이 아니다. 그 OBJ의 검증 지위는 별도 철회 기록으로 명시했고,
원본 결과는 보존했다. `U01_INTERVAL_SAFE_G8`은 누락을 보완한 검사로 재실행한 후보다.

최종 선택은 **U01_INTERVAL_SAFE_G8**이다. 실제 2621440 삼각형과 1310722 native 정점을
가진 닫힌 기둥을 교환용 OBJ로 남겼다. 공유 쌍을 포함한 최종 보완 검사와 16개 실제
단면 경고는 모두 0건이다. 검증 제외 범위와 조형적 PARTIAL은 아래에서 구분한다.

## 보존 기준과 연구 범위

- 시작 브랜치/커밋: `experiment/task35-sectional-column`, `f3a0642c40f4a42680733aa2e98ff34897dcf521`.
- 작업 브랜치: `experiment/task36-neutral-recursive`. 원격 push는 수행하지 않았다.
- Task35 보고서와 실제 H01/H02 메시·전체 렌더, 생성 코드·레시피를 확인했다.
  Task33/34의 이미 교정된 연산 순서와 coupling은 새로운 발견으로 계산하지 않았다.
- 기존 추적 파일 869개와 Task35의 선택된 원본/OBJ/최종 manifest/bundle 7개를 해시 기준으로
  기록했다. 과거 대규모 외부 아카이브 전체를 다시 복사하거나 감사하지 않았다.
- 변경은 새로운 Task36 코드·테스트·레시피·보고서와 현재 README/실행 경로 색인에 한정한다.
  과거 연구 기록, 테스트 기준, Task35 생성 함수는 수정하지 않았다.
- 데이터: `E:/CHESHIRE_DATA/task36/`. 원래 첨부 요청은 `USER_REQUEST.txt`에 원문으로 보존했다.
  Emergent Curvature 및 Boundary Constraint 추가 지시는 아래 대조와 검사에 반영했다.

## 확인된 출발점의 한계

Task35는 고정된 각도/높이 격자에 sectional growth/incision을 적용하는 연구다.
G0부터 비등방 팔각 단면과 목·어깨의 거시적인 profile을 포함한다. 일부 세대는
표본만 증가시키고, 최종 G5~G7 세분화는 주로 둘레 방향이다. 새로운 모든 면/모서리를
독립적인 다음 국소 연산으로 취급하는 일반적 face→edge→vertex 재귀와는 구별된다.
이것이 Task35의 검증된 국소 접힘을 부정하거나 유일한 실패 원인을 확정하는 뜻은 아니다.

Task36의 G0는 1000×1000×4000, X/Y가 단면, Z가 수직인 일정한 닫힌 정사각기둥이다.
초기 operator 정점은 12개, 사각면은 10개이며 수직 방향 두 셀만 있다. 목·어깨·파형·
장식 위치·무작위 요철을 입력하지 않았다. 단위는 미확정 project units이며 mm라고
가정하지 않는다. X/Y 반사와 90° 회전을 보존했다. 이는 정사각 외곽 고정과 다르다.

두 개의 coarse axial cell은 반복 길이의 초기 조건이다. 특히 1000/3000 높이는 그
초기 면 중심과 관련되므로, 접힘 발생 위치까지 초기 토폴로지와 독립적으로 발견했다고
주장하지 않는다. 사전에 굽힌 profile을 입력하지 않았다는 사실과 구별해야 한다.

초기 계획 `studies/task36/definitions/PREREGISTERED.json`의 고정 XYZ 캡은 L 대조 이후
후속 후보에서 **캡 Z 평면만 고정하고 XY는 허용**하는 것으로 바꿨다. 초기 계획을
소급 수정하지 않았다. 모든 비교군에서 해당 비교의 캡 정책은 명시적으로 동일하게 유지한다.

## 실제 생성 연산과 계보

새 opt-in 모듈은 `src/cheshire/task36_growth.py`다. 기존 reference subdivision의
교정된 face→edge→vertex 순서를 재사용한다. 매 단계 입력의 실제 법선·dihedral 변화와
국소 지지 거리를 읽고 새로운 face/edge 위치 및 retained vertex 위치를 계산한다.

국소 스케일은 면 중심에서 네 supporting edge line까지 거리의 최솟값이다. 길쭉한
면의 긴 변 때문에 변형 거리가 과장되는 것을 피한다. 비평면 사각면의 정확한 내접반경이나
물리적인 곡률반경이라고 해석하지 않는다. 현재 형상에 따라 달라지는 support와 bend가
매 단계 다시 계산된다. 최종 레시피의 수치 gain은 세대별 실루엣 스케줄 없이 일정하다.

계보 파일에는 실제 `input_edges`, `parent_face_vertices`, `parent_face`, `parent_corner`,
직전 point class와 root anchor를 저장한다. 새 edge/face point는 다음 단계에서 corner로
재사용된다. `operator_state.npz`에는 요청/해결된 제어 배열, 실제 각 성분의 변위,
안전 제한 전 XYZ와 최종 국소 factor가 별도로 남는다. 계보 기록만으로 조형적 성과를
판정하지 않고, 이동량·같은 입력의 반증·실제 단면을 함께 본다.

사각 operator 상태와 물리적 삼각 표면은 구별한다. native에는 사각면당 보조 fan centre와
삼각형 네 개가 있다. **보조 fan centre는 독립적인 folding 자유도가 아니다.**

| 세대 | Operator 정점 | Operator 사각면 | Native 정점 | 실제 삼각형 |
| --- | ---: | ---: | ---: | ---: |
| G0 | 12 | 10 | 22 | 40 |
| G1 | 42 | 40 | 82 | 160 |
| G2 | 162 | 160 | 322 | 640 |
| G3 | 642 | 640 | 1,282 | 2,560 |
| G4 | 2,562 | 2,560 | 5,122 | 10,240 |
| G5 | 10,242 | 10,240 | 20,482 | 40,960 |
| G6 | 40,962 | 40,960 | 81,922 | 163,840 |
| G7 | 163,842 | 163,840 | 327,682 | 655,360 |
| G8 | 655,362 | 655,360 | 1,310,722 | 2,621,440 |

## 곡률·외곽의 기여도 분리

J 대조는 동일 입력/같은 gain에서 다음 세 성분을 분리했다.

`출력 = interpolating split + a·(표준 CC−split) + s·(weighted geometry−CC) + n·(full−weighted geometry)`

첫 성분은 표준 CC의 기하학적 평균화 변위다. 두 번째도 가중 선형 평균을 포함하므로
`averaging_gain=0`을 모든 평균 연산의 제거라고 부르지 않는다. 마지막은 face normal
placement가 후속 edge/vertex에 전파된 효과까지 포함한다. smooth shading이나 scalar
smoothstep은 이 기하학적 성분과 다르다. 렌더는 native flat normal을 사용했다.

| G5 대조 | 관찰 | 해석 |
| --- | --- | --- |
| J01 전체 성분 | XY 외곽 약 1368 | 초기 둥근 실루엣에는 CC 기여가 있다 |
| J02 표준 CC 성분만 제거 | 약 2112, 각진 큰 fan/판 | smoothing이 단일 원인은 아니다 |
| J03 표준 CC만 | 매끈한 수축, 장식 없음 | 곡면 정밀화와 장식 발생은 구별된다 |
| J04 normal 성분 제거 | 약 1007, 접힌 면의 큰 분절 | normal placement가 깊이 발달에 기여 |
| J05 normal 성분만 | 약 1421, 표면 질감 위주 | normal displacement만으로 충분하지 않음 |
| J06 weighted stencil 제거 | 약 1146, 튜브 성격 | 가중 결합이 큰 접힘 구성에 기여 |

이 표는 여러 세대의 경로 비교다. 안전 backtracking 계수는 서로 달랐으므로 G5 폭의
차이 전체를 한 성분의 순수한 기여량으로 해석하지 않는다. 이를 분리하기 위해 실제
J01 G2를 공통 입력으로 고정한 추가 단일 단계 대조를 수행했다. 모든 적용 계수는
1이며, FULL은 원래 J01 G3 native 배열과 정확히 일치했다. 강화된 공유 쌍 포함
검사에서도 여덟 조건 모두 교차 0건이었다.

| 같은 G2에서 한 단계 적용 | 실제 XY 폭 |
| --- | ---: |
| FULL | 1325.07 |
| 표준 CC 성분 제거 | 1421.05 |
| 표준 CC만 | 1156.70 |
| normal 성분 제거 | 1272.21 |
| normal만 | 1305.54 |
| weighted stencil 제거 | 1209.57 |
| 캡 XY만 허용 | 1325.07 |
| ancestry bias 제거 | 1270.89 |

자료는 `diagnostics/SAME_INPUT_COMPONENTS`다. 이것은 동일 입력에서의 직접 효과이며
최종 조형 평가를 대신하지 않는다.

후속 후보는 baseline CC 성분을 제거하고 stencil/normal 성분을 각각 0.65로 낮췄다.
단순 변위 증폭 대신 더 작은 국소 변화의 반복을 선택했다. 별도의 전역 profile,
전역 후처리 smoothing/relaxation은 넣지 않았다. 국소 가중 stencil 자체의 평활화/외삽
효과는 남아 있으므로 순수한 특정 folding 수학만으로 곡률이 발생했다고 주장하지 않는다.

## Boundary Constraint / Carrier Inheritance 가설 판정

| 가설 | 확인된 사실 | 판정 |
| --- | --- | --- |
| Bounding box/정규화가 외곽을 제한 | operator에 전역 XY clamp/매세대 bbox rescale 없음. 실제 외곽이 1000을 넘음 | 이 형태의 제한은 발견하지 못함 |
| 원래 G0 정점·모서리 고정 | retained vertex 이동은 `1−vertex_memory`로 조절. 기본 memory=.2. 내부 G0 점도 크게 이동 | 전체 G0 고정 가설은 기각 |
| 캡이 외곽을 고정 | 기본 fixed XYZ는 실재. L01에서 XY만 풀어도 G5 폭 1368.01→1367.88 | 제약은 존재하지만 이 비교에서 주된 원인은 아님 |
| 최초 법선만 사용 | coupled placement는 현재 실제 법선을 사용 | 최초 법선 고정 가설은 기각 |
| 초기 네 방향의 계승 | 음의 edge/vertex tension 및 상속 V/F 대각이 방향과 판 구성을 강하게 계승 | 실재하는 연산 편향; 완전 제거되지 않음 |
| 새 요소가 원래 외곽을 못 넘음 | T02 G6부터 새 점이 G0 점보다 큰 XY 극값을 형성. S 대조도 새 G1 점이 극값을 형성 | 절대적인 외곽 봉쇄는 아님 |
| 렌더 정규화가 변화를 가림 | 카메라 폭 5000, target=(0,0,2000), 조명 고정. 세대별 fit 없음 | 해당 렌더에서는 발견하지 못함 |

edge tension −.7의 기준 edge stencil은 이전 양 끝점 기여가 85%, 새 face 기여가
15%인 혼합이다. vertex tension −2는 단순 평활화가 아닌 반대 방향의 외삽을 포함한다.
이것은 hard lock과 다르지만 root edge/큰 판을 계승하는 원인이다. L02의 상속 bias 제거는
큰 fan 대신 튜브/질감 성격을 강화했다. S01~S03의 현재 normal contrast 반응은 새 점의
외곽 참여를 만들었지만 전체 판 지배를 해결하지 못했다. S04/S06의 edge 결합 변경은
G4에서 캡 삼각형 32개의 방향이 뒤집혀 거절했다. S05의 vertex tension 제거만으로도
더 둥근 튜브가 되어, 유망하지 않은 방향을 고밀도로 확대하지 않았다.

reference의 edge normal은 두 현재 face normal의 산술 평균이며 unit-normalized
방향이 아니다. 따라서 접힌 면의 법선이 서로 상쇄되면 직접 edge-normal 변위가
약해질 수 있다. 실제 구현 사실이지만, 이것을 판 지배의 단독 원인으로 분리한 실험은
이번에 수행하지 않았다. full edge 위치에는 face→edge 결합도 포함된다.

T02의 실제 전체 XY 폭은 G3 1499.90 → G5 1686.20 → G7 1737.75 → G8 1744.03이다.
G8의 원래 12점 XY 극값은 847.56, 전체 점의 극값은 872.02이다. 초기 바깥 점들은
실제로 약 491.53 이동했다. 다만 T02에는 아래 교차 결함이 있으므로 이 수치는 경계
자유도의 진단 증거이며 검증된 교환 후보의 성과로 사용하지 않는다.

90° 회전 대칭은 일정한 square carrier와 동일한 기하 규칙이 계승하는 조건이다.
네 방향의 동일성은 유지하지만 각 방향 안에서 굽은 단면이나 분기는 가능하다.
이를 각 높이의 사각 외곽 보존 조건으로 해석하지 않았다.

## 물리적 표면의 재분할에서 발견한 병목

비평면 사각면을 평균 fan centre로 다시 분할하면, inactive split만으로도 원래 실제
삼각 표면이 바뀐다. 동일한 M01 G5 입력에서 mean split은 횡단 교차 32건과 면적
−41027.42 변화를 만들었다. V/F 대각 midpoint를 사용하고 입력의 실제 fan centre를
표본으로 삼는 `surface='vf'`는 같은 비교에서 교차 0건, 면적 차이 약 7.45e−9였다.
원본/두 자식 표면은 `diagnostics/SAME_G5_SURFACE_SPLIT`에 있다.

이 변경은 변형 없는 refinement의 표면 오차를 제거한다. 강한 active folding의 교차까지
없애지는 않는다. N01은 여전히 G6에서 거절됐고, 후속 smaller/deeper + local safety를
시험했다. inactive VF의 실제 표면 거리/면적 보존은 별도 테스트로 확인했다.

## 안전 제한과 교차 검사에서 발견한 별도의 결함

과거의 전역 backtracking은 한 부위의 교차 때문에 모든 점의 변형을 함께 줄였다.
새 국소 방식은 실제 충돌 삼각형이 속한 사각면의 operator 점만 선택하고, 대칭으로
닫힌 마스크의 변형량을 절반씩 줄인다. 매번 전체 삼각형 검사와 캡 방향/퇴화를 다시
확인한다. 너무 작은 factor는 0이 되며 개수도 기록한다. 안전한 부분의 변형은 유지된다.
반복 budget이 소진되거나 결함이 남으면 실패로 저장하며 통과시키지 않는다.

Q03의 256 pair batch/24회 budget은 G7에서 72건을 남겨 거절됐다. 4096 pair batch는
더 많은 충돌을 같은 회차에서 처리했다. 이는 검출 허용오차 완화가 아니다. 최종 U01은
같은 batch와 최대 48회 진단 budget을 사용하며, 실제 사용 회수는 metadata에 기록한다.

### 기존 검사 0건을 철회한 이유

Task33의 narrow phase는 삼각형 모서리와 상대 삼각형의 **엄격한 내부 barycentric hit**를
검사한다. 교차선의 두 끝이 각각 양쪽 삼각형의 모서리에 정확히 놓이면 모든 hit가
거절되지만, 그 사이에는 양쪽 삼각형 내부의 실제 교차선이 존재할 수 있다.

T02 G8의 `Z=1000.12345` 실제 단면에서 원본 삼각형 쌍 `922974/1283423` 등을 추적했다.
두 법선의 외적 크기는 약 .252로 비평행이며 공유 정점도 없다. barycentric 좌표가
0인 endpoint 때문에 기존 판정은 False다. 이는 단순한 점 접촉이나 공면 겹침이 아니다.
전체 16개 실제 단면의 경고를 native ID까지 역추적한 `T02_SECTION_TRACE`에서도
같은 positive noncoplanar interior interval 문제가 확인됐다.

보완 검사 `tools/task36_triangle_interval.py`는 서로의 평면으로 두 삼각형을 잘라,
공통 교차선 위의 내부 구간이 양의 길이로 겹치는지 검사한다. 양쪽 삼각형 모두 상대
평면을 가로질러야 한다. **기존 strict 검사 OR 보완 검사**를 적용하므로 기존 검출을
제거하지 않는다. 별도 synthetic edge-to-edge 반례, 떨어진 구간, 평행/점 접촉,
실제 T02 반례 테스트를 추가했다. 기존 Task32/33 함수나 테스트는 바꾸지 않았다.

기존 BVH 가속은 이 발견과 구별된다. 자체 C# helper는 AABB 후보 탐색만 가속했고
기존 narrow phase를 그대로 호출했다. 양성/음성/무작위 fixture와 실제 G7에서 pair 및
exhausted 후보 수가 동일했다. R01→T02의 G0~G7 mesh/quad NPZ 30개도 byte SHA가
동일하다. 따라서 누락은 가속으로 발생한 것이 아니라 기존 strict predicate의 한계다.

`deliverables/T02_VERIFIED_BVH_G8/WITHDRAWN_VALIDATION.json`이 이전 OBJ의 검증 철회를
명시한다. 데이터는 삭제하지 않았다. 이 후보 이름의 VERIFIED는 당시 실행 ID일 뿐
현재 안전성 판정으로 읽으면 안 된다. U01은 `contact_engine='bvh_interval'`을 사용한다.

보완 검사의 거리 허용오차는 mesh 최대 span으로 정규화한 좌표에서 1e−10이다.
생성 중 `bvh_interval`은 기존 shared-vertex broad-phase 제외를 유지한다. T02의 유한
단면 경고 7652개 중 644개는 공유 정점 쌍이었다. 따라서 최종 독립 감사에는
`bvh_inclusive`도 추가했다. 이 경로는 공유 정점 쌍을 후보에 포함하고, 정상적인 hinge나
점 접촉과 구별해 양쪽 내부의 양의 교차 구간만 검출한다. 별도 반례/정상 hinge 테스트로
확인했다. 공면 및 경계만의 접촉/접선은 여전히 제외된다. 유한한 단면과 검사 0건만으로
모든 solid validity, 두께, 제작/강도를 인증하지 않는다.

## 재귀적 발달의 증거와 측정 한계

Q01 G6의 동일 입력/동일 실제 안전 마스크 대조에서 정확 replay 차이는 0이다.
새 점 변형을 제거하면 최대 좌표 차이 160.44, retained 이동만 제거하면 35.53이다.
feature control을 rest로 고정하면 12.98 차이가 난다. 후자는 placement와 법선까지
초기 형상으로 돌리는 실험은 아니다. 해당 counterfactual 중 일부는 교차를 만들어
실패 상태로 보존했으며 교환용 결과로 사용하지 않는다.

실제 표면을 보존하는 subdivision-only 대조와 early-G1/G2-only 대조는 후속 active
folding과 구별된다. 새 점이 움직인다는 사실 자체는 새로운 골의 증명이 아니므로
material edge curve와 실제 삼각 표면 절단을 별도로 측정했다.

측정에는 2048개의 필터 없는 유한 표본과 기존 prominence 15 project units를 사용했다.
material 곡선은 실제 operator/native edge 연결을 확인한 source ID와 보간 weight로
추적한다. 비평면일 수 있으며, 고정 세계 Z 단면과 같지 않다. radial excess의 골 깊이는
공간상 최단거리나 곡면을 가로지르는 정확한 fold depth가 아니다. finite parent basin
내부의 flanking crest/valley 증거이며, 연속 능선 전체의 인증이 아니다.

T02의 material G7→G8에는 13개 사전 지정 높이 중 1000/2000/3000의 세 위치에서만
추가 내부 골이 기록됐다(80개 finite basin 기록, radial depth 15.41~23.53). 다른 위치에
있다고 확대하지 않는다. 그러나 T02는 교차 결함이 있어 최종 기하 성과에서 제외한다.
모든 G8 고정 세계 횡단/종단에는 multiple-hit ray가 있어 radial peak 집계는 무효다.
outermost ray만 골라 숫자를 만들지 않았다. 실제 raw segment와 경고는 그대로 보존했다.
U01의 최종 수치는 완료 기록에서 별도로 보고한다.

## 렌더·실제 메시·검증 자료의 읽는 법

G0와 모든 G1~G8에서 split-only `Gg_PRE` 및 실제 `Gg_FOLD`를 저장한다.
각 native `mesh.npz` 외에 `quad_state.npz`, `operator_state.npz`, identity, metadata,
source overlay, recipe, 실행 시간·메모리 기록이 있어 OBJ만으로 복구한다고 가정하지 않는다.

전체 카메라는 물리 폭 5000, target=(0,0,2000), front=(0,0), oblique=(28,22),
정확한 side=(90,0)다. 같은 world light를 사용하므로 측면은 상대적으로 어둡다.
매 단계 bbox fitting, geometric smoothing, 이미지 retouching은 하지 않았다.
detail은 모든 세대에 동일한 target=(0,0,1000), width=1800을 썼다. detail은 부분을
의도적으로 crop한 것으로 전체 외곽 인증이 아니다. 렌더 manifest의 native SHA,
candidate/세대 label, image/visibility SHA를 검증한다. 표시용 float32 오차는 별도 기록한다.

실제 횡단은 Z=500..3500을 250 간격으로, 각 값에 .12345를 더한 고정 평면이다.
종단은 Y=0, X=0, X=Y다. raw 삼각 표면 절단 선분과 PNG/SVG를 제공한다.
graph snap 7 decimals와 방향 허용오차 1e−8은 검사 식별용이며 메시 repair에 사용하지 않는다.

## 계산·의존성·출처

G8 사전 비용은 655360 사각면/2621440 삼각형, `512 MiB + 삼각형당 1800 bytes`로
약 5.26 GB를 예측했다. 실제 process-family RAM, 사용 가능 RAM의 65%/12 GiB 상한과
2 GiB free floor를 기존 guard로 관찰한다. 예측은 실행 전 55% reserve를 사용한다.
실행 시간·과거 face cap으로 안전 검사를 건너뛰지 않았다. G9는 약 1049만 삼각형과
약 19.41 GB 예측으로 이 guard의 12 GiB 상한을 넘는다. 개선 근거 없이 실행하지 않았다.

기존 검사 G7의 6379824 후보를 같은 순서/결과로 검사하면서 BVH 경로는 약 7.13초였다.
큰 batch R01 G7의 생성/repair 전체 1126.84초는 T02 102.87초로 줄었다.
생성 규칙을 바꾸는 최적화와 검출 predicate를 보완하는 변경을 별도로 보존했다.

새 외부 패키지·논문 코드·라이선스가 추가되지 않았다. C# BVH와 interval 보완은 이
연구에서 작성한 코드다. 기존 repository의 reference/Task29/32/33 helper를 재사용한다.
Windows 기존 .NET Framework C# compiler로 SHA별 helper를 빌드하며 소스·binary hash를
저장한다. NumPy/SciPy/Trimesh/COMPAS/Pyrender 및 MOLA/CoreCLR 등 기존 의존성의 버전,
license metadata와 DLL hash는 최종 테스트 기록에 있다. 그림 생성만 기존 ALICE venv의
Matplotlib을 읽어서 사용했다. Hansmeyer의 원래 알고리즘을 구현했다는 주장은 하지 않는다.

## 완료 기록

### 마지막 원인 분리: 몸통과 캡의 edge coupling

S04에서 전역 `edge_tension=0.5`는 캡 삼각형 32개를 뒤집었다. 이를 몸통의 불가능으로
해석하지 않고, 새 선택값 `cap_edge_tension=-0.7`로 **끝단 edge에만 기존 규칙을 유지**했다.
몸통의 값 0.5는 edge 배치에서 새 face의 비중을 75%, 이전 endpoint를 25%로 바꾼다.
기존 -0.7의 비중은 각각 15%/85%다. 변위 gain을 증폭한 실험이 아니다.
기본값 None은 이전 모든 실행을 그대로 유지하며, 캡 반전과 분리 제어를 직접 비교하는
회귀 테스트를 추가했다. W01/W02 G5는 sign response를 분리한 대조이고 W03는 W02의
동일 gain을 G8까지 반복한다.

**W03_BODY_RECURSIVE_G8**은 두 넓은 몸통이 가는 부분으로 모였다가 벌어지는 전체
구성이 U01보다 분명하다. 하지만 넓고 각진 옆면과 긴 능선이 남는다. 물질 곡선의 새
부모 내부 골은 G4에서 2/13 높이(1500/2500), G5에서 6/13(750/1250/1750/2250/2750/3250),
G6에서 2/13(500/3500)에 나타났고, **G7·G8에서는 고정 prominence 15의 새 골이 0/13**이다.
기존 골이 모두 없어졌다는 뜻은 아니며, 이 측정에서 추가 발달을 확인하지 못했다는 뜻이다.
G7→G8 부모 envelope ratio는 0.9992–1.0911이다. U01의 G8 3/13 높이에서 72개의
절단별 child basin이 추가된 성과를 W03의 전체 실루엣 개선으로 대체하지 않는다.

W03의 전체 폭/깊이는 1551.4173, 높이는 4000, 원래 12점의 최대 이동은 389.9109다.
초기 외곽을 벗어난 operator 점은 148976개다. 그러나 G2 이후 새로운 E/F 점은 직전
전체 XY bbox를 넘지 않으며 G8의 최대 XY는 원래 corner 후손과 일치한다. U01에서도
G3 이후 새 E/F는 직전 전체 bbox를 넘지 않았다. 이는 **전역 bbox clamp가 없다는 사실과
새 점의 외곽 발생이 충분하다는 주장이 다름**을 보여준다. 현재 coupling/초기 토폴로지의
외곽 상속 병목은 해결 완료로 보고하지 않는다. 산술평균 edge normal의 소멸은 일부
강한 접힘에서 관찰됐지만 중앙값은 U01 G8에서 약 0.992여서 전체 실패의 단일 원인으로
확정하지 않았다.

W03도 1310722 native 정점/2621440 삼각형이다. 공유 쌍을 포함한 전체 interval 검사
24480784 후보에서 교차 0, 16개 단면 경고 0, 연결 성분 1/Euler 2/퇴화 및 link 오류 0,
대칭 최대 오차 약 4.11e-12, 끝단 Z 오차 0이다. 공면·접선·경계만의 접촉은 검사에서
제외된다. 13개 횡단 radial profile은 모두 다가값이므로 골 개수를 계산하지 않는다.
기술적으로 검증된 대조 OBJ를 별도로 제공하며 주 선택 U01을 덮어쓰지 않는다.

### 실행·검증·복구 자료

- 전체 회귀: **979 passed, 59.58초**, skip/기준 완화 없음.
  `E:/CHESHIRE_DATA/task36/tests_final_body/`에 원본 로그·의존성/DLL SHA·테스트 SHA가 있다.
- U01 전체 생성 1260.86초, 관찰된 process-family peak 약 3.22 GB. W03 전체 생성
  346.07초, peak 약 3.12 GB. W03 G8 local repair는 13회, 제한점 46948개, 0 factor는 0개다.
  U01 G8는 24회, 제한점 124548개, 0 factor 132개다. 시간은 측정된 이 환경의 값이다.
- 모든 주요 직전/직후: `validation/U01_EARLY`, `U01_PRE8`, `U01_FINAL` 및
  `W03_EARLY`, `W03_PRE8`, `W03_FINAL`. 최종 공유 쌍 포함 검사는 각 FINAL에 있다.
- 재생성은 Git bundle의 새 clone와 해당 producer의 정확한 source overlay에서 수행했다.
  U01과 W03의 각각 G0–G8 **50개 NPZ byte hash** 비교 결과는
  `preservation/RECOVERY_U01_G8/recovery.json`, `preservation/RECOVERY_W03_G8/recovery.json`이다.
  동일 호스트의 기존 dependency site/DLL을 사용했으며 독립적인 offline 설치 보장은 아니다.
- 최종 외부 `preservation/FINAL_STATE.json`은 완료 커밋과 bundle, 보존 검사 결과를 연결한다.
  `preservation/FINAL_INVENTORY/inventory.json`은 보호한 기존 소스/Task35 자료와 전체
  Task36 checkpoint/source/render label 및 SHA의 최종 확인이다. 전체 외부 과거 자료의
  새 독립 인증으로 확대하지 않는다.
- T01은 metadata 변수 충돌로 중지된 도구 오류, R01은 BVH 도입을 위해 의도적으로 중단한
  실행이다. 형상 실패와 구분해 원본 로그를 남겼다. 초기 복구 v1의 venv guard 실패와
  Task35 비교 composite의 이름 충돌도 보존했다. 후자는 남은 동일 render/manifest에서
  새 파일명으로 완료했으며 기존 이미지를 덮어쓰지 않았다.

대표 자료는 `E:/CHESHIRE_DATA/task36/` 기준 다음과 같다.

| 자료 | 경로 |
| --- | --- |
| U01 실제 G0–G8 정면/사선/측면 | `renders/U01_ALL_GENERATIONS.png` |
| U01 동일 부위 확대 | `renders/U01_HIERARCHY_DETAIL.png` |
| W03 실제 G0–G8 및 확대 | `renders/W03_ALL_GENERATIONS.png`, `renders/W03_HIERARCHY_DETAIL.png` |
| 같은 G8 U01/W03 대조 | `renders/W03_VS_U01_G8.png` |
| Task35 H01과 U01 동일 조건 | `renders/TASK35_H01_VS_TASK36_U01.png` |
| 실제 삼각 표면 횡단/종단 | `plots/U01_ACTUAL_SECTIONS/`, `plots/W03_ACTUAL_SECTIONS/` |
| 검증된 원래 좌표의 교환 OBJ/recipe | `deliverables/U01_INTERVAL_SAFE_G8/`, `deliverables/W03_BODY_RECURSIVE_G8/` |
| 모든 세대 native·quad·operator state | `candidates/U01_INTERVAL_SAFE_G8/`, `candidates/W03_BODY_RECURSIVE_G8/` |
| 실제 물질 edge 곡선/추가 골/외곽 측정 | `measurements/U01_MATERIAL/`, `measurements/W03_MATERIAL/`, `measurements/U01_BOUNDARY/`, `measurements/W03_BOUNDARY/` |

같은 입력의 비교와 실패 자료를 포함한 전체 ledger는 최종 inventory를 기준으로 한다.
준비된 definition 개수를 실제 수행한 실험 수로 세지 않는다. 이번 연구에서 확인한
재귀적 세부 발달과 일부 거시 변화는 성과지만, **큰 구조 안의 깊은 작은 골이 전체에
분포하고 모든 각도에서 풍부한 장식으로 읽히는 최종 목표는 PARTIAL**이다.

## 다음 연구 전략

1. G9의 면 수 확대보다 **현재 형상의 접힘 방향으로 local stencil을 재조직하는 소규모
   대조**를 우선한다. 단순 상속 bias 제거는 튜브로 돌아갔으므로 큰 부모 접힘을
   유지하는 기능과 V/F 대각 고정을 분리할 필요가 있다.
2. 초기 네 root face와 두 axial cell의 반복을 바꾸는 최소 토폴로지 대조를 별도로
   구성한다. 거친 장식을 미리 새기는 대신 같은 중립 외곽/같은 실제 변형 스케일을
   유지해야 한다. 현재 자료는 초기 토폴로지 전체의 영향이 제거됐다는 증거가 아니다.
3. 생성된 큰 판의 내부 폭·방향을 기준으로 다음 edge/face 배치를 선택하되, 먼저
   작은 조각에서 위계와 깊이 유지·교차를 확인한다. 모든 face에 동일한 class sign을
   반복하는 규칙만으로는 전체 조형 분화가 충분하지 않았다.
4. 보완 교차 검사와 실제 단면 경고를 함께 유지한다. 이번에 찾은 strict edge 반례를
   통과하지 못하는 결과를 검증된 교환 메시로 다시 부르지 않는다.
5. 기둥 결과를 게이트/스툴의 설계 또는 제작 성공으로 확대하지 않는다. 상인방 결합,
   강도, 최소 두께, 가구 치수 설계는 이번 범위에 포함되지 않는다.
