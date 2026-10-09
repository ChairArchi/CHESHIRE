# ASTRA 실험·자료 색인 — 2026-10-10

루트: `E:/CHESHIRE_DATA/astra_research/`. 아래 경로는 이 루트 기준이다. source: `C:/Users/USER/CHESHIRE_ASTRA`, branch `research/astra-independent`. 모든 역사 아카이브를 재복제하지 않았다. 누락된 과거 파일은 기존 [인수인계](ASTRA_HANDOFF.md)와 [역사 감사](ASTRA_HISTORY_AUDIT.md)의 한계를 따른다.

## 연구 묶음

| 경로 | 수행 내용 | 판단 |
|---|---|---|
| `constraint_probe/`, `decomposition/` | 실제 Task36 상태 재구성, 동일 입력 averaging/diagonal 분리, 전체 G5 대조4개 | 판·깊이가 함께 바뀌며 단일 lock 원인 아님 |
| `primal_probe/` | 5차31개 소형 경쟁: intrinsic, current/rest, cap, diagonal, signed/support | 보수적 조건은 얕고 강한 조건은 교차 |
| `dual_probe/` | 6차23개 실행: DS role, CC 교대, fan sampling | frame/판 유지, 새 깊이 부족 |
| `recovered_probe/` | 2차8개: Task29 exact cube, 과거 macro의 column 이전, 후속 대조 | 강한 macro 복구, 계속 강하게 적용하면 교차 |
| `rotating_probe/` | 2차10개: 방향/relaxation/feedback/current-rest | 보수적 국소 변화와 실패 경계 |
| `recipes/` | 아래27개 정의+재현2회 | 통합 레시피의 직접 실행 기록 |
| `hierarchy/` | 실제 표면 barycentric 전이,13높이/2048방향/15prominence | 선택 B/D/E 유효 prefix의 새 basin0 |
| `evaluation/` | P01–P09 실제 native 렌더·세계 단면 | P05 이후 명시적 비금속 clay |

실행 수는 연구 성과 수가 아니다. probe와 통합 레시피에는 이전 결과를 옮긴 대조도 포함된다. 초기 rotating probe의 anchor-first 메타데이터는 최종 다중 parent 처리와 다르므로 주 계보 증거로 쓰지 않는다. P01–P04 평가 이미지는 초기 material 기본값(metallic1)이므로 최종 동일 재질 비교에서 제외한다.

## 통합 레시피 실행 목록

각 행의 native/state는 `recipes/<ID>/G<n>/`, 정확한 입력은 `recipe.json`, 적용값·parents는 `operator_state.npz`, source는 `source/`, 유효성은 `history.json`이다. 레시피 소스 사본은 [definitions](../studies/astra/definitions/)에 있다. 마지막 세대가 실패면 그 상태도 저장돼 있다.

| ID | 마지막 G | 삼각형 | 최초 invalid G | 마지막 교차 | 시간 s | 관측 peak MiB |
|---|---:|---:|---:|---:|---:|---:|
| A00_AVERAGING | 5 | 40960 | — | 0 | 3.31 | 219.1 |
| A01_FIXED | 5 | 40960 | — | 0 | 3.29 | 219.4 |
| A02_DIRECTION_CYCLE | 5 | 40960 | — | 0 | 3.29 | 220.0 |
| A03_GEOMETRY_DIRECTION | 5 | 40960 | 5 | 176 | 3.36 | 222.7 |
| A04_DUAL_ROLE | 5 | 40960 | — | 0 | 3.25 | 219.5 |
| B00_RECOVERED | 5 | 40960 | — | 0 | 3.23 | 191.0 |
| B01_FULL_BLEND | 6 | 163840 | 6 | 224 | 9.18 | 278.9 |
| B02_SIGNED | 5 | 40960 | 5 | ≥1024 | 3.31 | 217.8 |
| B03_LOWER_DIAGONAL | 6 | 163840 | — | 0 | 7.73 | 279.2 |
| B04_ROTATING | 6 | 69120 | — | 0 | 4.86 | 231.3 |
| B05_QUAD_G7 | 7 | 655360 | 7 | 720 | 32.70 | 825.5 |
| B06_ROTATING_G8 | 8 | 622080 | — | 0 | 29.85 | 637.6 |
| B07_SMOOTH_CONTROL | 8 | 622080 | — | 0 | 31.65 | 753.1 |
| B08_REFERENCE_CONTROL | 8 | 622080 | — | 0 | 26.87 | 641.0 |
| B09_CUBE | 6 | 41472 | — | 0 | 3.31 | 219.3 |
| B10_SHORT_COLUMN | 6 | 69120 | — | 0 | 4.87 | 231.2 |
| D00_ADAPTIVE_MEAN | 9 | 164000 | — | 0 | 17.10 | 359.5 |
| D00_REPLAY | 9 | 164000 | — | 0 | 17.25 | 366.2 |
| D01_ADAPTIVE_DOMINANT | 9 | 163984 | 9 | 24 | 17.67 | 319.9 |
| D01_REPLAY | 8 | 81984 | — | 0 | 10.84 | 272.4 |
| D02_UNIFORM_DOMINANT | 9 | 1866240 | — | 0 | 124.41 | 2458.9 |
| D03_ADAPTIVE_NOFOLD | 9 | 163984 | — | 0 | 16.67 | 364.5 |
| D04_ADAPTIVE_REFERENCE | 9 | 283984 | — | 0 | 25.64 | 493.5 |
| E00_EXACT_REFINEMENT | 7 | 655360 | — | 0 | 40.63 | 902.4 |
| E01_MONOTONIC | 6 | 163840 | 6 | 416 | 11.32 | 298.5 |
| E02_NONMONOTONIC | 6 | 163840 | 6 | ≥1024 | 9.62 | 297.6 |
| E03_NO_DIFFUSION | 5 | 40960 | 5 | ≥1024 | 3.79 | 222.3 |
| E04_REFERENCE | 7 | 655360 | 7 | ≥1024 | 34.48 | 827.8 |
| E05_AMPLITUDE30 | 6 | 163840 | 6 | ≥1024 | 10.12 | 322.1 |

## 바로 실행할 유효 후보

```powershell
Set-Location C:/Users/USER/CHESHIRE_ASTRA
.venv/Scripts/python.exe -B tools/astra_recipe.py --recipe studies/astra/definitions/D00_ADAPTIVE_MEAN.json --tag MY_D00
.venv/Scripts/python.exe -B tools/astra_hierarchy.py --candidate E:/CHESHIRE_DATA/astra_research/recipes/MY_D00 --tag MY_D00_CHART --stages 3,4,5,6,7,8,9
.venv/Scripts/python.exe -B tools/astra_deliver.py --stage E:/CHESHIRE_DATA/astra_research/recipes/MY_D00/G9 --tag MY_D00_OBJ
```

D01은 `studies/astra/definitions/D01_VALID_G8.json`을 사용한다. 전체 D01_ADAPTIVE_DOMINANT는 의도적으로 G9 실패를 재현하는9단계 정의다. 출력 tag는 새 이름을 사용해야 한다. 렌더 요청 JSON은 [구현 문서](ASTRA_IMPLEMENTATION.md#7-실제-명령과-의존성)를 따른다. 안전한 실행 완료와 조형 성공은 서로 다른 판정이다.

## 핵심 산출물

| 자료 | 절대경로 또는 루트 상대경로 |
|---|---|
| D00 실제 G0–G9 native/operator/state | `E:/CHESHIRE_DATA/astra_research/recipes/D00_ADAPTIVE_MEAN/` |
| D01 실제 G0–G8 및 실패 G9 | `E:/CHESHIRE_DATA/astra_research/recipes/D01_ADAPTIVE_DOMINANT/` |
| D00 전 세대 정면·사선·측면·확대·실제 절단 | `evaluation/P09_D00_SEQUENCE/` |
| Task36 동일 조건 및 B 대조 | `evaluation/P06_COST_AND_CAUSALITY/` |
| D 최종 후보·실패 경계 | `evaluation/P07_ADAPTIVE_BOUNDARY/` |
| E curvature 대조·실패 | `evaluation/P08_COHERENT_CURVATURE/` |
| 재현 가능한 검증 OBJ | `deliverables/D00_G9_RESEARCH/`, `deliverables/D01_G8_RESEARCH/` |
| 검사·OBJ 원본 SHA·역읽기 | 각 deliverables의 `exchange.json` |
|55 NPZ 원본/재생 정확 일치 | `verification/replay_comparison.json` |
| 소형 검토용 실제 이미지 | `C:/Users/USER/CHESHIRE_ASTRA/studies/astra/images/` |
| 원본 이미지 절대·상대경로/해시 | repo images의 `sources.json`, `final_comparison_sources.json` |
| 기계 판독 실행표·단면표 | `verification/recipe_index.json`, `verification/hierarchy_index.json` |
| 테스트 로그 | `commission/final_pytest_retry.log` (1024 passed), 첫 setup 오류는 `final_pytest.log` |
| 신규 데이터 파일·SHA 목록, 보존 커밋 및 bundle | `verification/data_manifest.jsonl`, `verification/preservation.json` |

## 해석과 보존 경계

주요 구현은 `src/cheshire/astra_*.py`, 실행·측정은 `tools/astra_*.py`, 신규 회귀45개는 `tests/test_astra_*.py`다. 구체적인 수식과 외부 출처는 [구현](ASTRA_IMPLEMENTATION.md), [원문 조사](ASTRA_PRIMARY_METHODS.md), [dual 실험](ASTRA_DUAL_EXPERIMENTS.md)에 연결한다. 공면·접선·경계 접촉은 기존 교차 검사 제외이며 제작용 solid 인증이 아니다.

전통적인 Task01–36 기록·원작 이미지·논문을 새로 복제하지 않았다. 접근하지 못한 eCAADe/Mesh Grammars 상세 PDF, √3 원논문 PDF와 MOLA 재배포 라이선스의 미확인 범위를 문헌 문서에 명시했다. 사용자 참고 이미지는 대화의 시각 자료로 사용했고 생성 레시피나 복제 목표로 해석하지 않았다.
