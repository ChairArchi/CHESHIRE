# ASTRA 후속 연구 판단

현재 출발점은 **D00의 적응 분할을 더 깊게 반복하면 해결된다**가 아니다. D00는 검증·재현 가능한 macro 보존 대조, Task36 U01은 더 풍부한 내부 세부의 기준으로 남긴다. 둘 중 하나의 아키텍처를 유지할 의무는 없다. [실제 결과](ASTRA_RESEARCH_RESULTS.md)의 실패를 다음 가설 선택에 사용한다.

## 먼저 바꿀 연구 단위

단일 face의 normal offset 대신 **실제 능선 양측을 포함한 연결 patch**에서 중간 규모 골을 생성하는 연산을 시험하는 것이 다음 유력 후보다. 현재 scalar curvature response는 세밀한 hinge가 큰 반응을 만들고, physical amplitude를 키우면 주변 면과 충돌한다. 단순한 셀 크기 보정이나 더 많은 subdivision으로 이 문제가 해결된다는 근거가 없다.

1. G3의 실제 crest 하나와 valley 하나를 선택하되 고정 좌표 장식이 아니라 곡률·폭·주변 방향으로 patch를 찾는다. 초기 진단은 선택을 명시하고 동일 patch를 대조한다.
2. 실제 patch 너비와 두 측면의 방향을 바탕으로 변형 support와 방향 field를 만든다. normal-only, 접선/법선 결합, 기존 Task32 connected patch 및 Task33–35 feature-scale 방식의 최소 이식본을 나란히 비교한다. 기존 방식의 fixed radial/material 가정은 그대로 자유3D 방식인 것처럼 들여오지 않는다.
3. 부모 crest를 둘러싼 새 두 능선과 중앙 골이 실제 삼각 표면에서 생기는지, 주변 patch와 연결돼 있는지, 다음 동일 규칙이 새 구조를 재선택하는지 확인한다. 모양을 코드에 직접 지정한 ornament template은 대조에서 분리한다.
4. 각 step의 clearance와 transverse/coplanar 상태를 함께 기록한다. 기존 전체 검사0만으로 가까운 면 사이에 충분한 변형 여유가 있다고 가정하지 않는다. 충돌 한계가 먼저 오면 강도만 줄이지 말고 support/방향/연결의 원인을 분리한다.

**진입 기준:** 소형 patch에서 기존 부모 깊이를 유지하며 prominence15의 실제 새 내부 골을 적어도 한 세대 만들어야 전체 column 비용을 투입한다. 이 수치는 현 좌표의 기존 비교 기준이며 새 입력으로 옮길 때 단위를 명시한다. 국소 성공은 전체 성공과 구분한다. 여러 사전 위치·방향과 다음 세대까지 유지되지 않으면 PARTIAL이다.

## topology 변화는 별도 능력으로 검증

Digital Grotesque II의 porosity는 중요한 미구현 항목이다. 그러나 현재 교차 메시를 welding하거나 고정 위치 구멍을 넣어 발생적 topology라고 부르면 안 된다. [역사 감사의 최소 조건](ASTRA_HISTORY_AUDIT.md#7-발생적-genus-변경을-연구하기-전에-빠진-최소-조건)을 따르는 독립 소형 실험이 필요하다. near-contact 사건 탐지, 두 disk 경계의 유효 replacement, Euler/vertex-link/embedding 검사, 대칭 사건 충돌 처리, 다음 subdivision의 extraordinary valence 지원을 먼저 증명한다. 이 능력과 깊은 주름은 서로 대체 성과가 아니다.

## 반복하지 않을 것

- B05의 강한 quad continuation 또는 D01 G9를 그대로 늘리는 실행: 이미 교차 실패가 있다.
- D02를 더 조밀하게 만드는 실행:186만 삼각형에서 새 내부 basin 증거가 없었다.
- E02/E05를 변위만 증폭하는 실행:15/30단위 둘 다 충분한 계층 발달 전에 교차했다.
- 초기 smoothing·bbox lock·수정 전 coupling을 단일 원인으로 다시 제시하는 설명: 현재 코드와 기존 대조가 반박한다.
- Task36보다 외곽이 부드러워졌다는 이유만으로 개선 판정: 깊은 내부 골의 성과를 잃을 수 있다.

## 실행과 재사용

실행기·레시피·체크포인트·검사 도구는 [구현](ASTRA_IMPLEMENTATION.md)과 [색인](ASTRA_EXPERIMENT_INDEX.md)에 연결돼 있다. D00/D01 유효 prefix가55 NPZ byte-exact로 재현됐다. 신규 작업은 새 branch와 새 tag에서 실행하고 현재 source snapshot과 실패 상태를 보존한다. 기존 baseline tag, original worktree, Task01–36 archive를 변경하지 않는다.

현재 .venv와 일부 DLL은 기존 머신의 환경을 읽는다. 다른 머신으로 이관할 때는 `pyproject.toml`, 기존 handoff의 dependency 목록, DLL 라이선스와 Python3.12 환경을 먼저 맞춰야 한다. source Git bundle만으로 대형 메시·외부 의존성까지 복원되는 것은 아니다. 새 데이터 SHA 목록은 무결성 검사용이며 별도 물리 디스크 백업을 대신하지 않는다.
