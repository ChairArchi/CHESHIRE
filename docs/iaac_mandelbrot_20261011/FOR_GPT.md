# CHESHIRE — IAAC / Mandelbulb 시험 검토 인계

**독립적인 기둥 형상 시험을 검토해 주세요.** 기존 KNOT/TORQUE 게이트 개발은 보존되어 있고, 이번 시험에는 사용자 지시로 아치·개구부 조건을 적용하지 않았습니다. Issue #1의 과거 게이트 조건과 구분해 주세요. 자동 예약이나 후속 실행을 등록하는 요청은 아닙니다.

**유망한 조형 기준:** `input_field/DIRECTIONAL_FIELD/G02_CC`. 사용자는 아래 형상을 긍정적으로 평가했고, 마디 사이의 침범과 더 설득력 있는 접힘 방식이 중요하다고 지적했습니다. 최종안 채택은 아닙니다.

![유망 기준 — 실제 메시의 정면·사선·측면](images/preferred_three_views.png)

## 확인된 사실과 미확인 부분

- 현재 D 계열 입력은 **단면 폭·깊이와 축방향 좌표를 직접 변형한 매스**입니다. 접힘선을 기준으로 양쪽 면의 꺾임·굽힘을 함께 계산하는 folding 알고리즘은 구현하지 않았습니다. ‘접힘 입력’이라는 이름을 실제 origami 구현의 증거로 해석하지 마세요.
- 실제 경로는 방향별로 어긋난 팽창/축방향 되돌림 → bilinear 분할 → 유한 Mandelbulb 영역 내부 정점의 외부 격자점 방향 이동 → 별도 CC 표시 메시입니다. 원본 IAAC 코드의 복구가 아닙니다. 공개되지 않은 수식·수치·입력은 재구성한 가정입니다.
- IAAC 기준 형상은 공개 `pres125`의 **LOOP 1 + Catmull–Clark**입니다. 공개 G0 입력이라고 단정할 수 없습니다. 입력과 필드를 별도로 준비했다는 가설은 미확정입니다.
- CC의 실제 좌표 평균화와 별도 기하학적 smoothing을 구분합니다. 별도 smoothing은 적용하지 않았지만 CC는 좌표를 바꿉니다. 렌더에는 저장된 실제 메시와 동일 재질만 사용했습니다.
- 유망 기준은 좌우 대칭 오차 0, 단일 폐합 연결체이지만 **자기교차가 확인됐습니다.** 제작 가능성·두께·구조는 미검증입니다. 마디의 형태적 침범과 실제 면 교차를 동일시하지 마세요.
- 곡선 접힘/origami 공개 구현은 문서와 일부 코드를 검토한 상태입니다. 설치·실행·통합하지 않았습니다.

## 검토 순서

1. [짧은 결과 보고서](REPORT.md), [공개 자료와 재구성 범위](SOURCES.md)
2. 동일 토폴로지의 입력 × 필드 OFF/ON: [정면](images/input_field_front.png) · [사선](images/input_field_oblique.png) · [측면](images/input_field_side.png)
3. [필드 G1 → G2 → 별도 CC](images/input_field_stages.png), [직접 모델링 입력 → CC1 → CC2](images/D02_INTERLEAVED_stages.png)
4. 후속 매스 변형 D02/D04/D05: [정면](images/fold_modes_geometry_front.png) · [사선](images/fold_modes_geometry_oblique.png) · [측면](images/fold_modes_geometry_side.png)
5. 같은 필드 적용: [정면](images/fold_modes_field_front.png) · [사선](images/fold_modes_field_oblique.png) · [측면](images/fold_modes_field_side.png)
6. [이전 균등 네 방향 주름과의 차이](images/fold_logic_oblique.png), 필요할 때만 [36개 레시피 정면 목록](images/catalogue_front.png)
7. [핵심 검사 기록](technical/validation_summary.json), [실패 기록](technical/failed_trials.json), [공개 파일 목록](MANIFEST.json)

## 판단받고 싶은 질문

1. 현재 유망 기준에서 유지할 큰 형태와 마디 간 관계는 무엇이며, ‘쿠션 같은 팽창’과 면이 돌아드는 접힘의 차이는 어디에서 생기나요?
2. 입력 매스와 Mandelbulb 장을 분리한 비교가 무엇을 입증하고, 무엇까지는 입증하지 못하나요? 이미지의 복잡성을 알고리즘 성공으로 대체하지 말아 주세요.
3. 큰 흐름을 보존하며 **접힘선과 주변 면이 함께 변하는 방식**을 시험하려면 어떤 접근이 적절한가요? curved-crease 또는 공개 origami 구현을 근거와 함께 검토해 주세요. IAAC가 origami를 사용했다고 가정하지 마세요.
4. 다음 실제 시험은 최대 두 가지로 제안해 주세요. 범용 엔진 확장이나 무제한 필드 수치 탐색보다, 현재 부족한 접힘 관계를 확인할 수 있는 비교를 우선해 주세요.

## 데이터와 검토 범위

**공개 패키지는 렌더·문서·검사 기록입니다. 원본 메시·체크포인트·BLEND·필드 격자는 업로드하지 않았으며 로컬에 보존했습니다.** 이미지에서 판단한 것과 제출된 검사 기록을 확인한 것을 구분해 주세요. 로컬 경로는 공개 다운로드 링크가 아닙니다.

소스는 같은 브랜치의 [`experiments/iaac_mandelbrot_20261011`](../../experiments/iaac_mandelbrot_20261011)입니다. 관련 CHESHIRE 모듈은 `src/cheshire`에 있습니다. 코드의 실행 파일·출력 경로는 로컬 환경용입니다.

실패한 D03은 전체 각도 항을 함께 바꾼 재매개화에 그쳐 실제 접힘 경로 이동으로 인정하지 않았습니다. D04는 되돌림 강화와 함께 자기교차가 생겼습니다. 둘 다 성공으로 포장하지 않습니다.

검토를 Issue #1에 남길 경우 이 독립 시험임을 명시해 주세요. 기존 게이트 후보의 폐기나 최종 미적 선택을 의미하지 않습니다.
