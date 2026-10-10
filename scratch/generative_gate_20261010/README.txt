CHESHIRE — 재사용 가능한 게이트 생성 파이프라인
작업 영역: scratch/generative_gate_20261010

최우선 최신 시험 — Tissue 결합 방식
원본 TARGET 체크포인트를 보존하는 것과 최종 출력에 불투명한 타깃 면을
전부 남기는 것을 구분한다. 이제 그 차이를 실제 메시 세 개로 비교한다.
1. 01_overlay: Tissue LAST + 원본 타깃 전체 (이전 방식).
2. 02_replace_selected: 실제 Tissue UNUSED. 선택된 원본 면을 제거하고
   생성 셀과 미선택 면을 결합한다.
3. 03_tissue_only: 실제 Tissue LAST만. 타깃은 렌더와 출력에 포함하지 않는다.
입력 셀, 타깃, 선택 면, 크기, 깊이, offset은 세 결과에서 동일하다.
높이 증폭으로 구멍을 드러내는 시험이 아니다.

재실행 (프로젝트 폴더에서 새 출력 경로 사용)
..\..\.venv\Scripts\python.exe -B compare_tissue.py --target-stage runs/hierarchy_microfold23/19_crease_subdivide --mapping-stage runs/micro_simple_tissue23/20_tessellate --input inputs/neutral --output runs/my_tissue_comparison
compare_tissue.py는 기존 공통 engine.tessellate와 headless Tissue를 호출하는
체크포인트 후속 실행기다. 후보별 전용 모델링 좌표나 장식을 만들지 않는다.
--target-stage와 --mapping-stage를 다른 완료 실행으로 교체할 수 있으며,
저장된 매핑 관측 좌표가 타깃과 정확히 같은지 먼저 확인한다.
새 중립 입력은 run.py로 베이스와 첫 매핑 체크포인트를 만든 뒤 같은 방식으로
비교한다. 실제 ALICE 연결로 주장하지 않는다.

출력: runs/tissue_composition23/{01_overlay,02_replace_selected,03_tissue_only}
각각 OBJ/PLY, 정면/사시/확대 렌더, 상태 및 검사 기록을 저장한다.
tissue_comparison.html에서 같은 카메라로 비교한다.
검사: test_runs/tissue_combine_7.xml (18개 통과).

UNUSED의 열린 경계는 의도된 면 제거의 결과이며 폐쇄 솔리드 검사를
억지로 통과시키거나 자동으로 구멍을 메우지 않는다. 별도 표면 검사로
유한 좌표, 0면적, 비다양체 모서리, 방향, 대칭 및 파일 재로드를 확인한다.
현재 단순 셀은 인접 셀/미선택 타깃 경계와 용접된 연속 표면이 아니다.
선택은 전체 688,128면 중 6,000면(약 0.87%)이므로 LAST에는 국소 패치만
남는다. 전체 게이트의 조직화를 완성했다는 뜻이 아니다.
이 표면 출력은 닫힌 메시를 요구하는 현재 CC/DS/solid Boolean의 후속
입력으로 바로 사용할 수 없다. 원본 타깃 기반 연산과 표면 출력은 구분한다.

PATCH 검토
Tissue 공식 문서와 external/tissue/tessellate_numpy.py를 확인했다.
LAST는 마지막 생성 조직, UNUSED는 생성 조직+사용하지 않은 타깃 면이다.
PATCH는 subdivision 이전 사각면과 마지막 Subdivision/Multires modifier를
함께 사용한다. modifier 없는 현재 baked 타깃에 PATCH 옵션만 주면 QUAD로
폴백한다. 이번 동일 타깃 비교에는 QUAD를 유지했다. PATCH 연결은 아직
구현하지 않았으며 이전 cage와 crease modifier의 평가 결과부터 검증해야 한다.
https://github.com/alessandro-zomparelli/tissue/wiki/Tessellate

아래는 이전 실험 기록이다. 최신 의도는 위의 '선택 면 치환' 시험이 우선한다.

최신 Tissue 실험 — INPUT과 TARGET의 역할
다발의 큰 흐름은 subdivision으로 만든 TARGET이 담당한다.
INPUT은 components/simple_micro_cell/component.json의 단순 다공성 셀이다.
기존 cell12 메시를 그대로 사용하고 매핑 크기만 작게 지정했다.
configs/micro_simple_tissue.json은 microfold 타깃 생성 19단계 뒤 Tissue를
적용한다. opening/lintel/전이부와 현재 곡률을 이용해 면을 선택한다.
keep_target=true로 타깃 좌표와 면을 보존하며 전체 평활화를 추가하지 않는다.
이는 타깃 몸체를 관통하는 다공성 재료가 아니라, 보존된 타깃에 작은
구멍 있는 셀을 덧붙이는 실험이다. 다발의 시각적 가독성은 렌더로 비교한다.
bundle_curved/strand_curved와 micro_bundles/micro_strands는 방향 수정 전
개발 기록이며 현재 권장 INPUT이 아니다. micro_bundles23 실행은 중단했다.

단순 셀 포함 전체 재실행 (새 출력 폴더 사용)
..\..\.venv\Scripts\python.exe -B run.py --input inputs/neutral --config configs/micro_simple_tissue.json --output runs/my_simple_tissue
동일한 기존 타깃을 재사용하여 Tissue만 실행
..\..\.venv\Scripts\python.exe -B run.py --input inputs/neutral --config configs/micro_simple_tissue.json --output runs/my_simple_tissue_resume --resume-stage runs/hierarchy_microfold23/19_crease_subdivide
체크포인트는 COMPLETE인 원본 실행, 동일 입력 SHA, 동일 seed, 동일 단계
설정 prefix일 때만 재사용한다. 다른 입력이나 seed라면 전체 실행한다.
--input inputs/neutral_wide 또는 같은 입력 계약의 새 폴더로 바꿀 수 있다.
--seed 71로 다른 후보를 만든다. 실제 비교 실행 여부는 run.json으로 확인한다.

중단된 방향 — 노출 높이 비교
처음 micro_simple_tissue23은 전체 렌더에서 구멍이 잘 읽히지 않았다.
선택 면의 한 변 길이 중앙값은 입력 높이의 약 0.3%이며, offset 0.35에서
셀 일부가 타깃 표면 안쪽으로 매핑된다. 보존 검사 통과가 시각적 성공을
의미하지 않는다. configs/micro_exposed_tissue.json은 동일 셀 메시와 동일
타깃을 사용하되 xy_scale 0.7→1.0, z_factor 0.35→0.65, depth 1.6→2.2,
offset 0.35→0.95만 바꾼 비교였다. 이 방향은 사용자 정정으로 중단했고,
micro_exposed_tissue23은 대칭 후 닫힌 위상 검사에도 실패했다. 정상 결과로
제출하지 않는다. 추가 접힘 강도는 바꾸지 않았다.
tissue_focus.json은 실제 선택 면에서 정한 전후 공통 확대 카메라다.
셀끼리/몸체와의 겹침은 남아 있을 수 있다. 관통 다공성 몸체로 해석하지 않는다.

최신 비교안 — 아래 초기 결과 목록보다 우선
- hierarchy_twist23: 기존 Blender Simple Deform으로 기둥 꼬임 강화.
  현재 우측 지지부의 중심과 영역 가중치로 회전축/전이 범위를 결정한 뒤
  변위를 반사한다. 평활화와 면 연결 변경은 하지 않는다.
- hierarchy_sixfold23: 접기→능선 돌출 6회. 마지막에 실제 Blender의
  Subdivision Surface와 crease_edge 속성으로 현재의 날카로운 모서리 보존.
- hierarchy_microfold23: 큰 접힘 3회 뒤 먼저 crease subdivision으로
  해상도를 높이고 작은 접힘 3회. 끝에 다시 crease subdivision.
  단순 반복의 고주파 샘플링 한계를 줄이는 비교안이다.
- region_fibers23의 Tissue 실험은 별도로 그대로 보존한다.
micro_simple_tissue23이 최신 microfold 타깃에 단순 셀을 덧붙인 비교안이다.
해당 run.json이 COMPLETE인지 먼저 확인한다.

최신 비교안 실행
..\..\.venv\Scripts\python.exe -B run.py --input inputs/neutral --config configs/hierarchy_microfold.json --output runs/my_microfold
..\..\.venv\Scripts\python.exe -B run.py --input inputs/neutral --config configs/hierarchy_twist.json --output runs/my_twist
꼬임 강도는 support_twist의 angle(라디안), 추가 접힘 깊이는 pleat_flow의
depth(입력 높이로 정규화한 단위)로 조절한다. depth가 있으면 amount보다 우선한다.
변형 강도가 크면 자기 교차가 생길 수 있으며, 현재 기본 검사가 이를 모두
검출하지 않는다. 형태를 비교해 선택하는 설계 프로토타입이다.
render_regions.py 단계폴더 명령으로 저장된 실제 적용 마스크를 시각화한다.
validation_summary.json은 Tissue 후 타깃 보존, 다른 입력 비교, 원본 소스
보존 검사를 모은다. test_runs/final_checkpoint_6.xml은 17개 기능 테스트 결과다.

평탄화 제어의 실제 범위
CC fold-lock은 이전 단계의 강한 접힘 정점을 고정하지만 새 정점까지 모두
고정하는 것은 아니다. Blender crease subdivision도 모든 면의 위치나
주름 깊이를 완전히 보존하는 연산은 아니다. 현재 이면각으로 선택한
모서리에 높은 crease 값을 주어 둥글어지는 정도를 제어한다.
Tissue 타깃 보존은 별개로 직접 검사한다. 생성된 작은 조직과 타깃을
이어붙인 단계에서 타깃 좌표·면이 동일하고, 대칭 처리 후 원래 타깃
정점의 최대 위치 차이는 약 2.22e-16(내부 정규화 단위)였다.
최종 개구부 Boolean은 통로에 들어오는 부분을 자를 수 있다.
Blender의 headless Tissue 로그에 나타나는 'Viewport not in local view'는
해당 실행에서 tessellation 완료를 막지 않았으며, 실제 결과를 별도 검사했다.
참고 기능 문서:
https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/simple_deform.html
https://docs.blender.org/manual/en/3.6/modeling/modifiers/generate/subdivision_surface.html

현재 범위
최신 지시에 따라 실제 ALICE 데이터는 사용하지 않는다. inputs/neutral과
inputs/neutral_wide는 합성 중립 게이트다. 입력 메시, 개구부 다각형,
지지부/상부의 면 영역을 읽어 매 단계의 실제 기하에 연산을 적용한다.
특정 완성 모델을 크기에 맞춰 변형하는 방식이 아니다.
기존 연구 코드와 체크포인트는 수정하지 않고 가져와 사용한다.

우선 확인할 결과
- runs/region_fans23: 영역별 깊은 주름을 만든 타깃.
- runs/region_fibers23: 위 타깃의 마지막 단계에 작은 Tissue 조직을 추가한 실험.
- runs/hierarchy_base23: 다음 베이스. opening–lintel–전이부를 주 흐름으로
  묶고, 보조 변형의 가중치를 낮춰 조용한 영역과 구별한다. Tissue 미적용.
- runs/region_fans_wide23: 다른 중립 입력에 region_fans와 같은 설정 적용.
각 폴더의 run.json이 COMPLETE인 결과만 정상 완료 결과다.
FAILED 폴더는 원인 확인을 위한 개발 기록이며 제출 모델이 아니다.
조형적 완성 여부는 렌더를 보고 판단해야 한다. 높은 면 수는 그 증명이 아니다.

실행 — 현재 Windows 작업 환경의 PowerShell
Set-Location C:\Users\USER\CHESHIRE\scratch\generative_gate_20261010
..\..\.venv\Scripts\python.exe -B run.py --input inputs/neutral --config configs/hierarchy_base.json --output runs/my_base
..\..\.venv\Scripts\python.exe -B run.py --input inputs/neutral --config configs/region_fibers.json --output runs/my_tissue

출력 폴더는 항상 새로운 경로여야 한다. 기존 결과는 덮어쓰지 않는다.
--no-render는 메시와 측정 데이터만 저장한다.
--seed 71로 스칼라 초기장과 이를 쓰는 연산의 변화를 시험할 수 있다.
단, hierarchy_base의 큰 흐름은 기하로 결정된다. seed만 바꾸어도 반드시
큰 형태가 달라지는 것은 아니다. 큰 흐름의 변형에는 설정의 depth,
flow_angle, lintel_angle, frequency, fan_strength와 영역별 가중치를 사용한다.
후보마다 별도 모델링 스크립트를 쓰지 않는다.

다른 입력 생성 및 실행
..\..\.venv\Scripts\python.exe -B make_input.py --output inputs/my_gate --width 3.3 --height 3.2 --depth 0.8 --opening-width 1.9 --opening-height 2.2
..\..\.venv\Scripts\python.exe -B run.py --input inputs/my_gate --config configs/region_fans.json --output runs/my_gate_result

외부 메시 입력 계약
gateflow/input.py 및 inputs/neutral/gate.json 참조.
- schema: cheshire-neutral-input/1
- mesh: 입력 폴더 내 OBJ. 정점 v, 양의 1-based 면 인덱스 f, 삼각형/사각형.
- mesh_sha256: OBJ의 SHA256. 입력 변경 시 함께 갱신한다.
- axes: X_RIGHT_Y_FRONT_Z_UP. X 중심에 대한 양측 대칭, 닫힌 유효 메시.
- regions: support_left, support_right, upper에 해당하는 0-based 면 번호.
- openings: 주 개구부 하나의 profile_xz 다각형.
- source_kind: 실제 출처를 정직하게 기록한다.
높이로 내부 정규화한 뒤 원래 좌표계로 내보낸다. 개구부 다각형과 영역
경계는 실제 마스크 계산과 마지막 opening Boolean에 사용한다.
parameters와 depth_bounds의 모든 항목을 연산에 사용하는 것은 아니다.
현재 개구부의 깊이는 관통 Boolean으로 취급한다.
이 계약은 향후 ALICE 연결을 위한 경계일 뿐, ALICE 연동 완료를 뜻하지 않는다.

핵심 실행 단계
1. 기존 CHESHIRE의 가중 CC/DS로 타깃 해상도 확보.
2. 현재 메시의 그래프에서 높이 흐름과 opening까지의 측지 거리를 계산.
3. 그 장으로 방향성 주름을 만들고 국소적인 수렴/발산을 더함.
   fan 중심은 현재 곡률의 특징에서 선택하며 고정 장식 좌표를 사용하지 않음.
4. 현재 메시에서 능선을 다시 검출하여 별도의 normal_extrude 실행.
5. CC 및 기존 fold-lock으로 해상도를 높인 뒤 다른 규모의 주름/돌출 반복.
6. 선택적 Tissue는 충분히 변형한 타깃 뒤에만 적용.
7. 입력 opening 다각형으로 통로를 보호하고 OBJ/PLY 및 렌더 저장.
모든 단계에서 양측 대칭을 유지한다.

연산의 정확한 의미
pleat_flow는 흐름장을 이용한 법선 방향 주름 변위와 접선 방향 수렴이다.
종이를 접는 강체 회전이나 Hansmeyer 원본 구현의 완전한 복제는 아니다.
fold_field와 Freedom domains는 별도로 실제 국소 회전 구성을 사용한다.
CC/DS는 기존의 확장 subdivision 구현을 호출한다.
normal_extrude는 현재 정점 법선을 따라 실제 좌표를 이동한다.
MOLA의 면 돌출과는 구별된다. 현재 결과에 쓰지 않은 연산을 썼다고 세지 않는다.

영역별 위계
opening: 전달받은 profile_xz에 대한 현재 정점의 거리.
transition: 현재 메시의 상부/지지부 면 인접 경계에서 확산한 영향.
lintel: 상부 영역과 opening 근접도를 결합한 영향.
deformation: 현재 곡률 및 법선 변화에서 얻은 국소 특징.
hierarchy_base는 opening/transition/lintel을 주 흐름으로 놓고,
그 바깥의 deformation 가중치를 0.12로 낮춘다. 이전 region_fans는 0.7이다.
주 흐름의 방향은 lintel 영역에서 부드럽게 전환된다.
조용한 영역에는 낮은 주름 이득과 작은 안쪽 변위가 적용된다.
모든 실제 마스크와 변위는 operator_state.npz에 저장된다.

Tissue의 작은 INPUT과 TARGET
components/fiber14/component.json이 타깃과 독립된 실제 다공성 입력이다.
Tissue polyhedral_wireframe으로 만든 셀을 CC로 세분화한 뒤, mapping의
xy_scale과 z_factor로 좁고 긴 섬유성 비율을 지정한다.
Blender의 실제 object.tissue_tessellate가 타깃의 선택된 사각면에 매핑한다.
타깃의 현 기하와 법선으로 방향/깊이를 계산한다. 단순 이미지 텍스처가 아니다.
--component 다른파일.json 으로 입력 부품을 교체할 수 있다.
새 부품 생성 예:
..\..\.venv\Scripts\python.exe -B make_component.py --kind fiber --thickness 0.14 --output components/my_fiber

keep_target=true이면 기존 타깃의 정점과 면을 그대로 보존하여 추가한다.
어댑터는 Tissue 직후의 좌표 오차 0과 면 연결 동일성을 검사한다.
이 검사의 범위는 이후 대칭 처리와 최종 opening Boolean 이전이다.
후속 전체 평활화/voxel fuse는 현재 Tissue 레시피에 없다.
중요한 한계: 타깃과 작은 닫힌 조직들을 합쳐 저장한 다중 쉘 조립체다.
서로 교차할 수 있으며 하나의 Boolean union solid라고 주장하지 않는다.

실제로 연결한 기술
- CHESHIRE reference_subdivision / polygon_dual_subdivision: CC/DS, fold-lock.
- SciPy: 현재 그래프의 harmonic solve, 거리, 확산, 공간 검색.
- Libigl: 현재 곡률/주방향; 25,000 정점 이후에는 cotangent 평균 곡률.
  밀도가 높은 단계의 주방향은 계산하지 않는다.
- Tissue + headless Blender: 실제 다공성 셀 생성과 component tessellation.
- Manifold3D: 입력 opening의 Boolean subtraction.
- Trimesh: 메시 입출력, 기본 위상 검사; Pyrender/Cycles: 실제 메시 렌더.
다음 기존 기술도 공통 엔진의 다른 레시피에서 실행했다:
- HDMola + COMPAS: 면 돌출 및 생성된 cap에 대한 후속 성장.
- Astra/Freedom: adaptive 연산과 국소 회전 영역.
- SciPy/Scikit-image: 선택적 voxel fuse와 marching cubes.
  둥글어짐/미세 조직 소실 문제로 최신 주름·Tissue 레시피에서는 제외했다.
CGAL, Directional/SDQ, Differential Growth, 완전한 SDF 엔진을 현재 결과에
사용했다고 주장하지 않는다. 별도 도구를 무조건 삽입하지 않는다.

의존성과 이식
gateflow/runtime.py는 기존 CHESHIRE/src, CHESHIRE_ASTRA/src,
기존 작업의 deps와 이 작업의 격리 deps를 사용한다.
외부 버전과 기존 파일 SHA256은 environment.json, Python 목록은 requirements.txt.
경로 변경 시 CHESHIRE_ROOT, CHESHIRE_ASTRA_ROOT, CHESHIRE_EXTERNAL_DEPS,
CHESHIRE_BLENDER를 지정한다. MOLA에는 Libraries/HDMola/1.0.0/HDMola.dll과
.NET 런타임이 필요하다. 모든 연산이 다른 운영체제에서 검증된 것은 아니다.
Tissue upstream의 GPL 라이선스는 external/tissue에 보존되어 있다.
Blender GUI 조작은 요구하지 않는다.

검증 및 증거
..\..\.venv\Scripts\python.exe -B -m pytest tests/test_pipeline.py -q -p no:cacheprovider --basetemp test_runs/새로운폴더
각 run.json: 실행 상태, 사용 소스 SHA256, 입력/설정 SHA256, 단계별 검사,
기본 위상, 연결 요소 수, 대칭 오차, opening Boolean, OBJ/PLY 재로딩 검사.
각 단계: mesh.obj/.ply, observations.npz, operator_state.npz, state.npz,
stage.json, views/front.png 및 oblique.png.
최종: result.obj/.ply, views, progression.png. Cycles 폴더는 별도 실물 메시 렌더.
기본 검사는 닫힘, 방향 일관성, 유한 좌표, 0면적 삼각형, 양의 부호 체적이다.
모든 자기 교차의 부재, 구조 강도, 제작 가능성을 보증하지 않는다.

참고에서 실제로 취한 힌트
Hansmeyer 2010 Subdivision Beyond Smoothness: 비균일/비정상 가중치,
생성된 정점 종류의 차등 처리, subdivision과 법선 돌출의 결합.
일반적인 평활 subdivision 반복만으로 복잡성이 사라지는 문제를 피한다.
mirror.pdf: 절단/반사를 통한 대칭 연산. 현재는 중앙 양측 대칭 제약이며,
논문의 모든 재귀 대칭 규칙을 구현한 것은 아니다.
Digital Grotesque 공식 이미지: 크기별 조직 위계와 수렴/발산을 조형 참고로 사용.
https://www.michael-hansmeyer.com/digital-grotesque-I
https://michael-hansmeyer.com/digital-grotesque-II.html
https://github.com/alessandro-zomparelli/tissue
Tissue 매핑은 별도로 연결한 구현이다. 2010 논문의 다공성 기법과 동일하다고
주장하지 않는다. 논문/이미지는 참조 자료이며 생성 메시가 아니다.
