"""Package actual initial-G4 models and hash-bound render comparisons.

Writes only a new REVIEW directory under --exports-root. Historical producer
assets/models are read-only. The code archive is an auditable prototype source
package; it does not pretend to contain the historical replay inputs.
"""
from pathlib import Path
import argparse
import hashlib
import html
import json
import os
import re
import shutil
import time
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
FAMILIES={"B":"기준형","O":"큰 주름 겹침","F":"부채형 위계","T":"반사 비틀림","C":"긴 주름의 묶음","D":"분기 수 변화"}
VIEWS={"whole":"전체","crown":"상부","body":"몸통","oblique":"사선","deformation":"변형 방향","design_regions":"설계 영역","bands":"재료 구간","authored_material_bands":"재료 구간"}
DEFORMATION=[("작은 G3 변형",[.30,.32,.35]),("바깥으로 벌어짐",[.90,.34,.055]),("안으로 수축",[.035,.42,.78]),("축 방향 접힘·되접힘",[.64,.12,.43]),("둘레 방향 뒤틀림",[.015,.62,.48]),("복합 변형",[.80,.66,.12])]
REFERENCES=[
    dict(title="Subdivided Columns",url="https://www.michael-hansmeyer.com/subdivided-columns.html",text="단순화한 Doric 입력에 몸통·기단·상부 등의 정보를 넣고 구간별 파라미터로 여러 규모의 형상을 전개합니다."),
    dict(title="Platonic Solids",url="https://www.michael-hansmeyer.com/platonic-solids",text="세분화의 배치 가중치와 면·모서리·정점 법선 방향 돌출을 바꾸어 전체 형태와 작은 형상을 함께 변화시킵니다."),
    dict(title="Digital Grotesque I",url="https://www.michael-hansmeyer.com/digital-grotesque-I",text="초기 분할의 변경이 후속 자식 면의 계보로 전파되는 원리를 설명합니다.")]
SOURCE_FILES=("early_macro_fields.py","early_bundled_fields.py","variation_recipes.py","variation_recipes.json",
    "branching_recipes.json","macro_replay.py","macro_replay_connected.py","macro_replay_bundled.py",
    "macro_replay_branching.py","sidewall_connected_selection.py","test_early_macro_fields.py",
    "run_variation_batch.py","native_export_and_qa_v3.py","render_variations.py","prepare_review.py",
    "prepare_design_colors.py","finalize_early_review.py")


def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()
def record(p):return dict(path=str(Path(p).resolve()),sha256=sha(p))
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
def rel(p,base):return Path(os.path.relpath(p,base)).as_posix()


def checked(r):
    p=Path(r["path"])
    if sha(p)!=r["sha256"]:raise ValueError("Bound artifact changed: "+str(p))
    return p


def family(sid):return sid[0] if sid and sid[0] in FAMILIES else "기타"


def collect_renders(root,models):
    plans={sha(p):(p,read(p)) for p in sorted(root.rglob("*PLAN*.json"))}
    images={sid:{} for sid in models};receipts=[];ignored=[]
    for receipt in sorted(root.rglob("RENDER_RECEIPT.json"),key=lambda p:p.stat().st_mtime):
        data=read(receipt);items=data.get("items",[])
        if not items and data.get("images"):
            items=[dict(id=im.get("id"),source_sha256=im.get("source_sha256"),images=[im]) for im in data["images"]]
        used=False
        plan_record=plans.get(data.get("plan_sha256"));plan_items={}
        if plan_record:plan_items={v["id"]:v for v in plan_record[1].get("items",[])}
        for item in items:
            sid=item.get("id")
            if sid not in models:continue
            if item.get("source_sha256")!=models[sid]["actual_geometry"]["sha256"]:
                ignored.append(dict(receipt=str(receipt),id=sid,reason="Image geometry does not bind the exported actual G4."));continue
            for im in item.get("images",[]):
                view=im["view"];path=Path(im["path"])
                if not path.is_absolute():path=receipt.parent/path
                if sha(path)!=im["sha256"]:raise ValueError("Actual render PNG changed: "+str(path))
                with Image.open(path) as image:size=list(image.size)
                plan=plan_items.get(sid,{})
                images[sid][view]=dict(path=str(path),sha256=im["sha256"],size=size,
                    render_receipt=record(receipt),view=view,meaning=im.get("meaning",plan.get("color_meaning")),
                    palette=im.get("palette",plan.get("palette")),actual_view=im,
                    render_plan=record(plan_record[0]) if plan_record else None)
                used=True
        if used:receipts.append(record(receipt))
    return images,receipts,ignored


def cropped_whole(path):
    """Layout-only crop: retain >=450/1000 width, expand for a wider silhouette."""
    with Image.open(path) as image:im=image.convert("RGB")
    width=1000;height=round(im.height*width/im.width)
    im=im.resize((width,height),Image.Resampling.LANCZOS)
    a=np.asarray(im);edge=np.concatenate((a[:max(2,height//40)].reshape(-1,3),a[-max(2,height//40):].reshape(-1,3)))
    background=np.median(edge,axis=0);mask=np.max(np.abs(a.astype(float)-background),axis=2)>45
    ys=slice(max(0,height//25),max(1,height-height//25));active=np.flatnonzero(mask[ys].sum(axis=0)>max(3,height*.012))
    left,right=275,725
    if len(active):left=min(left,int(active.min())-35);right=max(right,int(active.max())+36)
    left=max(0,left);right=min(width,right)
    return im.crop((left,0,right,height)),dict(normalized_width=1000,crop=[left,0,right,height],minimum_preserved_width=450,geometry_edited=False)


def montage(ids,models,images,path,title):
    font_path=Path("C:/Windows/Fonts/malgun.ttf")
    font=ImageFont.truetype(str(font_path),22) if font_path.exists() else ImageFont.load_default()
    small=ImageFont.truetype(str(font_path),17) if font_path.exists() else ImageFont.load_default()
    columns=min(len(ids),6);tile_w=270;tile_h=650;rows=(len(ids)+columns-1)//columns
    result=Image.new("RGB",(columns*tile_w,56+rows*tile_h),"#f6f3ed");draw=ImageDraw.Draw(result);draw.text((20,15),title,font=font,fill="#222222");crops=[]
    for i,sid in enumerate(ids):
        im,crop=cropped_whole(images[sid]["whole"]["path"]);crops.append(dict(id=sid,**crop))
        im.thumbnail((tile_w-20,tile_h-95),Image.Resampling.LANCZOS)
        px=(i%columns)*tile_w;py=56+(i//columns)*tile_h
        result.paste(im,(px+(tile_w-im.width)//2,py));draw.text((px+12,py+tile_h-78),sid+" · "+FAMILIES.get(family(sid),"기타"),font=font,fill="#222222")
        draw.text((px+12,py+tile_h-42),"높이비 "+format(models[sid]["actual_height_to_B00_control_height"],".2f"),font=small,fill="#555555")
    result.save(path);return dict(**record(path),layout_crops=crops)


def code_bundle(output,models,root,qa_path):
    entries={};missing=[]
    for name in SOURCE_FILES:
        p=HERE/name
        if p.exists():entries["code/"+name]=p
        else:missing.append(name)
    # Include actual executed per-case recipes and producer bindings, not large meshes.
    for sid,row in models.items():
        receipt=checked(row["source_receipt"]);data=read(receipt)
        entries["executed_cases/"+sid+"/RECEIPT.json"]=receipt
        recipe=Path(data["recipe_file"])
        if sha(recipe)!=data["recipe_sha256"]:raise ValueError("Executed candidate recipe changed")
        entries["executed_cases/"+sid+"/RECIPE.json"]=recipe
    for name in ("BUNDLED_CATALOG.json","CONNECTED_RETRY_CATALOG.json","BRANCHING_CATALOG.json","RUN_REQUEST.json"):
        if (root/name).exists():entries["configuration/"+name]=root/name
    text=("초기 형상 변형 알고리즘·실행 기록\n\n"
        "상태: 진단용·미채택. 이 변형군을 최종 설계로 채택하거나 사용자 목표가 완료되었다고 주장하지 않습니다.\n\n"
        "G0 길이와 물질 좌표 구간, 실제 G1/G2 가중치·되말림, G3 분기·큰 접힘을 바꾸고 G4까지 실제로 재생하는 시제품입니다.\n"
        "일반 수학 필드와 현재 기둥의 재생 어댑터를 구별합니다. early_macro_fields.py와 early_bundled_fields.py는 일반 좌표/차트 입력용이며, macro_replay*.py는 과거 Cheshire 연산·자산을 요구하는 어댑터입니다.\n\n"
        "이 ZIP은 전체 과거 입력 자산을 포함한 독립 실행 배포본이 아닙니다. 원래 source checkout과 실행 receipt에 기록된 역사적 입력·field cache가 필요합니다. 전체 PLY는 별도 models 폴더에 있습니다.\n\n"
        "필요 환경: Python, NumPy, SciPy, Pillow. 실제 렌더링은 Blender와 기존 프로젝트 연산이 필요합니다.\n"
        "일반 필드 검사: python -B code/test_early_macro_fields.py\n"
        "재생 예: python -B code/macro_replay.py --recipe <개별 JSON> --output <새 결과 폴더> --source-repo <원래 source checkout>\n"
        "연결·묶음·분기 안은 각 macro_replay_connected.py / macro_replay_bundled.py / macro_replay_branching.py를 사용합니다.\n"
        "내보내기: python -B code/native_export_and_qa_v3.py --root <실험 폴더> --output <새 models 폴더> --expected-count "+str(len(models))+"\n\n"
        "계산 기준: X/Y 전역 반사, Z축 기둥, inherited material t. 지역 Boolean 반사를 실행했다는 뜻은 아닙니다. 구조적 닫힘/유한값/면적과 PLY 전체 재읽기를 검사하지만 교차·제조 안전성을 인증하지 않습니다.\n")
    manifest=dict(kind="EARLY_DYNAMIC_ALGORITHM_SOURCE_PACKAGE",files={name:record(path) for name,path in entries.items()},
        optional_source_files_not_present=missing,native_QA=record(qa_path),historical_assets_included=False,
        standalone_full_replay_claimed=False,unused_late_or_fine_ornament_excluded=True)
    target=output/"code.zip"
    with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,path in sorted(entries.items()):z.write(path,name)
        z.writestr("README_KO.txt",text);z.writestr("SOURCE_MANIFEST.json",json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:raise ValueError("Code archive CRC failed")
        for name,row in manifest["files"].items():
            if hashlib.sha256(z.read(name)).hexdigest()!=row["sha256"]:raise ValueError("Code archive member SHA differs")
    (output/"README_KO.txt").write_text(text,encoding="utf-8");write(output/"SOURCE_MANIFEST.json",manifest)
    return dict(**record(target),bytes=target.stat().st_size,CRC_passed=True,member_SHA_passed=True)


HTML=r'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>체셔 · 초기 형상 비교</title>
<style>body{margin:0;background:#f5f2ec;color:#242422;font:16px/1.65 "Malgun Gothic",sans-serif}main{max-width:1500px;margin:auto;padding:32px}h1{font-size:32px;margin:0 0 10px}h2{font-size:23px;margin:36px 0 12px}p{max-width:1050px}a{color:#315d75}button,select{font:inherit;padding:9px 14px;border:1px solid #bdb8af;border-radius:8px;background:#fff}button{cursor:pointer}button.active{background:#274b5a;color:white}.tools{display:flex;flex-wrap:wrap;gap:9px;margin:15px 0}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(225px,1fr));gap:16px}.card,.compare article,.detail{background:#fff;border:1px solid #ded8ce;border-radius:14px;padding:13px}.card h3{margin:7px 0 3px}.card img{width:100%;height:340px;object-fit:contain;background:#e9e7e2}.muted{color:#666;font-size:14px}.compare{display:grid;grid-template-columns:1fr 1fr;gap:16px}.compare img{width:100%;height:580px;object-fit:contain;background:#e9e7e2}.detailgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}.detailgrid img{width:100%;object-fit:contain}.swatch{display:inline-block;width:15px;height:15px;border-radius:4px;margin:0 6px 0 14px;vertical-align:middle}.legend{padding:14px;background:#ebe6dc;border-radius:10px;margin:14px 0}.montages img{max-width:100%;height:auto}.badge{padding:3px 7px;background:#e9e5dc;border-radius:5px;font-size:13px}.notes{max-width:1000px}.missing{padding:36px;text-align:center;color:#777}@media(max-width:700px){main{padding:18px}.compare{grid-template-columns:1fr}.compare img{height:470px}.card img{height:300px}}</style>
<main><h1>체셔 · 초기 형상 비교</h1><p><span class="badge">진단용 · 미채택</span></p><p>길이와 마디, 큰 접힘, 초기 연산 가중치와 분기 수를 바꾼 실제 G4 형상입니다. 검토 결과 현재 설계 방향으로 채택하지 않았으며, 초기 변형과 구조 변화의 차이를 확인하는 기록으로 보존합니다.</p><p id="summary" class="muted"></p>
<div class="tools" id="families"></div><div class="tools"><button data-view="whole" class="active">전체</button><button data-view="crown">상부</button><span class="muted">전체는 공통 축척 · 상부는 개별 확대</span></div><div class="grid" id="grid"></div>
<h2>두 안 나란히 비교</h2><div class="tools"><select id="left"></select><select id="right"></select><select id="compareView"><option value="whole">전체</option><option value="crown">상부</option><option value="body">몸통</option><option value="oblique">사선</option><option value="deformation">변형 방향</option><option value="design_regions">설계 영역</option><option value="bands">재료 구간</option></select></div><div class="compare" id="compare"></div>
<h2>참고 확대 관찰</h2><p class="muted">확대 관찰 대상을 기록하는 구역이며 최종 채택을 뜻하지 않습니다.</p><div id="selected"></div>
<h2>컬러 읽는 법</h2><div class="legend" id="legend"></div><p class="muted">변형 방향 색은 지정된 큰 형태 필드의 방향입니다. 길이 변경과 초기 연산·분기 변화 전체를 합산한 변형량은 아닙니다. 설계 영역과 재료 구간 색은 생성에 사용한 구간을 보여주며, 곡률·강도·미적 점수를 뜻하지 않습니다.</p>
<h2>계열별 모음</h2><div class="montages" id="montages"></div>
<h2>알고리즘과 검증 기록</h2><p><a href="code.zip">알고리즘 코드 ZIP</a> · <a href="README_KO.txt">실행 안내</a> · <a href="../models/NATIVE_EXPORT_AND_QA.json">모델 검사 기록</a> · <a href="FINAL_REVIEW_RECEIPT.json">이미지·패키지 기록</a></p><p class="muted">닫힌 연결 구조와 양의 면적, 대칭, 저장 모델의 전체 재읽기를 확인한 초기 형상 시제품입니다. 교차나 제조 안전성의 인증 결과는 아닙니다.</p>
<h2>초기 변형의 참고 원리</h2><div id="references" class="notes"></div><p class="muted">공식 프로젝트 설명에서 정성적 원리를 참고했습니다. 같은 구현이나 수치상 변형 비율을 재현했다는 뜻은 아닙니다.</p></main>
<script id="payload" type="application/json">__DATA__</script><script>
const d=JSON.parse(document.querySelector('#payload').textContent), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let family='all',view='whole';
const get=(m,v)=>m.images[v]||(v==='bands'?m.images.authored_material_bands:null), picture=(m,v,css='')=>{const im=get(m,v);return im?`<a href="${esc(im.url)}"><img class="${css}" src="${esc(im.url)}" alt="${esc(m.id+' '+(d.views[v]||v))}" loading="lazy"></a>`:'<div class="missing">이 보기는 제공되지 않습니다.</div>'};
const title=m=>m.id+' · '+m.family_label;
function grid(){document.querySelector('#grid').innerHTML=d.models.filter(m=>family==='all'||m.family===family).map(m=>`<article class="card">${picture(m,view)}<h3>${esc(title(m))}</h3><div class="muted">${esc(m.label)}<br>높이비 ${m.height_ratio.toFixed(2)} · ${m.triangles.toLocaleString()}삼각형</div><a href="${esc(m.ply)}">PLY</a></article>`).join('')}
document.querySelector('#summary').textContent=`기준형 포함 ${d.models.length}안 · G4 native 형상 · 선택 ${d.selected.length}안`;
document.querySelector('#families').innerHTML='<button class="active" data-family="all">전체 계열</button>'+Object.entries(d.families).filter(([k])=>d.models.some(m=>m.family===k)).map(([k,v])=>`<button data-family="${k}">${esc(v)}</button>`).join('');
document.querySelector('#families').onclick=e=>{if(!e.target.dataset.family)return;family=e.target.dataset.family;document.querySelectorAll('[data-family]').forEach(b=>b.classList.toggle('active',b===e.target));grid()};
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{view=b.dataset.view;document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x===b));grid()});
for(const id of ['left','right'])document.querySelector('#'+id).innerHTML=d.models.map(m=>`<option value="${esc(m.id)}">${esc(title(m))}</option>`).join('');document.querySelector('#right').selectedIndex=Math.min(1,d.models.length-1);
function compare(){const v=document.querySelector('#compareView').value;document.querySelector('#compare').innerHTML=['left','right'].map(id=>{const m=d.models.find(m=>m.id===document.querySelector('#'+id).value);return `<article><h3>${esc(title(m))}</h3>${picture(m,v)}<p>${esc(d.comments[m.id]||'')} <a href="${esc(m.ply)}">PLY</a></p></article>`}).join('')};for(const id of ['left','right','compareView'])document.querySelector('#'+id).onchange=compare;
document.querySelector('#selected').innerHTML=d.selected.length?d.selected.map(id=>{const m=d.models.find(x=>x.id===id);return `<article class="detail"><h3>${esc(title(m))}</h3><p>${esc(d.comments[id]||'')}</p><div class="detailgrid">${['crown','body','oblique','deformation','design_regions','bands'].filter(v=>get(m,v)).map(v=>`<div><strong>${esc(d.views[v]||v)}</strong>${picture(m,v)}</div>`).join('')}</div></article>`}).join(''):'<p class="muted">선택 기록이 아직 없습니다. 위에서 모든 실제 형상을 비교할 수 있습니다.</p>';
document.querySelector('#legend').innerHTML=d.legends.map(l=>`<div><strong>${esc(l.title)}</strong><p>${esc(l.description)}</p>${l.rows.map(r=>`<span><i class="swatch" style="background:rgb(${r.rgb.map(x=>Math.round(x*255)).join(',')})"></i>${esc(r.name)}</span>`).join('')}</div>`).join('');
document.querySelector('#montages').innerHTML=d.montages.map(m=>`<p><strong>${esc(m.title)}</strong> · <a href="${esc(m.url)}">원본 열기</a></p><a href="${esc(m.url)}"><img src="${esc(m.url)}" alt="${esc(m.title)}" loading="lazy"></a>`).join('');
document.querySelector('#references').innerHTML=d.references.map(r=>`<p><a href="${esc(r.url)}">${esc(r.title)}</a> — ${esc(r.text)}</p>`).join('');grid();compare();</script></html>'''


def main(a):
    started=time.perf_counter();qa_path=a.exports_root/"models/NATIVE_EXPORT_AND_QA.json";qa=read(qa_path)
    if not qa.get("passed") or not qa.get("all_exported_geometry_full_readback_exact"):raise ValueError("Actual full-readback native export must pass first")
    models={row["id"]:row for row in qa["variants"]}
    if len(models)!=len(qa["variants"]) or "B00" not in models:raise ValueError("Unique exported candidates including B00 are required")
    if a.expected_count is not None and len(models)!=a.expected_count:raise ValueError("Export count differs from requested final comparison")
    images,render_receipts,ignored=collect_renders(a.root,models)
    for sid in models:
        if not all(v in images[sid] for v in ("whole","crown")):raise ValueError("Actual whole/crown render missing for "+sid)
        checked(models[sid]["model"])
    selection_path=a.root/"SELECTION.json";selection=read(selection_path) if selection_path.exists() else dict(ids=[],comments={})
    selected=selection.get("ids",[])
    if len(selected)!=len(set(selected)) or any(sid not in models for sid in selected):raise ValueError("Selection must name unique actual exported IDs")
    out=a.exports_root/"REVIEW";out.mkdir(parents=True,exist_ok=False);(out/"images").mkdir();(out/"montages").mkdir();(out/"receipts").mkdir()
    data_models=[];copied=[]
    for sid,row in sorted(models.items()):
        receipt=read(checked(row["source_receipt"]));recipe=receipt["final"]["dynamic_recipe"];views={}
        for view,im in images[sid].items():
            if not re.fullmatch(r"[A-Za-z0-9_-]+",view):raise ValueError("Unsafe view filename")
            target=out/"images"/(sid+"__"+view+Path(im["path"]).suffix.lower());shutil.copyfile(im["path"],target)
            if sha(target)!=im["sha256"]:raise ValueError("Copied PNG changed")
            views[view]=dict(url=rel(target,out),**{k:v for k,v in im.items() if k!="path"});copied.append(dict(id=sid,view=view,source=im["path"],**record(target)))
        data_models.append(dict(id=sid,label=recipe.get("label_ko",sid),family=family(sid),family_label=FAMILIES.get(family(sid),"기타"),
            height_ratio=row["actual_height_to_B00_control_height"],triangles=row["quality"]["triangles"],ply=rel(row["model"]["path"],out),images=views))
    montage_rows=[];montage_proof=[]
    for key,label in FAMILIES.items():
        ids=[sid for sid in sorted(models) if family(sid)==key]
        if not ids or key=="B":continue
        title=label+" · 전체 비교";proof=montage(ids,models,images,out/"montages"/(key+"_whole.png"),title)
        montage_proof.append(proof);montage_rows.append(dict(title=title,url=rel(proof["path"],out)))
    if selected:
        ids=list(dict.fromkeys(["B00"]+selected));proof=montage(ids,models,images,out/"montages/selected_comparison.png","기준형과 참고안 · 전체 비교")
        montage_proof.append(proof);montage_rows.insert(0,dict(title="기준형과 참고안 · 채택 아님",url=rel(proof["path"],out)))
    legends=[dict(title="변형 방향",description="실제 G3 큰 형태 필드의 우세 방향입니다. 다른 세대의 변형 전체를 뜻하지 않습니다.",rows=[dict(name=k,rgb=v) for k,v in DEFORMATION]),
        dict(title="재료 구간",description="상속된 material t를 나눈 설계 구간입니다. 색 순서가 곡률이나 변형 강도의 순위는 아닙니다.",rows=[])]
    design=[]
    for sid in selected:
        im=images[sid].get("design_regions")
        if im and im.get("palette"):
            rows=[dict(name=v.get("label_ko",v.get("name","")),rgb=v.get("rgb",v.get("rgba",[])[:3])) for v in im["palette"]]
            if rows not in design:design.append(rows)
    for i,rows in enumerate(design):legends.append(dict(title="설계 영역"+(" "+str(i+1) if len(design)>1 else ""),description="초기 연산에 지정한 설계 구간입니다. 변형량 전체나 새 곡률 판정은 아닙니다.",rows=rows))
    payload=dict(models=data_models,selected=selected,comments=selection.get("comments",{}),families=FAMILIES,views=VIEWS,montages=montage_rows,legends=legends,references=REFERENCES,status="DIAGNOSTIC_NOT_ADOPTED",user_adopted=False,goal_complete=False)
    write(out/"review_data.json",payload)
    encoded=json.dumps(payload,ensure_ascii=False).replace("<","\\u003c")
    page=out/"review.html";page.write_text(HTML.replace("__DATA__",encoded),encoding="utf-8")
    archive=code_bundle(out,models,a.root,qa_path)
    for i,r in enumerate(render_receipts):shutil.copyfile(r["path"],out/"receipts"/(f"render_{i:02d}.json"))
    result=dict(kind="ACTUAL_INITIAL_G4_REVIEW_PACKAGE",passed=True,status="DIAGNOSTIC_NOT_ADOPTED",user_adopted=False,goal_complete=False,model_count=len(models),selected_ids=selected,
        gallery=record(page),code_archive=archive,export_QA=record(qa_path),render_receipts=render_receipts,
        copied_actual_images=copied,montages=montage_proof,ignored_incompatible_render_items=ignored,
        selection=record(selection_path) if selection_path.exists() else None,source=record(__file__),
        all_PNG_copies_SHA_exact=True,original_geometry_or_renders_modified=False,
        late_ornament_added=False,reference_comparison_qualitative_only=True,
        self_intersection_or_manufacturing_certificate=False,elapsed_seconds=time.perf_counter()-started)
    write(out/"FINAL_REVIEW_RECEIPT.json",result);print(page,sha(page),len(models),len(copied),archive["sha256"],flush=True)
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);p.add_argument("--exports-root",type=Path,required=True);p.add_argument("--expected-count",type=int);main(p.parse_args())
