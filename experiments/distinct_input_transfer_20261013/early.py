"""A different G0 macro mass through unchanged selected G1--G4 operators.

The old transfer adapter is reused as a library, never edited or disguised.
G0 uses existing seed_mass.evaluate instead of the fixed legacy deep fold.
All downstream recipes and geometric functions remain unchanged.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


old = module('distinct_existing_early_adapter', HERE.parent/'recipe_transfer_20261013/early.py')
seed = module('distinct_fixed_input_definition', HERE/'input_seed.py')
CASE = 'CENTRAL_SPINDLE'
STAGES = old.STAGE_IDS


def build(root):
    root = Path(root).resolve()
    folders = {stage: root/'states'/stage for stage in STAGES}
    if any(path.exists() for path in folders.values()):
        raise FileExistsError('Existing early stages are preserved.')
    old.core.memory_guard()
    selected = old.selected_receipts()
    hashes = old.code_hashes()
    hashes.update(seed.code_hashes())
    hashes[str(Path(__file__).resolve().relative_to(REPO)).replace('\\', '/')] = old.digest(__file__)
    records, nodes = {}, []

    def save(stage, mesh, chart, candidate, state, metadata=None, parent=None, pairs=None,
             guides=(), rails=()):
        context = dict(input_case=CASE, candidate=candidate,
            transfer_schema='CHESHIRE_DISTINCT_INPUT_FIXED_DOWNSTREAM_V1',
            geometry_code_sha256=hashes,
            downstream_selected_recipe_receipt=selected[stage]['path'] if stage != 'G00_INPUT' else None,
            downstream_selected_recipe_receipt_sha256=selected[stage]['sha256'] if stage != 'G00_INPUT' else None,
            input_change_scope='G0 macro mass and input-generation recipe changed; all G1--G7 operators/coefficients remain fixed.',
            added_normal_field_passes=0, self_intersection='NOT_CHECKED_EXPLORATORY',
            fabrication='NOT_CHECKED', **(metadata or {}))
        if parent is not None:
            p = folders[parent]
            context.update(source=str(p), source_generation=records[parent]['subdivision_generation'],
                source_control_sha256=records[parent]['control_file_sha256'],
                source_generation_json_sha256=old.digest(p/'generation.json'), parent_stage=str(p))
        record, result = old._save(folders[stage], mesh, chart, context, state,
            pairs=pairs, guides=guides, rails=rails)
        if stage == 'G00_INPUT':
            record['checks']['minimum_native_triangle_area_threshold'] = 1e-12
            if record['checks']['minimum_native_triangle_area'] <= 1e-12:
                record['checks']['passed'] = False
                old.write(folders[stage]/'generation.json', record)
                raise ValueError('Original G0 positive-area threshold failed; no repair.')
            old.write(folders[stage]/'generation.json', record)
        records[stage] = record
        nodes.append(dict(id=stage, folder=str(folders[stage]), generation=int(mesh.generation),
            generation_json_sha256=old.digest(folders[stage]/'generation.json')))
        old.write(root/'STAGES_EARLY.json', dict(schema='CHESHIRE_DISTINCT_EARLY_STAGES_V1',
            input_case=CASE, status='IN_PROGRESS', stages=nodes))
        return result

    mesh, chart, parts, input_recipe = seed.build()
    recipes = dict(input_case=CASE, input_method=seed.INPUT_METHOD,
        original_input_method='seed_mass.legacy_core with fixed inherited deep fold',
        original_input_recipe=selected['G00_INPUT']['metadata']['recipe'], input_recipe=input_recipe,
        carrier=dict(rings=25, sectors=16, radius=.78),
        task36=old.ancestry.RECIPE, overlap_events=old.overlap.EVENTS,
        wall=old.wall.RECIPE, root_event=old.core.patch_growth.RECIPE,
        sidewall_event=old.sidewall.RECIPE,
        field_passes=[dict(iterations=4, fraction=.55, budget=.35, local_target_factor=1),
            dict(iterations=8, fraction=.55, budget=.28, local_target_factor=2)],
        geometry_code_sha256=hashes, workflow=str(old.WORKFLOW), workflow_sha256=old.digest(old.WORKFLOW))
    root.mkdir(parents=True, exist_ok=True)
    old.write(root/'RECIPE_EARLY.json', recipes)
    save('G00_INPUT', mesh, chart, CASE, parts, dict(recipe=input_recipe,
        input_method=seed.INPUT_METHOD, subdivision_passes_total=0,
        input_carrier_bilinear_splits=0, field_passes_total=0))
    mesh, chart, state, metadata = old.ancestry_field(mesh, chart, 1, selected['G01_ANCESTRY'])
    save('G01_ANCESTRY', mesh, chart, 'ANCESTRY_STAGED', state, metadata, 'G00_INPUT')
    del state
    mesh, chart, state, metadata = old.ancestry_field(mesh, chart, 2, selected['G02_OVERLAP'])
    save('G02_OVERLAP', mesh, chart, 'OVERLAP', state, metadata, 'G01_ANCESTRY')
    del state
    mesh, chart, state, metadata, guides, rails = old.wall_stage(mesh, chart)
    save('G03_WALL', mesh, chart, 'WALL', state, metadata, 'G02_OVERLAP', guides=guides, rails=rails)
    del state, guides, rails
    source_surface = mesh.surface
    mesh, chart, events, state = old.core.patch_growth.build(mesh, chart, 'ROOT_ONLY')
    accepted = sum(event['status'] == 'accepted' for event in events)
    if accepted != 1:
        raise ValueError('Fixed root rule failed; no selection retuning.')
    state = save('G03_ROOT', mesh, chart, 'ROOT_ONLY', state,
        dict(event_recipe=old.core.patch_growth.RECIPE, source_surface=source_surface,
            added_topology_events=accepted, constructive_event_count=accepted,
            reflected_constructive_event_instances=4*accepted,
            accepted_canonical_events_by_level=[1, 0, 0], added_field_passes=0,
            added_mandelbulb_evaluations=0, subdivision_passes_added=0), 'G03_WALL')
    old.write(folders['G03_ROOT']/'events.json', events)
    records['G03_ROOT']['events_file_sha256'] = old.digest(folders['G03_ROOT']/'events.json')
    old.write(folders['G03_ROOT']/'generation.json', records['G03_ROOT'])
    nodes[-1]['generation_json_sha256'] = old.digest(folders['G03_ROOT']/'generation.json')
    mesh, chart, events, state = old.sidewall.build(mesh, chart, state, events)
    accepted = sum(event['status'] == 'accepted' for event in events)
    if accepted != 3 or not np.array_equal(state['accepted_event_counts_by_level'], [1, 3, 0]):
        raise ValueError('Fixed sidewall rule failed; no selection retuning.')
    state = save('G03_SIDEWALL', mesh, chart, 'SIDEWALL_FAN', state,
        dict(event_recipe=old.sidewall.RECIPE, source_surface='mean', added_topology_events=accepted,
            constructive_event_count=1+accepted, inherited_canonical_root_events=1,
            new_canonical_sidewall_events=accepted, reflected_constructive_event_instances=4*(1+accepted),
            reflected_new_sidewall_event_instances=4*accepted, accepted_canonical_events_by_level=[1, accepted, 0],
            added_field_passes=0, added_mandelbulb_evaluations=0, subdivision_passes_added=0), 'G03_ROOT')
    old.write(folders['G03_SIDEWALL']/'events.json', events)
    records['G03_SIDEWALL']['events_file_sha256'] = old.digest(folders['G03_SIDEWALL']/'events.json')
    old.write(folders['G03_SIDEWALL']/'generation.json', records['G03_SIDEWALL'])
    nodes[-1]['generation_json_sha256'] = old.digest(folders['G03_SIDEWALL']/'generation.json')
    incoming_faces = mesh.faces
    incoming_pairs = old._pairs(mesh, chart, state)
    mesh, chart, refinement = old.core.refine(mesh, chart)
    pairs = {axis: old.mirror.refine_mirror_pairs(incoming_faces, refinement['input_edges'], pair)
        for axis, pair in incoming_pairs.items()}
    save('G04_NEUTRAL', mesh, chart, 'SIDEWALL_FAN', refinement,
        dict(neutral_CC_passes_added=1, added_CC_passes=1, added_topology_events=0,
            added_field_passes=0, added_mandelbulb_evaluations=0, parent=str(folders['G03_SIDEWALL'])),
        'G03_SIDEWALL', pairs=pairs)
    for name, expected in hashes.items():
        if old.digest(REPO/name) != expected:
            raise ValueError('Generation source changed during actual transfer.')
    old.write(root/'STAGES_EARLY.json', dict(schema='CHESHIRE_DISTINCT_EARLY_STAGES_V1',
        input_case=CASE, status='PASS', stages=nodes, geometry_code_sha256=hashes,
        scope='Different G0 macro mass with unchanged G1--G4 recipe; visual success not assumed.'))
    del mesh, chart, state, refinement, incoming_faces, incoming_pairs
    gc.collect()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    build(parser.parse_args().root)
