"""Small closed-grid and cube counterexamples; never load the actual WALL G3."""
from pathlib import Path
import importlib.util
import copy

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location('tested_connected_patch_growth',
    Path(__file__).resolve().parents[1]/'experiments/connected_fold_growth_20261012/patch_growth.py')
growth = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(growth)


def box_grid(cross=16, longitudinal=64):
    """Closed quad cuboid surface with symmetry seams represented by shared IDs."""
    lookup, xyz, chart = {}, [], []
    def vertex(i, j, k):
        key = (i, j, k)
        if key not in lookup:
            lookup[key] = len(xyz)
            x, y, z = -1.+2.*i/cross, -1.+2.*j/cross, 10.*k/longitudinal
            xyz.append([x, y, z]); chart.append([k/longitudinal, x, y])
        return lookup[key]
    faces = []
    for j in range(cross):
        for k in range(longitudinal):
            faces.append([vertex(0,j,k), vertex(0,j,k+1), vertex(0,j+1,k+1), vertex(0,j+1,k)])
            faces.append([vertex(cross,j,k), vertex(cross,j+1,k), vertex(cross,j+1,k+1), vertex(cross,j,k+1)])
    for i in range(cross):
        for k in range(longitudinal):
            faces.append([vertex(i,0,k), vertex(i+1,0,k), vertex(i+1,0,k+1), vertex(i,0,k+1)])
            faces.append([vertex(i,cross,k), vertex(i,cross,k+1), vertex(i+1,cross,k+1), vertex(i+1,cross,k)])
    for i in range(cross):
        for j in range(cross):
            faces.append([vertex(i,j,0), vertex(i,j+1,0), vertex(i+1,j+1,0), vertex(i+1,j,0)])
            faces.append([vertex(i,j,longitudinal), vertex(i+1,j,longitudinal), vertex(i+1,j+1,longitudinal), vertex(i,j+1,longitudinal)])
    xyz, chart, faces = np.asarray(xyz), np.asarray(chart), np.asarray(faces, np.int64)
    mesh = growth.ArrayMesh(xyz, faces, np.full(len(xyz), -1, np.int8), xyz.copy(),
        np.full((len(faces), 3), -1, np.int64), 3)
    mesh.surface = 'vf'
    return mesh, chart


def assert_vertex_link_cycles(mesh):
    links = [[] for _ in mesh.xyz]
    for polygon in mesh.faces:
        for index, v in enumerate(polygon):
            links[v].append((int(polygon[index-1]), int(polygon[(index+1)%4])))
    for edges in links:
        neighbours = {}
        for a, b in edges:
            neighbours.setdefault(a, []).append(b); neighbours.setdefault(b, []).append(a)
        assert all(len(row) == 2 for row in neighbours.values())
        visited, stack = set(), [next(iter(neighbours))]
        while stack:
            v = stack.pop()
            if v not in visited:
                visited.add(v); stack.extend(neighbours[v])
        assert len(visited) == len(neighbours)


@pytest.fixture(scope='module')
def built():
    mesh, chart = box_grid()
    return mesh, chart, {mode: growth.build(mesh, chart, mode) for mode in growth.MODES}


def test_root_is_identical_before_branches_and_source_is_untouched(built):
    source, chart, results = built
    untouched, original_chart = box_grid()
    assert np.array_equal(source.xyz, untouched.xyz)
    assert np.array_equal(source.faces, untouched.faces)
    assert np.array_equal(source.classes, untouched.classes)
    assert np.array_equal(source.rest, untouched.rest)
    assert np.array_equal(source.anchors, untouched.anchors)
    assert source.surface == 'vf' and np.array_equal(chart, original_chart)
    root = results['ROOT_ONLY']; branch = results['BRANCHED']
    assert root[3]['event_001_output_xyz_hash'] == branch[3]['event_001_output_xyz_hash']
    assert root[3]['event_001_output_face_hash'] == branch[3]['event_001_output_face_hash']
    assert root[2][0] == branch[2][0]
    assert root[3]['accepted_event_counts_by_level'][0] == 1
    assert np.array_equal(root[3]['accepted_event_counts_by_level'][1:], [0, 0])


def test_all_outputs_are_closed_oriented_one_body_with_no_orphans(built):
    for out, chart, events, evidence in built[2].values():
        topology = growth.topology(out)
        assert len(out.xyz)-len(topology['edges'])+len(out.faces) == 2
        assert len(np.unique(out.faces)) == len(out.xyz)
        assert out.faces.shape[1] == 4 and np.isfinite(out.xyz).all()
        assert out.surface == 'mean' and out.generation == 3
        assert evidence['subdivision_passes_added'] == 0
        assert_vertex_link_cycles(out)


def test_actual_vertex_and_oriented_face_reflection_use_identity_even_when_chart_duplicates(built):
    for out, chart, events, evidence in built[2].values():
        assert len(np.unique(chart, axis=0)) < len(chart)
        for axis, name in enumerate(('x', 'y')):
            pair = evidence['mirror_'+name+'_vertex_pairs']
            assert np.array_equal(pair[pair], np.arange(len(pair)))
            sign = np.ones(3); sign[axis] = -1.
            assert np.array_equal(out.xyz, out.xyz[pair]*sign)
            assert np.array_equal(growth._canonical_polygons(out.faces),
                                  growth._canonical_polygons(pair[out.faces[:, ::-1]]))
            faces = evidence['mirror_'+name+'_face_pairs']
            assert np.array_equal(faces[faces], np.arange(len(faces)))
            seam = np.abs(chart[:, axis+1]) == 0.
            assert np.array_equal(pair[seam], np.flatnonzero(seam))
            assert np.all(out.xyz[seam, axis] == 0.)


def test_descendants_are_actual_parent_cap_faces_and_rings_keep_source_chart(built):
    out, chart, events, evidence = built[2]['BRANCHED']
    assert evidence['accepted_event_counts_by_level'][1] == 3
    accepted = {event['event_id']: event for event in events if event['status'] == 'accepted'}
    for event in events:
        if event['status'] == 'rejected':
            assert event.get('reason')
            continue
        key = f'event_{event["event_id"]:03d}_'
        assert len(evidence[key+'selected_input_faces']) >= 2
        if event['level']:
            assert np.all(evidence[key+'selected_parent_roles'] == 2)
            assert np.all(evidence[key+'selected_parent_event_ids'] == event['parent_event_id'])
            assert event['parent_event_id'] in accepted
            tokens = set(event['proposal']['selected_tokens'])
            assert tokens <= set(accepted[event['parent_event_id']]['generated_cap_tokens'])
        assert len(evidence[key+'ring_source_vertex_ids']) == 3*event['boundary_vertices']
    assert any(event['level'] == 2 for event in events)
    assert np.all(out.classes[evidence['vertex_birth_event_ids'] > 0] == -1)
    assert len(evidence['face_roles']) == len(out.faces)


def test_tiny_support_is_rejected_explicitly_instead_of_selecting_ids(monkeypatch):
    source, chart = box_grid(4, 8)
    with pytest.raises(ValueError, match='insufficient|disk Euler'):
        growth.build(source, chart, 'ROOT_ONLY')
    source, chart = box_grid(8, 32)
    recipe = copy.deepcopy(growth.RECIPE)
    recipe['minimum_patch_faces'] = 8
    # Force enough root support but reject its smaller actual-cap descendants.
    recipe['root_parameter_halfwidth'] = .14
    recipe['root_cross_halfwidth'] = .35
    monkeypatch.setattr(growth, 'RECIPE', recipe)
    out, out_chart, events, evidence = growth.build(source, chart, 'BRANCHED')
    rejected = [event for event in events if event['status'] == 'rejected']
    assert rejected and all(event.get('reason') for event in rejected)
    assert evidence['accepted_event_counts_by_level'][1] == 0
    assert np.array_equal(evidence['mirror_x_vertex_pairs'][evidence['mirror_x_vertex_pairs']], np.arange(len(out.xyz)))


def test_cross_seam_cube_and_asymmetric_source_are_rejected():
    from cheshire.reference_subdivision import cube
    source = cube(2.); source.generation = 3
    chart = np.column_stack([(source.xyz[:, 2]+1.)/2., source.xyz[:, :2]])
    with pytest.raises(ValueError, match='crosses'):
        growth.build(source, chart, 'ROOT_ONLY')
    source, chart = box_grid(4, 8)
    source.xyz[0, 0] += .01
    with pytest.raises(ValueError, match='actual XYZ'):
        growth.build(source, chart, 'ROOT_ONLY')
