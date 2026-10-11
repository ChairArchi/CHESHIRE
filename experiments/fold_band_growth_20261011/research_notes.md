# IAAC 공개 자료 추가 추적 — 2026-10-11

원본 Mesh Subdivision 프로젝트와 같은 수업의 공개 도식·코드 이미지를 구분해 읽었다. 원저자 이름, 교수 이름, IAAC/GitHub 조합으로 제한 검색했지만 이번 검색에서는 원본 실행 코드 저장소를 찾지 못했다. 비공개이거나 존재하지 않는다고 단정하지 않는다.

## 핵심 발견 5개

1. **원본의 최종 장식 단계를 nearest-outside 반복과 동일시하면 안 된다.** [원문](https://www.iaacblog.com/programs/mesh-subdivision/)의 `DESIGN_MANDELROT + SUBDIVISION`은 Mandelbrot-derived column에 서로 다른 subdivision을 적용하고 추가 attractor curves를 넣었다고 설명한다. [도판 6](https://www.iaacblog.com/wp-content/uploads/2020/12/python_presentationfinal6.png)~[8](https://www.iaacblog.com/wp-content/uploads/2020/12/python_presentationfinal8.png)은 `MANDELBROT ATTRACTORS + 1 LEVEL SUBDIVISION`, [도판 9](https://www.iaacblog.com/wp-content/uploads/2020/12/python_presentationfinal9.png)는 `+2 LEVELS SUBDIVISION`이라고 표시한다. **확인:** 파생 초기 매스와 후속 장식 연산이 구별된다. **미확인:** nearest-outside와 후속 subdivision의 정확한 연결 순서·공식·가중치.

2. **같은 수업의 DragonSkin은 기존 정점과 새 중심점을 서로 다른 offset으로 이동한다.** [본문](https://www.iaacblog.com/programs/dragonskin-python-for-grasshopper-mesh-subdivision/)과 [개념 도식](https://www.iaacblog.com/wp-content/uploads/2020/12/group-2_final-python-17.jpg)은 `Move Vertices by Offset Depth 01` → edge midpoint/quad subdivision → `Move Center Vertex by Offset Depth 02`를 보인다. [정의 도식](https://www.iaacblog.com/wp-content/uploads/2020/12/group-2_final-python-19.jpg)은 normals, closest attractors, attractor range와 scale values를 명시한다. **시사점:** 기존 정점의 큰 형상과 새 중심점의 작은 변화를 동일한 nearest-target 규칙으로 취급할 필요가 없다. **미확인:** 원본 Mandelbrot 프로젝트가 이 코드를 그대로 사용했는지.

3. **실제로 읽을 수 있는 같은 교수 수업의 Python 코드는 nearest-point 투영 대신 법선 방향 offset을 쓴다.** [L-Systems 페이지](https://www.iaacblog.com/programs/l-systems-python/)의 [공개 코드 이미지](https://www.iaacblog.com/wp-content/uploads/2021/12/e59bbee7898712.png)는 quad의 중점·중심점 생성, 기존 정점 및 새 중심점의 법선 방향 offset, closest-curve distance/range를 사용하는 `attractorValue`를 보인다. 작은 글자의 정확한 상수는 복원하지 않았다. **확인:** 표면의 현재 방향과 곡선과의 거리가 변위를 제어하는 실제 코드 계열이 공개되어 있다. **미확인:** 원본 프로젝트와 동일 함수인지, 삼각형 분기·접합 처리가 원본과 같은지.

4. **원본도 triangular / frame-and-void / quad subdivision을 시험했다.** 사용자가 제공한 원본 Code 흐름도를 [공개 원본 이미지](https://www.iaacblog.com/wp-content/uploads/2020/12/group-4_python-presentation1.png)와 직접 대조해 확인했다. 최종 상자에 세 계열 시험을 명시한다. 따라서 앞서 기록했던 ‘원본에서 frame/void 사용 근거를 찾지 못했다’는 판단은 수정한다. **확인:** 원본 프로젝트의 시험 범위에 frame/void가 포함된다. **미확인:** 어떤 최종 컬럼에 어느 계열과 조합이 적용되었는지. 별도 [Metamorphic Pavilion 의사코드](https://www.iaacblog.com/wp-content/uploads/2021/12/pseudo-code-2.jpg)는 frame을 offset face와 원래 정점 사이의 연결로 설명하지만, 이 후속 프로젝트의 정확한 코드를 원본에 소급 적용하지 않는다.

5. **이번 한계에 관한 기술적 추론:** 독립적인 nearest-outside 격자 목표는 인접 정점에 다른 목표가 선택될 때 짧은 파장의 요철을 만든다. 격자 간격만 줄여도 원래 형상장 자체가 고주파이면 큰 접힘을 새로 만드는 연산으로 바뀌지 않는다. 공개 자료에서 가장 유력한 빠진 층은 ‘Mandelbrot 초기 형상 뒤에 붙는, 기존/새 정점 역할과 방향을 구분한 attractor-controlled subdivision’이다. 이는 현재 구현과 공개 자료를 비교한 **추론**이며 원본 공식을 복원했다는 뜻은 아니다. 큰 접힘의 인접 변위를 연계하는 시험과, 기존/새 정점 offset을 나누는 최소 비교가 합리적이다. 둘 다 실패하면 반복 수 증가로 포장하지 말아야 한다.

## 확인하지 못한 것

- 원본의 정확한 3D Mandelbrot 식, Z 보정, 곡선 거리의 매핑 상수, weld/normal 공유 처리.
- 원본에 Catmull–Clark 또는 Doo–Sabin이 사용되었다는 명시적 근거.
- 원본의 자기교차 억제·제작 가능성 검증.
- 낮은 해상도 레이블의 숫자. 숫자를 추정 복원해 실험값이라고 표기하지 않았다.

이번에 직접 읽은 공개 이미지의 로컬 사본: `C:/Users/Public/Documents/ESTsoft/CreatorTemp/iaac_source_follow/`. 이것은 임시 연구 자료이며 실험 출력이나 원본 코드로 취급하지 않는다.

## +1 / +2 도판 추가 대조

- 도판 9의 첫 컬럼 상단에서 `u:20`, `v:20`을 읽을 수 있다. u/v의 정확한 입력 정의는 공개 도판에서 확인하지 못했다. 원본 입력에도 별도 해상도 계열 변수가 있다는 단서이며, 20×20급 입력 비교의 근거로 참고할 수 있다. 곧바로 원본이 400 faces였다고 단정하지 않는다.
- 도판 6~9는 고정 입력과 고정 계수로 이어지는 세대 진행표가 아니다. n 값, 곡선 위치와 모양, 아래의 `offsetHeight`, `attrVal`, `moveVal`, `attrCrvNr`가 함께 바뀐다. 특히 도판 6의 수평 원형 곡선과 7~8의 높이 방향 굴곡 곡선은 큰 관계를 유도할 수 있는 별도 제어다. 이들 변수의 정확한 공식·부호 convention·연산 순서는 미확인이다. 도판의 차이를 subdivision 횟수 하나의 효과로 귀속하지 않는다.
- 공개 L-Systems 코드의 식은 기존 정점에 `normal * offset * attractorValue(point)`, 새 중심점에도 `face normal * offset * attractorValue(centre)` 형태를 보인다. 이 보이는 이동식에는 supporting-edge radius나 mesh-local edge length를 곱하는 항이 없다. 재귀 호출의 offset 인자 뒤 작은 연산 기호·숫자는 확실히 읽히지 않아, 원본이 고정 world-unit offset을 세대마다 유지한다고 주장할 수 없다. CHESHIRE의 `support_radius * gain * decay`는 추가 선택이며 원본에서 확인된 필수 조건이 아니다.
- 도판 6의 일부 안도 첫 subdivision에서 얕고 조밀한 요철을 이미 보인다. 따라서 ‘IAAC는 모든 후보에서 큰 접힘이 단계마다 성장하고 잔요철이 늦게 생긴다’는 일반화도 피한다. 우리가 추적할 대상은 선별된 깊은 골·곡선 제어·정점 역할의 관계이지, 공개 카탈로그 전체의 일률적인 성공이 아니다.

## 사용자 제공 원본 도식으로 수정한 판단

- 위 4번을 원본 Code 흐름도에 맞춰 갱신했다. 공개 URL의 1024×576 이미지를 직접 읽었으며, 추가 source 탐색은 하지 않았다.
- 원본의 [nearest-outside 의사코드](https://www.iaacblog.com/wp-content/uploads/2020/12/group-4_python-presentation2.png)와 [inside/outside 방사 이동 의사코드](https://www.iaacblog.com/wp-content/uploads/2020/12/group-4_python-presentation4.png)는 매 cycle에서 형상장 판정을 다시 적용하는 반복을 나타낸다. ‘초기 형상장 1회 + 이후 normal offset만’은 CHESHIRE의 분리 비교이며, 원본 통합 반복의 재현으로 표기하면 안 된다.
- 현재 M1+2 role 조합은 초기 field-derived mass 뒤 normal-offset 영향을 분리하기 위한 부분 조합이다. 역할별 offset과 매 cycle field 판정을 함께 사용하는 FULL_LOOP는 더 직접적인 통합 비교가 되지만, 원본의 계수·순서·subdivision 종류까지 복원했다는 뜻은 아니다.
