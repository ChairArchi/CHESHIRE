"""Build a review of the measured Tissue composition experiment."""
from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parent
base='runs/tissue_composition23'
r=json.loads((ROOT/base/'comparison.json').read_text())
if r['status']!='COMPLETE':raise RuntimeError('Comparison has not completed')
variants=[('01_overlay','1. TARGET 전체 + Tissue'),('02_replace_selected','2. UNUSED: 선택 면 치환'),('03_tissue_only','3. LAST: Tissue만')]
panels=[]
for view,label in [('front','정면'),('oblique','사시'),('micro','동일 부위 확대')]:
 cards=[]
 for name,title in variants:
  rel=f'{base}/{name}/cycles/{view}.png'
  if not (ROOT/rel).is_file():raise FileNotFoundError(rel)
  cards.append(f'<figure><figcaption>{title}</figcaption><a href="{rel}"><img src="{rel}" alt="{title} {label}"></a></figure>')
 panels.append(f'<h2>{label}</h2><div class="grid">'+''.join(cards)+'</div>')
rows=[]
for name,title in variants:
 c=r['variants'][name]['checks']
 rows.append(f'<tr><td>{title}</td><td>{c["selected_original_faces_remaining"]:,}</td><td>{c["unused_original_faces_remaining"]:,}</td><td>{c["boundary_edges"]:,}</td><td>{c["symmetry_max_error"]:.2g}</td><td><a href="{base}/{name}/result.obj">OBJ</a> / <a href="{base}/{name}/result.ply">PLY</a></td></tr>')
page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CHESHIRE / Tissue 결합 방식 비교</title><style>
body{background:#121416;color:#eee7db;font:16px/1.7 system-ui;margin:0}main{max-width:1600px;margin:auto;padding:30px}h1{font-size:30px}h2{font-size:22px;margin-top:40px}a{color:#abd6e9}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}figure{margin:0}img{width:100%;display:block}figcaption{padding:10px 0}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #555;text-align:left;padding:10px}.note{padding:16px;background:#24292d}@media(max-width:750px){.grid{grid-template-columns:1fr}main{padding:16px}}</style><main>
<h1>같은 TARGET·INPUT, 결합 방식만 변경</h1>
<p>subdivision으로 만든 타깃 체크포인트, 단순한 다공성 셀, 6,000개 선택 면, 깊이 1.6, offset 0.35, xy_scale 0.7, z_factor 0.35를 동일하게 고정했다. 높이 증폭이나 추가 평활화 없이 실제 Tissue의 LAST / UNUSED를 실행했다. 모든 이미지는 OBJ의 실제 렌더이며 전후 카메라와 조명을 공유한다.</p>
<p><a href="README.txt">실행 방법</a> · <a href="compare_tissue.py">비교 실행 코드</a> · <a href="gateflow/tissue_comparison.py">검증·출력 연결부</a> · <a href="runs/tissue_composition23/comparison.json">실행 기록</a> · <a href="review.html">이전 타깃·파이프라인 결과</a></p>
<p class="note">선택 면 6,000 / 688,128개(약 0.87%)를 고정한 국소 비교다. LAST 화면에서 나머지 게이트가 사라지는 것은 원본 면을 실제로 제외했기 때문이다. UNUSED는 선택된 원본 면을 제거하지만 현재 셀은 면 경계와 자동으로 이어지지 않아 열린 경계가 남는다. 완성된 연속 다공성 게이트나 단일 솔리드로 주장하지 않는다.</p>
<p>관찰 결과: 덧붙임에서는 원본 면이 셀의 구멍 뒤를 막는다. UNUSED에서는 같은 높이의 셀인데도 검은 빈 공간이 보이며, 큰 접힘은 주변의 미선택 타깃과 함께 남는다. LAST에서 셀 자체의 구멍과 국소 흐름은 확인되지만 패치가 너무 희박하고 분리되어 큰 다발 전체를 재구성하지 못한다. 현재 시험은 결합 방식의 오류를 확인·수정했으며, 연속된 다공성 표면 생성은 다음 해결 과제다.</p>
'''+''.join(panels)+'''<h2>실제 면 구성 검사</h2><table><tr><th>방식</th><th>남은 선택 원본 면</th><th>남은 미선택 원본 면</th><th>열린 경계 모서리</th><th>대칭 오차</th><th>메시</th></tr>'''+''.join(rows)+'''</table>
<p>모든 결과에 유한 좌표, 0면적 삼각형, 비다양체 모서리, 방향 일관성, OBJ/PLY 재로드 검사를 수행했다. 열린 경계는 숨기거나 자동으로 메우지 않았다. 동일 셀 기하가 세 결합 방식에 포함되는지도 수치로 확인했다. 이 검사는 모든 자기 교차의 부재를 보증하지 않는다.</p>
<h2>LAST / UNUSED / PATCH</h2><p>LAST는 마지막 생성 조직만, UNUSED는 생성 조직과 사용하지 않은 타깃 면을 유지한다. 기존 덧붙임 방식은 LAST 결과에 원본 전체를 추가하는 별도 처리였다. <a href="https://github.com/alessandro-zomparelli/tissue/wiki/Tessellate">Tissue 공식 문서</a>와 설치된 실제 소스 양쪽에서 확인했다.</p>
<p>PATCH는 subdivision 이전 사각면 크기를 기준으로, 마지막 Subdivision/Multires modifier로 얻은 곡면을 따라 매핑한다. 이미 subdivision이 적용된 메시만 넘기면 이 구조가 없고 현재 upstream은 QUAD로 폴백한다. 이번 통제 비교에는 PATCH를 사용하지 않았다. 이후 도입할 경우 이전 단계 cage와 crease modifier를 함께 전달하고 타깃 곡면 일치부터 검증해야 한다.</p></main></html>'''
(ROOT/'tissue_comparison.html').write_text(page,encoding='utf8')
print('tissue_comparison.html written')
