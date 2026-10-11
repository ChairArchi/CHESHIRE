# 절단·반사 시험 중단 기록

**판정: 목표 이탈. 원래 기둥 개발의 후속안으로 채택하지 않는다.**

참고 논문의 절단·반사·접합을 기둥 전체에 적용하면서 하부를 버리고 상부를 비스듬히 반사했다. 추가 X/Y 반사로 Y자형 하부가 생겼다. 사용자의 목표인 기존 기둥의 깊은 접힘과 근접 디테일 발전을 전체 구성 변경으로 잘못 옮긴 시험이다. 논문은 참고 자료였으며 구현 의무가 없었다. 원래 후보와 모든 실패 결과는 보존한다.

| 결과 | 실제 메시 상태 | 결정 |
|---|---|---|
| LONG R1 | 폐합된 3개 연결체 | 실패, R2 미생성 |
| CROSS R1 | 폐합된 단일 연결체; genus 8; X/Y Boolean 반사 차집합 부피 0 | 실제 공동 변화는 있으나 Y자 버팀대 인상, 후속안 제외 |
| CROSS R2 | 폐합된 2개 연결체 | 실패, R3 미생성 |
| SEED CC1 / CROSS R1 CC1 | 단일 폐합체, 각각 genus 5 / 8 유지 | 엄격한 X/Y 대칭 검사 실패; 둥근 다면체 인상도 해결책 아님 |

SEED에는 반경 .22의 축 방향 구멍을 별도로 뚫었다. 이때 이미 genus가 0→5로 변했으며, 이를 반사 연산이 스스로 만든 공동으로 해석하지 않는다. Genus는 위상적 손잡이 수이며 눈에 보이는 개별 구멍 개수와 동일한 지표가 아니다.

실제 결과: `E:/CHESHIRE_DATA/structural_fold_20261012`. 각 폴더의 `geometry.npz`, `column.ply`, `generation.json` 및 `preview/`에 저장했다. raw 반사 결과도 별도 보존했다. CC는 Blender의 실제 Catmull–Clark 1회 적용이며 렌더 효과가 아니다. CC 결과는 면적 기준을 통과해도 대칭 검사를 실패하므로 대칭 후보로 부르지 않는다. 허용치는 바꾸지 않았다.

자기교차·두께·강도·제작 가능성은 미검증. Manifold의 NoError를 자기교차 없음으로 해석하지 않는다. 기존 quad chart와 태그를 Boolean 결과에 이전하지 않았다. Tissue, 프랙탈 필드, origami solver는 이 시험에 적용하지 않았다.

[첫 비교](images/first_step_comparison.png) / [R2 실패](images/cross_fork_progression.png) / [CC 진단](images/structural_finish_comparison.png). 새 시험 내 카메라는 동일하며 이전 기둥 렌더와는 전체 ortho scale이 다르다(14 대 12).

복귀 기준은 보존된 `E:/CHESHIRE_DATA/fold_coherence_20261012/CURVED/SPAN/G02`다. 이후 개발은 원래 깊은 골·방향별 접힘의 연속성에서 진행한다.
