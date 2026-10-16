"""Retain the verified prototype algorithm while presenting only initial shapes."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
import numpy as np


def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    repo=Path(__file__).resolve().parents[2]
    exp=Path('E:/CHESHIRE_DATA/experiments/overlapping_fold_layout_20261017')
    output=Path('E:/CHESHIRE_DATA/exports/20261017/COLUMN_OVERLAPPING_FOLD_LAYOUT')
    review=output/'INITIAL_REVIEW'
    qa_path=output/'models_verified/OVERLAP_EXPORT_AND_QA.json';qa=read(qa_path)
    if not qa['passed'] or qa['completed_count']!=4:raise ValueError('Incomplete verified pipeline.')
    fields=Path('C:/Users/USER/CHESHIRE/scratch/TWO_MANDEL_INITIAL_COLORED_20261017')
    receipt=read(fields/'TRANSPARENT_RENDER/RENDER_RECEIPT.json')
    item=receipt['items'][0];source=Path(item['geometry']);picture=item['images'][0]
    if sha(source)!=item['source_sha256'] or sha(Path(picture['path']))!=picture['sha256']:
        raise ValueError('Colored actual source binding differs.')
    transparent=review/'TWO_MANDEL_SOURCE_FIELDS_TRANSPARENT.png'
    if transparent.exists():raise FileExistsError(transparent)
    shutil.copyfile(picture['path'],transparent)
    shutil.copyfile(fields/'TRANSPARENT_RENDER/RENDER_RECEIPT.json',review/'TRANSPARENT_RENDER_RECEIPT.json')
    for ident in ['K00','K06','K08']:
        old=Path('C:/Users/USER/CHESHIRE/scratch')/('overlap_'+ident+'_smoke_20261017')/'states/G00_INPUT/geometry.npz'
        fresh=exp/'variants'/ident/'states/G00_INPUT/geometry.npz'
        with np.load(old,allow_pickle=False) as a,np.load(fresh,allow_pickle=False) as b:
            if any(not np.array_equal(a[k],b[k]) for k in ['xyz','faces']):raise ValueError('Shown input differs from final replay.')
    sources={}
    for ident in ['K00','K06','K08','K08_M2']:
        contract=read(exp/'variants'/ident/'RECIPE.json')
        for original,binding in contract['source_snapshots'].items():
            p=Path(binding['snapshot'])
            if sha(p)!=binding['sha256']:raise ValueError('Actual executed source changed.')
            name='source/'+Path(original).relative_to(repo).as_posix()
            if name in sources and sources[name][1]!=binding['sha256']:raise ValueError('Conflicting source version.')
            sources[name]=(p,binding['sha256'])
    local=Path(__file__).parent
    for name in ['inspect_overlap_v2.py','preview_two_fields.py','render_initial_fields.py','package_initial_preview.py','complete_initial_delivery.py']:
        p=local/name;sources['source/'+p.relative_to(repo).as_posix()]=(p,sha(p))
    for relative in ['experiments/inherited_strong_layout_20261017/inspect_strong.py',
            'experiments/inherited_rule_variations_20261017/inspect_inherited.py',
            'experiments/early_dynamic_variations_20261016/run_variation_batch.py',
            'experiments/early_dynamic_variations_20261016/render_variations.py']:
        p=repo/relative;sources['source/'+relative]=(p,sha(p))
    archive=review/'OVERLAPPING_FOLD_ALGORITHM.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for name,(p,digest) in sorted(sources.items()):z.write(p,name)
        z.write(local/'overlap_recipes.json','configuration/overlap_recipes.json')
        z.write(qa_path,'records/OVERLAP_EXPORT_AND_QA.json')
        z.write(review/'INITIAL_PREVIEW_RECEIPT.json','records/INITIAL_PREVIEW_RECEIPT.json')
        z.write(fields/'SOURCE_FIELDS_RECEIPT.json','records/SOURCE_FIELDS_RECEIPT.json')
        for ident in ['K00','K06','K08','K08_M2']:
            root=exp/'variants'/ident
            for name in ['RECIPE.json','RECIPE_EARLY.json','RECEIPT.json']:
                z.write(root/name,'records/'+ident+'/'+name)
            for stage in sorted((root/'states').iterdir()):
                if (stage/'generation.json').is_file():z.write(stage/'generation.json','records/'+ident+'/states/'+stage.name+'/generation.json')
        z.writestr('README.txt','Existing SPAN fold constructor with 49-ring matched sampling, six/eight unequal overlapping major-fold events, and optional genuine two-Mandel-field overlap. Original fold/subdivision/Mandel kernels retained; source profiles/positions are recorded. G0 K08_M2 equals K08; the field difference acts at G1/G2. External original seed inputs and finite-field caches are referenced by exact paths/hashes rather than included. Run replay_overlap.py with a single declared recipe, a fresh output directory, and the original source checkout. Prototype validated through G4, not self-intersection/fabrication certified. User-facing images intentionally show G0 and separate two-field source volumes; no selected main-model replacement. Bottom plate remains a future source-fold-position adjustment.')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('Source ZIP failed.')
    page=review/'review.html'
    page.write_text('''<!doctype html><html lang="ko"><meta charset="utf-8"><title>초기 형상</title><style>body{max-width:1500px;margin:32px auto;padding:0 20px;background:#15191d;color:#eeeae2;font:18px/1.6 system-ui,"Malgun Gothic"}img{max-width:100%;display:block;margin:20px auto}a{color:#a9dce8}</style><p>후속 성장 전 G0 입력: 원래 두 주접힘 / 여섯 접힘 / 여덟 접힘. 하단 판이 남아 있는 수정 전 입력입니다.</p><img src="G0_INITIAL_COMPARISON.png" alt="후속 성장 전 초기 형상 세 안"><p>파랑과 주황은 두 실제 만델벌브 생성장을 구분합니다. 반투명으로 겹침 위치를 보여줍니다. 두 G0 기둥을 포개 놓은 이미지는 아닙니다.</p><img src="TWO_MANDEL_SOURCE_FIELDS_TRANSPARENT.png" alt="파랑 주황 두 만델벌브 생성장"><p><a href="TWO_MANDEL_INITIAL_source_masses.png">불투명 보기</a> · <a href="OVERLAPPING_FOLD_ALGORITHM.zip">알고리즘과 레시피</a></p></html>''',encoding='utf8')
    result=dict(status='COMPLETED_INITIAL_VISUAL_REVIEW_AND_VERIFIED_PIPELINE',user_adopted=False,main_model_replaced=False,
        source_algorithm_archive=dict(path=str(archive),sha256=sha(archive)),
        gallery=str(page),initial_comparison=str(review/'G0_INITIAL_COMPARISON.png'),
        two_field_colored_preview=str(transparent),shown_G0_matches_final_replay=True,
        verified_native_models=4,QA=dict(path=str(qa_path),sha256=sha(qa_path)),
        bottom_plate_retained=True,M2_status='TECHNICAL_COMPARISON_ONLY',self_intersection_or_manufacturing_certified=False)
    (exp/'RUN_RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    (review/'DELIVERY.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(page)


if __name__=='__main__':main()
