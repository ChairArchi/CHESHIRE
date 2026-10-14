"""Preserve the single local scale-refinement result and matched evidence."""
from pathlib import Path
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
ROOT=Path('E:/CHESHIRE_DATA/experiments/comb_scale_refinement_20261014/trial01')
DOC=REPO/'docs/comb_scale_refinement_20261014'
FIXED={'measure.py':'0e197a2f437664e5b9db134f0e9c0d7a39398913800653150eac842c48a8bf58',
       'render.py':'8a82a55ed86afbbd923e7252ad2508844c19814bfe54f1f1f7d238d58b7324fb',
       'boards.py':'4ec89ecdfc7ac8162fabf174d94f8abf6b39c3b0ee9eb890e32adf761d33ba1c'}

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(8*1024**2),b''):h.update(block)
    return h.hexdigest()

def main():
    receipt=json.loads((ROOT/'RECEIPT.json').read_text(encoding='utf8'))
    proof=json.loads((ROOT/'RENDER_VERIFICATION.json').read_text(encoding='utf8'))
    if proof['passed'] is not True:raise ValueError('Matched render verification failed.')
    fixed=FIXED.copy();fixed['run.py']=receipt['geometry_code_sha256']['experiments/comb_scale_refinement_20261014/run.py']
    for name,checksum in fixed.items():
        if digest(HERE/name)!=checksum:raise ValueError('Executed source differs: '+name)
    selected=('RECEIPT.json','MEASUREMENT.json','RENDER_VERIFICATION.json',
        'images/SOURCE_LIST.json','images/SPAN_macro.png','images/SPAN_close_oblique.png','images/SPAN_front.png')
    evidence=[]
    for relative in selected:
        source,target=ROOT/relative,DOC/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and digest(target)!=digest(source):raise ValueError('Existing evidence differs.')
        if not target.exists():shutil.copyfile(source,target)
        evidence.append(dict(source=str(source),preserved=str(target),sha256=digest(source)))
    review=json.loads((DOC/'VISUAL_REVIEW.json').read_text(encoding='utf8'))
    record=dict(date='2026-10-14',timezone='Asia/Seoul',decision=review['decision'],
        user_choice='Retain clear broad comb relief. Reduce only oversized scales; preserve the accepted small scales.',
        one_local_refinement_candidate=True,source_growth_generation=7,added_G8=False,
        accepted_source='comb_relief_20261014/trial01/RELIEF remains read-only; previous checkpoints and original controls unchanged.',
        recipe=receipt.get('recipe'),statistics=receipt.get('statistics'),
        validation=receipt['variants']['REFINED'].get('validation'),
        visual_review=review,executed_source_sha256=fixed,evidence=evidence,
        Mandelbulb='No deferred Mandelbulb/flower experiment performed.')
    encoded=json.dumps(record,ensure_ascii=False,indent=2)+'\n'
    for target in (DOC/'CHECKPOINT.json',ROOT/'CHECKPOINT.json'):
        if target.exists() and target.read_text(encoding='utf8')!=encoded:raise ValueError('Existing checkpoint differs.')
        target.write_text(encoded,encoding='utf8')
    print(json.dumps(dict(evidence_files=len(evidence),executed_source_bytes_verified=True,decision=review['decision'])))

if __name__=='__main__':main()
