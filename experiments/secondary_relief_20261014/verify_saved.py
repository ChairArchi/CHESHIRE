"""Independent saved source-plus-delta and unchanged-topology check."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import numpy as np


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for b in iter(lambda:stream.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    root=p.parse_args().root.resolve();record=json.loads((root/'RECEIPT.json').read_text(encoding='utf-8'))
    dest=root/'SAVED_VERIFICATION.json'
    if dest.exists():raise FileExistsError('Earlier proof preserved.')
    source=Path(record['source'])
    if digest(source/'geometry.npz')!=record['source_geometry_sha256'] or digest(root/'geometry.npz')!=record['geometry_sha256'] or digest(root/'displacement.npz')!=record['displacement_file_sha256']:raise ValueError('Actual source/output/evidence changed.')
    with np.load(source/'geometry.npz',allow_pickle=False) as a,np.load(root/'geometry.npz',allow_pickle=False) as b:
        x,y=a['xyz'],b['xyz'];topology=bool(np.array_equal(a['faces'],b['faces']))
    with np.load(root/'displacement.npz',allow_pickle=False) as data:d,core=data['displacement'],data['limiter_core']
    exact=True;peak=0.;zero_exact=True;changed=0
    for start in range(0,len(x),262144):
        stop=min(start+262144,len(x));s=x[start:stop].astype(float);v=d[start:stop];out=y[start:stop]
        exact &= bool(np.array_equal(s+v,out));peak=max(peak,float(np.linalg.norm(v,axis=1).max()));changed+=int(np.any(s!=out,axis=1).sum())
        c=core[start:stop];zero_exact &= bool(np.array_equal(s[c],out[c]))
    passed=exact and zero_exact and topology and peak<=record['amplitude_bound']*(1+1e-12)
    result=dict(passed=bool(passed),all_saved_source_plus_delta_exact=exact,triangle_array_unchanged=topology,limiter_core_original_positions_exact=zero_exact,
        actual_changed_vertices=changed,maximum_saved_delta=peak,geometry_sha256=record['geometry_sha256'],source_geometry_sha256=record['source_geometry_sha256'],
        code_sha256=digest(__file__),scope='Every saved vertex and full triangle array compared. Geometry-local area/orientation/symmetry and inherited graph checks are in RECEIPT.json; no independent normal-field replay, self-intersection or aesthetic certification.')
    dest.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    shutil.copyfile(__file__,root/'source_snapshot'/'verify_saved.py')
    if not passed:raise ValueError('Actual saved preservation failed.')
    print('SAVED_SOURCE_DELTA_TOPOLOGY_PASS',changed,peak,flush=True)


if __name__=='__main__':main()
