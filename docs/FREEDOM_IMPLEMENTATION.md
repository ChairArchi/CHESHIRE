# Generative Freedom — 구현과 재현 경계

출발 기준은 `0c4ec452518415d2fb12f724553e25d732c4c7c2`, 작업 브랜치는 `experiment/astra-generative-freedom`이다. 이 문서는 구현 의미와 검증 범위를 설명한다. 후보의 조형 판정과 측정 결과는 별도 결과 보고서를 따른다. 원본 Task 자료는 수정하지 않으며, 새 실험은 `E:/CHESHIRE_DATA/astra_freedom/`에 보존한다.

**공통 표면과 계보.** `ArrayMesh`의 operator polygon과 실제 native 삼각 표면을 구분한다. Field·patch·domain은 실제 삼각형을 midpoint 1→4로 분할하고 기존·신규 정점을 변형한다. 분할만 수행하면 각 부모 삼각형의 표면을 보존한다. `parent_faces`, `input_edges`, 원본 좌표와 적용 변위가 실제 연결 관계를 기록한다. 세대 번호, face 수, ancestry 존재만으로 새 형상의 발생이나 부모 내부의 공간적 포함을 증명하지 않는다. 기존 정점 유지율이나 patch 반경은 명시적 제어이며, 숨겨진 bounding-box 정규화는 없다.

**Field: 특징 계산과 실제 변형.** [freedom_growth.py](../src/cheshire/freedom_growth.py)는 lumped mass `M`과 cotangent FEM stiffness `L`로 `(M+r²L)X̄=MX`를 풀고, 관측 좌표와 heat-filtered 좌표의 차이를 법선에 투영해 detail을 얻는다. `X̄`를 메시 좌표로 대체하지 않는다. 정규화한 detail에 split·amplify·oscillate 반응을 적용하고, 선택한 법선 및 접선 방향으로 실제 변위를 만든다. 부모 거리 기준과 현재 평균 edge 길이 기준을 별도로 선택한다. `response='zero'`는 법선 반응만 끄므로, 순수 분할 대조에는 `tangent=0`도 필요하다.

`source='seed'`는 실험 시작 시점의 **실제 입력 형상**을 midpoint로 운반해 관측한다. 최초 scalar 배열을 계속 복사하는 방식은 아니다. `source='current'`는 현재 생성 형상을 읽는다. 특히 `frame='coherent'`는 관측 형상의 heat-filtered 법선을 사용하므로, source 변경은 scalar 특징과 적용 방향을 함께 바꾼다. 따라서 coherent current/seed 비교를 “특징만 동결하고 방향은 동일한 대조”라고 해석하면 안 된다. 실제 배치 기준 `base_xyz`는 두 조건 모두 현재 표면이다.

**Patch와 domain: 연결된 회전 영역.** [freedom_patch.py](../src/cheshire/freedom_patch.py)는 지배적 hinge 방향에 따른 유한 Rodrigues 회전을 연구한다. Face별 crease 방식과, 실제 hinge midpoint 주변의 여러 셀을 같은 축으로 회전하는 연결 patch 방식이 구분된다. 후자는 graph-edge 최단거리로 반경을 정하며, 실제 연속 표면의 정확한 geodesic은 아니다. 공유 정점의 회전 제안을 가중 결합한다. 별도의 XYZ Laplacian smoothing은 없지만, 제안 평균화 자체가 서로 다른 접힘을 상쇄할 수 있다.

[freedom_domains.py](../src/cheshire/freedom_domains.py)는 그 상쇄를 줄이는 경쟁 가설이다. `b=|dihedral|`, `ℓ=edge length`로 점수 `b√ℓ`를 만들고, 강한 후보부터 선택한다. 선택한 seed에서 `spacing·r`보다 가까운 다른 seed를 graph 거리로 억제한다. 동일 점수는 결정적 edge 순서를 사용하므로 반사 대칭을 보장하지 않는다. 후보의 길이 조건과 거리 단위는 입력 좌표계와 같다.

반경 안의 정점에 대해 `t=(1−(d/r)²)²`, 축에 수직인 면내 방향을 `s`, seed 원점에서의 벡터를 `δ`라 하면 회전각은 다음과 같다.

`θ = polarity · angle · tanh(2b) · tanh(5δ·s/r) · t`

회전 제안은 `R_axis(θ)δ−δ`, 결합 가중치는 `(tb/π)^power`다. `power`는 경쟁 제안을 집중시키며, 반경과 회전각은 서로 다른 효과를 낸다. 이 규칙은 자체 연구 가설이고 물리 시뮬레이션이나 원작 알고리즘의 복원 주장이 아니다. `source='rest'`는 운반된 `ArrayMesh.rest`에서 seed 각도·길이를 읽지만, 축·법선·graph 거리는 현재 형상을 사용한다. Field의 시작 형상 `seed`와 같은 대조가 아니다.

Domain state에는 zero-angle 분할 helper에서 상속된 `resolved_angles`, `observed_edge_angles`, `patch_rotation_proposals`도 남는다. 실제 domain 연산 해석에는 `seed_observed_bend`, `selected_seed_edges`, `domain_moves`, `domain_weights`, `resolved_displacement`를 사용한다. Coverage와 proposal attenuation은 적용 범위와 상쇄 진단이며 조형 성공 지표가 아니다.

**Legacy·pocket·fan.** [freedom_legacy.py](../src/cheshire/freedom_legacy.py)는 기존 완성 coupling의 가중 CC를 재사용하고, 현재 길이와 실제 부모로 운반한 길이를 기하평균해 normal 거리 기준을 정한다. Pocket은 현재 face 중심 주변의 inset cap과 원래 공유 경계를 잇는 네 rim을 만든다. Support는 중심에서 supporting edge line까지의 최소 거리이며, 비평면 polygon의 고유 폭을 인증하는 값은 아니다. Legacy pocket의 깊이는 현재 support를 사용한다. 운반된 CC 거리 기억과 pocket 깊이 기억을 혼동하면 안 된다.

[freedom_nested.py](../src/cheshire/freedom_nested.py)는 별도로 pocket support 기억을 도입한다. `current_support^(1−memory) · parent_support^memory`가 깊이를 정한다. 명시적으로 저장한 `physical_centres`를 통해 exact-fan refinement와 untouched polygon의 실제 삼각 표면을 유지한다. Weighted CC 대조는 실제 좌표를 바꾸는 연산이다. Exact physical surface 보존이 rest-chart parameterization까지 보존한다는 뜻은 아니므로, fan 변화의 무변형 검증에는 world-plane 절단을 우선한다. 재개 시 `quad_state.npz`의 `physical_centres`, `parent_support`를 복원해야 한다. 일반 `load_mesh`만으로 이 operator 상태가 모두 복원되지는 않는다. Cap/rim 역할은 실제 face 계보이며 공간적 포함 인증은 아니다.

**재현과 산출물.** 저장소 환경에서 다음처럼 새 tag로 실행한다. 정의 파일과 source snapshot이 구체적인 입력·계수를 정한다. 실행 중 관련 소스를 수정하면 source-identity 검사가 실패하므로, 수정과 실행을 분리한다.

```powershell
.venv/Scripts/python.exe -B tools/freedom_experiment.py --spec studies/freedom/definitions/J02_OUTWARD.json --tag J02_REPLAY_20261010A
.venv/Scripts/python.exe -B tools/freedom_deliver.py --request E:/CHESHIRE_DATA/astra_freedom/deliverables/D01B_CORE/request.json --tag D02_REPLAY_20261010A
```

`experiments/`, `legacy_probe/`, `nested_probe/`, `patch_probe/`, `hierarchy/`, `deliverables/`에 native·operator 상태, 레시피, 검증, 실패와 이미지가 나뉜다. OBJ는 좌표·면의 정확한 교환용이며 연구 상태 전체를 대신하지 않는다. Exporter는 `.17g` roundtrip, native 해시와 세대 라벨, embedding, 대칭, 횡단 교차를 확인한다. Invalid 결과도 이름·헤더에 표시해 보존한다. 실제 world-cut segment와 triangle ID를 저장하지만 2D 단면 교차 검사는 하지 않는다. 접선·공면·boundary-only 접촉은 횡단 검사에서 제외되고 cap 도달 값은 총 교차 수가 아니다. 검사 통과가 전체 solid 또는 예술적 성공 인증은 아니다.

기존 ArrayMesh·가중 CC·실제 표면 변환·검증·렌더 helper를 재사용했고, heat-response·유한 patch/domain 회전·pocket support 운반 규칙은 새 자체 구현이다. 원문과 공개 구현의 구분은 [ASTRA_PRIMARY_METHODS](ASTRA_PRIMARY_METHODS.md), 의존성과 배포 경계는 [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md)를 따른다. MOLA·Hansmeyer 원작 소스를 복사하거나 그 비공개 생성 과정을 구현했다고 주장하지 않는다. 외부 자료의 열람 가능성을 재배포 허가로 해석하지 않는다.
