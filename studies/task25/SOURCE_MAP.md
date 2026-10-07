# Task25 중앙 상인방의 생성 경로

기준은 Task24 `385ec86c1f18ee1e2e0d61e2b32c524ceccfb683`의 실제 H1
73,114 vertices / 73,112 faces다. 사용자 원본 두 이미지는 새 시각 증거로
보존했다. 이미지의 네 갈래 조직과 실제 H1의 중앙부는 대응하지만, 이미지
파일만으로 사용자가 연 정확한 파일 해시나 Rhino 카메라를 인증하지 않는다.

## 위치와 추적 기준

원래 좌표, Z-up, 전면 -Y를 유지했다. C0는 Task15 계열의 5-cell U형 carrier
24 vertices / 22 faces다. W/H/D=4000/3500/500, opening=2200/2600,
origin=(-400.036865234375,-18.533447265625,0). 이는 보존된 계열의 기준이며,
새 ALICE 원본의 물리 단위나 원본 mesh ID를 복구한 것은 아니다. 단위는
미확정이고 3DM도 None이다.

중앙부 추적 규칙: 실제 face centroid의 `abs(x+400)<700`,
`1600<z<3000`, y 전체. `analysis/ancestry_map.json`에 각 체크포인트의
**실제 face IDs**, C0 양의 조상 연관, event IDs, geometry/lineage 파일
SHA256을 저장했다. 이 영역은 앞·뒤·아랫면을 포함하는 진단 영역이며,
스크린샷을 그대로 선택 규칙으로 사용하지 않았다.

C0 face 14는 전면 상인방, 15는 뒷면, 16은 아랫면이다. 실제 face 16 cycle은
`[7,6,10,9]`, centroid=(-400.036865234375,-18.533447265625,2600),
normal=(0,0,-1)이다. Face 14 centroid y=-268.533447265625, normal=(0,-1,0),
face 15 centroid y=231.466552734375, normal=(0,1,0)이다.

## 보존된 단계에서 보이는 변화

| 실제 저장 단계 | 중앙부 증거 | 해석 |
|---|---|---|
| BACKBONE_S01–S02 | 낮은 해상도의 쌍을 이루는 V형 배치 | 두 modified CC가 큰 조직을 준비한다. 완성된 네 말림으로 단정하지 않는다. |
| BACKBONE_S03 | 위·아래의 각진 조직이 분명해짐 | 선택된 전·후면의 TaperedExtrusion이 기여한다. |
| BACKBONE_S04 | 네 갈래 둥근 조직이 더 명확해짐 | Taper 뒤 standard CC가 형태를 연결한다. |
| C07 = BACKBONE_S05 | 위·아래 크기가 다른 네 갈래 관계가 이미 존재 | 두 Mola event와 세 CC를 거친 입력이다. |
| H1 S01 | 중심과 주변의 각진 능선·층이 강화됨 | macro Fold: band 10, wf=-280, we=320, wp=520, w1=.8, w2=-2.8, w6=-.9, w7=.8. |
| H1 S02 | 주변 Roof 추가 | 중심 네 말림의 최초 생성 단계가 아니다. |
| H1 S03 | 안쪽 굴곡이 더 둥글고 반복적으로 읽힘 | cleft Fold: band 5, wf=we=wp=130, w1=-.35, w2=-.65. |
| H1 S04–S07 | 중심 조직의 주요 관계가 지속됨 | 이후 Frame→Taper→Frame→Taper가 네 말림의 주된 발생원이라는 증거는 없다. |

S02 진단 영역 24 faces의 C0 연관은 14/15/16에 각각 6/6/12,
S03 72 faces는 22/22/28, S04 276 faces는 82/82/112,
C07 476 faces는 150/150/176이다. S03 이후 영역에는 event_1의 실제
부모들(334,335,336,338,339,340 등)이 함께 나타난다. 따라서 이 조직을
Mola와 무관한 CC 단독 결과로 주장하지 않는다. 양의 face 조상은 시공상의
연관 기록이며, 음의 가중치와 전체 이웃의 **완전한 기하 영향계수**가 아니다.

초기 backbone의 정확한 선언은 보존된 `task24/inputs/backbone.json`이다.
실행된 것은 처음 다섯 단계다. 나중에 나열된 nested_articulation/event_3를
실행된 것으로 세지 않는다. 처음 두 CC의 wf/we/wp **비율**은 실행 시
전체 current mean edge length와 곱해지고, w1/w2/w3/w4는 무차원이다.
첫 CC: (.3,-.08,.1,-1,-.7,0,0), 두 번째:
(.16,-.05,.045,-1.05,-.9,-.8,.5), 순서는 wf/we/wp/w1/w2/w3/w4.
Taper height_ratio=.26, fraction=.3; standard CC; event_1 cap의
InsetFrame width_ratio=.08이 이어진다.

## Task25에서 직접 확인한 통합 문제

H1 말단의 네 기존 네트워크는 Mola에서 살아남은 원래 edge 조각만 추적한다.
모든 새 장식 edge에 ridge/valley 의미가 이어지는 기능은 없다. 중앙 진단
영역 3,247 faces 중 band 8에서 기존 support가 닿는 것은 115 faces였다.
실제 첫 FLOW 실험도 중앙은 대조군과 거의 같고 mantle에서 변화가 컸다.

기존 N6 router로 실제 현재 전체 메시와 C0/face history를 따라
`lintel_convergence_support`를 만들었다. 중심 normalized xz=(0,.71),
상부 targets=(±.13,.82), 하부=(±.1,.63), target_y_ratio=-1.1이다.
네 팔을 동일한 shape로 복제하거나 사후 mirror하지 않았다. 라우팅의 실제
ordered paths, junctions, root edges, parent cells와 C0 연관은 각 시도의
`new_support_route.json` 및 continuation state에 있다. 첫 CONVERGENCE_G1의
실제 routing seed는 **22183**이고, rounded CONTROL_G1에서 새로 찾은
권장 G2의 seed는 **77308**이다. 후자는 CONTROL_G1에서
(-400.03685893864747,-538.5083922277673,2603.095368325734)이며,
경로 중간의 공유 분기 212/948/77311도 실제 graph의 junction으로 보존한다.
같은 C0 guide라도 현재 geometry와 eligible valence가 달라지면 seed가 달라진다.
정렬된 junction 목록의 첫 ID를 routing seed와 혼동하지 않는다.

이 새 경로의 sharpness는 **0**이다. 접힘 배치의 support를 지정하고 기존
mantle crease 제약은 별도로 유지한다. 새 edge를 모두 sharp 처리하거나
일반 Mola 의미 계승을 구현한 것은 아니다. `folding_support.json`과 실제
새 메시 overlay에 다음 세대의 경로와 활성 point 수를 기록한다.
Overlay에서 중앙에서 상부와 양쪽 말림 주변으로 이어지는 경로를 확인할 수 있다.
각 내부 홈 전체를 ridge/valley로 직접 추적한 것은 아니며, placement band가
그 실제 graph 이웃에 작용한다.

## 카메라와 증거의 한계

Ancestry detail은 orthographic azimuth=0, elevation=-12,
target=(-400,0,2450), frame width=1800; 두 번째 각도는 18/-25, 같은 target과
width다. 아랫면은 0/-30, width=2200. 모델마다 독립 fitting하지 않았다.
메시 전체를 유지한 고정 crop이며 변환은 디스플레이 회전뿐이다.

`backbone_detail.png`, `ancestry_detail.png`, `ancestry_underside.png`는
기존 System.Drawing painter의 **폴리곤 프리뷰**다. 교차 가림이 근사적이며
Rhino 캡처·clay render·AO가 아니다. 어두운 중심을 관통구멍으로 판정하지
않는다. Native 파일의 mesh-plane 단면은 실제 깊이의 별도 선형 증거다.
