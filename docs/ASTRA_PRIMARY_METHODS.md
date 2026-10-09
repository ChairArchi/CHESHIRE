# ASTRA — 원논문 대조와 독립 primal 실험

2026-10-10. 기존 상세 연구는 [인수인계](ASTRA_HANDOFF.md)와 [연구 계보](astra/TASK_LINEAGE.md)를 따른다. 이 문서는 독립 조사에서 확인한 구현 차이와 새 소형 실험만 기록한다. 원작의 제작 소스·선정 레시피는 확보되지 않았다.

## 1. 원문에서 확인한 범위

| 1차 자료 | 확인한 기술 | 이번 구현과 구분 |
| --- | --- | --- |
| [Design by Subdivision, 2010](https://archive.bridgesmathart.org/2010/bridges2010-167.pdf), pp.168–171 | 가중 CC, V/E/F 계보, 국소·외부 공간 가중치 | 현행 Task29의 같은 단계 face coupling은 이미 교정됐다. 새 발견으로 반복하지 않는다. |
| [Subdivision Beyond Smoothness, 2010](https://doi.org/10.2312/COMPAESTH/COMPAESTH10/075-081), pp.76–78 | 가중 DS, F/E/V 기원별 face 제어, 세대별 계수와 CC/DS 조합 | 일반 DS만으로 genus가 바뀌지는 않는다. 문헌의 vertex fusion·valence 제한은 별도 위상 변경이다. |
| [From Mesh to Ornament, 2010](https://doi.org/10.52842/conf.ecaade.2010.285), pp.287–291 | 균일 입력+외부장, 분화된 입력+내재 특징의 비교 | 초기 균일 메시에는 구분할 내재 특징이 부족할 수 있다. 외부 공간 제어를 곧바로 미리 만든 최종 실루엣과 동일시하지 않는다. |
| [Subdivided Columns 공식 설명](https://michael-hansmeyer.com/subdivided-columns) | Doric 기둥의 비례·기둥머리·기단·fluting·entasis와 태그를 가진 입력 | 정사각 중립 carrier는 CHESHIRE의 진단 조건이며 원작 전체의 필수 입력 조건이 아니다. |
| [Digital Grotesque I](https://michael-hansmeyer.com/digital-grotesque-I) / [II](https://michael-hansmeyer.com/digital-grotesque-II) | 결정적 생성·선정 과정; II의 genus 변경, 겹친 표면·분기·공극 | 원작의 전체 실행 알고리즘이 공개됐다는 뜻은 아니다. 고정 위상 표면 접힘으로 II의 위상 특성까지 달성했다고 주장할 수 없다. |

『From Mesh to Ornament』는 분화된 입력이 초기 셀에 장식을 가두어 반복적인 조각처럼 보일 수 있다는 문제도 다룬다. 반대로 Figure 4는 늘인 큐브와 기단에 수직으로 배치한 네 가중치 집합을 사용한다. 입력의 분화와 제어장의 분화는 각각 비교할 변수다. 공식 proceedings 전체 fetch는 실패했고, [원문 전사 mirror](https://id.scribd.com/document/383049043/ecaade2010-lowres)에서 해당 문단을 확인했다. 수식은 손실된 전사 대신 아래 Bridges·Eurographics 원본과 대조했다.

## 2. 식과 평가 순서

Bridges p.168 Eq.1–4의 핵심은 다음과 같다. `Rbar`는 원래 edge 양 끝점의 중점 평균, `Fbar`는 같은 단계에서 완성된 face 점 평균이다.

```text
F = mean(P) + nf*wf
E = ((Fa+Fb)*(1+w1)+(Pa+Pb)*(1-w1))/4 + ne*we
V = (Fbar*(1+w2)+Rbar*(2-w2)+(d-3)*P)/d + np*wp
Fnext = ((Vprev*(1+w3)+Fprev*(1-w3))*(1+w4)
         +(Eprev1+Eprev2)*(1-w4))/4 + nf*wf
```

[현행 reference 구현](../src/cheshire/reference_subdivision.py)은 완성된 새 face를 E와 V에 사용하며, V에는 변형된 새 edge 점을 다시 넣지 않는다. Edge normal은 인접 단위 face normal의 산술평균이다. 원문은 길이를 incident face 규모로 조절하지만 정확한 스칼라 규약·vertex normal 정규화·물리적 비평면 quad 삼각화를 모두 고정하지 않는다. Eq.10 attraction 완료 순서도 실행 코드로 제공되지 않았다.

Eurographics p.77 Eq.5–6의 DS corner 식은 다음과 같다.

```text
quad: ((2.25+2*w)*P0+(.75-w)*(P1+P3)+.25*P2)/4 + nf*wf
tri:  (2/3)*(1+w/2)*P0 + (1-w)*(P1+P2)/6 + nf*wf
```

이 식과 F/E/V face 기원은 [기존 DS 구현](../src/cheshire/dual_subdivision.py)에 이미 있다. 새 dual 연구의 국소 제어는 독립적인 추가 규칙이다. DS를 전혀 시험하지 않았다는 결론은 잘못이다.

## 3. 독립 조사에서 드러난 차이

- **평균화 대조는 이미 있다.** Task36 J01/J02 및 `SAME_INPUT_COMPONENTS`는 full/제거 CC 평균화를 비교했다. 평균화 재도입 자체를 미시도 해법으로 부르지 않는다. U01/W03의 선택된 식은 interpolation에 stencil·normal 차분을 더하는 별도 연산이다.
- **Planarity 규약이 다르다.** Bridges p.170은 한 점에서 다른 세 점 평면까지의 거리를 그 세 점의 삼각형 둘레로 나눈다. 기존 `fields()`는 전체 quad 둘레를 쓰고 하나의 corner만 선택한다. 비평면 quad에서는 순환 인덱싱에 따라 특징값이 달라질 수 있다. 새 primal은 네 corner 측정의 최댓값을 사용한다. 이는 대칭적인 확장 규약이며 원문과 완전히 같은 식이라고 부르지 않는다.
- **Motif 정보가 빈약할 수 있다.** 현행 `u_map`의 `(degree,degree)`는 동일 valence라도 다른 연결 배치를 구별하지 않는다. 규칙적인 닫힌 CC 영역에서 `u`가 같으면 Eq.10은 `(1-4*w6*u)*F + 4*w6*u*C`로 축약된다. 이동은 생기지만 그 사실만으로 지역 분화가 생기지는 않는다.
- **특징의 평균화와 기하 평균화를 구별한다.** Face 특징을 vertex로 모았다가 다시 face/edge로 보내는 과정도 차이를 약화할 수 있다. 새 실험은 face 제어를 직접 계산하고 공유 edge/vertex에서 필요한 평균만 사용한다. 이 선택의 보편적 우월성은 검증되지 않았다.

## 4. 새 primal 규칙과 실제 비교

코드: [astra_primal.py](../src/cheshire/astra_primal.py), [실행기](../tools/astra_primal_probe.py), [테스트](../tests/test_astra_primal.py).

기본은 분해하지 않은 reference placement이며, 선택적으로 물리적 선형 interpolation과 convex blend할 수 있다. 실험에서는 blend=1을 사용했다. 현재 메시의 edge 길이비, 순환 인덱싱에 불변인 planarity, 인접 normal 관계를 읽는다. 외부장은 초기 높이 범위에서 정의한 Z 선형값에 tanh를 적용한 **명시적인 외부 제어**다. 출력 좌표나 목표 실루엣을 지정하지 않는다. `source=rest`는 특징 관측만 고정하며, 실제 placement와 normal은 현재 메시를 사용한다.

후속 방향 규칙은 다음처럼 새로 설계했다. `bend`는 face에 접한 edge들의 `1-dot(normal_a,normal_b)` 평균이다.

```text
score = log(aspect) - 3*planarity - .75*bend - .2
w4 = L*tanh(2*score)
w3 = -.8*tanh(log(aspect))
```

양의 w4는 V/F 대각, 음의 w4는 E/E 쌍을 더 반영한다. Support 옵션은 현재 face 중심에서 supporting edge line까지의 최소거리로 normal 변위 길이를 정한다. 원문의 mean-edge 길이와 구별되며, 비평면 polygon의 정확한 내재 반경이나 주곡률은 아니다. **특징→계수 함수, 상수, 경계 조건은 모두 이번 실험의 선택**이다.

모든 자료의 root는 `E:/CHESHIRE_DATA/astra_research/primal_probe/`다. 다음 표의 링크는 같은 카메라·flat shading으로 실제 저장 메시를 렌더한 비교다.

| 실험 / 실제 비교 이미지 | 결과와 해석 |
| --- | --- |
| [P01_FULL](E:/CHESHIRE_DATA/astra_research/primal_probe/P01_FULL/renders/comparison.png): 상수·내재·외부·결합·고정 × 기둥/큐브, 10회 | G4까지 상수/내재 기둥과 모든 큐브는 교차 0. 외부 기둥 G3 88건, 결합 G4 64건, 고정 G3 88건. 얕은 반복 주름과 상자 구성이 남았다. |
| [P02_CAP_ABLATION](E:/CHESHIRE_DATA/astra_research/primal_probe/P02_CAP_ABLATION/renders/comparison.png): 실패 기둥 3회 | 끝단 extrusion 억제와 Z 고정을 함께 제거했다. 결합 current는 G4 교차 0이나 높이가 약 3799로 줄었다. 외부/고정은 G4 64건. 경계 정책은 기여 요인이며 단일 원인은 아니다. |
| [P03_DIAGONAL](E:/CHESHIRE_DATA/astra_research/primal_probe/P03_DIAGONAL/renders/comparison.png): w4=.9→1.35, 4회 | Normal 증폭 없이 바꿨다. 내재 기둥·두 큐브 G5 교차 0, 상수 기둥 G5 240건. 잔주름 증가는 깊은 내부 접힘의 성과로 평가하지 않았다. |
| [R01_SIGNED_SUPPORT](E:/CHESHIRE_DATA/astra_research/primal_probe/R01_SIGNED_SUPPORT/renders/comparison.png): 방향 부호 × support 2×2+고정, 두 입력 10회 | Current 부호 기둥은 support 유무 모두 G4에서 검사 상한 256건에 도달했다. 고정은 G5 통과. 모든 큐브는 G5 통과. 실제 형상 반응이 안정성과 동일하지 않다. |
| [R02_CONVEX_STENCIL](E:/CHESHIRE_DATA/astra_research/primal_probe/R02_CONVEX_STENCIL/renders/comparison.png): L=1.4→1, current/rest × 두 입력, 4회 | Eq.4 face 계수를 모두 비음수로 제한한 대조. 네 후보 G5 교차 0. Current 기둥의 w4 음/양 592/1968, 고정 512/2048로 다음 방향 판단이 실제 달라졌다. 곡면과 얕은 주름이 우세하여 깊은 다층 접힘 성공은 아니다. |

총 31개의 소형 실행이며 G5를 넘지 않았다. 그림에는 실패한 마지막 단계도 포함된다. **이미지 라벨만으로 유효 후보라고 판단하면 안 된다.** 각 root의 `summary.json`, 후보 `history.json`, 단계 `validation.json`을 함께 읽는다. `mesh.npz`가 native 물리 표면, `quad_state.npz`와 operator state가 다음 연산의 입력·계보다. 소스 복사본·SHA·레시피·G0부터 마지막 단계·렌더 manifest가 함께 있다.

신규 primal 테스트 **6개 통과**. 참조 식 일치, 특징의 순환/스케일 불변성, current/rest 차이, 반사 대칭, 두 옵션의 독립성을 검사했다. 옵션 추가 후 초기 P01 상수 기둥 G1–G4의 XYZ와 connectivity 배열이 저장값과 정확히 일치했다. 최초 부호 fixture는 높이 4000에서 양·음이 모두 나온다는 잘못된 가정을 했고 실패했다. 양쪽 부호를 시험하는 높이 8000 fixture로 명시적으로 바로잡았으며 실제 실험 입력이나 판정 기준은 바꾸지 않았다.

교차 검사는 기존 strict 검사와 positive interior interval 검사의 합집합이며 shared-vertex 쌍도 포함한다. 공면·접선·경계만의 접촉은 제외한다. 대칭 수치는 nearest-neighbor 진단이며 bijective topology 인증을 대신하지 않는다. 이 소형 경쟁에서 실제 단면 기반 깊이 인증이나 교환 OBJ 인증은 수행하지 않았다. 따라서 **기하 반응 근거는 확보했지만 조형 목표는 미달**이며, 추가 분할 수만 늘릴 후보로 추천하지 않는다.

## 5. MOLA 및 삼각 연결 변경의 출처 경계

[공개 Python MOLA 소스](https://raw.githubusercontent.com/dbt-ethz/mola/master/mesh_subdivision.py)의 `subdivide_mesh_catmull(values)`는 CC 점을 먼저 모두 계산하고 face-derived 점만 나중에 이동한다. 같은 단계의 extruded face를 E/V에 전달하는 reference 식과 다르다. [HDMolaGH](https://github.com/dbt-ethz/HDMolaGH)는 subdivision 조합과 면 특성 기반 필터를 제공하지만, 원작 DG의 복구된 제작 알고리즘이라는 근거는 없다.

별도 삼각 연결 변경 실험의 문헌 기준은 Kobbelt의 [√3-subdivision 공식 색인](https://vci.rwth-aachen.de/publications/2000/)과 [접근 가능한 공식 개별 페이지](https://www.graphics.rwth-aachen.de/publication/03138/)다. 원문은 3배 삼각형 분할 및 반복 후 원래 edge 방향을 바꾸는 연결 구조를 다룬다. 이번 실험이 그 **connectivity 방식**을 참고하더라도, 별도로 작성한 Laplacian relaxation을 원논문의 smoothing mask와 동일하다고 주장하지 않는다. 원문의 극한면 매끄러움 보장도 변형한 실험에 자동 승계되지 않는다.

기존 edge flip은 [공식 OpenMesh √3 소스 문서의 해당 단계](https://www.graphics.rwth-aachen.de/media/openmesh_static/Documentations/OpenMesh-7.0-Documentation/a00680_source.html)에서도 확인된다. 논문 PDF의 직접 fetch는 timeout이어서 원 smoothing 식을 이 문서에서 새로 전사하지 않았다.

## 6. 접근·라이선스·보존

- Bridges 원본과 Eurographics 원본은 `E:/CHESHIRE_DATA/research_archive/references/pdfs/`에 보존돼 있다. 이번 조사에서 Eurographics live PDF는 403, eCAADe 및 Mesh Grammars 전체 PDF fetch는 실패했다. 읽지 못한 상세식을 추정하지 않았다.
- 논문·작가 이미지의 공개 열람을 재배포 허가로 해석하지 않는다. 새 upstream 코드나 원작 이미지·PDF를 저장소에 반입하지 않았다.
- Python MOLA와 HDMolaGH의 열람한 root에서 명시적인 재배포 라이선스를 확인하지 못했고 LICENSE fetch도 실패했다. 이용·배포 조건은 기존 [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md)를 따른다.
- √3 공식 색인의 요청 URL은 이 조사에서 cache miss였으나 같은 기관의 기존 도메인 공식 페이지와 논문 색인은 접근됐다. OpenMesh/OpenFlipper 코드를 복사하거나 설치한 것은 아니다.
- 과거 소스·테스트·체크포인트는 변경하지 않았다. 현재 실험의 세부 기록과 실패를 다음 연구의 비교 근거로 남기며, 원작과 같은 알고리즘을 복원했다는 주장으로 바꾸지 않는다.
