"""Portable actual-image review and source archive for three macro prototypes."""
from pathlib import Path
import argparse
import hashlib
import html
import json
import shutil
import zipfile
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()


def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')


INFO={
 'S01_CALYX':dict(title='겹꽃받침',text='작은 하부 마디 → 긴 줄기 → 서로 겹치는 두 상부 군집. 구간마다 3·5·4 방향의 겹막을 사용했습니다.',
    assessment='중첩과 크기 위계가 보입니다. 중앙의 긴 줄기와 상부 접힘을 이어 주는 중간 구조는 더 필요합니다.'),
 'S02_RECURSIVE':dict(title='불균등한 되접힘',text='아래의 작은 접힘 2개, 중간의 큰 접힘 1개, 위의 작은 접힘 2개를 서로 다른 방향과 간격으로 배치했습니다.',
    assessment='절단·반사와 불균등 배치가 작동합니다. 현재는 큰 접힘 하나와 매끈한 줄기가 지배하는 기술 시안입니다.'),
 'S03_CURTAIN':dict(title='연속 겹막',text='긴 접힘 3개가 줄기를 따라 굽고, 길이가 다른 짧은 접힘 2개가 부분적으로 이어집니다.',
    assessment='긴 흐름이 명확합니다. 넓은 막이 갈라지고 작은 겹으로 이어지는 중간 규모의 구조는 더 발전시킬 여지가 있습니다.')}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--exports-root',type=Path,required=True)
    a=p.parse_args()
    qa=read(a.exports_root/'models/STRUCTURAL_EXPORT_AND_QA.json')
    if not qa['passed'] or qa['completed_count']!=3:raise ValueError('All three actual native models required.')
    models={r['id']:r for r in qa['variants']}
    out=a.exports_root/'REVIEW';out.mkdir(exist_ok=False)
    images=out/'images';images.mkdir()
    mapped={sid:dict(refined={},initial={}) for sid in models}
    render_bindings=[]
    for rp in sorted(a.root.glob('*/RENDER_RECEIPT.json')):
        r=read(rp);render_bindings.append(dict(path=str(rp),sha256=sha(rp)))
        for item in r['items']:
            initial=item['id'].endswith('_G00')
            sid=item['id'][:-4] if initial else item['id']
            if sid not in models:continue
            source=models[sid]['actual_G00_geometry' if initial else 'actual_G02_geometry']
            if item['source_sha256']!=source['sha256']:raise ValueError('Displayed mesh differs from exported actual stage.')
            for im in item['images']:
                src=Path(im['path'])
                if sha(src)!=im['sha256']:raise ValueError('Actual PNG binding changed.')
                dest=images/src.name
                if dest.exists():raise ValueError('Duplicate review image.')
                shutil.copyfile(src,dest)
                mapped[sid]['initial' if initial else 'refined'][im['view']]='images/'+dest.name
    for sid,row in mapped.items():
        if set(['whole','crown','body','oblique','structural_parts'])-row['refined'].keys() or 'whole' not in row['initial']:
            raise ValueError('Missing actual required views for '+sid)
    # One common-scale overview. Crops preserve each full silhouette.
    font=ImageFont.truetype(r'C:/Windows/Fonts/malgun.ttf',27)
    canvas=Image.new('RGB',(1650,1300),(26,29,32));draw=ImageDraw.Draw(canvas)
    payload=[]
    for i,sid in enumerate(sorted(models)):
        im=Image.open(out/mapped[sid]['refined']['whole']).convert('RGB')
        w,h=im.size;im=im.crop((int(w*.25),0,int(w*.75),h));im.thumbnail((540,1190))
        x=i*550;canvas.paste(im,(x+(550-im.width)//2,70))
        draw.text((x+18,12),INFO[sid]['title'],font=font,fill=(238,236,228))
        model_path=Path(models[sid]['model']['path'])
        rel='../'+model_path.relative_to(a.exports_root).as_posix()
        payload.append(dict(id=sid,**INFO[sid],**mapped[sid],model=rel))
    canvas.save(out/'STRUCTURAL_COMPARISON.png')
    data=json.dumps(payload,ensure_ascii=False).replace('</','<\/')
    page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>체셔 · 초기 접힘 구성</title>
<style>body{margin:0;background:#171c20;color:#e9e8e1;font:16px/1.65 system-ui,"Malgun Gothic",sans-serif}main{max-width:1500px;margin:auto;padding:30px}h1{font-size:30px;margin:0}p{max-width:1000px;color:#c7c9c7}a{color:#7edac8}select,button{font:inherit;color:#eee;background:#2a3339;border:1px solid #52616b;border-radius:6px;padding:7px 12px}.toolbar{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin:24px 0}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.card{background:#222a2f;border:1px solid #3d484f;border-radius:10px;overflow:hidden}.card img{display:block;width:100%;aspect-ratio:1;object-fit:contain;background:#20272c}.caption{padding:16px}.caption h2{margin:0;font-size:21px}.small{font-size:14px;color:#b8bfbd}.legend{display:flex;gap:16px;flex-wrap:wrap}.swatch{width:12px;height:12px;display:inline-block;margin-right:7px}.note{border-left:3px solid #7bcbbd;padding:6px 16px;margin:26px 0}footer{margin-top:36px;border-top:1px solid #3c484e;padding-top:20px;font-size:14px}details{margin:15px 0}summary{cursor:pointer}@media(max-width:850px){.grid{grid-template-columns:1fr}main{padding:18px}}</style>
<main><h1>초기 접힘 구성 · 세 가지 구조 시안</h1><p>서로 다른 큰 접힘의 배치와 연결을 비교합니다. 표면 장식은 추가하지 않았습니다. 기존 기둥의 돌출량 비교 26안은 별도 진단 기록으로 보존했습니다.</p>
<div class="toolbar"><label>화면 <select id="view"><option value="whole">전체</option><option value="crown">상부 확대</option><option value="body">몸통 확대</option><option value="oblique">사선 전체</option><option value="structural_parts">구성 색상</option></select></label><label>단계 <select id="stage"><option value="refined">두 번 분할한 후속 형상</option><option value="initial">초기 입체</option></select></label></div>
<div class="grid" id="cards"></div><div class="legend"><span><i class="swatch" style="background:#0a6ebf"></i>중심 줄기</span><span><i class="swatch" style="background:#e8590e"></i>큰 접힘</span><span><i class="swatch" style="background:#03a176"></i>작은 겹 / 하위 접힘</span></div><p class="small">색은 실제 초기 구성 부품과 그 후손을 나타냅니다. 곡률이나 변형 강도를 측정한 분류가 아닙니다. 전체 화면은 같은 물리적 카메라 배율입니다.</p>
<div class="note">현재는 큰 구조를 비교하는 초기 시제품입니다. 참고 이미지처럼 여러 크기의 주름이 서로 갈라지고 이어지는 풍부함까지 달성한 결과로 보지는 않습니다. 닫힌 한 성분·관통 고리 0·양의 면적·실제 세대 대응과 파일 재읽기를 확인했으며, 제작용 최종 검증은 수행하지 않았습니다.</div>
<details><summary>참고한 생성 원리</summary><p>구역별로 다른 규칙을 쓰는 단순한 기둥 입력은 <a href="https://www.michael-hansmeyer.com/subdivided-columns">Subdivided Columns</a>, 큰 형태와 작은 형태를 함께 바꾸는 분할 가중치와 법선 방향 확장은 <a href="https://michael-hansmeyer.com/platonic-solids.html">Platonic Solids</a>, 초기 변경이 후손 형상으로 이어지는 원리는 <a href="https://michael-hansmeyer.com/digital-grotesque-I.html">Digital Grotesque I</a>의 공식 설명을 참고했습니다. 공개 설명만으로 세대별 변형률을 수치 비교할 수는 없습니다. 이번 시안은 그 구현을 재현했다고 주장하지 않습니다.</p></details>
<footer><a href="STRUCTURAL_COMPARISON.png">전체 비교 이미지</a> · <a href="../STRUCTURAL_GRAMMAR_SOURCE.zip">생성 알고리즘과 실행 기록</a><p>기준 완성 모델은 보존했습니다. 이 세 시안의 미적 채택은 아직 결정하지 않았습니다.</p></footer></main>
<script>const data=DATA;const view=document.querySelector('#view'),stage=document.querySelector('#stage'),cards=document.querySelector('#cards');function show(){cards.innerHTML='';for(const r of data){const s=stage.value;const v=s==='initial'?'whole':view.value;const article=document.createElement('article');article.className='card';const img=document.createElement('img');img.src=r[s][v];img.alt=r.title+' '+v;const box=document.createElement('div');box.className='caption';const h=document.createElement('h2');h.textContent=r.title;box.appendChild(h);const p=document.createElement('p');p.textContent=r.text;box.appendChild(p);const note=document.createElement('p');note.className='small';note.textContent=r.assessment;box.appendChild(note);const a=document.createElement('a');a.href=r.model;a.textContent='실제 모델 PLY';box.appendChild(a);article.append(img,box);cards.appendChild(article)}view.disabled=stage.value==='initial'}view.onchange=show;stage.onchange=show;show();</script></html>'''.replace('DATA',data)
    (out/'review.html').write_text(page,encoding='utf8')
    archive=a.exports_root/'STRUCTURAL_GRAMMAR_SOURCE.zip'
    sources=['grammar_kernel.py','fan_grammar.py','curtain_grammar.py','recursive_grammar.py','recursive_grammar_closed.py','build_grammar.py','build_grammar_v2.py','build_grammar_v3.py','inspect_and_export_v2.py','finalize_review.py']
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name in sources:z.write(HERE/name,'experiments/structural_grammar_20261016/'+name)
        repo=HERE.parents[1]
        for name in ['reference_subdivision.py','normalization.py','__init__.py']:
            z.write(repo/'src/cheshire'/name,'src/cheshire/'+name)
        for sub in sorted(a.root.iterdir()):
            if (sub/'RECEIPT.json').exists():
                r=read(sub/'RECEIPT.json')
                if r.get('schema')!='CHESHIRE_NEW_STRUCTURAL_GRAMMAR_V1':continue
                for name in ['RECEIPT.json','DESIGN.json','COLOR_LEGEND.json']:
                    z.write(sub/name,'executed/'+r['id']+'/'+name)
        z.writestr('README.txt','Executed prototype source for the CHESHIRE workspace. Requires NumPy, SciPy, manifold3d and the existing repository. The local dependency directory is recorded in grammar_kernel.py. Re-run each generator with build_grammar_v3.py --module <module> --id <id> --output <fresh-folder>. This is a source archive, not a self-contained environment or a fabrication certificate. The 26 earlier protrusion variants are not adopted. No ornament was added to these three structures.')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('Source archive CRC failed.')
    manifest=dict(schema='CHESHIRE_STRUCTURAL_GRAMMAR_REVIEW_V1',status='COMPLETED_INITIAL_STRUCTURE_PROTOTYPES',
        ids=sorted(models),review_html=str(out/'review.html'),comparison=str(out/'STRUCTURAL_COMPARISON.png'),
        actual_native_QA=dict(path=str(a.exports_root/'models/STRUCTURAL_EXPORT_AND_QA.json'),sha256=sha(a.exports_root/'models/STRUCTURAL_EXPORT_AND_QA.json')),
        render_receipts=render_bindings,source_archive=dict(path=str(archive),sha256=sha(archive)),
        views=mapped,ornament_added=False,user_adopted=False,reference_level_achieved=False,fabrication_certified=False)
    write(a.exports_root/'DELIVERY_MANIFEST.json',manifest)
    print(out/'review.html',flush=True)


if __name__=='__main__':main()
