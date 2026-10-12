"""Finish the same authored G6 design with low roots and sidewall descendants.

One revision, not a parameter search. Reuses the frozen parent loader, Task32
batch sweep, cumulative ancestry and final checks from study.py. Trial01 and
the current DEPTH_08 G6 source remain read-only.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('design_one_finish_study', HERE/'study.py')
study = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = study
_spec.loader.exec_module(study)
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/design_one_20261013/trial02')
FIRST_PASS = Path('E:/CHESHIRE_DATA/experiments/design_one_20261013/trial01')


def root_spec():
    f = np.linspace(.06, 1., 11)
    return dict(direction=[0., 0., 1.], heights=(.38*f).tolist(),
        scales=(1.-.30*f**1.2).tolist(), bend=.30, twist=.04, projection_guard=False)


def descendant_spec(level, index):
    f = np.linspace(.08, 1., 9)
    height, taper, bend = (1.25, .70, .35) if level == 1 else (.95, .68, .25)
    return dict(direction=[0., 0., 1.], heights=(height*f).tolist(),
        scales=(1.-taper*f**1.2).tolist(), bend=bend,
        twist=.06 if index % 2 == 0 else -.06, projection_guard=False)


def disk(mesh, selected, name):
    selected = np.asarray(selected, np.int64)
    try:
        if len(selected) < 2:
            raise ValueError('Fewer than two selected faces.')
        study.sweep.disk_boundary(mesh, selected)
    except ValueError as exc:
        raise ValueError(name+': authored patch is not a valid disk: '+str(exc)) from exc
    return selected


def wall_plans(mesh, metadata):
    plans = []
    for event in metadata['events']:
        nb = int(event['boundary_vertices'])
        nl = len(event['geometry']['actual_heights'])
        cap = np.asarray(event['canonical_cap_faces'], np.int64)
        wall_start = int(cap[0])-nl*nb
        wall = (wall_start+np.arange(nl*nb)).reshape(nl, nb)
        width = max(2, int(round(nb*.11)))
        for slot, fraction in enumerate((.125, .375, .625, .875)):
            centre = int(round(nb*fraction)) % nb
            columns = (centre-width//2+np.arange(width)) % nb
            name = event['name']+'_wall_'+str(slot)
            selection = disk(mesh, wall[2:9, columns].ravel(), name)
            plans.append(dict(name=name, selection=selection,
                spec=descendant_spec(1, len(plans))))
    if len(plans) != 12:
        raise ValueError('Exactly twelve canonical wall children required.')
    return plans


def tip_plans(mesh, metadata):
    plans = []
    for event in metadata['events']:
        cap = np.asarray(event['canonical_cap_faces'], np.int64)
        # The wall child cap retains the actual 7-row rectangular face order.
        # A geometric ellipse can split on a bent wall; use its existing grid.
        if len(cap) % 7:
            raise ValueError(event['name']+': expected actual seven-row wall cap.')
        grid = cap.reshape(7, -1)
        width = grid.shape[1]
        selected = grid[2:5, width//4:width-width//4].ravel()
        name = event['name']+'_tip'
        plans.append(dict(name=name, selection=disk(mesh, selected, name),
            spec=descendant_spec(2, len(plans))))
    if len(plans) != 12:
        raise ValueError('Exactly twelve canonical tips required.')
    return plans


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    folder = root/'DESIGN_A/SPAN/G06_designed'
    if (root == study.SOURCE.resolve() or study.SOURCE.resolve() in root.parents or
            root == FIRST_PASS.resolve() or FIRST_PASS.resolve() in root.parents or folder.exists()):
        raise FileExistsError('Preserved source and first-pass results cannot be overwritten.')
    study.core.memory_guard()
    print('LOAD actual current SPAN DEPTH_08 G6; finish same authored design', flush=True)
    mesh, chart, source_faces, vp, fp, parent = study.load_parent()
    hashes = dict(parent['geometry_code_sha256'])
    for path in (HERE/'study.py', HERE/'batch_sweep.py', Path(__file__).resolve()):
        hashes[str(path.relative_to(study.REPO))] = study.digest(path)
    allowed = np.flatnonzero(source_faces)
    plans = [dict(name='body_root_'+str(i), domain=domain,
        selection=disk(mesh, study.select(mesh, chart, domain, allowed), 'body_root_'+str(i)),
        spec=root_spec()) for i, domain in enumerate(study.DOMAINS)]
    del allowed, source_faces
    source_parent = np.arange(len(mesh.faces))
    cumulative_events = np.zeros(len(mesh.faces), np.int64)
    cumulative_roles = np.zeros(len(mesh.faces), np.int8)
    levels, event_start = [], 1
    for level in range(3):
        print('APPLY finish level', level, 'canonical disks', len(plans), flush=True)
        out, outchart, metadata, state = study.sweep.batch_sweep(mesh, chart, plans, vp, fp, event_start)
        source_parent = source_parent[state['parent_face']]
        cumulative_events = cumulative_events[state['parent_face']]
        cumulative_roles = cumulative_roles[state['parent_face']]
        new = state['face_event_ids'] > 0
        cumulative_events[new] = state['face_event_ids'][new]
        cumulative_roles[new] = state['face_roles'][new]
        metadata['design_level'] = level
        metadata['placement'] = ('same three SOURCE body domains' if level == 0 else
            'four sidewall arc windows per low root' if level == 1 else
            'one central actual-cap grid rectangle per wall child')
        levels.append(metadata)
        next_plans = wall_plans(out, metadata) if level == 0 else tip_plans(out, metadata) if level == 1 else []
        mesh, chart, plans = out, outchart, next_plans
        vp = dict(X=state['mirror_x_vertex_pairs'], Y=state['mirror_y_vertex_pairs'])
        fp = dict(X=state['mirror_x_face_pairs'], Y=state['mirror_y_face_pairs'])
        event_start += metadata['added_topology_events']
        gc.collect()
    count = sum(item['added_topology_events'] for item in levels)
    if mesh.generation != 6 or count != 27:
        raise ValueError('Actual G6 and 27 canonical authored events required.')
    proof = study.actual_symmetry(mesh, state)
    state.update(source_g6_parent_face=source_parent, design_face_event_ids=cumulative_events,
        design_face_roles=cumulative_roles, implementation=np.array('TASK32_AUTHORED_LOW_ROOT_SIDEWALL_FINISH'))
    context = dict(input_case='SPAN', candidate='DESIGN_A', source=str(study.SOURCE),
        source_control_sha256=parent['control_file_sha256'], source_generation=6,
        source_generation_json_sha256=study.digest(study.SOURCE/'generation.json'),
        geometry_code_sha256=hashes, design_revision='LOW_ROOT_SIDEWALL_CHILDREN_V2',
        first_pass_trial01=str(FIRST_PASS), first_pass_trial01_access='READ_ONLY',
        added_CC_passes=0, added_topology_events=count, reflected_event_instances=4*count,
        added_field_passes=0, added_mandelbulb_evaluations=0, operator_levels=levels,
        design_scope='Same three low SOURCE roots; four sidewall children per root and one cap tip per child.',
        placement_rule=dict(root_domains=study.DOMAINS, root_rings=11, wall_child_rings=9,
            root_wall_rows=[2, 9], wall_arc_centres=[.125, .375, .625, .875],
            wall_arc_width_fraction=.11, tip_cap_grid_rows=[2, 5],
            tip_cap_grid_columns='middle half of actual seven-row wall cap'),
        symmetry=proof, topology_scope='Attached Task32 walls and caps; intersections allowed; no collision repair.',
        methodology_scope='Existing Task32 formula and existing design-study ancestry; one authored finish revision.',
        validation_scope='Existing finite/closed-oriented/connected-control/no-orphan/native-area checks once; actual oriented-control and XYZ symmetry once.')
    print('SAVE final once and required geometry checks', flush=True)
    record = study.core.save(folder, mesh, chart, context, state)
    if study.digest(study.SOURCE/'control_quad.npz') != parent['control_file_sha256']:
        raise ValueError('Read-only source changed during finish.')
    study.write(root/'SUMMARY.json', dict(candidate='DESIGN_A', source=str(study.SOURCE),
        design_revision='LOW_ROOT_SIDEWALL_CHILDREN_V2', first_pass_trial01=str(FIRST_PASS),
        first_pass_trial01_access='READ_ONLY', subdivision_generation=6, added_CC_passes=0,
        authored_canonical_events=count, reflected_event_instances=4*count,
        checks=record['checks'], symmetry=proof, visual_success='PENDING_REVIEW',
        generation_json_sha256=study.digest(folder/'generation.json')))
    print('DONE same DESIGN_A actual G6; CC added 0; canonical events', count, flush=True)


if __name__ == '__main__':
    main()
