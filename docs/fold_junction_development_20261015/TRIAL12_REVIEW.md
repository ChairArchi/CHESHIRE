# 전체 소주름 교체 테스트 결과 — 2026-10-15

**상태: 요청한 비교 테스트 완료, 최종안 미채택.** 사용자 평가: “오히려 더 이상해졌는데. 가능성은 보이네. 지금 형상은 … 잘 만든거 그냥 덮어버린 느낌이 강하네.”

## 실제 결과

실험은 `E:/CHESHIRE_DATA/experiments/fold_junction_development_20261015/trial12c_all_small_mandel_replacement/`다. 같은 카메라·조명·재질·900px·flat shading의 CONTROL/FIELD 근접·몸체·전면 6개 PNG 및 PAIR_RECEIPT를 생성했다. 새 형상은 실제 원본과 같은 14,004,226 native 정점 / 28,008,448 삼각형이다. 전체/디테일 PLY는 정확한 reconstructed float64 좌표와 원래 연결을 기록하고 전체 roundtrip 검증을 통과했다.

내보내기: `E:/CHESHIRE_DATA/exports/20261015/COLUMN_SMALL_MANDELBULB_TEST/`

- `comparison.html`: 3개 화면의 오프라인 원본/시험본 slider.
- `CHESHIRE_PARENT_PROBE_FIELD_FULL.ply`: 전체 시험본, 700,211,636 bytes.
- `CHESHIRE_PARENT_PROBE_FIELD_DETAIL.ply`: 실제 native 삼각형의 근접 부분집합, 4,257,695 bytes. 절단 경계는 열린 상태이며 cap을 만들지 않았다.
- `MANIFEST.json`: `research_probe` 상태, 코드·입력·PNG·좌표·연결·PLY 왕복 검증.

원본 NESTED02와 기존 export는 그대로다. 이번 시험본을 기준 모델로 승격하지 않는다.

## 눈에 보이는 판정

작은 형상의 밀도·말림·입체감은 강하게 바뀌었다. 전체 기둥의 큰 윤곽은 알아볼 수 있지만, 근접과 몸체에는 가로로 반복되는 띠·층과 비늘 같은 덩어리가 앞선다. 원래의 긴 S 흐름을 읽는 데 방해가 된다. 사용자 말대로 기존에 잘 만든 형상 위에 독립된 형상을 덮은 인상이 강하다.

이 결과는 Mandelbulb의 세부 형상 성향을 강하게 표현할 가능성을 보여준다. 그러나 기존 능선·골·뿌리의 흐름에 종속된 새 접힘을 얻은 것은 아니다. world-space 각도 매핑의 방향 질서가 기존 부모 질서와 독립되어 있다는 점이 화면의 반복 띠와 부합한다. 이를 유일한 원인으로 분리 검증한 것은 아니며, 낮은 단계의 형상 분리와 중립 CC의 영향도 포함된다.

## 구현과 범위

명목상 물리 경계 0.30(높이 약3%)의 전체 역할 intrinsic 저역통과 곡면에서 시작하여 기존 후반 디테일을 제외한다. 실제 G3 전체 27,354개 제어점의 필터 결과를 같은 ancestry CC 네 번으로 G7까지 올렸다. 이 처리의 크기 경계는 완만하며, 의미론적 주름을 전수 분류하거나 큰 능선·실루엣을 정확히 고정하지 않는다. 실제 G4에서 필터링하는 계산과도 동일하지 않은 더 거친 근사다.

새 기하는 finite power8/orbit8 Mandelbulb의 구면 방향별 sampled outer radial boundary에서 얻었다. 전체 곡면에 연속 각도 매핑을 적용하고 법선 진폭0.035 및 같은 boundary 기울기의 작은 접선 이동을 사용했다. 전체 volumetric Mandelbulb topology·분기·관통공이나 IAAC의 원본 loop를 재현한 것으로 부르지 않는다.

두 차례 G4 선형 계산은 모델·렌더 생성 전에 런타임 병목으로 종료·보존했다. `trial12`와 `trial12b`에는 RUNTIME_RESTART 기록이 있으며, 실제 출력은 `trial12c` 한 안이다. 최종 계산은 필터6.18초, 전체 생성·검증75.41초였다. G4 비용 예상은 실제보다 과소평가했고, 앞으로 같은 규모에서 해당 직접 분해를 반복하지 않는다.

## 다음 작업에서 지킬 것

사용자는 시험본의 가능성을 인정했으나 코팅처럼 가리는 인상을 지적했다. 이 말은 기존 큰 흐름을 버리거나 이번 전면 mapping을 최종안으로 채택하라는 뜻이 아니다. 작은 기하의 형상 성향과 기존 능선·골의 방향·접속 관계를 함께 설계해야 한다. 새 실행은 아직 지시되지 않았다. 이전의 약한 local FIELD·ruled carrier·무작위 강도 조정을 성공한 해법으로 되돌리지 않는다.

G8은 여전히 실제 실행하지 않았다. G7 원본의 65,536개 edge instance 표본에서 주요0.15 lobe 간격당 약37개 median edge가 있다. 이는 주요 형상 밀도의 근거이며, 더 작은 fractal harmonics나 모든 위치의 해상도를 보증하지 않는다. G8이 효과 없다는 인과 실험을 수행한 적도 없다. 관련 수치와 실제 범위는 WHOLE_SMALL_REPLACEMENT_TEST.md에 있다.
