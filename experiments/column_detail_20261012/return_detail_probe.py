"""Two authored small radial/axial returns beside the preserved G3 folds.

One existing Task33 bilinear split followed by existing smooth_deep PCHIP
events. No Task36 normal offset, new field pass, XYZ smoothing, or physical
origami solver. Global G4 is a detail geometry pass, not fractal iteration 4.
"""
from pathlib import Path
import argparse
import json
import shutil
import sys

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nested_probe as nested

ancestry = nested.ancestry
prior = ancestry.prior
task33_folds = nested.roles.prior.task33_folds
SOURCE = Path('E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G03')
ALGORITHM = 'EXISTING_SMALL_PCHIP_RETURN_DETAIL_G4_V1'
EVENTS = [
    dict(id='LOWER_SIDE_ADJACENT_RETURN', direction=.12, height=.350,
         span=.026, expansion=.14, constriction=.09, reexpansion=.12,
         return_depth=.18, overlap_width=.22, sweep=.10, mirror=False),
    dict(id='UPPER_FRONT_ADJACENT_RETURN', direction=1.45, height=.655,
         span=.028, expansion=.12, constriction=.08, reexpansion=.10,
         return_depth=.18, overlap_width=.22, sweep=.10, mirror=False),
]


def hybrid_pair(root):
    """Same saved post-return G4 controls; add only one finite field pass."""
    source = root / 'RETURN_DETAIL' / 'G04'
    folder = root / 'RETURN_HYBRID' / 'G04'
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError('Existing hybrid result preserved: ' + str(folder))
    inherited = json.loads((source / 'generation.json').read_text(encoding='utf8'))
    if inherited['quick_integrity'] != 'PASS':
        raise ValueError('No hybrid continuation of a failed RETURN_DETAIL source.')
    mesh, chart = ancestry.load_control(source / 'control_quad.npz')
    if mesh.generation != 4:
        raise ValueError('Hybrid pair requires actual saved post-return G4 controls.')
    pre_field = mesh.xyz.copy()
    cfg = prior.field_recipe('n4', .55)
    cfg['iterations'] = 18
    trees, cache = prior.helpers.outside_trees(cfg,
        Path('E:/CHESHIRE_DATA/fold_band_growth_20261011'))
    mesh.xyz, fields, field_log = ancestry.loop.apply_field(
        mesh.xyz, mesh.faces, chart, cfg, trees, .55, .16, 2)
    mesh.surface = 'mean'
    physical = ancestry.task36_growth.native(mesh)
    triangles = physical.faces[:, :3]
    physical_chart = np.concatenate([chart, chart[mesh.faces].mean(1)])
    reflection_failure = None
    try:
        _, symmetry_error, triangle_match = prior.reflection_state(
            physical.xyz, triangles, physical_chart)
    except ValueError as error:
        reflection_failure = str(error)
        symmetry_error = None
        triangle_match = None
    actual = trimesh.Trimesh(physical.xyz, triangles, process=False)
    area = float(actual.area_faces.min())
    components = len(trimesh.graph.connected_components(actual.face_adjacency,
        nodes=np.arange(len(triangles)), min_len=1))
    checks = dict(finite=bool(np.isfinite(physical.xyz).all()),
        watertight=bool(actual.is_watertight), winding_consistent=bool(actual.is_winding_consistent),
        components=components, minimum_triangle_area=area, minimum_area_threshold=1e-12,
        minimum_area_pass=area > 1e-12, geometric_reflection_error=symmetry_error,
        reflected_triangle_sets_identical=triangle_match, reflection_failure=reflection_failure)
    passed = (checks['finite'] and checks['watertight'] and checks['winding_consistent']
        and checks['minimum_area_pass'] and components == 1 and reflection_failure is None)
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder / 'geometry.npz', xyz=physical.xyz, faces=triangles)
    np.savez_compressed(folder / 'checkpoint.npz', xyz=physical.xyz, faces=triangles,
        chart=physical_chart, classes=physical.classes, rest=physical.rest,
        anchors=physical.anchors, generation=np.array(4))
    np.savez_compressed(folder / 'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces,
        chart=chart, classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors,
        generation=np.array(4))
    np.savez_compressed(folder / 'operation_fields.npz', **fields,
        pre_field_post_return_xyz=pre_field, post_field_xyz=mesh.xyz)
    actual.export(folder / 'gate.ply')
    shutil.copy2(__file__, folder / 'return_hybrid_recipe.py')
    moved = np.linalg.norm(mesh.xyz - pre_field, axis=1)
    signature = dict(algorithm=ALGORITHM + '_FIELD_ONLY_PAIR', stage=4,
        source=str(source), field_recipe=cfg, fraction=.55, field_budget=.16,
        local_target_factor=2, extra_quad_splits=0)
    metadata = dict(signature=signature, candidate='RETURN_HYBRID', stage='G04',
        source=str(source / 'checkpoint.npz'), parent=str(source / 'checkpoint.npz'),
        lead_source=str(SOURCE / 'checkpoint.npz'), study_scope='Column only; matched field-only comparison',
        operation='Load exact saved post-return G4 controls; add one existing finite escape-18 nearest-outside field pass and no extra split',
        cycle_order=['Task33_bilinear_refinement', 'authored_small_PCHIP_returns',
            'finite_nearest_outside_field'],
        paired_control_source=str(source / 'control_quad.npz'),
        paired_difference='Same post-return control state, topology, chart, lineage and authored events; only the final field operation is added.',
        authored_return_events=inherited['authored_return_events'],
        inherited_authored_return_events=inherited['inherited_authored_return_events'],
        new_authored_return_events_in_pair=0, new_quad_splits_in_pair=0,
        field_recipe=cfg, field_step=field_log, field_cache=cache,
        field_iterations=18, field_passes_total=4, subdivision_passes_total=4,
        task36_passes_inherited=3, new_small_authored_return_passes=1,
        global_geometry_generation=4,
        counting_rule='The paired field completes the fourth geometry cycle; no fifth refinement or duplicate small return.',
        maximum_field_step=float(moved.max()), field_moved_control_fraction=float((moved > 1e-12).mean()),
        field_budget_scope='Field displacement only; source authored-return displacement is a separate prior operation.',
        legacy_protection='Small-return source protected guide cores only while adding the authored events. This unchanged field pass applies no feature-memory attenuation and may move those cores.',
        control_vertices=len(mesh.xyz), control_quads=len(mesh.faces),
        physical_vertices=len(physical.xyz), physical_triangles=len(triangles),
        separate_geometric_smoothing=False, CC_coordinate_averaging=False,
        symmetry='Existing canonical-quarter field queries and reflected vectors; no posthoc XYZ averaging.',
        provenance='Existing CHESHIRE bilinear/PCHIP geometry followed by finite Mandelbulb-field reconstruction; not IAAC original executable equations or physical origami.',
        quick_integrity='PASS' if passed else 'FAILED_PRESERVED_NO_REPAIR',
        aesthetic_status='PENDING_ACTUAL_RENDER_REVIEW',
        self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication_thickness_structure='NOT_CHECKED', **checks)
    prior.base.dump(folder / 'generation.json', metadata)
    print('GENERATED RETURN_HYBRID G4', len(physical.xyz), len(triangles),
        'field step', metadata['maximum_field_step'], 'symmetry', symmetry_error,
        'quick', metadata['quick_integrity'], flush=True)
    if not passed:
        raise ValueError('Failed hybrid pair preserved without repair or threshold change.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path,
                        default=Path('E:/CHESHIRE_DATA/column_detail_20261012'))
    parser.add_argument('--name', default='RETURN_DETAIL')
    parser.add_argument('--hybrid', action='store_true',
        help='Use exact saved RETURN_DETAIL G4 controls and add only one existing field pass.')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.hybrid:
        hybrid_pair(root)
        return
    family = Path(args.name)
    if family.is_absolute() or len(family.parts) != 1 or '..' in family.parts:
        raise ValueError('Candidate must be one relative folder beneath the output root.')
    folder = root / family / 'G04'
    signature = dict(algorithm=ALGORITHM, source=str(SOURCE), stage=4,
        events=EVENTS, operation_order=['Task33_bilinear_refinement',
            'authored_small_PCHIP_returns'],
        legacy_core_source='Existing nested_probe G3 actual surface guides',
        legacy_core_inner=nested.CORE_INNER, legacy_core_outer=nested.CORE_OUTER,
        new_field_passes=0)
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError('Existing result preserved; no automatic overwrite: ' + str(folder))
    source_meta = json.loads((SOURCE / 'generation.json').read_text(encoding='utf8'))
    mesh, chart = ancestry.load_control(SOURCE / 'control_quad.npz')
    if mesh.generation != 3 or source_meta['quick_integrity'] != 'PASS':
        raise ValueError('Expected preserved passing OVERLAP G3 controls.')
    incoming = mesh.xyz.copy()
    refined, state, refine_log, refinement = task33_folds.refine(mesh,
        dict(carrier=incoming, chart=chart), carrier_smoothing=False, smooth_geometry=False)
    chart_out = state['chart']
    if not np.array_equal(refined.xyz[:len(incoming)], incoming):
        raise ValueError('Existing bilinear refinement changed inherited V positions.')
    if refined.generation != 4 or len(refined.faces) != 4 * len(mesh.faces):
        raise ValueError('Unexpected global generation or quad split count.')
    pre_return = refined.xyz.copy()
    canonical = chart_out.copy()
    canonical[:, 1:] = np.abs(canonical[:, 1:])
    pairs = prior.helpers.existing.symmetry(chart_out)
    guides = nested.legacy_guides(mesh, chart)
    _, protection_fields = nested.activation(pre_return, chart_out, guides, 1)
    protection = protection_fields['legacy_factor']
    raw_events = []
    applied_events = []
    for event in EVENTS:
        raw = prior.smooth_deep.smooth_event(canonical, event)
        raw[:, :2] *= np.where(chart_out[:, 1:] < 0, -1, 1)
        prior.helpers.existing.reflect(raw, chart_out, pairs)
        applied = raw * protection[:, None]
        prior.helpers.existing.reflect(applied, chart_out, pairs)
        raw_events.append(raw)
        applied_events.append(applied)
    displacement = np.sum(applied_events, axis=0)
    refined.xyz = pre_return + displacement
    refined.surface = 'mean'
    physical = ancestry.task36_growth.native(refined)
    triangles = physical.faces[:, :3]
    physical_chart = np.concatenate([chart_out, chart_out[refined.faces].mean(1)])
    reflection_failure = None
    try:
        _, symmetry_error, triangle_match = prior.reflection_state(
            physical.xyz, triangles, physical_chart)
    except ValueError as error:
        reflection_failure = str(error)
        symmetry_error = None
        triangle_match = None
    actual = trimesh.Trimesh(physical.xyz, triangles, process=False)
    area = float(actual.area_faces.min())
    components = len(trimesh.graph.connected_components(actual.face_adjacency,
        nodes=np.arange(len(triangles)), min_len=1))
    checks = dict(finite=bool(np.isfinite(physical.xyz).all()),
        watertight=bool(actual.is_watertight), winding_consistent=bool(actual.is_winding_consistent),
        components=components, minimum_triangle_area=area, minimum_area_threshold=1e-12,
        minimum_area_pass=area > 1e-12, geometric_reflection_error=symmetry_error,
        reflected_triangle_sets_identical=triangle_match, reflection_failure=reflection_failure)
    passed = (checks['finite'] and checks['watertight'] and checks['winding_consistent']
        and checks['minimum_area_pass'] and components == 1 and reflection_failure is None)
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder / 'geometry.npz', xyz=physical.xyz, faces=triangles)
    np.savez_compressed(folder / 'checkpoint.npz', xyz=physical.xyz, faces=triangles,
        chart=physical_chart, classes=physical.classes, rest=physical.rest,
        anchors=physical.anchors, generation=np.array(4))
    np.savez_compressed(folder / 'control_quad.npz', xyz=refined.xyz, faces=refined.faces,
        chart=chart_out, classes=refined.classes, rest=refined.rest,
        anchors=refined.anchors, generation=np.array(4))
    np.savez_compressed(folder / 'operation_fields.npz', **refinement, **protection_fields,
        pre_return_xyz=pre_return, displacement=displacement,
        raw_event_0=raw_events[0], raw_event_1=raw_events[1],
        applied_event_0=applied_events[0], applied_event_1=applied_events[1],
        incoming_point_classes=mesh.classes)
    actual.export(folder / 'gate.ply')
    shutil.copy2(__file__, folder / 'return_detail_recipe.py')
    lengths = np.linalg.norm(displacement, axis=1)
    raw_lengths = np.linalg.norm(np.sum(raw_events, axis=0), axis=1)
    protected = protection_fields['legacy_core_weight'] >= 1. - 1e-12
    metadata = dict(signature=signature, candidate=str(family), stage='G04',
        source=str(SOURCE / 'checkpoint.npz'), parent=str(SOURCE / 'checkpoint.npz'),
        study_scope='Column only; small authored-return comparison, no gate synthesis',
        operation='One existing Task33 bilinear quad split then two selected radial/axial PCHIP return events; no field',
        cycle_order=signature['operation_order'], refinement=refine_log,
        authored_return_events=EVENTS, authored_return_events_this_pass=2,
        inherited_authored_return_events=source_meta['inherited_authored_return_provenance'],
        provenance='Authored CHESHIRE geometry using unchanged smooth_deep.smooth_event; neither fractal-emergent growth nor physical origami.',
        event_logic='Existing radial expansion, constriction, re-expansion plus independent axial reversal. Height-varying angular activation is not material torsion.',
        event_profile_knots=prior.smooth_deep.KNOTS.tolist(),
        existing_event_limits='Original fixed local_h angular offset .05 and terminal envelope retained; not a new scale-invariant fold law.',
        core_protection='Existing nested G3 actual-surface guides attenuate only the new return vector; no old XYZ averaging or automatic crease extraction.',
        core_inner=nested.CORE_INNER, core_outer=nested.CORE_OUTER,
        protected_core_controls=int(protected.sum()),
        protected_core_moved=int((lengths[protected] > 1e-12).sum()),
        source_control_vertices=len(mesh.xyz), source_control_quads=len(mesh.faces),
        control_vertices=len(refined.xyz), control_quads=len(refined.faces),
        physical_vertices=len(physical.xyz), physical_triangles=len(triangles),
        maximum_raw_authored_step=float(raw_lengths.max()),
        maximum_applied_authored_step=float(lengths.max()),
        event_maximum_applied_step=[float(np.linalg.norm(d, axis=1).max()) for d in applied_events],
        active_control_fraction=float((lengths > 1e-12).mean()),
        inherited_controls_moved=int((lengths[:len(mesh.xyz)] > 1e-12).sum()),
        inherited_controls_maximum_step=float(lengths[:len(mesh.xyz)].max()),
        inherited_controls_policy='Unlike E/F-only NESTED, this authored event may move old controls inside selected bands; inactive old controls remain exact.',
        inactive_surface_limit='Bilinear child-quad mean fans can alter the physical surface of nonplanar quads even where authored displacement is zero.',
        global_geometry_generation=4, subdivision_passes_total=4,
        field_passes_total=3, new_field_passes=0, field_used=False,
        new_small_authored_return_passes=1, task36_passes_inherited=3,
        counting_rule='G4 is total geometry generation; this pass does not add a fourth fractal classification or Task36 normal-offset cycle.',
        separate_geometric_smoothing=False, CC_coordinate_averaging=False,
        symmetry='Canonical X/Y event vectors copied to corresponding reflection partners; no posthoc XYZ averaging.',
        physical_surface='Arithmetic quad-centre triangle fans, unchanged renderer material and geometric normals.',
        quick_integrity='PASS' if passed else 'FAILED_PRESERVED_NO_REPAIR',
        aesthetic_status='PENDING_ACTUAL_RENDER_REVIEW',
        self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication_thickness_structure='NOT_CHECKED', **checks)
    prior.base.dump(folder / 'generation.json', metadata)
    print('GENERATED', str(family), 'G4', len(physical.xyz), len(triangles),
        'step', metadata['maximum_applied_authored_step'],
        'active', metadata['active_control_fraction'], 'core_moved', metadata['protected_core_moved'],
        'symmetry', symmetry_error, 'quick', metadata['quick_integrity'], flush=True)
    if not passed:
        raise ValueError('Failed result preserved without repair or threshold change.')


if __name__ == '__main__':
    main()
