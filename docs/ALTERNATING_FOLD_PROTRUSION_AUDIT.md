# Alternating Fold–Protrusion Growth — 정적 보존 감사

2026-10-10. **판정: NOT VERIFIED.** Task24·25 및 Astra/Freedom의 기존 코드, 실제 레시피, 저장 operator/계보와 기존 측정을 읽었다. 새 형상 생성·테스트·렌더·특징 탐색은 실행하지 않았다. 저장된 변위의 개수/크기 집계만 수행했다.

검증 대상은 **접힘이 만든 자식 영역 → 그 영역의 새 돌출 → 그 돌출의 새 접힘 → 다음 생성의 기반**이라는 연속 기하 과정이다. 연산 순서, topology의 parent–child, nonzero displacement만으로 성공이라고 판정하지 않는다.

## Task24: 순서와 자식면의 실제 후속 반응은 존재

원본 `385ec86c1f18ee1e2e0d61e2b32c524ceccfb683`, `experiment/task24-hero-design-sprint`.

| 실제 레시피 | 보존된 순서 | 직접 확인된 부분 증거 | 부족한 증거 |
|---|---|---|---|
| `studies/task24/recipes/H1.json` | mantle fold → Roof → cleft fold → 실제 Roof 자식의 frame/taper/frame/taper | S02 Roof 36 event, 144 자식면. S03에서 그 자식면을 source로 하는 face point 144개 중 108개에 추가 fold 변위가 1e-10보다 큼; 최대 121.33333333333354 원래 단위 | S01이 만든 특정 새 접힘 영역을 새 돌출의 출생 영역으로 식별하고, S03에서 그 돌출에 새 fold 특징이 생겼다는 직접 연결 없음. 마지막 taper 후 fold 단계도 없음 |
| `studies/task24/recipes/H2_R1.json` | crown fold → major TaperedExtrusion → branch fold → extrusion 측면의 secondary taper → 자식 장식 | S02 돌출 12 event, 60 자식면. S03의 해당 face point 60개 모두에 추가 fold 변위; 최대 140.874513955967 원래 단위 | 실제 재변위가 새 fold 발생을 뜻하지 않음. folded-child feature → protrusion feature → folded-protrusion feature의 연속 추적 없음. 뒤의 secondary taper에는 후속 fold 없음 |
| `studies/task24/recipes/H3_R3.json` | 두 큰 fold → depth extrusion / Roof / 자식 장식 | 최종 선언에서 두 큰 fold가 장식보다 먼저 실행됨 | 최종 R3는 돌출 뒤 재접힘 순환의 증거가 아님. 이전 R1/R2의 실패·순서 변경을 성공으로 소급하지 않음 |

저장 데이터는 `E:/CHESHIRE_DATA/task24/designs/{H1,H2_R1}/attempt_002/S02_operator.json.gz`와 `S03_operator.json.gz`다. S02 `events[].children[].id`를 S03 `operator.combined_fold.placement`의 `point_class='face'`, `source`에 정확히 연결하고 `additional_displacement`를 집계했다. 이는 reference crease CC에 더한 배치 항이며 전체 이동·접힘 깊이의 측정값이 아니다. 요약과 입력 해시는 [저장 감사 JSON](research_archive/ALTERNATING_SAVED_OPERATOR_AUDIT.json), [자산 해시 목록](research_archive/SELECTED_ASSET_MANIFEST.json)에 있다.

구현 참조의 행 번호는 이 문서 브랜치에 보존한 Task36 소스 기준이다. `examples/hero_design_sprint.py:302`의 fold 분기, `:339`의 event parent/계보와 네트워크 전달, `src/cheshire/crease_folding.py:92`의 support 가중 변위가 관련된다. `src/cheshire/crease_folding.py:106`은 `P_crease + alpha*(P_existing_sharp_weighted - P_standard_smooth)`를 기록한다. Task24 당시 구현은 위 원본 commit과 색인의 링크를 사용하며, 현재 runner의 후대 변경과 구분한다. 실제 수치 판정은 당시 저장 S02/S03 operator를 직접 읽은 결과다. MOLA가 만든 새 장식 edge의 crease 의미는 일반적으로 계승되지 않는다. [당시 결과와 계승 한계](TASK24_RESULTS.md).

## Task25: 큰 말림의 실제 조상과 continuation

원본 `b4000cf85bc0768821976bab4b454ca35b8ccca3`, `experiment/task25-generational-folding`.

[SOURCE_MAP](../studies/task25/SOURCE_MAP.md)은 BACKBONE_S01/S02 modified CC, S03 Taper, S04 standard CC, S05 InsetFrame에서 중앙 네 갈래 조직이 이미 나타남을 기록한다. H1 S01/S03은 이를 강화한다. 이 사실은 ‘말림이 전부 terminal 장식에서 발생했다’는 해석을 지지하지 않는다.

`H1_CURVATURE_G2`는 `H1_CONTROL_G1`의 실제 상태에서 새 중앙 support를 찾아 계속하며 wf/we/wp는 모두 0이다. 다른 CONVERGENCE/RENEWED/AMPLIFIED 대조는 기존 fold·오프셋의 효과를 구분한다. Task25 continuation은 `examples/generational_folding.py:154`의 `fold_state`를 호출하며, `src/cheshire/fold_continuation.py:48`에서 실제 parent의 history/signature를 전달한다. 새로운 protrusion event를 각 continuation 사이에 삽입하고 그 event의 새 특징을 다시 접는 순환을 검증한 실험은 아니다.

양의 C0 조상, event role과 branch signature는 구성 계보다. signed 영향계수, 부모 골의 공간적 내부 또는 새 fold 특징의 탄생을 자동 입증하지 않는다. 큰 말림 보존의 성과는 유지하되 핵심 가설의 입증으로 바꾸지 않는다.

## Astra / Freedom: 자식 반응·국소 골 연결과 교대 성장 가설을 구분

원본 Astra `0c4ec452518415d2fb12f724553e25d732c4c7c2`, Freedom `0ac8830c059193240babf49700a45241d18bb38b`. 공개 소스는 [Astra/Freedom 스냅샷](https://github.com/ChairArchi/CHESHIRE/tree/archive/astra-freedom-2026-10-10)이다.

- `legacy_probe_P03_LINEAGE_AUDIT.json`은 pocket→weighted CC→다음 pocket→weighted CC 등의 레시피와 실제 CAP/RIM 계보를 보존한다. 기존 `P03_LINEAGE_AUDIT/lineage_evidence/lineage.json`에서 Q02_CHILD_RESPONSE의 G4 pocket 560개 중 outward 528, inward 32 및 이전 G2 role 연관이 확인된다. **이전 접힘의 특정 자식 영역에서 생긴 돌출을 다음 fold까지 동일 특징으로 잇는 증거는 아니다.**
- `H00_POCKET_FOLD.json`은 Q02_CHILD_RESPONSE G4 뒤 current patch fold를 실행한다. pocket 뒤 fold의 실행 관계는 있지만, 요구한 연속 fold→protrusion→fold 특징의 직접 추적은 기록하지 않는다.
- `J02_OUTWARD.json`은 G4/G5/G6 domain 회전, `J09_BROAD.json`은 저장 J02 G6를 받아 G7 domain 회전을 실행한다. radius와 polarity 이름을 새 protrusion event의 증거로 사용하지 않는다.
- J09의 기존 `hierarchy/J09_FOUR_GENERATION_CHAIN_V2/evidence.json`은 같은 초기 부모·골의 G4–G7 국소 연결을 직접 기록한다. 실제 골의 이어짐은 인정한다. 다만 동일 domain 연산으로 생긴 골/crest의 변화에서 독립적인 돌출 발생과 그 돌출의 재접힘을 구분한 기록은 아니다. 자기교차가 있고 유한 단면의 성과다.

`src/cheshire/freedom_domains.py:14`는 현재 형상의 hinge·길이를 읽고, `:56`은 seed, domain move, 실제 displacement를 저장한다. 이 상태가 존재한다는 사실과 요구한 교대 성장의 기하 증명은 별개다. Astra Gate Grammar의 미커밋 연구는 별도 로컬 사본으로만 보존했으며 커밋된 Astra/Freedom과 혼합하지 않았다.

## 보존 판정

**연산 조합과 실제 자식면 재변형은 확인했다. 요구한 Alternating Fold–Protrusion Growth의 직접 증거는 확보하지 못했다.** 따라서 `NOT VERIFIED`로 남긴다. 방법의 불가능성, 실패한 전체 가설 또는 구현 불능으로 확대하지 않는다. 추가 실험은 수행하지 않고 연구 동결을 유지한다.
