"""Finite Task23 declarations; downstream fragments load actual prior values."""
from copy import deepcopy
from pathlib import Path
import argparse
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'examples'))
from cheshire.artifact_root import ArtifactRoot
from cross_cell_crease_study import raw_mesh, mesh_to_data, read, write


def recipe(name, family, input_name, networks, generations=2):
    fractional = any(n.get('profile', 'CONSTANT') != 'CONSTANT' or not float(n.get('sharpness', 4)).is_integer() for n in networks)
    return dict(id=name, family=family, input=input_name, networks=deepcopy(networks), generations=generations,
        mode='UNIFORM_FRACTIONAL' if fractional else 'INTEGER_COMPAS', composition=[],
        contact_policy='Diagnostic sampler cap256; contacts never stop finite compatible evolution. Cleanliness is a final preference.',
        no_global_finish=True, quiet_region='Source lower supports remain unornamented')


def controls(root):
    results = []
    for shape in ('cube', 'column', 'U_gate'):
        original = raw_mesh(read(root.resolve('inputs/'+('C0' if shape == 'U_gate' else shape)+'.json')))
        for q in (0, 1, 2):
            mesh = original.subdivided(scheme='quad', k=q) if q else original
            write(root.resolve(f'inputs/control_{shape}_q{q}.json'), mesh_to_data(mesh))
        configurations = [
            (dict(generator='N1', relation='outer_lintel', sharpness=1), 4, 1),
            (dict(generator='N1', relation='outer_lintel', sharpness=2), 4, 1),
            (dict(generator='N1', relation='outer_lintel', sharpness=4), 4, 1),
            (dict(generator='N1', relation='outer_lintel', sharpness=6), 6, 1),
            (dict(generator='N6', junction='T', sharpness=4), 4, 2),
            (dict(generator='N6', junction='X', sharpness=4), 4, 2),
            (dict(generator='N6', junction='Y', sharpness=4), 4, 2),
            (dict(generator='N6', junction='T', sharpness=4.5, profile='JUNCTION_SOFT_ENDS'), 4, 2),
            (dict(generator='N1', relation='outer_lintel', sharpness=4.5, profile='TWO_PEAKS'), 4, 2),
            (dict(generator='N6', junction='T', sharpness=4.5), 4, 2)]
        for i, (spec, depth, q) in enumerate(configurations, 1):
            if shape == 'U_gate': q = 0 if depth == 6 else 1
            spec.update(quiet_below=0.)
            if spec['generator'] == 'N6' and shape != 'U_gate':
                spec['junction_xz'] = [0, .5]
                spec['minimum_seed_support'] = 0.
                spec['minimum_target_support'] = 0.
                arms = dict(T=[[-.5, .5], [.5, .5], [0, 1.]], X=[[-.5, .5], [.5, .5], [0, 1.], [0, 0.]], Y=[[-.5, 1.], [.5, 1.], [0, 0.]])
                spec['arm_targets'] = arms[spec['junction']]
            r = recipe(f'CTRL_{shape}_{i:02d}', 'CONTROL', f'control_{shape}_q{q}', [spec], depth)
            r['max_faces'] = 300000; results.append(r)
    return results


def primary(root):
    specs = [
        ([dict(generator='N1', relation='outer_lintel', sharpness=4)], 2),
        ([dict(generator='N1', relation='opening_rim', sharpness=4)], 2),
        ([dict(generator='N1', relation='support_shoulder_lintel', sharpness=4)], 2),
        ([dict(generator='N1', relation='outer_lintel', sharpness=6)], 3),
        ([dict(generator='N1', relation='opening_rim', sharpness=1)], 2),
        ([dict(generator='N2', sharpness=4, length_ratio=.8, max_steps=80)], 2),
        ([dict(generator='N2', sharpness=4, seed_xz=[0, .90], length_ratio=1.1, turn_cost=2.0)], 2),
        ([dict(generator='N3', sharpness=4, length_ratio=1.0, max_turn=.7)], 2),
        ([dict(generator='N3', sharpness=4.5, profile='CENTER_SOFT_TAILS', length_ratio=1.0)], 2),
        ([dict(generator='N5', side='left', sharpness=4), dict(generator='N5', side='right', sharpness=4)], 2),
        ([dict(generator='N5', side='left', sharpness=4.5, profile='JUNCTION_SOFT_ENDS'), dict(generator='N5', side='right', sharpness=4.5, profile='JUNCTION_SOFT_ENDS')], 2),
        ([dict(generator='N6', junction='T', sharpness=4)], 2),
        ([dict(generator='N6', junction='X', sharpness=4)], 2),
        ([dict(generator='N6', junction='Y', sharpness=4)], 2),
        ([dict(generator='N1', relation='outer_lintel', sharpness=4.5, profile='SHOULDER_TO_CENTER'),
          dict(generator='N1', relation='opening_rim', sharpness=4.5, profile='TWO_PEAKS')], 2),
        ([], 2)]
    results = [recipe(f'A{i:02d}', 'A_PURE_CREASE', 'C07', n, g) for i, (n, g) in enumerate(specs, 1)]
    for i in range(11):
        n, g = specs[i]
        results.append(recipe(f'B{i+1:02d}', 'B_MOTIF_CREASE', 'TASK22_SHARP', n, min(g, 2)))
    for i, (profile, s, g) in enumerate([('CONSTANT', 4, 1), ('CENTER_SOFT_TAILS', 4.5, 1), ('JUNCTION_SOFT_ENDS', 3.5, 1)], 12):
        results.append(recipe(f'B{i:02d}', 'B_ORDERED_RIDGE_TRANSFER', 'ORDERED',
            [dict(generator='N4', sharpness=s, profile=profile, length_ratio=1.0, seed_xz=[-.30, .94])], g))
    return results


def initialize(root):
    if read(root.resolve('study/verification.json'))['status'] != 'PASS':
        raise ValueError('Exact integer parity gate required before study initialization.')
    recipes = controls(root)+primary(root)
    for r in recipes: write(root.resolve('study/recipes/'+r['id']+'.json'), r)
    write(root.resolve('study/plan.json'), dict(controls=30, family_A=16, family_B=14,
        downstream_target=dict(C=14, D=14, E=20), refinement_cap=24,
        ordinary_face_ceiling=300000, production_face_ceiling=500000, exceptional_production_ceiling=1000000,
        process_tree_plus_driver_bytes=4*1024**3, case_timeout_seconds=900, disk_floor_bytes=12*1024**3,
        contact_cap=256, post_cap_additional_stages=None, no_terminal_smoothing=True))
    print('Initialized baseline declarations; contact counts are diagnostic under the user override.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output-root', type=Path, required=True)
    initialize(ArtifactRoot(parser.parse_args().output_root))
