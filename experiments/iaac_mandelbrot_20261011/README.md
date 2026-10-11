# IAAC / Mandelbulb / 접힘 입력 비교

독립 브랜치 `experiment/iaac-mandelbrot-growth-20261011`. 기존 CHESHIRE 소스·후보는 수정하지 않았다. 아치 조건은 사용자 지시에 따라 해제하고 기둥에서 원리를 시험했다.

코드는 이 폴더, 실제 출력은 `E:/CHESHIRE_DATA/iaac_mandelbrot_20261011`에 있다. `REPORT.md`가 짧은 평가이고 `SOURCES.md`는 공개 근거와 재구성의 경계다. `INDEX.json`은 결과 위치 및 검사 상태 목록이다. 원본 IAAC 코드 또는 물리적 origami 구현이라고 주장하지 않는다.

**용어:** 아래 ‘접힘 입력’은 단면·축방향 좌표를 직접 변형한 매스다. 접힘선을 따라 양쪽 면을 함께 꺾고 굽히는 알고리즘은 이번 코드에 구현하지 않았다. 사용자가 긍정적으로 평가한 `input_field/DIRECTIONAL_FIELD/G02_CC`를 유망한 조형 기준으로 보존하며, 현재 구성의 변형 강도만 높이는 분기는 종료했다.

## 실제 생성된 자료

| 폴더 | 내용 |
|---|---|
| `columns` | 원통 기준 CHESHIRE Task36 / 프랙탈 최근접 이동 / 부호 이동 비교 |
| `variations` | 36개의 유한한 필드·분할·입력 조건 비교, V16 퇴화 실패 포함 |
| `folded` | F01–F06: 균등 네 방향 접힘. 참조 접힘 논리와 달라 보존 후 중단 |
| `directional` | 방향별 엇갈린 능선과 축방향 되접힘을 직접 모델링한 초기 매스 |
| `input_field` | 입력 매스와 필드를 분리한 비교 및 접힘 방식 후속 시험 |
| `review` | 동일 카메라 정면·사선·측면 비교표와 세대 이미지 |

각 유효 체크포인트의 `checkpoint.npz`는 quad 제어 메시·chart·재시작 상태, `geometry.npz`와 `gate.ply`는 실제 삼각 메시다. `gate`라는 파일명은 공용 내보내기 이름이며 기둥 결과도 동일하다. `recipe.py` 및 단계별 recipe 사본, `generation.json`, `operation_fields.npz`에 생성 설정과 실제 변위가 보존된다. 렌더 폴더에는 카메라 조건을 명시한 `render_receipt.json`이 있다.

`CC1/CC2`와 `G02_CC`는 실제 Catmull–Clark 연산의 별도 체크포인트다. 이를 프랙탈 성장 세대로 세지 않는다. 별도 기하학적 smoothing은 없다. 렌더에는 저장된 삼각형과 단일 재질만 사용했다. 비교표는 동일한 중앙 crop/축소와 이미지 밖 캡션만 사용했다.

## 실행 예

저장 폴더가 이미 있으면 체크포인트를 덮어쓰지 않는다. 대용량 출력은 E 드라이브로 향한다. 아래 명령은 이 worktree 루트에서 프로젝트 Python 환경으로 실행한다.

```powershell
python experiments/iaac_mandelbrot_20261011/column_study.py --help
python experiments/iaac_mandelbrot_20261011/variation_study.py --names V17_NEW_ONLY V24_TURN --last 2
python experiments/iaac_mandelbrot_20261011/directional_cage.py --names D02_INTERLEAVED D04_DEEP_RETURN D05_CURVED_PATH
python experiments/iaac_mandelbrot_20261011/input_field_test.py
python experiments/iaac_mandelbrot_20261011/input_field_test.py --directional-inputs D04_DEEP_RETURN D05_CURVED_PATH --field-only
python experiments/iaac_mandelbrot_20261011/batch_render.py --folders directional/D05_CURVED_PATH/CC2 --workers 1
```

검사는 기존 `scratch/gate_synthesis_20261011/check_mesh.py`의 CGAL 검사 경로를 사용했다. 결과는 검사 대상 메시 옆의 `gate.validation.json`; 좌우 정점·면 대응은 `symmetry.json`이다. 검사 결과가 없는 메시의 교차 여부는 미검증이다. 단일 폐합 연결체와 자기교차 부재는 별개다. 두께·구조·제작 가능성은 전체 실험에서 미검증이다.

렌더링에 사용한 Blender/Python 위치는 `batch_render.py`에 명시되어 있다. 다른 PC에서는 해당 실행 경로와 `study.py`의 `DEFAULT_ROOT`를 조정해야 한다. 기존 CHESHIRE 모듈과 프로젝트 설치 의존성이 필요하다.
