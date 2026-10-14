"""One original-SPAN replay with bounded G1/G2 finite-field axial attenuation.

All frozen geometric modules are imported read-only. The sole source-rule
revision scales the applied field's Z component inside one material band.
Intermediate late stages store controls/evidence; G07_FINAL stores native once.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
import sys
import time

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ORIGINAL_G0 = Path('E:/CHESHIRE_DATA/fold_band_growth_20261011/inputs/SPAN_SPARSE/G00')
ORIGINAL_G0_SHA = 'cff9089de50aac6019684829cd70303d77e3fceaaabf3f090a06636f4f6cbf55'
ORIGINAL_G0_RECEIPT_SHA = '6226ab8043dbd50732da3be842e9a0d2fb3f6fd8a1906dc5d9e1936564a615e1'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


early = module('end_revision_frozen_early_adapter', HERE.parent/'recipe_transfer_20261013/early.py')
late = module('end_revision_frozen_late_adapter', HERE.parent/'recipe_transfer_20261013/late.py')
RECIPE = {
    'schema': 'CHESHIRE_ORIGINAL_SPAN_FIELD_AXIAL_ATTENUATION_V1',
    'source_case': 'SPAN', 'original_G0_geometry_loaded_exactly': True,
    'revised_stages': [1, 2],
    'coordinates': 'Inherited early material chart: t=chart[:,0], theta=atan2(abs(chart[:,2]),abs(chart[:,1])). No current-XYZ inverse map.',
    'mask': {'t_centre': .63, 't_halfwidth': .085,
             'theta_centre': .86, 'theta_halfwidth': .66, 'plateau_start': .60},
    'weight_equation': 'w=plateau((t-.63)/.085,.60)*plateau((theta-.86)/.66,.60)',
    'axial_gain_equation': 'gain=1-.75*w', 'minimum_axial_gain': .25,
    'revision_equation': 'applied_field_delta_new=(raw_applied_dx,raw_applied_dy,gain*raw_applied_dz)',
    'unchanged': ['Original G0 XYZ, quads and chart', 'G1/G2 Task36 recipe',
                  'Authored G2 PCHIP returns', 'Raw finite-field target search and budgets',
                  'Measured WALL rule', 'Task32 topology-event rules',
                  'G4-G7 subdivision, whole-field, linked and wide-root rules'],
    'dependent_geometry': 'Original later operators recompute their geometry-dependent normals, rails and frames on the revised actual parents.',
    'field_semantics': 'Authored axial attenuation of the existing finite-field vector. The revised applied vector is not generally directed at the nearest finite-outside target. No final-outside guarantee is asserted.',
    'validation_scope': 'One revised replay, not an independent unchanged-baseline replay. Final source correspondence and localized splice belong to the orchestrator.',
}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def ah(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def exact_original_seed(radius_scale_profile):
    if tuple(radius_scale_profile) != (1.,) * 8:
        raise ValueError('This replay accepts the unchanged original SPAN input only.')
    if sha(ORIGINAL_G0/'control_quad.npz') != ORIGINAL_G0_SHA or sha(ORIGINAL_G0/'generation.json') != ORIGINAL_G0_RECEIPT_SHA:
        raise ValueError('Original frozen G0 source changed.')
    with np.load(ORIGINAL_G0/'control_quad.npz', allow_pickle=False) as data:
        xyz, faces, chart = data['xyz'], data['faces'], data['chart']
    # Historical G0 saved only XYZ/quads/chart. Recover ancillary carrier
    # associations by the exact original ancestry_probe convention.
    mesh, carrier_chart = early.seed.variation.carrier(dict(rings=25, sectors=16, radius=.78))
    if not np.array_equal(mesh.faces, faces) or not np.array_equal(carrier_chart, chart):
        raise ValueError('Original carrier quads/chart correspondence changed.')
    mesh.xyz = xyz.copy()
    mesh.anchors[:, 0] = np.arange(len(faces))
    mesh.surface = 'mean'
    if mesh.generation != 0:
        raise ValueError('Original source is not G0.')
    with np.load(ORIGINAL_G0/'operation_fields.npz', allow_pickle=False) as data:
        parts = {key: data[key] for key in data.files}
    recipe = read(ORIGINAL_G0/'generation.json')['recipe']
    return mesh, chart.copy(), parts, copy.deepcopy(recipe), copy.deepcopy(recipe)


_frozen_ancestry_field = early.ancestry_field


def revised_ancestry_field(mesh, chart, generation, selected):
    out, outchart, state, metadata = _frozen_ancestry_field(mesh, chart, generation, selected)
    if generation not in (1, 2):
        raise ValueError('Only G1/G2 finite fields may be revised.')
    raw_applied = np.asarray(state['applied_field_displacement']).copy()
    before = out.xyz.copy()
    settings = RECIPE['mask']
    theta = np.arctan2(abs(outchart[:, 2]), abs(outchart[:, 1]))
    weight = (early.wall.wall_fold.plateau((outchart[:, 0]-settings['t_centre'])/settings['t_halfwidth'], settings['plateau_start']) *
              early.wall.wall_fold.plateau((theta-settings['theta_centre'])/settings['theta_halfwidth'], settings['plateau_start']))
    gain = 1. - .75 * weight
    applied = raw_applied.copy()
    applied[:, 2] *= gain
    correction = applied - raw_applied
    out.xyz[:, 2] += correction[:, 2]
    if not np.array_equal(out.xyz[:, :2], before[:, :2]) or not np.array_equal(applied[:, :2], raw_applied[:, :2]):
        raise ValueError('Axial-only revision unexpectedly changed X/Y.')
    if not np.array_equal(out.xyz[weight == 0], before[weight == 0]):
        raise ValueError('The early revision leaked outside the material mask.')
    raw_norm = np.linalg.norm(raw_applied, axis=1)
    applied_norm = np.linalg.norm(applied, axis=1)
    budget = .35 if generation == 1 else .28
    if np.any(applied_norm > raw_norm + 1e-12) or applied_norm.max() > budget + 1e-12:
        raise ValueError('Axial attenuation increased the applied field step or its budget.')
    if not np.isfinite(out.xyz).all():
        raise ValueError('Nonfinite revised early source.')
    # Raw finite target coordinates, inside status, and raw_field_displacement
    # remain the frozen search result. These explicit applied arrays describe
    # the actual revised geometry rather than silently relabelling that result.
    state.update(pre_axial_revision_field_displacement=raw_applied,
                 applied_field_displacement=applied, field_displacement=applied.copy(),
                 field_axial_revision_mask=weight, field_axial_gain=gain,
                 field_axial_revision_delta=correction, post_field_xyz=out.xyz.copy())
    revision = dict(recipe=copy.deepcopy(RECIPE), generation=generation,
        material_mask_vertices=int(np.count_nonzero(weight)),
        actual_changed_vertices=int(np.count_nonzero(correction[:, 2])),
        raw_applied_field_sha256=ah(raw_applied), revised_applied_field_sha256=ah(applied),
        material_mask_sha256=ah(weight), axial_gain_sha256=ah(gain),
        axial_gain_range=[float(gain.min()), float(gain.max())],
        maximum_abs_axial_correction=float(abs(correction[:, 2]).max()),
        maximum_raw_applied_field_norm=float(raw_norm.max()),
        maximum_revised_applied_field_norm=float(applied_norm.max()),
        field_budget=budget, X_Y_bitwise_unchanged_this_revision=True,
        outside_material_mask_bitwise_unchanged_this_revision=True,
        applied_norm_did_not_increase=True)
    metadata['original_raw_field_step'] = copy.deepcopy(metadata['field_step'])
    metadata['field_step'] = dict(metadata['field_step'],
        maximum_field_step=float(applied_norm.max()),
        authored_axial_attenuation_applied=True,
        applied_vector_scope=RECIPE['field_semantics'])
    metadata['source_rule_revision'] = revision
    metadata['cycle_order'] = list(metadata['cycle_order']) + ['bounded_material_field_axial_attenuation']
    return out, outchart, state, metadata


_frozen_early_save = early._save


def early_save(folder, mesh, chart, context, state, **kwargs):
    context = dict(context, input_case='SPAN',
        transfer_schema=RECIPE['schema'],
        input_only_change='No G0 change. One bounded G1/G2 applied finite-field axial attenuation; dependent later operators recompute on revised parents.',
        source_rule_revision_recipe=copy.deepcopy(RECIPE))
    return _frozen_early_save(folder, mesh, chart, context, state, **kwargs)


def late_load(root, stage):
    path = late.folder(root, stage)
    info = read(path/'generation.json')
    if info['input_case'] != 'SPAN' or not info['checks']['passed']:
        raise ValueError('Verified actual SPAN revised parent required: ' + stage)
    if sha(path/'control_quad.npz') != info['control_file_sha256']:
        raise ValueError('Actual revised control file changed: ' + stage)
    data = late.arrays(path/'control_quad.npz')
    mesh = late.core.ArrayMesh(data['xyz'], data['faces'], data['classes'], data['rest'], data['anchors'], int(data['generation']))
    mesh.surface = str(data['surface'])
    if mesh.generation != info['subdivision_generation']:
        raise ValueError('Saved subdivision generation differs from actual parent.')
    return mesh, data['chart'], info


_frozen_late_bind = late.bind
_frozen_late_save = late.save


def late_bind(*args, **kwargs):
    result = _frozen_late_bind(*args, **kwargs)
    result.update(input_case='SPAN', source_rule_revision=copy.deepcopy(RECIPE),
        recipe_scope='Original SPAN G0 loaded exactly; bounded G1/G2 field axial attenuation; all later selected operators and coefficients reused on actual revised parents.',
        exclusions=['Additional parameter matrix', 'Added ornament meshes', 'Whole-column remeshing',
                    'Independent unchanged-baseline replay', 'Self-intersection repair', 'Fabrication certification'])
    return result


def late_save(root, stage, mesh, chart, state, context, native=True):
    return _frozen_late_save(root, stage, mesh, chart, state, context, native=stage == 'G07_FINAL')


early.seed_input = exact_original_seed
early.ancestry_field = revised_ancestry_field
early._save = early_save
early.INPUT_CASE = 'SPAN'
late.load = late_load
late.bind = late_bind
late.save = late_save


def prepare(root):
    """Bind and snapshot the adapter plus frozen transitive modules once."""
    hashes = early.code_hashes()
    hashes[Path(__file__).resolve().relative_to(REPO).as_posix()] = sha(Path(__file__).resolve())
    recipe = dict(schema=RECIPE['schema'], input_case='SPAN', source_rule_revision=RECIPE,
        original_G0=dict(folder=str(ORIGINAL_G0), control_sha256=ORIGINAL_G0_SHA,
                         generation_sha256=ORIGINAL_G0_RECEIPT_SHA,
                         operation_fields_sha256=sha(ORIGINAL_G0/'operation_fields.npz')),
        geometry_code_sha256=hashes, frozen_late_recipe_checks=late.recipe_proof(),
        scope='One modified original-SPAN replay; original saved research and code stay read-only.')
    target = root/'RECIPE.json'
    if target.exists():
        if read(target) != recipe:
            raise FileExistsError('Saved replay recipe differs; use a new output root.')
    else:
        root.mkdir(parents=True, exist_ok=True)
        early.write(target, recipe)
    snapshots = {}
    for rel, expected in hashes.items():
        source = REPO/rel.replace('\\', '/')
        if sha(source) != expected:
            raise ValueError('Frozen source changed: ' + rel)
        dest = root/'source_snapshot'/rel.replace('\\', '/')
        if dest.exists():
            if sha(dest) != expected:
                raise ValueError('Saved source snapshot changed: ' + rel)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        snapshots[rel] = dict(source=str(source), snapshot=str(dest), sha256=expected)
    binding = root/'SOURCE_SNAPSHOT.json'
    proof = dict(geometry_code_sha256=hashes, sources=snapshots)
    if binding.exists() and read(binding) != proof:
        raise ValueError('Source snapshot bindings differ.')
    if not binding.exists():
        early.write(binding, proof)
    return recipe


def check_source_bindings(root):
    recipe = read(root/'RECIPE.json')
    if recipe['source_rule_revision'] != RECIPE:
        raise ValueError('Saved axial revision recipe differs.')
    for rel, expected in recipe['geometry_code_sha256'].items():
        if sha(REPO/rel.replace('\\', '/')) != expected or sha(root/'source_snapshot'/rel.replace('\\', '/')) != expected:
            raise ValueError('Executed source/snapshot changed: ' + rel)
    if sha(ORIGINAL_G0/'control_quad.npz') != ORIGINAL_G0_SHA or sha(ORIGINAL_G0/'generation.json') != ORIGINAL_G0_RECEIPT_SHA:
        raise ValueError('Original G0 source changed during replay.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--stage', choices=('early',) + late.STAGES, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    started = time.perf_counter()
    if args.stage == 'early':
        prepare(root)
        print('REPLAY original SPAN G0-G4 with one bounded field axial revision', flush=True)
        early.build(root, radius_scale_profile=(1.,) * 8)
    else:
        check_source_bindings(root)
        late.recipe_proof()
        if late.folder(root, args.stage).exists():
            raise FileExistsError('Saved replay stage is immutable: ' + args.stage)
        print('REPLAY original later operator on revised actual parent: ' + args.stage, flush=True)
        if args.stage in ('G05_DIRECTIONAL', 'G06_DEPTH08'):
            late.directional(root, args.stage)
        elif args.stage == 'G06_MIDDLE':
            late.middle(root)
        elif args.stage == 'G07_SURFACE':
            late.surface(root)
        elif args.stage in ('G07_LINKED_RAW', 'G07_WIDE_RAW'):
            late.fields(root, args.stage)
        else:
            late.filter_saved(root, args.stage)
    check_source_bindings(root)
    print('DONE ' + args.stage + ' seconds=' + str(round(time.perf_counter() - started, 3)), flush=True)


if __name__ == '__main__':
    main()
