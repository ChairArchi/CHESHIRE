# Generative Freedom 실행 인덱스

기준커밋 `0c4ec45` 뒤의 독립 실험이다. [결과](../../docs/FREEDOM_RESULTS.md), [구현과 재현](../../docs/FREEDOM_IMPLEMENTATION.md). 전체자료 루트: `E:/CHESHIRE_DATA/astra_freedom/`. 새로 생성한 자료만 보존·목록화하며 기존 대형 아카이브 전체를 복제하지 않는다.

| 경로 | 용도 |
|---|---|
| `experiments/F00..F14` | heat 특징, 비단조 응답, parent/local 규모, current/seed, 계속 적용 대조 |
| `experiments/H00..H02_REPLAY` | pocket 이후 연결된 영역 접힘. H02 원실행 source guard 실패 별도 보존 |
| `experiments/J00..J12` | 겹침 상쇄 분리, inward/outward, rest seed, 축 전환, G7/G8 반경 대조 |
| `legacy_probe/` | 조상 거리·연산 전환·실제 cap/rim pocket, 실패와 정확 재현 |
| `patch_probe/` | 개별 면 회전→여러 셀 영역 회전, 반경 분리와 G7 추적 |
| `nested_probe/` | weighted CC/exact physical fan, parent-support memory 단일 요인 대조 |
| `hierarchy/` | 실제 삼각 표면 chart, strict NEW, 같은 골 연결, 대표 실제 좌표 증거 |
| `deliverables/` | 상태 명시 OBJ·native·world 단면·렌더·roundtrip·소스 SHA |
| `quick_views/` | 동일 조건 다세대·세부·과거 기준 비교. native SHA와 라벨을 연결한 manifest |
| `verification/` | 전체 테스트, 재현 비교, 환경, 최종 보존 검증·Git bundle |
| `references/` | 공식사진의 로컬 관찰본. 배포 라이선스를 가정하지 않음 |

`definitions/`는 실제 실행 JSON 사본이다. 실행마다 새 tag를 사용한다. 기존 결과 폴더에 덮어쓸 수 없다. `experiments/*/revision.json`은 생성 당시 baseline HEAD이며 수정 중 소스의 실체는 각 `source/`와 `source_identity.json`이다. 최종 보존 커밋은 `verification/preservation.json`이 연결한다. 전체 의존 코드는 Git에, 실행별 핵심 소스는 로컬 snapshot에 있다. snapshot 파일만으로 모든 의존성을 수집했다고 주장하지 않는다.

```powershell
.venv/Scripts/python.exe -B tools/freedom_experiment.py --spec studies/freedom/definitions/J02_OUTWARD.json --tag MY_J02
.venv/Scripts/python.exe -B tools/freedom_hierarchy_compare.py --tag MY_J02_MEASURE --candidates MY_J02
.venv/Scripts/python.exe -B tools/freedom_deliver.py --request my_selected_stages.json --tag MY_EXPORT
```

`my_selected_stages.json` 형식: `[{"id":"MY_J02_G6","stage":"E:/CHESHIRE_DATA/astra_freedom/experiments/MY_J02/G6"}]`. 후속 J09는 보존된 J02 G6를 시작점으로 쓰며 G7이다. 독립적으로 처음부터 재현하려면 레시피의 `start`를 새 MY_J02/G6로 바꾼 별도 사본을 사용한다. native/operator state 둘 다 보존해야 하며 OBJ만으로 제어·계보를 재구축할 수 없다.

Legacy·nested 계열은 `freedom_legacy_probe.py`, `freedom_nested_probe.py`에 해당 `definitions/<계열>_<실행>.json`을 `--spec`으로 전달한다. 여러 case의 recipe이며 generic runner와 교환할 수 없다. Patch 계열은 `freedom_patch_probe.py --round 3 --tag MY_PATCH`처럼 소스에 보존된 round 정의를 사용한다. Round4/5/6은 보존된 R03/R05 자료에 의존하므로 독립 경로로 옮길 때 그 의존 경로를 먼저 확인한다. 세부 명령은 각 `--help`를 따른다.

자동 전체자료 목록 `EXPERIMENT_INDEX.json`은 실행 상태·절대/상대경로·주요 결과를 연결한다. `verification/artifact_inventory.jsonl`은 최종 신규 로컬 아카이브 파일 SHA256 목록이다. 이 목록과 Git bundle은 별도의 오프라인 백업 장치를 대신하지 않는다.
