"""Same incoming physical geometry, one-step component/boundary controls.

No backtracking differences: every requested displacement is applied at factor1.
Invalid alternatives are labelled and preserved, never exchanged.
"""
import json,sys,shutil
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from cheshire.task36_growth import step,native,quick_integrity
from cheshire.reference_subdivision import ArrayMesh
from task36_research import checkpoint,SOURCES
from task36_contacts import contacts
from task33_preserve import sha,write_new
ROOT=Path('E:/CHESHIRE_DATA/task36')


def main():
    source=ROOT/'candidates/J01_DECOMPOSED/G2_FOLD';z=np.load(source/'quad_state.npz')
    mesh=ArrayMesh(*(z[k].copy() for k in ['xyz','faces','classes','rest','anchors']),int(z['generation']))
    mesh.surface=str(z['surface']) if 'surface' in z else 'mean'  # Historical J01 used mean fans.
    params=json.loads((source.parent/'request.json').read_text())['parameters']
    dest=ROOT/'diagnostics/SAME_INPUT_COMPONENTS';dest.mkdir(parents=True,exist_ok=False)
    identities={}
    for name in SOURCES+['tools/task36_component_probe.py']:
        target=dest/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/name,target);identities[name]=sha(target)
    rows=[]
    variants=[('FULL',{}),('NO_AVERAGING',dict(averaging_gain=0)),('AVERAGING_ONLY',dict(stencil_gain=0,normal_gain=0)),('NO_NORMAL',dict(normal_gain=0)),('NORMAL_ONLY',dict(averaging_gain=0,stencil_gain=0)),('NO_STENCIL',dict(stencil_gain=0)),('FREE_CAP_XY',dict(cap_mode='plane_only')),('NO_ANCESTRY',dict(ancestry_gain=0))]
    baseline=None
    for name,change in variants:
        out,op=step(mesh,**dict(params,**change));stage=dest/name/'G3_FOLD';checkpoint(stage,out,source,op,dict(requested=dict(params,**change),applied_factor=1))
        if baseline is None:baseline=out.xyz.copy()
        value=dict(id=name,stage=str(stage),contacts=contacts(native(out),cap=4096,interval=True,include_shared=True),integrity=quick_integrity(out),extent=np.ptp(out.xyz,axis=0).tolist(),max_difference_from_full=float(abs(out.xyz-baseline).max()),rms_difference_from_full=float(np.sqrt(np.mean((out.xyz-baseline)**2))))
        rows.append(value);print(name,value['extent'],value['contacts']['transverse_contacts'],flush=True)
    write_new(dest/'summary.json',dict(source=str(source),source_native_sha256=sha(source/'mesh.npz'),rows=rows,source_identity=identities,common_applied_factor=1,limitation='One-step incoming G2 comparison, not full multi-generation aesthetics. No adaptive safety adjustment; invalid outputs are diagnostic only.'))


if __name__=='__main__':main()
