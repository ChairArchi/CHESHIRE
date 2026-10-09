"""Independent original-vs-BVH broad-phase regression, including failures."""
import json,sys
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_contacts import contacts as original
from task36_contacts import contacts as accelerated
from task29_search import load_mesh
from task33_preserve import sha,write_new
from cheshire.reference_subdivision import ArrayMesh
ROOT=Path('E:/CHESHIRE_DATA/task36')


def verify():
    rows=[]
    stages=[('D01_VERTEX_CONTRAST',4),('E01_COUPLED',4),('M01_FREE_RECURSIVE_G8',6),('N01_EXACT_SURFACE_G6',6),('S02_ALL_GEOMETRY',5)]
    for name,g in stages:
        stage=ROOT/'candidates'/name/f'G{g}_FOLD';m=load_mesh(stage);a=original(m,cap=4096);b=accelerated(m,cap=4096)
        row=dict(id=name,native_sha256=sha(stage/'mesh.npz'),original=a,accelerated=b,pairs_exact=a['pairs']==b['pairs'])
        if not row['pairs_exact'] or (not a['cap_reached'] and a['checked_nonadjacent_AABB_pairs']!=b['checked_nonadjacent_AABB_pairs']):raise ValueError('Broad-phase equivalence failed.')
        rows.append(row);print(name,'exact',a['transverse_contacts'],flush=True)
    for seed in range(5):
        rng=np.random.default_rng(seed);x=rng.normal(size=(180,3));tri=np.arange(180).reshape(-1,3)
        m=ArrayMesh(x,np.column_stack([tri,np.full(len(tri),-1)]),np.zeros(len(x),np.int8),x.copy(),np.zeros((len(tri),3),np.int64))
        a=original(m,cap=4096);b=accelerated(m,cap=4096)
        if a['pairs']!=b['pairs'] or a['checked_nonadjacent_AABB_pairs']!=b['checked_nonadjacent_AABB_pairs']:raise ValueError('Random intersecting triangle regression failed.')
        rows.append(dict(id='deterministic_random_'+str(seed),original=a,accelerated=b,pairs_exact=True))
    stage=ROOT/'candidates/Q01_LOCAL_SAFETY_G6/G6_FOLD';m=load_mesh(stage);a=json.loads((stage/'growth.json').read_text())['contacts'];b=accelerated(m,cap=4096)
    if a['pairs']!=b['pairs'] or a['checked_nonadjacent_AABB_pairs']!=b['checked_nonadjacent_AABB_pairs']:raise ValueError('Full 163840-triangle original certificate mismatch.')
    rows.append(dict(id='Q01_FULL_G6',native_sha256=sha(stage/'mesh.npz'),original=a,accelerated=b,pairs_exact=True))
    write_new(ROOT/'validation/BVH_EQUIVALENCE.json',dict(rows=rows,all_exact=True,old_predicate_sha256=sha(REPO/'tools/task33_contacts.py'),new_wrapper_sha256=sha(REPO/'tools/task36_contacts.py'),helper_source_sha256=sha(REPO/'tools/native/Task36Bounds.cs'),
       scope='Ascending pair identities and exhausted candidate counts on real successes/failures and deterministic intersecting fixtures. Full dense known-original certificate included. Same imported narrow phase; no new tolerance or exclusions.'))


if __name__=='__main__':verify()
