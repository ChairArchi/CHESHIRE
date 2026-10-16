"""Bind same-sampling native G0 geometry to actual displacement/waist colors."""
from pathlib import Path
import hashlib
import json
import numpy as np


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    root = Path('E:/CHESHIRE_DATA/experiments/selective_overlap_20261017')
    source = root / 'source_candidates_v2'
    colors = root / 'actual_source_colors_v2'
    colors.mkdir(exist_ok=False)
    palette = [dict(name='기존 접힘 구조', rgb=[.91, .43, .08]),
               dict(name='추가 접힘의 영향', rgb=[.035, .48, .85]),
               dict(name='원형의 목 중심', rgb=[.42, .48, .52])]
    items, proofs = [], []
    for ident in ['B193', 'K08_193', 'S08_HIER_193', 'L08_PRIMARY_193']:
        parent = source / ident
        receipt = json.loads((parent / 'generation.json').read_text(encoding='utf8'))
        for filename, binding in receipt['actual_files'].items():
            if sha(parent / filename) != binding['sha256']:
                raise ValueError('Saved source changed: ' + ident)
        item = dict(id=ident, geometry=str(parent / 'geometry.npz'),
                    controls=str(parent / 'control_quad.npz'), views=['whole', 'oblique'])
        if ident == 'L08_PRIMARY_193':
            with np.load(parent / 'control_quad.npz', allow_pickle=False) as d:
                q = d['faces']
            with np.load(parent / 'operation_fields.npz', allow_pickle=False) as d:
                delta = np.linalg.norm(d['actual_added_delta'], axis=1)
                guard = d['waist_guard_vertex_mask']
            tags = (delta[q].mean(1) > .015).astype(np.int32)
            tags[guard[q].mean(1) >= .5] = 2
            tags = np.repeat(tags, 4)
            path = colors / (ident + '_source_classes.npy')
            np.save(path, tags)
            meaning = ('Orange: original complete source. Blue: mean matching-control displacement from '
                       'original source exceeds .015 model units. Gray: measured source waist-core '
                       'material intervals. Actual quad classes repeat to the four native fan triangles. '
                       'These classify fold effects, not ownership of separate Mandelbulb masses.')
            item.update(color=True, face_colors=str(path), palette=palette,
                        color_name='source_roles', color_meaning=meaning)
            proofs.append(dict(id=ident, geometry_sha256=sha(parent / 'geometry.npz'),
                               operation_sha256=sha(parent / 'operation_fields.npz'),
                               color_sha256=sha(path), counts=np.bincount(tags, minlength=3).tolist(),
                               meaning=meaning))
        items.append(item)
    plan = root / 'G0_REVIEW_PLAN_v2.json'
    if plan.exists():
        raise FileExistsError(plan)
    plan.write_text(json.dumps(dict(common_scale=11.2, items=items), ensure_ascii=False, indent=2), encoding='utf8')
    (colors / 'COLOR_PROOF.json').write_text(json.dumps(dict(palette=palette, variants=proofs), ensure_ascii=False, indent=2), encoding='utf8')
    print(plan)


if __name__ == '__main__':
    main()
