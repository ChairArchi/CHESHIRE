# trial15 — G7 CHILD/SMALL만 Mandelbulb 경계로 교체한 실제 시험

최신 사용자 지시인 **“전체가 아니라 G7에서 생성된 것만 Mandelbulb로 바꾸기”**를 구현한 시험이다. 동일 조건의 실제 native CONTROL/FIELD 근접·몸체 이미지를 직접 확인했다. 이번에는 작은 띠들의 변화가 확실히 보이고 큰 S 리본, 세로 수렴과 전체 볼륨의 인상은 남는다. 그러나 근접에서는 띠 가장자리에 거친 삼각 톱니와 찢긴 조각 같은 표면이 반복된다. 정제된 하위 프랙탈 가지나 매끄러운 조각적 디테일로 완성됐다고 판단하지 않는다. **요청 범위를 충족한 가시적 시험 후보이며, 최종 미적 채택안으로 기록하지 않는다.**

## 정확한 범위와 원본

기준은 `E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial02/NESTED`다. 전체 형상을 G3/G4로 되돌리거나 필터링하지 않았다.

```text
보존 부모 = replay G07_SURFACE + accepted primary_delta
          = accepted NESTED02 - delta_child - delta_small
후보      = 보존 부모 + 원래 G7 detail footprint 안의 새 Mandelbulb 경계 응답
```

원래 CHILD 입력인 보존 부모의 XYZ 해시는 `298a7c8853da37c6add586bb697c1c06fa9325d89dc64ea807d7f75a2de35755`다. 이전 읽기 전용 대조에서 두 부모 구성법의 최대 오차는 `1.7763568394002505e-15`였고, 원래 CHILD/SMALL delta 배열 해시는 receipt와 일치했다. trial15 runner는 부모와 성분의 동일성을 다시 검사했고 `component_identity_error=0.0`을 기록했다.

G6에서 이어진 중립 G7과 큰 흐름의 primary gain은 유지했다. **G7 CHILD·SMALL 두 성분만 제거하고 교체**했다. point birth mask는 사용하지 않았다. 원래 G7 detail이 실제로 작동한 3,943,441개 제어점을 support로 사용하며 모든 원래 역할을 포함한다. 원래 양의 `parent_mask` 3,943,445개 중 성분이 실제로 0인 4개는 포함하지 않는다. 나머지 보호 제어점 3,058,673개는 bit-exact이고 기록된 outside error는 `0.0`이다. 이는 제어점 기준 증거이며, 모든 의미적 큰 능선·실루엣을 별도로 고정했다는 주장은 아니다.

새 응답은 실제 finite power8 / 8회 spherical-power Mandelbulb에서 얻은 radial boundary를 사용한다. 경계의 normal 성분과 같은 경계 미분에서 얻은 intrinsic across 성분을 기존 G7 phase flank에 매핑했다. 별도 world-angle coating이나 SOURCE 전용 mask, 기둥에 붙인 장식 메시를 사용하지 않았다. **전체 Mandelbulb 체적·overhang·branch topology를 재현한 것은 아니다.** 출력은 기존 실제 G7이며 G8이나 추가 subdivision은 없다.

## 실제 이미지와 결과 파일

출력 root:

`E:/CHESHIRE_DATA/experiments/fold_junction_development_20261015/trial15_g7_detail_mandel`

이 root 안의 확인 대상은 다음과 같다.

- `FIELD_FLAT/review/close_oblique.png` — 새 후보 근접.
- `FIELD_FLAT/review/body_oblique.png` — 새 후보 몸체.
- `CONTROL_FLAT/review/close_oblique.png`, `body_oblique.png` — 정확한 기존 NESTED02 비교.
- `PROBE_RECEIPT.json`, `FORMATION.json`, `QUALITY.json` — 생성·범위·품질 기록.
- `FIELD_DELTA.npz` — 기준 제어점에 더하는 정확한 sparse delta. SHA-256: `77c60df4f61ad6fb170a47f5ed7cafaa7430f3430bb7d97ee0c176653f3535c2`.

기준 native geometry 파일 해시는 `cde95d13f64d86739ac25e134e67024533d6be4fafec7a5d4c7a46896b65403e`, 기준 control 파일 해시는 `0092aaf46018411a0008156cc52d223dd25f2ca3192ae7ccc25e21f0afc385d3`이다. 후보의 완전한 native XYZ 해시는 `bf0c30033eb277fe6cad43da00528b4d4d4eaa7faac2b9f9336f0dbf3fd9264d`이다. 기존 native 연결을 사용하고, 변경된 실제 quad corners에서 모든 fan centre를 직접 다시 계산했다. 원본 배열을 수정하지 않았다.

## 조형 판단과 기술적 한계

CONTROL의 가늘고 약한 주름보다 FIELD의 경계가 깊고 눈에 잘 띈다. 몸체 거리에서도 변화는 읽히지만, 동일한 거친 톱니가 여러 띠에 반복되면서 큰 리본의 깨끗한 흐름과 경쟁한다. 근접에서는 부드럽게 갈라져 나온 하위 잎·줄기보다 파쇄된 가장자리로 읽힌다. 가시성 확보와 아름다운 디테일 완성은 별개의 판단이다.

최소 native triangle area는 `8.468270444959312e-11`로 양수다. 다만 기준 triangle normal과 내적이 음수인 triangle이 2,785,640개, 약 **9.95%**다. 이것만으로 충돌이나 topological inversion이 증명되지는 않지만, 근접에서 확인한 날카로운 파편형 표면과 함께 남겨야 할 중요한 품질 신호다. global self-intersection은 검사하지 않았다. 기록을 바꾸거나 shader/normal map으로 이 표면을 감추지 않았다.

추후 내보내기 대상 경로는 `E:/CHESHIRE_DATA/exports/20261015/COLUMN_G7_DETAIL_MANDELBULB`로 정할 수 있다. 이 문서 작성 시점에는 **내보내기 완료를 확인하지 않았다**. 내보낼 때에는 baseline native/control과 위 `FIELD_DELTA.npz`로 실제 좌표를 재구성하고, 후보 native XYZ 해시 및 같은 연결을 확인해야 한다. 현재 시험 파일과 receipt는 수정하지 않는다.

이전 trial14는 엄격한 수치 대칭 검사 이후 최신 지시로 중단했으며 조형 실패로 평가하지 않았다. 현재 trial15가 그 경로를 rescue한 결과는 아니다. 이전 범위 증거는 [G7_DETAIL_REPLACEMENT_SCOPE.md](G7_DETAIL_REPLACEMENT_SCOPE.md), 중단 기록은 [TRIAL14_STOPPED.md](TRIAL14_STOPPED.md)에 있다.
