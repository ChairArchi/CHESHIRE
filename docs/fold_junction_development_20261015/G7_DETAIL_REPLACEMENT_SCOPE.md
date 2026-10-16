# G7에서 추가한 작은 디테일만 교체 — 확정 범위

최신 사용자 지시는 기둥 전체가 아니라 **G7에서 생성된 작은 디테일만 Mandelbulb로 교체**하는 것이다. 기준은 채택된 `parent_nested_folds_20261014/trial02/NESTED`이며, 큰 흐름을 다시 만들거나 G4/G3까지 되돌려 필터링하지 않는다.

## 실제 저장 성분

```text
NESTED02 = replay G07_SURFACE + primary_delta + delta_child + delta_small
교체용 부모 = NESTED02 - delta_child - delta_small
            = replay G07_SURFACE + primary_delta
```

실제 저장 제어점 7,002,114개에서 두 부모 구성법의 최대 좌표 오차는 `1.7763568394002505e-15`였다. `G07_SURFACE + primary_delta`의 XYZ SHA-256은 `298a7c8853da37c6add586bb697c1c06fa9325d89dc64ea807d7f75a2de35755`이며, 원래 CHILD 연산 입력 해시와 **정확히 일치**한다.

`primary_delta`는 기존 G6 MIDDLE의 큰 흐름을 `.95+.35*p`로 강조한 성분이다. 이번 작은 디테일 교체에서는 유지한다. 실제 교체 대상은 fresh normal 평가로 추가했던 **CHILD와 SMALL 두 성분**이다. G7에서 새로 태어난 E/F 점 전체를 고르는 방법은 해당 생성 성분의 범위가 아니다.

| 기존 성분 | 실제 mask 제어점 수 | 실제 이동 제어점 수 | 최대 변위 |
| --- | ---: | ---: | ---: |
| CHILD | 3,943,445 | 3,943,441 | `.0301923641` |
| SMALL | 1,780,404 | 1,780,400 | `.0084435401` |
| CHILD mask 밖 보호 영역 | 3,058,669 | 0 | `0` |

기존 `parent_mask`는 inherited phase의 flank support다. SOURCE 전용 mask가 아니며 원래 CHILD/SMALL이 작동한 모든 역할을 포함한다. feature support는 진폭을 약화했지만 부착 역할을 전부 제외하지 않았다. 교체는 이 실제 support와 저장된 budget/width를 사용하고, 바깥 좌표는 그대로 유지해야 한다. 이는 임의의 새 역할 mask나 world 전체 coating과 구별된다.

## 원본 파일과 해시

공통 디렉터리: `E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial02`.

- `PARENT_STATE.npz` — `e5d3261aeb8fba6b423542f8a6c190521d029749403962c1f30be28ca7c02a10`
- `NESTED_STATE.npz` — `ec30d6bd0cd29e2f6acce6bb504c823117396eddaa3e15de49649f78fe87c258`
- `delta_child` 배열 — `e8247c4b5b18dc761d627e04bef80f155c5c98a0968edd088a11e33add89ac85`
- `delta_small` 배열 — `d7ac993cdc1dc84482d4045626f206bd15d0176a3af5ad7ff9b0d936cb5cd61f`
- 실제 `replay/states/G07_SURFACE/control_quad.npz` — `89653a94af3b2de1d875a3206a15a127f4418ef957cd011d4bca05c44fa21921`

두 delta 배열은 NESTED02 원래 receipt의 기록과 일치함을 확인했다. 이후 runner도 이 binding과 원래 CHILD 입력 해시를 확인해야 한다.

## G7 phase의 최소 재구성

실제 replay `G06_MIDDLE/evidence.npz`의 `directional_phase`, 같은 G6 control의 `faces`, `G07_SURFACE/evidence.npz`의 `input_edges`를 사용한다.

```python
phase7 = np.concatenate([
    phase6,
    phase6[input_edges].mean(axis=1),
    phase6[faces6].mean(axis=1),
])
```

실제 재구성 결과 7,002,114개 unwrapped phase의 SHA-256은 `a6e30ce8d733182e2b8bdc0d264927109c0c8f28672d44fe87604f6ba9d69afa`로 `RECEIPT.json/parent_frame_proof`와 정확히 일치했다. G6 원본 phase 해시는 `cc3f306019c3892e6c92513e2adfcb4d758c392d7de982e000a0452cc2f36d17`이다. G7 evidence의 `parent_phase`는 sin/cos로 운반한 **wrapped** 값이므로 이 unwrapped phase와 대체하면 안 된다.

이 문서는 기존 성분의 정확한 교체 범위를 정한다. 새 Mandelbulb 디테일의 가시성·미적 성공·충돌 여부를 미리 보증하지 않는다. 추가 native 모델이나 렌더를 이 검증 과정에서 생성하지 않았다.
