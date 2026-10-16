"""Actual G0 comparisons and source-delta/waist-reference colors."""
from pathlib import Path
import hashlib
import json
import numpy as np


def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    root=Path('E:/CHESHIRE_DATA/experiments/selective_overlap_20261017')
    source=root/'source_candidates_v1'
    colors=root/'actual_source_colors_v1';colors.mkdir(exist_ok=False)
    items=[];proof=[]
    for ident in ['K00','K08']:
        parent=Path('E:/CHESHIRE_DATA/experiments/overlapping_fold_layout_20261017/variants')/ident/'states/G00_INPUT'
        items.append(dict(id=ident,geometry=str(parent/'geometry.npz'),controls=str(parent/'control_quad.npz'),views=['whole']))
    palette=[dict(name='기본 형상',rgb=[.91,.43,.08]),dict(name='보조 접힘이 작용한 곳',rgb=[.035,.48,.85]),dict(name='목의 기준 영역',rgb=[.41,.47,.51])]
    for ident in ['S06_LOBES','S08_LOBES','S08_PHASE']:
        parent=source/ident;receipt=read(parent/'generation.json')
        for filename,binding in receipt['actual_files'].items():
            if sha(parent/filename)!=binding['sha256']:raise ValueError('Saved source changed.')
        with np.load(parent/'control_quad.npz',allow_pickle=False) as d:q=d['faces']
        with np.load(parent/'operation_fields.npz',allow_pickle=False) as d:
            delta=np.linalg.norm(d['secondary_delta'],axis=1)
            guard=d['guard_vertex_mask']
        tags=(delta[q].mean(1)>.015).astype(np.int32)
        tags[guard[q].mean(1)>=.5]=2
        tags=np.repeat(tags,4)
        tagpath=colors/(ident+'_native_source_classes.npy');np.save(tagpath,tags)
        meaning='Orange: base input including original primary folds. Blue: mean matching-control displacement from primary-only input exceeds .015 model units. Gray: declared measured waist-reference material intervals, not a claim of bit-exact preservation. Actual quad labels are repeated to that quad\'s four native fan triangles.'
        items.append(dict(id=ident,geometry=str(parent/'geometry.npz'),controls=str(parent/'control_quad.npz'),views=['whole','oblique'],
            color=True,face_colors=str(tagpath),palette=palette,color_name='source_roles',color_meaning=meaning))
        proof.append(dict(id=ident,source_sha256=sha(parent/'geometry.npz'),operation_sha256=sha(parent/'operation_fields.npz'),
            tags_sha256=sha(tagpath),meaning=meaning,actual_tag_counts=np.bincount(tags,minlength=3).tolist()))
    plan=root/'G0_REVIEW_PLAN_v1.json'
    if plan.exists():raise FileExistsError(plan)
    plan.write_text(json.dumps(dict(common_scale=11.2,items=items),ensure_ascii=False,indent=2),encoding='utf8')
    (colors/'COLOR_PROOF.json').write_text(json.dumps(dict(palette=palette,variants=proof),ensure_ascii=False,indent=2),encoding='utf8')
    print(plan)


if __name__=='__main__':main()
