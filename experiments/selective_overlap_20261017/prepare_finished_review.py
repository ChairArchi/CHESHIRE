"""Plan a full actual native G5 final review after independent export QA."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np

EXP = Path('E:/CHESHIRE_DATA/experiments/selective_overlap_20261017')
EXPORT = Path('E:/CHESHIRE_DATA/exports/20261017/COLUMN_SELECTIVE_OVERLAP_FINISHED')


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(b)
    return h.hexdigest()


def main(finish):
    qa = json.loads((EXPORT / 'models/SELECTIVE_FINAL_EXPORT_AND_QA.json').read_text(encoding='utf8'))
    if qa.get('status') != 'PASS':
        raise ValueError('Actual final export QA required.')
    model = next((EXPORT / 'models').glob('*.ply'))
    receipt = json.loads((finish / 'RECEIPT.json').read_text(encoding='utf8'))
    item = dict(id='L08_FINISHED', geometry=str(model), views=['whole', 'oblique', 'crown'],
                custom_views=dict(detail=dict(target=[0, 0, 6.8], scale=4.0, direction=[.60, -1, .12])))
    item['views'].append('detail')
    records = receipt.get('arrays', {})
    label = records.get('QUAD_EFFECT_CLASSES') or records.get('FACE_EFFECT_CLASSES')
    if label:
        path = Path(label['path'])
        if sha(path) != label['sha256']:
            raise ValueError('Actual final effect classes changed.')
        tags = np.load(path, mmap_mode='r', allow_pickle=False)
        if len(tags) != 3312640:
            raise ValueError('Actual G5 quad class count differs.')
        colors = EXP / 'FINISHED_NATIVE_EFFECT_CLASSES.npy'
        if colors.exists():
            raise FileExistsError(colors)
        np.save(colors, np.repeat(tags.astype(np.int32), 4))
        item.update(color=True, face_colors=str(colors), color_name='effects',
            palette=[dict(name='기존 형상', rgb=[.91, .43, .08]),
                     dict(name='만델벌브 요철', rgb=[.035, .48, .85]),
                     dict(name='티슈 우세', rgb=[.06, .61, .40]),
                     dict(name='목과 말단 보호', rgb=[.42, .48, .52])],
            color_meaning='Measured dominant final relief effect on each actual quad; classes are repeated to that quad\'s four full native triangles. Orange base, blue Mandel, green Tissue, gray protected waist/caps. These are decoration effects, not ownership of separate initial masses.')
    plan = EXP / 'FINISHED_REVIEW_PLAN.json'
    if plan.exists():
        raise FileExistsError(plan)
    plan.write_text(json.dumps(dict(common_scale=11.2, items=[item], actual_model_sha256=sha(model),
                                   final_receipt_sha256=sha(finish / 'RECEIPT.json')), ensure_ascii=False, indent=2), encoding='utf8')
    print(plan)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--finish', type=Path, required=True)
    a = p.parse_args()
    main(a.finish)
