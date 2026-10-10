"""Build a local review page from completed runs and a source-only archive."""
from pathlib import Path
import json,html,zipfile
ROOT=Path(__file__).resolve().parent
choices=[('micro_simple_tissue23','최신: 다발형 TARGET 보존 + 단순한 다공성 INPUT'),('hierarchy_microfold23','Tissue 이전 TARGET: 큰 접힘 3회 → 해상도 증가 → 작은 접힘 3회'),('hierarchy_sixfold23','같은 해상도에서 접기·돌출 6회'),('hierarchy_twist23','기둥 꼬임 강화 / 접기·돌출 3회'),('hierarchy_base23','주 흐름·보조 조직·조용한 영역'),('region_fibers23','이전 타깃 보존 + 후기 Tissue 실험'),('region_fans_wide23','다른 중립 입력 / 동일 region_fans 설정')]
cards=[]
for name,label in choices:
 folder=ROOT/'runs'/name;record=folder/'run.json'
 if not record.is_file():continue
 r=json.loads(record.read_text())
 if r['status']!='COMPLETE':continue
 base='runs/'+name;f=r['final'];images=[]
 for view in ['front','oblique']:
  rel=base+'/views/'+view+'.png';images.append(f'<a href="{rel}"><img src="{rel}" alt="{view}"></a>')
 links=[('OBJ',base+'/result.obj'),('PLY',base+'/result.ply'),('생성 단계',base+'/progression.png'),('검증 기록',base+'/run.json'),('실행 설정',base+'/config.json')]
 if (folder/'cycles/detail.png').is_file():links.append(('근접 렌더',base+'/cycles/detail.png'))
 if (folder/'cycles/micro.png').is_file():links.append(('셀 확대 / 공통 카메라',base+'/cycles/micro.png'))
 anchor=' · '.join(f'<a href="{path}">{text}</a>' for text,path in links)
 cards.append(f'<article><h2>{html.escape(label)}</h2><p>{f["triangles"]:,} triangles · {f["components"]:,} components · symmetry error {f["symmetry_max_error"]:.2g}</p><div class="views">'+''.join(images)+f'</div><p>{anchor}</p></article>')
page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CHESHIRE / 생성 결과 비교</title><style>
body{margin:0;background:#101215;color:#e6e4de;font:16px/1.7 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:40px 24px}h1{font-size:34px}h2{font-size:21px;margin-bottom:0}a{color:#9fccdd}article{margin:32px 0 48px;border-top:1px solid #3a3d41;padding-top:18px}.views{display:grid;grid-template-columns:1fr 1fr;gap:12px}img{display:block;width:100%;height:auto}p{max-width:1000px}.note{background:#22272c;padding:18px 24px;border-left:3px solid #bca17d}@media(max-width:650px){.views{grid-template-columns:1fr}}</style><main>
<h1>CHESHIRE / 흐름·꼬임·미세 접힘 비교</h1>
<p>같은 생성 엔진에 입력과 설정을 전달해 만든 실제 메시다. 이미지는 메시의 렌더이며 생성형 이미지나 텍스처 합성이 아니다.</p>
<p><a href="tissue_comparison.html">최신: 덧붙임 / UNUSED 치환 / LAST 단독 비교</a> · <a href="README.txt">재실행 안내와 현재 한계</a> · <a href="run.py">실행 코드</a> · <a href="gateflow/engine.py">연산 코드</a> · <a href="pipeline_source.zip">파이프라인 소스 묶음 — 외부 환경 제외</a> · <a href="validation_summary.json">검증 요약</a> · <a href="test_runs/tissue_combine_7.xml">기능 테스트 18개</a></p>
<p class="note">최신 지시에 따라 합성 중립 게이트로 개발했다. 실제 ALICE 연동 결과가 아니다. Tissue 실험은 타깃을 보존한 다중 쉘 조립체이며 하나의 Boolean union solid는 아니다. 기본 메시 검사 통과는 모든 자기 교차의 부재나 제작 가능성의 증명이 아니다. 조형의 최종 선택은 사용자가 한다.</p>
<h2>이전 실험: 단순 INPUT / 타깃 전체 덧붙임</h2>
<p>다발의 큰 흐름은 subdivision TARGET에서 만든다. 최신 Tissue 실험은 단순 셀을 6,000개 선택 면에 작게 매핑하고 기존 타깃을 보존한다. 왼쪽은 적용 전, 오른쪽은 적용 후 실제 메시다. 큰 주름 보존과 작은 조직의 시각적 효과를 구분해 비교한다. 셀의 구멍이 타깃 몸체까지 관통하는 것은 아니다.</p>
<div class="views"><a href="runs/hierarchy_microfold23/cycles/detail.png"><img src="runs/hierarchy_microfold23/cycles/detail.png" alt="Tissue 이전 TARGET"></a><a href="runs/micro_simple_tissue23/cycles/detail.png"><img src="runs/micro_simple_tissue23/cycles/detail.png" alt="단순 셀 적용 후"></a></div>
<p>전체 타깃 면이 구멍 뒤를 막는 문제를 확인하여, 현재는 결합 방식 비교로 전환했다. 높이 증폭안은 채택하지 않았다.</p>
<h2>변형이 집중되는 이유</h2><p>주황색은 높은 영향, 파란색은 낮은 영향이다. 입력 개구부 경계, 상부/지지부의 면 영역 경계, 현재 곡률을 실제로 사용한다. 최신 위계 설정은 주변의 국소 변형보다 opening–lintel–전이부를 우선한다.</p>
<a href="runs/hierarchy_base23/04_pleat_flow/region_maps.png"><img src="runs/hierarchy_base23/04_pleat_flow/region_maps.png" alt="실제 영역별 영향 지도"></a>
'''+''.join(cards)+'</main></html>'
(ROOT/'review.html').write_text(page,encoding='utf8')
with zipfile.ZipFile(ROOT/'pipeline_source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(ROOT.glob('*.py')):z.write(f,f.name)
 for name in ['README.txt','requirements.txt','environment.json','tissue_focus.json']:
  z.write(ROOT/name,name)
 for directory in ['gateflow','configs','inputs','components','tests']:
  for f in sorted((ROOT/directory).rglob('*')):
   if f.is_file() and '__pycache__' not in f.parts and f.suffix in ['.py','.json','.obj','.txt']:
    z.write(f,f.relative_to(ROOT))
print('review.html and pipeline_source.zip written')
