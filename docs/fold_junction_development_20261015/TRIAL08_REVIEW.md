# Trial08 검토 — 미채택

**판정: NOT_ADOPTED.** 실제 G6→G7 생성 1회와 52,500개 제어점의 이동은 확인했지만, 현재 근접 화면의 개선으로 채택하지 않는다. 최대 이동은 0.0535027315 모델 단위이며, 형성된 family 0의 material t 범위는 0.2883–0.5151이다.

같은 카메라의 정확한 neutral G7과 비교한 900px RGB 결과는 다음과 같다. 차이는 세 채널 중 최대 절대 차이로 계산했다.

| 화면 | 차이 >10/255인 픽셀 | 해석 |
| --- | ---: | --- |
| close_oblique | 0 / 810,000 | 최대 차이도 3/255. 근접 접속부 개선은 보이지 않는다. |
| body_oblique | 522 / 810,000 (0.0644%) | 변화는 화면 아래 y=756–899에 집중된다. |

기록된 lower/centre/upper rail의 X/Y 반사본 444점을 원래 카메라에 투영하면 close 화면 안에 들어오는 점은 0개다. 투영 y 범위가 1343–3330으로 화면 아래에 있다. Body 화면에는 238점이 들어오지만, 투영만으로 실제 가시성이나 가려짐까지 증명하지는 않는다.

시각적으로 넓은 면, 컵 모양 끝단과 둔한 접속이 여전히 지배적이다. 새로운 부모→자식 주름의 연결 위계는 읽히지 않는다. NESTED02보다 차분해진 근접 표면은 기존 late field의 생략과 구분해야 한다. NESTED02 대비 close의 차이 >10 픽셀은 21.4315%인 반면, 생성 효과만 분리한 neutral 대비 close에서는 0개다.

원인은 초기화 범위의 불일치다. `run_recursive.py`는 G3 `owner==0`을 SOURCE로 이어받고, G3 WALL의 `rails_0`, `rails_1`만 부모로 초기화한다. 이 두 초기 PCHIP/WALL 영역은 나중에 전체 몸체에 생긴 G6 MIDDLE의 `20θ` 주름들을 열거하지 않는다. Family 1은 SOURCE chart 밖의 74개 표본 때문에 종료됐다. 같은 두 rail의 coverage 보정만으로 모든 G6 주름의 연속 생성을 입증할 수 없다. SOURCE 필터를 단순 제거하면 동일 material chart를 공유하는 서로 다른 생성 면의 표본이 섞일 수 있다.

Neutral 이미지 재사용은 가능하다. Trial08 `REFERENCE_G7/geometry.npz`와 audit01의 `G07_SURFACE/display_geometry.npz`는 파일 SHA256까지 동일하다: `80928b87a12f8ba0a6c426adda31e3e9861e1c0e855a2c36358e689eabd1d7b1`. XYZ/삼각형 배열·개수, 조건, body/close 카메라와 기존 PNG 해시도 일치한다. 기존 audit의 **저장 제어면을 산술 중심 fan으로 표시한 파생물**이라는 출처를 유지해 body/close를 재사용한다. Audit에 neutral front는 없다.

원본 PNG와 receipt 경로·SHA, 수치 및 범위는 [TRIAL08_REVIEW.json](TRIAL08_REVIEW.json)에 보존했다. 이번 기록 작성에서는 기존 분석값을 옮겼으며, 재렌더링·PNG 변경·픽셀 분석 재실행은 하지 않았다.
