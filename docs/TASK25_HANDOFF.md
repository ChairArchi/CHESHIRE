# CHESHIRE / Modern Cliché Task25 handoff

Task24 기준: `385ec86c1f18ee1e2e0d61e2b32c524ceccfb683`.
Task25 branch: `experiment/task25-generational-folding`.
최종 local commit SHA와 clean 상태는 외부 `source_revision.json`에 기록한다.
생성은 commit 전에 실행했으므로 각 `request.json`의 baseline commit만으로
코드를 식별하지 않는다. 실제 실행 파일 SHA256와 `source_snapshots`를 함께
보존했고, 최종 release 파일 해시도 별도로 저장한다.

모든 큰 결과는 `E:\CHESHIRE_DATA\task25`에 있다. 권장 모델의 정확한 이름,
OBJ/3DM 경로·바이트 수·해시 및 검토/모델 ZIP은 `deliverables.json`을 읽는다.
`FINAL_REPORT.md`, `analysis/SOURCE_MAP.md`, `analysis/DESIGN_DECISION.md`,
`analysis/measurements.json`이 선택·생성 경로·실측 기록이다. Review ZIP은
검토용이며 전체 역사와 대용량 체크포인트를 포함하지 않는다. MODEL ZIP의
`checkpoint/geometry.json.gz` + `state.json.gz`는 다음 세대로 이어갈 실제
상태다. 재생성을 위한 frozen 입력 전체는 외부 `inputs`와
`input_identity.json`에 별도로 남아 있다.

## 실행 환경

실제 사용: Windows PowerShell 5.1, Python 3.12.10, COMPAS 2.15.1,
pytest 9.1.1, pythonnet 3.0.5, 기존 .NET8/CoreCLR,
RhinoCommon 8.18.25100.11001. 전체 gate는 공식
`C:\Users\USER\Libraries\HDMola\1.0.0\HDMola.dll`을 사용했다.
DLL은 배포 ZIP에 포함하지 않는다. 이번 Task25 추가 세대는 기존 CC 접힘을
사용했고 새로운 Mola event를 추가하지 않았다.

## 실제 파일 열기

Rhino 8에서 `deliverables.json`의 native.path를 Open한다. 단위는 **None**,
원래 좌표·원점, Z-up이다. 스케일을 바꾸지 않는다. 레이어 이름은
`TASK25_<lead>`, object는 `<lead>_FULL_RESOLUTION`이다. 원래 OBJ SHA256가
object user string에 있다. Zoom Extents 뒤 Shaded/Arctic에서 전체를 확인하고,
중앙 상인방 아랫면으로 접근한다. 자동 처리에서는 interactive clay 캡처를
완성하지 못했으므로, native exact reread/headless open과 캡처를 구분한다.

고정 비교 카메라: whole front 0/0, oblique 32/16, underside 0/-30,
target=(-400,0,2000), orthographic frame width=8600. Detail은 0/-12 및
18/-25, target=(-400,0,2450), width=1800. Close는 0/-12,
target=(-400,0,2390), width=800. Renderer의 전체 회전행렬은 각
`renders/<tag>/camera_manifest.json`에 있다. 모델별 독립 crop fitting은 없다.
이미지는 기존 painter 폴리곤 프리뷰이며 교차 가림은 근사적이다.

## 재현

Task25 local commit을 사용하고, 기존 venv와 환경을 유지한다. 원래 결과
루트에서 같은 recipe를 다시 실행하면 새 attempt가 생기므로 새 루트를
권장한다. 아래는 H1의 292k 대조군과 오프셋을 제거한 1.17M 경로를 재현한다.
실행 전 메모리 예측과 기존 live guard가 적용된다.

```powershell
$task25Replay = 'E:\CHESHIRE_DATA\task25_replay'
New-Item -ItemType Directory -Path $task25Replay -Force | Out-Null
Copy-Item -LiteralPath 'E:\CHESHIRE_DATA\task25\inputs' -Destination $task25Replay -Recurse
Copy-Item -LiteralPath 'E:\CHESHIRE_DATA\task25\recipes' -Destination $task25Replay -Recurse
Copy-Item -LiteralPath 'E:\CHESHIRE_DATA\task25\input_identity.json' -Destination $task25Replay
.\.venv\Scripts\python.exe examples\generational_folding.py --output-root $task25Replay --run H1_CONTROL_G1 H1_CURVATURE_G2
.\.venv\Scripts\python.exe tools\folding_views.py --output-root $task25Replay --names H1 H1_CONTROL_G1 H1_CURVATURE_G2 --tag replay
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\crease_projection.ps1 -PlanPath "$task25Replay\renders\replay\projection_plan.json"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\folding_native.ps1 -ArtifactRoot $task25Replay -ObjPath "$task25Replay\designs\H1_CURVATURE_G2\attempt_001\H1_CURVATURE_G2.obj" -Name H1_CURVATURE_G2
```

대조군 G2는 `H1_CONTROL_G1 H1_CONTROL_G2`, noisy 경로는
`H1_CONVERGENCE_G1 H1_CONVERGENCE_G2`, small-offset 경로는
`H1_CONTROL_G1 H1_RENEWED_G2`를 새 루트에서 순서대로 실행한다.
원래 CONTROL_G2 attempt_001은 예측 중단이고 성공 파일은 attempt_002다.
새 루트에서 중단 조건이 다르면 attempt 번호도 달라질 수 있다.
계속 사용할 recipe의 checkpoint 경로는 실제 성공한 디렉터리를 명시한다.

## 상태로 재개하기

OBJ만 읽으면 mesh ID/point origins/세대·조상·branch·crease state가 사라진다.
Keyed geometry와 함께 저장된 `CHESHIRE_CC_CONTINUATION_V1` 상태를 사용한다.
같은 레시피 구조에서 `checkpoint`를 실제 체크포인트의 **루트 상대 경로**로
지정하고 새 recipe ID를 사용하면 된다. MODEL ZIP의 checkpoint를 외부 루트에
옮길 경우 `checkpoint` 경로도 그 실제 위치로 바꾼다. 루트에는 frozen
`inputs`, `input_identity.json`, `recipes`가 있어야 한다.
G2에서 이미 만들어진 중앙 경로를 이어갈 때는 `support_route`를 새 레시피에서
생략하고 `support_network_ids=['lintel_convergence_support']`로 현재 state의
실제 descendant 경로를 사용한다. 동일 network ID를 다시 추가하지 않는다.

Absolute CC는 C07의 3 + Task24 Fold 2 = 5에서 시작해 6, 7로 이어진다.
Continuation depth는 0,1,2이고 network generation은 실제 route birth 이후의
split 수다. 세 번호를 혼용하거나 resume 시 0으로 되돌리지 않는다.
Task24 말단에는 generic point origins가 없으므로 첫 세대에서 실제
corner/edge/face 구조로 bootstrap했다. 다음 세대부터 기존 Eq4가 그 실제
origins를 사용한다. 모든 history/events/roles/positive C0 associations,
branch signatures, anchors, root/parent edges, sharpness와 complete point origins를
lossless interning으로 저장한다. next_step=None은 미예약 상태이며 데이터 누락이 아니다.

## 검증과 남은 문제

전체 gate: 798 passed, zero skips. `output/task25_pytest_final.txt` 및 검토 ZIP의
로그를 확인한다. Uninterrupted vs save/reload 테스트는 geometry와 다음 접힘에
영향을 주는 전체 state가 정확히 같다. 실제 전체 H1의 기존 3-mesh 실행과
pointwise 실행은 IDs/oriented topology가 같고, 최대 좌표차는 원래 단위로
1.1368683772161603e-13이다. 수치 반올림 차이를 숨겨 bitwise 동일하다고
주장하지 않는다. 모든 성공 OBJ를 실제 파일에서 재읽었다. 권장 native는
실제 File3dm 재읽기와 RhinoDoc.OpenHeadless를 통과한다.

4.68M 추가 세대는 자동 실행하지 않았다. 같은 보수적 예측은 total 약
26.67GB이며 이번 머신의 잔여 메모리와 비교해 안전하지 않다. 이는 관측된
OOM이나 face-count 상한이 아니다. 새 상태·코드 경로에 보수적 여유를 남긴
5700 bytes/output-face 예측, 55% 잔여 RAM의 추가 할당 제한, live guard와
2GiB 잔여 RAM floor를 유지한다. 시간·접촉·외피 변경은 stop 조건이 아니다.

Automatic clay/DCC capture, 작은 접힘의 전체 gate 분기 조직, mantle/support의
언어 연결은 여전히 약하다. 단면/closed connectivity만으로 물리적인 내부
부피, 새 관통공극, 교차 없음이나 제작 가능성을 증명하지 않는다. Task26,
push/merge/publish는 실행하지 않는다.
