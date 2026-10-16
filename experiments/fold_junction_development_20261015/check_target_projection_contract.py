"""Small semantic checks for the full-residual target adapter, not aesthetics."""
from pathlib import Path
import importlib.util
import json
import numpy as np

HERE = Path(__file__).resolve().parent

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def check():
    op = module('target_contract_operator', HERE/'target_projected_subdivision.py')
    native = module('target_contract_native', HERE/'run_final.py')
    xyz = np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],
                    [-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]], float)
    q = np.array([[0,3,2,1],[4,5,6,7],[0,1,5,4],
                  [1,2,6,5],[2,3,7,6],[3,0,4,7]], np.int64)
    pair = np.stack((q,np.roll(q,-1,axis=1)),axis=2)
    edges, following = np.unique(np.sort(pair,axis=2).reshape(-1,2),axis=0,return_inverse=True)
    following = following.reshape(-1,4)
    degree = np.bincount(edges.ravel(),minlength=len(xyz))
    q7 = np.stack((len(xyz)+np.roll(following,1,axis=1),q,len(xyz)+following,
                   np.broadcast_to((len(xyz)+len(edges)+np.arange(len(q)))[:,None],q.shape)),axis=2).reshape(-1,4)
    def identity(x,c,s): return np.zeros_like(x)
    neutral = native.neutral_delta(xyz,q,edges,following,degree)
    zero,_,_,_ = op.subdivide(xyz,q,xyz,edges,following,degree,q7,identity)
    if not np.array_equal(zero,neutral): raise AssertionError('Identity target differs from neutral CC')
    height = .731
    def plane(x,c,s):
        residual = np.zeros_like(x)
        residual[:,2] = height-x[:,2]
        return residual
    out,_,_,_ = op.subdivide(xyz,q,xyz,edges,following,degree,q7,plane)
    error = float(np.max(np.abs(out[:,2]-height)))
    idem = float(np.max(np.abs(plane(out,np.zeros_like(out),'CHECK'))))
    if error > 2e-15 or idem > 2e-15: raise AssertionError('Full-residual plane contract failed')
    return dict(identity_target_bit_exact=True,all_class_plane_maximum_error=error,
                plane_idempotence_residual=idem,proves='Target-residual semantics only; not beauty or absence of intersections.')

if __name__ == '__main__':
    print(json.dumps(check(),indent=2))
