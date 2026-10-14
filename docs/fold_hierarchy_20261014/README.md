# G7 주름 위계 및 표면 단위 재구성

2026-10-14 / Asia-Seoul

사용자가 최신 3D 모델을 직접 확인한 뒤 제안한 주름의 강약·크기 위계와 더 큰 표면 결을 다룬 고정 레시피 한 개이다. 기존 체크포인트는 보존하며, 이번 자료의 조형 채택은 실제 렌더 검토 뒤 판단한다.

## 입력과 계보

비교 기준은 `comb_scale_refinement_20261014/trial01/REFINED`이다. 연산 입력은 이 결과와 공통인 `end_rule_revision_20261014/trial01/REVISED/control_quad.npz`이며 SHA256은 `0915ac8f56509768c6329a7d848793c6936b903d4d9316e01b1076a76aba8e27`이다.

원본 및 수정 replay의 실제 G7 SURFACE, LINKED_FINISHED, FINAL에서 기존 변위를 추출하고, 기존 end mask로 동일하게 혼합하였다. accepted REVISED의 정확한 splice를 확인했으며 추출 성분 합의 최대 좌표 오차는 `1.7763568394002505e-15`이다. 실제 G6 MIDDLE 변위에는 저장 G6/G7 ID로 복원한 중립 CC 선형 연산을 적용했다. 이 연산의 actual SURFACE 재현 오차는 원본·replay 모두 `3.552713678800501e-15`이다.

## 주름 위계 연산

실제 G6 MIDDLE의 unwrapped phase를 실제 G7 old-vertex/edge/face 대응으로 운반한다. `k=phase/(2π)`의 범위는 0~5이며 각 사분면의 k1·k4 주변을 주부모 영역으로 지정했다. 이는 작성한 위상 기준이며 실제로 읽히는 주름 개수를 측정한 수치는 아니다.

`p=1−(1−exp(−((k−1)/.70)^4))·(1−exp(−((k−4)/.70)^4))`

MIDDLE, LINKED, WIDE의 gain은 각각 `.45+.55p`, `.30+.70p`, `.18+.82p`이다. accepted XYZ에 `(gain−1)×기존 성분 변위`를 더하고 실제 반사 ID로 변위를 운반한다. 원본 형상 전체를 평균하거나 새로운 주름장을 누적하지 않는다.

이는 기존 성분의 강약을 재배분한 G7 수정이다. 후기 형상장의 법선을 새 carrier에서 다시 계산하지 않았으며, 전체 G1~G7 재실행이나 새 성장 공식의 일반성 검증으로 취급하지 않는다.

## 더 큰 표면 단위

최신 REFINED native roof를 그대로 세분하거나 누적하지 않고, 위계를 수정한 공통 carrier 위에 대체 native 마감을 구성한다. 실제 G6 부모의 G7 자식 네 개를 하나의 사선 단위로 사용하며, 부모 경계의 여덟 점은 유지한다. 부모 중심과 native child fan 중심만 이동하며 기존 fan 연결관계를 유지한다. 저장 control carrier와 FINISHED native prefix가 일부 다른 것은 의도한 마감 범위이다.

한 단위는 대응 G7 자식 대비 약 두 배의 재료 좌표상 선형 폭이다. 최신 REFINED에서 이미 네 개로 작게 나눈 구간 대비로는 더 큰 변화가 생길 수 있으므로, 최신 모델 모든 부위의 실제 폭을 정확히 두 배로 만들었다는 의미는 아니다.

지원은 기존 broad warpage mask를 부모별 평균한 뒤 `.65×자기값+.35×실제 네 이웃 평균`으로 한 번 완화했다. 이는 지원 경계의 부모 단위 완화이며, 주부모골의 시작·끝을 검출하여 자동 결속한 연산은 아니다.

## 검증과 보존

HIERARCHY와 FINISHED는 각각 14,004,226 정점, 28,008,448 삼각형이며 원본 G7 native fan의 실제 face 해시가 같다. HIERARCHY의 X/Y 좌표 반사 잔차는 입력과 동일한 약 `4.785e−14`이다. FINISHED의 변위 반사 잔차는 약 `8.882e−16`이다. FINISHED에서 1,083,952 부모 패치를 채택하고 27,660 위험 패치를 전체 반사 궤도 단위로 제외했다. 양의 삼각형 면적, 실제 경계 보존 및 마감 패치의 old/new 법선 내적을 확인했다.

원본 코드·연구 데이터·체크포인트를 덮어쓰지 않았다. 추가 G8, Mandelbulb, Boolean, remesh는 없다. IAAC/Hansmeyer의 원 구현을 재현했다는 주장이 아니라 CHESHIRE의 기존 생성 결과와 자체 작성 제어값을 사용한 수정이다. 이 검증은 전역 자기교차, 제작 적합성 또는 미적 성공을 보증하지 않는다.

## 시각 검토

root가 기존 bare/새 HIERARCHY의 정면·근접·macro와 기존 REFINED/새 FINISHED의 근접·macro를 실제 PNG로 비교하였다. 근접 화면에서 중앙의 반복 주름은 낮아지고 좌우의 강한 주름은 남아 강약 재배분이 확인된다. 전체 실루엣의 변화는 작다. 이는 주름의 위계를 조정할 수 있다는 결과이며, 큰 주름과 작은 주름의 종속 관계가 완성되었다는 판정은 아니다.

FINISHED의 사선 반복 단위 확대와 넓은 분포는 시각적으로 분명하다. 다만 일부 넓은 면에서는 큰 삼각 비늘이나 각진 지붕으로 읽히며, 중앙 지원 영역의 계단형 경계도 남아 있다. 중앙의 조용해진 면과 하단의 둔한 띠 역시 다음 조형 판단 대상이다. 지원값의 이웃 완화가 구현되었다는 사실과 경계가 조형적으로 매끄러워졌다는 주장은 구별한다. 기존 승인 결과를 대체 확정하지 않고 비교 연구안으로 보존한다.

동일 카메라·재질·all-flat 조건에서 주름만의 비교와 두 변경을 합한 비교를 따로 보존했다. 이번 최종 비교는 두 변경을 동시에 포함하므로 모든 시각 차이를 표면 결 하나에 귀속하지 않는다.

사용자는 확대된 삼각 비늘이 다른 조형과 따로 읽히며 일부 구간에 접힘 디테일이 부족하다고 지적하였다. root도 동일한 문제를 확인했다. 이번 확대 마감은 채택하지 않는다. 보조 주름의 강도를 과하게 낮춘 범위와 기존 지원 마스크가 만드는 빈 영역을 구분하며, 다음 수정에서 기존 주름과 미세 형성의 연속성을 우선한다.

## 보존 자료

큰 배열과 실제 메시: `E:/CHESHIRE_DATA/experiments/fold_hierarchy_20261014/trial01`

- [PREPARATION.json](PREPARATION.json): 기존 성분·unwrapped phase·연관 배열 결속
- [MIDDLE_PREPARATION.json](MIDDLE_PREPARATION.json): 실제 중립 CC 재현 및 MIDDLE 변위 추출
- [RECEIPT.json](RECEIPT.json): 고정 레시피, 실행 코드 snapshot, 두 실제 결과와 입력 SHA
- [HIERARCHY_VALIDATION.json](HIERARCHY_VALIDATION.json): 주름 위계 carrier 검증
- [FINISHED_VALIDATION.json](FINISHED_VALIDATION.json): 대체 native 마감 검증
- [EXPORT_MANIFEST.json](EXPORT_MANIFEST.json): 전체 및 근접 PLY의 실제 좌표·면 인덱스 재읽기 검증
- [RENDER_VERIFICATION.json](RENDER_VERIFICATION.json): 별도 두 비교의 동일 카메라·재질·실제 메시 readback 검증
- [IMAGE_PROVENANCE.json](IMAGE_PROVENANCE.json): 실제 전후 PNG와 대화 비교 이미지의 출처

코드: `experiments/fold_hierarchy_20261014/{prepare.py,middle_lift.py,run.py,texture.py}`. 새 데이터 배열은 이 문서 폴더에 복사하지 않는다.
