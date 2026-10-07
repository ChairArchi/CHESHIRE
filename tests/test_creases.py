from copy import deepcopy
import json
from pathlib import Path

import pytest
from compas.datastructures import Mesh
from compas.geometry import Box

from cheshire.creases import (CreaseNetwork, crease_subdivide_once, make_network,
    edge_key, fractional_vertex, crease_vertex)
from cheshire.crease_policy import assess_contact_policy
from cheshire.execution import ExecutionBudget
from cheshire.crease_routing import CreaseRouter

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    if name == 'gate':
        data = json.loads((ROOT/'studies/task19/C0.json').read_text())
        return Mesh.from_vertices_and_faces({v['id']: v['xyz'] for v in data['vertices']},
            {f['id']: f['vertices'] for f in data['faces']})
    return Mesh.from_shape(Box(2, 2, 2) if name == 'cube' else Box(1, 1, 6))


@pytest.mark.parametrize('name', ['cube', 'column', 'gate'])
def test_integer_exact_installed_compas_coordinates_oriented_topology_decay(name):
    mesh = fixture(name); original_mesh = mesh; original = deepcopy(mesh.__data__)
    # Includes a degree-three corner, degree-two crease and one-edge dart.
    v = min(mesh.vertices()); neighbors = mesh.vertex_neighbors(v)
    edges = [(v, u) for u in neighbors] + [(neighbors[0], mesh.vertex_neighbors(neighbors[0])[1])]
    network = make_network(mesh, 'parity', edges, 2, {'rule': 'fixture-first-corner'})
    reference = mesh.copy()
    for e in network.edges:
        reference.edge_attribute(e.vertices, 'crease', 2)
    networks = (network,)
    for generation in range(3):
        expected = reference.subdivided(scheme='catmullclark', k=1)
        step = crease_subdivide_once(mesh, networks, current_generation=generation)
        assert list(step.mesh.vertices()) == list(expected.vertices())
        assert [(v, step.mesh.vertex_coordinates(v)) for v in step.mesh.vertices()] == [(v, expected.vertex_coordinates(v)) for v in expected.vertices()]
        assert [(f, step.mesh.face_vertices(f)) for f in step.mesh.faces()] == [(f, expected.face_vertices(f)) for f in expected.faces()]
        assert len(step.networks[0].edges) == len(network.edges)*2**(generation+1)
        assert all(e.sharpness == max(2-generation-1, 0) for e in step.networks[0].edges)
        assert all((expected.edge_attribute(e.vertices, 'crease') or 0) == e.sharpness for e in step.networks[0].edges)
        assert all(e.parent_edge in {p.vertices for p in networks[0].edges} for e in step.networks[0].edges)
        assert step.mesh.is_closed() and step.mesh.is_manifold()
        mesh = step.mesh; networks = step.networks; reference = expected
    assert original_mesh.__data__ == original


def test_midpoint_two_edge_corner_and_dart_hand_oracles():
    mesh = fixture('cube'); xyz = {v: mesh.vertex_coordinates(v) for v in mesh.vertices()}
    v = min(mesh.vertices()); neighbors = mesh.vertex_neighbors(v)
    smooth = mesh.subdivided(k=1)
    for degree in (0, 1, 2, 3):
        networks = (make_network(mesh, 'rule', [(v, u) for u in neighbors[:degree]], 3, {'degree': degree}),) if degree else ()
        step = crease_subdivide_once(mesh, networks)
        if degree < 2:
            assert step.mesh.vertex_coordinates(v) == smooth.vertex_coordinates(v)
        elif degree == 2:
            assert step.mesh.vertex_coordinates(v) == pytest.approx([(xyz[neighbors[0]][i]+6*xyz[v][i]+xyz[neighbors[1]][i])/8 for i in range(3)])
        else:
            assert step.mesh.vertex_coordinates(v) == xyz[v]
        for row in step.metadata['edge_points']:
            if degree and tuple(row['edge']) in {e.vertices for e in networks[0].edges}:
                a, b = row['edge']
                assert step.mesh.vertex_coordinates(row['point']) == [(xyz[a][i]+xyz[b][i])/2 for i in range(3)]


def test_network_roundtrip_hash_ancestry_and_descendant_connectivity():
    mesh = fixture('cube'); edges = list(mesh.face_halfedges(0))
    cells = {f: [f+100] for f in mesh.faces()}; history = {f: {'source': {f: 1.}} for f in mesh.faces()}
    net = make_network(mesh, 'loop', edges, 2.5, {'generator': 'face-cycle'}, cells=cells, history=history)
    data = json.loads(json.dumps(net.to_data())); restored = CreaseNetwork.from_data(data)
    assert net == restored and net.digest() == restored.digest() and hash(net) == hash(restored)
    assert data['cross_cell'] and len(data['c0_ancestry']) >= 2
    result = crease_subdivide_once(mesh, (net,), mode='UNIFORM_FRACTIONAL')
    roots = {e.vertices: e for e in net.edges}
    for e in result.networks[0].edges:
        assert e.c0_faces == roots[e.root_edge].c0_faces
        assert e.parent_cells == roots[e.root_edge].parent_cells
        assert e.sharpness == 1.5
    altered = deepcopy(data); altered['junction_vertices'] = [987]
    with pytest.raises(ValueError): CreaseNetwork.from_data(altered)
    with pytest.raises(ValueError): make_network(mesh, 'absent', [(0, 999)], 2, {})
    from dataclasses import replace
    integer=replace(net,edges=tuple(replace(e,sharpness=2) for e in net.edges))
    assert all(type(e.sharpness) is float for e in integer.edges)
    assert crease_subdivide_once(mesh,(integer,)).mesh.is_closed()


def test_fractional_limits_midpoint_blend_and_variable_junction_masks():
    mesh = fixture('cube'); v = min(mesh.vertices()); neighbors = mesh.vertex_neighbors(v)
    xyz = {p: mesh.vertex_coordinates(p) for p in mesh.vertices()}; smooth = mesh.subdivided(k=1)
    edges = [(v, u) for u in neighbors[:2]]
    for s in (0, .5, 1):
        net = make_network(mesh, 'uniform', edges, s, {})
        result = crease_subdivide_once(mesh, (net,), mode='UNIFORM_FRACTIONAL')
        sharp = crease_vertex(v, neighbors[:2], xyz, smooth.vertex_coordinates(v))
        assert result.mesh.vertex_coordinates(v) == pytest.approx([s*sharp[i]+(1-s)*smooth.vertex_coordinates(v)[i] for i in range(3)])
        assert all(e.sharpness == 0 for e in result.networks[0].edges)
    incident = [(neighbors[0], 3.), (neighbors[1], 3.), (neighbors[2], .25)]
    actual, metadata = fractional_vertex(v, incident, xyz, smooth.vertex_coordinates(v))
    expected = crease_vertex(v, neighbors[:2], xyz, smooth.vertex_coordinates(v))
    assert actual == pytest.approx([.25*xyz[v][i]+.75*expected[i] for i in range(3)])
    assert metadata == dict(parent='CORNER', child='CREASE', parent_weight=.25)
    actual, metadata = fractional_vertex(v, [(neighbors[0], .2), (neighbors[1], .8)], xyz, smooth.vertex_coordinates(v))
    sharp = crease_vertex(v, neighbors[:2], xyz, smooth.vertex_coordinates(v))
    assert actual == pytest.approx([.5*sharp[i]+.5*smooth.vertex_coordinates(v)[i] for i in range(3)])
    assert metadata['parent_weight'] == .5
    with pytest.raises(ValueError): crease_subdivide_once(mesh, (make_network(mesh, 'fraction', edges, .5, {}),))


def test_fixed_corner_overrides_crease_and_budget_blocks_before_growth():
    mesh = fixture('cube'); v = min(mesh.vertices())
    net = make_network(mesh, 'fixed', [(v, u) for u in mesh.vertex_neighbors(v)[:2]], .5, {})
    result = crease_subdivide_once(mesh, (net,), mode='UNIFORM_FRACTIONAL', fixed=[v])
    assert result.mesh.vertex_coordinates(v) == mesh.vertex_coordinates(v)
    with pytest.raises(ValueError): crease_subdivide_once(mesh, (net,), mode='UNIFORM_FRACTIONAL', budget=ExecutionBudget(10, 100))


def test_contact_cap_is_diagnostic_and_hard_failures_still_stop():
    assert assess_contact_policy(0)['design_eligible']
    assert assess_contact_policy(10)['design_eligible']
    assert not assess_contact_policy(11)['design_eligible']
    assert not assess_contact_policy(31)['stop']
    cap = assess_contact_policy(256, cap_reached=True)
    assert not cap['stop'] and cap['additional_requested_stage_allowed'] and not cap['design_eligible']
    assert not assess_contact_policy(256, cap_reached=True, stages_after_cap=1)['stop']
    assert not assess_contact_policy(256, cap_reached=True, stages_after_cap=5)['stop']
    assert cap['capability_state']=='SELF_INTERSECTING_CAPABILITY'
    assert assess_contact_policy(101)['capability_usable']
    assert assess_contact_policy(0, catastrophic=True)['hard_stop']
    assert not assess_contact_policy(11, mode='DESIGN')['stop']
    assert assess_contact_policy(0,valid=False)['stop']


def test_source_routing_deterministic_real_edges_and_cross_cell_counts():
    mesh = fixture('gate'); history = {f: {'source': {f: 1.}} for f in mesh.faces()}
    cells = {f: [f] for f in mesh.faces()}
    router = CreaseRouter(mesh, mesh, history, cells)
    spec = dict(generator='N1', relation='outer_lintel', sharpness=4, quiet_below=.5)
    a = router.generate(spec); b = router.generate(json.loads(json.dumps(spec)))
    assert a.digest() == b.digest() and a.to_data()['cross_cell']
    assert len(a.to_data()['c0_ancestry']) >= 2 and len(a.to_data()['parent_cell_ancestry']) >= 3
    assert {e.vertices for e in a.edges} <= {edge_key(e) for e in mesh.edges()}
    assert not a.junction_vertices


def test_fractional_profile_route_and_three_arm_junction():
    # Several edges per arm are needed to distinguish an actual spatial profile.
    mesh = fixture('cube').subdivided(scheme='quad', k=2)
    history = {f: {'source': {f: 1.}} for f in mesh.faces()}; cells = {f: [f] for f in mesh.faces()}
    router = CreaseRouter(mesh, mesh, history, cells)
    spec = dict(generator='N6', junction='T', junction_xz=[0, .5],
        arm_targets=[[-.5, .5], [.5, .5], [0, 1.]], sharpness=4.5,
        profile='JUNCTION_SOFT_ENDS', quiet_below=0.)
    net = router.generate(spec)
    assert net.junction_vertices and len({e.sharpness for e in net.edges}) > 1
    step = crease_subdivide_once(mesh, (net,), mode='UNIFORM_FRACTIONAL')
    assert any(step.metadata['vertex_masks'][v]['parent'] == 'CORNER' for v in net.junction_vertices)
