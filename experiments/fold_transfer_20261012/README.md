# Fold transfer study — 2026-10-12

서로 다른 실제 초기 매스 **SPAN / COUNTER**에 같은 작은 return·field·보호 규칙을 적용한 제한적인 기둥 비교다. 두 G0는 동일한 25-ring / 16-sector carrier의 **402 controls / 400 quads**와 material chart를 사용한다. 현재 확인 범위는 이 두 입력이며, 임의 메시나 다른 topology에서도 작동한다는 주장은 하지 않는다.

SPAN G0는 보존된 `SPAN_SPARSE/G00`의 실제 좌표를 읽고 원래 carrier의 rest/classes/anchors를 복원했다. COUNTER G0는 기존 `seed_mass.evaluate(chart, RECIPES['COUNTER'])`를 같은 초기 chart에서 직접 평가했다. 최종 G3를 변형한 후 다른 초기 입력으로 부른 것이 아니다. 원본 초기 매스와 이전 후보는 보존한다.

`study.py`는 기존 Task36 growth와 inactive VF 재분할, `smooth_deep.smooth_event`의 radial/axial PCHIP return, 유한 Mandelbulb nearest-outside field를 재사용한다. 추가 파일 `memory.py`는 선택한 material-profile 특징과 inherited controls의 보호를 다룬다. 실제 origami solver나 IAAC의 공개되지 않은 원본 방정식 구현 완료로 설명하지 않는다.

```powershell
cd C:/Users/USER/CHESHIRE/worktrees/curved-fold-side-20261011
C:/Users/USER/CHESHIRE/.venv/Scripts/python.exe -B experiments/fold_transfer_20261012/inputs.py --root E:/CHESHIRE_DATA/fold_transfer_20261012
C:/Users/USER/CHESHIRE/.venv/Scripts/python.exe -B experiments/fold_transfer_20261012/study.py --help
C:/Users/USER/CHESHIRE/.venv/Scripts/python.exe -B experiments/fold_transfer_20261012/boards.py
```

큰 메시·checkpoint·실제 렌더는 `E:/CHESHIRE_DATA/fold_transfer_20261012`에 있다. SPAN G3는 기존 `E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G03`을 재사용한다. COUNTER G3는 새 root의 `COUNTER/G03`; 최종 비교의 COUNTER G4는 **`COUNTER_MATCHED/{RETURN_ONLY,UNPROTECTED,PROTECTED}/G04`**를 사용한다. 이전 `COUNTER/.../G04` 진단 결과는 보존하되 matched 보드에 섞지 않는다.

다른 G0를 받는 인터페이스는 `--input <G0폴더> --name <새이름> --root <새출력폴더> --stage 4`다. 동일한 chart·위상·classes·rest를 요구하며 임의 메시를 자동 변환하지 않는다. Height10 기준 필드 배치와 모델 단위 계수가 남아 있어 전체 스케일 독립성은 입증되지 않았다. 세 번째 입력으로 이 인터페이스를 실행한 결과는 없다. 기존 출력 덮어쓰기는 거부한다.

보드는 실제 `preview/{front,oblique,side}.png`를 전체 형상 그대로 축소·배치한다. 출력은 `docs/fold_transfer_20261012/images`의 `transfer_progression.png`, `selected_views.png`, `field_comparison.png`다. SPAN 확대 비교는 동일 카메라의 `detail/front_meso.png`와 `side_meso.png`(z2.8 / z5.0, span4)를 사용한다. 다음 명령으로 `detail_comparison.png`만 만든다.

```powershell
C:/Users/USER/CHESHIRE/.venv/Scripts/python.exe -B experiments/fold_transfer_20261012/boards.py --boards detail
```

G4 검토 직후에는 G5를 권하지 않았다. 이후 사용자의 가설에 따라 `g5_probe.py`로 **RETURN_ONLY G4 두 입력에서 동일한 G5 규칙을 한 차례 실행**했다. SPAN에는 변형 없는 재분할 대조군을 추가했고, 두 입력 모두 필드 전 RETURN_ONLY / 필드 후 PROTECTED 상태를 저장했다. 필드 횟수는 부모의 실제 기록을 이어받아 3→4이며 subdivision generation5와 구분한다. `g5_boards.py`, `g5_review.py`와 docs의 `G5_REPORT.md` / `G5_INDEX.json`이 후속 기록이다. 저장된 결과의 덮어쓰기는 거부한다.

근접 질서 대조는 `stencil_probe.py`다. 같은 두 G4 RETURN_ONLY에서 Task36의 기존 ancestry stencil만 활성화하고 normal gain은 0으로 둔다. 기존 event 주변 broad activation과 carried tag 보호를 적용하며 신규 return·형상장·smoothing은 없다. `stencil_boards.py --boards detail fronts`는 저장된 실제 렌더를 비교한다. STENCIL 자체의 시각적 변화는 약했으며 자기교차는 미검증이다. 실행을 반복해 기존 폴더를 덮어쓰지 않는다.

`pin_probe.py`는 PROTECTED G5에 저장된 필드 전 좌표·raw 변위·태그를 그대로 재사용해, 일반 이전 control의 고정만 해제한 TAG_ONLY를 생성한다. 추가 field/subdivision/return은 없다. 보호 태그 core는 고정하고 새 점의 적용 변위도 동일하게 유지한다. `pin_boards.py`는 실제 확대와 두 입력 3뷰를 배치한다. TAG_ONLY는 잔조직 혼잡을 줄였지만 새로운 접힘 위계 확보는 미해결이다. `g5_review.py --validate-tag-only`는 이 두 신규 후보만 핵심 검사하며 기존 PROTECTED 검사를 반복하지 않는다. 저장된 큰 파일은 `{SPAN,COUNTER}_G5_TAG_ONLY/G05`; 모든 원본·대조군은 보존한다.

큰 접힘 보존 수치와 조형적 성공은 구분한다. PROTECTED의 더 많은 잔조직이 중간 규모 위계 개선을 뜻하지 않으며, 원래 G3와 RETURN_ONLY도 비교 기준으로 남긴다. 자기교차 등 최종 핵심 검증과 조형적 판단은 별도 보고서·validation 기록을 따른다. 두께·구조·제작 가능성은 검증하지 않았다.
