"""Task23 isolated workers, actual checkpoints, bounded capability exploration."""
import argparse
import json
from collections import Counter, defaultdict
from copy import deepcopy
from math import acos, degrees, dist
from pathlib import Path
import shutil
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
for folder in ('rhino', 'examples', 'tools'):
    sys.path.insert(0, str(ROOT/folder))
from compas.datastructures import Mesh
from cheshire import inspect_mesh, save_mesh
from cheshire.artifact_root import ArtifactRoot
from cheshire.creases import CreaseNetwork, CreaseEdge, canonical, crease_subdivide_once, edge_key
from cheshire.crease_routing import CreaseRouter, unit, dot
from cheshire.crease_policy import assess_contact_policy
from cheshire.execution import ExecutionBudget
from cheshire.gate_integrity import GateIntegrityMonitor
from cheshire.lineage import ParentRef
from cheshire.ornament import source_history, propagate_history, select_event_faces, depth_diagnostics
from cheshire.branching import BranchSignatures
from cheshire.vocabulary import VocabularyStage, vocabulary_event
from cheshire_worker import mesh_to_data, RUNTIME_IDENTITY
from branching_process import bounded_worker
from ornament_study import digest, file_hash, gz_write
from beyond_smoothness_verify import read, write
from beyond_smoothness_study import restore_history, can_resume
from beyond_smoothness_diagnostics import observe, stats

BASELINE = '66cb4f90d0b15834d358db5ce2569c813379b0b1'


def raw_mesh(data):
    return Mesh.from_vertices_and_faces({v['id']: v['xyz'] for v in data['vertices']},
        {f['id']: f['vertices'] for f in data['faces']})


def versions():
    import compas
    names = [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'src/cheshire').rglob('*.py'))]
    names += ['rhino/'+n for n in ('cheshire_worker.py', 'exchange.py', 'worker_process.py')]
    names += ['examples/'+n for n in ('cross_cell_crease_study.py', 'beyond_smoothness_study.py',
        'beyond_smoothness_diagnostics.py', 'beyond_smoothness_verify.py', 'ornament_study.py', 'carrier_scale_study.py')]
    names += ['tools/'+n for n in ('branching_process.py', 'crease_crossings.py', 'morphology.py')]
    return dict(COMPAS=compas.__version__, Python=sys.version, source_files={n: file_hash(ROOT/n) for n in names},
        installed_COMPAS_subdivision_sha256=file_hash(ROOT/'.venv/Lib/site-packages/compas/datastructures/mesh/subdivision.py'),
        commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())


def make_request(root, recipe, phase, dll):
    inputs = {p.name: digest(read(p)) for p in root.resolve('inputs').iterdir() if p.suffix in ('.json', '.gz')}
    if recipe.get('composition') and dll is None:
        raise ValueError('Existing composition requires the explicitly supplied official standalone DLL.')
    backend = dict(HDMola_sha256=file_hash(dll), runtime='Existing CoreCLR/.NET8; official external DLL, not distributed.') if recipe.get('composition') else None
    dependencies = {ref: digest(read(root.resolve(ref))) for ref in recipe.get('prepared_substrate', {}).get('assets', {})}
    if dependencies != recipe.get('prepared_substrate', {}).get('assets', {}):
        raise ValueError('Reviewed substrate assets changed; refuse to compose a different checkpoint.')
    return dict(baseline=BASELINE, recipe=recipe, code=versions(), frozen_inputs=inputs, external_backend=backend,
        max_faces=recipe.get('max_faces', 300000), max_vertices=recipe.get('max_faces', 300000)*2,
        contact_cap=256, crossing_sample_faces=4096, mode='EXPLORATION',
        design_policy='User override: contacts diagnostic only; clean preference separate from finite/topology/operator/resource compatibility.',
        phase=phase, substrate_dependencies=dependencies, output_identity='Relative to explicitly configured artifact root')


def prepared_substrate(root, declaration):
    """Load an actual reviewed A/B checkpoint, with independently checked bytes."""
    for ref, sha in declaration['assets'].items():
        if digest(read(root.resolve(ref))) != sha: raise ValueError('Prepared substrate hash mismatch: '+ref)
    if declaration['reviewed_stage']['policy']['hard_stop']:
        raise ValueError('Prepared substrate has a hard geometric/topological boundary.')
    ref=declaration['artifact']; label=declaration['stage']; directory=root.resolve(ref)
    mesh=raw_mesh(read(directory/(label+'.json.gz'))); data=read(directory/(label+'_lineage.json.gz'))
    history=restore_history(data['history']); events=deepcopy(data['events'])
    cells={int(f):row for f,row in data['source_cells'].items()}
    anchors={int(v):p for v,p in data['anchors'].items()}; signature_data=read(directory/(label+'_signatures.json.gz'))
    tracker=BranchSignatures(mesh); paths=[tuple(p) for p in signature_data['paths']]
    tracker.faces={int(f):{paths[p]:w for p,w in refs} for f,refs in signature_data['faces'].items()}
    for event in events:
        tracker.event_counts.update({(*tuple(p['path']),event['operator']+':'+c['role'])
            for p in event.get('parent_branch_signatures',[]) for c in event['children']})
    networks=tuple(CreaseNetwork.from_data(n) for n in read(directory/(label+'_networks.json')))
    if set(history)!=set(cells) or set(cells)!=set(tracker.faces) or set(cells)!=set(mesh.faces()):
        raise ValueError('Prepared substrate history/signature coverage mismatch.')
    actual_edges={edge_key(e) for e in mesh.edges()}
    if any(e.vertices not in actual_edges for n in networks for e in n.edges):
        raise ValueError('Prepared crease edge is absent from its actual mesh.')
    return mesh,history,events,cells,anchors,tracker,networks


def task22_motif_ancestry(root):
    # The saved Task22 point record names actual C07 input vertices. Associate
    # those observed topology classes, not a guessed semantic motif lineage.
    from cheshire.sharp_subdivision import topology_motifs
    original=raw_mesh(read(root.resolve('inputs/BACKBONE_S05.json.gz')))
    classes=topology_motifs(original)
    metadata=read(root.resolve('inputs/TASK22_HERO_G1_operator.json.gz'))
    return {r['point']:tuple(sorted({'Task22-input-'+classes[v].key() for v in r['input_vertices']}))
        for r in metadata['motif_applications']}


def load(root, name):
    if name.startswith('control_'):
        mesh = raw_mesh(read(root.resolve('inputs/'+name+'.json')))
        return mesh, mesh, source_history(mesh), [], {f: [f] for f in mesh.faces()}, {}, BranchSignatures(mesh)
    source = raw_mesh(read(root.resolve('inputs/C0.json')))
    if name == 'C07':
        geometry = 'BACKBONE_S05.json.gz'; lineage = 'BACKBONE_S05_lineage.json.gz'; signatures = 'BACKBONE_S05_signatures.json.gz'; anchors = 'C07_anchors.json'
    elif name == 'TASK22_SHARP':
        geometry = 'TASK22_HERO_terminal.json'; lineage = 'TASK22_HERO_terminal_lineage.json.gz'; signatures = 'TASK22_HERO_terminal_signatures.json.gz'; anchors = 'C07_anchors.json'
    elif name == 'ORDERED':
        geometry = 'TASK21_ORDERED.json'; lineage = 'TASK21_ORDERED_lineage.json.gz'; signatures = 'ORDERED_CORE_signatures.json.gz'; anchors = 'TASK21_ORDERED_anchors.json'
    elif name == 'TASK22_BOUNDARY':
        geometry = 'TASK22_BOUNDARY_terminal.json'; lineage = 'TASK22_BOUNDARY_terminal_lineage.json.gz'; signatures = 'TASK22_BOUNDARY_terminal_signatures.json.gz'; anchors = 'C07_anchors.json'
    else:
        raise ValueError('Unknown frozen substrate.')
    mesh = raw_mesh(read(root.resolve('inputs/'+geometry))); data = read(root.resolve('inputs/'+lineage))
    history = restore_history(data['history']); events = deepcopy(data['events'])
    cells = {int(f): row for f, row in data.get('source_cells', {}).items()}
    if not cells:
        cells = {f: [f] for f in raw_mesh(read(root.resolve('inputs/BACKBONE_S05.json.gz'))).faces()}
        if name == 'ORDERED':
            for i in range(6, 13):
                parents = read(root.resolve(f'inputs/ORDERED_S{i:02d}_lineage.json.gz'))['face_parents']
                cells = {int(f): sorted({c for p in refs for c in cells[p['id']]}) for f, refs in parents.items()}
    signature_data = read(root.resolve('inputs/'+signatures)); paths = [tuple(p) for p in signature_data['paths']]
    tracker = BranchSignatures(mesh)
    tracker.faces = {int(f): {paths[p]: w for p, w in refs} for f, refs in signature_data['faces'].items()}
    for event in events:
        if name == 'ORDERED' and event['stage_index'] >= 11:
            continue
        tracker.event_counts.update({(*tuple(p['path']), event['operator']+':'+c['role'])
            for p in event.get('parent_branch_signatures', []) for c in event['children']})
    if name == 'ORDERED':
        for i in (11, 12):
            parents = read(root.resolve(f'inputs/ORDERED_S{i:02d}_lineage.json.gz'))['face_parents']
            tracker.advance({int(f): [ParentRef(p['id'], p['weight']) for p in refs] for f, refs in parents.items()},
                dict(events=[e for e in events if e['stage_index'] == i]))
    assert set(history) == set(cells) == set(tracker.faces) == set(mesh.faces())
    anchor_map = {int(v): p for v, p in read(root.resolve('inputs/'+anchors)).items() if mesh.has_vertex(int(v))}
    return mesh, source, history, events, cells, anchor_map, tracker


def crossing(root, directory, geometry, label, source):
    directory.mkdir(parents=True, exist_ok=True); start = perf_counter()
    faces = geometry['faces']; sample = faces if len(faces) <= 4096 else [faces[i*len(faces)//4096] for i in range(4096)]
    used = {v for f in sample for v in f['vertices']}
    write(directory/'request.json', dict(mesh=source))
    write(directory/'response.json', dict(variants=[dict(id=label, mesh=dict(vertices=[v for v in geometry['vertices'] if v['id'] in used], faces=sample))]))
    process = bounded_worker([ROOT/'tools/crease_crossings.py', directory, '--cap', 256], directory/'logs', 120)
    write(directory/'process.json', process)
    if process['exit_code']:
        raise ValueError('Contact diagnostic process failed; checkpoint retained, no further growth.')
    result = read(directory/'crossing_audit.json')['candidates'][0]
    result.update(sampled_faces=len(sample), total_faces=len(faces), cap=256,
        scope='Deterministic ordered subset, adjacent/coplanar contacts excluded; no global collision certificate.',
        diagnostic_wall_seconds=perf_counter()-start)
    return result


def network_metrics(mesh, networks, threshold=20.):
    normals = {f: mesh.face_normal(f) for f in mesh.faces()}; result = []
    for net in networks:
        visible = []; angles = []; all_length = 0.
        for e in net.edges:
            a, b = mesh.edge_faces(e.vertices); length = mesh.edge_length(e.vertices); all_length += length
            angle = degrees(acos(dot(normals[a], normals[b]))) if all(sum(x*x for x in normals[f]) > .5 for f in (a, b)) else None
            if angle is not None: angles.append(angle)
            if angle is not None and angle >= threshold: visible.append((e.vertices, length, angle))
        adjacency = defaultdict(set)
        for i, (edge, length, angle) in enumerate(visible):
            for v in edge: adjacency[v].add(i)
        unseen = set(range(len(visible))); components = []
        while unseen:
            seed = min(unseen); stack = [seed]; found = {seed}; unseen.remove(seed)
            while stack:
                i = stack.pop()
                for v in visible[i][0]:
                    new = adjacency[v] & unseen; unseen.difference_update(new); found.update(new); stack.extend(sorted(new))
            components.append(sum(visible[i][1] for i in found))
        data = net.to_data(); weights = [e.sharpness for e in net.edges]
        result.append(dict(network_id=net.network_id, generation=net.generation, parent_cell_count=len(data['parent_cell_ancestry']),
            C0_face_count=len(data['c0_ancestry']), cross_cell=data['cross_cell'], geometric_length=all_length,
            surviving_sharp_edges=sum(w > 0 for w in weights), mean_sharpness=sum(weights)/len(weights), max_sharpness=max(weights),
            junctions=len(net.junction_vertices), dihedral=stats(angles), visible_threshold_degrees=threshold,
            high_dihedral_length=sum(v[1] for v in visible), visible_crease_survival_ratio=sum(v[1] for v in visible)/all_length if all_length else None,
            longest_high_dihedral_chain_length=max(components, default=0.), high45_edge_count=sum(a >= 45 for a in angles),
            note='Declared-route adjacent-normal contrast, not occlusion-aware visibility or an aesthetic score.'))
    return result


def terminal_networks(old, new, networks, corner_parents):
    """Retain only proved unchanged corner copies; no event crease invention."""
    copies = defaultdict(list)
    for v, parent in corner_parents.items():
        if parent is not None and old.has_vertex(parent) and new.vertex_coordinates(v) == old.vertex_coordinates(parent):
            copies[parent].append(v)
    known = {edge_key(e) for e in new.edges()}; rows = []; reports = []
    for net in networks:
        retained = []; lost = []
        for edge in net.edges:
            candidates = {edge_key((a, b)) for a in copies[edge.vertices[0]] for b in copies[edge.vertices[1]] if a != b and edge_key((a, b)) in known}
            if len(candidates) == 1:
                e = candidates.pop(); retained.append(CreaseEdge(e, edge.sharpness, edge.vertices, edge.root_edge, edge.parent_cells, edge.c0_faces, edge.motif_ancestry))
            else: lost.append(dict(edge=list(edge.vertices), reason='missing/ambiguous unchanged source edge'))
        # Event operations may sever a graph: keep connected fragments with explicit IDs.
        remaining = {e.vertices: e for e in retained}; adjacency = defaultdict(set)
        for e in retained:
            for v in e.vertices: adjacency[v].add(e.vertices)
        fragments = []
        while remaining:
            seed = min(remaining); stack = [seed]; component = []
            while stack:
                key = stack.pop()
                if key not in remaining: continue
                e = remaining.pop(key); component.append(e)
                for v in key: stack.extend(sorted(adjacency[v] & remaining.keys()))
            component.sort(key=lambda e: e.vertices); fragments.append(component)
        for i, fragment in enumerate(fragments):
            name = net.network_id if len(fragments) == 1 else net.network_id+f'/retained-{i:03d}'
            rows.append(CreaseNetwork(name, net.seed_rule_json, tuple(fragment), net.generation,
                sum(new.edge_length(e.vertices) for e in fragment), net.routing_json))
        reports.append(dict(network_id=net.network_id, retained_edges=len(retained), affected_edges=lost,
            semantics='Only exact unchanged constructive corner copies and verified output edges retained. Crease semantics on affected event derivatives NOT IMPLEMENTED.'))
    return tuple(rows), reports


def choose_faces(mesh, source, history, networks, declaration, events):
    eligibility = select_event_faces(mesh, history, declaration.get('selector', {}), source)
    selected = eligibility['selected_ids']
    network_edges = {e.vertices for n in networks for e in n.edges}
    adjacent = {f for e in network_edges for f in mesh.edge_faces(e)}
    junctions = {v for n in networks for v in n.junction_vertices}
    junction_faces = {f for v in junctions for f in mesh.vertex_faces(v)}
    distance = {f: 0 for f in (junction_faces if declaration.get('placement') == 'JUNCTION' else adjacent)}
    frontier = sorted(distance)
    for hop in range(1, declaration.get('hops', 2)+1):
        new = {g for f in frontier for g in mesh.face_neighbors(f)} - distance.keys()
        for f in new: distance[f] = hop
        frontier = sorted(new)
    # Seed nested children from actual event identity, rather than reselecting the whole cage.
    parent_stage = declaration.get('parent_stage')
    if parent_stage:
        eligible = {c['id'] for e in events if e['stage'] == parent_stage for c in e['children'] if c['role'] == declaration['parent_role'] and mesh.has_face(c['id'])}
        selected = [f for f in selected if f in eligible]
    else:
        selected = [f for f in selected if f in distance]
    if declaration.get('quad_only', True): selected = [f for f in selected if len(mesh.face_vertices(f)) == 4]
    source_side=declaration.get('source_side')
    if source_side:
        xx=[source.vertex_coordinates(v)[0] for v in source.vertices()]; center=(min(xx)+max(xx))/2
        def side(f):
            value=sum(source.face_centroid(c)[0]*w for c,w in history[f]['source'].items())-center
            return 'left' if value < -1e-8 else 'right' if value > 1e-8 else 'center'
        selected=[f for f in selected if side(f)==source_side]
    count = declaration.get('max_events', 48)
    selected.sort(key=lambda f: (distance.get(f, 0), -mesh.face_area(f), f))
    if declaration.get('stratify_by')=='C0_FACE':
        # Round-robin source cohorts distribute a sparse count over the route;
        # rank within each cohort stays unchanged. No terminal face IDs supplied.
        groups=defaultdict(list)
        for f in selected:
            c=max(history[f]['source'],key=lambda c:(history[f]['source'][c],-c)); groups[c].append(f)
        selected=[groups[c][i] for i in range(max(map(len,groups.values()),default=0)) for c in sorted(groups) if i<len(groups[c])]
    if declaration.get('spacing', 0):
        kept = []; blocked = set()
        for f in selected:
            if f in blocked: continue
            kept.append(f); blocked.add(f)
            blocked.update(mesh.face_neighbors(f))
            if len(kept) >= count: break
        selected = kept
    else: selected = selected[:count]
    return selected, dict(declaration=declaration, eligible_in_band=len(distance), selected_ids=selected,
        eligibility_excluded_counts=eligibility['excluded_counts'],
        policy='Source eligibility, network adjacency/junction graph band, descending existing face area, deterministic ID tie; no hand-picked terminal faces.')


def one(root, reference, request, dll):
    directory = root.resolve(reference); directory.mkdir(parents=True, exist_ok=False)
    write(directory/'request.json', request); write(directory/'worker_identity.json', RUNTIME_IDENTITY)
    for name, sha in request['code']['source_files'].items():
        if file_hash(ROOT/name) != sha: raise ValueError('First-party source changed before worker: '+name)
    for name, sha in request['frozen_inputs'].items():
        if digest(read(root.resolve('inputs/'+name))) != sha: raise ValueError('Frozen input changed: '+name)
    if request['external_backend'] and file_hash(dll) != request['external_backend']['HDMola_sha256']:
        raise ValueError('Official backend fingerprint changed.')
    recipe = request['recipe']; mesh, source, history, events, cells, anchors, tracker = load(root, recipe['input'])
    prepared=recipe.get('prepared_substrate')
    prepared_networks=()
    if prepared:
        if recipe['generations'] != 0: raise ValueError('Prepared composition must not silently repeat CC generations.')
        mesh,history,events,cells,anchors,tracker,prepared_networks=prepared_substrate(root,prepared)
    original_mesh = mesh; original = deepcopy(mesh.__data__); source_data = mesh_to_data(mesh)
    monitor = None if recipe['input'].startswith('control_') else GateIntegrityMonitor(source)
    budget = ExecutionBudget(request['max_faces'], request['max_vertices'], 48)
    networks = (); records = []; started = perf_counter(); failed = None; cap_seen = False; stages_after_cap = 0
    prefix = 'INPUT'; state = 'UNMEASURED'; last_design_eligible = False; last_usable = False

    def retain(label, metadata, parents=None, vertex_parents=None, operator_seconds=0.):
        nonlocal state, cap_seen, stages_after_cap, last_design_eligible, last_usable
        serialization_start = perf_counter(); geometry = mesh_to_data(mesh)
        gz_write(directory/(label+'.json.gz'), geometry)
        gz_write(directory/(label+'_lineage.json.gz'), dict(history=history, events=events, source_cells=cells,
            face_parents=parents, vertex_parents=vertex_parents, anchors=anchors))
        gz_write(directory/(label+'_signatures.json.gz'), tracker.to_data())
        write(directory/(label+'_networks.json'), [n.to_data() for n in networks])
        gz_write(directory/(label+'_operator.json.gz'), metadata)
        serialization_seconds = perf_counter()-serialization_start
        diagnostics = observe(mesh, cells, source_history=history)
        audit = crossing(root, directory/('audit_'+label), geometry, label, source_data)
        catastrophic = len(diagnostics['degenerate_fan_faces']) >= max(8, int(.01*mesh.number_of_faces())) or diagnostics['distributions']['face_area']['max'] <= 0
        valid = mesh.is_valid() and mesh.is_manifold() and mesh.is_closed() and diagnostics['components'] == 1
        if cap_seen: stages_after_cap += 1
        policy = assess_contact_policy(audit['sampled_transverse_crossings'], cap_reached=audit['sample_limit_reached'],
            valid=valid, catastrophic=catastrophic, stages_after_cap=stages_after_cap)
        cap_seen = cap_seen or audit['sample_limit_reached']
        last_design_eligible = policy['design_eligible'] and not diagnostics['degenerate_fan_faces']
        last_usable = policy['capability_usable']
        state = 'HARD_STOP' if policy['hard_stop'] else policy['capability_state']
        row = dict(stage=label, statistics=inspect_mesh(mesh), geometry_sha256=digest(geometry), geometry_state=state,
            diagnostics=diagnostics, crossings=audit, policy=policy, design_eligible=last_design_eligible,
            networks=network_metrics(mesh, networks), operator_seconds=operator_seconds,
            collision_seconds=audit['diagnostic_wall_seconds'], serialization_seconds=serialization_seconds,
            cumulative_seconds=perf_counter()-started)
        if monitor: row['monitor'] = monitor.evaluate(mesh, anchors, generation=len(records))
        records.append(row)
        write(directory/'summary.json', dict(status='RUNNING', request_sha256=digest(request), recipe=recipe, stages=records))
        print(recipe['id'], label, mesh.number_of_faces(), state, round(perf_counter()-started, 2), flush=True)
        if policy['stop']: raise ValueError('Retained checkpoint reached explicit capability stopping policy.')

    try:
        if prepared:
            from types import SimpleNamespace
            p=[source.vertex_coordinates(v) for v in source.vertices()]
            router=SimpleNamespace(center=[(min(q[a] for q in p)+max(q[a] for q in p))/2 for a in range(3)])
            networks=prepared_networks
            retain('SUBSTRATE',dict(reviewed_substrate=prepared,reference='Actual reviewed crease checkpoint; original declaration and CC history retained in referenced source.'))
        else:
            motifs=task22_motif_ancestry(root) if recipe['input']=='TASK22_SHARP' else None
            router = CreaseRouter(mesh, source, history, cells, events,motifs=motifs)
            networks = tuple(router.generate(spec, 'network-'+str(i+1)) for i, spec in enumerate(recipe['networks']))
            retain('G0', dict(routing=[n.to_data() for n in networks], reference='Declared path before geometry refinement'))
        for generation in range(recipe['generations']):
            t = perf_counter()
            schedule=recipe.get('fold_schedule')
            if schedule is not None:
                if len(schedule)!=recipe['generations']:
                    raise ValueError('Fold schedule must explicitly cover every generation.')
                from cheshire.crease_folding import folded_crease_once
                step=folded_crease_once(mesh,networks,schedule[generation],mode=recipe['mode'],budget=budget,current_generation=generation)
            else:
                step = crease_subdivide_once(mesh, networks, mode=recipe['mode'], budget=budget, current_generation=generation)
            seconds = perf_counter()-t
            parents = {r['id']: [ParentRef(r['source_face'], 1.)] for r in step.metadata['face_sources']}
            history = propagate_history(history, parents)
            cells = {f: sorted({c for p in refs for c in cells[p.key]}) for f, refs in parents.items()}
            tracker.advance(parents, {})
            mesh = step.mesh; networks = step.networks
            anchors = {v: anchors.get(v) for v in mesh.vertices() if anchors.get(v) is not None}
            retain('G'+str(generation+1), step.metadata,
                {f: [dict(id=p.key, weight=p.weight) for p in refs] for f, refs in parents.items()}, step.sampling_parents, seconds)
        expected=recipe.get('expected_substrate')
        if expected and (digest(mesh_to_data(mesh)) != expected['geometry_sha256']
                or digest([n.to_data() for n in networks]) != expected['networks_sha256']
                or digest(json.loads(canonical(tracker.to_data()))) != expected['signatures_sha256']):
            raise ValueError('Independent crease-prefix replay differs from reviewed substrate; no downstream composition.')
        for i, declaration in enumerate(recipe.get('composition', []), 1):
            if not last_usable:
                raise ValueError('Composition blocked by a hard geometry/topology boundary, not contacts.')
            selected, selection = choose_faces(mesh, source, history, networks, declaration, events)
            if not selected: raise ValueError('Empty deterministic design selector; no invented event geometry.')
            stage = VocabularyStage(declaration['id'], declaration['operator'], declaration['parameters'], {})
            routes = None
            if stage.operator == 'Roof':
                route_edges = [e.vertices for n in networks for e in n.edges]
                routes = {}
                for f in selected:
                    center = mesh.face_centroid(f)
                    edge = min(route_edges, key=lambda e: (dist(center, [(mesh.vertex_coordinates(e[0])[a]+mesh.vertex_coordinates(e[1])[a])/2 for a in range(3)]), e))
                    tangent = unit([mesh.vertex_coordinates(edge[1])[a]-mesh.vertex_coordinates(edge[0])[a] for a in range(3)])
                    routes[(stage.id, f)] = dict(common_directional_basis=tangent, centerline=router.center[0],
                        basis_policy='Closest declared current edge tangent; existing winding-preserving constructor-axis choice')
            t = perf_counter(); old = mesh
            step = vocabulary_event(mesh, history, stage, selected_faces=selected, dll_path=str(dll),
                budget=budget, stage_index=recipe.get('composition_stage_base',recipe['generations']+12)+i, routes=routes,
                allow_large_taper=recipe.get('policy_override',False))
            seconds = perf_counter()-t; parents = step['lineage'].face_parents
            networks, network_report = terminal_networks(old, step['mesh'], networks, step['corner_parents'])
            cells = {f: sorted({c for p in refs for c in cells[p.key]}) for f, refs in parents.items()}
            anchors = {v: anchors.get(p) for v, p in step['corner_parents'].items() if anchors.get(p) is not None}
            tracker.advance(parents, dict(events=step['events']))
            mesh = step['mesh']; history = step['history']; events.extend(step['events'])
            retain('E'+str(i), dict(declaration=declaration, selection=selection, events=step['events'], backend=step['backend'],
                terminal_crease_contract=network_report),
                {f: [dict(id=p.key, weight=p.weight) for p in refs] for f, refs in parents.items()},
                {v: [[p.key, p.weight] for p in refs] for v, refs in step['lineage'].vertex_parents.items()}, seconds)
    except (ValueError, ArithmeticError) as error:
        failed = str(error)
    geometry = mesh_to_data(mesh); write(directory/'terminal.json', geometry); save_mesh(mesh, directory/'terminal.obj')
    gz_write(directory/'terminal_lineage.json.gz', dict(history=history, events=events, source_cells=cells, anchors=anchors))
    gz_write(directory/'terminal_signatures.json.gz', tracker.to_data()); write(directory/'terminal_networks.json', [n.to_data() for n in networks])
    write(directory/'branch_signatures.json', tracker.diagnostics(history, events))
    artifacts = {p.name: file_hash(p) for p in directory.iterdir() if p.is_file() and p.name != 'summary.json'}
    write(directory/'summary.json', dict(status='TECHNICAL_STOP' if failed else 'SUCCESS', reason=failed or 'Requested finite recipe completed',
        geometry_state=state, design_eligible=last_design_eligible, recipe=recipe, request_sha256=digest(request), stages=records,
        terminal_statistics=inspect_mesh(mesh), output_sha256=digest(geometry), runtime_seconds=perf_counter()-started,
        source_immutable=original_mesh.__data__ == original, artifacts=artifacts, ornament=depth_diagnostics(history, events)))


def execute(root, ids, phase, dll):
    for name in ids:
        if shutil.disk_usage(root.path).free < 12*1024**3:
            raise ValueError('External disk below12GiB safety floor; no fallback.')
        recipe = read(root.resolve('study/recipes/'+name+'.json')); request = make_request(root, recipe, phase, dll)
        base = root.resolve('study/'+phase+'/'+name); attempts = sorted(base.glob('attempt_*')) if base.exists() else []
        if any(can_resume(p, request) for p in attempts):
            print(name, 'RESUME verified', flush=True); continue
        for relative, sha in request['code']['source_files'].items():
            destination = root.resolve('cache/source_snapshots/'+sha+'/'+relative)
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT/relative, destination)
        directory = base/f'attempt_{len(attempts)+1:03d}'; ref = root.reference(directory)
        req = root.resolve('study/requests/'+phase+'/'+name+'.json'); write(req, request)
        args = [Path(__file__).resolve(), '--worker', ref, '--request', root.reference(req), '--output-root', root.path]
        if dll is not None: args += ['--dll', dll]
        process = bounded_worker(args, root.resolve('logs/'+phase+'/'+name+'_'+directory.name), 900)
        if not (directory/'summary.json').exists(): write(directory/'summary.json', dict(status='PROCESS_STOP', reason='See stderr', stages=[]))
        summary = read(directory/'summary.json'); summary['process'] = process
        if process['exit_code']:
            summary.update(status='PROCESS_STOP', reason=process['stop'] or 'Worker exception; see stderr')
        write(directory/'summary.json', summary)
        print(name, summary['status'], summary.get('geometry_state'), round(process['seconds'], 2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--phase', default='CONTROL'); parser.add_argument('--run', nargs='+')
    parser.add_argument('--worker'); parser.add_argument('--request'); parser.add_argument('--dll', type=Path)
    args = parser.parse_args(); root = ArtifactRoot(args.output_root)
    if args.worker: one(root, args.worker, read(root.resolve(args.request)), args.dll)
    elif args.run: execute(root, args.run, args.phase, args.dll)
    else: parser.error('Choose --worker or --run')
