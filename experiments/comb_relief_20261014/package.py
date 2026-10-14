"""Preserve one completed integral ridge trial and its matched visual evidence."""
from pathlib import Path
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
ROOT=Path('E:/CHESHIRE_DATA/experiments/comb_relief_20261014/trial01')
DOC=REPO/'docs/comb_relief_20261014'
FIXED={'measure.py':'bdf9871881a9170ba3d71e5209405fd8d4d318895a9ef3ed12ffd9105668a825',
       'render.py':'08c503ae0895869090693ca01301394332583cdb6d3d129abc97300629496c13',
       'boards.py':'eb41128068312fa4f4609b373acc190d226dd295a6c0bc294a268e447f7c9c14'}

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(8*1024**2),b''):h.update(block)
    return h.hexdigest()

def main():
    receipt=json.loads((ROOT/'RECEIPT.json').read_text(encoding='utf8'))
    proof=json.loads((ROOT/'RENDER_VERIFICATION.json').read_text(encoding='utf8'))
    if proof['passed'] is not True:raise ValueError('Actual matched rendering verification failed.')
    fixed=FIXED.copy();fixed['run.py']=receipt['geometry_code_sha256']['experiments/comb_relief_20261014/run.py']
    for name,checksum in fixed.items():
        if digest(HERE/name)!=checksum:raise ValueError('Executed source differs: '+name)
    selected=('RECEIPT.json','MEASUREMENT.json','RENDER_VERIFICATION.json',
        'images/SOURCE_LIST.json','images/SPAN_macro.png','images/SPAN_front.png','images/SPAN_close_oblique.png')
    preserved=[]
    for relative in selected:
        source,target=ROOT/relative,DOC/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and digest(target)!=digest(source):raise ValueError('Existing evidence differs.')
        if not target.exists():shutil.copyfile(source,target)
        preserved.append(dict(source=str(source),preserved=str(target),sha256=digest(source)))
    review=json.loads((DOC/'VISUAL_REVIEW.json').read_text(encoding='utf8'))
    record=dict(date='2026-10-14',timezone='Asia/Seoul',decision=review['decision'],
        one_candidate=True,source_growth_generation=7,added_G8=False,
        user_direction='Meaningful visible small diagonal comb/scale detail over the broad existing pattern; original major fold language retained.',
        original_checkpoint='WIDE_ROOT_FINISHED/SPAN/G07 remains read-only and separate. Same REVISED body as user attachment is the reference source for this study.',
        recipe=receipt['recipe'],geometry_statistics=receipt['statistics'],
        geometry_validation=receipt['variants']['RELIEF']['validation'],
        deferred_Mandelbulb='No Mandelbulb or flower-covering experiment performed; user explicitly deferred it.',
        executed_source_sha256=fixed,evidence=preserved,visual_review=review)
    encoded=json.dumps(record,ensure_ascii=False,indent=2)+'\n'
    for target in (DOC/'CHECKPOINT.json',ROOT/'CHECKPOINT.json'):
        if target.exists() and target.read_text(encoding='utf8')!=encoded:raise ValueError('Existing checkpoint differs.')
        target.write_text(encoded,encoding='utf8')
    print(json.dumps(dict(evidence_files=len(preserved),executed_source_bytes_verified=True,decision=review['decision'])))

if __name__=='__main__':main()
