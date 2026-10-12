"""One authored connected ornament sequence on the actual current SPAN G6.

Reuses Task32 disk sweeps. This is design placement, not a parameter search or
another subdivision generation. The preserved parent remains read-only.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE = Path('E:/CHESHIRE_DATA/experiments/directional_g6_20261013/trial01/DEPTH_08/SPAN/G06')
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/design_one_20261013/trial01')
sys.path.insert(0, str(REPO/'src'))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


core = module('design_one_core', HERE.parent/'connected_fold_growth_20261012/study.py')
mirror = module('design_one_mirror', HERE.parent/'connected_fold_growth_20261012/verify.py')
sweep = module('design_one_sweep', HERE/'batch_sweep.py')
digest, write = mirror.digest, core.write


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def arrays(path, keys):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in keys}


def load_parent():
    info = read(SOURCE/'generation.json')
    if (info['subdivision_generation'] != 6 or info['candidate'] != 'DEPTH_08'
            or info['input_case'] != 'SPAN' or not info['checks']['passed']
            or not info['quick_symmetry']['passed']):
        raise ValueError('Actual current verified SPAN DEPTH_08 G6 required.')
    for name, key in (('control_quad.npz', 'control_file_sha256'),
            ('evidence.npz', 'evidence_file_sha256')):
        if digest(SOURCE/name) != info[key]:
            raise ValueError('Preserved parent changed: '+name)
    data = arrays(SOURCE/'control_quad.npz',
        ('xyz', 'faces', 'classes', 'rest', 'anchors', 'chart', 'generation', 'surface'))
    mesh = core.ArrayMesh(data['xyz'], data['faces'], data['classes'], data['rest'],
        data['anchors'], int(data['generation']))
    mesh.surface = str(data['surface'])
    g5 = Path(info['preserved_parent']['path'])
    g4 = Path(info['preserved_parent']['g4']['path'])
    g3 = Path(info['preserved_parent']['g3']['path'])
    ancestry = ((g3, g4), (g4, g5), (g5, SOURCE))
    pairs = arrays(g3/'evidence.npz', ('mirror_x_vertex_pairs', 'mirror_y_vertex_pairs'))
    pairs = dict(X=pairs['mirror_x_vertex_pairs'], Y=pairs['mirror_y_vertex_pairs'])
    for incoming, outgoing in ancestry:
        faces = arrays(incoming/'control_quad.npz', ('faces',))['faces']
        edges = arrays(outgoing/'evidence.npz', ('input_edges',))['input_edges']
        pairs = {axis: mirror.refine_mirror_pairs(faces, edges, pair)
            for axis, pair in pairs.items()}
        del faces, edges
    face_pairs = {axis: mirror.face_involution(mesh.faces, pair)
        for axis, pair in pairs.items()}
    evidence = arrays(SOURCE/'evidence.npz', ('input_face_support', 'parent_face'))
    source_faces = evidence['input_face_support'][evidence['parent_face']] == 0
    return mesh, data['chart'], source_faces, pairs, face_pairs, info


# Authored positions descending from the current shoulder into adjoining body.
# Domain: material height t, half-height, quadrant angle, half-angle.
DOMAINS = ((.70, .035, .94, .20), (.625, .028, .86, .18), (.55, .026, 1.12, .16))


def select(mesh, chart, domain, allowed):
    ids = np.asarray(allowed, np.int64)
    t, ht, angle, ha = domain
    selected = []
    for start in range(0, len(ids), 100000):
        chunk = ids[start:start+100000]
        points = chart[mesh.faces[chunk]]
        c = points.mean(1)
        a = np.arctan2(c[:, 2], c[:, 1])
        score = ((c[:, 0]-t)/ht)**2+((a-angle)/ha)**2
        selected.append(chunk[(score < 1.) & np.all(points[:, :, 1:] > 1e-11, axis=(1, 2))])
    result = np.concatenate(selected)
    if len(result) < 16:
        raise ValueError('Authored disk has insufficient faces.')
    return result


def spec(level, index):
    height = ((.78, .66, .76)[index % 3] if level == 0 else (1.08 if level == 1 else 1.0))
    fraction = np.linspace(.08, 1., 9)
    # Dense longitudinal rings retain a rounded root and narrowing termination.
    scales = 1.-(.52 if level == 0 else .62)*fraction**1.25
    return dict(direction=[0., 0., 1.], heights=(height*fraction).tolist(),
        scales=scales.tolist(), bend=.40 if level == 0 else .32,
        twist=(.08 if index % 2 == 0 else -.08), projection_guard=False)


def child_domains(domain, level):
    t, ht, a, ha = domain
    if level == 1:
        return [(t+sign*.40*ht, .28*ht, a-sign*.18*ha, .42*ha) for sign in (-1, 1)]
    return [(t+.10*ht, .48*ht, a, .50*ha)]


def actual_symmetry(mesh, state):
    result = {}
    for axis, label, coordinate in (('X', 'x', 0), ('Y', 'y', 1)):
        pair = state['mirror_'+label+'_vertex_pairs']
        face_pair = state['mirror_'+label+'_face_pairs']
        mirror.involution(pair, len(mesh.xyz), axis+' vertices')
        mirror.involution(face_pair, len(mesh.faces), axis+' faces')
        maximum = 0.
        for start in range(0, len(mesh.faces), 100000):
            ids = np.arange(start, min(start+100000, len(mesh.faces)))
            reflected = pair[mesh.faces[ids, ::-1]]
            actual = mesh.faces[face_pair[ids]]
            matches = np.zeros(len(ids), bool)
            for shift in range(4):
                matches |= np.all(actual == np.roll(reflected, shift, axis=1), axis=1)
            if not matches.all():
                raise ValueError('Actual oriented control reflection failed.')
        for start in range(0, len(mesh.xyz), 120000):
            stop = min(start+120000, len(mesh.xyz))
            reflected = mesh.xyz[pair[start:stop]].copy()
            reflected[:, coordinate] *= -1.
            maximum = max(maximum, float(np.linalg.norm(mesh.xyz[start:stop]-reflected, axis=1).max(initial=0.)))
        if not np.isfinite(maximum) or maximum > 1e-9:
            raise ValueError('Actual control XYZ symmetry failed.')
        result[axis] = dict(passed=True, actual_control_xyz_max_error=maximum,
            oriented_control_faces_identical=True, tolerance=1e-9)
    return dict(passed=True, axes=result,
        native_scope='Arithmetic quad-centre fans inherit the verified reflected control cycles; native triangle sets not independently sorted.',
        full_independent_replay='NOT_PERFORMED_THIS_DESIGN_ITERATION')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    folder = root/'DESIGN_A/SPAN/G06_designed'
    if root == SOURCE.resolve() or SOURCE.resolve() in root.parents or folder.exists():
        raise FileExistsError('Preserved result cannot be overwritten.')
    core.memory_guard()
    print('LOAD actual current G6 and saved reflection ancestry', flush=True)
    mesh, chart, source_faces, vp, fp, parent = load_parent()
    hashes = dict(parent['geometry_code_sha256'])
    for path in (HERE/'study.py', HERE/'batch_sweep.py'):
        hashes[str(path.relative_to(REPO))] = digest(path)
    roots = [dict(name='body_root_'+str(i), domain=domain,
        selection=select(mesh, chart, domain, np.flatnonzero(source_faces)), spec=spec(0, i))
        for i, domain in enumerate(DOMAINS)]
    plans, levels, event_start = roots, [], 1
    source_parent = np.arange(len(mesh.faces))
    cumulative_events = np.zeros(len(mesh.faces), np.int64)
    cumulative_roles = np.zeros(len(mesh.faces), np.int8)
    for level in range(3):
        print('APPLY authored level', level, 'canonical disks', len(plans), flush=True)
        out, outchart, metadata, state = sweep.batch_sweep(mesh, chart, plans, vp, fp, event_start)
        source_parent = source_parent[state['parent_face']]
        cumulative_events = cumulative_events[state['parent_face']]
        cumulative_roles = cumulative_roles[state['parent_face']]
        new = state['face_event_ids'] > 0
        cumulative_events[new] = state['face_event_ids'][new]
        cumulative_roles[new] = state['face_roles'][new]
        next_plans = []
        if level < 2:
            for plan, event in zip(plans, metadata['events']):
                for child_index, domain in enumerate(child_domains(plan['domain'], level+1)):
                    next_plans.append(dict(name=plan['name']+'_child_'+str(child_index),
                        domain=domain, spec=spec(level+1, len(next_plans)),
                        selection=select(out, outchart, domain, event['canonical_cap_faces'])))
        levels.append(metadata)
        mesh, chart, plans = out, outchart, next_plans
        vp = dict(X=state['mirror_x_vertex_pairs'], Y=state['mirror_y_vertex_pairs'])
        fp = dict(X=state['mirror_x_face_pairs'], Y=state['mirror_y_face_pairs'])
        event_start += metadata['added_topology_events']
        gc.collect()
    if mesh.generation != 6:
        raise ValueError('Topology events must preserve actual G6.')
    proof = actual_symmetry(mesh, state)
    state.update(source_g6_parent_face=source_parent, design_face_event_ids=cumulative_events,
        design_face_roles=cumulative_roles, implementation=np.array('TASK32_AUTHORED_ATTACHED_SWEEP'))
    count = sum(item['added_topology_events'] for item in levels)
    context = dict(input_case='SPAN', candidate='DESIGN_A', source=str(SOURCE),
        source_control_sha256=parent['control_file_sha256'], source_generation=6,
        source_generation_json_sha256=digest(SOURCE/'generation.json'), geometry_code_sha256=hashes,
        added_CC_passes=0, added_topology_events=count, reflected_event_instances=4*count,
        added_field_passes=0, added_mandelbulb_evaluations=0, operator_levels=levels,
        design_scope='One authored sequence extending shoulder ornament into adjacent SOURCE body with three decreasing attached sweep levels.',
        symmetry=proof, topology_scope='Attached Task32 walls and caps; intersections allowed; no collision repair.',
        methodology_scope='Reuse of existing Task32 sweep, not a new universal growth algorithm or an exact reproduction of a reference.',
        validation_scope='Existing finite/closed-oriented/connected-control/no-orphan/native-area checks once, plus actual oriented-control reflection and XYZ.')
    print('SAVE and required geometry checks', flush=True)
    record = core.save(folder, mesh, chart, context, state)
    if digest(SOURCE/'control_quad.npz') != parent['control_file_sha256']:
        raise ValueError('Read-only parent changed during run.')
    write(root/'SUMMARY.json', dict(candidate='DESIGN_A', source=str(SOURCE),
        subdivision_generation=6, added_CC_passes=0, authored_canonical_events=count,
        reflected_event_instances=4*count, checks=record['checks'], symmetry=proof,
        visual_success='NOT_ASSESSED', generation_json_sha256=digest(folder/'generation.json')))
    print('DONE DESIGN_A actual G6, CC added 0, events', count, flush=True)


if __name__ == '__main__':
    main()
