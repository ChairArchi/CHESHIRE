# Task24 — Hero design sprint

**결과: PARTIAL.** 실제 메시 세 안의 실루엣, 질량 배치와 깊이 차이는
확인했다. 그러나 세 안 모두를 설득력 있는 Hero 게이트라고 판정하지는
않는다. 큰 형태에서 중간 분기와 미세 장식으로 이어지는 일관된 위계,
다층 공간과 공극의 풍부함은 Digital Grotesque 목표에 미달한다.

리드는 **H1 ANGULAR MANTLE / CLEFT**다. 넓은 맨틀, 변형이 이어지는
지지부와 통과 공간의 관계가 가장 잘 읽힌다. H2는 한쪽으로 기울어진
분기와 더 가벼운 상부 질량을 보여준다. H3는 깊이와 가림이 크게 변하지만
큰 판이 장식과 개구부를 가려 게이트로서는 가장 약하다. 면 수와 접촉 수는
선정 점수로 쓰지 않았다.

| 최종 안 | 실제 레시피 ID | 정점 / 면 | 생성 시간 | 디자인 판단 |
|---|---|---:|---:|---|
| 맨틀 / 클레프트 | H1 | 73,114 / 73,112 | 123.95초 | 리드. 상부와 지지부의 연결, 비교적 읽히는 통과 공간 |
| 분기 크라운 | H2_R1 | 73,218 / 73,216 | 144.43초 | 비대칭 분기와 실루엣 차이. 중간 가지와 작은 장식의 관계는 약함 |
| 파편 / 캐니언 | H3_R3 | 72,590 / 72,636 | 154.46초 | 깊은 교차 판과 가림. 정돈된 간극 순서와 게이트 기능은 불충분 |

시간은 최종 worker의 체크포인트·내보내기를 포함한 실제 시간이다.
후속 이미지 생성과 접촉 진단 시간은 별도다. 생성 프로세스와 driver의
관측 RAM 피크는 각각 약 0.85, 0.85, 0.80 GiB다. 사용 가능한 RAM에서
다음 단계의 증가를 추정했고 무거운 형상은 순차 처리했다. 예전 300k 면
제한과 900초 시간 제한은 이어받지 않았다. 자원 때문에 형태를 줄인
타협은 없었다.

## 입력과 참조

Task23 기준은 `140932fb6cbcaec4a1d27665fb99bf0e0a806fc3`다. Task24는
이 커밋에서 시작했고 `experiment/task24-hero-design-sprint`에 분리했다.
최종 소스 커밋과 파일 SHA256은 외부 `source_revision.json`에 기록한다.
생성 당시 HEAD와 실제 실행 파일 SHA256은 각 `request.json`에 남는다.
검토 ZIP의 `source/execution`에는 실제 생성에 사용한 runner도 보존했다.
최종 소스에는 생성 수치 변경 없이 동결 입력의 바이트·내용 해시를
재사용 전에 확인하는 검증을 추가했다.

R20의 저장된 출력 전체를 해시 검증했고 기존 독립 재생성 PASS 기록도
확인했다. R20의 최종 메시를 다른 완성 레시피들에 무작정 연결하지 않았다.
R20과 동일한 **동결 C07 입력과 계보**에서 검증된 라우팅·폴드·장식 순서를
새로 조합했다. 입력 바이트와 canonical SHA256은 `input_identity.json`에 있다.

C07의 원형 C0는 Task15의 24정점 / 22면, 다섯 셀 U 게이트다. 과거 dense
게이트에서 계산한 원점과 고정된 건축 치수로 재구성한 입력이며 ALICE 원본 메시와 동일하다는
증거는 없다. C0의 W/H/D는 4000/3500/500, 초기 개구부 W/H는 2200/2600,
원점은 `[-400.036865234375, -18.533447265625, 0]`이다.
Task24에서 새 입력으로 대체하지 않았다.

상류 파일에는 물리 단위가 저장되어 있지 않다. 원래 모델 좌표를 그대로
유지하고 3DM 단위를 `None`으로 기록했다. mm라고 추정해 변환하지 않았다.
Z가 위쪽이고 정면은 -Y에서 본다. 단위 확인 요청은 별도로 남겼다.

참조 여섯 개는 실제 JSON과 실제 사선 이미지를 확인했다.
`source_map.json`과 `SOURCE_MAP.md`가 파일·함수·체크포인트·이미지를 연결한다.
Y07은 X07의 E2에서 후속 장식을 이어가는 레시피다. Y19는 R19의 E2에서
이어가는 레시피이며, “order”는 상대적인 시각 평가다. 독립된 정렬 연산,
공간장 또는 대칭 규칙이 아니다.

## 조합과 실제 수정

모든 수치, seed(None), 네트워크 선언, 선택 조건과 실행 순서는 최종
`recipes/*.json`, 기본값 해석은 `resolved_parameters.json`, 실제 선택 면·
배치·계보는 각 시도의 operator/lineage/network 체크포인트에 있다.

* H1: X10의 대향 N3 경로와 기존 N6의 명시적 어깨→지지부 경로.
  큰 각진 폴드 → Roof → R20/Y19 계열의 맞춘 법선 오프셋과 제한된
  후속 폴드 → 실제 Roof 자식 면의 frame/taper/frame/taper.
  X01과 X10이 공유하는 N3 연속 경로를 쓰지만 X01 전체 레시피를 별도로
  실행했다는 뜻은 아니다.
* H2_R1: X01 N3와 Y07 양측 N5를 조합. 큰 폴드 → 큰 tapered branch →
  다음 crease 세대 → 실제 branch 측면의 중간 taper → 자식 장식 네 단계.
  초안의 상자 같은 큰 cap을 보고 cap fraction과 중간 가지 역할을 바꿨다.
  개구부나 교차를 복구하려는 수정이 아니다.
* H3_R3: Y19의 맞춘 큰 오프셋 → X02의 강한 점 클래스별 파편 변형 →
  깊이 방향 조립 → 실제 측면의 Roof → 자식 장식 네 단계.
  R1/R2에서는 중간 장식 뒤의 강한 폴드가 새 코너 클래스를 과장해 큰 판이
  게이트를 가렸다. 마지막 수정은 두 큰 폴드를 먼저 끝내는 순서 변경이다.
  여전히 큰 판이 지배하므로 정돈된 캐니언을 달성했다고 주장하지 않는다.

초기 세 메시를 먼저 생성하고 검토했다. 이후 두 디자인 수정, 캐니언의
한 국소 연산 호환성 처리, 마지막 순서 수정만 했다. 연구 atlas나 자동
미감 탐색은 열지 않았다. 초안과 실패 체크포인트는 삭제하지 않았다.

H3_R1은 S04까지 완료한 뒤 요청한 InsetFrame에서 `Mola cap
reverses/collapses`로 멈췄다. S04의 메시·계보·경로를 그대로 이어받은 H3_R2는
동일한 기존 생성자를 실제 작은 부모 면에 먼저 적용해 호환성을 확인했다.
면 96249의 실패를 기록하고 사용 가능한 면만 처리했다. 수치나 위치를
고쳐서 교차를 제거하지 않았다. 실패한 원본 시도는 그대로 남는다.

Mola 단계 뒤에는 정확히 남은 원래 edge만 crease로 추적한다. 영향을 받은
새 장식 edge의 crease 의미는 구현되어 있지 않다. 반면 실제 양의 구성
계보와 branch signature는 유지했다. 이를 변형의 부호 있는 계수 계보나
일반 의미 상속이라고 부르지 않는다.

## 검증과 시각 증거

세 최종 OBJ를 실제 디스크에서 다시 읽어 XYZ와 방향 있는 면 연결이
정확히 일치함을 확인했다. H1과 H2_R1은 C07에서 독립 재생성해 메시,
전체 event/history, branch signature와 남은 crease network도 정확히
일치했다. H3_R3은 C07에서 완료한 명시적 레시피와 실제 export 검증을
남겼으며 별도의 두 번째 독립 재생성을 했다고 주장하지 않는다.

최종 세 안은 모두 유한 좌표, 연결된 closed/manifold 표현이며 Euler 값은
2다. 이 표현상의 성질이 전역 자기교차 부재나 출력 가능한 부피를 뜻하지는
않는다. 기존 접촉 샘플러는 진단으로만 실행했다. 실제 수치와 cap은
`geometry_observations.json`에 있다. 접촉 수, 개구부 변화와 기존 envelope는
생성 중지나 형태 복구 조건으로 쓰지 않았다.

`renders/final`은 실제 OBJ의 정면·사선·측면·후면 공통 축척 비교와 각 안의
fitted view를 포함한다. 전체 문맥 디테일과 실제 태그 자식 면만 격리한
도해를 함께 제공한다. 격리 도해에는 주변 형상이 숨겨졌음을 명시했다.
`camera_manifest.json`은 회전 행렬, crop, 축척, 조명과 선택 면을 기록한다.
원본 형상에는 이동·변위·스무딩·decimation을 적용하지 않았다.

이미지는 기존 `tools/crease_projection.ps1`의 System.Drawing polygon
프리뷰다. 중립 회색 조명과 같은 카메라를 썼지만 painter 방식이므로 교차
면의 픽셀 가림은 근사적이다. ray tracing, Rhino 뷰포트 캡처 또는 beauty
render라고 표시하지 않았다. 이미지 생성이나 변위 텍스처는 사용하지 않았다.

공식 외부 HDMola를 활성화한 최신 전체 repository gate는 **793 passed /
29.95초 / zero skips**다. 새 검증은 event→crease 뒤의 실제 descendant
선택, on-disk export, 카메라 회전의 거리 보존, 실패한 국소 생성자만
제외하는 처리의 원본 불변성, 동결 입력 변경 시 재사용 거부를 확인한다.
preset 수치 자체를 재확인하는
테스트는 추가하지 않았다.

## Rhino와 다음 디자인 단계

세 안 모두 전체 해상도 3DM으로 저장했고 설치된 **RhinoCommon
8.18.25100.11001**로 실제 파일을 다시 읽었다. XYZ와 방향 있는 면 배열은
정확히 일치한다. 실제 `RhinoDoc.OpenHeadless`에서도 각 파일이 mesh 한
객체로 열린다. 객체명은 `<ID>_DESIGN_FULL_RESOLUTION`, 레이어는
`TASK24_<ID>`이며 실제 GUID는 import evidence에 기록했다.

표시용 normal만 계산했다. welding, triangulation, remeshing, thickening,
스무딩 또는 충돌 복구를 하지 않았다. `renders/native`의 클레이 프리뷰는
이 **실제 3DM 재읽기 데이터**에서 만든다. 원본 OBJ와 구성 체크포인트도
별도로 보존한다.

숨김 Rhino 애플리케이션의 뷰포트 캡처 시도는 반환하거나 이미지를 생성하지
못했고 이 태스크의 프로세스만 생성 시각을 확인해 종료했다. 관련 기록과
시도 소스는 `dcc/viewport_attempt.json`, `dcc/failed_capture_source.ps1`이다.
정상 작동한 NoWindow 파일 검증 경로와 구분한다. **실제 interactive
viewport / 최종 Hero render는 미검증**이다. 내보내기·native 재읽기와
target-format 프리뷰 준비는 확인했지만 완성 렌더나 제작 준비를 선언하지 않는다.

Rhino에서 `dcc/H1.3dm`을 Open하면 원래 원점과 Z-up 방향으로 열린다.
단위는 아직 None이므로 단위가 확인된 뒤 문서 단위를 지정한다. 모델을
임의로 rescale하지 않는다. `Zoom Extents` 후 Shaded/Arctic로 검토할 수 있다.
지면 접점, 실제 통과 clearance, 구조·조립과 최종 재질/조명은 후속 건축
디자인에서 결정할 사항이다. print-ready watertightness나 voxel 변환을
이번 단계의 필수 조건으로 쓰지 않았다.

## 재현과 열기

아티팩트 루트는 `E:\CHESHIRE_DATA\task24`다. 큰 체크포인트는 `designs`,
최종 OBJ 사본은 `meshes`, native 파일은 `dcc`, 이미지와 작은 검토 ZIP은
`review`에 있다. ZIP에는 큰 메시와 DLL을 넣지 않는다.

CHESHIRE 소스 커밋에서 Python 3.12, COMPAS 2.15.1, pythonnet 3.0.5,
기존 CoreCLR/.NET8과 공식 HDMola를 사용한다. Rhino export에는 설치된
Rhino 8과 Windows PowerShell/System.Drawing이 필요하다. 추가 renderer를
설치하지 않았다.

검토 ZIP의 `inputs`, `recipes`, `input_identity.json`을 새 artifact root에
복사하면 전체 Task23 atlas 없이 최종 세 안을 실행할 수 있다. DLL 경로는
기존 ignored local setting에서 읽는다.

```powershell
$task24Root = 'E:\CHESHIRE_DATA\task24_replay'
$task24Dll = (Get-Content output/local_settings.json -Raw | ConvertFrom-Json).mola_dll_path
.\.venv\Scripts\python.exe examples\hero_design_sprint.py --output-root $task24Root --run H1 H2_R1 H3_R3 --dll $task24Dll
.\.venv\Scripts\python.exe examples\hero_design_views.py --output-root $task24Root --names H1 H2_R1 H3_R3 --tag final
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\hero_rhino_export.ps1 -ArtifactRoot $task24Root -NamesCsv H1,H2_R1,H3_R3 -InputTag final
.\.venv\Scripts\python.exe examples\hero_design_views.py --output-root $task24Root --names H1 H2_R1 H3_R3 --tag native --rhino
```

## 목표와 남은 차이

[Digital Grotesque I](https://michael-hansmeyer.com/digital-grotesque-I)의
초기 큰 변화가 후속 작은 구성에 전달되는 원칙은 실제 event 자식 선택과
세대 사이의 구성에서 부분적으로 구현했다. 전체 형상·중간 분기·작은
기하의 관계는 있지만 많은 장식은 큰 판 뒤에 숨거나 반복적인 끝부분으로
남는다. 지지부의 어휘도 상부만큼 풍부하지 않다.

[Digital Grotesque II](https://michael-hansmeyer.com/digital-grotesque-II)가
설명하는 genus 변화, 여러 규모의 공극과 서로 엮인 피부를 재현한 것은
아니다. 사용한 기존 CC와 disk 교체 장식은 이번 조합에서 그러한 위상
변화를 만들지 않았다. 실제 시점 변화와 깊은 교차는 확인했지만 균형 잡힌
다층 공간과 정돈된 간극은 부족하다. 별도 알고리즘 연구나 Task25를
자동으로 시작하지 않는다.
