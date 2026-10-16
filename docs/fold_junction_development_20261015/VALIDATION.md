# 최종 후보 기술 검증 — 2026-10-15

대상은 `E:\CHESHIRE_DATA\experiments\fold_junction_development_20261015\trial04_branch_final`의 실제 **G7 전체 모델**이다. **사용자는 trial04의 눈에 보이는 변화가 부족하다고 판정했으며 이 후보는 채택하지 않는다.** 이 문서는 미채택 과거 후보의 생성 receipt와 기술 증빙만 보존한다. 현재 작업 방향은 원래 NESTED02의 큰 형상을 유지하면서 명확히 보이는 능선·골 디테일을 만드는 것으로 변경되었다. 기술 검증 통과를 조형 개선이나 NESTED02 교체로 해석하지 않는다.

## 실제 생성과 확인 범위

| 항목 | 실제 결과 |
| --- | --- |
| G7 control | 7,002,114 정점 / 7,002,112 quads |
| Native quad-centre fan | 14,004,226 정점 / 28,008,448 삼각형 |
| 실제 X/Y 반사 대응의 최대 좌표 오차 | 3.3084646133829665e-14 |
| Native 좌표·삼각형 면적 유한성 | 통과 |
| 퇴화 삼각형 | 0 |
| 최소 native 삼각형 면적 | 5.919404254391246e-10 |
| 원래 NESTED02 대비 최종 정점 변위 norm 최대 | 0.15633726699683498 |
| 추가 subdivision / G8 / 새 topology event | 0 / 없음 / 0 |
| 생성 시간 | 108.5806초 |

현재 G7의 실제 좌표를 기준으로 새 변위만 G4→G7의 보존된 V/E/F 계보로 운반했다. 원본 XYZ 전체를 subdivision하거나 평활화하여 대체하지 않았다. 원본의 미세 좌표 잔차와 faces/classes/rest/anchors/chart를 유지하며 좌표에는 최종 변위를 더한다. Native는 같은 quad-centre fan 규칙으로 저장했다. 닫힘·면 연결의 신규 전역 재검사, 전역 자기교차 및 제작 적합성 검사는 이번 확인 범위에 없다.

## 세 가지 새 변위의 실제 크기

| 연산 | 입력→출력 계보 | 설정과 실제 최대 |
| --- | --- | --- |
| 부분 축 재접속 | 성숙한 G7의 G4 old-ID 표본 | strength **0.35**, G4 Z 변위 최대 **0.15895779254047004** |
| 측정 부모에서 갈라지는 daughter relief | G4→G5 | 실제 반경 lobe에서 **24개 event**, gain 1.0, 새 변위 최대 **0.020544243115813977** |
| 연속 flow relief | G5→G6 | 위상 배수 4, gain 0.65, 새 변위 최대 **0.014926370257284022** |
| 연속 flow relief | G6→G7 | 위상 배수 8, gain 0.65, 새 변위 최대 **0.007403476624465251** |

Detail 세 단계의 최대값은 각각 그 단계에서 새로 계산한 vector의 크기다. 최종 표면에서 분리 측정한 누적 기여의 최대값이나 단순 합산 진폭이 아니다. 세 단계의 Gram 관측 제외 수는 모두 0이다. 두 flow 단계의 퇴화 입력 법선과 complete-vector clipping 수는 각각 0이다.

축 보정 단독은 X/Y와 반경을 정확히 보존하고, SOURCE가 아닌 면에 incident한 G4 정점을 고정한다. **그 뒤 추가하는 법선 detail은 X/Y도 움직이므로 최종 전체 모델의 반경이 원본과 정확히 같다는 뜻은 아니다.**

## 의도적으로 남긴 사항과 해석 제한

- 부분 펼침은 말린 림의 깊이와 그림자를 유지하기 위한 조형 선택이다. 검사한 G4 SOURCE meridian 72,512개 모서리에서 음의 dZ/dt는 5,506→4,364개로 남는다. 이 수치는 오류 목록이나 미관 점수가 아니며, 0을 목표로 삼지 않는다.
- 위상은 보존된 실제 `G06_MIDDLE/evidence.npz`의 `directional_phase`를 G4 old-ID prefix에서 샘플링한 뒤, 현재 V/E/F 평균으로 운반했다. 저장된 전체 G6/G7 위상 배열을 정확히 재현한 것은 아니다.
- Daughter의 scalar branch field는 측정한 event 양 끝에서 변위와 첫 longitudinal derivative가 0이다. Completed-face 결합은 이웃 표본에 stencil halo를 만들 수 있으므로, 최종 모든 정점이 그 끝점에서 부모에 정확히 고정되거나 수학적 C1 접속을 달성했다고 주장하지 않는다.
- X/Y 반사 오차·유한성·양의 삼각형 면적은 확인했으나 전역 충돌 자유, 제작성 및 근접 조형의 개선을 보증하지 않는다. 조형 판정은 최종 동일 카메라·재질·조명 렌더에 따로 기록한다.

## 보존과 provenance

NESTED02 기준 control·receipt와 실제 G3 ownership, G4 chart/quad, G6 phase, G7 mirror evidence 및 관련 generation metadata는 실행 전후 파일 해시로 묶였다. 실행 소스 `run_final.py`, `axial_reconnect_v2.py`, 그 의존 파일 `axial_reconnect.py`, `branch_detail.py`, `coupled_flow_detail.py`의 snapshot도 보존하고 실행 후 동일성을 확인했다.

| 파일 | SHA256 |
| --- | --- |
| 최종 `RECEIPT.json` | `8ae5898e1e5a878d41da000d9676995141c6f4921f651652ab48ea89dd0a3338` |
| 최종 `DEVELOPED/geometry.npz` | `f57fa477f259c8f448535093e055494ed217a727299d0582040be603e8a6dde8` |
| 최종 `DEVELOPED/control_quad.npz` | `c76d68d0f6193613f26f6818afd06333634241c3a2af5afe22c8c021e926f19c` |
| NESTED02 기준 control | `0092aaf46018411a0008156cc52d223dd25f2ca3192ae7ccc25e21f0afc385d3` |
| NESTED02 기준 receipt | `ab212bf9222980a25cb6d0c5ca31aa82ad0fe5f48b64864d9ed8e8d5fbb02524` |

수치 출처: 위 trial의 `RECEIPT.json` 및 `DEVELOPED/VALIDATION.json`. 이 문서 작성 시 대용량 geometry/control 배열을 다시 로드하지 않았다.
