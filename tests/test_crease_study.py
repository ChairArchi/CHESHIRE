"""Focused portable resume/replay contract, independent of installed host/data."""
import json
from pathlib import Path
import sys

import pytest
from compas.datastructures import Mesh
from compas.geometry import Box

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from cross_cell_crease_study import can_resume, digest, file_hash, read, write, raw_mesh, mesh_to_data
from cheshire.artifact_root import ArtifactRoot
from cheshire.creases import crease_subdivide_once
from cheshire.crease_routing import CreaseRouter
from cheshire.ornament import source_history


def test_external_root_relocation_hash_resume_and_independent_crease_replay(tmp_path):
    root=ArtifactRoot(tmp_path/'external_artifacts'); directory=root.resolve('study/HERO/specimen/attempt_001')
    directory.mkdir(parents=True)
    mesh=Mesh.from_shape(Box(2,2,2)).subdivided(scheme='quad',k=1)
    data=mesh_to_data(mesh); history=source_history(mesh); cells={f:[f] for f in mesh.faces()}
    spec=dict(generator='N1',relation='outer_lintel',sharpness=3,quiet_below=0.)
    def run(serialized):
        original=raw_mesh(json.loads(json.dumps(serialized)))
        net=CreaseRouter(original,original,history,cells).generate(json.loads(json.dumps(spec)))
        step=crease_subdivide_once(original,(net,))
        step=crease_subdivide_once(step.mesh,step.networks,current_generation=1)
        return mesh_to_data(step.mesh), [n.to_data() for n in step.networks]
    a,na=run(data); b,nb=run(json.loads(json.dumps(data)))
    assert digest(a)==digest(b) and na==nb
    request=dict(recipe=spec,input='inputs/fixture.json',code=dict(source_files={'fixture':'same-bytes'},commit='old'))
    write(directory/'request.json',request); write(directory/'terminal.json',a)
    write(directory/'summary.json',dict(status='SUCCESS',request_sha256=digest(request),
        artifacts={'terminal.json':file_hash(directory/'terminal.json')}))
    current=json.loads(json.dumps(request)); current['code']['commit']='new-commit-of-same-bytes'
    assert can_resume(directory,current)
    # Relocating the artifact root preserves relative identity and validated bytes.
    import shutil
    relocated=tmp_path/'different_external_drive'; shutil.copytree(root.path,relocated)
    restored=ArtifactRoot(relocated).resolve(root.reference(directory))
    assert can_resume(restored,current)
    current['recipe']['sharpness']=2
    assert not can_resume(restored,current)
    (directory/'terminal.json').write_text('{}')
    assert not can_resume(directory,request)
    with pytest.raises(ValueError): root.resolve('../outside')
