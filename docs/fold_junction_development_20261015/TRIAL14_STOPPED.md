# trial14 — 엄격한 수치 대칭 검사 후 중단, 조형 판정 없음

경로: `E:/CHESHIRE_DATA/experiments/fold_junction_development_20261015/trial14_literal_mandel_boundary`.

실제 G6→G7 finite Mandelbulb 경계 target 생성은 target 및 compact stage evidence를 저장한 뒤 `symmetry_correction > 2e-12` 검사에서 멈췄다. **FORMED native 모델과 최종 RECEIPT는 생성되지 않았고 렌더도 없었다.** 따라서 조형 실패나 미적 미채택 결과로 기록하지 않는다.

저장된 compact completed F/E/V 배열과 동일 입력 중립 G7 좌표, 실제 X/Y mirror ID로 당시 출력 좌표를 읽기 전용 재구성했다. 양 축 모두 최대 paired norm 오차는 `1.9936413141116816e-9`, 최대 좌표 성분 오차는 `1.3298464551780853e-9`였다. p99는 `1.8209011484034673e-15`, p99.9는 `1.0604123640246303e-13`이고 `1e-8` 초과 점은 없었다. 이는 가시적 비대칭을 뜻하는 크기가 아니다. projector 반복의 수치 증폭이라는 해석은 가능하지만 원인을 독립 실험으로 분리하지 않았다.

재구성은 compact evidence가 생략한 `1e-12` 이하 변위를 포함하지 않으므로 그 수준의 오차 한계가 있다. stage NPZ의 확인된 SHA-256은 `3b6dcc169b7af21fd840b9202b0b5f6bee60e1cefa7b996a0b58af0bfd9abc90`이다. 원래 frozen run/operator/target 파일은 변경하지 않았다.

이후 사용자가 **전체가 아닌 G7의 작은 디테일만 교체**하도록 방향을 바꿨다. 이에 trial14 경로를 중단했으며, 대칭 허용치를 바꾸거나 rescue generation을 실행하지 않았다. 저장된 부분 증거만 보존한다. 다음 범위는 [G7_DETAIL_REPLACEMENT_SCOPE.md](G7_DETAIL_REPLACEMENT_SCOPE.md)에 기록했다.
