"""Focused field controls and exact existing-geometry regression."""
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"examples"))
import spatial_activity_study as study
from cheshire.activity import ActivityField, diffuse, distance_values, distances, field_statistics, inherit_values, lerp_weight, peak_normalize, scale_at, source_graph
from cheshire.generational_subdivision import generational_subdivide_once
from cheshire.weighted_doosabin import weighted_doosabin_once
from subdivision_capability_study import polygon_mesh, read, write


def test_frozen_registration_graph_distance_and_source_immutability():
    source = polygon_mesh(read(study.FROZEN/"C0.json")); before = source.__data__
    graph = source_graph(source); frozen = read(study.FROZEN/"fields.json")
    assert frozen["source_hash"] == study.digest(read(study.FROZEN/"C0.json"))
    for name, ids in study.SEEDS.items():
        assert frozen["layouts"][name]["source_vertex_ids"] == list(ids)
        d = distances(graph, ids); values = distance_values(graph, ids, radius=3)
        assert all(d[v] == 0 and values[v] == 1 for v in ids)
        assert all(values[v] == max(0, 1-d[v]/3) for v in graph)
        assert all(abs(d[v]-d[n]) <= 1 for v in graph for n in graph[v])
    assert source.__data__ == before
    with pytest.raises(ValueError): distances(graph, [999])
    with pytest.raises(ValueError): distance_values(graph, [0], radius=0)


def test_diffusion_symmetry_and_predeclared_scale_separation():
    source = polygon_mesh(read(study.FROZEN/"C0.json")); graph = source_graph(source)
    mirror_pairs = [(0,12),(1,15),(2,14),(3,13),(4,8),(5,11),(6,10),(7,9),(16,23),(17,22),(18,20),(19,21)]
    for name, seeds in study.SEEDS.items():
        initial = {v: float(v in seeds) for v in graph}; d = distances(graph, seeds)
        stats = {}
        for scale, iterations in study.TIMES.items():
            raw = diffuse(graph, initial, iterations=iterations)
            values = peak_normalize(raw)
            assert all(values[a] == pytest.approx(values[b], abs=1e-15) for a,b in mirror_pairs)
            assert all(0 <= v <= 1 for v in values.values())
            # Degree-weighted mass is conserved by this random-walk diffusion.
            assert sum(raw[v]*len(graph[v]) for v in graph) == pytest.approx(sum(initial[v]*len(graph[v]) for v in graph))
            stats[scale] = field_statistics(values, d)
        assert stats["FINE"]["distance_weighted_spread"] < stats["MEDIUM"]["distance_weighted_spread"] < stats["BROAD"]["distance_weighted_spread"]
        assert stats["FINE"]["effective_fraction"] < stats["MEDIUM"]["effective_fraction"] < stats["BROAD"]["effective_fraction"]
    assert diffuse(graph, initial, iterations=0) == initial
    for rate in (-.1,1.1,float("nan")):
        with pytest.raises(ValueError): diffuse(graph, initial, rate=rate)


def test_positive_parent_inheritance_and_unavailable_values():
    values = {1: .2, 3: 1.0}
    assert inherit_values(values, {8: [(1,.25),(3,.75)]}) == {8:.8}
    assert inherit_values(values, {8: [(99,1.0)]}) == {8:None}
    with pytest.raises(ValueError): inherit_values(values, {8:[(1,-.1),(3,1.1)]})
    with pytest.raises(ValueError): inherit_values(values, {8:[(1,.5)]})
    field = ActivityField("test", values); values[1] = 0
    assert field.vertex(1) == .2
    with pytest.raises(TypeError): field.values[1] = 0
    with pytest.raises(ValueError): ActivityField("bad", {0:float("nan")})


def test_local_weight_interpolation_and_control_assignments():
    assert lerp_weight(.2, -.9, 0) == .2
    assert lerp_weight(.2, -.9, 1) == -.9
    assert lerp_weight(0, -.8, .25) == -.2
    assert [scale_at("M",g) for g in range(1,7)] == ["BROAD","MEDIUM","MEDIUM","FINE","FINE","FINE"]
    assert [scale_at("R",g) for g in range(1,7)] == ["FINE","MEDIUM","MEDIUM","BROAD","BROAD","BROAD"]
    assert [scale_at("P",g) for g in range(1,7)] == ["MEDIUM","FINE","FINE","BROAD","BROAD","BROAD"]
    assert all(scale_at("S",g)=="MEDIUM" for g in range(1,7))
    with pytest.raises(ValueError): lerp_weight(0,1,None)
    with pytest.raises(ValueError): scale_at("M",0)


def test_uniform_local_parameters_reproduce_original_operator_exactly():
    source = polygon_mesh(read(study.FROZEN/"C0.json")); original = study.mesh_to_data(source)
    weights = dict(wf=.3,w1=-1,we=-.08,w2=-.7,wp=.1,w3=-.4,w4=.6)
    origins = None
    for generation in range(2):
        field = ActivityField("uniform", {v:1 for v in source.vertices()})
        expected = generational_subdivide_once(source,weights,origin_lineage=origins,current_generation=generation)
        actual = generational_subdivide_once(source,weights,origin_lineage=origins,current_generation=generation,
            **study.modulation(source,field,weights,"CC"))
        assert study.mesh_to_data(expected.mesh) == study.mesh_to_data(actual.mesh)
        assert all(a["w3"]==weights["w3"] and a["w4"]==weights["w4"] for a in actual.metadata["later_generation_face_stencil"]["applications"])
        source, origins = expected.mesh, expected.origin_lineage
    source = polygon_mesh(original); families=None
    weights = read(study.FROZEN/"recipes.json")["DS"][0]
    for generation in range(2):
        field = ActivityField("uniform",{v:1 for v in source.vertices()})
        expected = weighted_doosabin_once(source,weights,face_families=families,current_generation=generation)
        actual = weighted_doosabin_once(source,weights,face_families=families,current_generation=generation,
            **study.modulation(source,field,weights,"DS",families))
        assert study.mesh_to_data(expected.mesh) == study.mesh_to_data(actual.mesh)
        source,families = expected.mesh,expected.face_families


def test_source_fields_static_run_determinism_and_exact_saved_uniform():
    references = read(study.FROZEN/"uniform_reference_hashes.json")
    for grammar in ("CC","DS","HYBRID"):
        spec = study.case_spec("A","A_SHOULDER_PAIR",grammar,"U",2)
        result = study.run_case(spec)
        assert result["source_immutable"]
        assert all(r["geometry_hash"]==references[grammar][f"G{r['generation']}"] for r in result["stages"])
    spec = study.case_spec("A","C_UPPER_BIAS","CC","S",2)
    first = study.run_case(spec); second = study.run_case(spec)
    assert [r["geometry_hash"] for r in first["stages"]] == [r["geometry_hash"] for r in second["stages"]]
    assert all(r["source_coverage"]==1 for r in first["stages"])


def test_resume_verifies_spec_completion_and_all_geometry_hashes(tmp_path):
    spec = study.case_spec("A","A_SHOULDER_PAIR","DS","S",1)
    directory=tmp_path/"case"
    study.one(spec,directory)
    write(directory/"crossing_audit.json",{"candidates":[{"id":"G1"}]})
    assert study.valid_completed(directory,spec)
    assert not study.valid_completed(directory,{**spec,"strategy":"M"})
    data=read(directory/"G1.json")
    data["vertices"][0]["xyz"][0]+=1; write(directory/"G1.json",data)
    assert not study.valid_completed(directory,spec)
    write(directory/"summary.json",dict(status="PARTIAL",generations_reached=0,stages=[]))
    assert not study.valid_completed(directory,spec)
