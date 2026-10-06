from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"rhino"))
from carrier_study import coarse_gate
from cheshire.weighted_doosabin import weighted_doosabin_once
from cheshire_worker import mesh_to_data
from capability_display import polygon_display_plan,comparison_items
from exchange import CAPABILITY_MODE,MAX_STAGE_COUNT,validate_mesh_data,validate_request,validate_response
import capability_study


def test_polygon_exchange_and_display_fan_are_explicit_opt_in():
    data=mesh_to_data(weighted_doosabin_once(coarse_gate([0,0,0])).mesh); original=deepcopy(data)
    with pytest.raises(ValueError,match="triangle/quad"):
        validate_mesh_data(data)
    assert validate_mesh_data(data,120000,120000,allow_polygons=True) is data
    faces,ids,ngons=polygon_display_plan(data)
    assert len(ngons)==4 and len(faces)==len(data["faces"])+8
    assert all(len(face) in (3,4) for face in faces)
    for group in ngons:
        original_face=next(f for f in data["faces"] if f["id"]==group["source_face"])
        assert group["vertices"]==original_face["vertices"]
        assert all(ids[i]==original_face["id"] for i in group["faces"])
    assert data==original and MAX_STAGE_COUNT==50000


def test_review_loader_preserves_source_verifies_files_and_publishes_valid_prefixes(tmp_path,monkeypatch):
    monkeypatch.setattr(capability_study,"ROOT",tmp_path)
    study=tmp_path/"output/task17/study"; study.mkdir(parents=True)
    source=mesh_to_data(coarse_gate([0,0,0])); ds=mesh_to_data(weighted_doosabin_once(coarse_gate([0,0,0])).mesh)
    def evidence(path,data):
        path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(data),encoding="utf-8")
        return hashlib.sha256(path.read_bytes()).hexdigest()
    sha=evidence(study/"C0.json",source)
    manifest=dict(source_file_sha256=sha,design_status="PARTIAL_SUCCESS",evidence_note="Synthetic loader fixture; not visual evidence.",display=[
        dict(case="C11_REFERENCE",generation=0,roles=["TASK16 C11 CONTROL"],file_sha256=evidence(study/"cases/C11_REFERENCE/G0.json",source)),
        dict(case="DS_TEST",generation=1,roles=["BEST WEIGHTED DS","MAX_CAPABILITY_CANDIDATE","GATE_LEGIBLE_CANDIDATE"],file_sha256=evidence(study/"cases/DS_TEST/G1.json",ds))])
    evidence(study/"selections.json",manifest)
    request=dict(protocol=1,run_id=str(uuid4()),source=dict(object_id="synthetic",document_serial=1),mode=CAPABILITY_MODE,mesh=source)
    validate_request(request); original=deepcopy(request); checkpoints=[]
    result=capability_study.run_subdivision_capability_study(request,publish=lambda r:checkpoints.append(deepcopy(r)))
    assert result["status"]=="SUCCESS" and request==original
    assert len(checkpoints)==3 and [len(r["variants"]) for r in checkpoints]==[1,2,2]
    assert all(validate_response(r,request) is r for r in checkpoints)
    assert len(comparison_items(result))==3
    assert result["variants"][1]["mesh"]==ds
    (study/"cases/DS_TEST/G1.json").write_text("{}",encoding="utf-8")
    with pytest.raises(ValueError,match="Reviewed output changed"):
        capability_study.run_subdivision_capability_study(request)
