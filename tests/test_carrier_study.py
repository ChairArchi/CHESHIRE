from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "rhino"))
from carrier_study import coarse_gate,carrier_ladder,carrier_statistics,expanded_schedule,LOCAL_SCHEDULES,run_uniform,topology_warning_association


def test_connected_outward_planar_gate_has_shared_interfaces_and_opening():
    mesh=coarse_gate()
    stats=carrier_statistics(mesh)
    assert (stats["vertex_count"],stats["edge_count"],stats["face_count"]) == (24,44,22)
    assert stats["components"] == 1 and stats["boundary_edge_count"] == 0 and stats["is_manifold"]
    assert stats["bounding_box"] == [4000,500,3500]
    assert stats["signed_volume"] == pytest.approx((4000*3500-2200*2600)*500)
    assert len({tuple(sorted(mesh.face_vertices(f))) for f in mesh.faces()}) == 22
    assert all(len(mesh.face_vertices(f)) == 4 for f in mesh.faces())
    assert not any(-1100 < mesh.face_centroid(f)[0] < 1100 and mesh.face_centroid(f)[2] < 2600 for f in mesh.faces())


def test_carrier_ladder_deterministic_and_does_not_move_or_mutate_source():
    source=coarse_gate(); before=deepcopy(source.__data__)
    first,second=carrier_ladder(source),carrier_ladder(source)
    assert source.__data__ == before
    assert [m.number_of_faces() for m in first.values()] == [22,88,352]
    assert all(first[k].__data__ == second[k].__data__ for k in first)
    for mesh in first.values():
        assert carrier_statistics(mesh)["bounding_box"] == [4000,500,3500]
        assert all(mesh.vertex_coordinates(v) == source.vertex_coordinates(v) for v in source.vertices())


def test_identical_schedule_across_carriers_and_immutable_geometry():
    carriers=carrier_ladder(coarse_gate()); schedule=LOCAL_SCHEDULES["L3_soft_interpolation"]
    for mesh in carriers.values():
        before=deepcopy(mesh.__data__)
        result=run_uniform(mesh,schedule,generations=1)
        assert result["status"] == "SUCCESS"
        assert result["stages"][0]["ratios"] == schedule[0]
        assert result["schedule"] == expanded_schedule(schedule)
        assert mesh.__data__ == before


def test_extraordinary_diagnostic_reports_actual_topology_without_causality():
    mesh=coarse_gate(); stats=carrier_statistics(mesh)
    assert sum(stats["valence_histogram"].values()) == 24
    assert stats["extraordinary_vertex_count"] == sum(mesh.vertex_degree(v) != 4 for v in mesh.vertices())
    report=topology_warning_association(mesh,[0,1])
    assert report["near_warning_faces"]+report["far_warning_faces"] == 2
    assert report["near_faces"]+report["far_faces"] == 22
    assert "no attribution of cause" in report["interpretation"]


def test_budget_stop_keeps_source_and_never_calls_backend(monkeypatch):
    import carrier_study
    from cheshire.execution import ExecutionBudget
    mesh=coarse_gate(); before=deepcopy(mesh.__data__)
    monkeypatch.setattr(carrier_study,"BUDGET",ExecutionBudget(87,90,6))
    monkeypatch.setattr(type(mesh),"subdivided",lambda *a,**k: pytest.fail("Over-budget backend called"))
    result=run_uniform(mesh,LOCAL_SCHEDULES["L4_macro_corner"])
    assert result["status"] == "FAILED" and not result["stages"] and "budget" in result["reason"]
    assert mesh.__data__ == before


def test_interruption_after_completed_checkpoint_keeps_readable_partial(tmp_path,monkeypatch):
    import json
    sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "examples"))
    import carrier_scale_study as experiment
    from cheshire_worker import mesh_to_data
    source=tmp_path / "source.json"; schedule=tmp_path / "schedule.json"
    source.write_text(json.dumps(mesh_to_data(coarse_gate())),encoding="utf-8")
    schedule.write_text(json.dumps(LOCAL_SCHEDULES["L4_macro_corner"]),encoding="utf-8")
    def interrupted(mesh,weights,**options):
        run_uniform(mesh,weights,generations=1,publish=options["publish"])
        raise RuntimeError("Simulated interruption before G2")
    monkeypatch.setattr(experiment,"run_uniform",interrupted)
    directory=tmp_path / "case"
    with pytest.raises(RuntimeError,match="Simulated interruption"):
        experiment.one(directory,source,schedule,6)
    summary=json.loads((directory / "summary.json").read_text())
    response=json.loads((directory / "response.json").read_text())
    assert summary["status"] == "PARTIAL" and summary["generations_reached"] == 1
    assert summary["source_immutable"] and summary["stages"][0]["checkpoint_elapsed_seconds"] >= 0
    assert len(response["variants"]) == 1 and response["variants"][0]["id"] == "G1"
    assert (directory / "G1.obj").exists() and (directory / "checkpoint.json.gz").exists()
