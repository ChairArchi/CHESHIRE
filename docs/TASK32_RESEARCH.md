# Task32 — 초기 가설 및 기존 연구 검토 기록

이 문서는 실험을 시작할 때의 가설·검토 기록이다. 실제 후속 대조, 실패,
검증·보존 결과와 현재 판정은 [TASK32_RESULTS.md](TASK32_RESULTS.md)에 있다.

기준 커밋: `17c0415b8d7bdead8763949bfa8d95f18fad908c`.
브랜치: `experiment/task32-relational-morphology`.
새 산출물: `E:/CHESHIRE_DATA/task32`. 기존 Task31 1,539개 파일을 크기·SHA256으로 확인했다.
ALICE 및 Task01–31의 연산·테스트·산출물을 변경하지 않는다. 원격 push 없음.

## 연구 전 확인한 사실

| 연구 | 코드·원본 기록·실제 이미지에서 확인 | 이번 연구에 주는 제약 |
|---|---|---|
| 23 | cross-cell crease, 실제 parent/event ancestry, 깊이 7–8 constructive detail 존재. R20 전체뷰는 넓은 둥근 지지부와 각진 상부가 지배한다. sampled contact와 drift 존재. | 피드백 부재라고 단정할 수 없다. 더 강한 crease와 단일 면의 중첩 extrusion만 재실행하지 않는다. |
| 24 | H1/H2/H3 조합은 구분되지만 세 개의 설득력 있는 Hero는 아니라는 원판정. Task23 계열의 같은 연산 재조합. | 구성 차이를 새 알고리즘 효과로 귀속하지 않는다. |
| 25 | normal-offset 중지 시 넓은 curl이 회복됨. w3/w4 증폭은 작은 각진 조각 증가. inherited FLOW는 중앙 motif 개선 미미. 실제 H1_S01 전체뷰는 fragment texture가 강하다. | 단순 진폭 증가와 고해상도가 위계를 해결한다는 가설은 지지되지 않는다. |
| 26 | 같은 전체 U carrier, material-space support·reflection 구현. 실제 native 단면에서 두 lead의 차이는 작다. | 대칭 정확성과 조형적 개선은 별도다. |
| 27 | PROFILE carrier·geometry feedback는 이미 존재. static/dynamic matched views 모두 cell 반복이 남는다. | geometry feedback 자체를 신규 성과로 주장하지 않는다. |
| 28 | 단순 column G1 macro/G2 secondary/G3 pleats, G4–5에서 세부 소실. 실제 progression 확인. | smoothing은 일부 조건에서 실제 문제지만 모든 Task31 약점의 원인이라고 확정하지 않는다. |
| 29 | 원논문 coupled CC, 실제 point classes, local scales, locks, 20 G8 lineages. 세부는 cell motif와 연관됨. | 이미 실패한 point-class 증폭/lock 탐색을 새로운 방향으로 포장하지 않는다. |
| 30 | CC/DS 조합과 지역 descriptor 비교 후 병목 C 판정. | CC↔DS 전환만으로 hierarchy를 얻었다고 주장하지 않는다. |
| 31 | persistent four-mode 지역 제어, actual parent inheritance, early tunnel/CHANNEL. 실제 whole/detail에서 넓은 lobes·neck·lintel band와 세부 억제 확인. | opening은 명시적 topology edit. persistence 우월성·독립 fine hierarchy·무교차 solid는 미입증. |

위 해석은 기존 기록과 관찰의 결합이며 모든 가능한 기존 파라미터의 실패를 증명하지 않는다.
검토 이미지의 경로·해시는 최종 증거 목록에 보존한다. 기존 기록의 판정은 수정하지 않는다.

## 문헌 및 구현 구분

1. [Gingras & Kry, 2019, Reaction Diffusion and Growth of Thin Shells](https://www.cs.mcgill.ca/~kry/pubs/gi2019/Reaction_Diffusion_Shell_Growth.pdf): Gray–Scott 신호와 물리 thin-shell growth의 결합. 논문은 성장률·분할·신호의 상호작용 및 충돌 처리 제약을 논의한다. 이번 metric-growth는 rest-edge 변화와 변위 Laplacian을 쓰는 독립 surrogate다. ARCSim 재현·물리적 folding·재료 적합성을 주장하지 않는다. RD를 구현하지 않은 결과를 RD라고 부르지 않는다.
2. [Li et al., 2011, Field-Guided Shape Grammars](https://peterwonka.net/Publications/pdfs/2011.TVCG.Li.FieldGuidedGrammar.TechnicalReport.pdf): field가 관계·배치·규칙을 제어하는 접근을 조사한다. 이번 swept hierarchy는 기존 U carrier의 arc/angle에서 부모 envelope·위상에 자식을 연결하는 독립 displacement 응용이다. 원논문 streamline transport, tensor design, collision/merge를 구현한 것은 아니다. 실제 다운로드·읽기 범위는 별도 sources manifest에 기록한다.
3. [Eck et al., 1995, Multiresolution Analysis of Arbitrary Meshes](https://hhoppe.com/proj/mra/): 스케일을 분리해 다루는 근거. 이번 구현은 wavelet analysis나 arbitrary remeshing을 구현하지 않는다.
4. [Stein et al., 2018, Developability of Triangle Meshes](https://www.cs.cmu.edu/~kmcrane/Projects/DiscreteDevelopable/): seam/ruling을 가진 developable 모델링을 검토. geometry를 flattenable하게 만드는 목표가 이번 closed gate의 부피·개구부와 자동으로 양립하지 않는다. 공식 공개 구현의 [라이선스](https://github.com/odedstein/DevelopabilityOfTriangleMeshes/blob/master/LICENSE.txt)는 GPLv2, 추가 의존성 라이선스도 존재한다. 코드를 복사·설치하지 않는다.
5. [Geometry Central](https://geometry-central.net/surface/algorithms/geodesic_distance/)의 공식 distance 문서 및 [MIT 라이선스](https://github.com/nmwsharp/geometry-central/blob/master/LICENSE)를 확인했다. 이번 carrier arc는 polyhedral geodesic/heat method가 아니다. 라이브러리를 설치하거나 원 코드를 복사하지 않는다.
6. [Ready](https://github.com/GollyGang/ready)는 mesh RD 공개 구현으로 조사했다. 저장소는 GPL-3.0을 표시한다. 개별 소스·라이선스 파일 확인 수준은 manifest에 기록한다. 코드 재사용·실행 검증 없음.

## 가설과 초기 배치

- H1: 공간적으로 다른 rest length를 실제 geometry에 만족시키는 변형이 per-cell 돌출과 다른 중간 규모 형태를 만들 수 있는가? 동일 성장량의 isotropic/anisotropic 및 bands/nested 비교. gradient 수치 검증 및 zero-growth 대조 먼저 수행.
- H2: 작은 요소의 방향·위상을 큰 요소와 연결하면 서로 독립된 cell detail보다 hierarchy가 읽히는가? 같은 진폭·주파수에서 coupling on/off, twist on/off 비교. 실제 topology branching과 구분.
- 대조: 정확히 같은 `gate_input('RECT', False)`와 neutral CC. Task31 actual checkpoint도 같은 카메라로 비교한다. 서로 다른 mesh counts와 연산 단계는 표시한다.

G2에서 변형하고 G4에서 전체/사선/상부 확대를 먼저 검토한다. 실험 수의 최종 상한은 정하지 않는다. 관찰 후 추가 가설·실험·보류 이유를 기록한다. 첫 작동 결과는 최종 lead로 확정하지 않는다.

## 실행·보존

`.venv/Scripts/python.exe -B tools/task32_research.py run --definition E:/CHESHIRE_DATA/task32/definitions/pilot/P02_GROWTH.json`

`tools/task32_designs.py pilot`는 배치 정의를 한 번 생성한다. `request --folder ... --tag ...`로 별도 render request를 생성하고 `task32_research.py render --request ... --tag ...`로 기존 Task31 renderer를 새 write root에서 실행한다.

각 stage는 actual mesh, classes/rest/anchors, operator state, 파라미터, parent SHA, 소스 SHA, 시간·기하 지표를 보존한다. 완료 checkpoint 재개 시 모든 파일·부모·정의·소스 identity를 확인한다. 변경된 소스는 새 ID로 실행해야 한다. 기존 파일 덮어쓰기는 거부한다.

기존 `hero_design_sprint.guarded`의 실제 RAM·process birth identity·프로세스 가족 종료 장치를 사용한다. RAM 예측·최소 4GiB disk reserve를 추가 유지한다. 임의의 wall-clock stop 없음. solver maxiter는 명시된 수치 계산 예산이며 미수렴을 성공으로 처리하지 않는다.

closed oriented edge incidence, finite 좌표 및 unsigned area는 저장할 때 검사한다. 이것만으로 manifold vertex link·자기교차·개구부·solid validity를 증명하지 않는다. 추가 기하 검증·동일 렌더·단면 및 checkpoint replay를 거쳐 결과를 판정한다.
