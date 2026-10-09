"""A retained geometric rejection must survive an attempted resume."""
import json
import shutil
from pathlib import Path
import numpy as np
import pytest
from cheshire.reference_subdivision import cube,ArrayMesh
from cheshire.task32_patches import simple_projected_ring


def test_projected_boundary_admission_detects_crossing_and_touching():
    assert simple_projected_ring(np.array([[0,0],[2,0],[2,2],[0,2]],float))
    assert not simple_projected_ring(np.array([[0,0],[2,2],[2,0],[0,2]],float))
    assert not simple_projected_ring(np.array([[0,0],[2,0],[1,0],[1,2],[0,2]],float))


def test_geometry_rejection_is_preserved_and_cannot_be_bypassed_by_resume(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'tools'))
    import task32_research as runner
    base=cube()
    # Two individually closed cubes with a real transverse intersection.
    m=ArrayMesh(np.concatenate([base.xyz,base.xyz+[400,150,100]]),
        np.concatenate([base.faces,base.faces+len(base.xyz)]),np.tile(base.classes,2),
        np.concatenate([base.rest,base.rest+[400,150,100]]),np.tile(base.anchors,(2,1)),0)
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'basic_gate',lambda:m)
    definition=tmp_path/'definition.json'
    definition.write_text(json.dumps(dict(id='REJECT',steps=[dict(kind='audit'),dict(kind='cc',row={})])),encoding='utf-8')
    with pytest.raises(ValueError,match='Transverse crossings'):runner.run(definition)
    retained=tmp_path/'candidates/REJECT/S01'
    before={p.name:p.read_bytes() for p in retained.iterdir()}
    with pytest.raises(ValueError,match='resumption cannot bypass'):runner.run(definition)
    assert before=={p.name:p.read_bytes() for p in retained.iterdir()}
    assert not (tmp_path/'candidates/REJECT/S02').exists()
    assert not (tmp_path/'candidates/REJECT/completed.json').exists()


def test_resume_after_topology_edit_restores_scopes_and_ends_old_coordinate_lineage(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'tools'))
    import task32_research as runner
    import cheshire.task32_patches as patches
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'basic_gate',cube)
    # Use a known disk on the test cube; execute real spectrum, surgery and CC.
    monkeypatch.setattr(patches,'choose_front_disks',lambda mesh,spec:([np.array([0])],[]))
    steps=[dict(kind='cc',row={}),dict(kind='spectral',spec=dict(modes=[2,4],amplitude=1)),
           dict(kind='patches',spec=dict(heights=[.2,.4,.6],scales=[1,1,1])),dict(kind='cc',row={})]
    definition=tmp_path/'original.json';runner.write_new(definition,dict(id='ORIGINAL',steps=steps))
    runner.run(definition)
    resumed_definition=tmp_path/'resumed.json';d=dict(id='RESUMED',steps=steps);runner.write_new(resumed_definition,d)
    dest=tmp_path/'candidates/RESUMED'
    runner.write_new(dest/'request.json',dict(definition=d,definition_sha256=runner.sha(resumed_definition),sources=runner.source_identity()))
    for i in range(4):shutil.copytree(tmp_path/f'candidates/ORIGINAL/S{i:02}',dest/f'S{i:02}')
    assert not (dest/'S03/spectral_state.npz').exists()
    runner.run(resumed_definition)
    for file in ['mesh.npz','branch_state.npz','operator_state.npz']:
        with np.load(tmp_path/'candidates/ORIGINAL/S04'/file) as a,np.load(dest/'S04'/file) as b:
            assert set(a.files)==set(b.files)
            for key in a.files:np.testing.assert_array_equal(a[key],b[key])
