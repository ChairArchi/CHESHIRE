"""Risk introduced by Task24: constructive events before crease subdivision.

Verify that a later selector finds actual descendants, rather than stale event
face IDs, and that export preserves the mixed sequence's real geometry.
"""
from copy import deepcopy
import os
from pathlib import Path
import sys

import pytest
from compas.datastructures import Mesh
from compas.geometry import Box

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
from cross_cell_crease_study import choose_faces, terminal_networks
from cheshire import save_mesh,load_mesh
from cheshire.creases import make_network,crease_subdivide_once
from cheshire.execution import ExecutionBudget
from cheshire.lineage import ParentRef
from cheshire.ornament import source_history,propagate_history
from cheshire.vocabulary import VocabularyStage,vocabulary_event


@pytest.mark.skipif(not os.environ.get('CHESHIRE_MOLA_DLL'),reason='Explicit real HDMola required')
def test_event_then_crease_then_role_descendant_export(tmp_path):
    source=Mesh.from_shape(Box(2,2,2));before=deepcopy(source.__data__)
    history=source_history(source)
    net=make_network(source,'retained',list(source.face_halfedges(0)),6,{})
    stage=VocabularyStage('major','TaperedExtrusion',dict(height_ratio=.8,fraction=.6),{})
    event=vocabulary_event(source,history,stage,selected_faces=[0],
        dll_path=os.environ['CHESHIRE_MOLA_DLL'],budget=ExecutionBudget(1000,1000,64),allow_large_taper=True)
    nets,_=terminal_networks(source,event['mesh'],(net,),event['corner_parents'])
    crease=crease_subdivide_once(event['mesh'],nets,budget=ExecutionBudget(1000,1000,64))
    parents={r['id']:[ParentRef(r['source_face'],1.)] for r in crease.metadata['face_sources']}
    history=propagate_history(event['history'],parents)
    declaration=dict(selector=dict(z_min=-10,z_max=10,role='EXTRUSION_SIDE',event_stage='major'),
        placement='ADJACENT',hops=8,max_events=100,spacing=0)
    selected,_=choose_faces(crease.mesh,source,history,crease.networks,declaration,event['events'])
    assert selected
    assert all(('major','EXTRUSION_SIDE') in history[f]['roles'] for f in selected)
    assert all('major:parent:0' in history[f]['events'] for f in selected)
    assert set(history)==set(crease.mesh.faces())
    # Exact output round trip is stronger than preset-value assertions.
    path=tmp_path/'mixed.obj';save_mesh(crease.mesh,path)
    assert load_mesh(path).to_vertices_and_faces()==crease.mesh.to_vertices_and_faces()
    assert source.__data__==before


def test_display_camera_rotation_preserves_metric_depth():
    from hero_design_views import matrix,rotated
    from math import dist
    data=dict(vertices=[dict(id=11,xyz=[2.,3.,4.]),dict(id=29,xyz=[-8.,7.,1.])],
        faces=[dict(id=41,vertices=[11,29,11])])
    before=deepcopy(data)
    for angles in [(0,0),(32,16),(90,0),(180,0)]:
        moved=rotated(data,matrix(*angles))
        assert dist(*[v['xyz'] for v in moved['vertices']])==pytest.approx(dist(*[v['xyz'] for v in data['vertices']]))
        assert moved['faces']==data['faces']
    assert data==before


@pytest.mark.skipif(not os.environ.get('CHESHIRE_MOLA_DLL'),reason='Explicit real HDMola required')
def test_local_constructor_failure_does_not_erase_usable_geometry():
    from hero_design_sprint import preflight_event
    mesh=Mesh.from_vertices_and_faces(
        [[0,0,0],[1,0,0],[1,1,0],[0,1,0],
         [3,0,0],[4,0,0],[5,.001,0],[4,.001,0]],
        [[0,1,2,3],[4,5,6,7]])
    before=deepcopy(mesh.__data__)
    stage=VocabularyStage('frame','InsetFrame',dict(width_ratio=.12),{})
    usable,failures=preflight_event(mesh,source_history(mesh),stage,[0,1],os.environ['CHESHIRE_MOLA_DLL'])
    assert usable==[0]
    assert failures and failures[0]['face']==1
    assert 'cap' in failures[0]['actual_constructor_failure'].lower()
    assert mesh.__data__==before


def test_frozen_input_mutation_is_rejected_before_cache_resume(tmp_path):
    from hero_design_sprint import verify_frozen_inputs
    from cross_cell_crease_study import write,file_hash,digest
    from cheshire.artifact_root import ArtifactRoot
    root=ArtifactRoot(tmp_path);path=root.resolve('inputs/mesh.json');path.parent.mkdir()
    data=dict(vertices=[dict(id=0,xyz=[1.,2.,3.])],faces=[])
    write(path,data)
    identity=dict(inputs=[dict(file='inputs/mesh.json',byte_sha256=file_hash(path),canonical_sha256=digest(data))])
    write(root.resolve('input_identity.json'),identity)
    assert verify_frozen_inputs(root)==identity
    data['vertices'][0]['xyz'][0]=2.;write(path,data)
    with pytest.raises(ValueError,match='Frozen input bytes changed'):
        verify_frozen_inputs(root)
