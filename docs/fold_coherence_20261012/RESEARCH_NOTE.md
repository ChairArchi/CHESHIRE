# 근접 디테일의 생성 방식 — 공개 자료와 현재 구현

| 사례 | 공개 자료에서 확인되는 방식 | 이번 작업에 적용할 판단 |
|---|---|---|
| [Subdivided Columns](https://michael-hansmeyer.com/subdivided-columns.html) | 같은 subdivision 과정이 전체 형상부터 미세 조직까지 발달시킨다. 입력 부품의 태그에 따라 파라미터가 달라진다. 페이지는 정확한 전체 가중치와 세대별 레시피를 공개하지 않는다. | 여러 크기의 조직을 연결하는 지역별 반응이 중요하다. 셀별 돌출 강도나 반복 수 증가만으로 같은 질서를 얻는다는 근거는 없다. |
| [Digital Grotesque II](https://michael-hansmeyer.com/digital-grotesque-II.html) | genus를 바꾸는 subdivision을 명시하며 다중 skin, 분기와 여러 규모의 구멍을 만든다. | 현재 CHESHIRE의 표면 정점 이동과 다른 위상 변화다. 그 깊이를 이미 재현했다고 주장하지 않는다. 근접 디테일 문제를 이유로 이번에 새 위상 엔진을 만들지는 않는다. |
| [Mandelbulber 실제 메시 exporter](https://github.com/buddhi1980/mandelbulber2/blob/master/mandelbulber2/src/mesh_export.cpp) | 볼륨의 거리 임계값과 격자 해상도를 설정하고 Marching Cubes로 fractal 경계 메시를 추출한다. | 기존 메시 정점을 sampled nearest-outside target 쪽으로 일부 이동시키는 현재 방식과 다르다. Fractal 경계 자체의 디테일이 필요하다면 별도 비교 대상이다. |

[IAAC](https://www.iaacblog.com/programs/mesh-subdivision/)의 공개 pseudocode는 subdivision과 3D Mandelbrot 영역 판정·정점 이동의 결합을 보여준다. 이를 근거로 subdivision과 fractal이 양립하지 않는다고 판단하지 않는다. 다만 공개 도판만으로 전체 수식·가중치가 복원됐다고 말할 수 없다.

현재 CHESHIRE도 finite Mandelbulb field를 사용한다. Inside 판정 정점에 대해 sampled outside target 방향의 일부 이동을 적용하고 길이를 제한한다. 모든 최종 정점이나 삼각형이 fractal의 경계에 놓인다는 보장은 없다. 따라서 field를 더 강하게 쓰거나 escape 반복 수를 높이는 것만으로 근접 조형이 더 정돈된다는 근거도 없다.

기존 G2 저장 배열의 전후 렌더에서 반복 선반과 칸이 필드 이전 Task36 단계부터 보인다. 필드 이후에는 깊은 공동과 중앙 수렴이 더 명료해지는 이득도 있다. 필드 하나를 원인으로 지목하지 않는다. 셀 normal/stencil의 반복 배치, sampled target 전환, 보호 태그 경계가 미세 면 방향의 경쟁을 만들 수 있다는 설명은 기술적 추론이며 각각의 기여를 완전히 분리한 결과는 아니다.

이번 후속 LATE 조합은 G1–G2의 강한 셀 변형을 늦추고, G3부터 기존 연산을 작은 강도로 다시 활성화한다. 필드 이동에 주변 control-edge 평균 길이의 .25라는 추가 상한을 둔다. 좌표를 평균하거나 표면을 smoothing하는 방식은 아니다. 이 변경도 미적 성공은 실제 근접 렌더로 판단해야 한다.

사용자 추가 목표: 향후 주두 일부를 스툴 정도 규모로 FDM 출력할 가능성이 있어 G5–G6 근접 디테일을 목표로 한다. 이번에는 자를 위치·실물 치수·출력 조건을 확정하거나 제작용 모델을 보증하지 않는다. 자기교차는 기록하되 조형 탐색의 중단 기준으로 사용하지 않는다.
