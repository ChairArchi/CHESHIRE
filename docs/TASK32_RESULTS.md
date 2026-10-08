# TASK32 — 관계를 가진 형상 생성 연구 결과

**판정: PARTIAL.** 실제 메시의 parent–child 구조를 생성하고 제어하는 경로는 확보했다. 디지털 그로테스크의 풍부한 Macro–Meso–Micro 장식에 도달했다고 판단하지 않는다. 검사를 통과한 결과에도 블록 형태와 넓은 빈 영역이 강하다. 최종 디자인을 선정하지 않았다.

2026-10-09에 실행·검증한 결과다. 요청한 연구 기한은 2026-10-10이며, 토요일에 실행하지 않은 연구를 실행한 것으로 서술하지 않는다.

- 브랜치 `experiment/task32-relational-morphology`; 시작점 `17c0415b8d7bdead8763949bfa8d95f18fad908c`.
- **68개 연구 대조**: 64개 완주, 교차 검사에서 중단한 4개. 완주는 조형 성공/solid 유효성 판정이 아니다.
- 별도 복구 시험 5개: 4개 성공, 1개 실패 후 수정·재검증. 전체 실행 ID 73개.
- 외부 산출물 `E:/CHESHIRE_DATA/task32`: 실패, 파라미터, 소스, native state, 이미지, depth mask, 단면, 문헌을 보존했다.
- 기존 Task31 **1,539개 파일**의 크기·SHA256이 작업 전후 동일하다. ALICE HEAD `6fcfc42736e60dbd9254a368c06d99c2b2c403a0`과 기존 `notify.ps1` 미추적 상태도 그대로다. 기존 Task01–31 알고리즘·테스트 기준을 변경하지 않았다. push 없음.

## A. Research Review

### 기존 연구에서 확인한 병목

새 알고리즘 전에 실제 Task23–31 코드·연구 기록·이미지를 검토했다. [연구별 상세 표](TASK32_RESEARCH.md)와 `analysis/reviewed_prior_images.json`의 원본 경로·해시가 근거다. 기존 연구 평가와 산출물은 수정하지 않았다.

Task23의 깊은 constructive detail, Task25의 FLOW/curl, Task26의 material coordinates/reflection, Task27의 geometry feedback, Task28의 generational weighting, Task29의 point classes/local scale/locks, Task30의 CC↔DS 비교, Task31의 persistent regional modes와 CHANNEL은 이미 존재한다. 단순히 depth·feedback·crease가 없었다고 진단할 수 없다. 실제 whole views에는 cell motif 반복, 넓은 lobes/neck과 약한 중간 규모 관계가 남았다.

Task28의 후기 smoothing은 특정 progression에서 세부를 약화시켰지만 모든 Task31 약점의 원인으로 확정하지 않았다. PROFILE carrier와 단순 gate를 혼합해 알고리즘 효과로 비교하지 않았다. 재실험에서는 multi-face cap, intrinsic field, scope inheritance, 접촉 검사 등 달라진 조건을 명시했다.

추가 검사에서 기존 Task31 G2는 전체 **2,432개 triangle** 검사 중 transverse contact 검출 상한 256쌍에 도달했다. G5에서도 표본 9쌍이 검출됐다. G2를 재사용한 C09/C10/D10/E06의 문제를 모두 새 연산 탓으로 돌릴 수 없다. 원본을 수리하거나 폐기하지 않았다. Task31 G5 Euler는 0이며 이번 단순 gate 계열은 2다. 기존 내부 CHANNEL과 U gate의 중앙 빈 공간은 서로 다른 개구부다.

### 문헌·원형·이번 응용

| 출처와 실제 확인 범위 | 적용과 한계 |
|---|---|
| [Gingras & Kry, 2019](https://www.cs.mcgill.ca/~kry/pubs/gi2019/Reaction_Diffusion_Shell_Growth.pdf), pp.1–5 방법·제약 | 원형은 Gray–Scott/ARCSim plastic-strain growth/adaptive remeshing. 이번 graph-spring surrogate는 RD나 물리 thin-shell을 구현한 것이 아니다. |
| [Li et al., Field-Guided Shape Grammars](https://peterwonka.net/Publications/pdfs/2011.TVCG.Li.FieldGuidedGrammar.TechnicalReport.pdf), pp.4–8 및 11 | field/scope 관계를 검토했다. tensor design, hyperstreamline, Bullet collision/merge를 복제하지 않았다. 이번 disk sweep은 별도 직접 구성이다. |
| [Eck et al., Multiresolution Analysis](https://hhoppe.com/mra.pdf), pp.2–3 및 8 | 규모별 표현의 근거. 이번 phase hierarchy는 wavelet decomposition이나 arbitrary remeshing의 구현이 아니다. |
| [Vallet & Lévy, Manifold Harmonics](https://www.cs.jhu.edu/~misha/ReadingSeminar/Papers/Vallet08.pdf), pp.2–4 | 일반화 eigenproblem을 구현했다. barycentric lumped mass를 사용하며 원논문의 전체 DEC/out-of-core solver를 재현하지 않았다. |
| [Meyer et al., Discrete Differential-Geometry Operators](https://www.multires.caltech.edu/pubs/diffGeoOps.pdf), 관련 곡률 유도와 pp.9–13 | cotan mean curvature/angle-defect Gaussian curvature를 적용했다. mixed Voronoi 대신 barycentric lumped area를 사용했다. |
| [Banchoff, Parallel Surfaces](https://www.math.brown.edu/tbanchof/balt/ma106/dtext64.html), 공식 regularity 식 | reciprocal curvature는 일정 offset의 국소 특이점과 관련된다. 가변 offset의 tanh 제한은 응용 heuristic이며 global collision 보증이 아니다. |
| [Desbrun et al., Implicit Fairing](https://people.eecs.berkeley.edu/~jrs/meshpapers/DesbrunMeyerSchroderBarr.pdf), §2.2–2.5 및 §4.3–5.1 | backward-Euler scalar diffusion을 log-bound에 적용했다. 전체 geometry fairing/exact volume preservation의 재현은 아니다. |
| [Geometry Central](https://geometry-central.net/surface/geometry/quantities/), 공식 distance/quantity 문서와 MIT LICENSE | cotan/lumped area/geodesic 정의 확인. 이번 U arc는 정확한 geodesic이 아니다. 설치·코드 복사 없음. |
| [Developability of Triangle Meshes](https://www.cs.cmu.edu/~kmcrane/Projects/DiscreteDevelopable/), 공식 abstract/GPLv2 LICENSE만 | flattenable surface 목표는 gate 장식에 자동 대응하지 않는다. 본문·solver를 검증했다고 주장하지 않는다. 설치·복사 없음. |
| [Ready](https://github.com/GollyGang/ready), README와 GPL-3.0 표시 | mesh RD 참고 구현. 개별 solver와 전체 license file 확인은 미완료다. 실행·재사용 없음. |

`references/`에 PDF·SHA256·추출 기록을 보존했다. 초기 `fitz` 미설치로 실패한 추출 기록을 남긴 뒤 기존 Task29의 선택적 reader로 추출했다. 텍스트 추출 성공과 실제 읽은 범위를 구분한다. upstream 구현 코드를 복사하거나 실행하지 않았다.

## B. Experimental Results

### 구현한 메커니즘

기본 입력은 기존 `gate_input('RECT', False)`의 동일한 단순 gate, G0 **74 V / 80 F**다. 단위는 원본 model unit으로 남겼다. 다른 기본 carrier나 특정 참고 이미지의 형태를 도입하지 않았다.

| 메커니즘 | 수학·geometry·topology의 의미 |
|---|---|
| Metric growth | 공간별 target edge length를 지정하고 length error + graph bending surrogate + anchors를 최소화. 별도의 algebraic volume penalty 비교. gradient를 finite difference로 검증했다. 물리 shell folding으로 주장하지 않는다. |
| Carrier hierarchy | U arc/angle의 parent envelope/phase에 finer field를 연결한 실제 normal displacement. shoulder chart discontinuity는 의심 요인이며 확정 원인이 아니다. |
| Intrinsic hierarchy | cotan `Lφ=λMφ` 좌표에서 부모 phase/envelope에 finer phase를 결합. topology는 유지한다. eigensystem residual·mass orthogonality를 검증했다. |
| Curvature/transport/diffusion | 국소 curvature/tanh 제한, `(M+ℓ²L)u=Mf` log-bound diffusion, material interpolation과 실제 zero-weight CC stencil의 field 전달을 비교. bound diffusion은 개별 국소 제한을 완화할 수 있다. |
| Connected disk grammar | multi-face cap을 여러 boundary ring으로 sweep. face scope/cap/level을 CC와 실제 child 선택으로 전달. V/E/F connectivity는 바뀌고 genus는 유지한다. 직접 구성한 branching이며 새로운 subdivision 수식/emergent branching은 아니다. |
| Projection/contact admission | projected boundary 교차와 cap orientation을 검사. initial plane 검사만으로 curved sweep을 보증할 수 없어 root/child/final 전체 triangle 검사를 추가했다. |

각 immutable 정의는 `definitions/`의 JSON이다. 단계별 native NPZ에는 mesh/rest/classes/anchors/generation과 CC parent map/local scales, growth state, branch scopes, spectral basis/domain/coordinates를 저장한다. topology edit에서 정의되지 않은 spectral 좌표 lineage는 종료하고 직전 상태를 보존한다.

### 연구 계열과 비용

경과는 guard가 측정한 실행 시간이며 solver 시간만의 값이 아니다. D08의 검증 재개 비용도 포함한다. peak는 0.5초 간격 process tree + driver RAM 표본이며 true peak/GPU VRAM 측정치가 아니다.

| 계열 | 개수 | 조건·관찰 | 경과 범위 | 최대 표본 RAM |
|---|---:|---|---:|---:|
| P | 11 | neutral, growth .25/.55/.9, anisotropy, field coupling/twist | 2.13–2.36 s | 179 MiB |
| R | 8 | roots/children, neck/twist/3rd level, growth 결합 | 3.73–9.44 s | 303 MiB |
| S | 7 | modes/amplitude, coupling off, remeasure | 2.17–2.72 s | 193 MiB |
| V | 6 | growth와 volume penalty/bending/anisotropy | 2.23–3.70 s | 178 MiB |
| C | 10 | curvature limit, G2/G3 birth, 실제 Task31 prefix | 2.26–5.27 s | 238 MiB |
| D | 10 | bound diffusion, CC field transport, 규모별 ablation | 4.72–6.79 s | 380 MiB |
| E | 6 | macro 입력과 분기 결합 | 4.78–8.86 s | 306 MiB |
| F | 4 | footprint/clearance, 분기 직후 검사; 모두 중단 | 11.99–22.99 s | 187 MiB |
| G | 3 | projection admission과 제한된 contact screen | 13.70–27.57 s | 240 MiB |
| H | 1 | G02 이후 neutral CC 추가 | 22.98 s | 591 MiB |
| I | 2 | straight child, footprint .24/.18, 전체 contact screens | 47.83–48.88 s | 293 MiB |

개별 값·파라미터·소스·검사 상태는 `analysis/experiment_summary.csv`와 JSON에 있다. 최대 H01은 383,296 F다. RAM 기반 12 GiB/available RAM guard, 2 GiB 여유 RAM, process birth/family 확인, 단계 전 RAM·disk forecast와 저장 reserve를 유지했다. 임의 elapsed-time cutoff는 없다. optimizer maxiter는 명시된 수치 예산이며 수렴 여부를 기록했다.

### 실제 판정을 바꾼 대조

| 대조 | 확인된 사실 | 판단 |
|---|---|---|
| S01–S07 | 모두 최종 contact-positive 표본 | eigensystem 정상 상태와 geometry 안정성은 별개다. |
| V01–V06 | volume ratio 약 .99969–.99999 수렴; 교차 표본은 남음 | algebraic volume은 local thickness/hierarchy 해결책이 아니다. |
| D06 → D07 | macro-only D06 경고 0; meso 추가 후 S06 전체 검사 17쌍 | 이 조건의 불안정성은 micro 이전 meso에서 시작한다. 모든 folding에 대한 일반 명제는 아니다. |
| D08 | 최종 155,648 triangle 전체 transverse 검사 0, quad fan 경고 0 | 유효한 field 비교 기준. 전체에서는 반복 띠가 강하다. |
| E02/F01 | E02 최종 표본 0이나 root 전체 87쌍. F01 12쌍이 오른쪽 상부 patch에 집중; projected boundary 한 번 교차 | 최종 표본/smoothing 후 이미지로만 안전성을 판단할 수 없다. 높이 조절만으로 해결되지 않았다. |
| G02 | 표본 통과 후 child 전체 13쌍, 최종 전체도 13쌍 | G02를 안전 후보에서 제외. 초기 plane admission은 curved path를 보증하지 않는다. |
| G02 → I01 | child bend .2 → 0. 같은 5 roots / 7 children. root 11,456, child 47,912, final 191,648 triangle 전체 검출 0 | 이 설정에서는 child sweep 휨이 교차 원인이라는 강한 대조 증거다. |
| I01 → I02 | child radius .24 → .18; 실제 7 → 10 children. root 11,456, child 48,044, final 192,176 triangle 전체 검출 0 | smaller footprint는 모든 두-child 제안을 수용했다. 명목 count로 대체하지 않는다. |
| G02 → H01 | 4배 면 수 이후 전체에서 읽히는 위계 변화가 작음 | 추가 depth 할당 근거가 약하다. G02 접촉 문제의 해결로 주장하지 않는다. |

I01은 **95,826 V / 95,824 F**, I02는 **96,090 V / 96,088 F**다. 두 결과는 유한 좌표, nondegenerate diagnostic triangles, 한 connected component, 모든 vertex link cycle, oriented closed edge incidence, Euler 2, opposed quad-fan 0을 확인했다. G01 root-only도 최종 전체 transverse 검사 0이다.

검출기는 coplanar/tangent/shared-vertex 및 adjacent-face embedding 문제를 제외한다. **전체 triangle 검사 0도 모든 solid/제작 유효성의 증명은 아니다.** 근거가 약한 초기 PASS는 이후 전체 검사 결과로 철회했고 원본 출력은 보존했다.

### 실제 메시 비교 이미지

- [Task31 최종 G8 / I01 / I02](E:/CHESHIRE_DATA/task32/renders/FINAL_TASK31_G8_COMPARISON.png): front / oblique / lintel.
- [I01/I02 크게 보기](E:/CHESHIRE_DATA/task32/renders/straight_children.png).
- [같은 축의 실제 단면](E:/CHESHIRE_DATA/task32/renders/FINAL_SECTIONS.png), [PDF](E:/CHESHIRE_DATA/task32/renders/FINAL_SECTIONS.pdf).
- [D08/E02 progression](E:/CHESHIRE_DATA/task32/renders/PROGRESSION.png), [중단한 분기의 실제 geometry](E:/CHESHIRE_DATA/task32/renders/REJECTED_CONSTRUCTION.png).

G8 비교는 camera pose/width/target, flat normals, clay, lights, GPU backend, **1400×1400 px** 일치를 검증했다. Task31은 5,021,696 F의 기존 렌더이며 현재 두 결과와 면 수가 다르다. 원본 이미지를 바꾸거나 500만 면의 GPU buffer를 재적재하지 않았다. 기존 G8 파일과 해시를 참조하는 증거를 기록했다.

모든 계열의 front/oblique/lintel 이미지·native mesh·visibility hash는 `renders/<tag>/manifest.json`에 있다. geometry hash와 실제 단면으로 변화가 형상임을 확인했다. 중앙 portal 고정 ROI는 실제 depth mask에서 정면 배경이 유지됐다. 3D clearance, 내부 CHANNEL, genus 또는 미적 점수로 사용하지 않는다.

## C. Morphology Assessment

**Macro:** 중앙 빈 공간, 두 지지부와 상부를 읽을 수 있다. intrinsic 좌표 변형은 한쪽 팽창/다른 쪽 수축을 만든다. 대칭·비대칭의 미적 우열을 미리 정하지 않았다. 거부된 patch를 억지로 대칭 복제하지 않았다.

**Meso:** I01/I02에 여러 면으로 연결된 넓은 root와 parent cap에서 나온 실제 child가 존재한다. cell-level 표면 질감과 다른 구성 요소가 전체에서 읽힌다. 그러나 부착된 블록과 넓은 전이 면의 인상이 강하다. 유기적인 접힘이나 전체 장식 조직화가 Task31보다 우수하다고 선언하지 않는다.

**Micro:** S/C/D는 부모 좌표에 세부를 수학적으로 연결했지만 반복 띠와 교차를 만들었다. I 계열 child는 관계가 있지만 풍부한 pleats/미세 분기/엣지 위계까지 확보하지 못했다. scale relationship의 기술적 존재와 조형적으로 읽히는 위계는 별도의 결론이다.

자동 지표로 디자인을 선정하지 않았다. D08, G01, I01/I02는 기술적 재현 기준이며 작품 순위가 아니다. 최종 미적 판단은 사용자에게 남긴다.

## D. Next-step Recommendation

1. **I01/I02에서 작은 설계 연구를 이어 간다.** parent 형태와 child 위치/footprint/방향을 각각 통제하고 사용자가 선택한 방향에서 전이·접힘을 발전시킨다. 전체에서 읽히는 효과를 확인한 뒤 배리에이션을 만든다.
2. **curved child를 되돌릴 때 path/간섭을 검증한다.** 현재 normal-plane admission은 curved sweep 보증이 아니다. 단계별 sweep 방향·경계 간 간섭 또는 contact-aware path를 작은 구조에서 확인한다. Boolean/대형 solver는 이번 범위에 넣지 않았다.
3. **Micro를 마지막 point-class 증폭으로 채우지 않는다.** 실제 parent scope와 국소 크기·곡률에 연결된 detail을 별도로 비교한다. 제어 영역과 provenance는 확보했지만 detail 메커니즘은 미해결이다.
4. **Task31은 별도 선택지로 유지한다.** 기존 결과·CHANNEL/state 모두 보존했다. G2를 안정적인 입력으로 가정해 혼합하지 않는다. 내부 opening이 필요한 새 prototype에는 독립 검증이 필요하다.
5. **대규모 물리 solver와 depth 증가는 보류한다.** spring surrogate는 shell folding을 대신하지 못했다. 실제 thin-shell/RD/충돌 체계에는 별도 fidelity 검증이 필요하다. H01 결과는 지금 더 큰 face budget을 정당화하지 않는다.

## 검증·보존·복구

- 전체 테스트 **904 passed**: 기존 886 + 신규 18. 실제 HDMola DLL/coreclr 사용. 기준 완화·skip 없음. 마지막 audit-full 통합 변경의 관련 4개 테스트도 통과했다.
- 신규 테스트는 gradient, rigid/scale invariance, eigensystem, diffusion conservation, 실제 surgery/vertex links/contact pair equivalence, rejected checkpoint와 topology-edit 재개를 검증한다.
- D08 fresh replay와 completed-prefix 재개: **44 NPZ 파일의 모든 배열 일치**.
- G02 첫 prefix 재개는 종료된 spectral state를 메모리에 남겨 실패했다. 실패 ID/로그 보존. 각 complete checkpoint의 state 부재를 종료된 lineage로 처리하도록 수정한 뒤 fresh/prefix 재개 **52 NPZ 파일의 모든 배열 일치**를 확인했다. mesh/classes/rest/anchors/branch/operator state 포함.
- rejected audit checkpoint를 재개해 다음 CC로 넘어가지 못하도록 회귀 테스트를 추가했다. completed-prefix 복구를 검증했으며 mid-optimizer/incomplete-stage restart는 주장하지 않는다.
- **596개 단계의 1,979개 payload 파일** 해시·parent chain·source/step identity를 검증했다. 정확한 실행 소스 10세트를 `source_snapshots/<identity>/`에 저장했다. 과거 batch는 해당 소스/정의를 복구해야 재개된다.
- Git의 CRLF 변환도 source hash를 바꿀 수 있다. Git revision과 source overlay를 함께 복구한다. checkpoint/파라미터/소스가 바뀌면 새 ID를 요구한다.
- 외부 bundle에서 별도 checkout을 복구하고 `git fsck` 및 I02 checkpoint 재개를 확인했다. 기존 worker는 checkout-local `.venv` executable/prefix를 요구한다. 원본 interpreter를 직접 사용한 거부 기록도 보존했다. 새 local venv와 기존 의존성의 읽기 전용 참조로 검증했으며, bundle이 Python 의존성까지 포함하는 독립 배포물이라고 주장하지 않는다.
- local commits를 작은 단위로 보존했다. 주요 단계: `93df5f3`, `3857909`, `2d05c3e`, `c034d26`, `b451c3c`, `ade92cf`, `8570acd`, `2a2b71c`, `42c88bc`, `2f72524`. 최종 보존 commit/bundle/독립 복구 기록은 `preservation/git_recovery.json`에 있다.
- 보호 manifest, 문헌·추출 실패, 실제 이미지/단면/state/logs를 `FINAL_ARTIFACTS.json`으로 색인한다. 기존 외부 연구 자료 전체를 복제하지 않았다.

독립 checkout에 해당 batch의 정확한 소스와 선언 환경을 복구한 뒤 재개한다:

```powershell
.venv/Scripts/python.exe -B tools/task32_research.py run --definition E:/CHESHIRE_DATA/task32/definitions/straight_children/I01_STRAIGHT_CHILD.json
```

실험 의존성 `.[task32,review]`, 선택적 reader `.[reference]`, 단면 export `.[study-plots]`를 선언했다. 실제 Matplotlib export는 기존 설치 환경을 읽기 전용 재사용했고 ALICE 환경·소스를 수정하지 않았다. 출력 경로는 독립 Task32 연구용이며 기본 제품 API로 통합하지 않았다.

## 기술적 대안 판단

더 높은 generation과 기존 point-class 계수 증폭에 집중하기보다 field 관계, multi-face scope, projection admission, 전체 contact 검증으로 연구 방향을 전환했다. 실제 이미지와 단계별 교차 결과가 이유다. 최종 표본 0을 첫 성공으로 채택하지 않고 전체 검사로 반증한 뒤 curved child를 분리했다. 기존 알고리즘을 대체하거나 원본 연구 판정을 바꾸지 않았다. 결과는 기술적 부분 성공이며 조형 목표와의 남은 차이를 명시했다.
