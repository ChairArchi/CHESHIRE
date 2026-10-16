# trial16 — 기존 G7 Mandelbulb 응답 3배 증폭 시험

사용자의 최신 지시 **“좀 증폭해서 덮을 수는 없나, 지금 애매함”**에 따라 trial15에서 저장한 Mandelbulb 응답을 정확히 3배로 키운 시험을 완료했다. 실제 근접·몸체 native 렌더를 trial15와 비교했다. 가장자리의 돌출과 어두운 골, 기존 면을 덮는 인상은 확실히 강해졌다. 다만 기존 톱니가 큰 각진 판·가시·겹친 부채 형태로 커졌고, 중앙 접속부와 몸체 전체의 거친 인상이 더 강하다. **증폭 요청을 수행한 research probe이며 최종 아름다운 설계로 채택하지 않았다.**

## 변경 범위

```text
보존 부모 = replay G07_SURFACE + accepted primary_delta
trial15    = 보존 부모 + saved Mandelbulb response
trial16    = 보존 부모 + 3 * saved trial15 Mandelbulb response
```

기준 NESTED02의 G7 `delta_child`·`delta_small`은 제거한 상태를 유지한다. 기존 G6 흐름과 primary gain 성분을 다시 만들거나 필터링하지 않았다. **FIELD_DELTA 전체나 기존 CHILD/SMALL을 3배로 키운 것이 아니다.** 저장된 새 Mandelbulb 성분만 증폭했다. 매핑, 경계 profile, 방향 frame, 기존 G7 support 및 point ordering은 trial15와 같다. G8·추가 subdivision·새 장식 메시·새 전역 mapping은 없다.

support는 원래 G7 detail이 실제로 작동한 3,943,441개 제어점이며 모든 원래 역할을 포함한다. 바깥 3,058,673개 제어점은 bit-exact, outside error는 `0.0`, component identity error는 `0.0`이다. 작은 성분의 정확한 출처는 [G7_DETAIL_REPLACEMENT_SCOPE.md](G7_DETAIL_REPLACEMENT_SCOPE.md)에 있다.

새 응답의 최대 norm은 trial15 `.0385306`에서 trial16 `.1155917`로 증가했다. 최대 normal 요청은 `.1048667`, B 요청은 `.0524997`이다. 기존 NESTED02와의 최대 총 차이는 `.1475015`다. 숫자는 증폭의 수행 증거이며 미적 성공의 척도가 아니다.

## 실제 출력과 이미지

실험 root:

`E:/CHESHIRE_DATA/experiments/fold_junction_development_20261015/trial16_g7_mandel_gain3`

- `FIELD_FLAT/review/close_oblique.png` — 실제 3배 후보 근접.
- `FIELD_FLAT/review/body_oblique.png` — 실제 3배 후보 몸체.
- `CONTROL_FLAT/review/close_oblique.png`, `body_oblique.png` — 정확한 기존 NESTED02 비교.
- `PROBE_RECEIPT.json` — 생성 성분·원본 binding·완전한 native 재구성 기록.
- `PAIR_RECEIPT.json` — 동일 조건 CONTROL/FIELD 실제 이미지 기록.
- `FORMATION.json`, `QUALITY.json` — 범위·증폭·품질 기록.
- `FIELD_DELTA.npz` — 기준 제어점에 더하는 최종 sparse delta. SHA-256: `25915aef5c4df14b9499f7c2b4a2d0345fb41973906b13702ab2d776d5a6c4a7`.

후보의 완전한 native XYZ 해시는 `673067f1b862c752027a6c44548529896283df697672b2be487f6c8a8452341b`이다. 원래 연결을 유지하고 변경된 quad corners에서 fan centres를 직접 다시 계산했다. 증폭 원본은 trial15의 `G7_DETAIL_REPLACEMENT_STATE.npz`이며 그 파일 해시는 `3a108982aacabb270e5826888338b4e7434cb0494c3d8d85b9ad63ce6201bb18`이다.

## 조형 판단과 방법의 한계

trial15보다 변화와 덮는 효과는 명확하다. 긴 S 리본의 방향과 기둥의 기본 수렴은 여전히 읽히지만, 증폭된 판과 톱니가 그 사이의 조용한 면보다 강하게 시선을 끈다. 3배 증폭은 이 base field에 없던 새 잎맥·연속 가지·프랙탈 하위 형상을 만들지 않았다. **현재 방법 안에서는 같은 형상의 크기와 그림자를 확대했을 뿐이며, 이를 새 anatomy의 생성이라고 부르지 않는다.**

사용한 형상은 실제 finite 3D Mandelbulb의 sampled radial boundary에서 유도한 B/N pullback이다. literal volumetric Mandelbulb component나 그 overhang·분리된 branch topology를 기둥의 일부와 교체한 것은 아니다. 이 구별은 형상장의 출처를 부정하는 것이 아니라, 실제 구현 범위를 정확히 남기기 위한 것이다.

최소 native triangle area는 `8.468270444959312e-11`로 양수다. 기준 normal과 내적이 음수인 triangle은 약 **15.80%**로 trial15의 9.95%보다 늘었다. 큰 회전·foldover 가능성을 살펴야 하는 품질 신호이지만 이 수치만으로 충돌이나 topology inversion을 단정하지 않는다. global self-intersection은 검사하지 않았다. 원본 receipt와 frozen operator는 수정하지 않았다.

## Research-probe 내보내기 완료

출력 디렉터리:

`E:/CHESHIRE_DATA/exports/20261015/COLUMN_G7_MANDELBULB_GAIN3`

`MANIFEST.json`은 `status=research_probe`, `research_probe_not_adopted=true`로 기록한다. 생성된 파일을 확인했으며 exporter의 exact roundtrip 검증 기록은 다음과 같다.

- `CHESHIRE_PARENT_PROBE_FIELD_FULL.ply` — float64, 14,004,226 vertices / 28,008,448 triangles. 파일 SHA-256: `6d59ded6851b508c22f8e5d985d75694ac00893bd5eb69b57f9fb44133179ba4`.
- `CHESHIRE_PARENT_PROBE_FIELD_DETAIL.ply` — 실제 native subset, 84,720 vertices / 166,822 triangles. open cut boundary이며 새 cap은 없다.
- `comparison.html` — 실제 근접·몸체 CONTROL/FIELD PNG 비교.
- 원본 probe/pair/render receipts와 `SOURCE_SPARSE_CONTROL_DELTA.npz` — 재구성 근거 보존.

내보내기는 연구 후보 보존이며 설계 채택이나 제작 적합성 인증을 뜻하지 않는다. 이 리뷰에서는 새 모델·추가 테스트·추가 렌더를 실행하지 않고 저장된 기록과 실제 이미지만 읽었다.
