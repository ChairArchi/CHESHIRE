"""Color actual G4 by declared early design zones and actual branch ancestry."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
from scipy.interpolate import PchipInterpolator


PALETTE=[dict(name='끝단 / 완만한 연결',rgb=[.31,.34,.38]),
    dict(name='길게 이어지는 큰 접힘',rgb=[.035,.43,.77]),
    dict(name='큰 상부 벌림과 귀환',rgb=[.90,.34,.055]),
    dict(name='하부 중간 크기 군집',rgb=[.60,.15,.48]),
    dict(name='중앙 작은 군집',rgb=[.015,.61,.47]),
    dict(name='실제 생성된 가지',rgb=[.79,.65,.12])]


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()


def bump(t,c,w):return np.maximum(0,1-((t-c)/w)**2)**3


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--ids',nargs='+',required=True)
    p.add_argument('--name',default='DESIGN_COLOR_RENDER_PLAN')
    a=p.parse_args()
    out=a.root/'design_region_colors';out.mkdir(exist_ok=True)
    items=[]
    for ident in a.ids:
        root=a.root/'variants'/ident
        receipt=json.loads((root/'RECEIPT.json').read_text(encoding='utf8'))
        if receipt['status']!='PASS':raise ValueError('Only completed actual G4 may be colored.')
        r=json.loads((root/'RECIPE.json').read_text(encoding='utf8'))['recipe']
        stage=root/'states/G04_NEUTRAL'
        with np.load(stage/'control_quad.npz',allow_pickle=False) as d:
            q=d['faces'];t=d['chart'][q,0].mean(1)
        with np.load(stage/'evidence.npz',allow_pickle=False) as d:roles=d['face_roles']
        cfg=r.get('bundled_fields',{})
        weights=np.zeros((len(q),4))
        if cfg:
            env=PchipInterpolator(cfg.get('envelope_knots',[0.,.06,.18,.38,.55,.73,.88,.96,1.]),
                cfg.get('envelope_values',[0.,.18,.86,1.,.85,1.,.72,.12,0.]))(t)
            weights[:,0]=cfg.get('strength',.38)*env
            weights[:,1]=cfg.get('crown_strength',.38)*bump(t,cfg.get('crown_centre',.75),cfg.get('crown_width',.17))
            weights[:,2]=cfg.get('lower_strength',.22)*bump(t,cfg.get('lower_centre',.23),cfg.get('lower_width',.17))
            weights[:,3]=cfg.get('middle_strength',0.)*bump(t,cfg.get('middle_centre',.47),cfg.get('middle_width',.06))
        else:
            # Fresh D carriers explicitly vary their coarse radial profile.
            # These are named design zones, never a measured displacement map.
            weights[:,0]=.35*bump(t,.48,.43)
            weights[:,1]=.55*bump(t,.76,.22)
            weights[:,2]=.38*bump(t,.20,.18)
        tags=weights.argmax(1).astype(np.int32)+1
        tags[(weights.max(1)<.025)|(t<=.04)|(t>=.96)]=0
        tags[roles!=0]=5
        native=np.repeat(tags,4)
        f=out/(ident+'_G4_design_tags.npy')
        if f.exists():raise FileExistsError('Preserve design colors.')
        np.save(f,native)
        meaning='Declared early design zones evaluated from this candidate\'s inherited material height on actual G4 faces, plus actual generated G3 branch roles. This is a design-region map, not measured deformation magnitude, curvature classification or the complete difference from the old model.'
        m=dict(id=ident,palette=PALETTE,meaning=meaning,recipe_sha256=sha(root/'RECIPE.json'),
            actual_controls_sha256=sha(stage/'control_quad.npz'),actual_evidence_sha256=sha(stage/'evidence.npz'),
            tags_sha256=sha(f),native_triangle_counts=np.bincount(native,minlength=6).tolist())
        (out/(ident+'_COLOR_RECEIPT.json')).write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8')
        items.append(dict(id=ident,geometry=str(stage/'geometry.npz'),controls=str(stage/'control_quad.npz'),
            views=[],color=True,face_colors=str(f),palette=PALETTE,color_name='design_regions',color_meaning=meaning))
    dest=a.root/(a.name+'.json')
    if dest.exists():raise FileExistsError('Preserve renderer plan.')
    dest.write_text(json.dumps(dict(common_scale=18.,items=items),ensure_ascii=False,indent=2),encoding='utf8')
    print(dest,len(items),flush=True)


if __name__=='__main__':main()
