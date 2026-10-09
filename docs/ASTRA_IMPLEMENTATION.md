# ASTRA — 독립 생성·검증 구현 안내

2026-10-10. 이 문서는 현재 구현의 실행·입출력·해석 계약을 설명한다. 최종 조형 판정과 전체 테스트 결과는 [최종 연구 결과](ASTRA_RESEARCH_RESULTS.md)에서 확인한다. 기존 아키텍처를 유지해야 한다는 권고가 아니며, 아래 엔진은 서로 대조하거나 대체할 수 있는 독립 실험이다.

작업 폴더는 `C:/Users/USER/CHESHIRE_ASTRA`, 신규 연구 자료는 `E:/CHESHIRE_DATA/astra_research/`다. Task01–36 원본과 과거 실험 경로는 실행 대상으로 덮어쓰지 않는다. 연구 배경과 확인된 제약은 [역사·제약 감사](ASTRA_HISTORY_AUDIT.md), 과거 정확한 복구 계약은 [인수인계](ASTRA_HANDOFF.md)를 따른다.

## 1. 현재 엔진과 연산의 차이

| 엔진 | 실제 위치·연결 규칙 | 해석 경계 |
|---|---|---|
| [reference](../src/cheshire/reference_subdivision.py) | 같은 세대 face를 완료한 뒤 edge·vertex에 전달하는 modified CC. 명시된 normal offset·signed weights·literal SUM attraction | 공개 수식에 기반하지만 프로젝트의 scale/normal/recipe 선택을 포함한다. legacy의 input-centroid 경로와 다르다. |
| [primal](../src/cheshire/astra_primal.py) | quad aspect, cyclic 대칭 planarity, 인접 normal bend와 선택적 외부 Z field가 CC control을 바꿈. interpolation과 전체 weighted 결과를 직접 blend | Task36의 `weighted−CC` 차분 조합과 다르다. aspect/planarity는 proxy이며 Z field는 외부 조직이다. `signed_stencil`은 현재 특징으로 V/F 대각과 E/E 쪽 선호를 바꾸는 자체 규칙이다. |
| [dual](../src/cheshire/astra_dual.py) | DS 연결과 실제 F/E/V face-role. 인접 면에 대한 support 비율, corner normal contrast, 선택적 role별 부호가 corner 위치를 조절 | 지원하는 tri/quad 경로의 실험이며 범용 n-gon·임의 메시 solver가 아니다. support는 supporting-line 거리 proxy이고 논문의 생산 레시피를 복원한 것은 아니다. |
| [rotating](../src/cheshire/astra_rotating.py) | triangle centre를 삽입하고 이전 edge를 모두 뒤집어 새 face-centre 사이를 연결. signed hinge response에 따른 normal 이동과 조절 가능한 이웃 평균 이동 | sqrt(3)의 centre insertion/old-edge flip 연결 아이디어를 참고했다. 논문의 정확한 smoothing mask·수렴 극한을 구현했다고 주장하지 않는다. 자체 fold·relaxation 규칙이며 genus는 유지한다. |
| [adaptive](../src/cheshire/astra_adaptive.py) | 현재 관측 면적의 quantile로 selected face를 고르고 centre를 삽입. 양쪽 face가 selected인 이전 edge만 flip. 혼합 경계는 old edge와 selected-side fan, unselected face는 원래 삼각형 유지 | 기존 논문의 adaptive 방식 재현이 아닌 자체 conforming 선택 규칙이다. `hinge=dominant`는 절댓값 최대 signed hinge를 읽고 동률은 평균한다. 좌표별 강제 motif나 구멍 생성이 아니다. |
| [curvature](../src/cheshire/astra_curvature_response.py) | 입력 삼각 표면에서 signed edge-angle curvature를 읽고 scalar graph diffusion을 적용한 뒤 midpoint로 전달하여 current normal 방향으로 이동 | 좌표 smoothing과 구별한다. 물리 스케일 요청값·실제 기록된 diffusion 범위를 따로 읽으며, 비단조 반응이 새 위계를 보장하지 않는다. §8 참조 |
| `fan` / `task36` | [fan sampling](../src/cheshire/astra_dual.py)은 명시된 mean-centre fan의 실제 표면을 보존하며 다음 quad operator로 넘긴다. `task36`은 기존 별도 연구 연산을 호출 | 단순 sampling, 기하 변형, 실제 연결 변경을 결과에서 구별한다. fan은 지원하는 mean-surface 입력 계약을 검사한다. |

Adaptive에서 `selection=uniform`은 모든 face를 선택하는 대조다. quantile이 `.5`여도 동률과 tolerance 때문에 정확히 절반만 선택되는 것은 아니므로 실제 `selected_faces`를 기록한다. retained vertex의 relaxation은 incident selected-face 비율로 가중된다. 따라서 unselected face라고 모든 corner가 고정되는 것은 아니다. 경계에 T-junction을 추가하는 방식이 아니라 같은 old edge를 양쪽이 공유하는 conforming 삼각 연결을 만든다.

기둥은 기본 X/Y 단면·Z 수직, 일정한 정사각 단면이며 물리 단위는 별도 확정되지 않았다. 1:1은 X/Y 초기 비례 조건이다. 전역 bbox rescale이나 사각 외곽 lock을 뜻하지 않는다. `primal/dual`의 선택적 plane cap과 rotating/adaptive의 기본 자유 끝단은 서로 다른 조건이므로 비교 레시피에서 드러내야 한다.

## 2. 통합 레시피와 실행 상태

[astra_recipe.py](../tools/astra_recipe.py)가 carrier와 순서가 명시된 `steps`를 읽는다. 현재 `operator` 값은 `reference`, `primal`, `dual`, `task36`, `rotating`, `adaptive`, `curvature`, `fan`이다.

```json
{
  "carrier": {"kind":"column", "side":1000, "height":4000, "divisions":2},
  "steps": [
    {"operator":"reference", "parameters":{"weights":{"wf":0.02,"w1":0.1}}},
    {"operator":"rotating", "parameters":{"fold":0.35,"relaxation":0.04,"source":"current"}},
    {"operator":"adaptive", "parameters":{"selection":"adaptive","hinge":"dominant","quantile":0.5}}
  ]
}
```

위 JSON은 형식 설명용이며 검증된 최종 후보의 레시피가 아니다. 실제 대조는 각 실행 폴더의 `recipe.json`을 사용한다. reference의 `offset_units=ABSOLUTE`는 `GLOBAL_SCALE`을 명시한 경우에만 현재 global mean edge로 나누어 원래 좌표 단위의 offset을 전달한다. 나머지 ratio와 local scale을 같은 숫자로 비교하지 않는다.

각 새 tag는 `recipes/<tag>/`를 `exist_ok=False`로 만든다. `G0`부터 실제 단계별 `G<n>`을 저장하고, `history.json`, `validation.json`, `completed.json` 또는 `failed.json`을 남긴다. 접촉·embedding 결함이 있으면 기본은 그 상태를 보존하고 중단한다. 명시적 `continue_invalid_diagnostic`은 실패 상태의 후속 관찰용이다. 최종 `INVALID_DIAGNOSTIC`를 기술적 통과나 교환 승인으로 읽지 않는다.

실행 준비의 삼각형·메모리 예측은 보수적 상한 모델이다. adaptive는 실제 선택 수가 작더라도 uniform 3배 계열로 예측한다. 기존 `guarded()`는 process family 메모리와 가용 RAM을 실행 중 감시한다. 사전 reserve는 가용 RAM 55%/12GiB 한도, 실행 중에는 기록된 측정 한도와 최소 free floor를 사용한다. 생성·평가·계층 분석의 각 `execution.json`에서 실제 guard 결과와 관측 peak를 확인한다.

### 소스 snapshot과 실제 실행은 다르다

통합 runner는 지정 소스들을 `source/`에 복사하고 `source_identity.json`에 SHA256을 저장한다. 시작과 정상 종료 직전에 live Worktree 파일이 snapshot 해시와 같은지 확인하며 종료 확인을 `source_verified_after.json`에 남긴다. 그러나 **실행은 snapshot overlay를 import하는 격리 환경이 아니라 live Worktree의 코드**를 사용한다. snapshot은 재현할 당시 코드의 근거이며, 시작/종료 해시 검증을 frozen execution이라고 부르지 않는다.

`revision.json`의 Git HEAD만으로 미커밋 소스 전체를 복원할 수 없다. 실제 producer snapshot과 recipe·source hash를 함께 보존한다. 오래된 prototype runner가 현재 unified runner의 모든 검증을 수행했다고 소급 주장하지 않는다. 시작 후 소스가 바뀐 run은 해당 기록과 실패 여부를 먼저 확인한다.

## 3. 실제 표면·체크포인트·계보

| 파일 | 계약 |
|---|---|
| `mesh.npz` | 해당 단계에서 렌더·절단·교차·교환에 사용하는 **실제 native 삼각 표면**. xyz, face cycle, rest, class, anchor, generation 저장 |
| `operator_mesh.npz` | 다음 연산을 위한 원래 polygon/triangle state. surface 방식과 DS role을 함께 보존 |
| `operator_state.npz` | 실제 input edge/face, parent 대응, 읽은 feature, 요청/적용 control과 변위 등 연산별 state |
| `summary.json`, `validation.json` | operator metadata, native SHA, counts, embedding·교차 결과. 출력 파일 존재만으로 통과를 뜻하지 않음 |

Polygon을 native로 바꿀 때는 명시된 centroid fan 또는 자격을 갖춘 VF diagonal fan을 사용한다. 이미 삼각형인 rotating/adaptive 입력은 polygon 절반을 버리는 변환 없이 실제 삼각형을 그대로 쓴다. evaluator와 deliver는 triangle 전용 입력을 검사한다. 보조 fan centre와 실제 독립 operator 정점을 혼동하지 않는다.

Rotating의 `parent_faces`는 flip된 각 child triangle을 만든 **이전 두 triangle**이다. no-flip fan은 한 부모와 `-1`을 저장한다. Adaptive는 더 자세히 `input_faces`, `input_edges`, `parent_faces`, `parent_old_corners`, `child_construction`을 남긴다.

- construction `0`: retained face, 실제 한 부모와 이전 세 corner.
- construction `1`: selected/unselected 경계의 unflipped fan, 실제 selected-side 부모와 old edge 두 corner.
- construction `2`: 양쪽이 selected인 edge flip, 실제 두 parent face와 해당 old corner.

`selected_face_ids`, `selected_centroid_ids`, `flipped_edges`, 선택 전 요청 offset과 선택 후 resolved offset도 저장한다. 여러 부모의 `anchors`가 다르면 `-1`을 쓰며, 실제 다중 부모 정보는 `parent_faces`로 유지한다. anchor 하나만 읽어 geometry가 단일 부모를 따른다고 추정하면 안 된다. 이 대응은 **구성·위상 계보**다. retained vertex의 이웃 평균 등 모든 signed 좌표 영향의 Jacobian을 완전히 표현한다는 뜻은 아니다.

Polygon→triangle 전환 뒤의 parent ID는 실제 입력 native triangle의 index를 기준으로 읽는다. 다른 종류의 operator face index와 바로 같은 번호라고 가정하지 않는다. 이전 단계의 native·operator state 모두가 필요한 이유다.

## 4. current와 rest 대조의 정확한 의미

`source=current`는 현재 형상의 feature를 읽는다. `source=rest`는 transported reference 좌표와 **현재 connectivity**로 다시 만든 기준 embedding에서 feature를 읽는다. 새 centre, DS corner, edge flip 등이 rest embedding도 바꾸므로 최초 feature 배열을 영구 고정한 대조가 아니다. 실제 placement와 normal은 여전히 current mesh를 사용한다.

따라서 결과는 “현재 변형 형상 관측”과 “진화하는 reference embedding 관측”의 차이다. 최초 scalar를 ancestry로 동결한 실험, 위치·normal까지 초기 형상으로 고정한 실험과 구별한다. 일부 초기 prototype docstring의 freeze 표현보다 이 실제 데이터 경로를 우선한다.

## 5. 실제 단면·렌더·유한 계층 분석

[astra_evaluate.py](../tools/astra_evaluate.py)는 native 삼각 표면만 읽고 정면/사선/정확한 측면을 같은 요청 카메라로 그린다. 기본 width5000, target=(0,0,2000), 각도 (0,0)/(28,22)/(90,0), flat shading이다. 렌더의 material은 roughness .9, metallic 0이다. 요청에서 카메라를 바꿀 수 있으므로 동일 조건 비교에는 같은 설정을 사용해야 한다.

라벨은 `_G<n>`으로 끝나야 하고 native generation과 일치해야 한다. stage의 `G<n>`도 검사한다. native hash와 개별 artifact SHA를 기록한다. 실패 형상의 관찰 렌더와 교환용 통과 결과를 구별한다.

절단은 실제 triangle-plane intersection이다. `cuts.npz`는 raw XYZ 선분과 원래 triangle ID를 보존한다. 기본 횡단 높이 Z=500..3500, 간격250, 각 +.12345이며 종단은 XZ/YZ/X=Y다. raw cut은 전체 geometry를 반영하지만 파생 longitudinal profile의 표본 범위는 **고정 Z=0..4000**이다. cube·짧거나 이동한 입력에는 raw cut과 coverage를 우선한다. multiple-hit radial profile을 outermost로 골라 위계를 늘리지 않는다.

[astra_hierarchy.py](../tools/astra_hierarchy.py)는 edge flip으로 기존 ring 계보가 깨진 뒤에도 실제 표면 위에 놓이는 비교 곡선을 만든다.

1. 각 generation의 rest triangle을 사전 지정 Z=500..3500 step250+.12345에서 절단한다.
2. rest 선분 양 끝을 그 **원래 triangle의 barycentric weight**로 계산하고 actual XYZ에 옮긴다.
3. rest XY에서 2048개의 고정 각도 ray를 표본한다. 양의 radial 교점이 유일한 경우에만 실제 XYZ와 vertex support/weight를 저장한다. 같은 endpoint 중복은 허용하지만 서로 다른 반경, 같은 rest 위치의 서로 다른 actual sheet, ray와 겹치는 선분은 무효다.
4. `norm(actualXY)−rest_radius`의 radial excess를 구하고, 유효한 이전/다음 곡선만 기존 prominence15 `child_valleys`와 `envelope_retention`으로 비교한다.

전체 segment×angle 배열을 만들지 않고 관련 angular interval만 계산한다. raw rest/actual 선분·triangle ID·endpoint weight·각 표본의 support/weight/XYZ·coverage·재구성 오차·source hash를 남긴다. affine deformation 전이와 모호한 교점 거절을 테스트한다.

이것은 **변하는 construction chart에서 표본한 유한 곡선**이다. edge/material ancestry가 계속 동일하다는 인증, 연속 ridge 전체의 증명, intrinsic fold depth가 아니다. 고정 세계 단면과도 다르다. 새 골 0건은 이 위치·표본·prominence에서 추가 골을 확인하지 못했다는 뜻이며 모든 공간적 변화를 부정하지 않는다.

## 6. 최종 교환용 OBJ의 별도 검사

[astra_deliver.py](../tools/astra_deliver.py)는 선택한 native를 다시 검사한다. 일반 evaluator의 nearest-distance 대칭만으로 export를 승인하지 않는다.

- 전체 native triangle의 기존 strict 검사와 positive interior interval 보완 검사의 합집합, 공유 정점 쌍 포함.
- [embedding policy](../src/cheshire/astra_validation.py): finite, 퇴화·zero-area·orphan 없음, 유효 vertex link, 연결 성분1, 현재 primitive 연구의 Euler2.
- X/Y 반사와90도 회전의 일대일 vertex 대응 및 변환 방향에 맞는 triangle cycle 일치, 좌표 오차≤1e−8.
- `.17g` OBJ 기록 후 모든 좌표와 oriented triangle index를 순서대로 다시 읽어 정확 일치 및 count 확인.

validator source hash, native hash, producer 완료/실패 상태, OBJ hash를 저장한다. 유효한 `exchange.json`의 `exact_roundtrip=true`까지 확인해야 한다. OBJ는 operator continuation state를 대신하지 않는다. 전 세대의 실패가 있는 후보는 producer lineage까지 읽어야 하며 최종 geometry 검사만으로 생성 과정 전체의 유효성을 소급하지 않는다.

공면 겹침·접선·경계만의 접촉은 transverse 검사 제외다. signed algebraic volume, 유한 단면, 교차0을 제작용 solid·최소 두께·강도 인증으로 확대하지 않는다. 현재 export policy는 genus 변경 결과를 위한 범용 계약이 아니다.

## 7. 실제 명령과 의존성

아래는 보존된 B06 recipe를 **새 tag**로 실행하고 그 결과를 분석하는 예다. 기존 완료 폴더에 덮어쓰지 않는다. 결과의 완성도·실행 비용은 recipe별로 판단한다.

```powershell
Set-Location C:/Users/USER/CHESHIRE_ASTRA
.venv/Scripts/python.exe -B tools/astra_recipe.py --recipe E:/CHESHIRE_DATA/astra_research/recipes/B06_ROTATING_G8/recipe.json --tag MY_B06_REPLAY
.venv/Scripts/python.exe -B tools/astra_hierarchy.py --candidate E:/CHESHIRE_DATA/astra_research/recipes/MY_B06_REPLAY --tag MY_B06_HIERARCHY --stages 3,4,5,6,7,8
.venv/Scripts/python.exe -B tools/astra_evaluate.py --request E:/CHESHIRE_DATA/astra_research/my_views.json --tag MY_B06_VIEWS
.venv/Scripts/python.exe -B tools/astra_deliver.py --stage E:/CHESHIRE_DATA/astra_research/recipes/MY_B06_REPLAY/G8 --tag MY_B06_EXCHANGE
```

`my_views.json`은 사용자 실행 전에 새로 작성할 요청 파일이다. 예시는 `[ {"id":"MY_B06_REPLAY_G8", "stage":"E:/CHESHIRE_DATA/astra_research/recipes/MY_B06_REPLAY/G8"} ]`다. evaluator 출력은 `evaluation/`, 계층 자료는 `hierarchy/`, OBJ는 `deliverables/`에 저장된다. 해시가 다른 source로의 replay는 과거 byte-exact 재현과 구분해야 한다.

새 패키지를 설치하는 작업은 이 구현에 포함하지 않았다. 기존 Python 3.12 Worktree venv와 NumPy/SciPy, Trimesh/Pyrender/Pillow, 기존 검사 도구 및 로컬 C# BVH helper를 사용한다. 일부 의존성은 원래 CHESHIRE 환경을 읽으므로 독립 Worktree가 완전한 offline 배포 환경이라는 뜻은 아니다. 버전·외부 DLL/라이선스 경계는 [pyproject](../pyproject.toml), [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md), [인수인계 의존성 기록](ASTRA_HANDOFF.md)을 따른다.


## 8. Coherent curvature response: 추가 연산 계약

[astra_curvature_response.py](../src/cheshire/astra_curvature_response.py)의 `curvature`는 이전 삼각형을 **exact midpoint 1→4**로 표본화한 다음 모든 정점에 normal 변위를 적용한다. 곡률 H와 diffusion은 입력 삼각 표면에서 계산하고 새 midpoint에는 해당 scalar를 전달한다. 통합 runner는 `base_xyz`가 있을 때 실제 변형 직전 표면을 `G<n>_PRE/mesh.npz`, 변형 후 표면을 `G<n>/mesh.npz`에 따로 저장한다. PRE는 원래 삼각 표면의 재표본이며 새 접힘으로 세지 않는다. PRE 파일이 있다는 사실을 별도 교차 재검사 완료와 혼동하지 않는다.

정점의 signed curvature proxy는 `H_v = Σ_incident_edges(length·oriented_dihedral)/(4·barycentric_vertex_area)`다. **H의 차원은 1/길이**, `q=H·reference_length`는 무차원이다. `amplitude`, `radius`, `reference_length`는 입력 좌표 단위를 쓴다. length와 실제 displacement를 generation별 cell 크기로 조용히 바꾸지 않는다. `source=rest`는 이 경로에서도 변하는 reference embedding을 관측하며 placement normal은 current geometry에서 계산한다.

Diffusion은 XYZ가 아니라 scalar q에만 적용한다. edge weight는 `exp(−.5·(edge_length/radius)^2)/edge_length^2`, `dt=radius^2/(2·iterations)`, 정점별 update 계수는 최대 `.45`다. 요청한 `radius`를 실제 도달한 geodesic kernel 반경이라고 부르지 않는다. `diffusion_local_rms_distance = sqrt(iterations·alpha·weighted_mean(edge_length^2))`와 metadata의 min/max를 저장한다. 이것은 **실제 edge/alpha에서 계산한 국소 random-walk RMS 추정**이며 전체 확산 kernel의 공간적 RMS를 정확히 측정한 값도 아니다. 계수 포화와 지역별 edge 길이 때문에 요청 radius와 다를 수 있다.

`monotonic`은 `tanh(q)`, `nonmonotonic`은 `tanh(q·(1−(q/q0)^2))`를 사용한다. 마지막 normal displacement는 `polarity·amplitude·response`다. 비단조식에서 ±64q0의 scalar 포화 제한은 cubic overflow 방지이며 bbox/정점 위치 clamp가 아니다. 서로 다른 곡률 구간의 반응을 시험하는 자체 가설이고 ridge splitting이나 분기·Digital Grotesque 조형 성공을 증명한 식이 아니다.

State에는 raw H·무차원 q·diffused q·edge angle/length·vertex area·diffusion alpha/weight/RMS, exact PRE 위치·current normal·resolved displacement를 저장한다. child face의 실제 parent face, 새 midpoint의 parent edge와 인접 parent face, retained vertex ID도 남긴다. 자체 repair는 없으며 같은 외부 embedding·교차 정책으로 후단 유효성을 판단한다. 새 골의 발달 여부와 실패 세대는 별도 실제 결과·단면 증거를 따르고 이 구현 안내에서 확대 판정하지 않는다.
