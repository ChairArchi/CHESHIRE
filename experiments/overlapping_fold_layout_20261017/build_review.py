"""Package actual source-fold/G4 layout comparisons and their recorded algorithms."""
from pathlib import Path
import argparse
import hashlib
import html
import json
import shutil
import zipfile
from PIL import Image, ImageDraw, ImageFont


IDS=['K00','K06','K08','K08_M2']
NOTES={
 'K00':'원래 두 주접힘 · 같은 샘플 밀도의 기준안',
 'K06':'여섯 주접힘의 간격·폭·방향을 다르게 중첩',
 'K08':'여덟 주접힘을 더 촘촘히, 불균등하게 중첩',
 'K08_M2':'여덟 주접힘 + 만델벌브 생성장 두 개의 중첩 확대'}
SHORT={'K00':'기준안','K06':'여섯 접힘','K08':'여덟 접힘','K08_M2':'두 생성장 중첩'}
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def record(path):return dict(path=str(path),sha256=sha(path))


def board(rows,path):
    canvas=Image.new('RGB',(1680,1000),'#15191d');d=ImageDraw.Draw(canvas)
    title=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',29)
    label=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',23)
    small=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',18)
    d.text((24,18),'같은 생성 원리 · 불균등한 여섯 / 여덟 주접힘의 중첩',font=title,fill='#f0eee8')
    d.text((24,62),'G4 실제 메시 · 같은 카메라와 배율 · K00 기준 + 6접힘 / 8접힘 / 두 만델벌브 중첩',font=small,fill='#b4c0c8')
    for i,row in enumerate(rows):
        x=12+420*i;y=108
        image=Image.open(row['images']['layout_whole']).convert('RGB').crop((300,65,900,1145))
        image.thumbnail((404,750),Image.Resampling.LANCZOS)
        canvas.paste(image,(x+(404-image.width)//2,y))
        d.text((x+8,870),row['id']+' · '+SHORT[row['id']],font=label,fill='#f0eee8')
        text=NOTES[row['id']]
        # Fixed short caption lines avoid clipping long Korean phrases.
        lines=[text] if len(text)<25 else [text[:24],text[24:]]
        for n,line in enumerate(lines):d.text((x+8,912+28*n),line,font=small,fill='#b4c0c8')
    canvas.save(path)


PAGE='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>큰 접힘 배치 비교</title>
<style>*{box-sizing:border-box}body{margin:0;background:#15191d;color:#eeeae2;font:16px/1.65 system-ui,"Malgun Gothic",sans-serif}main{max-width:1480px;margin:auto;padding:32px 20px}h1{font-size:29px;margin:0 0 12px}p{max-width:1080px}a{color:#9bd6dc}button,select{font:inherit;padding:8px 12px;border:1px solid #5b6872;border-radius:5px;background:#27323a;color:#fff}nav{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.card{background:#20282e;padding:12px;border-radius:8px}.card img{width:100%;display:block}.card h2{font-size:19px;margin:12px 0}.card p{margin:8px 0;color:#c2cdd4}.board{width:100%;margin:28px 0}.muted{color:#b5c1c9}.legend{display:flex;gap:12px;flex-wrap:wrap}details{margin:24px 0;padding:16px;background:#20282e}table{border-collapse:collapse;width:100%}th,td{text-align:left;border-bottom:1px solid #46525b;padding:10px}@media(max-width:1000px){.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.grid{grid-template-columns:1fr}}</style>
<main><h1>불균등한 여섯·여덟 접힘을 서로 중첩</h1>
<p>기존 접힘 생성식의 시작 지점·적용 폭·방향·개수를 바꿔 초기 형상을 다시 만들었습니다. 바탕 반지름, 각 접힘의 돌출·귀환 진폭, 끝부 생성식과 후속 연산의 수학은 유지했습니다. K08_M2는 같은 여덟 접힘 입력에서 두 만델벌브 생성장의 겹침 범위도 넓힌 비교안입니다.</p>
<p class="muted">K00은 원래 두 접힘을 나머지 안과 같은 49링으로 샘플한 기준안입니다. 6·8은 실제 실행한 주접힘 수이며, 보이는 덩어리가 정확히 그 수로 분리된다는 뜻은 아닙니다. G4는 초기 형상 비교 단계입니다.</p>
<nav><label>보기 <select id="view"><option value="layout_whole">G4 전체</option><option value="upper_same">G4 상부 확대</option><option value="source">G0 초기 접힘</option><option value="actual_change">G0 실제 변화 컬러</option><option value="field_change">두 만델벌브 중첩의 G2 변화</option></select></label><a href="comparison_board.png">비교 이미지</a><a href="algorithm_source.zip">알고리즘·레시피</a></nav>
<div class="grid" id="grid"></div>
<p class="muted">G0 컬러는 같은 초기 재료 정점에서 원래 형상과의 실제 좌표 차이를 표시합니다. 각 면의 네 정점 평균이며, 전 안에 같은 모델 단위 문턱을 사용했습니다. 회색 &lt;0.01 · 파랑 0.01–0.05 · 초록 0.05–0.15 · 주황 0.15–0.35 · 빨강 ≥0.35.</p>
<a href="comparison_board.png"><img class="board" src="comparison_board.png" alt="같은 G4 단계의 원래 기준안과 새로운 세 배치"></a>
<details><summary>검증과 재사용</summary><p>원래 주형 생성 함수를 다시 평가해 저장된 초기 좌표와 생성 성분을 독립 검사했습니다. 실제 부모면·분할 계보·반사 대칭·닫힌 메시와 PLY 전체 저장 값을 확인했습니다. 이 비교는 시각적 프로토타입이며, 자기교차나 제작 적합성을 인증하지 않습니다.</p><p>알고리즘 ZIP에는 고정한 기존 소스와 새 조절 레시피, 실행·검사 기록을 넣었습니다. 외부 초기 입력과 유한 Mandel field 캐시는 원래 경로·해시를 참조하며 ZIP에 포함하지 않았습니다.</p><p><a href="delivery.json">출력 기록</a> · <a href="qa.json">독립 형상 검사</a></p></details></main>
<script>const rows=__DATA__;const e=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function draw(){let view=document.querySelector('#view').value;document.querySelector('#grid').innerHTML=rows.map(r=>{let source=r.images[view];return `<article class="card"><h2>${e(r.id)} · ${e(r.label)}</h2>${source?`<a href="${e(source)}"><img src="${e(source)}" alt="${e(r.label)} ${e(view)}"></a>`:(view==='field_change'?'<p>K08_M2에서 같은 K08 입력과 비교한 결과를 표시합니다.</p>':'<p>원래 기준 형상 · 좌표 차이 0</p>')}<p>${e(r.note)}</p><a href="${e(r.ply)}">실제 G4 PLY 모델</a></article>`}).join('')};document.querySelector('#view').addEventListener('change',draw);draw();</script></html>'''


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--exports',type=Path,required=True);p.add_argument('--qa',type=Path,required=True)
    a=p.parse_args();qa=read(a.qa)
    if not qa['passed'] or qa['completed_count']!=4:raise ValueError('Independent QA must pass all four cases.')
    catalog=read(Path(__file__).parent/'overlap_recipes.json')
    recipes={r['id']:r for r in catalog['recipes']}
    render_path=a.root/'COMPARISON_RENDER/RENDER_RECEIPT.json';render=read(render_path)
    outputs=a.exports/'REVIEW';outputs.mkdir(exist_ok=False)
    images_dir=outputs/'images';images_dir.mkdir()
    bindings=[];image_map={}
    for item in render['items']:
        geom=Path(item['geometry'])
        if sha(geom)!=item['source_sha256']:raise ValueError('Actual rendered geometry changed.')
        for im in item['images']:
            source=Path(im['path'])
            if sha(source)!=im['sha256']:raise ValueError('Actual rendered image changed.')
            target=images_dir/source.name;shutil.copyfile(source,target)
            if sha(target)!=im['sha256']:raise ValueError('Image copy differs.')
            image_map[(item['id'],im['view'])]=target
            bindings.append(record(target))
    if len(bindings)!=16:raise ValueError('Expected actual 16 rendered images.')
    rows=[];qa_rows={r['id']:r for r in qa['variants']}
    for ident in IDS:
        ply=Path(qa_rows[ident]['model']['path'])
        if sha(ply)!=qa_rows[ident]['model']['sha256']:raise ValueError('Native model changed.')
        pictures={view:str(image_map[(ident,view)]) for view in ['layout_whole','upper_same']}
        pictures['source']=str(image_map[(ident+'_G0','layout_whole')])
        if ident!='K00':pictures['actual_change']=str(image_map[(ident+'_G0','actual_change')])
        if ident=='K08_M2':pictures['field_change']=str(image_map[('K08_M2_G2','field_change')])
        rows.append(dict(id=ident,label=recipes[ident]['label_ko'],note=NOTES[ident],images=pictures,ply=str(ply)))
    board_path=outputs/'comparison_board.png';board(rows,board_path)
    portable=[]
    for row in rows:
        portable.append(dict(row,id=row['id'],images={k:Path(v).relative_to(outputs).as_posix() for k,v in row['images'].items()},
            ply='../models/'+Path(row['ply']).relative_to(a.exports/'models').as_posix()))
    page=outputs/'review.html'
    page.write_text(PAGE.replace('__DATA__',json.dumps(portable,ensure_ascii=False).replace('</','<\\/')),encoding='utf8')
    shutil.copyfile(a.qa,outputs/'qa.json')
    sources={};repo=Path(__file__).resolve().parents[2]
    for ident in IDS:
        contract=read(a.root/'variants'/ident/'RECIPE.json')
        for original,binding in contract['source_snapshots'].items():
            file=Path(binding['snapshot'])
            if sha(file)!=binding['sha256']:raise ValueError('Executed source binding differs.')
            relative=Path(original).relative_to(repo).as_posix()
            name='source/'+relative
            if name in sources and sources[name][1]!=binding['sha256']:raise ValueError('Conflicting source versions.')
            sources[name]=(file,binding['sha256'])
    for file in Path(__file__).parent.glob('*.py'):sources['source/'+file.relative_to(repo).as_posix()]=(file,sha(file))
    for relative in ['experiments/inherited_rule_variations_20261017/inspect_inherited.py',
                     'experiments/inherited_strong_layout_20261017/inspect_strong.py',
                     'experiments/early_dynamic_variations_20261016/run_variation_batch.py',
                     'experiments/early_dynamic_variations_20261016/render_variations.py']:
        file=repo/relative;sources['source/'+relative]=(file,sha(file))
    archive=outputs/'algorithm_source.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name,(file,digest) in sorted(sources.items()):z.write(file,name)
        z.write(Path(__file__).parent/'overlap_recipes.json','configuration/overlap_recipes.json')
        z.write(a.qa,'records/independent_qa.json');z.write(render_path,'records/render_receipt.json')
        for ident in IDS:
            for name in ['RECIPE.json','RECIPE_EARLY.json','RECEIPT.json']:
                z.write(a.root/'variants'/ident/name,'records/'+ident+'/'+name)
            for stage in sorted((a.root/'variants'/ident/'states').iterdir()):
                if (stage/'generation.json').is_file():
                    z.write(stage/'generation.json','records/'+ident+'/stages/'+stage.name+'/generation.json')
        z.writestr('README.txt','Original SPAN fold constructor with actual seed-event positions/spans/directions/count varied. Original kernels and immutable external input/cache bindings are preserved. Native NPZ/PLY and external finite-field caches are not included. Run source/experiments/overlapping_fold_layout_20261017/replay_overlap.py --recipe <single recipe JSON> --output <fresh folder> --source-repo <original checkout>. K00 uses the original two folds at the same 49-ring sampling as all variants. Original25 seed reconstruction is verified separately. K06/K08 change fold placement/count using the same constructor. K08_M2 uses the identical K08 seed with genuinely recomputed overlapping two-Mandel-field targets. Visual prototype; no self-intersection or fabrication certification.')
        z.writestr('SOURCE_MANIFEST.json',json.dumps({k:v[1] for k,v in sources.items()},indent=2))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('Source archive integrity failed.')
    for row in portable:
        for path in [row['ply'],*row['images'].values()]:
            if not (outputs/path).is_file():raise ValueError('Unresolved actual gallery asset.')
    manifest=dict(passed=True,model_count=4,rendered_image_count=16,user_adopted=False,
        same_original_fold_constructor=True,variants_original_G0_exact=False,sampling_matched_baseline=True,original25_constructor_verified_separately=True,
        original_radius_amplitudes_caps_and_downstream_operator_kernels_unchanged=True,
        gallery=record(page),board=record(board_path),algorithm_archive=record(archive),
        QA=record(a.qa),actual_images=bindings,main_model_replaced=False,
        self_intersection_or_manufacturing_certified=False)
    (outputs/'delivery.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print('STRONG_REVIEW_READY',page)


if __name__=='__main__':main()
