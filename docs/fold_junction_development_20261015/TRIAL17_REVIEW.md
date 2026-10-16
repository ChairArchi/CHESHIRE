# trial17 — G7 Mandelbulb 경계만 둥글게 한 후보

사용자는 증폭한 trial16 이후 이전 전체 coating처럼 더 부드러운 결과를 요청했다. 이에 **G7 작은 디테일 교체 범위와 기존 큰 흐름은 유지하고, 새 radius target만 둥글게 하며 B 변위를 줄인 한 후보**를 실행했다. 실제 근접·몸체 native 이미지를 직접 확인했다.

trial15/16의 큰 파편·톱니 판이 크게 줄었고 긴 S 리본과 기둥의 세로 흐름이 다시 차분하게 이어진다. 새 디테일과 깊어진 골도 읽힌다. 세 후보 중 이번 부드러움 요청에는 **trial17을 가장 정돈된 검토 후보로 제시한다**. 다만 규칙적인 잔주름과 기존 cup 접속부의 어색함은 남으며, 새 자식 가지나 연속된 프랙탈 anatomy를 완성했다고 판단하지 않는다. 이것은 이미지 판단이며 숫자만으로 미적 성공을 선언한 것이 아니다.

## 실행 범위

보존 부모는 실제 replay `G07_SURFACE + accepted primary_delta`다. 원래 NESTED02의 `delta_child`·`delta_small`만 제거하고 새 성분으로 교체했다. 원본 G6/G7 carrier XYZ를 smoothing/fairing하지 않았다. 동일한 기존 G7 support 3,943,441개 제어점과 모든 원래 역할을 사용하며, 밖의 3,058,673개 제어점은 bit-exact, outside error는 `0.0`이다. point birth mask, 추가 G8, 새 장식 메시 또는 전체 world coating은 없다.

변경은 두 가지다.

- 실제 finite power8 / 8회 Mandelbulb의 **새 sampled radius target**에 angular Gaussian σ=`[1.2,1.2]` samples를 적용하고 그 뒤 미분했다. 원본 profile의 normalization을 그대로 유지했으며 둥글게 된 값을 다시 재증폭·재정규화하지 않았다.
- normal cap은 강한 `.105`로 유지하고 B cap을 normal amplitude의 `.067`로 줄였다. 실제 최대 B 요청은 `.006971`이다. trial16의 `.052500`보다 크게 작다.

따라서 이 결과는 trial16의 전체 XYZ를 매끈하게 만든 결과가 아니다. G6 흐름과 이전 부모 성분은 보존하고 새 target 형상과 그 접선 변위만 바꿨다.

## Normal 성분의 한계

저장된 `normal_scalar`와 `inherited_parent_mask`만 읽은 좁은 감사에서, mask 안 제어점 기준 음의 normal 변위는 **73.5321%**, 양의 변위는 **26.4494%**였다(`1e-12` tolerance). RMS는 `.0174416`, 평균은 `-.0067004`, 실제 최소/최대는 **`-.0744399 / +.0437532`**다. `.105`는 허용 envelope cap이고 실제 양의 peak는 그보다 작다. target smoothing 후 raw normalization을 유지한 결과와 구별해야 한다.

이는 제공된 local normal 방향을 따라 대체로 안쪽으로 움직인다는 뜻이다. unweighted 제어점 비율이며 표면 면적·부피 변화의 증거는 아니다. 이 부호만으로 결과를 거부하지 않는다. 실제 이미지는 trial16보다 더 부드럽고 정돈되어 보인다.

현재 방식은 Mandelbulb radial boundary의 **deviation을 B/N으로 옮기는 pullback**이다. 기둥 일부를 literal volumetric Mandelbulb component와 교체한 것도, 기존 표면을 전부 감싸는 outer envelope를 만든 것도 아니다. 향후 outer-envelope 개념을 검토한다면 현재의 inward/outward radial-deviation 방식과 별도로 정의해야 한다. 이 리뷰 뒤 자동으로 새 구현이나 변형을 실행하지 않는다.

## 실제 산출물과 근거

출력 root:

`E:/CHESHIRE_DATA/experiments/fold_junction_development_20261015/trial17_g7_mandel_rounded`

- `FIELD_FLAT/review/close_oblique.png`, `body_oblique.png` — 실제 둥근 후보 이미지.
- `CONTROL_FLAT/review/close_oblique.png`, `body_oblique.png` — 정확한 NESTED02 기준.
- `PROBE_RECEIPT.json`, `PAIR_RECEIPT.json` — 생성과 동일 조건 이미지의 기록.
- `FORMATION.json`, `QUALITY.json` — 범위·profile 처리·품질 기록.
- `FIELD_DELTA.npz` — 파일 SHA-256 `3e4b0820a4df1bea68a96a9e7b1bf2fbc60a949961c0fd06feca6f5f92d84086`.
- `G7_DETAIL_REPLACEMENT_STATE.npz` — 좁은 normal 감사에서 확인한 파일 SHA-256 `e9a992fd842cc7b96af22ea66707887b83e8573da7b957b174d75872599c3a8d`.

완전한 후보 native XYZ 해시는 `1632f6b4dab14c492a860cb83b54ac1d1a0c86f065b7827b6c1796332cda5b03`이다. 기존 연결과 실제 quad-corner fan centres를 사용한다. 최소 native triangle area는 `8.468270444959312e-11`로 양수이며 기준 normal과 내적이 음수인 triangle은 약 **7.52%**다. 이 수치는 trial16의 15.80%보다 줄었으나 global self-intersection 검증이나 제작 적합성 증명을 뜻하지 않는다.

이 문서 작성 시점에는 렌더와 probe 산출물까지 확인했다. 별도 PLY export 완료는 이 문서에서 주장하지 않는다. 원래 receipt·frozen operator·E 원본은 수정하지 않았고, 추가 모델 테스트나 렌더도 실행하지 않았다. scope의 재구성 근거는 [G7_DETAIL_REPLACEMENT_SCOPE.md](G7_DETAIL_REPLACEMENT_SCOPE.md), 비교 후보는 [TRIAL15_REVIEW.md](TRIAL15_REVIEW.md), [TRIAL16_REVIEW.md](TRIAL16_REVIEW.md)에 있다.
