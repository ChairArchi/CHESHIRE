# ASTRA — 연구 계보 및 독립 제약 감사

2026-10-10. 과거 결과의 요약을 다시 작성하는 대신, 유지할 근거와 재검토할 선택을 연결한다. 현재 연구의 다른 후보 실행·검증이 완료됐다는 주장은 이 문서에 포함하지 않는다. 여기서 새로 실행한 것은 §4의 **U01 G2→G3 단일 단계 대조 네 개**뿐이다.

## 1. 근거와 읽는 순서

- [전체 Task01–36 색인](astra/TASK_LINEAGE.md), [Task01–31 복원 상태](astra/TASK01_31_INDEX.json), [대표 실제 이미지](astra/IMAGES.md).
- [기존 상세 원장](E:/CHESHIRE_DATA/research_archive/CHESHIRE_TASK01_31_MASTER_LEDGER.md), [기술별 변화](E:/CHESHIRE_DATA/research_archive/TECHNICAL_EVOLUTION.md), [전환점](E:/CHESHIRE_DATA/research_archive/TURNING_POINTS.md). 원장과 소스·checkpoint를 구별한다.
- [자료 공백](E:/CHESHIRE_DATA/research_archive/MISSING_MATERIAL.md), [현재 경로 공백](astra/MISSING_PATHS.json), [원본 경로 목록](astra/LOCAL_FILES.csv).
- 실제 최신 연산은 [Task36 소스](../src/cheshire/task36_growth.py), [reference 연산](../src/cheshire/reference_subdivision.py), `E:/CHESHIRE_DATA/task36/candidates/{U01_INTERVAL_SAFE_G8,W03_BODY_RECURSIVE_G8}/`의 request·quad·native·operator 배열을 대조했다.

Task01–05 개별 당시 실행 로그, Task01/12 최초 자연어 요청, Task01–09 원본 raster 일부는 미발견이다. 일부 옛 Rhino lifecycle은 당시부터 미검증이었다. **자료 복원 완료, 당시 기술 검증 통과, 오늘의 강화된 검증 통과는 서로 다른 사실**이다. 기존 979개 테스트 통과는 인수인계 기준점의 결과이며 이 문서 작성 중 전체 회귀를 새로 실행하지 않았다.

## 2. Task01–36: 기술 전환과 남은 선택

| Task | 확보한 연구 기반 | 현재 독립 연구가 다시 볼 부분 |
|---|---|---|
| 01–04 | OBJ identity, 기하 측정, scalar mapping, deterministic rule/budget | normal variation은 곡률 proxy. smoothstep은 기하 smoothing과 다르며 비용 통과도 형상 품질 인증은 아니다. [원장](E:/CHESHIRE_DATA/research_archive/CHESHIRE_TASK01_31_MASTER_LEDGER.md#task01) |
| 05–08 | 실제 normal 이동, 양의 lineage, quad refinement, Rhino 외부 worker | signed 위치 계수와 semantic parent를 분리한 계약은 유효하다. 일반 재귀 엔진과 전체 host lifecycle은 자동 완성된 것이 아니다. [계보](astra/TASK_LINEAGE.md) |
| 09–13 | MOLA taper·cap 재귀, raw/terminal CC 대조, 시각 prototype·고정 카메라 atlas | face-local tile/scaffold가 남았다. terminal smoothing만으로 큰 조직이 새로 생기지 않았다. [Task11 비교](astra/images/T11_RAW_CC.png) |
| 14–16 | modified CC, coarse carrier, 직전 V/E/F class | legacy 경로의 같은 세대 coupling 한계는 Task29에서 별도 교정됐다. 이를 새 버그로 재발견하지 않는다. [수식 계약](WEIGHTED_SUBDIVISION_REFERENCE.md) |
| 17–18 | DS F/E/V 기원, CC↔DS 전환, 여러 공간 규모의 activity | DS의 구성 차이는 확보했으나 독립 micro는 약했다. peak-normalized activity의 총량은 같지 않아 순서 우월성을 확정하지 못했다. [Task17](TASK17_RESULTS.md), [Task18](SPATIAL_ACTIVITY_STUDY.md) |
| 19–21 | 실제 topology event·sibling role·directional roof | 계보와 분기는 수치·위상적으로 달랐으나 셀을 넘는 조형 관계는 약했다. 큰 fin은 교차했다. [19](ORNAMENT_CAPABILITY_STUDY.md), [20](DIFFERENTIATED_BRANCHING_STUDY.md), [21](VOCABULARY_SANDBOX_STUDY.md) |
| 22–23 | literal SUM attraction, finite crease와 descendant graph | sharpness/graph 연결은 깊은 접힘과 동일하지 않다. 강한 attraction의 collapse와 교차 실패를 보존했다. [22](BEYOND_SMOOTHNESS_STUDY.md), [23](CROSS_CELL_CREASE_STUDY.md) |
| 24–25 | 실제 큰 말림의 조상 추적과 후속 continuation | 강한 normal offset을 멈추자 curl이 회복됐지만 새 작은 위계는 약했다. 큰 음의 stencil은 각진 분절을 늘렸다. [24](TASK24_RESULTS.md), [25](TASK25_RESULTS.md) |
| 26–28 | 전체 게이트 대칭, current section feedback, 단일 기둥 benchmark | Task27 R4는 면적 측정 오류를 교정했다. 큰·중간 조직과 늦은 세부 소실을 구분했다. STOP/R3 자료는 실패·폐기 판정과 함께 보존된다. [26](TASK26_RESULTS.md), [27](TASK27_RESULTS.md), [28](TASK28_RESULTS.md) |
| 29–31 | corrected face→edge→vertex, 지역 상태, 실제 multi-parent DS, explicit handle | coupling·state 보존은 성과다. Task31 구멍은 지정한 G2 annulus 수술이며 발생적 porosity가 아니다. [29](TASK29_RESULTS.md), [30](TASK30_RESULTS.md), [31](TASK31_RESULTS.md) |
| 32 | metric-growth surrogate, spectral hierarchy, connected multi-face grammar | 물리 shell solver가 아니며 일부 부착 장식·블록 인상이 남았다. 별도 방식 전체가 반증된 것은 아니다. [결과](TASK32_RESULTS.md), [문헌](TASK32_RESEARCH.md) |
| 33–34 | 실제 깊은 내부 골과 현재 crest에 반응하는 refolding | V01 깊이 성과와 N04 current/frozen 대조는 유지한다. 지정 chart/phase와 판·리본 반복, 추가 fine 4/33 한계가 있다. [33](TASK33_RESULTS.md), [34](TASK34_RESULTS.md) |
| 35–36 | 구간별 기둥, growth/incision 분리, 중립 carrier의 매 세대 재귀, 강화된 교차 검사 | Task35 coarse profile은 사전 설정이다. Task36 U01의 fine와 W03의 macro는 서로 다른 성과이며 모두 조형 PARTIAL이다. [35](TASK35_RESULTS.md), [36](TASK36_RESULTS.md) |

이 계보는 하나의 알고리즘이 매번 개선된 역사가 아니다. 입력 형상, 물리적 표면의 정의, 계수 스케일, 검증 기준도 함께 바뀌었다. 같은 Task 번호나 같은 최종 face 수만으로 서로 같은 조건의 비교가 성립하지 않는다.

## 3. 최신 연산에서 직접 확인한 제약

### 실제 합성 stencil은 단순한 raw weight 혼합과 다르다

Task36 최종 레시피는 `I + .65*(G-C) + .65*(N-G)`다. `I`는 VF physical split, `C`는 표준 CC, `G`는 normal 없는 weighted 위치, `N`은 normal 포함 위치다. `averaging_gain=0`은 **CC 차분을 빼는 추가 외삽**을 남긴다.

직전 V/F 대각을 쓰는 몸통 면에서 `w4=1.6`이면 normal·repair 전 face 배치는 다음과 같다.

```
P = aV*V + aF*F - .26*E1 - .26*E2
 aV = .5 + .65*((1+w3)*2.6/4 - .25)
 aF = .5 + .65*((1-w3)*2.6/4 - .25)
```

실제 U01 G7→G8의 `aV=.508223..566936`, `aF=.953064..1.011777`이다. W03도 유사하다. 저장된 `face_base + .65*stencil_component`와 수식을 재구성한 오차는 두 후보 모두 **1.82e−12 이하**다. 모든 eligible 면의 E 계수 −.26은 현재 형상을 읽어 선택한 방향이 아니라 계속 계승되는 signed 대각 구조다.

`R`을 이전 endpoint 평균, `Cbar`를 인접 이전 face centre 평균, `Fraw`를 합성 전 새 weighted face 평균이라 하면 no-normal edge 배치는 U01에서 `1.2275R+.0975Fraw−.325Cbar`, W03 몸통에서 `.8375R+.4875Fraw−.325Cbar`다. 기존 보고서의 85/15와 25/75는 **reference 내부 식**의 비중이며 합성 후 전체 배치를 충분히 설명하지 않는다.

retained vertex의 no-normal 항은 `Vout=Vold+(.52/n)*(2Rbar−Fraw_bar−Cbar)`다. 원래 위치 계수 1이 남는 반평균화이며 hard lock은 아니다. 외곽이 조상에 집중되는 현상의 구체적인 원인 후보지만, 이 식만으로 조형 실패의 단일 원인을 확정하지 않는다.

### 실제 변위·측정 공백·안전 감쇠

- G8 몸통 새 face 요청 변위의 stencil/normal 중앙값은 U01 **7.469/.333**, W03 **3.111/.256**이다. stencil이 normal보다 큰 면은 각각 **99.9878%/99.9756%**다. 법선 이동 증폭만으로 현재 지배적 운동을 개선한다고 보기 어렵다.
- 실제 VF 내부 hinge는 native에 존재하지만 `fields()`의 단일 polygon normal과 inter-quad `face_bend`에 **직접 포함되지 않는다**. 네 corner 좌표는 다음 식에 들어가므로 생성 기하 전체를 무시하는 것은 아니다.
- G7 몸통 131072개 면 중 내부 hinge >45°는 U01 26864/W03 18992개다. 그중 inter-quad angle proxy <15°는 352/624개다. 내부 접힘과 controller scalar의 불일치는 확인됐지만 전체가 보이지 않는다는 결론은 과장이다.
- incoming support 중앙값 G3/G5/G7은 U01 61.308/12.605/2.381, W03 58.693/10.927/2.020이다. 이 값은 centroid와 supporting line 거리이며 비평면 면의 정확한 내접반경이 아니다. refinement와 skinny cell의 영향을 분리해야 한다.
- G8 몸통 face에 실제 factor<1인 수는 U01 28072/W03 11024다. 모든 깊은 접힘이 안전 장치 때문에 막히지는 않는다. 안전 제한 제거의 근거가 아니며 같은 입력·같은 factor 대조가 필요하다.
- 현재 reference와 sharp attraction은 **literal SUM**을 쓴다. U01/W03는 `w6=w7=u=0`이므로 이 항은 비활성이다. SUM을 mean으로 잘못 바꿔 현재 결과가 약해졌다는 증거는 없다.
- 동일한 사각 두 셀과 대칭적인 결정론 규칙은 네 면·두 axial 절반의 동등성을 유지한다. 서로 동등한 초기 상태와 제어만으로 서로 다른 지역 정체성이 저절로 선택되지는 않는다. 동일한 직선 실루엣의 coarse tessellation을 바꾸는 대조와 스케일 보정이 필요하다.

이 절의 경량 배열 분석은 두 후보의 실제 `G{3,5,7}_FOLD/{quad_state,mesh}.npz`와 `G{4,6,8}_FOLD/operator_state.npz`를 사용했다. 세대나 normal gain만 보고 결과를 추정하지 않았다.

## 4. 새로 실행한 동일 입력 대조: U01 G2→G3

자료: [summary.json](E:/CHESHIRE_DATA/astra_research/constraint_probe/summary.json). 각 조건의 native/quad/operator NPZ, 요청 파라미터, SHA, 원본 소스 사본을 같은 폴더에 저장했다. 입력은 원래 U01 `G2_FOLD/quad_state.npz`; baseline은 기존 G3 XYZ와 정확히 일치한다.

| 조건 | XY 폭 | 몸통 내부 hinge 중앙값/p95 | >45° 면 수 /512 |
|---|---:|---:|---:|
| BASELINE_SIGNED |1499.903|18.988/63.675°|64|
| INTERP_WEIGHTED_BLEND: `averaging_gain=.65` |1415.287|16.784/56.676°|32|
| SIGNED_W4_035: `diagonal_tension=.35` |1475.915|11.758/44.455°|16|
| BLEND_W4_035: 두 변경 결합 |1391.299|11.394/32.939°|0|

모두 1282 native 정점/2560 삼각형이다. **repair·backtracking 없이** 공유 정점 쌍 포함 interval 교차0, 퇴화·캡 반전0, 캡 Z 오차0, X/Y 반사 오차≤4.55e−13이었다. 동일 `plane_only` 캡과 VF surface를 유지했다. 공면·접선·경계만 접촉은 검사 제외다.

`averaging_gain=stencil_gain=.65`이면 위치식은 `I+.65*(G-I)+normal`로 바뀐다. 이 대조는 표준 CC 성분이 만드는 차이를 명시적으로 측정한 것이며 smoothing 영향이 없다고 해석하지 않는다. 대각 tension과 합성 방식이 실제 각진 접힘에 각각 기여한다는 단일 단계 근거다. 각도 감소와 면적 감소가 좋은 깊이까지 없앨 수 있으므로 **조형 개선·전체 시퀀스 성공을 선언하지 않는다**. 다음 판단에는 같은 카메라 실제 메시와 부모 내부 깊이 유지가 필요하다.

## 5. 보류됐으나 다시 비교할 가치가 있는 방향

| 보존 기술 | 재사용할 근거 | 그대로 복사하면 놓치는 점 |
|---|---|---|
| [Task25 curl](TASK25_RESULTS.md) | 같은 입력에서 normal offset 중지 시 큰 말림 회복; 강한 w3/w4는 fragmentation 증가 | 계층 추가는 약했다. 기존 큰 조직과 crease·support를 포함한 결과이므로 zero-normal을 만능 규칙으로 만들지 않는다. |
| [Task17/30 DS](TASK17_RESULTS.md)·[혼합 경로](TASK30_RESULTS.md) | face/edge/vertex 기원별 inset/frame 구성이 CC와 다름 | DS 뒤 CC Eq4는 class 자격이 없어 fallback한다. 같은 세대 번호끼리 point-class 성과를 비교하면 안 된다. |
| [Task23 cross-cell crease](CROSS_CELL_CREASE_STUDY.md) | 실제 descendant edge로 연결을 계승함 | 선 연결·sharpness는 깊이·음영·입체 연결의 대체 지표가 아니다. |
| [Task31 지역 상태](TASK31_RESULTS.md) | 실제 signed geometry와 multi-parent memory로 지역 차이를 만들었음 | tertile은 물리적 곡률 기준이 아니며 incident mean이 지역 경계 contrast를 낮춘다. persistent 우월성도 모든 descriptor에서 입증되지 않았다. |
| [Task32 connected patch](TASK32_RESULTS.md) | 여러 셀을 하나의 연산 범위로 다뤄 단일 셀 scaffold를 벗어날 수 있음 | 당시 block/부착 인상과 검증 실패가 있다. 전체 방법의 성공도 불가능도 아직 확정하지 않는다. |
| [Task33–35 feature-scale 골](TASK35_RESULTS.md) | 부모 crest의 폭·prominence와 실제 chord를 써 깊은 내부 골을 만들었음 | fixed material chart·radial 방향·입력 profile을 포함한다. 자유로운 3D 재귀의 증명으로 이식하지 않는다. |

가장 작은 다음 대조는 **합성 stencil·실제 native hinge 인식·초기 tessellation**을 각각 분리하는 것이다. 이 중 하나의 개선이 다른 항을 대체한다고 미리 정하지 않는다.

## 6. 공개 논문과 현재 geometry field의 경계

이번 감사에서는 보존된 원논문 [Subdivision Beyond Smoothness, 2010 PDF](<E:/CHESHIRE_DATA/research_archive/references/pdfs/075-081 (1).pdf>)와 [추출 원문 R1](E:/CHESHIRE_DATA/research_archive/references/cached_text/R1.txt)을 직접 대조했다. 외부 구현을 새로 반입하지 않았다. 전체 출처·라이선스 접근 이력은 [참고문헌](astra/REFERENCES.md)을 따른다.

- p.76의 Eq1–4는 새 face를 완료한 뒤 edge에 전달하는 구조와 face/edge/vertex normal offset을 설명한다. 현재 reference의 coupling은 이에 기반하며 legacy의 input-centroid 방식과 구별된다.
- 같은 페이지는 face normal의 perimeter scale을 가능한 선택으로 설명하고 edge normal을 인접 normal의 평균으로 정의한다. Task36의 minimum support, tanh bend, VF 물리 표면, cap 정책, CC 차분 합성, 국소 충돌 repair는 **CHESHIRE의 선택**이다. perimeter가 논문의 언급이라고 현재 support를 곧바로 버릴 근거도 없다.
- p.77–78의 nonstationary/nonuniform weight, 환경 weight set, topology/motif, tagging·locking은 서로 다른 제어 수단이다. 현재 `NORMAL_VARIATION`, `PLANARITY`, local scale, signed neighbour displacement가 그 전체를 재현한다고 주장하지 않는다. 현재 planarity는 네 번째 점과 첫 세 점 평면의 거리 proxy이며 arbitrary polygon/physical hinge 곡률이 아니다.
- Eq10/11은 literal attraction 합이다. Task36에서 이 항이 꺼진 것은 명시된 연구 선택이다. 같은 전역 상수를 다시 켠다고 새 topology motif가 생기는 것은 아니다.
- p.77은 위치가 겹치는 정점을 합치거나 거리 조건으로 합치는 선택, 그리고 valence 제한에 따른 porosity를 설명한다. 이 설명은 **현재 topology-preserving refinement만으로 genus가 바뀐다는 뜻이 아니며**, watertight·무교차 solid를 보장하는 완전한 수술 규약도 제공하지 않는다.

## 7. 발생적 genus 변경을 연구하기 전에 빠진 최소 조건

현재 Task36 CC refinement와 좌표 변형은 연결 그래프의 위상형을 유지한다. 퇴화·자기교차를 만들었다고 유효한 손잡이나 구멍이 생성된 것은 아니다. Task31 `coarse_edit()`는 G2에서 ±Y 방향 quad mouth를 선택하고 지정 ratio의 annulus를 연결한다. Euler 변화와 parent는 기록하지만, **고정 위치 구멍이 아닌 발생 규칙**의 완료 증거가 아니다.

새로운 거대 프레임워크보다 아래 작은 조건을 먼저 충족해야 한다.

1. **기하 사건 정의:** 실제로 접근한 비인접 surface patch와 향하는 방향·간격·국소 두께를 읽어 사건을 제안해야 한다. 특정 높이나 ID에 decorative hole을 배치하는 규칙과 구별한다. 현재 checker는 교차 판정 도구이며 near-contact/clearance·공면 접촉·안팎의 완전한 판정을 제공하지 않는다.
2. **유효한 국소 replacement:** 단순 정점 welding은 pinch/nonmanifold를 만들 수 있다. 두 disk 경계의 방향·서로 분리됨·연결 가능성, edge incidence=2, vertex link가 단일 cycle인지 검사하고, 제거/추가 면과 전후 Euler·component를 기록해야 한다. topology가 맞아도 삼각 embedding이 교차하면 거절한다.
3. **현재 형상을 읽는 선택과 대조:** 사건 임계값을 넘지 않는 동일 입력, 임계값 바로 전후, 이미 교차한 invalid 입력을 소형 fixture에서 나눠 본다. 한 번 실제 사건이 일어난 뒤 후속 refinement가 새 연결부를 읽는지 확인해야 한다. 실패를 smoothing이나 숨은 repair로 통과시키지 않는다.
4. **대칭·경쟁 사건 처리:** 하나의 사건과 X/Y 반사 사건을 함께 계획하고, overlap하는 편집의 순서·중복·거절을 결정론적으로 기록한다. Task31의 한 쌍 mouth는 당시 비대칭이며 그대로 현재 대칭 요구를 만족하지 않는다.
5. **표면·계보의 재시작 계약:** 실제 물리 삼각 표면, 새 extraordinary valence, signed 위치와 positive parent를 구분해 저장한다. 기존 V/F class 자격이 깨진 곳은 fallback/재분류를 명시해야 한다. 성공한 genus 수만 보고 연속 접힘·개구부 가시성·제작 가능성을 함께 성공 처리하지 않는다.

최소한의 독립 시험은 하나의 coarse contact event를 원인에 따라 제안하고, 유효 topology/embedding 및 다음 한 세대를 보존하는 수준이다. 아직 일반 자동 porosity·충돌 기반 수술·solid Boolean의 구현이나 성공을 주장하지 않는다. 이러한 사건이 최종 목표에 실제로 필요한지도 접힘만의 대조와 함께 판단할 문제다.
