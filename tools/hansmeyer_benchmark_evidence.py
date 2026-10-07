"""Freeze one real lineage and check identity, not an automatic beauty score."""
import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / 'examples'), str(REPO / 'tools')]
from hansmeyer_benchmark import restore_state, directory, BASELINE
from cross_cell_crease_study import read, write, file_hash, raw_mesh, mesh_to_data
from generational_folding import verify_obj
from cheshire.sharp_subdivision import sharp_subdivide_once
from cheshire.execution import ExecutionBudget


def ordered_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def freeze(root, name, last):
    target = root / 'lead'
    if (target / 'lineage.json').exists():
        raise ValueError('Preserve the frozen lineage; do not overwrite it.')
    rows = []
    for g in range(last + 1):
        source = root / 'input/G0' if g == 0 else directory(root, name, g)
        for filename in ['geometry.json.gz', 'state.json.gz', 'summary.json', f'G{g}.obj']:
            if not (source / filename).is_file():
                raise ValueError('Incomplete actual stage: ' + str(source))
        if g:
            request = read(source / 'request.json')
            parent = root / 'input/G0' if g == 1 else directory(root, name, g - 1)
            assert request['parent_geometry_sha256'] == file_hash(parent / 'geometry.json.gz')
            assert request['parent_state_sha256'] == file_hash(parent / 'state.json.gz')
        copied = target / f'G{g}'
        if copied.exists():
            # A stopped export may already have copied complete stage bytes.
            # Resume only after proving that every file is the same source.
            assert {p.name for p in source.iterdir()} == {p.name for p in copied.iterdir()}
            assert all(file_hash(p) == file_hash(copied / p.name) for p in source.iterdir())
        else:
            shutil.copytree(source, copied)
        data = read(copied / 'geometry.json.gz')
        state = restore_state(read(copied / 'state.json.gz'))
        assert state['generation'] == g
        mesh = raw_mesh(data)
        assert mesh.is_closed() and mesh.is_connected() and mesh.is_manifold()
        rows.append(dict(generation=g, actual_source=str(source), frozen_copy=str(copied),
                         ordered_geometry_sha256=ordered_hash(data),
                         files={p.name: dict(bytes=p.stat().st_size, sha256=file_hash(p))
                                for p in copied.iterdir() if p.is_file()},
                         OBJ=verify_obj(mesh, copied / f'G{g}.obj')))
    definition = read(root / 'definitions/candidates' / (name + '.json'))
    schedule = [read(target / f'G{g}/summary.json') for g in range(1, last + 1)]
    write(root / 'definitions/generation_weight_schedule.json',
          dict(candidate=name, definition=definition, resolved_stages=schedule,
               policy='Exact actual global weights and current edge-scale offsets. No external smoothing modifier.'))
    write(target / 'lineage.json', dict(candidate=name, final_generation=last, baseline=BASELINE, stages=rows,
          policy='Byte-identical copies of a single complete saved candidate ancestry. Request parents retain original source paths; hashes also identify the copied preceding stage.'))
    (root / 'dcc').mkdir(exist_ok=True)
    shutil.copy2(target / f'G{last}/G{last}.obj', root / 'dcc/lead.obj')
    print('Frozen actual lineage', name, 'G0..G' + str(last), flush=True)


def audit(root):
    lead = read(root / 'lead/lineage.json')
    continuation = []
    # Independently recompute EVERY lead child from the actual reloaded parent.
    # The saved origin classes must reproduce Eq4 without a reconstructed cage.
    for g in range(1, lead['final_generation'] + 1):
        parent = root / 'lead' / f'G{g-1}'
        child = root / 'lead' / f'G{g}'
        m = raw_mesh(read(parent / 'geometry.json.gz'))
        state = restore_state(read(parent / 'state.json.gz'))
        s = read(child / 'summary.json')
        result = sharp_subdivide_once(m, s['resolved_weights'], u_map=s['declared']['u_map'],
                    unknown_u=s['declared']['unknown_u'], origin_lineage=state['origins'],
                    budget=ExecutionBudget(200000, 200000, None), current_generation=g-1)
        assert mesh_to_data(result.mesh) == read(child / 'geometry.json.gz')
        actual = restore_state(read(child / 'state.json.gz'))
        assert result.origin_lineage == actual['origins']
        assert {r['id']: state['face_ancestry'][r['source_face']] for r in result.metadata['face_sources']} == actual['face_ancestry']
        continuation.append(dict(generation=g, exact_ordered_XYZ_oriented_faces=True,
                                 exact_origin_classes=True, exact_coarse_face_ancestry=True,
                                 eq4_eligible=result.metadata['later_generation_face_stencil']['eligible_faces']))
    stages = []; by_generation = defaultdict(set); patches = []
    for d in sorted((root / 'candidates').iterdir()):
        if not d.is_dir():
            continue
        definition = root / 'definitions/candidates' / (d.name + '.json')
        if not definition.is_file():
            continue
        shutil.copy2(definition, d / 'candidate_definition.json')
        for p in sorted(d.glob('G*/summary.json')):
            s = read(p); stage = p.parent; data = read(stage / 'geometry.json.gz')
            h = ordered_hash(data); by_generation[s['generation']].add(h)
            request = read(stage / 'request.json'); parent = Path(request['parent'])
            assert file_hash(parent / 'geometry.json.gz') == request['parent_geometry_sha256']
            assert file_hash(parent / 'state.json.gz') == request['parent_state_sha256']
            for path, sha in request['source_hashes'].items():
                candidates = [REPO / path, root / 'source_snapshots' / sha / path]
                assert any(p.is_file() and file_hash(p) == sha for p in candidates)
            stages.append(dict(candidate=s['candidate'], generation=s['generation'], directory=str(stage),
                 ordered_geometry_sha256=h, vertices=s['statistics']['vertex_count'],
                 faces=s['statistics']['face_count'], dihedral=s['dihedral'],
                 finite=s['coordinates_finite'], zero_area_faces=s['zero_unsigned_fan_faces'],
                 resolved_weights=s['resolved_weights'], OBJ=s['OBJ']))
    captures = []
    for p in sorted((root / 'renders').glob('*/camera_manifest.json')):
        manifest = read(p)
        for row in manifest['records']:
            assert file_hash(Path(row['geometry'])) == row['geometry_sha256']
            assert file_hash(Path(row['image'])) == row['image_sha256']
        captures.append(dict(path=str(p), sha256=file_hash(p), records=manifest['records']))
    for g in range(lead['final_generation'] + 1):
        d = root / 'lead' / f'G{g}'; state = restore_state(read(d / 'state.json.gz'))
        m = raw_mesh(read(d / 'geometry.json.gz'))
        counts = Counter(state['face_ancestry'].values())
        assert set(counts) == set(range(24)) and set(counts.values()) == {4**g}
        patches.append(dict(generation=g, real_coarse_face_descendant_counts=dict(counts),
                            current_valence_histogram=dict(Counter(m.vertex_degree(v) for v in m.vertices())),
                            note='Ancestry confirms where a later patch came from; counts and valence do not by themselves prove hierarchy.'))
    logs = [dict(path=str(p), **read(p)) for p in (root / 'logs').glob('*/process.json')]
    write(root / 'stage_manifest.json', dict(lead=lead, candidate_count=len(set(r['candidate'] for r in stages)),
          candidate_stage_count=len(stages), unique_geometries_by_generation={str(g):len(v) for g,v in by_generation.items()},
          stages=stages, captures=captures))
    write(root / 'analysis/geometry_validation.json', dict(status='PASS', exact_saved_child_replay=continuation,
           patches=patches, all_candidate_coordinates_finite=all(s['finite'] for s in stages),
           all_candidate_unsigned_face_areas_positive=all(s['zero_area_faces']==0 for s in stages),
           captured_geometry_and_image_hashes_verified=True, original_topology_preserved_in_OBJ=True))
    write(root / 'analysis/performance.json', dict(guarded_jobs=len(logs),
          sum_guarded_job_wall_seconds=sum(p['seconds'] for p in logs),
          maximum_sampled_process_tree_plus_driver_bytes=max(p['sampled_peak_tree_plus_driver_bytes'] for p in logs),
          resource_stops=[p for p in logs if p['resource_stop']], jobs=logs,
          scope='Sum of guarded per-job elapsed times, not total interactive sprint elapsed time. Includes renderer jobs and process startup. Tests and native Rhino operation measured separately.'))
    print('Exact saved continuation, parent/source/capture identities PASS;', len(stages), 'actual candidate stages', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output-root', type=Path, required=True)
    p.add_argument('--freeze', action='store_true'); p.add_argument('--lead')
    p.add_argument('--generation', type=int, default=5); p.add_argument('--audit', action='store_true')
    a = p.parse_args()
    if a.freeze:
        freeze(a.output_root, a.lead, a.generation)
    if a.audit:
        audit(a.output_root)
