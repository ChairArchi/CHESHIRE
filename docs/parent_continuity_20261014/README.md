# 성숙한 부모 형상의 연속성 보호

작업 시작일은 2026-10-14이며, 후보 생성 완료와 후속 검증은 한국 시간 자정 이후인 2026-10-15까지 이어졌다. 실험 폴더명과 기존 receipt의 `date`는 시작일을 유지한다. 이 문서는 실제 저장 자료를 설명하며 원본 연구 데이터와 이전 체크포인트를 변경하지 않는다.

## 범위와 현재 판단

원거리의 바로크적 풍부함을 유지하면서, 후속 CHILD·SMALL 변형이 부모 주름의 급격한 방향 전환 구간을 다시 변형하는 문제를 분리한다. 기존 NESTED02의 부모 carrier, 주축 가중치, 위상과 진폭 예산을 정확히 복원한 뒤, 실제 부모 기하에서 측정한 보호 가중치만 새 변위에 추가했다.

보존된 G6 MIDDLE과 실제 neutral-CC 자식 G7 SURFACE의 동일 카메라 비교에서는 컵형 끝과 겹침이 이미 G6에 존재한다. 해당 부근의 G7 변화는 주로 조밀화와 완화로 관찰된다. 따라서 현재 보이는 끝단과 겹침 전체를 G7 또는 CHILD·SMALL의 신규 손상으로 확정하지 않는다. 이번 후보는 기존 끝을 재조형하는 실험이 아니라, 선택된 부모 기하에 추가되는 후속 변위를 억제하는 실험이다.

후보의 기술 검증과 실제 `close_oblique`·`body_oblique`·`front` 렌더 검토를 완료했다. **PARENT_GUARDED trial01은 조형 결과로 채택하지 않는다.** 큰 주름의 선택 영역을 보호하는 기능은 작동했으나, 사선 결이 섬처럼 끊겨 고르지 못하고 기존 컵형 끝은 남았다. 사용자가 변화가 무엇인지 물은 데 대해, 시각적 개선이 기대에 미치지 못했다고 확인했다. 수치 감소를 조형 성공으로 표현하지 않으며 기존 NESTED02를 이 후보로 대체하지 않는다.

## 자료 위치와 표시용 형상의 구분

| 자료 | 경로 | 의미 |
| --- | --- | --- |
| 이전 실제 완성 모델 | `E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial02/NESTED/geometry.npz` | 비교 기준 NESTED02 |
| 단계 분리 진단 | `E:/CHESHIRE_DATA/experiments/parent_continuity_20261014/audit01/` | 보존된 G6·G7 control의 표시와 읽기 전용 측정 |
| 이번 실제 후보 | `E:/CHESHIRE_DATA/experiments/parent_continuity_20261014/trial01/PARENT_GUARDED/` | 실제 저장한 새 G7 control 및 native 형상 |
| 후보 생성 근거 | `E:/CHESHIRE_DATA/experiments/parent_continuity_20261014/trial01/RECEIPT.json` | 원본·코드·상태 해시와 검증 수치 |

G6 MIDDLE과 G7 SURFACE의 원본 checkpoint는 `CONTROL_AND_EVIDENCE_ONLY`이며 당시 native 메시를 저장하지 않았다. `audit01/*/display_geometry.npz`는 보존된 quad의 네 꼭짓점과 산술평균 중심을 네 삼각형으로 연결한 **표시용 fan**이다. 저장된 꼭짓점은 정확히 유지되며 모델링 연산, 새 subdivision 또는 설계 후보 생성은 없다. 이를 당시 저장되어 있던 native 메시로 표현하지 않는다.

반면 `trial01/PARENT_GUARDED/geometry.npz`는 실제 후보 control에서 만든 native 메시이다. 감사 표시용 fan을 후보 입력으로 사용하지 않는다. 후보도 G7이며 새 CC 단계와 위상 사건은 각각 0회이다. 실제 부모와 CHILD 다음 표면에서 법선을 새로 평가하는 변형은 두 번이다.

감사 렌더는 기존 NESTED02의 `close_oblique`, `body_oblique` 카메라를 사용했다. 후보 렌더는 같은 기준의 `close_oblique`, `body_oblique`, `front`를 사용한다. 재질·조명·900×900 해상도·24 samples·Blender 4.5.4·all-flat 조건을 receipt로 대조한다. 형상 modifier와 normal map은 사용하지 않는다.

## 읽기 전용 단계 측정

근거는 `audit01/MEASUREMENTS.json`이다. 원본 G7 SURFACE에 저장된 주축 변위를 더하여 실제 NESTED02 carrier를 재현하고, 저장된 CHILD·SMALL 변위를 순서대로 더하여 실제 최종 control을 재현한 뒤 측정했다. 측정 과정에서 native 후보를 만들거나 원본 좌표를 수정하지 않았다.

| 단계 | quad 방향 변화 30° 초과 | 60° 초과 | 변위 차이/입력 edge 길이 1 초과 |
| --- | ---: | ---: | ---: |
| G7 SURFACE → 주축 가중 carrier | 81,820 / 1.1685% | 38,576 / 0.5509% | 37,136 / 0.1326% |
| carrier → CHILD | 694,436 / 9.9175% | 69,040 / 0.9860% | 188,064 / 0.6715% |
| CHILD → 최종 SMALL | 29,376 / 0.4195% | 15,380 / 0.2196% | 35,640 / 0.1272% |
| carrier → 최종 CHILD+SMALL | 802,432 / 11.4599% | 94,268 / 1.3463% | 303,016 / 1.0819% |

방향 변화는 실제 quad 7,002,112개 전체의 단위 법선 사이 각도이다. edge 지표는 `norm(delta_b-delta_a)/norm(input_b-input_a)`이며 네 방향 quad-edge incidence 28,008,448개를 세므로 공유 edge가 두 번 포함된다. 위 표의 분모는 각각 quad 수와 edge incidence 수이다. 방향 변화와 상대 변위가 크다는 사실만으로 손상이나 비연속을 확정하지 않는다. 특히 매우 짧은 입력 edge에서는 상대 비율이 커질 수 있다.

별도로 실제 G6 부모 face와 네 G7 자식 face를 대조했을 때 방향 변화 30° 초과는 90,824개(1.2971%), 60° 초과는 43,084개(0.6153%)였다. 이 비교는 의도된 neutral-CC 완화까지 포함하므로 신규 디테일 변형의 손상률과 같지 않다. 분포 분위수는 chunk마다 매 31번째 incidence 표본이며, 초과 개수와 최댓값은 전체 incidence 측정이다.

기존 위상 마스크가 실제 부모의 큰 방향 전환을 모두 보호하지 않는 점도 확인했다. 실제 G7 carrier에서 incident 단위 quad 법선의 평균 길이로 계산한 unsigned normal-cone 분산이 30° 이상인 control 119,868개 중 51,809개가 기존 CHILD 또는 SMALL에서 `1e-12`보다 크게 움직였다. 이 분산은 부호 있는 주곡률이나 능선·골·끝의 의미 분류가 아니다.

## 이번 보호 규칙

1. 실제 NESTED02의 G7 carrier 좌표를 복원한다. 위상·주축 가중치 `.95+.35*p`와 부모 진폭 예산은 기존 저장 상태와 정확히 대조한다.
2. 성숙한 G7 carrier의 **G5 계보 old-corner ID 위치**에서 quad를 샘플링한다. 과거 저장된 G5 형상으로 돌아가거나 G5 좌표로 대체하지 않는다.
3. `cone = acos(norm(mean(incident unit quad normals)))`를 도 단위로 계산한다. 5°에서 감쇠를 시작하고 25°에서 완전 보호한다. 기본 가중치는 `1-quintic(clip((cone-5)/20, 0, 1))`이다.
4. 한 G5 샘플 face의 꼭짓점 중 하나라도 25° 이상이면 그 face 전체를 hard core로 선택한다. 보호값에 실제 G5 edge graph의 `.5*self+.5*neighbor_mean`을 한 번 적용하고 core를 정확히 복원하여 한 셀 주변의 전이 폭을 둔다.
5. 검증된 G5→G6→G7 V/E/F ID 관계로 가중치를 운반한다. 선택한 G5 face의 모든 G7 후손 face 꼭짓점을 정확히 보호하고 실제 X/Y reflection orbit의 최솟값을 취한다. 네 꼭짓점이 모두 고정되므로 해당 native fan 중심도 부모와 같게 유지된다.
6. 보호 가중치를 기존 CHILD·SMALL의 compact 위상 마스크에 곱한다. 새 변위만 한 번 이웃 평균화하고 다시 마스크·점별 진폭 상한·실제 ID 반사를 적용한다. 부모 XYZ 자체는 평활화하지 않는다. SMALL에서도 같은 고정 보호가 유지된다.

CHILD 예산은 `min(.40*parent_envelope, .12*physical_flank_width)`, SMALL 예산은 `min(.28*child_budget, .075*physical_flank_width/3)`이다. 물리 폭은 실제 incoming quad의 unwrapped 부모 위상 기울기로 계산한 1차 근사이며 geodesic 거리나 원격 표면 사이의 여유를 인증하지 않는다.

## 실제 후보 수치

근거는 `trial01/RECEIPT.json`과 그 안의 `geometry_guard`, `nested`, `variants.PARENT_GUARDED.validation`이다.

| 항목 | 실측 |
| --- | ---: |
| G5 계보 샘플 control / quad | 437,634 / 437,632 |
| hard G5 face | 98,400 / 22.4846% |
| 보호 요청 G7 후손 quad | 1,574,400 |
| 네 꼭짓점의 guard가 모두 0인 G7 quad | 1,637,568 / 23.3868% |
| geometry guard가 0인 G7 control | 1,765,502 |
| 위상·기하 마스크를 합쳐 보호한 control | 3,892,454 |
| geometry guard 영역 최대 실제 움직임 | 0 |
| CHILD 최대 변위 | 0.0287913133 |
| SMALL 최대 변위 | 0.0066990082 |
| 부모/자식 예산 및 작은 마스크 포함관계 위반 | 0 |
| 실제 X/Y 위치 반사 최대 오차 | 3.3085×10⁻¹⁴ |
| native vertex / triangle | 14,004,226 / 28,008,448 |
| 양의 면적 triangle / 퇴화 triangle | 28,008,448 / 0 |
| 최소 triangle 면적 | 8.468270444954222×10⁻¹¹ |

CHILD의 mask별 변위 상한 검사에는 부동소수점 잔차 `1.734723475976807e-18`이 있다. 검증 허용값 `1e-12` 이내이며, 부모 예산 위반과 정확 보호 영역 움직임은 0이다. 개수 비율은 control 또는 quad 개수 기준으로 표면적 점유율이 아니다.

후보 native geometry SHA-256은 `6e9b9fa2498ae441f4adb015ccedfc6123d2fd8a1af3d96ec2f2865c9e78d443`이다. 삼각형 연결은 기존 native와 같은 `67109d7c7378b6cdfe82a713c74a860c98cdd53adcdce311f8612b3e6565a9ee`이며 실제 subdivision 번호를 증가시키지 않는다.

큰 normal cone에는 원하는 장식과 기존 결함이 모두 포함될 수 있다. 이번 규칙은 선택한 성숙 부모 기하를 후속 변위에서 보존하지만, 이미 존재한 겹침과 컵형 끝을 고치거나 전체 능선·골·끝을 자동 분류하지 않는다. 자기교차·충돌·제작 적합성과 수학적 G1 연속성은 검증 범위에 포함하지 않는다.

## 기존 후보와의 실제 변화 비교 및 종료 상태

2026-10-15의 `trial01/CHANGE_COMPARISON.json`은 동일한 부모 carrier에 대한 기존 NESTED02와 PARENT_GUARDED의 최종 변화를 읽기 전용으로 대조한 기록이다. 후보 변위의 최종 control 재현과 native old-corner prefix 일치를 확인했다. 비교를 위해 모델·렌더를 다시 생성하거나 기존 좌표를 수정하지 않았다.

| 동일 부모 대비 최종 변화 | NESTED02 | PARENT_GUARDED |
| --- | ---: | ---: |
| quad 방향 변화 30° 초과 | 802,432 / 11.4599% | 498,956 / 7.1258% |
| quad 방향 변화 60° 초과 | 94,268 / 1.3463% | 28,012 / 0.4001% |
| edge 상대 변위 차이 1 초과 | 303,016 / 1.0819% | 103,184 / 0.3684% |
| edge 상대 변위 차이 최댓값 | 251.59725694007827 | 16.633156105405597 |

geometry guard가 0인 control 1,765,502개의 부모 대비 최대 좌표 오차는 0이었다. 보호 요청 G7 후손 face 1,574,400개의 모든 꼭짓점과 **실제 저장 native fan 중심**의 최대 좌표 오차도 각각 0이었다. 방향·edge 변화는 위의 감사와 동일한 전체 incidence 및 표본 규칙을 사용했다. 이 감소는 선택된 부모 영역의 추가 변형을 억제했다는 기술적 근거이며, 근접 조형의 연속성이나 아름다움을 확보했다는 근거가 아니다.

이번 사이클은 미채택 후보와 진단 기록을 보존하고 종료한다. 새 대화에서는 **원래 끝단이 발생한 단계와 실제 surface 접속부터 검토**한다. 다음 실험 방식과 새 조형안은 이 기록에서 확정하지 않는다.

## 재현 명령

저장된 `audit01`과 `trial01`을 덮어쓰지 않는다. 아래는 **아직 없는 빈 `trial02` 경로**를 대상으로 한 재현 명령이며 이번 기록의 추가 실험 실행을 의미하지 않는다. 작업 위치는 `C:/Users/USER/CHESHIRE/worktrees/connected-fold-growth-20261012`이다.

```powershell
$env:TEMP = 'E:\CHESHIRE_DATA\tmp'
$env:TMP = 'E:\CHESHIRE_DATA\tmp'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$taskPython = 'C:\Users\USER\CHESHIRE\.venv\Scripts\python.exe'
$taskBlender = 'C:\Users\USER\CHESHIRE\scratch\generative_gate_20261010\external\blender-4.5.4-windows-x64\blender.exe'
$trialRoot = 'E:\CHESHIRE_DATA\experiments\parent_continuity_20261014\trial02'
& $taskPython -B experiments/parent_continuity_20261014/run_guarded.py --root $trialRoot
& $taskBlender --background --factory-startup --python experiments/parent_continuity_20261014/render_candidate.py -- --root $trialRoot
```

소스 코드와 실제 실행 snapshot·원본 해시는 receipt에서 서로 대조된다. 새 무거운 배열, native 모델, 렌더와 실행 임시 파일은 E 드라이브에 두며 이전 실제 checkpoint는 읽기 전용으로 유지한다.
