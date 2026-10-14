"""Preserve completed same-candidate geometry and shading comparisons."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ROOT = Path('E:/CHESHIRE_DATA/experiments/diagonal_facet_finish_20261014/trial01')
DOC = REPO/'docs/diagonal_facet_finish_20261014'
FIXED = {'measure.py':'40a19abf240bb79cfe6fe4ed328a5fba7cb663ebdf2c5fab794dd4a962b19c02',
    'render.py':'c544eaa4633ac07a0e9ae3fd42cc5bc2b500065be8c232158bccd13409543e73',
    'boards.py':'43f87a1096e3ec6edd3cecf482fdf08c1227ec61bdd95ad5f2455f034ba9851d',
    'render_allflat.py':'56c6d783c9b5ee8ecaaffed3c099ea3496a39f9a7fa915296aa2894b849c5264',
    'boards_allflat.py':'41ba664daaddbd1111205d57f67623ba483e6e0676d7c61002af65829e61c07f'}

def digest(path):
    h = hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(8*1024**2),b''): h.update(block)
    return h.hexdigest()

def main():
    receipt = json.loads((ROOT/'RECEIPT.json').read_text(encoding='utf8'))
    fixed = FIXED.copy()
    fixed['run.py'] = receipt['geometry_code_sha256']['experiments/diagonal_facet_finish_20261014/run.py']
    for name, checksum in fixed.items():
        if digest(HERE/name) != checksum: raise ValueError('Executed source changed: '+name)
    for name in ('RENDER_VERIFICATION.json', 'FLAT_RENDER_VERIFICATION.json'):
        if json.loads((ROOT/name).read_text(encoding='utf8'))['passed'] is not True:
            raise ValueError('Matched comparison failed.')
    selected = ('RECEIPT.json', 'MEASUREMENT.json', 'SOURCE_BINDING.json',
        'RENDER_VERIFICATION.json', 'FLAT_RENDER_VERIFICATION.json',
        'images/SOURCE_LIST.json', 'images/SPAN_macro.png',
        'images_allflat/SOURCE_LIST.json', 'images_allflat/SPAN_macro.png',
        'images_allflat/SPAN_front.png')
    records = []
    for relative in selected:
        source, target = ROOT/relative, DOC/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and digest(target) != digest(source): raise ValueError('Existing evidence differs.')
        if not target.exists(): shutil.copyfile(source,target)
        records.append(dict(source=str(source),preserved=str(target),sha256=digest(source)))
    review = json.loads((DOC/'VISUAL_REVIEW.json').read_text(encoding='utf8'))
    checkpoint = dict(date='2026-10-14', timezone='Asia/Seoul',
        one_geometry_candidate=True, native_finish_only=True, G=7, added_G8=False,
        decision=review['decision'], user_pattern_choice='Small diagonal comb/scale facets; requested more visible coverage.',
        original_design_baseline='WIDE_ROOT_FINISHED/SPAN/G07 unchanged; REVISED used only as selected visual-study source.',
        native_finish=receipt['recipe'], geometry_statistics=receipt['statistics'],
        selective_shading_decision='REJECTED: source-world-direction and quad-aspect selection hides much preferred comb even before geometry accent.',
        allflat_comparison='Same actual ACCENT geometry rendered under the same all-flat camera/material conditions as user reference; no regeneration.',
        deferred_user_suggestion='Flower-like Mandelbulb covering only very small awkward end clusters; explicitly not to experiment now. No Mandelbulb experiment performed.',
        executed_source_sha256=fixed, evidence=records, visual_review=review)
    encoded=json.dumps(checkpoint,ensure_ascii=False,indent=2)+'\n'
    for path in (DOC/'CHECKPOINT.json', ROOT/'CHECKPOINT.json'):
        if path.exists() and path.read_text(encoding='utf8') != encoded: raise ValueError('Checkpoint differs.')
        path.write_text(encoded,encoding='utf8')
    print(json.dumps(dict(preserved_files=len(records),executed_source_bytes_verified=True,decision=review['decision'])))

if __name__ == '__main__': main()
