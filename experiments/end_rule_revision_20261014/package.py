"""Preserve completed source-rule evidence without changing executed sources."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ROOT = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01')
DOC = REPO/'docs/end_rule_revision_20261014'

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(8*1024**2), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    receipt = json.loads((ROOT/'RECEIPT.json').read_text(encoding='utf8'))
    executed = receipt['geometry_code_sha256'].copy()
    executed['experiments/end_rule_revision_20261014/render.py'] = '58b8dff2f1ef9b91a438d97b5d7174dca3048e3f6e9af44e56b2bfdadf0c1ce8'
    executed['experiments/end_rule_revision_20261014/boards.py'] = '899443800b890ef3ea84a04b1ded081d978ccc8c9349038b7aad60a50cde445e'
    for relative, expected in executed.items():
        if digest(REPO/relative) != expected:
            raise ValueError('Executed source differs: '+relative)
    selected = ('RECEIPT.json', 'RUN_REQUEST.json', 'SOURCE_BINDING.json',
                'RENDER_VERIFICATION.json', 'images/SOURCE_LIST.json',
                'images/SPAN_front.png', 'images/SPAN_macro.png')
    files = []
    for relative in selected:
        source, target = ROOT/relative, DOC/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and digest(target) != digest(source):
            raise ValueError('Preserved evidence differs: '+relative)
        if not target.exists():
            shutil.copyfile(source, target)
        files.append(dict(source=str(source), preserved=str(target), sha256=digest(source)))
    review = dict(date='2026-10-14', timezone='Asia/Seoul',
        decision='PRESERVED_MIXED_ENDPOINT_STUDY_ORIGINAL_DESIGN_BASELINE_RETAINED',
        user_pattern_choice='Small repeated diagonal comb/scale facets confirmed.',
        next_study_input='REVISED saved native body for the explicitly selected fine pattern; not adoption of all revised ends.',
        geometry_outcome='Round return elongated and narrowed; blunt upper cap, transverse collar and crossing sheets remain.',
        shading_outcome='Normal interpolation alone removes much triangular faceting; no geometric improvement claimed for that effect.',
        source_unchanged=receipt['source_hashes_after'], executed_source_sha256=executed,
        evidence=files, assessment=str(DOC/'ASSESSMENT.txt'))
    text = json.dumps(review, ensure_ascii=False, indent=2)+'\n'
    for target in (DOC/'CHECKPOINT.json', ROOT/'CHECKPOINT.json'):
        if target.exists() and target.read_text(encoding='utf8') != text:
            raise ValueError('Existing checkpoint differs.')
        target.write_text(text, encoding='utf8')
    print(json.dumps(dict(packaged=len(files), executed_source_bytes_verified=True)))

if __name__ == '__main__':
    main()
