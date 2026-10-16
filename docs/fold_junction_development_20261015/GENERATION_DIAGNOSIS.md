# G6 이후 생성 규칙의 단절 — 2026-10-15

> **최신 조형 판정:** trial10은 native 렌더에서 큰 판과 각진 접속이 기존 흐름을 무너뜨려 미채택이다. 새 v2의 ruled carrier도 내부 S곡률을 평평하게 할 위험이 있어 실행 보류했다. [기존 흐름 보존과 Mandelbulb 결합 검토](FLOW_MANDELBULB_REVIEW.md)를 먼저 읽는다. 아래의 올바른 부모 매핑·support 확인은 조형 성공의 증거가 아니다.

> **추가 확정 진단:** 아래 초기 분석 뒤 실제 근접 S 패널을 native 삼각형 광선으로 검사했다. 8개 지점 전부 SOURCE이며 CAP/WALL 제외 때문이라는 가설은 성립하지 않는다. 화면에서 길게 보이는 큰 접힘의 여러 지점은 material t가 약 .67–.70에 몰려 있고, MIDDLE 위상은 여러 family에 걸친다. 따라서 그 큰 면을 하나의 height-axis MIDDLE 리본으로 다뤘던 후속 생성의 축·부모 구획이 실제 매크로 접힘과 맞지 않았다. 근거: `diagnosis_visible_face_owners_results.json`.

## 현재 수정

trial08과 trial09는 조형 개선으로 채택하지 않는다. 특히 trial08의 새 형성은 기존 근접 카메라 밖에 있었다. trial09는 새 G6 위상을 부모 목록으로 등록했지만, 여전히 실제 큰 매크로 접힘의 진행 방향을 충분히 나타내지 못했다.

현재 구현은 원래 G0/G2 PCHIP 사건 8개의 생성 계보를 부모 탐색 범위로 사용한다. SPAN warp는 원래 forward cubic을 정확히 역산한다. 실제 현재 표면에서 theta를 따라가는 접힘을 material t 방향으로 절단해 골·양 어깨를 읽고, 더 넓은 실제 어깨 안에서 같은 팽창→수축→재팽창 및 signed back-return 단면을 반복한다. 단면의 radial/axial 역할은 현재 부모의 normal/across 방향 N/B로 바뀌며, 크기는 현재 부모의 물리적 폭·깊이에 종속된다. 특정 이미지 좌표로 새 형상을 배치하지 않는다.

상부 부착으로 부모 탐색 범위 일부가 사라졌을 때에는 해당 ray 전체를 버리는 대신 실제 SOURCE의 연결된 횡단 구간으로 경계를 줄인다. 없어진 표면을 합성하거나 구멍을 가로질러 보간하지 않는다.

`recursive_fold_formation.py`의 실제 NESTED02 G7 사전 측정에서 canonical 부모 7개가 검출됐고, 앞서 광선으로 확인했던 근접 8개 지점 모두 새 forming support에 포함됐다. 이것은 올바른 면에서 작동한다는 증거이며 아름다움의 증거는 아니다. `trial10_macro_cross_folds`는 **현재 채택 NESTED02 G7 자체**를 입력으로 쓰고 세분 없이 단면을 다시 형성한다. 기존 late field나 primary gain을 제거한 차이를 새 형성의 효과로 보고하지 않는다. 채택 여부는 실제 동일 카메라의 근접·몸체·전체 렌더로 결정한다.

사용자는 특정 기둥에 수작업으로 리본·잎을 덧붙이는 방식을 거부했다. 목표는 이미 좋은 주름·수렴/발산·바로크 형상을 만드는 절차적 원리를 더 작은 규모까지 발전시키고, 같은 규칙을 다른 기둥에도 적용하는 것이다. 계산량·용량 최적화는 형상 확보 뒤에 한다. 아름다움과 눈에 보이는 변화가 우선이다.

## 확인된 사실

현재 결과는 재사용 가능한 다단계 recipe다. 하나의 성장식을 G0부터 G7까지 반복한 결과는 아니다. 이 구분은 성과를 부정하는 것이 아니라, 다음 세대에서 어떤 연산을 이어야 하는지 명확히 하기 위한 것이다.

| 구간 | 실제 생성 연산 | 후속 규모로 넘기는 상태 |
| --- | --- | --- |
| G0 | PCHIP radial/axial return, 비례, 깊은 골·terminal 형상 | material chart와 실제 XYZ. 큰 말림이 이미 존재 |
| G1·G2 | 현재 기하를 사용하는 Task36 coupled split + finite nearest-outside field. G2에는 두 return 추가 | 실제 XYZ와 V/E/F·material 계보 |
| G3 | 실제 어깨·골 측정 및 WALL 재구성. 공유 경계 root/sidewall 부착 | 두 longitudinal strip, event 소유권, 부착 root frame |
| G4 | 중립 CC | 현재 기하와 계보 |
| G5→G6 DEPTH08 | 실제 현재 centroid·법선·local scale에 directional coupled CC | 고정 G3 root frame과 event 소유권. **직접 support는 owner>0인 부착 부위** |
| G6 MIDDLE | 실제 현재 XYZ의 theta/z로 만든 whole-body normal field | 저장된 MIDDLE phase/support/z |
| G6→G7 SURFACE | 모든 추가 계수가 0인 중립 CC | G6 phase/support/z를 V/E/F 운반 |
| G7 NESTED02 | 저장된 phase의 flank cos 및 3배 cos에 의존하는 두 normal-offset pass | 새 골·어깨를 다음 부모로 재측정하는 상태는 없음 |

직접 근거:

- `experiments/directional_g6_20261013/g6_operator.py:97`: `support=(owners[parent53]>0)`; SOURCE 몸체 내부는 직접 형성 support가 0이며 경계에만 coupling이 전달될 수 있다.
- 같은 파일 113–120행: `wf/we/wp` 외 위치 계수는 0; 변위 단위는 실제 incident mean-edge scale이다. 계속 세분하면 이 scale도 줄어든다.
- `experiments/whole_column_detail_20261013/whole_field.py:161–188`: 현재 기하에서 theta/z와 normal을 계산하되 작성된 20theta 주름 함수 사용; generation은 6으로 유지한다.
- `experiments/recipe_transfer_20261013/late.py:217–236`: neutral CC 및 phase/support/z 운반.
- `experiments/parent_nested_folds_20261014/parent_nested_readable.py:163–218`: 기존 phase의 자식 함수와 예산; 새 자식 능선·골을 다음 부모로 읽는 연산은 없다.
- NESTED02는 `run_readable.py:80–116`에서 **전체 replay G07_SURFACE**와 replay MIDDLE 기여를 사용한다. original/replay 최종 mask splice를 입력으로 사용하는 것과 구분한다.

## 이미 했던 IAAC 대조와 반복 시험을 다시 해석하기

`docs/iaac_workflow_comparison_20261013/COMPARISON.txt:17–21`은 초기 형상장 loop가 G3 이후 다른 연산으로 전환된 점을 이미 기록했다. 그 차이를 기록한 것과 그것이 최종 미관 실패를 일으켰다고 인과적으로 검증한 것은 다르다. 이후 작업은 이 연결을 고치는 대신 작은 변위와 보호 mask를 반복했다.

반복 자체를 시험하지 않은 것도 아니다. `experiments/column_detail_20261012/continued_probe.py:79–97`은 실제 OVERLAP G3에서 Task36 split 후 finite18 nearest-outside field를 실행했다. 당시 평가(`technical/CONTINUED_DESIGN_REVIEW.md`)는 큰 형상 유지, 작은 grid/crust 증가, 독립적인 작은 주름 위계 미확보다.

보존 operation arrays의 추가 읽기 결과:

- incoming edge 중앙값 0.06287, post-Task36 child edge 중앙값 0.03302.
- 고정 coarse target grid 0.06/0.0625, local grid 0.03/0.03125. child edge의 42.70%가 0.03보다 작다.
- active field의 이웃 변위 차이/edge 길이 중앙값 0.513, p99 2.388.
- 8,277개 canonical active point가 3,224개 target으로 이동한다.
- Task36 기존 V 이동은 0, 새 E 이동 중앙값 0.00980, 새 F는 0.01914.
- G3 target factor3에서 G4 factor2로 바뀌어 국소 목표 검색은 오히려 거칠어졌다.

이 관찰은 고정 격자·birth class 대비·feedback이 crust를 만들 수 있다는 메커니즘의 증거다. 요인을 분리한 인과 실험은 아니다. 당시 입력은 현재 G6가 아닌 OVERLAP G3이므로, 현재 주름 원리의 추가 발전 전체가 불가능하다는 결론으로 확대하지 않는다.

## 수정할 대상

하드웨어 한계, subdivision 수식 자체의 오류, G6 이후 생성 불가능은 확인되지 않았다. 확인된 구현상의 구멍은 **생성된 몸체 주름을 다음 연산의 부모로 넘기는 상태와 호출 연결의 부재**다. 새 작은 법선값만 추가하면 이 구멍이 생기지 않는다.

기존 `NativeChartSampler`, `measure_child`, `measure_rails`, `region_fold.proposal(mode='RETURN')`, `descend.run()`에는 실제 표면의 골·어깨·물리 arc와 방향을 측정하고 기존 면을 함께 접는 부품이 있다. 다만 마지막 runner는 한 번의 descendant에서 멈추며, G3 전용 wrapper·canonical column chart·소유권 제약이 있다.

다음 구현의 계약은 `step(actual_mesh, material_chart, fold_state) -> actual_next_mesh, next_chart, next_fold_state`다. 실제 입력 기하의 소유 구간 안에서 골과 어깨를 다시 측정하고, 같은 3차원 형성 연산으로 자식을 만들고, 새 자식의 소유 구간과 측정 근거를 다음 호출에 넘긴다. 크기는 실제 부모 폭·깊이에 종속시킨다. 골이 검출되지 않으면 임의 문양으로 대체하지 않고 그 계보의 생성을 종료한다.

이는 G6 CC 함수를 그대로 다시 호출하는 것과 같지 않다. 기존에 성공한 기하 반응·부모 종속 형성을 SOURCE 몸체의 후속 규모에도 연결하는 수정이다. 아름다운 결과인지는 같은 카메라에서 실제 형상으로 판단해야 한다.

## 현재 조형 판정

NESTED02가 여전히 기준이다. trial04는 사용자에게 변화가 미미하다고 거부되었고, trial05/06은 반복 결이 강해 미채택, trial07은 명료한 형상 발전이 부족해 미채택이다. 수작업 projected ribbon guide/hero sculpt는 사용자 지시에 따라 중단했으며 실제 파일·모델을 생성하지 않았다. 이 진단 문서는 새로운 아름다운 형상을 완성했다는 보고가 아니다.
