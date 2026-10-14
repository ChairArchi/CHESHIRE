# G7 연속 사선 접힘 마감

2026-10-14 / Asia-Seoul

큰 삼각 비늘과 국소 지원 경계가 별도 장식처럼 읽힌 이전 확대 마감을 대체하는 수정이다. 같은 고정 구성에서 높이 위상의 주파수만 한 번 교정한 두 시험과, 두 번째 시험의 완료 변위만 확대하는 가시성 교정 한 개를 보존한다. 원본 연구와 accepted 모델은 보존하며, 새 형상의 시각적 채택은 실제 렌더 검토 뒤 판단한다.

## 입력과 위계 수정

비교 기준은 `comb_scale_refinement_20261014/trial01/REFINED` native 모델이다. 실제 연산은 공통 carrier인 `end_rule_revision_20261014/trial01/REVISED/control_quad.npz`에서 시작한다. SHA256은 `0915ac8f56509768c6329a7d848793c6936b903d4d9316e01b1076a76aba8e27`이다. 이전의 강한 위계 억제 결과와 확대 roof 결과를 입력으로 누적하지 않는다.

[기존 성분 추출](../fold_hierarchy_20261014/PREPARATION.json)과 [실제 중립 CC MIDDLE lift](../fold_hierarchy_20261014/MIDDLE_PREPARATION.json)를 사용한다. unwrapped 부모 위상의 k1·k4 주변을 강화하는 연속 가중치 p는 이전 위계 비교와 같다. MIDDLE gain은 `.95+.35p`, LINKED/WIDE gain은 `.80+.20p`이다. 부모 MIDDLE 성분을 95~130%로 조정하고 후기 주름을 80~100% 유지한다. 이 단계의 최대 실제 변위는 약 `.017478`이다.

이는 저장된 성분의 강약 재배분이며, G1~G7 전체 재실행이나 새로운 재귀 성장식의 확보로 취급하지 않는다.

## 연속 fine fold

수정한 carrier의 실제 법선에 한 번의 signed 변위를 적용한다.

`ψ=12×저장 부모 위상+2π×125×저장 높이 좌표` — trial02

`signed=H×.00025×양끝 smoothstep×(.55+.45sin²(부모 위상))×sampling_gain×cos(ψ)` — trial01·02

trial03은 trial02의 완료 fine 변위를 2.5배로 확대한다. 유효 fine 진폭 상한은 `H×.000625`이며 새 형상장이나 법선을 계산하지 않는다.

trial01은 높이 계수 400을 사용했다. 수평 띠의 영향을 줄이려는 단일 교정으로 trial02에서 이 계수만 125로 바꾸었다. 위계 gain, 부모 위상 계수 12, 진폭, 지원 및 변위 평균 규칙은 같다. trial01의 코드·배열·검증 기록은 수정하지 않는다.

부모 위상과 재료 높이를 결합한 사선 방향장이다. 부모 등고선과 항상 평행한 접힘이거나 모든 위치에서 동일한 물리 폭을 가진다는 뜻은 아니다. 기존 warpage 지원 마스크나 event support를 디테일의 활성 영역으로 사용하지 않는다.

모든 실제 incident edge의 위상 차이를 계산하여 `sampling_gain=min(1,((π/2)/max_gap)²)`로 진폭을 줄인다. 이는 샘플링이 부족한 구간의 진폭 감쇠이며 Nyquist 초과나 alias를 완전히 제거한 검증이 아니다. 새 변위만 실제 edge 이웃으로 한 번 평균한 뒤 실제 반사 ID로 운반한다. 기존 carrier 자체를 평균하지 않는다.

실제 control 정점을 이동하고 native fan 중심을 수정한 quad의 산술평균으로 다시 계산한다. 별도 roof, 독립적인 fan 중심 돌출, 새 면·정점 또는 G8을 추가하지 않는다. 최신 REFINED의 roof mesh에 누적하는 것이 아니라 공통 carrier의 대체 마감이다.

## 두 고정 시험의 실제 검증

control 정점 7,002,114개가 fine 변위로 모두 바뀌었으며 native는 14,004,226 정점·28,008,448 삼각형이다. 이는 정점 기준 변화 범위이며 표면적이나 조형 성공의 지표가 아니다. 실제 원본 native fan face 해시가 유지되었다.

두 시험의 고정 fine 진폭 상한은 `.00243396`이다. 새 fine 변위의 반사 잔차는 모두 0이며 실제 출력 좌표의 X/Y 반사 잔차는 원본과 같은 약 `4.785e−14`이다. 모든 native 삼각형의 면적은 양수이다.

| 항목 | trial01 · 높이 계수 400 | trial02 · 높이 계수 125 |
|---|---:|---:|
| 실제 최대 fine 변위 | .00242935 | .00242175 |
| sampling gain < .5 정점 비율 | 11.95% | 5.19% |
| edge 위상 표본 < π/2 비율 | 85.36% | 93.19% |
| 최소 native 삼각형 면적 | 7.857e−10 | 3.005e−10 |
| 실행 시간 | 178.6초 | 157.3초 |

이 차이는 샘플링 감쇠와 실제 메시의 수치 범위이며, 곡선의 아름다움이나 alias가 없다는 증거가 아니다.

원본 코드·메시·체크포인트를 수정하지 않았으며 두 시험의 입력 해시와 실행 snapshot을 각각 보존하였다. 이 검증은 전역 자기교차·제작 적합성·미적 성공을 보증하지 않는다. IAAC/Hansmeyer의 원 구현 복원이 아니라 기존 CHESHIRE 좌표와 자체 작성 계수를 사용한 G7 수정이다.

## 가시성 교정 · trial03

trial02 fine 변위의 크기만 고정 배율 2.5로 확대한다. 실제 구성은 `X03=X02+1.5×δ02`이며 `δfine,03=2.5×δfine,02`이다. 부모 위계, 높이 계수 125, 방향, 피치, 지원과 기존 변위 평균은 바뀌지 않는다. 새 normal-field pass는 0회이며 trial02의 normal-field pass 한 회를 계승한다.

유효 진폭 상한은 `.00608490`, 실제 최대 fine 변위는 `.00605438`이다. 원래 carrier에 확대 변위를 더하는 표현과 실제 구성의 최대 좌표 차이는 `1.7763568394002505e-15`이다. 7,002,114개 control 정점이 바뀌었고, 기존 native fan의 14,004,226 정점·28,008,448 삼각형을 유지한다. 모든 native 면적이 양수이며 최소 면적은 약 `6.038e−10`이다. fine 변위 반사 잔차는 0, 출력 좌표 반사 잔차는 원본과 같은 약 `4.785e−14`이다. 실행 시간은 약 95.0초이다.

이 검증은 가시성이나 아름다움을 판정하지 않는다. trial01·02의 코드와 JSON, 메시를 보존하며 trial03의 실제 렌더를 별도로 검토한다.

## 시각 검토

root가 세 시험의 실제 동일 조건 근접·macro 및 전체 형상을 검토하였다. trial01의 높이 계수 400은 작은 형상을 연결된 접힘으로 만들지만 규칙적인 횡방향 골판 인상이 강했다. trial02의 125는 이 인상이 줄고 기존 큰 주름에 더 잘 흡수되지만 작은 형성의 가시성이 약했다. trial03은 동일한 125 방향장·간격·지원·위계를 유지하고 미세 변위만 2.5배로 높여, 우측 하강 주름과 좌측 면에서 연결된 작은 접힘이 더 분명하게 보인다.

이는 기존 주름 좌표를 공유하는 연속적인 미세 형성의 검토 결과이다. 부모-자식 조형 위계 완성, 모든 근접 면의 품질, 기존 각짐 또는 말림 겹침의 해결을 뜻하지 않는다. trial03을 이번 연구의 최종 검토안으로 보존하며, 기존 승인 모델을 대체 확정하지 않는다.

사용자가 지적한 중앙의 넓은 주름 하단 절단면 인상은 별도 회귀이다. 동일 카메라와 렌더 조건의 기존 WIDE_ROOT/WIDE_ROOT_FINISHED에서는 말림과 작은 군집으로 연결되던 끝이 end_rule_revision의 REVISED에서 납작한 판형 종료부로 바뀐 것을 실제 이미지로 확인했다. 현재 fine field 이전부터 존재하므로 미세 결 추가로 발생한 것으로 귀속하지 않는다.

컷라인 영역의 실제 edge와 변위 분해에서도 국소 mask 합성의 전이 문제가 확인되었다. `Xfinal=Xoriginal+m*(Xreplay-Xoriginal)`에서 mask가 0에서 .125로 변하는 edge [52332,1959852]는 원본 길이 .00014165에서 합성 후 .01468549로 늘어났다. 이 edge의 합성 변위 차이를 분해하면 mask 전이 항은 .01452449, replay 변위 변화 항은 .00011546이다. 이웃 edge에서도 mask 전이 항이 우세하다. 해당 경계의 급격한 변위가 판형 종료부에 기여한다는 직접 근거이며, 전체 끝 모양의 유일한 원인을 확정하거나 끝단을 해결했다는 뜻은 아니다. 원본 replay 자체의 변형도 구분하여 보존한다.

[END_TERMINATION_AUDIT.json](END_TERMINATION_AUDIT.json)에 동일 카메라 이미지, 실제 원본·replay·mask 좌표와 대표 edge 세 개의 수치를 보존했다. 화면상의 control 깊이 필터는 근사값이며 정확한 triangle-ID picking은 아니다. 이 감사에서 새 형상·렌더·수리 실험은 하지 않았다.

## 종료 상태와 다음 방향

사용자의 지시에 따라 이번 연구는 여기서 종료한다. 추가 형상 시험을 시작하지 않는다. 세 고정 시험, 실패한 강한 횡방향 리듬, 최종 검토안 및 원본 계보를 함께 보존한다.

다음 단계의 권장 우선순위는 **중간 주름의 끝단 연속성 복구** 한 가지이다. 이번 미세 접힘의 방향·간격·진폭은 고정하고, 큰 주름이 갑자기 판처럼 끝나는 회귀를 수정한 뒤 같은 카메라에서 비교한다. 이는 향후 작업 제안이며, 아직 구현하거나 검증한 성과가 아니다.

끝단 비교와 근거: [동일 조건 이미지](END_SOURCE_COMPARISON.png), [이미지 출처](END_REFERENCE_IMAGES.json). 실제 edge 분해 근거는 종료부 감사 기록에 보존한다.

## 자료

큰 배열과 실제 모델: `E:/CHESHIRE_DATA/experiments/flow_fold_finish_20261014/{trial01,trial02,trial03}`

- [RECEIPT.json](RECEIPT.json), [VALIDATION.json](VALIDATION.json): 보존된 trial01의 고정 레시피와 실제 검증
- [FINAL_RECEIPT.json](FINAL_RECEIPT.json), [FINAL_VALIDATION.json](FINAL_VALIDATION.json): trial02의 입력·실행 코드 7개 snapshot·결과 SHA와 실제 검증
- [BOLD_RECEIPT.json](BOLD_RECEIPT.json), [BOLD_VALIDATION.json](BOLD_VALIDATION.json): trial03의 실제 source02 및 저장 fine 변위 결속, 배율 2.5와 실제 검증

코드: `experiments/flow_fold_finish_20261014/{run.py,flow_operator.py,run_curved.py,flow_curved_operator.py,run_bold.py}`. NPZ는 문서 폴더에 복사하지 않는다.
