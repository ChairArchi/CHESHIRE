# 주름을 보존하는 표면 장식 알고리즘

다른 기둥에도 같은 규칙을 적용하기 위한 분석·장식 코어다. 현재 기둥의 면 번호, 선택한 패치, 파일 경로는 코어에 들어가지 않는다. 현재 완성 모델22의 좌표를 이 API로 정확히 재현했다고 주장하지 않는다. 기존 실험에서 검증한 장식 적용 원리를 독립적으로 실행하고 검증할 수 있도록 분리한 버전이다.

## 입력과 판단

- `xyz`, `quads`: 실제 표면과 사각 면 연결 관계. 삼각형으로 내보낸 PLY를 임의로 다시 사각 면으로 해석하지 않는다.
- 물리 길이 단위를 가진 연속적인 `pattern_coordinates`: 기존 주름 생성기의 재료 좌표나 흐름 좌표를 전달한다. 새로운 기둥에서도 좌표 이음매를 관리해야 한다.
- 5개 연속 분류 가중치: 평온한 면, 약한 주름, 강한 방향성 주름, 볼록한 면, 복잡한 후보 영역. 후보 영역은 실제 가지 접합부라는 뜻이 아니다.
- 실제 만델벌브 유한 경계의 `theta/phi/radius` 자료. 좌표를 경계 높이에 대응시키는 방식이며 만델벌브의 전체 입체 위상을 새로 만드는 연산은 아니다.
- 선택 입력: 실제 Tissue 컴포넌트의 정규화 높이, Tissue 우선 가중치, 큰 주름 보호 가중치, 캡 마스크, 좁은 골 가중치.
- 선택 이력: 같은 재료 위치로 검증해 대응시킨 이전 세대의 좌표·법선. 이력이 없거나 분석 근거가 약하면 현재 표면의 분석으로 돌아간다. 정점이 생긴 시점을 주름의 생성 시점으로 간주하지 않는다.

색 분할과 장식 생성은 같은 분석 가중치를 사용한다. 이전 세대의 표본 수, 추정 오차와 방향 신뢰도는 별도 진단으로 남겨, 불확실한 값을 강한 분류로 표현하지 않는다. 흐름 후보와 검증된 주름 보호 영역도 구별한다.

## 장식 적용 API

```python
from cheshire.adaptive_ornament import (
    MandelRadialProfile, OrnamentRecipe, apply_adaptive_ornament,
)

profile = MandelRadialProfile(theta, phi, radius, provenance=source_metadata)
recipe = OrnamentRecipe(length_scale=1.0)
result = apply_adaptive_ornament(
    xyz, quads,
    shape_weights=measured_vertex_weights,  # N×5, 각 행 합계 1
    pattern_coordinates=physical_material_uv,  # N×2, 모델과 같은 길이 단위
    profile=profile,
    recipe=recipe,
    tissue_height=unweighted_actual_tissue_height,  # N, 0..1
    tissue_priority=tissue_weight,                  # N, 0..1
    flow_protection=protected_fold_weight,          # N, 1이면 좌표 고정
    cap_mask=caps,
    valley_weight=narrow_valley_weight,
)
new_xyz = result['xyz']
```

`Tissue height`는 가중치를 곱하기 전의 실제 컴포넌트 높이다. 이전 실험의 이미 가중된 Tissue 변위를 그대로 넣어 가중치를 두 번 곱하면 안 된다. Tissue 생성 플러그인과 기존 세대별 좌표 대응은 외부 어댑터가 맡는다. 코어가 임의의 천 모양을 Tissue 결과로 대체하지 않는다.

`tissue_height`만 제공하고 `tissue_priority`를 생략하면, 분석된 5개 가중치와 레시피의 `class_tissue_priorities`로 우선도를 자동 계산한다. 기본값은 방향성이 강한 주름에서는 낮고 볼록하거나 복잡한 후보 면에서는 높다. 외부 어댑터가 실제 접합부 정보를 가진 경우 명시적 우선도 입력으로 대체할 수 있다.

기본 SOURCE 만델벌브는 한 주기를 사용해 작은 장식을 만들고, 분류에 따라 높이를 조절한다. Tissue는 넓은 부푼 연결면을 담당하며 우선 가중치를 한 번만 적용한다. 실제 표면에서 다시 계산한 법선 방향으로만 움직이고, 큰 주름과 캡은 보호한다. 기하 안전 상한 뒤에도 면 방향을 직접 검사해 문제가 생긴 새 변위만 국소적으로 줄인다. 입력 좌표와 면은 수정하지 않는다.

`length_scale`을 바꾸면 장식의 주기와 높이가 함께 바뀐다. 호스트와 재료 좌표를 같은 배율로 변경하면 이 값도 같은 배율로 바꿔 동일한 상대 크기를 유지한다. 한 모델 안에서 세대별 바운딩박스로 임의 정규화하지 않는다.

## 실제 분할의 위치

현재 고밀도 표면의 CC 분할과, 앞선 세대에 장식을 넣고 CC로 전달하는 방식은 별도 비교 대상이다. 분할 전후의 호스트를 함께 처리한 차이 `CC(host+detail)-CC(host)`로 장식 변화를 분리해야, 원래 표면의 수축을 장식 개선으로 오해하지 않는다. 분할은 새 위상과 정확한 V/E/F 대응을 요구한다. `shade_smooth`나 단순 면 세분화를 실제 Catmull–Clark 기하 분할로 대체해서 설명하지 않는다.

연구 패치의 결과는 전체 기둥 채택을 뜻하지 않는다. 현재 코어는 연속 표면에 붙는 법선 장식이며 새 가지·구멍·덩어리 접합을 만들지 않는다. 전역 자기 교차와 제작 가능성은 별도 검증 대상이다.

전체 시험 적용용 실제 CC1 코어는 `cheshire.ornament_subdivision.prepare_cc1`이다. 특정 기둥 번호 없이 `xyz`, `quads`, 새 작업 폴더와 운반할 연속 속성을 받는다. V/E/F 순서와 각 원래 사각 면의 네 자식 면을 기록하며, 기본적으로 모든 모서리가 두 면에 속하는 닫힌 사각 면 표면을 요구한다. 디스크 배열로 계산하므로 큰 표면에 Python 메쉬 객체를 전부 만들지 않는다.

```python
from cheshire.ornament_subdivision import prepare_cc1

arrays, metadata = prepare_cc1(
    decorated_xyz, quads, new_work_folder,
    float_attributes={
        'shape_weights': measured_weights,
        'pattern_coordinates': physical_material_uv,
        'flow_protection': protected_fold_weight,
    },
    bool_attributes={'cap_mask': caps},
)
raw_cc_xyz = arrays['RAW_CC_XYZ']
bilinear_reference = arrays['BILINEAR_REFERENCE_XYZ']
child_quads = arrays['CHILD_QUADS']
```

이 함수는 실제 분할과 속성 운반을 분리한 코어다. 원시 CC 좌표의 주름 보호 혼합과 면 방향 복구는 전체 시험의 실행 어댑터가 이어서 수행한다. 현재 기둥 시험에서는 원래 주름 보호 가중치로 원시 CC와 선형 기준 표면을 섞고, 새 변위만 국소적으로 줄여 원래 팬과 사각 면의 두 대각선 표시를 검사한다. 작은 만델벌브를 추가로 다시 넣는 단계는 이번 전체 CC1 시험에 포함하지 않는다.

## 검증과 기록

`tests/test_adaptive_ornament.py`는 서로 다른 두 기둥, 크기·회전 변경, 정점 번호 변경, 큰 변위의 면 방향 복구, 보호 좌표의 정확한 유지와 입력 오류를 확인한다. 실제 캐시 만델벌브 자료를 사용한 재사용 실험과 렌더·색 지도는 E: 연구 산출물에 별도로 보존한다.

새 기둥으로 실행할 때는 `examples/adaptive_ornament_transfer.py`를 사용한다. 입력 NPZ에는 `xyz`, `faces`, `pattern_coordinates`가 필요하다. 선택적으로 `tissue_height`, `tissue_priority`, `flow_protection`, `cap_mask`, `valley_weight`와 분석 불확실 영역의 `fallback_face_weights`를 넣는다. 프로파일 NPZ의 키는 `theta`, `phi`, `radius`다.

```powershell
python -B examples/adaptive_ornament_transfer.py --host new_host.npz --profile mandel_profile.npz --radius 0.30 --recipe recipe.json --output new_result
```

출력 폴더가 이미 있으면 중단해 이전 결과를 보존한다. `geometry.npz`에 새 표면과 색 분할 가중치를 저장하고, `RECEIPT.json`에 입력·코드·프로파일 해시와 실제 검사 결과를 기록한다.

프로토타입의 단독 재사용 검증은 각각 4,608개 사각 면인 두 새 입력에서 수행했다. 수백만 면의 최종 모델은 기존 방식처럼 거친 세대에서 분석하고 검증된 계보로 가중치를 전달하는 어댑터가 필요하다. 고밀도 표면 전체의 분석 속도까지 검증한 버전은 아니다.

실행 결과는 레시피, 프로파일 해시, 분석 가중치, 원하는 높이와 적용된 높이, 국소 복구 가중치, 보호 마스크와 기하 검사 결과를 돌려준다. 큰 모델의 실행 한도는 `max_faces`로 명시한다. 기본 한도를 높이는 경우 원본 모델을 보존하고 새 출력 경로를 사용한다.
