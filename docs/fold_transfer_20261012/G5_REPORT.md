# CHESHIRE — G5의 작은 조직과 근접 질서

**G5에서 작은 조직은 더 가늘어졌고, 일반 정점의 고정을 풀면 과밀한 잔조직이 줄었다. 그러나 작은 접힘의 위계는 여전히 미해결이다.** 작은 면이 늘어나면 전체가 자동으로 부드러워진다는 가설은 부분적으로만 지지된다. 큰 골과 팽창부는 시각적으로 유지됐다.

[G4 → G5](images/g5_progression.png) · [G5 정면·사선·측면](images/g5_views.png) · [재분할 / 되접힘 / 형상장 분리 확대](images/g5_detail.png) · [STENCIL 확대 대조](images/g5_stencil_comparison.png) · [두 입력 STENCIL 정면](images/g5_stencil_fronts.png)

최신 원인 분리: [고정 조건만 바꾼 확대 비교](images/g5_pin_comparison.png) · [TAG_ONLY 두 입력의 3뷰](images/g5_tag_only_views.png)

두 실제 입력 모두 RETURN_ONLY G4에서 출발했다. 앞서 조형적 우위가 약했던 PROTECTED G4를 계속 누적하지 않았다. 동일한 G5 규칙을 적용했고, 모든 G5는 1,638,400개 삼각형으로 G4의 네 배다. 별도 smoothing은 없다.

| 상태 | 연산 | 실제 렌더에서 확인한 것 |
|---|---|---|
| REFINED_ONLY | SPAN의 기존 VF 표면을 변형 없이 재분할 | 큰 판면·쐐기·실루엣은 거의 그대로다. 분할 수 증가가 곡면 성숙을 뜻하지 않는다. |
| RETURN_ONLY | 두 입력에 같은 작은 PCHIP 자식 되접힘 2개 | 국소 변형은 생겼지만 현재 whole/meso 뷰에서 새 형태 단계로 강하게 읽히지는 않는다. |
| PROTECTED | 같은 RETURN_ONLY에 기존 형상장 1회, 이전 정점·태그 보호 | 중앙 spine과 일부 띠가 더 가늘고 촘촘해진다. 큰 골은 남지만 lace/crust가 주요 접힘과 경쟁한다. |
| STENCIL | G4에서 기존 Task36의 부모 셀 계보 변형만 국소 적용. 새 return·형상장·normal 돌출 없음 | 큰 골과 어깨는 남지만 REFINED_ONLY 대비 새로운 작은 접힘의 연결은 뚜렷하지 않다. 이번 설정의 조형적 효과는 약하다. |
| TAG_ONLY | PROTECTED G5와 정확히 같은 필드 전 좌표·raw 변위·태그에서, 모든 이전 정점을 고정하는 조건만 해제 | 중앙 띠와 아래 어깨의 잔가시·lace가 줄고 큰 골의 연결이 더 읽힌다. 측면 격자와 일부 넓은 판면은 남는다. 부분 개선으로 보존한다. |

STENCIL도 동일 규칙으로 두 입력에 적용했다. 최대 이동은 SPAN `0.01347`, COUNTER `0.01239` 모델 단위이며, 두 안 모두 기존 control과 보호 중심 7,230개의 이동은 0이다. 작은 적용 한 번으로 stencil 원리 전체의 유효성을 부정하지 않는다. REF↔STENCIL은 stencil의 효과를 분리하지만, FIELD↔STENCIL은 새 return 유무까지 달라 단일 변수 비교가 아니다.

사용자가 지적한 모호한 접힘을 [같은 카메라의 G3까지 되짚었다](images/g5_fold_lineage.png). **정면 팽창부 외곽의 리브가 짧은 골들로 갈라지는 부분, 측면 허리의 세로 골을 가로지르는 반복 선반은 이미 G3에 있다.** G4와 G5 재분할·STENCIL은 이를 유지한다. G5 FIELD는 중앙 능선 양옆과 아래 어깨에 촘촘한 조직을 추가해 별도의 혼잡함을 만든다. 반면 깊은 두 공동과 중앙 V자 경계는 날카로워도 방향 관계가 명료하다. 이는 시각적 판독이며 특정 자기교차가 그 원인임을 입증한 것은 아니다.

TAG_ONLY는 새 subdivision·return·필드 질의 없이 저장된 G5 변위를 재조합했다. SPAN 30,401 / COUNTER 17,845개 이전 control이 움직였고, 새 점의 적용 변위는 기존안과 차이 0이다. 보호 중심 9,350개는 이동 0이다. 같은 이웃 edge 표본에서 이동 차이가 입력 길이를 넘는 비율은 약 55→19% / 45→18%로 줄었다. 이는 일반 정점 고정의 영향을 분리한 관찰이다. 그러나 실제 edge 길이도 일부 수축하므로 이동 차이 감소만으로 형상 성숙이나 평탄화 방지를 입증하지 않는다. [진단 정의와 표본](technical/g5_pin_diagnosis.json) · [국소 수축 관찰](technical/g5_pin_edge_shape.json).

**초기 통제가 과했다는 가설은 아직 미확인이다.** G1–G3 형상장은 일반 이전 정점 고정을 적용하지 않았으므로, G3부터 있던 모호함을 후기 보호 규칙만으로 설명할 수 없다. 현재는 미리 정한 큰 return, 부모 셀의 subdivision, 프랙탈 형상장 이동이 결합돼 있다. 부모 return에서 작은 return 설정을 유도하지만, 서로 다른 규모의 접힘이 한 방향 관계로 성장한다는 조형적 성과는 약하다. 프랙탈 형상장을 썼다는 사실과 접힘 자체의 재귀적 위계 확보를 구분한다.

판단의 중심을 날카로움 자체에서 **가까이에서도 읽히는 생성 규칙**으로 옮겼다. 공식 [Subdivided Columns 9배 확대](https://michael-hansmeyer.com/images/subdivided-columns/subdivided-column-8-m.jpg)에도 날카로운 삼각 면은 많다. 내 시각적 해석으로는 작은 셀의 방향·간격·크기가 골과 어깨의 큰 흐름에 연결되는 점이 중요하다. 작가의 [설명](https://michael-hansmeyer.com/subdivided-columns.html)도 전체 곡률부터 국소 형상과 미세 구조까지의 연속성을 강조한다. 단순한 동일 모듈 반복을 새 목표로 삼지는 않는다.

[Digital Grotesque II의 근접 형상](https://michael-hansmeyer.com/images/digital-grotesque-II/digital-grotesque-II-13-m.jpg)은 하위 장식과 큰 부재가 연결되고 빈 공간도 층지게 발달한다. [공식 설명](https://michael-hansmeyer.com/digital-grotesque-II.html)의 topology 전이는 현재의 폐합 표면 재분할·변위와 다른 능력이다. 이번 G5에서 그것까지 확보했다고 주장하지 않는다. 현재의 우선 과제는 큰 접힘과 작은 셀 사이의 방향·규모 관계다.

두 PROTECTED와 두 TAG_ONLY G5에 핵심 검사를 적용했다. X/Y 반사 삼각형 집합 대응, 오차 `<4.25e-15`, 연결체 1개, 폐합, boundary/nonmanifold edge 0, 최소 면적 `>1e-12`를 확인했다. **네 안 모두 자기교차가 확인됐다.** 교차 총량이나 증감 비교는 아니며 두께·구조·제작 가능성은 미검증이다. 재분할 대조군·필드 전 중간 상태·STENCIL은 빠른 검사·렌더까지만 수행했으며 자기교차는 미검증이다. STENCIL도 X/Y 반사 대응, 폐합, 연결체 1개, 기존 면적 기준을 통과했다.

G5는 subdivision 다섯 번째 단계다. 이번 부모 G4는 형상장 3회였으므로 G5 RETURN_ONLY도 3회, PROTECTED와 TAG_ONLY는 4회다. TAG_ONLY는 그 네 번째 형상장의 고정 조건 대조이며 다섯 번째 필드 적용이 아니다. 형상장 내부 escape 반복은 18이며 이 숫자들을 접는 횟수 하나로 합치지 않는다. 원본과 모든 중간 상태는 보존했다.

**결론은 부분 채택이다.** TAG_ONLY는 일반 정점 고정의 부작용을 줄인 유망한 비교 자산이다. G3/G4 RETURN_ONLY는 큰 접힘의 명료함을 비교하는 기준으로 남기며 모든 안을 보존한다. STENCIL은 현재 설정에서 병목을 해결하지 못했다. G6를 누적하지 않는다. 다음 시험은 ① 중요한 골만 보호하고 나머지 변형을 허용하는 범위, ② 새 점들의 이동이 여러 셀을 가로질러 하나의 연속된 골을 이루는 관계 중 하나를 분리해 다루는 것이 타당하다. 전체 smoothing이나 잔조직 증폭으로 해결했다고 간주하지 않는다.

[실제 파일 위치](G5_INDEX.json) · [PROTECTED 핵심 검사](technical/g5_core_validation.json) · [TAG_ONLY 핵심 검사](technical/g5_tag_only_core_validation.json) · [세대 기록](technical/g5_summary.json). G5 실행 중 동명 모듈 충돌은 고쳤고, 최초에 저장된 유효 재분할 대조군은 그대로 보존했다. 해당 실행 이력은 INDEX에 남겼다.
