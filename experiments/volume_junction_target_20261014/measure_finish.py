"""Measure actual remesh protrusion change near the original marked controls."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import numpy as np
from scipy.spatial import cKDTree


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):
            result.update(block)
    return result.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    root=parser.parse_args().root.resolve()
    folder=root/'volume_finish_clean'
    path=folder/'PROTRUSION_REVIEW.json'
    if path.exists(): raise FileExistsError('Earlier measurements preserved.')
    info=json.loads((folder/'FINISH_RECEIPT.json').read_text(encoding='utf-8'))
    if digest(folder/'geometry.npz') != info['geometry_sha256']: raise ValueError('Finish changed.')
    with np.load(info['source_control'],allow_pickle=False) as data: source=data['xyz']
    with np.load(root/'selection.npz',allow_pickle=False) as data: mask=data['full_mask']>0.
    with np.load(folder/'geometry.npz',allow_pickle=False) as data: actual=data['xyz']
    selected=source[mask]
    tree=cKDTree(actual)
    distance,index=tree.query(selected,workers=-1)
    matched=actual[index].astype(float)
    old_r,new_r=np.linalg.norm(selected[:,:2],axis=1),np.linalg.norm(matched[:,:2],axis=1)
    result=dict(date='2026-10-14',geometry_sha256=info['geometry_sha256'],
        original_control_sha256=info['input_hashes']['source_control_sha256'],
        source_selected_controls=len(selected),
        source_selected_radius_maximum=float(old_r.max()),
        matched_finish_radius_maximum=float(new_r.max()),
        selected_radius_peak_change=float(new_r.max()-old_r.max()),
        source_radius_quantiles=np.quantile(old_r,[0,.5,.9,.99,1]).tolist(),
        matched_finish_radius_quantiles=np.quantile(new_r,[0,.5,.9,.99,1]).tolist(),
        source_to_finish_nearest_vertex_distance_quantiles=np.quantile(distance,[0,.5,.9,.99,1]).tolist(),
        original_bbox_minimum=source.min(axis=0).tolist(), original_bbox_maximum=source.max(axis=0).tolist(),
        finish_bbox_minimum=actual.min(axis=0).tolist(), finish_bbox_maximum=actual.max(axis=0).tolist(),
        actual_symmetry_scope='See VERIFICATION.json: every saved vertex tested.',
        code_sha256=digest(__file__),
        scope='All original marked controls matched to the closest actual finish VERTEX. This is geometric proximity and radial-envelope evidence, not preserved chart/feature-ID ancestry, exact surface distance, exact volume or aesthetic success. Removed internal layers can have large nearest-point distances.')
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    shutil.copyfile(__file__,folder/'source_snapshot'/Path(__file__).name)
    print('PROTRUSION_MEASURED',result['source_selected_radius_maximum'],result['matched_finish_radius_maximum'],flush=True)


if __name__=='__main__': main()
