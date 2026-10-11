"""Bounded same-rule, two-input, native-geometry-responsive G3 study."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('region_growth_existing_anchor',
    HERE.parent/'fold_return_20261012/study.py')
anchor = importlib.util.module_from_spec(spec); spec.loader.exec_module(anchor)
from region_fold import NativeChartSampler, measure_parent, measure_longitudinal, proposal

RECIPE = dict(name='native_measured_shoulder_region_v1', shoulder_fraction=.55,
    depth_ratio=.28, return_angle=.65, source_generation=2, output_generation=3,
    new_field_passes=0, geometric_averaging=0, cell_normal_placement=0,
    rule_scope='Same authored parent seeds and same coefficients on both existing column inputs; actual native geometry sets new guides, frames and physical scales',
    preservation='Source and controls preserved; strip endpoints have zero displacement. No claim of exact old fold-angle/depth retention.',
    generation_scope='One meso operation after inactive surface-preserving refinement; no recurrence or general-mesh claim')
SOURCES = dict(SPAN=HERE.parents[1]/'docs/fold_return_20261012/review_assets/OVERLAP_G02',
    COUNTER=HERE.parents[1]/'docs/fold_region_growth_20261012/review_assets/COUNTER_G02')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(root, case, mode, orientation='theta',source_override=None,frame_mode='native'):
    source = Path(source_override).resolve() if source_override else SOURCES[case]
    folder = root/mode/case/'G03'
    if folder.exists():
        raise FileExistsError('Existing result preserved: '+str(folder))
    mesh, chart, tags = anchor.t.load(source)
    original = mesh.xyz.copy()
    if mesh.generation != 2:
        raise ValueError('Actual G2 controls required.')
    receipt = json.loads((source/'generation.json').read_text(encoding='utf8'))
    parents = receipt.get('event_bank', receipt.get('authored_return_events', anchor.t.overlap.EVENTS))
    # Both inputs were made with the same two macro event seeds. Do not quietly
    # allow a larger bank or unrelated case-specific child events.
    if len(parents) != 2:
        raise ValueError('Exactly two preserved parent region seeds required.')
    physical = anchor.t.growth.native(mesh)
    pchart = np.concatenate([chart, anchor.t.face_values(mesh, chart)])
    sampler = NativeChartSampler(physical.xyz, physical.faces[:, :3], pchart)
    measure=measure_parent if orientation=='theta' else measure_longitudinal
    guides = [measure(sampler, parent, shoulder_fraction=RECIPE['shoulder_fraction'],frame_mode=frame_mode) for parent in parents]
    out, outchart, outtags, op = anchor.t.memory.refine(mesh, chart, tags)
    reference = out.xyz.copy()
    delta, weights = proposal(out.xyz, outchart, guides, mode='GROOVE' if mode == 'CONTROL' else mode,
        depth_ratio=0 if mode == 'CONTROL' else RECIPE['depth_ratio'], angle=RECIPE['return_angle'])
    existing = anchor.t.prior.helpers.existing
    existing.reflect(delta, outchart, existing.symmetry(outchart))
    out.xyz += delta
    physical = anchor.t.growth.native(out)
    triangles = physical.faces[:, :3]
    pchart = np.concatenate([outchart, anchor.t.face_values(out, outchart)])
    actual = trimesh.Trimesh(physical.xyz, triangles, process=False)
    _, errors, matches = anchor.t.prior.reflection_state(physical.xyz, triangles, pchart)
    checks = dict(finite=bool(np.isfinite(physical.xyz).all()), watertight=bool(actual.is_watertight),
        winding_consistent=bool(actual.is_winding_consistent), components=int(actual.body_count),
        minimum_triangle_area=float(actual.area_faces.min()), minimum_area_threshold=1e-12,
        geometric_reflection_error=errors, reflected_triangle_sets_identical=matches)
    passed = (checks['finite'] and checks['watertight'] and checks['winding_consistent'] and
        checks['components'] == 1 and checks['minimum_triangle_area'] > 1e-12 and max(errors) < 1e-9 and all(matches))
    folder.mkdir(parents=True)
    np.savez_compressed(folder/'control_quad.npz', xyz=out.xyz, faces=out.faces, chart=outchart,
        classes=out.classes, rest=out.rest, anchors=out.anchors, generation=np.array(out.generation),
        surface=np.array(out.surface), memory=outtags)
    np.savez_compressed(folder/'geometry.npz', xyz=physical.xyz, faces=triangles)
    np.savez_compressed(folder/'operation_fields.npz', reference_xyz=reference, delta=delta,
        region_weights=weights, chart=outchart, input_edges=op['input_edges'], parent_face=op['parent_face'])
    guide_metrics = []
    for index, guide in enumerate(guides):
        np.savez_compressed(folder/f'guide_{index}.npz', **guide)
        guide_metrics.append(dict(parent_id=parents[index]['id'],
            median_shoulder_arc=float(np.median(guide['shoulder_length'])),
            median_parent_signed_chord_relief=float(np.median(guide['parent_basin_deficit'] if orientation=='theta' else guide['parent_signed_chord_relief'])),
            parameter_axis=orientation,
            frame_mode=frame_mode,
            guide_transverse_coordinate_range=[float(guide['guide_cross'].min()),float(guide['guide_cross'].max())],
            guide_world_length=float(np.linalg.norm(np.diff(guide['centres'],axis=0),axis=1).sum())))
    actual.export(folder/'column.ply')
    metadata = dict(candidate=mode, input_case=case, stage='G03', recipe=dict(RECIPE,orientation=orientation,frame_mode=frame_mode), source=str(source),
        source_control_sha256=digest(source/'control_quad.npz'), source_generation=mesh.generation,
        source_field_passes=receipt['field_passes_total'], added_field_passes=0,
        new_authored_events=[], parent_region_seeds=parents, measured_guides=guide_metrics,
        actual_control_vertices=len(out.xyz), physical_vertices=len(physical.xyz), physical_triangles=len(triangles),
        maximum_displacement=float(np.linalg.norm(delta,axis=1).max()),
        moved_controls=int((np.linalg.norm(delta,axis=1)>1e-12).sum()),
        inherited_controls_moved=int((np.linalg.norm(out.xyz[:len(original)]-original,axis=1)>1e-12).sum()),
        quick_integrity='PASS' if passed else 'FAILED_PRESERVED', self_intersection='NOT_CHECKED_EXPLORATION',
        fabrication='NOT_CHECKED', guide_sampling='Barycentric actual native triangles in affine native material UV',
        source_revision='8a4cc2e4367802123d6f5fd24e70620259463642', **checks)
    (folder/'generation.json').write_text(json.dumps(metadata,indent=2),encoding='utf8')
    for path in (Path(__file__), HERE/'region_fold.py'):
        shutil.copy2(path,folder/path.name)
    print(case,mode,metadata['quick_integrity'],len(triangles),'max',metadata['maximum_displacement'],
        'guides',guide_metrics,flush=True)
    if not passed:
        raise ValueError('Quick geometry failure preserved, no repair or relaxed thresholds.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--cases',nargs='+',choices=list(SOURCES),default=list(SOURCES))
    parser.add_argument('--modes',nargs='+',choices=('CONTROL','GROOVE','RETURN'),default=['CONTROL','GROOVE','RETURN'])
    parser.add_argument('--orientation',choices=('theta','height'),default='theta')
    parser.add_argument('--frames',choices=('native','region'),default='native')
    parser.add_argument('--source-span',type=Path,help='Override the packaged SPAN G2 controls and receipt')
    parser.add_argument('--source-counter',type=Path,help='Override the packaged COUNTER G2 controls and receipt')
    args=parser.parse_args()
    for case in args.cases:
        for mode in args.modes:
            source=args.source_span if case=='SPAN' else args.source_counter
            run(args.root.resolve(),case,mode,args.orientation,source,args.frames)
