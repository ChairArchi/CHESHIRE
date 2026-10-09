from pathlib import Path
import numpy as np
from cheshire.reference_subdivision import cube,ArrayMesh,subdivide


def test_streamed_full_contact_pairs_match_original_full_narrow_phase(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'tools'))
    from task32_validation import transverse_contacts
    from task32_full_contacts import full_contacts
    base=cube();base,_,_=subdivide(base,{})
    overlap=ArrayMesh(np.concatenate([base.xyz,base.xyz+[400,150,100]]),
        np.concatenate([base.faces,base.faces+len(base.xyz)]),np.tile(base.classes,2),
        np.tile(base.rest,(2,1)),np.tile(base.anchors,(2,1)),base.generation)
    for mesh in [base,overlap]:
        a=transverse_contacts(mesh,cap=10000);b=full_contacts(mesh,cap=10000)
        assert {tuple(pair) for pair in a['pairs']}=={tuple(pair) for pair in b['pairs']}
        assert a['checked_nonadjacent_AABB_pairs']==b['checked_nonadjacent_AABB_pairs']
    assert full_contacts(overlap)['transverse_contacts']>0
