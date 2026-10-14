# 몸체 전체의 주름 위계 재구성 — 2026-10-14

몸체 전체의 부모 주름과 두 하위 수준 사이의 위계를 수정한다. 부모 생성장을 교체한 trial01·trial02는 실제 렌더에서 조형의 풍부함이 감소하여 채택하지 않았다. trial03은 반환값 처리 오류로 모델 저장 전에 중단했다. trial04는 기존 MIDDLE의 위상 경로와 변위를 보존하면서 두 주축 계열을 강화하고, 기존 NESTED02의 하위 규칙과 예산을 새 부모 위에서 다시 계산했다. **trial04는 실제 주축 대비를 확인한 비교 후보로 보존한다. 사용자 후속 판단에 따라 연속성 보존을 우선하며, 기존 NESTED02를 후속 비교 기준으로 유지한다.**

## 공통 입력과 변경 범위

입력은 보존된 실제 `E:\CHESHIRE_DATA\experiments\end_rule_revision_20261014\trial01\replay\states\G06_DEPTH08`이다. 제어점은 1,750,530개, 사각면은 1,750,528개이며 `control_quad.npz` SHA256은 `35f5bdbc39568a33697c2f414ad8754aa9b0e072ffe8f3bf8dfb0a76abdc58d1`이다. 기존 G0–G6 DEPTH08은 재계산하지 않는다. trial01·trial02는 MIDDLE을 교체했다. trial04는 같은 입력에서 실제 저장된 MIDDLE 변위를 재사용하되 LINKED/WIDE/FLOW를 섞지 않는다.

기존 MIDDLE은 실제 XYZ 각도에 사분면당 5주기인 `20theta`와 여러 높이 방향 변조를 적용했다. 하위 단계의 진폭 제한만으로는 이 동급 부모 주름의 반복을 바꾸지 못했다. G3에서 시작한 실제 장식 계보의 G6 면은 165,888개, 약 9.48%이며 Z 6.970–8.694에 한정된다. 상부 cap 계보만 수정하여 몸체 전체의 주름을 정리하는 방식은 범위가 맞지 않는다.

## trial01 — 재료 좌표 기반 후보, 시각적 비채택

`run.py`, `primary.py`, `secondary.py`로 생성했다. 재료 좌표 `t=chart[:,0]`, `theta=atan2(abs(chart[:,2]),abs(chart[:,1]))`와 `8theta-pi` 기반 위상으로 사분면당 2개의 넓은 부모 주름을 만들었다. 하위 접힘은 부모 위상의 제한된 옆면 구간에만 생성했으며, SECONDARY 예산은 부모 진폭의 .32 이하, TERTIARY는 SECONDARY의 .28 이하로 제한했다.

전체·근접 렌더에서 재료 좌표 기반의 넓은 부모와 좁은 하위 지원이 넓은 빈 면을 만들었다. 수치 예산을 충족했어도 근접 조형을 발전시킨 결과로 채택하지 않았다. 실제 저장은 `E:\CHESHIRE_DATA\experiments\ordered_primary_folds_20261014\trial01`에 보존한다.

trial01의 기존 검증 수치를 다음과 같이 보존한다.

- geometry SHA256: `175a902475c6cc7098f992965ab05ab9eb5c1877cb5d977f9bcbdecd84a4a870`
- control SHA256: `58a172d1be87f7022c7b341d0c69c1a96fb9d696a61332273a4f042ec9542e07`
- native 14,004,226 vertices / 28,008,448 triangles, 기존 G7 face 인덱스 동일
- PRIMARY / SECONDARY / TERTIARY 최대 변위: `0.0855150831161266` / `0.02774401169464195` / `0.007665546351894657`
- 하위 단계가 보존한 부모 정점 2,923,610개, 실제 이동 정확히 0
- 국소 옆면 폭 중앙값 `0.22826096378220678`, invalid quad 0
- 최종 좌표 모두 유한, 퇴화 삼각형 0, 최소 native 삼각형 면적 `1.8149934402155752e-10`
- 최종 X/Y 대칭 오차 `3.275157922644212e-14`
- 생성 시간 약 221.25초, 렌더·내보내기 제외

실제 입력에서 XYZ 각도와 재료 각도 차이는 중앙값 약 0.0433 rad, 99백분위 약 0.389 rad였다. trial01은 이 차이를 피하려고 재료 좌표를 사용한 후보였으나, 좌표 차이 자체가 미관 실패의 증명은 아니었다. 고정 재료 좌표 사용을 후속 후보의 필수 조건으로 삼지 않는다.

## trial02 — 실제 입력 표면 위상과 넓은 하위 지원, 시각적 비채택

실행 코드는 `run_surface.py`, `primary_surface.py`, `secondary_surface.py`이다. 실제 전체·근접 렌더에서 기존 조형의 풍부함이 감소하고 넓은 끝단이 드러나 채택하지 않았다. 다음은 실패 후보의 실제 규칙을 보존한 기록이다.

1. 보존된 실제 G6 DEPTH08에서 `t=(Z-zmin)/(zmax-zmin)`, `theta=atan2(abs(Y),abs(X))`를 한 번 정의한다. 실제 X/Y 반사 ID의 최소 ID 대표를 사용한다. 후속 단계에서는 이 위상을 다시 계산하지 않고 계승한다.
2. PRIMARY 위상은 `12theta-pi+1.8*sin(2theta)*sin(2pi*t/.18+.25)+.45*sin(4theta)*sin(2pi*t/.37)`이다. 사분면당 3주기이며, 고정 normalized Z에서 각방향 미분의 이론적 하한은 6.6이다. 이는 좌표상의 각방향 순서를 뜻하며 곡면 능선 검출을 뜻하지 않는다.
3. PRIMARY 프로파일은 `((.5+.5*cos(phase))^2-.375)/.625`이다. 범위는 [-.6,1]이며 균일한 위상 표본에서 평균 0이다. 실제 변조 표면의 평균 변위나 부피 보존은 주장하지 않는다.
4. PRIMARY 진폭 예산은 `.009H*PCHIP(actual_normalized_Z)*(1-.7*actual_feature_support)*(.825+.175*cos(2theta))`이며 실제 반사 궤도의 최솟값을 사용한다. 입력 높이는 `H=9.735842284057451`이다. feature support가 1인 구간의 기본 상한 `.0027H`는 이전 MIDDLE의 `.006H*(1-.55)`와 같다.
5. 실제 DEPTH08의 법선을 새로 구하여 변위를 계산한다. 새 변위만 한 차례 평균한 뒤 정점별 진폭 상한과 실제 ID 대칭을 적용한다. 이 PRIMARY 연산은 입력 좌표 자체를 평활화하지 않는다.
6. 실제 G6/G7 면·모서리·자식 ID를 확인하고, 저장된 SURFACE 재현을 검증한 중립 CC stencil로 새 PRIMARY 좌표를 G7로 올린다. 새 위상은 실제 V/E/F ID의 직접 scalar lift로, 진폭 예산은 동일한 중립 CC convex stencil로 운반한다. 이전 `20theta` 위상을 사용하지 않는다.
7. SECONDARY 지원은 `W=sin(parent_phase)^2`이다. 위상 중심선의 부동소수점 오차인 `abs(sin)<1e-14`만 정확한 0으로 만든다. 이전 후보의 넓은 보호 구간 대신 프로파일 중심선만 보존하며 옆면 전반에 하위 접힘을 허용한다. SECONDARY 위상은 `3*parent_phase`, 예산은 `min(.28*parent_envelope,.10*local_flank_width)`이다.
8. TERTIARY 지원은 `W*quintic(clip((cos(child_phase)-.15)/.65,0,1))`이며 위상은 `3*child_phase`이다. 예산은 `min(.28*child_budget,.075*local_flank_width/3)`이다. 두 하위 단계 모두 실제 입력 법선을 새로 구하고, 새 변위만 평균한 뒤 지원 마스크와 진폭 상한, 대칭을 재적용한다. 따라서 예산 상한이 실제 변위와 같다는 주장은 하지 않는다.

이는 하나의 고정된 위상 계열로 PRIMARY와 두 하위 수준을 연결하는 조형 규칙이다. G7은 실제 subdivision 횟수이며 세 장식 수준을 G8/G9로 부르지 않는다. 새 topology event, 독립 장식 메시, 전역 fractal/noise 마감은 추가하지 않는다.

## trial02 실제 계산 검증

실제 `trial02/RECEIPT.json` 및 `PRIMARY_G06/RECEIPT.json`에서 확인한 값이다.

- PRIMARY G6 control SHA256: `08743d0fc33cdbc3bce22ba8d9258a8d39c5c0004574691101b4bdbe0574dca1`
- 최종 geometry SHA256: `f5ad382e4e8bcd9672047852e6150c3160b1029372a50ca4737ec31eae1efbfa`
- 최종 control SHA256: `d1e421ca43a3bb40bb8e464459185c8c285393c16c007e9e46d60d32a5115b6b`
- native 14,004,226 vertices / 28,008,448 triangles, 기존 G7 face 인덱스 동일
- 저장 SURFACE의 중립 CC 재현 최대 좌표 오차: `3.552713678800501e-15`
- 실제 PRIMARY 최대 변위: `0.08599620141136051`
- 실제 SECONDARY / TERTIARY 최대 변위: `0.016494722333533045` / `0.004142317403900305`
- 정점별 진폭 상한 초과: `3.469446951953614e-18` (부동소수점 오차 범위)
- SECONDARY / TERTIARY 정점별 예산 초과: `4.336808689942018e-19` / `1.0842021724855044e-19`
- 부모 대비 SECONDARY 예산 및 SECONDARY 대비 TERTIARY 예산 상한 위반: 모두 0
- PRIMARY 변위의 X/Y 대칭 오차 0, 입력·출력 위치 대칭 오차 동일 `4.418687638008123e-14`
- 최종 G7 X/Y 위치 대칭 오차: `3.2862601528904634e-14`
- 실제 고정 normalized Z 각방향 미분 최솟값: `6.695308511577218`
- 길이 0인 입력 법선 0개
- 하위 단계가 보존한 부모 중심선 정점 13,300개, 실제 이동 정확히 0
- SECONDARY / TERTIARY 지원 제어점: 6,988,814개 / 2,953,764개. 이는 표면적 비율이 아니다.
- 국소 옆면 폭 중앙값 `0.16825700552775313`, invalid quad 0
- 최종 좌표 모두 유한, 퇴화 삼각형 0, 최소 native 삼각형 면적 `1.7961078582134482e-10`
- 생성 시간 약 220.28초, 렌더·내보내기 제외

수치 기록은 완료되었다. 실제 렌더 판정은 비채택이다. 수치 통과를 시각적 개선으로 해석하지 않는다.

## trial03 — 실행 오류, 모델 생성 전 중단

`run_retained.py`, `primary_retained.py`가 기존 MIDDLE을 강화하는 후보를 실행했으나, `_transport()`의 튜플 반환값에서 변위 배열 `[0]`을 선택하지 않아 좌표 덧셈에서 중단했다. 새 모델을 저장하기 전 발생한 구현 오류다. 해당 `trial03/source_snapshot_run/`은 실패 당시의 코드로 보존한다. 오류 수정은 별도 `run_retained_v2.py`, `primary_retained_v2.py`와 새 출력 `trial04`에서 진행한다. trial03에는 최종 메시나 성공 수치를 부여하지 않는다.

## trial04 — 기존 위상 경로 보존과 두 주축 계열 강화

실행 코드는 `run_retained_v2.py`, `primary_retained_v2.py`이며, 하위 연산은 보존된 `parent_nested_folds_20261014/parent_nested_readable.py`를 그대로 사용한다.

1. 같은 DEPTH08 입력에 실제 저장 MIDDLE의 변위를 더했을 때 저장된 MIDDLE 좌표와 정확히 일치하는지 확인한다. 저장된 위상·feature support·대칭 ID와 면·재료 좌표도 확인한다. 새로운 독립 주름장을 정의하지 않는다.
2. 실제 저장 위상에서 `k=phase/(2*pi)`, `p=1-(1-exp(-((k-1)/.70)^4))*(1-exp(-((k-4)/.70)^4))`로 두 주축 계열을 정의한다. 원래 `20theta` 기반 위상의 경로와 사분면당 5주기는 유지한다.
3. G6에서 `gain=1+1.6*p*(1-.75*feature_support)`를 실제 저장 MIDDLE 변위에 곱한다. 몸체 주축의 최대 설정은 2.6이며, support=1인 장식 계보에서는 최대 1.4다. 기존 NESTED02의 최대 설정 1.3 대비 주축 최대 설정비는 2배다. 기존 후보는 G7로 운반한 변위에 gain을 적용했으므로, 모든 실제 정점 변위가 정확히 2배가 된다는 뜻은 아니다.
4. PRIMARY는 저장된 실제 MIDDLE 변위를 재사용하며 별도의 새 법선 계산이나 변위 평균을 추가하지 않는다. 실제 ID로 대칭을 운반한 뒤 검증된 중립 CC로 새 G6 좌표를 G7로 올린다. 실제 위상도 이전과 같은 V/E/F scalar lift로 운반한다.
5. 기존 NESTED02의 저장된 `PARENT_STATE.npz`를 재현해 이전 하위 진폭 예산과 일치하는지 확인한다. 하위 연산에 공급하는 예산은 `min(old_NESTED02_budget, neutral_CC(new_G6_parent_envelope))`이다. 주축 강화만으로 하위 예산을 함께 늘리지 않는다.
6. 보존된 NESTED02 하위 규칙의 지원은 `s=(abs(wrapped_parent_phase)-.55)/1.8`, `W=64*s^3*(1-s)^3`이며 `0<s<1` 밖에서는 0이다. CHILD 예산은 `min(.40*supplied_parent_budget,.12*local_flank_width)`이다. trial02의 `sin²` 지원 및 .28 CHILD 규칙과 다르다.
7. SMALL 예산은 `min(.28*child_budget,.075*local_flank_width/3)`이다. CHILD와 SMALL은 강화된 실제 입력에서 법선을 각각 새로 계산한다. 새 변위만 한 차례 평균한 뒤 지원·예산·대칭 제한을 재적용한다. 물리적 폭 제한은 새 부모의 실제 위상 기울기로 계산한다.

이는 기존 조형 언어를 유지하며 두 부모 계열과 하위 접힘의 상대적 강약을 바꾸는 후보다. 새 의미상 능선 검출이나 topology recursion으로 해석하지 않는다.

## trial04 실제 계산 검증

실제 `trial04/RECEIPT.json`에서 확인한 값이다. 수치 검증과 아래의 실제 렌더 평가는 구분한다.

- 생성 영수증 SHA256: `f0e014664cac6f5a85e8e7fdff70089abbf27a480fc63f88f1bfcf2bd55b58a2`
- 최종 geometry SHA256: `bc155aa4780d5d9e2b228c193f01d0a29964b60b7cd4abdbc2e7b1975ba9be53`
- 최종 control SHA256: `21f2cb3610774f2f9f83ef4ffbbaa40c13f30958893b40b25d7ba28c682f0025`
- native 14,004,226 vertices / 28,008,448 triangles, 기존 G7 face 인덱스 동일
- 저장 MIDDLE의 입력+실제 변위 재현은 정확히 일치, 원래 위상 배열을 보존
- 실제 G6 gain 범위 `1.0000000005580814`–`2.6`
- PRIMARY 최대 변위 `0.1518791388129518`; 원래 MIDDLE 대비 추가 변위 최댓값 `0.09346408542335496`
- 실제 CHILD / SMALL 최대 변위: `0.030202872304068953` / `0.008418509973928187`
- 기존 NESTED02 하위 예산의 재현 오차 0; 새 CC 부모 예산과의 min으로 제어점 20개에서 예산 감소, 최대 감소 `0.001996657540412127`
- CHILD / SMALL 정점별 예산 초과: `3.469446951953614e-18` / `8.673617379884035e-19` (부동소수점 오차 범위)
- 하위 단계가 보존한 부모 정점 3,058,669개, 실제 이동 정확히 0
- CHILD / SMALL 지원 제어점: 3,943,445개 / 1,780,404개. 이는 표면적 비율이 아니다.
- 국소 옆면 폭 중앙값 `0.11373861975024771`, invalid quad 0
- 저장 SURFACE의 중립 CC 재현 최대 좌표 오차 `3.552713678800501e-15`
- 최종 좌표 모두 유한, 퇴화 삼각형 0, 최소 native 삼각형 면적 `7.419761553445555e-11`
- 최종 X/Y 위치 대칭 오차 `3.2862601528904634e-14`
- 생성 시간 약 273.21초, 렌더·내보내기 제외

## 실제 렌더 평가

비교 기준은 최신 보존 모델 `parent_nested_folds_20261014/trial02/NESTED`이다. 동일 카메라·조명·재질·all-flat 조건의 정면, 몸체 사선, 근접 사선을 root와 독립 검토자가 확인했다. trial04는 기존 세로 리본과 사선 결, 전체 장식 밀도를 유지하면서 주축 리본과 깊은 골의 전후 대비를 강화했다. trial01·trial02에 생겼던 큰 빈 판은 나타나지 않았다.

작은 말림의 어색한 겹침과 얇고 날카로운 끝은 남아 있고 일부에서는 더 강조된다. 처음에는 주축 강조 체크포인트로 선정했으나, 사용자가 후속 세대의 연속성과 기존 주름 보존을 우선한다고 명확히 하여 비교 후보로 남긴다. 근접 조형의 완성도나 모든 장식의 위계가 해결되었다고 평가하지 않는다. 기존 NESTED02는 후속 비교 기준으로 그대로 보존한다. 생성·렌더·수출의 실제 영수증과 판정은 `CHECKPOINT.json` 및 같은 디렉터리의 원본 영수증 사본에 남긴다.

## 근접 병목 진단

실제 G 번호는 메시 subdivision 횟수이다. 각 세대가 앞선 장식의 뿌리와 끝을 해석하여 새로운 장식을 생성했다는 뜻은 아니다. 후반 MIDDLE 및 NESTED는 위상과 진폭, 실제 입력 법선을 이용한 연결된 표면 변형이지만 실제 조형의 능선·뿌리·끝·접합부를 의미적으로 검출하지 않는다. 수치적인 진폭 종속을 조형적인 세대 계승과 동일하게 설명하지 않는다.

원거리에서는 큰 실루엣과 골의 리듬이 주도한다. 근접에서는 이전 단계에서 남은 끝단과 겹침, 후속 변형의 마무리가 드러난다. 기존의 어색한 끝단 위에 변형이 누적되면 그 문제가 확대될 수 있다. 일부 사선 결에는 실제 삼각면의 음영도 섞여 있다. 주축 강화는 큰 흐름의 조정이며 이 근접 병목을 해결한 실험이 아니다. 후속 기술 판단은 장식을 추가하는 양보다 뿌리·방향·끝·이웃 접힘 사이의 연결 규칙을 기준으로 해야 한다. 이 기록은 추가 실험 실행을 의미하지 않는다.

## 실제 저장과 재현

각 trial의 저장 위치는 `E:\CHESHIRE_DATA\experiments\ordered_primary_folds_20261014\trial01`부터 `trial04`까지이다. trial03은 실행 코드 snapshot만 보존된 중단 기록이며 아래 최종 산출물 목록은 생성 완료된 trial에 해당한다.

- `PRIMARY_G06/control_quad.npz`, `STATE.npz`, `RECEIPT.json`: 새 G6 좌표·실제 위상·진폭·변위·생성 기록
- `PRIMARY_G07_STATE.npz`: 실제 G7로 운반한 위상·부모 진폭
- `SUBORDINATE_STATE.npz`: 실제 SECONDARY/TERTIARY 변위·지원·예산
- `ORDERED/{control_quad,geometry}.npz`: 최종 실제 G7
- `RECEIPT.json`: 실제 입력·출력·실행 코드·snapshot 해시 및 수치 검증
- `ORDERED_FLAT/review/`: 동일 카메라·재질·조명·all-flat 조건의 실제 렌더 및 영수증

기존 trial은 덮어쓰지 않는다. 다음은 trial04의 규칙을 빈 `trial05`에 재현하는 명령이며 추가 실험 지시가 아니다. 렌더·내보내기는 실제 생성 완료 후 사용한다.

```powershell
$env:TEMP='E:\CHESHIRE_DATA\tmp'
$env:TMP='E:\CHESHIRE_DATA\tmp'
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python experiments/ordered_primary_folds_20261014/run_retained_v2.py --root E:/CHESHIRE_DATA/experiments/ordered_primary_folds_20261014/trial05
blender --background --python experiments/ordered_primary_folds_20261014/render.py -- --root E:/CHESHIRE_DATA/experiments/ordered_primary_folds_20261014/trial05
python experiments/ordered_primary_folds_20261014/export_model.py --root E:/CHESHIRE_DATA/experiments/ordered_primary_folds_20261014/trial05 --output E:/CHESHIRE_DATA/exports/20261014/COLUMN_ORDERED_PRIMARY_REPRODUCTION_TRIAL05
```

## 검증 범위와 한계

trial01·trial02는 새 부모 위상을 정의한 후보이며, trial04는 실제 저장된 MIDDLE 위상과 변위를 계승하는 후보다. 어느 후보도 의미상 능선·끝을 자동 검출한 결과나 topology recursion이 아니다. 이전 단계의 말림과 겹침은 입력 DEPTH08에 남아 있다. 국소 폭은 실제 면 위의 일차 위상 간격 추정이며 원격 면과의 충돌 여유가 아니다. trial02의 `sin²` 지원은 프로파일 중심선만, trial04의 compact 지원은 지정된 위상 구간을 보존한다. 이를 실제 의미상 능선의 자동 보호로 해석하지 않는다.

수치 예산 충족과 시각적 위계 개선을 구분한다. 전역 자기 교차·제작 적합성·다른 입력과 게이트로의 이전은 검증하지 않았다. 최종 렌더 판단과 내보내기는 별도 체크포인트에 기록한다.
