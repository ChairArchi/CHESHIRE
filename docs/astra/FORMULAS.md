# Formula map and implementation meaning

기호를 간략화한 탐색용 문서다. 정확한 cyclic order·mask·normal·resolved parameter는
링크된 계약과 실제 producer source를 따른다. 서로 다른 operator를 하나의 공식으로 합치지 않는다.

| Tasks | 핵심 수식 / 의미 | 원본 계약과 차이 |
| --- | --- | --- |
| 02 | normal variation = mean(pairwise incident unit-normal angle)/π | `attributes.py`; boundary unavailable. differential curvature 아님. |
| 03 | normalize/clipping; smoothstep(t)=t²(3−2t) | scalar mapping이다. geometry·shading의 smoothing과 다르다. |
| 05 | P'=P+n·field·strength·bbox_diagonal | input normal/bbox를 한 번 읽는 이동; local fold hierarchy 없음. |
| 06/07 | continuous field child=Σ positive parent weight·value, Σweight=1 | semantic association이지 signed geometry stencil의 복원이 아니다. bilinear corner patch는 README Task07.1. |
| 09–13,19–21 | DLL taper/inset/frame/roof, explicit rules and descendant roles | 외부 backend 실제 연산/정규화와 자체 role selection을 분리. 각 원래 module/DLL API 참조. |
| 14/29 | F'=mean(P)+nf·wf; E'=((C1+C2)(1+w1)+(P1+P2)(1−w1))/4+ne·we; V'=(F(1+w2)+E(2−w2)+P(n−3))/n+nv·wp | [Legacy contract](../WEIGHTED_SUBDIVISION_REFERENCE.md). Task29는 갱신된 같은 세대 face를 edge에 전달한다. legacy와 normal/evaluation-order 규약이 동일하다고 주장하지 않는다. |
| 16/29 | F''=((V'(1+w3)+F'(1−w3))(1+w4)+(E1'+E2')(1−w4))/4+nf·wf | 실제 직전 V/F opposite와 E pair 자격 필요. legacy16은 face만 뒤에서 교체, reference29는 face completion 뒤 edge/corner 계산. |
| 17/30 | quad corner=[P1(2.25+2w1)+(P2+P4)(.75−w1)+.25P3]/4+nf·w10; tri=(2/3)P1(1+w1/2)+(1/6)(P2+P3)(1−w1)+nf·w10 | [DS contract](../TASK17_REFERENCE.md). F/E/V는 DS face origins. Task17 n>4 standard fallback; Task31 opt-in polygon path와 다르다. |
| 18 | φ=max(0,1−graph_distance/3); diffusion .5, scales1/4/12 peak normalized | ordered controls의 total mass는 같지 않았다. ordered hierarchy의 우월성 미입증. |
| 22/23 | P=Pcrease+α(Pweighted_sharp−Pstandard_smooth) | [Crease contract](../CROSS_CELL_CREASE_REFERENCE.md). literal SUM attraction·finite crease를 구분. 강한 edge 보존≠깊은 fold 발생. |
| 27 | actual section descriptors + unsigned centroid-fan area | folded COMPAS polygon area의 cycle/reflection 의존을 R4에서 교정. area proxy를 physical curvature로 부르지 않는다. |
| 31 | signed neighbor-displacement contrast tertile→BULB/RIB/DEPTH; blend memory .8; DS mean over all actual parents | explicit annulus handle/edit는 field에서 emergent opening이 생긴 것과 다르다. |
| 32 | target edge error + graph bending surrogate + anchors; cotan Lφ=λMφ; diffusion (M+ℓ²L)u=Mf | [Task32](../TASK32_RESULTS.md)와 source의 gradient 검증. physical shell/RD/wavelet solver 재현 아님. |
| 33 | physical-scale macro field + parent-phase meso + gradient-zero fine notch; bounded fine amplitude | `task33_folds.py`, [결과](../TASK33_RESULTS.md). preset material chart와 phases. carrier preparation와 native bilinear resampling 분리. |
| 34 | current crest prominence/width→central cleft + two shoulders→re-read shoulder | `task34_refolding.py`. current/frozen 같은 입력 대조로 검증. 단순 generation schedule과 구분. |
| 35 | R=√(half_width·half_depth); broadness/scale slope/aspect→4/8-direction mix; current parent width/promotion + axial profile→incision | `task35_columns.py`. growth support와 incision support 분리. 입력 profile은 사전 조건이다. |
| 36 | support=min distance(face centre, supporting edge line); bend=1−dot(adjacent unit normals); gain factor=1+feedback·tanh(2·face_bend) | actual incoming geometry 매 세대 재판독. exact nonplanar inradius/principal curvature가 아니다. |
| 36 decomposition | P'=Pinterp+a(PCC−Pinterp)+s(Pweighted_noNormal−PCC)+d(Pfull−Pweighted_noNormal) | `task36_growth.py`; retained memory와 cap mask 적용 전/후 실제 배열 저장. a=0은 모든 산술평균 제거가 아니다. |
| 36 safety | Papplied=Ppre+local_factor·(Prequested−Ppre) | symmetry-closed intersecting local support만 .5씩 감소. zero factors/실제 거리 기록. bbox/global shape normalization 없음. |
| 36 surface | quad당 4 triangle fan; VF centre=midpoint(inherited V,F diagonal) | inactive refinement는 기존 physical fan을 그대로 sampling. 보조 centre는 독립 fold 자유도가 아니다. |

수렴–발산은 여기서 형상 관계를 설명한다. 물리적 flux나 특정 수학 정리로 인증하지 않는다.
큰·중간·작은 접힘의 깊이, sharpness, 공간 연결, 실제 계보와 finite section evidence는 별도다.
