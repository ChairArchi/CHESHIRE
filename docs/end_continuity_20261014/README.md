# 연결된 본체와 종속 표면 접힘 — 2026-10-14

이번 사이클은 큰 주름 끝의 판형 절단 회귀를 먼저 해결하고, 큰 흐름에 종속되는 표면 접힘을 적용한다. 사용자에게 조형 판단을 위임받아 한 본체와 한 마감 후보에 집중했다. 기존 모델과 보존된 실험은 수정하지 않았다.

## 원인과 선택

이전 `REVISED`는 원본 WIDE_ROOT_FINISHED와 전체 source replay를 좁은 마스크로 혼합했다. 실제 메시 edge에서 마스크 변화 항이 replay 자체의 변화 항보다 컸고, 그 구간에 판형 끝이 생겼다. 선행 진단과 같은 카메라의 비교는 `../flow_fold_finish_20261014/END_TERMINATION_AUDIT.json` 및 `END_SOURCE_COMPARISON.png`에 보존되어 있다.

저장된 전체 `replay/states/G07_FINAL`을 본체로 사용하면 이 혼합 경계가 사라진다. 실제 close/body 렌더에서 중앙의 긴 주름이 둥글게 말린 끝과 하단 군집으로 연결되는 것을 확인했다. 이 본체를 채택했다. 전체 replay도 모든 둔한 cap이나 겹침을 해결하지는 않는다.

보조 진단으로 G4 실제 edge 길이에 따른 물리 거리 마스크를 만들었다. 기존 edge `[52332,1959852]`의 마스크 변화 항은 `0.0145244893`에서 `0.0000051664`로 감소했다. 이는 전이 기울기 진단이며 형상 성과가 아니다. 해당 마스크로 새 형상을 만들지 않았고 최종 결과에도 사용하지 않았다.

## 실제 적용

1. 보존된 전체 replay G7을 읽는다. 새 G0–G7 replay는 실행하지 않았다.
2. replay의 실제 SURFACE/LINKED/FINAL 차이와 검증된 중립 CC stencil로 옮긴 MIDDLE 변위를 추출한다. 기존 마스크를 사용하지 않는다.
3. 실제 replay의 펼친 부모 phase에서 주축 가중치 `p`를 구하고, MIDDLE 기여에 `.95+.35p`, LINKED/WIDE 기여에 `.80+.20p`를 적용한다.
4. 새 본체의 법선을 다시 구하고 `psi=12*parent_phase+2*pi*125*z`인 연속 접힘을 적용한다. 높이 기준 진폭은 `.00035H`이며 이전 FLOW03의 `.000625H`보다 낮다.
5. 새 변위만 한 차례 평균하고 실제 mirror ID로 대칭을 운반한다. 원본 본체 좌표를 평활화하지 않는다. native fan 중심은 변형된 네 모서리의 평균으로 다시 계산한다.

이는 보존된 기여의 재가중과 실제 법선 기반 마감이다. 후속 단계의 모든 의존성을 재계산한 새 세대 성장 공식이나 레퍼런스와 동일한 재귀 장식 생성이라고 주장하지 않는다. 물리적 결 간격은 부모 phase와 표면 변형에 따라 달라진다.

## 저장 결과와 검증

- 본체 진단: `E:\CHESHIRE_DATA\experiments\end_continuity_20261014\trial01`
- 새 마감: `E:\CHESHIRE_DATA\experiments\end_continuity_20261014\trial02\COHERENT_FLOW`
- geometry SHA256: `e7adee3cd77d4882143aba82623e8cf839193c693866ab21315b410fb05bd34c`
- control SHA256: `5b7da9926eb13220e0b5c7ea3feeddde6bc53ab12321afff68ff7a9ece9a3493`
- native: 14,004,226 vertices / 28,008,448 triangles; 기존 G7 연결 인덱스 그대로 유지
- native face SHA256: `67109d7c7378b6cdfe82a713c74a860c98cdd53adcdce311f8612b3e6565a9ee`
- 유한 좌표, 퇴화 삼각형 0, 최소 삼각형 면적 `1.0199795429985221e-09`
- 실제 X/Y 위치 대칭 오차: `3.3084646133829665e-14`
- 실제 fine 변위 최댓값: `0.003400683210227338` (원본 모델 단위)
- 실제 중립 CC의 저장 SURFACE 재현 오차: `3.5527136788005009e-15`
- 생성 소요: 195.16초. 이 수치는 렌더와 export 시간을 포함하지 않는다.

기존 연결 인덱스가 동일함을 확인했지만, 이번에 자기 교차·제작성·전역 충돌을 새로 검증하지 않았다. 메시 수치 검증과 조형 판단은 별개다.

## 실제 렌더 판정과 내보내기

동일한 카메라·재질·조명·Blender 버전·all-flat 조건의 정면, 몸체 사선, 근접 렌더를 확인했다. 실제 native 좌표와 삼각 인덱스의 렌더 전후 readback이 동일하다. 중앙 판형 절단이 말린 끝과 하단 군집으로 연결되며, 이전 FLOW03보다 잔주름이 큰 흐름을 덜 덮는다. 주관적 조형 판단에 따라 `COHERENT_FLOW`를 이번 사이클의 결과로 채택했다.

이 비교는 본체, 기여 가중치, 미세 접힘이 함께 달라진 **결합 설계 비교**다. 미세 접힘만의 효과나 끝단만의 효과를 분리한 시험으로 해석하지 않는다. 생성 시점의 validation에는 렌더 전이므로 `aesthetic_success=Pending`이 남아 있으며, 이후 채택 판단은 이 문서와 `CHECKPOINT.json`으로 기록한다.

- 실제 렌더: `trial02\COHERENT_FLOW_FLAT\review\{front,body_oblique,close_oblique}.png`
- 3D 출력: `E:\CHESHIRE_DATA\exports\20261014\COLUMN_COHERENT_FLOW`
- FULL: `CHESHIRE_COLUMN_G7_COHERENT_FLOW_FULL.ply`, 700,211,654 bytes
- DETAIL: `CHESHIRE_COLUMN_G7_COHERENT_FLOW_DETAIL.ply`, 4,188,726 bytes
- 두 PLY의 모든 float64 좌표와 삼각 인덱스가 원본과 정확히 일치하는지 readback으로 확인했다. 축·단위를 변경하거나 단순화하지 않았다.
- DETAIL은 저장된 macro 목표점 반경 `.28` 안의 삼각형 중심으로 선택한 부분집합이다. 열린 절단 경계가 있으며 전체 모델이 아니다.
- 인라인 비교의 6개 이미지, 카메라 일치, 실제 PNG 출처, 이미지 전환·상태 복원을 확인했다. 브라우저 레이아웃 자동 검증을 했다고 주장하지 않는다.

생성, 렌더, export, 보조 마스크의 실제 기록 사본을 이 폴더에 보존했다. export 시점에는 최종 Git 커밋이 아직 없었으므로 export manifest의 `checkpoint=null`을 유지한다. 이후 Git 체크포인트는 해당 manifest 및 실행 코드의 실제 해시를 포함한다.

재현 명령은 작업 worktree 기준이며 기존 trial 폴더를 덮어쓰지 않는다. 새로운 출력 경로를 지정해야 재실행할 수 있다.

```powershell
python experiments/end_continuity_20261014/coherent_finish.py --root E:/CHESHIRE_DATA/experiments/end_continuity_20261014/trial03
blender --background --python experiments/end_continuity_20261014/render_finish.py -- --root E:/CHESHIRE_DATA/experiments/end_continuity_20261014/trial03 --phase review --variant COHERENT_FLOW
python experiments/end_continuity_20261014/export_finish.py --root E:/CHESHIRE_DATA/experiments/end_continuity_20261014/trial03 --output E:/CHESHIRE_DATA/exports/20261014/COLUMN_COHERENT_FLOW_REPRODUCTION
```

## 남은 과제

상부의 둥근 cap과 횡단 collar, 하단의 복잡한 겹침, 일부 근접 삼각 facet은 남아 있다. 이번 결과를 다른 입력이나 게이트에 이전한 것은 아니다. 최신 G7과 상인방의 접속은 별도 설계 과제다.
