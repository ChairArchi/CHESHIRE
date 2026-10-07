"""Contracts needed to continue a saved benchmark, independent of its appearance."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))
from hansmeyer_benchmark import specimen, specimen_definition, restore_state, phase
from cross_cell_crease_study import raw_mesh, mesh_to_data, gz_write, read
from cheshire.sharp_subdivision import sharp_subdivide_once


def test_coarse_specimen_is_closed_unornamented_and_zero_backend_matches_standard():
    mesh = specimen(specimen_definition())
    assert (mesh.number_of_vertices(), mesh.number_of_faces(), mesh.number_of_edges()) == (26, 24, 48)
    assert mesh.is_closed() and mesh.is_connected() and mesh.is_manifold()
    assert sorted(set(mesh.vertex_coordinates(v)[2] for v in mesh.vertices())) == [0, 650, 1800]
    actual = sharp_subdivide_once(mesh).mesh
    reference = mesh.subdivided(scheme='catmullclark', k=1)
    assert [actual.face_vertices(f) for f in actual.faces()] == [reference.face_vertices(f) for f in reference.faces()]
    for v in reference.vertices():
        assert actual.vertex_coordinates(v) == pytest.approx(reference.vertex_coordinates(v), abs=1e-11)


def test_saved_actual_origins_reproduce_next_nonstationary_generation(tmp_path):
    mesh = specimen(specimen_definition())
    first = sharp_subdivide_once(mesh, dict(wf=-280, w1=.8, we=320, w2=-2.8, wp=520))
    state = dict(generation=1, origins=first.origin_lineage,
                 face_ancestry={r['id']: r['source_face'] for r in first.metadata['face_sources']})
    gz_write(tmp_path / 'geometry.json.gz', mesh_to_data(first.mesh))
    gz_write(tmp_path / 'state.json.gz', state)
    restored = restore_state(read(tmp_path / 'state.json.gz'))
    geometry = raw_mesh(read(tmp_path / 'geometry.json.gz'))
    weights = dict(wf=70, w1=-1.05, we=-20, w2=-.9, wp=18, w3=-.8, w4=.5)
    a = sharp_subdivide_once(first.mesh, weights, origin_lineage=first.origin_lineage, current_generation=1)
    b = sharp_subdivide_once(geometry, weights, origin_lineage=restored['origins'], current_generation=1)
    assert mesh_to_data(a.mesh) == mesh_to_data(b.mesh)
    assert a.origin_lineage == b.origin_lineage
    assert b.metadata['later_generation_face_stencil']['eligible_faces'] == 96
    assert set(restored['face_ancestry'].values()) == set(mesh.faces())
    assert {r['source_face'] for r in b.metadata['face_sources']} == set(first.mesh.faces())


def test_nonstationary_class_pair_changes_actual_face_geometry_without_topology_change():
    first = sharp_subdivide_once(specimen(specimen_definition()), dict(wf=-280, we=320, wp=520))
    a = sharp_subdivide_once(first.mesh, origin_lineage=first.origin_lineage, current_generation=1)
    b = sharp_subdivide_once(first.mesh, phase(dict(w3=-.6, w4=.35))['weights'],
                            origin_lineage=first.origin_lineage, current_generation=1)
    assert [a.mesh.face_vertices(f) for f in a.mesh.faces()] == [b.mesh.face_vertices(f) for f in b.mesh.faces()]
    changed = {v for v in a.mesh.vertices() if a.mesh.vertex_coordinates(v) != b.mesh.vertex_coordinates(v)}
    face_points = {p['id'] for p in b.metadata['points'] if p['point_class'] == 'face'}
    assert changed and changed <= face_points
    assert a.sampling_parents == b.sampling_parents
