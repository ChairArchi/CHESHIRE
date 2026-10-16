"""Native G0/G4 views of actual source-fold layouts, with measured G0 differences."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
PALETTE=[dict(name='변화 없음 / 매우 작음',rgb=[.32,.35,.39]),
    dict(name='작은 변화',rgb=[.035,.39,.74]),dict(name='중간 변화',rgb=[.025,.65,.51]),
    dict(name='큰 변화',rgb=[.94,.43,.065]),dict(name='매우 큰 변화',rgb=[.71,.12,.25])]


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--ids',nargs='+',default=['J00','J01','J02','J03']);a=p.parse_args()
    base=a.root/'variants/J00/states/G00_INPUT/control_quad.npz'
    with np.load(base,allow_pickle=False) as d:bx,bq,bc=d['xyz'],d['faces'],d['chart']
    with np.load(a.root/'variants/J00/states/G04_NEUTRAL/geometry.npz',allow_pickle=False) as d:
        ref=d['xyz']
    lo,hi=ref.min(0),ref.max(0);height=float(hi[2]-lo[2])
    upper=dict(target=[0,0,float(lo[2]+.80*height)],scale=max(float(np.ptp(ref[:,0]))*1.30,height*.4),direction=[.54,-1,.16])
    whole=dict(target=[0,0,float((lo[2]+hi[2])/2)],scale=11.2,direction=[.17,-1,.06])
    colors=a.root/'actual_G0_change_colors';colors.mkdir(exist_ok=False)
    items=[];proof=[]
    for ident in a.ids:
        folder=a.root/'variants'/ident
        if read(folder/'RECEIPT.json')['status']!='PASS':raise ValueError('Incomplete candidate.')
        g4=folder/'states/G04_NEUTRAL';g0=folder/'states/G00_INPUT'
        items.append(dict(id=ident,geometry=str(g4/'geometry.npz'),controls=str(g4/'control_quad.npz'),
            views=['layout_whole','upper_same'],custom_views=dict(layout_whole=whole,upper_same=upper)))
        items.append(dict(id=ident+'_G0',geometry=str(g0/'geometry.npz'),controls=str(g0/'control_quad.npz'),
            views=['layout_whole'],custom_views=dict(layout_whole=whole)))
        if ident=='J00':continue
        source=g0/'control_quad.npz'
        with np.load(source,allow_pickle=False) as d:x,q,c=d['xyz'],d['faces'],d['chart']
        if not np.array_equal(q,bq) or not np.array_equal(c,bc):raise ValueError('Different material-point identities.')
        delta=np.linalg.norm(x-bx,axis=1);face_delta=delta[q].mean(1)
        tags=np.repeat(np.digitize(face_delta,[.01,.05,.15,.35]).astype(np.int32),4)
        tag_path=colors/(ident+'_G0_native_change.npy');np.save(tag_path,tags)
        meaning='Mean coordinate distance of the four matching G0 control vertices from the original J00 input. These are actual source-fold differences, not final density or curvature. Same thresholds .01/.05/.15/.35 in all cases.'
        items[-1].update(color=True,face_colors=str(tag_path),palette=PALETTE,color_name='actual_change',color_meaning=meaning)
        proof.append(dict(id=ident,source_sha256=sha(source),baseline_sha256=sha(base),tags_sha256=sha(tag_path),
            delta_quantiles=np.quantile(delta,[0,.5,.9,.99,1]).tolist(),changed_controls=int(np.count_nonzero(delta>1e-10)),
            thresholds=[.01,.05,.15,.35],meaning=meaning))
    plan=a.root/'COMPARISON_RENDER_PLAN.json'
    if plan.exists():raise FileExistsError(plan)
    plan.write_text(json.dumps(dict(common_scale=11.2,items=items),ensure_ascii=False,indent=2),encoding='utf8')
    (colors/'COLOR_PROOF.json').write_text(json.dumps(dict(palette=PALETTE,variants=proof),ensure_ascii=False,indent=2),encoding='utf8')
    print(plan,len(items))


if __name__=='__main__':main()
