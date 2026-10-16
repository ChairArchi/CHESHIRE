"""Same-stage comparisons and measured G2 coordinate-difference colors."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()


def read(p):return json.loads(Path(p).read_text(encoding='utf8'))


PALETTE=[dict(name='변화 없음 / 매우 작음',rgb=[.32,.35,.39]),
    dict(name='작은 변화',rgb=[.035,.39,.74]),
    dict(name='중간 변화',rgb=[.025,.65,.51]),
    dict(name='큰 변화',rgb=[.94,.43,.065]),
    dict(name='매우 큰 변화',rgb=[.71,.12,.25])]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--name',default='COMPARISON_RENDER_PLAN')
    p.add_argument('--ids',nargs='*')
    a=p.parse_args()
    folders=[f for f in sorted((a.root/'variants').iterdir()) if (f/'RECEIPT.json').exists()]
    base=a.root/'variants/I00/states/G02_OVERLAP/control_quad.npz'
    with np.load(base,allow_pickle=False) as d:bx,bq,bc=d['xyz'],d['faces'],d['chart']
    with np.load(a.root/'variants/I00/states/G04_NEUTRAL/geometry.npz',allow_pickle=False) as d:
        reference_xyz=d['xyz']
    low,high=reference_xyz.min(0),reference_xyz.max(0)
    height=float(high[2]-low[2])
    upper_view=dict(target=[0,0,float(low[2]+.80*height)],
        scale=max(float(np.ptp(reference_xyz[:,0]))*1.30,height*.40),
        direction=[.54,-1,.16])
    colors=a.root/'actual_G2_change_colors';colors.mkdir(exist_ok=True)
    items=[];rows=[]
    for f in folders:
        ident=f.name
        if a.ids and ident not in a.ids:continue
        r=read(f/'RECEIPT.json')
        if r['status']!='PASS':raise ValueError('Incomplete producer cannot be reviewed.')
        g4=f/'states/G04_NEUTRAL'
        items.append(dict(id=ident,geometry=str(g4/'geometry.npz'),controls=str(g4/'control_quad.npz'),
            views=['whole','upper_same'],custom_views={'upper_same':upper_view}))
        if ident=='I00':continue
        g2=f/'states/G02_OVERLAP'
        with np.load(g2/'control_quad.npz',allow_pickle=False) as d:
            x,q,c=d['xyz'],d['faces'],d['chart']
        if not np.array_equal(q,bq) or not np.array_equal(c,bc):
            raise ValueError('G2 colors require exact same topology/material-point identities.')
        magnitude=np.linalg.norm(x-bx,axis=1)
        face_mean=magnitude[q].mean(1)
        # Same physical thresholds for all candidates; no per-image rescaling.
        tags=np.repeat(np.digitize(face_mean,[.01,.05,.15,.35]).astype(np.int32),4)
        path=colors/(ident+'_G2_native_change.npy')
        if path.exists():raise FileExistsError('Preserve actual difference colors.')
        np.save(path,tags)
        meaning='Mean Euclidean coordinate difference of the four matching G2 control vertices from I00, inherited only to that quad\'s four actual native fan triangles. Same physical thresholds .01/.05/.15/.35 for every candidate. This measures actual G2 differences, not G4 change, final density or curvature.'
        items.append(dict(id=ident+'_G2',geometry=str(g2/'geometry.npz'),controls=str(g2/'control_quad.npz'),
            views=[],color=True,face_colors=str(path),palette=PALETTE,color_name='actual_change',color_meaning=meaning))
        rows.append(dict(id=ident,source_control_sha256=sha(g2/'control_quad.npz'),baseline_control_sha256=sha(base),
            tags_sha256=sha(path),meaning=meaning,thresholds=[.01,.05,.15,.35],
            actual_control_difference_quantiles=np.quantile(magnitude,[0,.5,.9,.99,1]).tolist(),
            native_color_counts=np.bincount(tags,minlength=5).tolist()))
    dest=a.root/(a.name+'.json')
    if dest.exists():raise FileExistsError('Preserve comparison plan.')
    dest.write_text(json.dumps(dict(common_scale=11.2,items=items),ensure_ascii=False,indent=2),encoding='utf8')
    (colors/'COLOR_PROOF.json').write_text(json.dumps(dict(palette=PALETTE,variants=rows),ensure_ascii=False,indent=2),encoding='utf8')
    print(dest,len(items),flush=True)


if __name__=='__main__':main()
