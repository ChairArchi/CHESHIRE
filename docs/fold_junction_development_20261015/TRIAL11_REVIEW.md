# trial11_parent_mandel_probe — 미채택

2026-10-15. 실제 NESTED02 G7을 기준 곡면으로 사용한 하나의 실제 부모(family4, G0_LEGACY_TIER3_DIAGONAL_SHOULDER) 비교이다. CONTROL은 원래 곡면이며 FIELD는 동일 topology에 부모 국소 finite 3D Mandelbulb 반응을 적용한다. 조형 위치는 원래 생성 계보와 실제 SOURCE 면의 측정에서 정하며, 카메라에 형상을 그리지 않았다.

결과: 큰 S 흐름은 trial10보다 유지되었지만, 근접의 상부 중앙·우측 반응이 잔돌기와 거친 껍질로 읽힌다. 독립된 아름다운 중간 접힘을 얻지 못했다. 사용자도 지저분해졌다고 판단했다. **미채택이며 전체 적용·PLY 내보내기를 하지 않는다.**

증빙은 `E:/CHESHIRE_DATA/experiments/fold_junction_development_20261015/trial11_parent_mandel_probe/`의 PROBE_RECEIPT.json, PAIR_RECEIPT.json 및 CONTROL_FLAT/review, FIELD_FLAT/review에 보존했다. 원래 native 삼각형을 한 번 로드하고 좌표만 바꾸어 두 형상을 동일한 카메라·조명·재질·flat shading으로 렌더했다. 해상도는 900px이며 좌표·연결·원본·코드 snapshot 검증을 포함한다.

실제 63,135개 canonical query 중 17,017개가 finite-inside였고, 15,448개가 유효하게 이동했다. 최대 물리 변위는 0.032018이다. 변경된 276,240개 fan 삼각형 중 12,736개(4.61%)는 원래 삼각형의 법선과 내적이 음수였다. 이는 국소 면 방향이 크게 바뀐다는 경고이며, 전역 self-intersection 검사나 winding 불일치 확정과 같지 않다. 국소 T 이동은 수치적으로 0이지만 이 사실도 아름다운 큰 흐름의 보존을 증명하지 않는다.

부모 규모에서 벡터 반응을 정리하는 수정이 논의되었으나, 사용자의 기준 정립 지시에 따라 다음 생성·렌더를 중단했다. trial12는 생성하지 않았다. 다음 작업은 [조형 기준](BEAUTY_CRITERIA.md)에 따른다.
