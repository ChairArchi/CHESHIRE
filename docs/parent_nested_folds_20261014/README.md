# 후속 두 단계의 장식 위계 재구성 — 2026-10-14

목표는 단계가 추가되어도 앞 단계 주름의 가독성을 유지하는 것이다. 같은 전체 높이 H를 기준으로 비슷한 크기의 새 주름을 더하던 후기 LINKED/WIDE와 전역 미세 FLOW를 제외하고, 실제 MIDDLE 부모의 옆면에 CHILD와 그 안의 SMALL을 새로 계산했다. 새 후보 하나를 최신 COHERENT_FLOW와 비교한다. 기존 모델과 연구 코드는 수정하지 않는다.

## 입력과 실제 생성 순서

입력은 보존된 coherent replay의 `G07_SURFACE`다. 앞선 체크포인트와 동일한 MIDDLE 주축 가중치 `.95+.35p`를 적용한 것을 부모 형상으로 삼는다. 실제 G6 MIDDLE 변위는 저장된 중립 CC SURFACE를 재현해 검증한 stencil로 G7에 운반한다. 계보와 phase·support·envelope는 실제 저장된 G6/G7 자료에서 읽는다.

1. 부모의 펼친 phase를 실제 입력 면 위에서 미분하여 국소 폭을 추정한다. 실제 quad 대각선의 Gram 행렬로 구한 접평면 위상 기울기를 incident RMS로 모은다. `width=min(1.8/gradient,.08H)`이며 작은 폭을 인위적으로 크게 올리지 않는다. 이 폭은 일차 국소 위상 간격이며 실제 골 사이의 측지 거리나 충돌 여유가 아니다.
2. 부모의 위상을 따라 옆면 구간 `.55<abs(wrapped_phase)<2.35`에 C2 창을 둔다. 부모 위상의 능선과 깊은 골 구간은 후속 변위를 받지 않는다. 이는 위상으로 정의된 구간이며 모든 의미상 끝단을 탐지하는 기능이 아니다.
3. CHILD의 돌출 예산은 `min(.28*parent_envelope,.075*local_width)`다. `parent_envelope`는 실제 G6의 `.006H*saved_envelope*(1-.55*saved_support)`를 실제 V/E/F ID로 운반하고 주축 가중치를 적용한 것이다. 부모 변위의 절댓값을 쓰지 않아 profile의 영점에서 예산이 잘못 사라지는 것을 피한다.
4. CHILD 위상은 부모 옆면 좌표에서 한 주기만 만든다. 별도의 높이 방향 진동을 더하지 않는다. 실제 부모의 법선으로 새 변위를 계산한다.
5. SMALL은 CHILD의 양의 중심부 안에서만 생긴다. 위상은 CHILD의 3배, 예산은 CHILD의 `.28` 이하이며 국소 폭 기준 상한도 적용한다. 실제 CHILD 결과의 법선을 다시 계산한다.
6. 각 새 변위만 한 차례 평균하고, C2 창을 다시 적용한 뒤 정점별 변위 상한과 실제 X/Y 대칭 ID를 적용한다. 본체 좌표 자체를 평활화하지 않는다.

모든 부모 옆면에 같은 규칙을 적용하며 화면의 특정 부분만 선택하지 않는다. G7 연결 인덱스와 세대 번호는 유지한다. G8, 새로운 CC 분할, 독립 장식 메시, Mandelbulb 평가를 추가하지 않았다.

## 실제 계산 결과

- 위치: `E:\CHESHIRE_DATA\experiments\parent_nested_folds_20261014\trial01`
- geometry SHA256: `d95de449e0cd4d275abbe0c250216e60ad205aec82855fc3ee10a3d08dcfd49a`
- control SHA256: `acb8be634d45263c9e0f0453fcda29cc39adee00a86754ff0dc3a575a558aca6`
- native: 14,004,226 vertices / 28,008,448 triangles, 기존 G7 연결 인덱스 동일
- 실제 CHILD 최대 변위: `0.021134654864468562`
- 실제 SMALL 최대 변위: `0.005910555045113487`
- 부모·자식 정점별 예산 위반: `0`
- SMALL의 부모 마스크 초과: `0`
- 보호 정점: `3,058,669`; 선택된 부모 형상 대비 이동: 정확히 `0`
- 국소 폭 중앙값: `0.10413580481138025` (원본 모델 단위)
- Gram 조건에 따른 invalid quad: `0`
- 유한 좌표, 퇴화 삼각형 `0`, 최소 native 삼각형 면적 `8.4682704449542221e-11`
- 실제 X/Y 위치 대칭 오차: `3.3084646133829665e-14`
- 생성 시간: `233.17초`; 렌더 및 export 시간 제외

`PARENT_STATE.npz`는 부모의 주축 변위와 예산을, `NESTED_STATE.npz`는 실제 CHILD/SMALL 변위·마스크·국소 폭을 보존한다. 부모와 중간 CHILD는 원본 SURFACE 및 이 실제 변위로 정확히 재구성할 수 있다. 별도 native 중간 메시를 저장하거나 새 형태를 추정하지 않았다.

## 검증 범위와 남은 병목

이번 수치는 후속 두 단계의 국소 예산·분포 종속 관계를 검증한다. 숫자만으로 시각적 위계나 아름다움이 확보되었다고 판정하지 않는다. 최신 COHERENT_FLOW의 실제 이미지와 같은 정면·몸체·근접 조건에서 별도로 판단한다.

G3–G6 생성 규칙과 MIDDLE의 전역 위상은 변경하지 않았다. MIDDLE 이전의 개별 장식 끝과 겹침은 부모 형상에 남는다. 따라서 전 세대의 장식 위계, 의미상 끝단 보존, 자기 교차 해소, 제작 적합성을 보장하지 않는다. 후속 두 단계의 위계 재구성과 전체 세대 위계의 해결을 구분한다.

## 렌더 후 한 차례 조정과 선택

trial01의 실제 정면·몸체·근접 이미지에서는 큰 주름의 면과 흐름이 명료해졌지만 새 CHILD가 너무 조용했다. 같은 위상·중첩 마스크·보호 구간을 유지하고 CHILD 예산만 `min(.40*parent_envelope,.12*local_width)`로 조정한 trial02를 한 차례 생성했다. SMALL은 `.28*CHILD` 및 `.075*width/3` 상한을 유지한다. trial01 코드와 자료는 그대로 보존하며 새 파일 `run_readable.py`, `parent_nested_readable.py`를 사용했다.

실제 같은 조건의 세 시점에서 trial02를 확인하고 후속 위계의 체크포인트로 채택했다. 기존 COHERENT_FLOW와 비교하면 비슷한 굵기의 후기 주름이 경쟁하던 인상이 줄고 큰 흐름과 넓은 면이 살아난다. trial01 대비 자식 접힘의 가독성은 조금 높아졌지만 후속 장식은 여전히 조용하다. 세 단계가 모두 명확한 장식 완성본이나 전 세대의 위계 해결로 판단하지 않는다. 본체와 후속 패스 구성이 함께 달라진 설계 비교이며 단순 진폭 조절만의 시험도 아니다.

- 채택: `E:\CHESHIRE_DATA\experiments\parent_nested_folds_20261014\trial02\NESTED`
- geometry SHA256: `cde95d13f64d86739ac25e134e67024533d6be4fafec7a5d4c7a46896b65403e`
- control SHA256: `0092aaf46018411a0008156cc52d223dd25f2ca3192ae7ccc25e21f0afc385d3`
- 실제 CHILD/SMALL 최대 변위: `0.030192364092097947` / `0.008443540122804991`
- 보호 정점 3,058,669개의 이동은 정확히 0, 두 단계 예산 위반 0, 퇴화 삼각형 0
- 생성 시간 247.37초, 렌더·export 제외
- 실제 렌더: `trial02\NESTED_FLAT\review\{close_oblique,body_oblique,front}.png`
- 비교: 최신 COHERENT_FLOW 실제 이미지 재사용, 동일 카메라·재질·조명·900²·24 samples·all-flat, native 표시 좌표·인덱스 및 렌더 전후 동일성 확인
- export: `E:\CHESHIRE_DATA\exports\20261014\COLUMN_PARENT_NESTED`
- FULL `CHESHIRE_COLUMN_G7_PARENT_NESTED_FULL.ply`: 700,211,635 bytes
- DETAIL `CHESHIRE_COLUMN_G7_PARENT_NESTED_DETAIL.ply`: 4,217,147 bytes, 원본 삼각형 부분집합이며 절단 경계가 열려 있음
- 전체 PLY 좌표·면 readback 일치, 단순화·축·단위 변경 없음

## 별도 외부 기술 조사

사용자 요청에 따라 공개 GitHub 소스에서 차용할 가치가 있는 기술만 별도 검토했다. 외부 기술의 설치·도입·새 구현은 하지 않았다. 조사 후보와 실제 확인한 함수·출처·한계는 `RESEARCH_OPPORTUNITIES.json`에 보존한다. 위 trial02는 이 조사 전에 생성한 CHESHIRE 자체 수정안이며 외부 후보를 적용한 결과가 아니다.
