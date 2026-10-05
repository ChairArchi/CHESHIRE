"""Real optional DLL tests; set CHESHIRE_MOLA_DLL to an explicit external path."""

from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import subprocess
from uuid import uuid4

import pytest
from compas.datastructures import Mesh
from cheshire import ExecutionBudget, FieldSpec, inherit_fields, validate_lineage_coverage
from cheshire.mola import eligible_planar_faces, extrude_tapered_once
import cheshire.mola as adapter

DLL = os.environ.get("CHESHIRE_MOLA_DLL")
pytestmark = pytest.mark.skipif(not DLL or not importlib.util.find_spec("pythonnet"),
                              reason="Optional real Mola backend: set CHESHIRE_MOLA_DLL and install .[mola].")
ROOT = Path(__file__).resolve().parents[1]


def execute(mesh, selection, **kwargs):
    return extrude_tapered_once(mesh, selected_faces=selection, height_ratio=kwargs.pop("height_ratio", 0.2),
                               fraction=kwargs.pop("fraction", 0.25), dll_path=DLL, **kwargs)


def test_real_unit_quad_triangle_normal_and_taper():
    for corners in ([0, 1, 2, 3], [3, 2, 1, 0], [0, 1, 2]):
        points = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]
        mesh = Mesh.from_vertices_and_faces(points[:len(corners)], [corners])
        result = execute(mesh, [0])
        height = result.parameters[0]["height"]
        normal = mesh.face_normal(0)
        upper = [result.mesh.vertex_coordinates(k) for k in result.parameters[0]["upper_vertex_ids"]]
        center = mesh.face_centroid(0)
        for base, top in zip(mesh.face_coordinates(0), upper):
            assert top == pytest.approx([0.75*base[a]+0.25*center[a]+height*normal[a] for a in range(3)], abs=2e-6)
        assert result.mesh.number_of_faces() == len(corners)+1
        assert list(result.face_roles.values()).count("cap") == 1
        assert result.backend["runtime"].startswith("8.")
        assert result.backend["target_framework"] == ".NETStandard,Version=v2.1"
        assert "FaceSubdivision" in result.backend["public_types"]


def test_cube_counts_neighbors_lineage_and_explicit_inheritance(box_mesh):
    parent = next(box_mesh.faces())
    result = execute(box_mesh, [parent])
    assert (result.mesh.number_of_vertices(), result.mesh.number_of_faces()) == (12, 10)
    assert result.mesh.is_closed() and result.mesh.is_manifold()
    for key in box_mesh.vertices():
        assert result.mesh.vertex_coordinates(key) == box_mesh.vertex_coordinates(key)
    for key in box_mesh.faces():
        if key != parent:
            assert result.mesh.face_vertices(key) == box_mesh.face_vertices(key)
    assert parent not in set(result.mesh.faces())
    assert validate_lineage_coverage(box_mesh, result.mesh, result.lineage) == []
    inherited = inherit_fields(result.lineage,
        {"value": {k: float(k) for k in box_mesh.vertices()}, "label": {k: k for k in box_mesh.vertices()}},
        [FieldSpec("value", "vertex", "scalar", "CONTINUOUS"),
         FieldSpec("label", "vertex", "categorical", "CATEGORICAL"),
         FieldSpec("area", "face", "scalar", "RECOMPUTE")])
    for key in result.parameters[parent]["upper_vertex_ids"]:
        refs = result.lineage.vertex_parents[key]
        assert inherited.values["value"][key] == pytest.approx(sum(ref.weight*ref.key for ref in refs))
        assert inherited.values["label"][key] is None
    assert inherited.recompute_fields == ["area"]


def test_adjacent_faces_keep_shared_base_edge_and_aligned_parameters(box_mesh):
    edge = next(box_mesh.edges())
    parents = list(box_mesh.edge_faces(edge))
    result = execute(box_mesh, parents, height_ratio={parents[0]: 0.1, parents[1]: 0.3},
                     fraction={parents[0]: 0.25, parents[1]: 0.65})
    assert (result.mesh.number_of_vertices(), result.mesh.number_of_faces()) == (16, 14)
    sides = result.mesh.edge_faces(edge)
    assert all(result.face_roles[k] == "side" for k in sides)
    assert {result.lineage.face_parents[k][0].key for k in sides} == set(parents)
    assert result.parameters[parents[0]]["height_ratio"] == 0.1
    assert result.parameters[parents[1]]["height_ratio"] == 0.3
    assert not set(result.parameters[parents[0]]["upper_vertex_ids"]) & set(result.parameters[parents[1]]["upper_vertex_ids"])
    assert result.mesh.is_closed() and validate_lineage_coverage(box_mesh, result.mesh, result.lineage) == []


def test_invalid_inputs_and_budget_block_before_backend(open_mesh, monkeypatch):
    def forbidden(*args):
        raise AssertionError("Backend must not execute.")
    monkeypatch.setattr(adapter, "_load_backend", forbidden)
    for params in ({"height_ratio": 0}, {"fraction": float("nan")}, {"fraction": 0.9},
                   {"height_ratio": {}}, {"fraction": {0: 0.25, 99: 0.3}}, {"cap_top": False},
                   {"budget": ExecutionBudget(4)}, {"budget": ExecutionBudget(50, 7)}):
        with pytest.raises(ValueError):
            execute(open_mesh, [0], **params)
    warped = open_mesh.copy()
    warped.vertex_attribute(next(warped.vertices()), "z", 0.1)
    with pytest.raises(ValueError, match="nonplanar"):
        execute(warped, [0])
    assert eligible_planar_faces(warped)[0] == []
    noop = execute(open_mesh, [])
    assert noop.mesh.__data__ == open_mesh.__data__ and noop.mesh is not open_mesh
    assert noop.backend is None and validate_lineage_coverage(open_mesh, noop.mesh, noop.lineage) == []


def test_repeatable_source_immutable_and_large_coordinate_boundary(open_mesh):
    before = deepcopy(open_mesh.__data__)
    first, second = execute(open_mesh, [0]), execute(open_mesh, [0])
    assert first.mesh.__data__ == second.mesh.__data__ and first.parameters == second.parameters
    assert open_mesh.__data__ == before
    translated = open_mesh.copy()
    for key in translated.vertices():
        x, y, z = translated.vertex_coordinates(key)
        translated.vertex_attributes(key, "xyz", [x+1e9, y-1e9, z+1e9])
    moved = execute(translated, [0])
    for key in translated.vertices():
        assert moved.mesh.vertex_coordinates(key) == translated.vertex_coordinates(key)


def test_real_external_worker_three_fixed_variants(box_mesh, tmp_path):
    # Import bridge without Rhino and exercise the unchanged isolated launcher.
    import sys
    sys.path.insert(0, str(ROOT / "rhino"))
    from cheshire_worker import mesh_to_data
    from exchange import read_json, validate_response, write_json_atomic
    from worker_process import worker_launch_options
    payload = {"protocol": 1, "run_id": str(uuid4()), "mode": "MOLA_TAPER_STUDY",
               "source": {"document_serial": 7, "object_id": "mola-control"},
               "mola_dll": DLL, "selected_faces": [next(box_mesh.faces())], "mesh": mesh_to_data(box_mesh)}
    write_json_atomic(tmp_path / "request.json", payload)
    process = subprocess.run(**worker_launch_options(ROOT, tmp_path / "request.json", tmp_path / "response.json"),
                             capture_output=True, text=True, timeout=60)
    assert process.returncode == 0, process.stderr
    result = validate_response(read_json(tmp_path / "response.json"), payload)
    assert result["status"] == "SUCCESS", result["reason"]
    assert [(v["name"], v["height_ratio"], v["fraction"]) for v in result["variants"]] == [
        ("A", 0.1, 0.25), ("B", 0.3, 0.25), ("C", 0.1, 0.65)]
    assert all((v["vertex_count"], v["face_count"]) == (12, 10) and v["lineage_coverage"] == [] for v in result["variants"])
    assert result["variants"][0]["parameters"][0]["height"]*3 == pytest.approx(result["variants"][1]["parameters"][0]["height"])
