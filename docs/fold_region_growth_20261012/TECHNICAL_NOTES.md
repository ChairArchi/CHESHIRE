# 실제 형상 기반 구간 접힘 — 기술 기록

기준 커밋은 `8a4cc2e4367802123d6f5fd24e70620259463642`다. 작업 브랜치는 `experiment/fold-region-growth-20261012`이며 기존 실험과 일반 엔진의 동작은 유지한다. 결과의 조형 판정은 [REPORT.md](REPORT.md)에 있다.

## 입력과 표면

SPAN은 기존 `docs/fold_return_20261012/review_assets/OVERLAP_G02`를 사용한다. COUNTER는 기존 다른 초기 형상의 실제 G2를 `review_assets/COUNTER_G02`에 포함했다. 두 입력의 제어점은 6,402개, 사각면은 6,400개다. 재료 좌표와 위상은 같고 실제 XYZ는 다르다. 입력 해시는 [SUMMARY.json](SUMMARY.json)에 있다.

기존 inactive interpolating refinement를 재사용한다. G2의 실제 native fan 표면을 VF 표현으로 이어받아 G3의 변형 기준으로 삼는다. 각 사각면의 실제 표면은 삼각형 fan 4개다. 새 변형 전의 CONTROL에 CC 좌표 averaging, 새 cell-normal offset, 새 fractal field를 적용하지 않는다.

재사용 의존 경로는 `experiments/fold_return_20261012/study.py` → 기존 transfer/memory/Task36 도구다. 실험 디렉터리를 단독으로 떼어낸 라이브러리는 아니다. 저장소 전체에서 실행한다.

## 측정과 변형

`region_fold.py`의 sampler는 실제 native 삼각형의 재료 높이와 정점별 `atan2`로 만든 affine UV를 쓴다. KD-tree는 후보 삼각형 탐색에만 사용한다. 실제 포함 판정과 barycentric 보간으로 위치를 구하며, 포함되는 삼각형이 없으면 실패한다. 최근접점으로 대체하지 않는다. 삼각형 ID와 보간 가중치도 저장한다. 월드 Z 절단은 아니다.

가로 안은 부모 밴드의 반지름 chord 결손으로 골을 찾는다. 세로 안은 각도 방향 chord relief의 절댓값으로 가장 강한 능선 또는 골을 찾고, 부호를 기록한다. 능선을 골이라고 바꾸어 부르지 않는다. 선택된 특징에서 인접 어깨의 물리적 호 길이 55% 위치를 모아 이차 가이드로 근사한다. 부모 영역의 탐색 범위는 기존 두 authored event에서 온다.

선택안 `--orientation height --frames region`은 가이드 중심의 삼차 근사와 어깨 횡방향의 이차 근사로 구간 방향을 정한다. 메시 XYZ, 측정한 중심점, 원래 삼각형은 평활화하지 않는다. 이 근사 방향이 실제 모든 패싯의 법선과 일치하는 것은 아니다.

변위는 구간 안의 V형 골과 끝단 taper다. 깊이 계수는 측정한 어깨 호 길이의 `0.28`이다. RETURN은 측정한 가이드 접선에 대한 짝 회전 `0.65 rad`도 더한다. 두 영역이 겹치면 변위를 합산한다. 충돌 해결이나 접힘 에너지 최소화는 없다. 반사는 실제 XYZ의 절댓값이 아닌 재료 좌표의 부호로 구성한다. 원본 접힘이 대칭 평면을 넘을 수 있기 때문이다.

옛 제어점도 영역 안에서는 움직인다. 선택안에서 움직인 옛 제어점은 SPAN 632개, COUNTER 720개다. 기존 원본은 별도 체크포인트로 보존한다. 끝단과 측정 영역 경계의 변위는 0이며, 전체 부모 접힘의 깊이·각도 불변을 보장하지 않는다.

## 대조와 판정의 한계

`measure.py`는 가이드마다 7개, 총 14개 재료 좌표 절단을 각각 257점으로 샘플링한다. 원래 G3 CONTROL과 새 후보를 **같은 원본 가이드 법선**으로 투영한다. 필터를 적용하지 않는다. 어깨 호 길이 4% 이상의 prominence를 가진 골 중, 가이드에서 횡방향 폭 20% 이내이며 기존 골과 폭 8% 이내로 대응되지 않는 골을 새 골로 센다. 이 임계값은 이번 비교의 고정된 판정이며, 독립적인 미적 품질 평가가 아니다.

구간 방향 안의 인접 접선·법선 최대 각도 변화는 네 가이드 전체에서 `7.63°` 미만이었다. 국소 방향 안에는 `176.39°`까지 변화가 있었다. 이 차이는 방향 제어의 변화이며, 원래 형상의 급격한 변화가 모두 오류였다는 뜻은 아니다. 원시 기록은 SUMMARY의 `frames`에 있다.

검증 범위는 기본 표면 무결성, 동일 계수, 실제 형상 반응, 유한 절단의 새 골, 저장 변형 재생이다. 자기교차 및 제작 검증은 제외했다. G4 이후를 예측하거나 전체 연속 위계를 인증하지 않는다.

## 실행

Python 3.12와 기존 `task32`, `review`, `test` extra가 필요하다. 실제 검증 환경은 NumPy 2.5.3, SciPy 1.18.1, trimesh 5.1.1, Pillow 11.3.0, pytest 9.1.1이다. Blender 렌더는 4.5.4에서 실행했다. 가상환경을 활성화한 뒤 저장소 루트에서 실행한다.

```powershell
python -B experiments/fold_region_growth_20261012/study.py --root output/MY_NEW_REGION --orientation height --frames region
python -B experiments/fold_region_growth_20261012/measure.py --root output/MY_NEW_REGION
python -B -m pytest -q tests/test_fold_region_growth.py -p no:cacheprovider --basetemp output/MY_NEW_REGION_TESTS
python -B experiments/fold_region_growth_20261012/verify.py --roots output/MY_NEW_REGION --output output/MY_NEW_REGION/replay.json
```

기존 결과 폴더가 있으면 생성기는 실패한다. 항상 새 root를 쓴다. 외부 G2는 `--source-span`, `--source-counter`로 지정할 수 있지만 현재와 같은 chart·표면 형식·두 부모 seed를 요구한다. `--orientation theta`는 가로 비교, `--frames native`는 국소 방향 비교다.

렌더링은 `geometry.npz`의 실제 삼각형만 쓴다. 전체 800×800 / 16 samples, 근접 1000×1000 / 32 samples다. flat normals와 기존 uniform mineral 재질이며 추가 형상·텍스처·normal map·render subdivision은 없다. 예를 들어 Blender 경로를 환경에 맞게 지정한 뒤:

```powershell
& $blenderPath --background --factory-startup --python experiments/fold_region_growth_20261012/render.py -- output/MY_NEW_REGION/GROOVE/SPAN/G03 --views front oblique side front_region side_region front_shoulder side_shoulder
```

모든 모드와 입력을 렌더링한 후 `boards.py --root output/MY_NEW_REGION --output output/MY_NEW_REGION/images`로 비교판을 만든다. [렌더 영수증](render_receipts/longitudinal_region/GROOVE/SPAN/detail.json)에 카메라·재질·표면 범위가 기록돼 있다. CONTROL 등 동일 삼각형 배열의 이미지를 재사용한 경우 `reuse.json`으로 출처와 동일 해시를 기록했다.

## 결과 위치와 재생

로컬 전체 결과는 다음 새 root들에 남아 있다. 기존 `E:/CHESHIRE_DATA` 결과는 변경하지 않았다.

| 로컬 root | 역할 |
|---|---|
| `output/fold_region_growth_20261012_final` | 교정된 가로 대조 |
| `output/fold_region_longitudinal_20261012` | 세로 / 국소 방향 |
| `output/fold_region_coherent_20261012` | 세로 / 구간 방향, 선택안 포함 |
| `output/fold_region_portable_replay_20261012` | 패키지 입력으로 두 GROOVE를 새로 생성한 결과 |

초기 `output/fold_region_growth_20261012`는 물리 좌표 부호로 반사한 프로토타입이다. 최종 판정에는 사용하지 않는다. 수정 전후 SPAN RETURN의 일부 점이 달랐고 최종판을 다시 렌더링했다. 다른 결과의 렌더 재사용은 geometry 파일의 바이트 동일성을 확인한 경우로 한정했다.

이번 패키지에는 두 입력, 선택 GROOVE 두 개의 제어 메시·실제 삼각형·변위·가이드·절단 배열, CONTROL 두 개의 제어 메시·삼각형, 모든 후보의 측정 결과와 비교 그림을 포함한다. PLY와 모든 대안의 전체 수치 상태는 로컬 output에 남긴다. `.npz`는 checkpoint이며 그림은 표시용이다. 각 후보의 `generation.json`에 실제 부모 seed와 계수 및 입력 해시가 있다.

18개 저장 변형의 재생 기록은 [technical/saved_operations.json](technical/saved_operations.json)이다. 동일한 가이드와 reference에서 변위를 다시 계산해 오차 0을 확인했다. 별도로 패키지 입력부터 새로 생성한 선택안의 배열 동일성은 SUMMARY의 `fresh_packaged_input_replay`에 있다. 별도 컴퓨터의 깨끗한 설치 검증은 아니다.

`package_review.py`는 완료된 세 비교 root와 새 입력 재생 root에서 작은 검토 패키지를 만든다. 기존 대상 파일과 다른 내용이면 덮어쓰지 않고 실패한다. MANIFEST는 패키지 파일과 새 실험 소스의 SHA-256을 기록한다. 이번 파일에만 적용되는 `.gitattributes`로 Git의 자동 줄바꿈 변환을 막아 체크아웃 사이에도 해시를 유지한다. 기존 엔진 의존성은 기준 커밋으로 지정한다.
