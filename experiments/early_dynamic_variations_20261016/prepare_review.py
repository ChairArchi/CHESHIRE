"""Prepare comparable native mesh cameras and honest coarse deformation colors."""
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


def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')


PALETTE=[dict(name='작은 변형 / 흐름 유지',rgb=[.30,.32,.35]),
    dict(name='바깥으로 벌어짐',rgb=[.90,.34,.055]),
    dict(name='안으로 수축',rgb=[.035,.42,.78]),
    dict(name='축 방향 접힘 / 되접힘',rgb=[.64,.12,.43]),
    dict(name='둘레 방향 뒤틀림',rgb=[.015,.62,.48]),
    dict(name='복합 변형',rgb=[.80,.66,.12])]


def deformation_colors(root,folder,ident):
    g3=folder/'states/G03_SIDEWALL'
    g4=folder/'states/G04_NEUTRAL'
    with np.load(g3/'control_quad.npz',allow_pickle=False) as d:
        x=d['xyz'];q=d['faces']
    with np.load(g3/'evidence.npz',allow_pickle=False) as d:
        delta=d['macro_actual_displacement'] if 'macro_actual_displacement' in d.files else np.zeros_like(x)
    before=x-delta
    R=float(np.median(np.linalg.norm(before[:,:2],axis=1)))
    p=before[q].mean(1);v=delta[q].mean(1)
    radial=p[:,:2]/np.maximum(np.linalg.norm(p[:,:2],axis=1)[:,None],1e-30)
    r=(v[:,:2]*radial).sum(1)
    tangent=(v[:,:2]*np.column_stack([-radial[:,1],radial[:,0]])).sum(1)
    components=np.column_stack([np.abs(r),np.abs(v[:,2]),np.abs(tangent)])
    ordered=np.sort(components,axis=1)
    dominant=components.argmax(1)
    tags=np.zeros(len(q),np.int32)
    moving=np.linalg.norm(v,axis=1)>.025*R
    tags[moving&(dominant==0)&(r>=0)]=1
    tags[moving&(dominant==0)&(r<0)]=2
    tags[moving&(dominant==1)]=3
    tags[moving&(dominant==2)]=4
    tags[moving&(ordered[:,-2]>.82*ordered[:,-1])]=5
    with np.load(g4/'evidence.npz',allow_pickle=False) as d:parent=d['parent_face']
    tags=np.repeat(tags[parent],4)
    out=root/'deformation_colors';out.mkdir(exist_ok=True)
    f=out/(ident+'_G4_native_tags.npy')
    if f.exists():
        if not np.array_equal(np.load(f),tags):raise ValueError('Existing deformation colors changed.')
    else:np.save(f,tags)
    meta=dict(id=ident,meaning='Dominant signed radial, axial, or tangential component of the actual prescribed G3 macro displacement, averaged over actual G3 faces and inherited to actual G4 children. This does not include G0 length changes, G1/G2 growth differences or event-shape differences.',
        palette=PALETTE,source_controls_sha256=sha(g3/'control_quad.npz'),
        source_evidence_sha256=sha(g3/'evidence.npz'),G4_evidence_sha256=sha(g4/'evidence.npz'),
        tags_sha256=sha(f),counts=np.bincount(tags,minlength=6).tolist())
    write(out/(ident+'_COLOR_RECEIPT.json'),meta)
    return f,meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--name',required=True)
    p.add_argument('--ids',nargs='*')
    p.add_argument('--views',nargs='+',default=['whole'])
    p.add_argument('--color-mode',choices=['none','bands','deformation'],default='none')
    a=p.parse_args()
    items=[]
    for folder in sorted((a.root/'variants').iterdir()):
        if a.ids and folder.name not in a.ids:continue
        if not (folder/'RECEIPT.json').exists():continue
        r=read(folder/'RECIPE.json')['recipe'];stage=folder/'states/G04_NEUTRAL'
        item=dict(id=folder.name,label_ko=r.get('label_ko',folder.name),
            geometry=str(stage/'geometry.npz'),controls=str(stage/'control_quad.npz'),
            views=a.views,color=a.color_mode!='none',bands=r.get('macro_fields',{}).get('nodes',4))
        if a.color_mode=='deformation':
            f,m=deformation_colors(a.root,folder,folder.name)
            item.update(face_colors=str(f),palette=PALETTE,color_name='deformation',color_meaning=m['meaning'])
        items.append(item)
    if not items:raise ValueError('No completed actual G4 models to review.')
    plan=dict(common_scale=18.0,items=items,
        whole_view_scope='Same physical orthographic scale for all candidates; close views independently frame crown/body.')
    dest=a.root/(a.name+'.json')
    if dest.exists():raise FileExistsError('Preserve review plan.')
    write(dest,plan)
    print(dest, len(items),flush=True)


if __name__=='__main__':main()
