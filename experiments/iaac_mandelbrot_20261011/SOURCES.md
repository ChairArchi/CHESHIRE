# 공개 자료와 재구성 범위

기준 자료는 IAAC의 [Mesh Subdivision](https://www.iaacblog.com/programs/mesh-subdivision/), Stefana Zapuc·Hanna Lepperod·Léa Garguet-Duport, 2020이다. 원본 실행 코드·정확한 수식·이동량은 확인하지 못했다.

공개 자료에서 직접 확인한 순서는 다음과 같다.

- [의사코드 A](https://www.iaacblog.com/wp-content/uploads/2020/12/group-4_python-presentation4.png): 면 분할 → 좌표 검사 → Z 범위 조정 → 영역 내부는 중심에서 멀어지고 외부는 중심으로 이동 → 면 생성 → 반복.
- [의사코드 B](https://www.iaacblog.com/wp-content/uploads/2020/12/group-4_python-presentation2.png): 기존 면 정점과 분할로 생긴 중간 정점 검사 → 3D 영역 밖의 가장 가까운 점 탐색 → Z 조정 → 내부 정점을 해당 점으로 이동 → 면 생성.
- [구성도](https://www.iaacblog.com/wp-content/uploads/2020/12/group-4_python-presentation1.png): 점군에서 프랙탈 영역을 제외한 공간, 여러 프랙탈 볼륨, 변수 변경, 여러 subdivision 방식, 추가 attractor를 다룬다.
- [세대 비교](https://www.iaacblog.com/wp-content/uploads/2020/12/pres113.png): 큰 형태가 있는 초기 출력 이후 세부 형상이 증가한다. 위쪽 메시 출력과 아래쪽 Catmull–Clark 처리 결과가 구별된다. 이 이미지가 단순 원통에서의 모든 중간 단계를 공개한 것은 아니다.

공개 슬라이드의 `n`, `Mandelbrot level`, `center`, 이동 깊이의 정확한 코드상 의미는 확인되지 않았다. 특히 볼륨 번호를 subdivision 세대 번호로 단정하지 않았다. 기둥의 요철, 전체 치수, 카메라를 정확하게 복제했다고 주장하지 않는다.

## 부족한 부분을 보완한 자료

1. Daniel White, [Mandelbulb](https://www.skytopia.com/project/fractal/mandelbulb.html): 구면좌표를 통한 3D power map과 높은 지수에서 발달하는 형상. 2D 복소수 Mandelbrot의 유일한 3D 확장이라는 주장은 하지 않는다.
2. Coding Train, [Challenge 168 / Mandelbulb](https://thecodingtrain.com/challenges/168-the-mandelbulb) 및 [점군 구현](https://github.com/CodingTrain/Coding-Challenges/tree/main/168_Mandelbulb/Processing/MandelBulb_Cloud): 정규 격자, 구면좌표 power, 유한 반복 탈출 판정을 보완했다.
3. [Mandelbulber 공식 Mandelbulb 구현](https://github.com/buddhi1980/mandelbulber2/blob/master/mandelbulber2/formula/definition/fractal_mandelbulb.cpp): 공개된 다른 구면좌표 convention과 power 제어를 대조했다. 해당 프로젝트의 소스 코드를 CHESHIRE에 복사하거나 설치하지 않았다.
4. Emma Fogarasi·Oleg Fryazinov, [3D Printing Hypercomplex Fractals, Hyperseeing 2022, pp.47–56, 부록 p.57](https://people.tamu.edu/~ergun/hyperseeing/2022/journal-sm.pdf#page=47): 유한한 볼륨 근사와 Houdini의 수식 구현을 확인했다. 논문의 kaleidoscope, 제작 절차와 제작 가능성 주장은 이번 실험에 이전하지 않았다.

## 이번 구현에서 명시적으로 선택한 값

`z0=0`, `z(k+1)=spherical_power(z(k),p)+c`, 반복 18회, 탈출 반경 4. `p=5,6`인 두 볼륨의 합집합을 사용했다. 각 볼륨의 중심 Z는 2.5, 7.5, 단면 scale은 1.6, Z scale은 2.8이다. 이는 IAAC의 복구된 설정이 아니다.

밖의 점군은 65×65×161 격자에서 직접 판정했다. 두 볼륨 모두의 밖에 있는 점만 남겼다. 최근접 탐색은 이 유한 격자에 대해서만 정확하다. 유한 반복에서 탈출하지 않았다는 사실은 무한 집합의 내부라는 증명이 아니다.

NEAREST는 내부 정점을 가장 가까운 외부 점까지 거리의 85%만 이동한다. 동일 격자점으로 정점들이 즉시 합쳐지는 것을 피하기 위한 공개되지 않은 보완값이다. SIGN은 원통 축을 중심으로 해석해 세대별 0.36/0.20/0.11의 부호 있는 반지름 이동을 적용한다. 이 `center` 해석은 추정이다.

좌우 대칭은 한쪽 필드와 메시를 계산해 반사 생성한다. 대칭면 위 정점의 최근접 탐색은 그 평면의 외부 점군에 한정한다. 좌표 평균화는 하지 않는다. 원시 성장에는 CC 기하 배치를 적용하지 않으며, 별도 CC 비교 메시만 한 번의 실제 neutral CC subdivision을 사용한다. 추가 smoothing은 없다.

아치 제약은 사용자 후속 지시에 따라 해제했다. 앞선 게이트 시험은 보존하고, 구현 판단은 곧은 기둥의 공개 단계 비교를 우선한다.

## 추가 확인: 사용자가 제시한 접힌 매스

첨부한 매스는 [pres125 도판](https://www.iaacblog.com/wp-content/uploads/2020/12/pres125.png)의 맨 왼쪽 아래, **LOOP 1 + CATMULL-CLARK** 결과에 해당한다. 위에는 같은 LOOP 1의 각진 메시가 있다. 따라서 이것을 공개된 G0 입력이라고 부르면 안 된다. 이 자료만으로 원통에서 첫 루프가 저렇게 변한 것인지, 이미 접힌 입력이 있었는지 결정할 수 없다. 공개 도식은 입력 메시와 프랙탈 공간을 별도 대상으로 다루지만, 정확한 입력 좌표는 회수되지 않았다.

방향별로 다른 접힘과 이웃 마디의 침범은 이미지에 대한 조형적 해석이다. 원본 메시가 없어 자기교차, 곡률, 물리적 종이 접힘 가능성을 판정하지 않았다. IAAC가 origami 알고리즘을 사용했다는 근거도 확인하지 못했다.

## 관련 origami 원리와 실제 공개 구현

- Demaine·Demaine·Koschitz·Tachi, [Curved Crease Folding: a Review on Art, Design and Mathematics](https://erikdemaine.org/papers/CurvedCrease_IASS2011/paper.pdf), 2011. 곡선 접힘은 접힌 선과 면의 굽힘이 결합된다. Huffman의 cusp column, 반사 구성, 이산 메시 최적화가 관련 있다. CHESHIRE 형상이 자동으로 가전개면이라는 뜻은 아니다.
- DeSimone·Teresi, [Mechanics of curved crease origami ... cross-talk between multiple folds](https://arxiv.org/abs/2412.18265), 2024. 초록에서 여러 접힘의 기계적 결합을 확인했다. 사용자 지적과의 관련성은 유추이며, IAAC 방법의 증거가 아니다.
- Tachi, [Freeform Origami Tessellations by Generalizing Resch's Patterns](https://origami.c.u-tokyo.ac.jp/~tachi/cg/FreeformOrigamiTessellationsTachi2013ASME.pdf), 2013. 전개 가능성 및 국소 충돌 제약을 다룬다. 전역 충돌을 자동으로 모두 없앤다는 보장은 아니다. 각진 tuck 구조는 이번 유기적 매스의 직접 출발점으로 우선하지 않았다.
- [OrigamiSimulator](https://github.com/amandaghassaei/OrigamiSimulator): 공개 README를 검토했다. 평면 접힘 도안의 여러 접힘을 함께 풀고 곡선 접힘 전처리 및 OBJ/STL 내보내기를 지원한다. 설치하거나 CHESHIRE에 통합하지 않았다.
- Sasaki·Mitani, [Ruling-aware Triangulation 연구](https://www.cgg.cs.tsukuba.ac.jp/projects/2020/RulingAwareTriangulation/index.html), 2020/2021 및 [공개 구현](https://github.com/sasaki-trombone/RulingAwareTriangulation). 곡선 접힘선을 polyline으로 근사하고 면의 직선 모선 방향을 고려해 삼각분할한다. 실제 접힘선 기반 입력이 필요할 때 검토할 수 있다. 현재 일반 quad cage에 이 논문의 물리 제약을 적용했다고 주장하지 않는다.

## 재구성의 확장과 경계

`variation_study.py`의 36개 레시피는 지수·볼륨 수·단면·구면좌표 convention·기존 정점 이동·CC 순서를 비교한다. ray 제한 탐색과 회전 필드는 보완 해석으로 표시했다. 확장 격자는 81×81×161이고, 일부 시험만 반복 횟수가 4/8이다. 이는 IAAC 설정의 복구가 아니다.

`folded_seed.py`의 F01–F06은 직접 모델링한 균등 네 방향 접힘이다. 참조 이미지의 방향별 접힘 논리를 충족하지 못했다. `directional_cage.py`의 D01/D02는 서로 어긋난 X/Y 능선과 되접힘을 공유 표면에 배치한 별도 모델링 시험이다. 프랙탈 생성도, 물리적 origami 시뮬레이션도 아니다.

`input_field_test.py`는 동일 25×32 토폴로지에서 원통/방향별 접힘 입력 × 필드 OFF/ON의 네 경우를 비교한다. 두 번의 bilinear 분할 뒤 동일한 한 번의 CC를 별도 저장한다. 입력과 필드를 분리할 수 있는지 시험하며, IAAC의 과거 작업 순서를 입증하는 실험은 아니다.

후속 접힘 시험은 D04의 축방향 되접힘 강도, D05의 재료 좌표와 공간 방향 분리로 제한했다. D03의 전 항 각도 변경은 연속 표면을 재매개화했을 뿐 의도한 접힘 경로 이동을 만들지 못해 실패로 기록했다. 해당 원본 출력은 수정하지 않고 별도 `assessment.json`을 남겼다. D02/D04/D05의 필드 적용은 같은 파라미터와 연산 순서를 사용한다.

추가로 OrigamiSimulator의 실제 [`curvedFolding.js`](https://github.com/amandaghassaei/OrigamiSimulator/blob/main/js/curvedFolding.js)와 [`crease.js`](https://github.com/amandaghassaei/OrigamiSimulator/blob/main/js/crease.js)를 열어 보았다. 입력에 mountain/valley 구분과 목표 접힘각을 보존하는 별도 구조가 있다. CHESHIRE의 이번 D 계열에는 해당 접힘선/목표각 구조를 적용하지 않았다. 소스 검토와 실행·통합을 구분한다.
