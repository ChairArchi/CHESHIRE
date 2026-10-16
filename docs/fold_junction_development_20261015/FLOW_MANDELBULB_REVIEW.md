# 기존 흐름 보존과 Mandelbulb 결합 검토 — 2026-10-15

사용자 요청: G6까지 읽히던 흐름을 살리는 방안, 그리고 레퍼런스처럼 Mandelbulb를 섞는 방안의 가능성을 검토한다. 이 검토에서 새 모델이나 렌더를 생성하지 않았다.

## 현재 결정

- **NESTED02가 계속 기준이다.** trial10_macro_cross_folds는 같은 카메라의 실제 native 근접·몸체 렌더에서 큰 판과 돌출, 각진 접속이 기존 S 흐름을 압도하여 미채택이다. 다른 기둥에 적용 가능한 계보를 찾은 것과 아름다운 형상 발전은 다르다.
- `recursive_fold_formation_v2.py`와 `run_macro_recursive_v2.py`는 준비되었지만 **전체 실행 보류**다. v2의 작은 진폭·폭·guide pooling은 유용할 수 있다. 그러나 두 경계 사이 ruled carrier로 내부 곡면을 교체하므로, 경계 좌표가 같아도 기존 내부 S곡률을 펴버릴 수 있다. trial11은 아직 생성하지 않았다.
- 다음 실제 조형 연산은 채택된 실제 곡면을 기준으로 해야 한다. 큰 능선·골의 경로, 말림의 깊이와 접선 흐름을 보존하고 그 안에서 하위 형상을 형성해야 한다. 단순한 경계 고정이나 작은 최대 변위는 이 조건의 충분한 증명이 아니다.

추가 코드 검토: 현재 macro 연산에서 원래 사건은 부모를 찾는 탐색 범위로만 쓰이며, event_wave/amplitude_multiplier를 사용한 실제 소유권 분할은 아직 없다. 같은 근접 S면을 family 4·5·7이 동시에 포함한다. 원래 작은 bridge 사건도 여러 변형이 합쳐진 성숙한 곡면의 깊이로 큰 진폭을 받을 수 있다. 따라서 탐색 범위를 찾았다는 이유로 8개가 각각 독립된 실제 부모라고 해석하지 않는다. 다음 형성 전에 중첩된 계보의 소유권과 부모 기여를 정리하여 같은 면에 변형이 거듭 쌓이지 않게 해야 한다.

## 공개 원리와 현재 구현

[IAAC Mesh Subdivision](https://www.iaacblog.com/programs/mesh-subdivision/)은 Mandelbrot 영역과 subdivision을 결합한다. 공개 nearest-outside 도판은 분할한 실제 좌표의 영역 판정과 목표점 이동을 다시 반복한다. 본문에는 영역 수·n 값뿐 아니라 subdivision 종류, 초기 형상, 깊이와 추가 attractor curve의 탐색도 명시되어 있다. 공개 자료는 최종 결과의 모든 수치나 원본 실행 코드를 제공하지 않는다.

[Hansmeyer Design by Subdivision](https://archive.bridgesmathart.org/2010/bridges2010-167.pdf)은 가중 보간과 face/edge/vertex 법선 돌출, 공간·세대에 따른 가중치, 원래 요소와의 거리 및 태그·locking을 설명한다. [Subdivided Columns](https://michael-hansmeyer.com/subdivided-columns)는 전체부터 세부까지 연속된 표현과 tagged input을 설명한다. 이 공개 설명에서 Mandelbulb가 한스마이어의 필수 핵심이라고 결론짓지 않는다.

우리 선택 계보도 이미 G1·G2에서 finite Mandelbulb의 nearest-outside 재구성을 사용했다. G3 이후에는 WALL/root, 방향성 subdivision, whole-body field와 nested normal field로 구동 방식이 바뀌었다. 따라서 문제는 Mandelbulb 코드 자체의 부재가 아니다. 근거: `../iaac_workflow_comparison_20261013/COMPARISON.txt`, `experiments/fold_band_growth_20261011/full_loop.py:31`.

## 가능성 비교

| 방안 | 기대할 수 있는 점 | 현재 판단 |
| --- | --- | --- |
| 기존 실제 곡면을 유지하며 부모에 종속된 가중 세분·작은 return을 형성 | CHESHIRE의 긴 S 흐름과 말림을 유지할 가능성이 가장 높음 | 우선 경로. 새 형상이 읽히면서 부모 흐름이 유지되는지는 native 렌더로 판단해야 함 |
| 현재 기둥 전체에 기존 world-space nearest-outside를 그대로 재개 | 공간 형상장의 3차원 반응을 직접 얻음 | 우선 실행하지 않음. 기존 능선·골 전체가 이동하고 격자 목표점에 모일 위험이 큼 |
| 실제 부모의 흐름·가로폭·깊이에 맞춘 국소 Mandelbulb 결합 | 흐름을 따라 변화하는 세부와 비균일한 수렴·발산을 구동할 가능성 | 유망한 설계 가설. IAAC 원본 재현이나 검증된 미적 해법으로 부르지 않음 |

국소 결합에서 원래 생성 사건 8개의 계보와 실제 현재 곡면에서 읽은 물리적 arc/frame을 사용한다. 임의의 카메라 패치나 손으로 배치한 장식을 사용하지 않는다. 부모를 따라 길게 이어지는 방향과 가로 방향을 구별하고, 형상장의 크기와 반응량을 부모의 폭·깊이에 종속시킨다. 한 번의 subdivision 안에서 가중치나 제한된 3차원 이동을 제어할 수 있지만, 단순한 scalar height map을 법선에 더하는 구현은 체적 Mandelbulb의 branching/topology를 재현하지 않는다.

## 이전 CONTINUED 실패가 의미하는 범위

보존된 operation 배열을 읽은 `diagnosis_continued_saved_results.json`에 따르면, 분할 후 median edge는 0.03302인데 target 후보 간격은 0.03/0.03125였다. 새 edge의 42.70%가 0.03보다 작다. 8,277개 active canonical point가 3,224개 목표점을 사용했다. 활성 이웃의 변위차/edge 비율은 median 0.513, p99 2.388이다. 이 수치는 격자 목표점으로의 집중과 이웃 변위의 급변이 crust를 만들 수 있다는 기계적 근거다.

같은 pass의 Task36 변위는 old V=0, new E median 0.00980, new F median 0.01914로 birth 종류에 따른 차이도 있다. G3 target factor3에서 G4 factor2로 목표 정밀도가 오히려 낮아졌다. 다만 여러 조건이 동시에 달라졌고 입력도 현재 G6가 아닌 이전 OVERLAP G3였다. 이 실험은 **그 특정 전역 결합의 실패**이며, 부모 흐름에 맞춘 모든 Mandelbulb 결합이 실패한다는 증거는 아니다.

## 효율적인 다음 판별

여러 power·반복수·세대 조합을 전역으로 돌리지 않는다. 우선 실제 생성 계보에서 얻은 하나의 연결된 부모 영역으로 비교한다. 동일한 실제 곡면·ownership·진폭 한도·세분 규칙을 사용하고, 부모 국소 형상장 반응의 유무만 다르게 한다. 부모의 골·능선 경로와 장거리 접선 흐름, 하위 형상 크기, 이웃 변위의 연속성을 함께 확인한다. 유의미한 구조가 보이고 기존 흐름이 유지되는 경우에만 전체 native 렌더로 확대한다. 수치 통과가 아름다움을 보장하지 않는다.

이 기록은 가능성 검토와 실패 방지 조건이다. 새로 아름다워진 결과물의 완성 보고가 아니다.
