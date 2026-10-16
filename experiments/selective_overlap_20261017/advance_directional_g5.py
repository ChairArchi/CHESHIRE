"""One unchanged, actual DIRECTIONAL G4->G5 operation on verified new parents.

G5 controls/evidence are stored; native geometry is generated only after the
separate final ornament operation. No G6/G7 stage is implied or evaluated.
"""
from __future__ import annotations

import argparse
import gc
import importlib.util
from pathlib import Path
import shutil
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCHEMA = 'CHESHIRE_SELECTIVE_ACTUAL_DIRECTIONAL_G5_ONLY_V1'
spec = importlib.util.spec_from_file_location('selective_actual_parent_late',
    HERE.parent/'early_dynamic_variations_20261016/late_detail_adapter.py')
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)
late = adapter.late


def native_area_check(mesh, chunk=65536):
    minimum = float('inf')
    bad = 0
    for start in range(0, len(mesh.faces), chunk):
        p = mesh.xyz[mesh.faces[start:start+chunk]]
        centre = p.mean(axis=1)
        for k in range(4):
            area = .5*np.linalg.norm(np.cross(p[:, k]-centre,
                p[:, (k+1)%4]-centre), axis=1)
            bad += int(np.count_nonzero(~np.isfinite(area) | (area <= 0)))
            minimum = min(minimum, float(area.min()))
    if bad:
        raise ValueError('Actual G5 native fans contain invalid areas: '+str(bad))
    return dict(triangles=int(4*len(mesh.faces)), minimum_triangle_area=minimum,
        degenerate_or_nonfinite_triangles=bad, native_geometry_stored=False)


def current_codes():
    codes = adapter.code_hashes()
    codes[Path(__file__).resolve().relative_to(REPO).as_posix()] = adapter.sha(__file__)
    return dict(sorted(codes.items()))


def run(root):
    root = Path(root).resolve()
    dest = root/'states/G05_DIRECTIONAL'
    if dest.exists() or (root/'G5_ONLY_RECIPE.json').exists():
        raise FileExistsError('Actual G5 stage/recipe is immutable: '+str(root))
    started = time.perf_counter()
    late.recipe_proof()
    proof = adapter.input_proof(root)
    codes = current_codes()
    snapshots = root/'g5_only_source_snapshot'
    snapshots.mkdir()
    for relative, checksum in codes.items():
        path = snapshots/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO/relative, path)
        if adapter.sha(path) != checksum:
            raise ValueError('G5 source snapshot differs: '+relative)
    recipe = dict(schema=SCHEMA, stage_order=['G05_DIRECTIONAL'],
        original_operator='fold_operator.build(actual_G4, actual_G4_evidence, actual_G3_evidence, DIRECTIONAL)',
        original_operator_recipe=late.fold5.RECIPE, actual_input=proof,
        geometry_code_sha256=codes,
        early_recipe_sha256=adapter.sha(root/'RECIPE.json'),
        final_pipeline='Actual G5 followed by a separately bound fresh ornament stage',
        G6_or_G7_evaluated=False, old_final_xyz_read_or_pulled_back=False)
    late.core.write(root/'G5_ONLY_RECIPE.json', recipe)
    print('VERIFIED ACTUAL G3/G4; BUILDING ORIGINAL DIRECTIONAL G5', flush=True)
    mesh, chart, parent = adapter.load(root, 'G04_NEUTRAL')
    g3 = late.evidence(root, 'G03_SIDEWALL')
    g4 = late.evidence(root, 'G04_NEUTRAL', ('parent_face', 'input_edges'))
    incoming_pairs = late.pairs(root, 'G04_NEUTRAL', mesh)
    out, metadata, state = late.fold5.build(mesh, g4, g3, 'DIRECTIONAL')
    if out.generation != 5 or len(out.faces) != 4*len(mesh.faces):
        raise ValueError('G5 is not the actual complete next subdivision.')
    p = np.asarray(state['parent_face'])
    if not np.all(np.bincount(p, minlength=len(mesh.faces)) == 4):
        raise ValueError('G5 actual parent-face split differs.')
    outchart = late.carry(chart, state['input_edges'], mesh.faces)
    state.update(late.propagate(mesh, state, incoming_pairs))

    # Auxiliary final-stage coordinates, recomputed from the actual G5 surface.
    # These do not enter or modify the unchanged DIRECTIONAL operator above.
    frame, radius, basis = late.fold5._root_frame(g3)
    canonical = out.xyz.copy()
    canonical[:, :2] = np.abs(canonical[:, :2])
    coordinates = (canonical-frame['origin']) @ basis/radius
    band = late.fold5.RECIPE['band']
    long = coordinates[:, 0]
    state['directional_phase'] = 2*np.pi*(coordinates[:, 1]/band['period_root_radius'] +
        band['major_linear']*long + band['major_warp_amplitude']*
        np.sin(band['major_warp_frequency']*long+band['major_warp_phase']))
    lo, hi = float(out.xyz[:, 2].min()), float(out.xyz[:, 2].max())
    state['frame_normalized_z'] = (out.xyz[:, 2]-lo)/(hi-lo)
    del canonical, coordinates, g3, g4, incoming_pairs, p, mesh, chart
    gc.collect()
    area = native_area_check(out)
    context = dict(schema=SCHEMA, input_case=parent['input_case'],
        candidate=parent['candidate'], stage_id='G05_DIRECTIONAL',
        source=str(root/'states/G04_NEUTRAL'), source_generation=4,
        source_control_sha256=parent['control_file_sha256'],
        source_evidence_sha256=parent['evidence_file_sha256'],
        source_generation_json_sha256=adapter.sha(root/'states/G04_NEUTRAL/generation.json'),
        parent_control_sha256=parent['control_file_sha256'],
        geometry_code_sha256=codes, operator_metadata=metadata,
        added_subdivision_passes=1, added_CC_passes=1,
        added_topology_events=0, added_mandelbulb_evaluations=0,
        native_fan_area_check=area,
        auxiliary_vertex_fields=dict(directional_phase='Actual G5 canonical abs(X,Y) in inherited root PCA frame, same original band equation; auxiliary only',
            frame_normalized_z='Actual G5 global Z bounds', actual_z_bounds=[lo,hi]),
        recipe_scope='Unchanged original DIRECTIONAL coefficients on actual new G4; one real next subdivision.',
        G6_or_G7_evaluated=False, old_final_xyz_read_or_pulled_back=False)
    adapter.save(root, 'G05_DIRECTIONAL', out, outchart, state, context, native=False)
    if current_codes() != codes:
        raise ValueError('Executed G5 source changed during operation.')
    # Recheck the externally owned parent files without loading dense arrays.
    adapter.checked_files(root, 'G04_NEUTRAL')
    adapter.checked_files(root, 'G03_SIDEWALL')
    saved = adapter.read(dest/'generation.json')
    receipt = dict(schema=SCHEMA, status='PASS', stage='G05_DIRECTIONAL',
        elapsed_seconds=time.perf_counter()-started,
        recipe_sha256=adapter.sha(root/'G5_ONLY_RECIPE.json'),
        generation_json_sha256=adapter.sha(dest/'generation.json'),
        control_file_sha256=saved['control_file_sha256'],
        evidence_file_sha256=saved['evidence_file_sha256'],
        control_vertices=len(out.xyz), control_quads=len(out.faces),
        native_fan_area_check=area, input_binding=proof,
        output_generation=5, added_subdivision_passes=1,
        G6_or_G7_evaluated=False, visual_success='NOT_ASSESSED',
        self_intersection='NOT_CHECKED_EXPLORATORY', fabrication='NOT_CHECKED')
    late.core.write(dest/'G5_EXECUTION_RECEIPT.json', receipt)
    print('ACTUAL G5 READY', receipt['control_vertices'], receipt['control_quads'],
        'seconds='+str(round(receipt['elapsed_seconds'], 3)), flush=True)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    run(args.root)
