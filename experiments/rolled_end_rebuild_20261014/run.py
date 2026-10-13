"""Source-guided parametric reconstruction of individual existing SPAN ends.

Current G7 supplies actual geometry and local material coordinates. Individual
existing ends may change shape under the user-approved protrusion/large-flow
constraints. No failed fairing output is used and no small detail is added.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import shutil
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


SOURCE_LOADER = HERE.parent/'finite_fork_folds_20261013/run.py'
previous = module('rolled_end_preserved_source_loader', SOURCE_LOADER)
operator = module('rolled_end_selected_operator', HERE/'roll_operator.py')
core, loader, digest, write = previous.core, previous.loader, previous.digest, previous.write
SOURCE = previous.SOURCE
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/rolled_end_rebuild_20261014/trial01')
G5 = Path('E:/CHESHIRE_DATA/experiments/coherent_fold_detail_20261013/trial01/DIRECTIONAL/SPAN/G05')
G6 = Path('E:/CHESHIRE_DATA/experiments/directional_g6_20261013/trial01/DEPTH_08/SPAN/G06')
G7 = Path('E:/CHESHIRE_DATA/experiments/whole_column_detail_20261013/trial01/SURFACE/MIDDLE/SPAN/G07')
HELPER = HERE.parent/'ornament_junction_finish_20261014/run.py'
helper = module('rolled_end_frozen_region_and_hierarchy', HELPER)
selection, load_lifts = helper.selection, helper.load_lifts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    started = time.perf_counter()
    root = args.root.resolve()
    if root.exists() and any(root.iterdir()):
        raise FileExistsError('Earlier output preserved; select a new empty root.')
    guard = previous.base.finish.memory_guard()
    root.mkdir(parents=True, exist_ok=True)
    print('LOAD actual original SPAN G7 and fixed local region associations', flush=True)
    mesh, chart, pairs, coords, height, source, ancestry, frame = previous.load()
    source_hash = previous.prior.array_hash(mesh.xyz)
    coarse_path, lifts, hierarchy = load_lifts(mesh)
    coarse_info = json.loads((Path(coarse_path)/'generation.json').read_text(encoding='utf-8'))
    coarse_count = coarse_info['control_vertices']
    mask, region = selection(mesh, coarse_count, pairs, lifts[0]['input_faces'])
    hashes = dict(source['geometry_code_sha256'])
    hashes.update(operator.code_hashes())
    for path in (Path(__file__), SOURCE_LOADER, HELPER, HELPER.parent/'junction_operator.py', HERE.parent/'finite_fork_folds_20261013/fold_operator.py'):
        hashes[path.relative_to(REPO).as_posix()] = digest(path)
    for rel, expected in hashes.items():
        path = REPO/rel.replace('\\', '/')
        if digest(path) != expected:
            raise ValueError('Frozen source mismatch: '+rel)
        dest = root/'source_snapshot'/rel.replace('\\', '/')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    request = dict(date='2026-10-14', timezone='Asia/Seoul', basis_commit='78d6f3fefcb61f16253b53b886853fa56a257350',
        source=str(SOURCE), source_receipt_sha256=previous.SOURCE_RECEIPT_SHA256,
        candidate='ROLLED_END_REBUILD', input_case='SPAN', subdivision_generation=7,
        purpose='User-approved individual end reshaping on original marked SPAN, preserving measured protrusion envelope and large fold flow; no stronger fairing.',
        new_detail_deferred=True, new_micro_lip_geometry_executed=False,
        allowed_individual_end_reshape=True, preserve_protrusion_amount=True, preserve_large_fold_flow=True,
        excluded_inputs=['CENTRAL_SPINDLE', 'FINITE_FORK', 'ATTACHED_LEAF', 'JUNCTION_FINISH', 'JUNCTION_TARGET'],
        recipe=operator.RECIPE, selected_region=region, hierarchy=hierarchy)
    write(root/'RUN_REQUEST.json', request)
    write(root/'RECIPE.json', dict(request, geometry_code_sha256=hashes, frame_bindings=frame))
    reflection = dict(X=pairs['mirror_x_vertex_pairs'], Y=pairs['mirror_y_vertex_pairs'])
    print('REBUILD separate source-owned ends with one ordered Bezier fold recipe', flush=True)
    out, metadata, state = operator.build(mesh, chart, reflection,
        lifts[0]['input_faces'], coarse_count, mask, lifts, height)
    state.update(mirror_x_face_pairs=pairs['mirror_x_face_pairs'], mirror_y_face_pairs=pairs['mirror_y_face_pairs'])
    if previous.prior.array_hash(mesh.xyz) != source_hash or not np.array_equal(out.faces, mesh.faces):
        raise ValueError('Actual input mutated or topology changed.')
    symmetry = loader.actual_symmetry(out, state)
    context = dict(input_case='SPAN', candidate='ROLLED_END_REBUILD', source=str(SOURCE), source_generation=7,
        source_control_sha256=source['control_file_sha256'], source_generation_json_sha256=previous.SOURCE_RECEIPT_SHA256,
        parent_stage=str(SOURCE), parent_control_sha256=source['control_file_sha256'],
        parent_generation_json_sha256=previous.SOURCE_RECEIPT_SHA256, geometry_code_sha256=hashes,
        added_CC_passes=0, added_topology_events=0, added_normal_field_passes=0,
        cumulative_normal_field_passes=source['cumulative_normal_field_passes'], added_mandelbulb_evaluations=0,
        source_geometry_averaged=False, source_geometry_parametrically_rebuilt=True, operator_metadata=metadata, selected_region=region,
        hierarchy=hierarchy, frame_ancestry=ancestry, symmetry=symmetry, memory_guard_before_load=guard,
        methodology_scope='Local asymmetric Bezier end targets guided by actual source boundaries and radial envelope; component and flute ownership stays separate, actual source-ID reflection. Source topology remains G7; no source averaging, target CC reconstruction, normal field, or new ornament.',
        exclusions=['Microdetail generation', 'New large ornament', 'G8', 'Geometry fairing', 'Neutral-CC target rebuilding',
            'Task32-cap assumption for WALL event0', 'Collision repair', 'Fabrication certification', 'Aesthetic certification'])
    del mesh, coords, reflection, lifts, pairs
    gc.collect()
    folder = root/'ROLLED_END_REBUILD/SPAN/G07'
    print('SAVE actual locally reshaped G7 and required full mesh checks once', flush=True)
    record = core.save(folder, out, chart, context, state)
    if digest(SOURCE/'generation.json') != previous.SOURCE_RECEIPT_SHA256:
        raise ValueError('Original source changed.')
    previous.base.checked(SOURCE, source, (('control_quad.npz', 'control_file_sha256'), ('evidence.npz', 'evidence_file_sha256')))
    for rel, expected in hashes.items():
        if digest(REPO/rel) != expected:
            raise ValueError('Source code changed during execution: '+rel)
    write(root/'SUMMARY.json', dict(date='2026-10-14', timezone='Asia/Seoul', source=str(SOURCE),
        candidate='ROLLED_END_REBUILD', input_case='SPAN', folder=str(folder), subdivision_generation=7,
        added_CC_passes=0, added_topology_events=0, added_normal_field_passes=0, added_mandelbulb_evaluations=0,
        source_geometry_averaged=False, source_geometry_parametrically_rebuilt=True, generation_json_sha256=digest(folder/'generation.json'),
        control_vertices=len(out.xyz), control_quads=len(out.faces), native_triangles=record['native_triangles'],
        checks=record['checks'], symmetry=symmetry, operator_metadata=metadata, selected_region=region,
        hierarchy=hierarchy, geometry_code_sha256=hashes,
        elapsed_generation_seconds=time.perf_counter()-started, actual_generation_process_memory=previous.process_memory(),
        visual_success='PENDING_ACTUAL_MATCHED_RENDER_REVIEW'))
    print('DONE local rolled-end reshape candidate; no small detail generation', flush=True)


if __name__ == '__main__':
    main()
