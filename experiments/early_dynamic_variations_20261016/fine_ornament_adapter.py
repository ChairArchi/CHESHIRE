"""Deposit existing finite Mandel/Tissue relief on actual new G6/G7 parents.

This adapter re-measures the new candidate's G3 shape at one physical graph
radius, then transports those continuous weights through actual saved CC face
ancestry. Dense host normals, local safety caps and orientation recovery use
the actual new input geometry. No final historical column XYZ is read.

Tissue is the existing actual paper-origin component's single-valued height
adapter: this run does not invoke Tissue or transfer overhangs/full-XYZ grafts.
Native closed host topology stays unchanged; deep relief can suggest pockets
without creating through holes. Self-intersections/printing remain unchecked.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import gc
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.interpolate import RectBivariateSpline


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(REPO/'src') not in sys.path:
    sys.path.insert(0, str(REPO/'src'))
from cheshire import adaptive_ornament as ornament
from cheshire.ornament_analysis import (EvidenceConfig, analyze_ornament_shape,
                                        face_fields_to_vertices, smooth01)

spec = importlib.util.spec_from_file_location('early_dynamic_ornament_actual_late',
                                            HERE/'late_detail_adapter.py')
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)
late = adapter.late
sha, ah, read = adapter.sha, adapter.ah, adapter.read
SCHEMA = 'CHESHIRE_EARLY_DYNAMIC_EXISTING_MANDEL_TISSUE_RELIEF_V1'
DEFAULT_PROFILE = Path('E:/CHESHIRE_DATA/experiments/fold_junction_development_20261015/'
                       'trial12c_all_small_mandel_replacement/MANDELBULB_PROFILE.json')
DEFAULT_TISSUE = Path('E:/CHESHIRE_DATA/experiments/generation_mirror_hybrid_20261016/'
                      'paper_tissue/ACTUAL_TISSUE_RECEIPT.json')
CC_STAGES = ('G04_NEUTRAL', 'G05_DIRECTIONAL', 'G06_DEPTH08', 'G07_SURFACE')


def sources(profile_receipt, tissue_receipt):
    """Load immutable actual source arrays and verify their original receipts."""
    pinfo, tinfo = read(profile_receipt), read(tissue_receipt)
    pfile = Path(pinfo['array_file'])
    if sha(pfile) != pinfo['array_file_sha256']:
        raise ValueError('Actual finite Mandel radial evidence changed.')
    with np.load(pfile, allow_pickle=False) as stored:
        boundary = {}
        for key in ('theta', 'phi', 'radius'):
            item = pinfo['tree'][key]
            value = stored[item['npz_key']]
            if list(value.shape) != item['shape'] or ah(value) != item['sha256']:
                raise ValueError('Actual Mandel boundary array differs: '+key)
            boundary[key] = value
    profile = ornament.MandelRadialProfile(**boundary, provenance=dict(
        actual_finite_boundary_receipt=str(profile_receipt),
        original_receipt_sha256=sha(profile_receipt)))
    tfile = Path(tinfo['height_grid'])
    if (not tinfo.get('actual_Tissue_call_succeeded', False) or
            sha(tfile) != tinfo['height_grid_sha256']):
        raise ValueError('Original actual Tissue height grid is not hash verified.')
    with np.load(tfile, allow_pickle=False) as stored:
        uv, height = stored['uv'], stored['height']
    if (uv.ndim != 1 or height.shape != (len(uv), len(uv)) or
            not np.isfinite(height).all() or height.min() < 0 or height.max() > 1+1e-12 or
            not np.all(np.diff(uv) > 0) or uv[0] != 0 or uv[-1] != 1 or
            np.max(np.abs(np.r_[height[0], height[-1], height[:, 0], height[:, -1]])) > 1e-12):
        raise ValueError('Normalized finite Tissue grid with zero outer taper required.')
    spline = RectBivariateSpline(uv, uv, height, s=0)
    info = dict(
        mandel=dict(receipt=str(profile_receipt), receipt_sha256=sha(profile_receipt),
                    arrays=str(pfile), arrays_sha256=sha(pfile),
                    profile_sampling_sha256=profile.sha256,
                    newly_evaluated_volumetric_mandel=False),
        tissue=dict(receipt=str(tissue_receipt), receipt_sha256=sha(tissue_receipt),
                    height_grid=str(tfile), height_grid_sha256=sha(tfile),
                    historical_actual_Tissue_call=True, new_Tissue_invocations=0,
                    source_semantics='Single-valued top-height graph of the existing actual paper-origin Tissue component; overhangs/handles are not transferred.',
                    original_operator=tinfo['actual_operator']))
    return profile, spline, info


def coarse_shape(root, radius, max_analysis_faces):
    """Analyze current new G3 once; cache is bound to its real controls/code."""
    mesh, chart, info = adapter.load(root, 'G03_SIDEWALL')
    if len(mesh.faces) > max_analysis_faces:
        raise ValueError('New G3 exceeds explicit shape-analysis face budget.')
    config = EvidenceConfig(radius=radius)
    expected = dict(schema=SCHEMA, parent_control_sha256=info['control_file_sha256'],
                    parent_generation_sha256=sha(adapter.folder(root, 'G03_SIDEWALL')/'generation.json'),
                    config=asdict(config), max_analysis_faces=max_analysis_faces,
                    analyzer_sha256=sha(REPO/'src/cheshire/ornament_analysis.py'))
    cache = root/('FINE_SHAPE_G3_R'+format(radius, '.8g').replace('.', '_'))
    if cache.exists():
        receipt = read(cache/'RECEIPT.json')
        if receipt['binding'] != expected or sha(cache/'fields.npz') != receipt['fields_sha256']:
            raise ValueError('Existing G3 shape evidence has different inputs; preserve it.')
        fields = late.arrays(cache/'fields.npz')
        return fields, receipt, mesh, chart
    print('ANALYZE actual new G3', len(mesh.faces), 'quads; physical radius', radius, flush=True)
    analysis = analyze_ornament_shape(mesh.xyz, mesh.faces, config=config)
    face_weights = analysis['face_shape_weights']
    pairs = late.pairs(root, 'G03_SIDEWALL', mesh)
    # Canonicalize scalar evidence by actual IDs, without averaging source XYZ.
    face_ids = np.arange(len(mesh.faces))
    px, py = pairs['mirror_x_face_pairs'], pairs['mirror_y_face_pairs']
    rep = np.minimum(np.minimum(face_ids, px), np.minimum(py, px[py]))
    face_weights = face_weights[rep]
    face_flow = analysis['candidate_flow_confidence'][rep]
    face_quality = analysis['face_classification_fit_quality'][rep]
    fields = dict(face_shape_weights=face_weights,
                  candidate_flow_confidence=face_flow,
                  classification_fit_quality=face_quality,
                  face_direction_coherence=analysis['face_direction_coherence'][rep])
    cache.mkdir(parents=True)
    np.savez_compressed(cache/'fields.npz', **fields)
    receipt = dict(binding=expected, fields_sha256=sha(cache/'fields.npz'),
                   metadata=analysis['metadata'],
                   canonical_scalar_transport='Minimum-ID actual X/Y face orbit; no old geometry and no XYZ averaging.',
                   class_mean_weights=face_weights.mean(axis=0).tolist(),
                   fit_quality_quantiles=np.quantile(face_quality, [0, .5, .9, 1]).tolist(),
                   actual_shape_remeasured=True, lineage_or_feature_birth_claimed=False)
    late.core.write(cache/'RECEIPT.json', receipt)
    del analysis
    gc.collect()
    return fields, receipt, mesh, chart


def inherited_fields(root, generation, fields, g3_mesh):
    """Actual saved parent_face composition, independent of native face IDs."""
    values = dict(fields)
    parent_count = len(g3_mesh.faces)
    ancestry = []
    for stage in CC_STAGES[:generation-3]:
        info = adapter.checked_files(root, stage)
        path = adapter.folder(root, stage)
        with np.load(path/'evidence.npz', allow_pickle=False) as stored:
            parent = stored['parent_face']
        if (parent.ndim != 1 or parent.dtype.kind not in 'iu' or not len(parent) or
                parent.min() < 0 or parent.max() >= parent_count or
                not np.all(np.bincount(parent, minlength=parent_count) == 4)):
            raise ValueError('Actual complete CC face ancestry required: '+stage)
        values = {key: value[parent] for key, value in values.items()}
        ancestry.append(dict(stage=stage, evidence_sha256=info['evidence_file_sha256'],
                             parent_face_sha256=ah(parent), parent_count=parent_count,
                             child_count=len(parent)))
        parent_count = len(parent)
    return values, ancestry


def flow_frame(root, mesh):
    """Use the new late inherited phase and current physical height/positions."""
    if mesh.generation == 6:
        path = adapter.folder(root, 'G06_MIDDLE')/'evidence.npz'
        keys = ('directional_phase', 'frame_normalized_z')
    elif mesh.generation == 7:
        path = adapter.folder(root, 'G07_SURFACE')/'evidence.npz'
        keys = ('parent_phase', 'normalized_z')
    else:
        raise ValueError('Actual G6 or G7 controls required.')
    with np.load(path, allow_pickle=False) as stored:
        phase, inherited_z = stored[keys[0]], stored[keys[1]]
    if (phase.shape != (len(mesh.xyz),) or inherited_z.shape != phase.shape or
            not np.isfinite(phase).all() or not np.isfinite(inherited_z).all()):
        raise ValueError('New candidate late flow frame does not match actual input.')
    return phase, inherited_z, dict(path=str(path), sha256=sha(path),
        phase_key=keys[0], height_key=keys[1],
        scope='New candidate actual late phase is inherited. Longitudinal physical distance uses current host Z. No old final XYZ or historical UV atlas is read.')


def orbit_safe_output(mesh, pairs, result, max_passes=32):
    """Transport only new relief; recheck native orientation after transport."""
    ids, vp = late.whole._mirror_pairs(dict(X=pairs['mirror_x_vertex_pairs'],
                                          Y=pairs['mirror_y_vertex_pairs']), len(mesh.xyz))
    delta, rep, _fx, _fy = late.whole._transport(
        result['normals']*result['actual_height'][:, None], ids, vp)
    fixed = result['fixed_mask']
    delta[fixed] = 0
    gain = np.ones(len(mesh.xyz))
    counts = []
    for _iteration in range(max_passes):
        out = mesh.xyz+delta*gain[:, None]
        out[fixed] = mesh.xyz[fixed]
        bad = ornament._bad_faces(out, mesh.faces, mesh.xyz, 65536)
        counts.append(int(np.count_nonzero(bad)))
        if not bad.any():
            return out, delta*gain[:, None], gain, counts
        hit = np.zeros(len(mesh.xyz), dtype=bool)
        hit[mesh.faces[bad].ravel()] = True
        hit |= hit[vp['X']] | hit[vp['Y']] | hit[vp['X'][vp['Y']]]
        gain[hit] *= .5
    raise ValueError('Post-reflection new-increment orientation recovery exhausted.')


def run(args):
    root = args.root.resolve()
    target = adapter.folder(root, args.output_stage)
    if target.exists():
        raise FileExistsError('Previous stage is preserved: '+str(target))
    started = time.perf_counter()
    mesh, chart, parent_info = adapter.load(root, args.input_stage)
    if mesh.generation not in (6, 7) or len(mesh.faces) > args.max_faces:
        raise ValueError('Actual G6/G7 input must fit the explicit --max-faces budget.')
    profile, tissue, source_info = sources(args.profile.resolve(), args.tissue.resolve())
    coarse, analysis_receipt, coarse_mesh, coarse_chart = coarse_shape(
        root, args.radius, args.max_analysis_faces)
    fields, ancestry = inherited_fields(root, mesh.generation, coarse, coarse_mesh)
    if len(fields['face_shape_weights']) != len(mesh.faces):
        raise ValueError('Input is not a descendant of the recorded actual CC parents.')
    weights, supported = face_fields_to_vertices(mesh.faces, fields['face_shape_weights'], len(mesh.xyz))
    coarse_flow, _ = face_fields_to_vertices(mesh.faces, fields['candidate_flow_confidence'], len(mesh.xyz))
    if not supported.all():
        raise ValueError('Actual host has unclassified orphan vertices.')
    weights /= weights.sum(axis=1)[:, None]
    phase, inherited_z, frame_receipt = flow_frame(root, mesh)
    pairs = late.pairs(root, args.input_stage, mesh)
    vertex_ids, vp = late.whole._mirror_pairs(dict(X=pairs['mirror_x_vertex_pairs'],
                                                Y=pairs['mirror_y_vertex_pairs']), len(mesh.xyz))
    rep = np.minimum(np.minimum(vertex_ids, vp['X']), np.minimum(vp['Y'], vp['X'][vp['Y']]))
    weights, coarse_flow, phase = weights[rep], coarse_flow[rep], phase[rep]
    height = float(np.ptp(mesh.xyz[:, 2]))
    physical_z = (mesh.xyz[:, 2]-float(mesh.xyz[:, 2].min()))[rep]
    # A 2*pi phase seam is exactly one radial-profile longitude period.
    uv = np.column_stack((physical_z, phase/(2*np.pi)*args.mandel_period))
    tissue_height = np.clip(tissue.ev(np.mod(physical_z/args.tissue_period, 1.),
                                    np.mod(phase/(2*np.pi), 1.)), 0., 1.)
    tissue_priority = np.clip(weights@np.array([.12, .30, .12, .68, .88]), 0., .9)
    # Preserve readable coherent-fold crests by attenuation, not an old mask.
    crest = (.5+.5*np.cos(phase))**8
    flow = np.clip(.35*weights[:, 2]+.20*coarse_flow+.15*crest*weights[:, 2], 0., .65)
    tmin, tmax = float(coarse_chart[:, 0].min()), float(coarse_chart[:, 0].max())
    caps = (np.isclose(chart[:, 0], tmin, atol=1e-12, rtol=0) |
            np.isclose(chart[:, 0], tmax, atol=1e-12, rtol=0))[rep]
    recipe = ornament.OrnamentRecipe(
        mandel_period=args.mandel_period,
        class_amplitudes=(.022, .020, .009, .021, .023),
        class_tissue_priorities=(.12, .30, .12, .68, .88),
        tissue_amplitude=args.tissue_amplitude, valley_amplitude=.004,
        normal_safety_ratio=.35, max_faces=args.max_faces)
    print('ORNAMENT actual G'+str(mesh.generation), len(mesh.faces),
          'quads; actual finite Mandel + existing Tissue height', flush=True)
    result = ornament.apply_adaptive_ornament(
        mesh.xyz, mesh.faces, shape_weights=weights, pattern_coordinates=uv,
        profile=profile, recipe=recipe, tissue_height=tissue_height,
        tissue_priority=tissue_priority, flow_protection=flow, cap_mask=caps)
    output_xyz, delta, post_gain, post_bad = orbit_safe_output(mesh, pairs, result)
    out = late.core.ArrayMesh(output_xyz, mesh.faces, mesh.classes,
                             mesh.rest, mesh.anchors, mesh.generation)
    out.surface = 'mean'
    symmetry = late.loader.actual_symmetry(out, pairs)
    if not np.array_equal(out.xyz[caps], mesh.xyz[caps]):
        raise ValueError('Original end cap coordinates changed.')
    metadata = dict(
        schema=SCHEMA, recipe=recipe.to_dict(),
        tissue_longitudinal_period=args.tissue_period,
        source_assets=source_info, analysis=analysis_receipt,
        actual_ancestry=ancestry, flow_frame=frame_receipt,
        flow_attenuation_scope='New current G3 coherent-fold weights/confidence plus new inherited late-phase crest; attenuation is not certified ridge detection.',
        shape_weight_mean=weights.mean(axis=0).tolist(),
        actual_displacement_quantiles=np.quantile(np.linalg.norm(delta, axis=1), [0, .5, .9, .99, 1]).tolist(),
        tissue_priority_quantiles=np.quantile(tissue_priority, [0, .5, .9, 1]).tolist(),
        cap_frozen_control_count=int(caps.sum()),
        orientation_recovery_bad_face_counts=result['recovery_bad_face_counts'],
        post_mirror_recovery_bad_face_counts=post_bad,
        physical_host_height=height, host_normals_recomputed=True,
        host_shape_analysis_generation=3, host_shape_remeasured=True,
        old_final_xyz_read_or_pulled_back=False,
        added_subdivision_passes=0, added_topology_events=0,
        added_through_holes=0, new_Tissue_invocations=0,
        full_XYZ_tissue_graft=False, single_valued_Tissue_height_relief=True,
        baseline_geometry_smoothed=False,
        self_intersection='NOT_CHECKED_EXPLORATORY', fabrication='NOT_CHECKED')
    source = adapter.folder(root, args.input_stage)
    context = dict(
        input_case=parent_info.get('input_case', 'EARLY_DYNAMIC'),
        candidate=parent_info.get('dynamic_candidate', parent_info.get('candidate', root.name)),
        stage_id=args.output_stage, parent_stage=str(source), source=str(source),
        source_control_sha256=parent_info['control_file_sha256'],
        source_generation_json_sha256=sha(source/'generation.json'),
        operator_metadata=metadata, symmetry=symmetry,
        geometry_code_sha256={path.relative_to(REPO).as_posix(): sha(path) for path in (
            Path(__file__).resolve(), HERE/'late_detail_adapter.py',
            REPO/'src/cheshire/adaptive_ornament.py', REPO/'src/cheshire/ornament_analysis.py')},
        self_intersection='NOT_CHECKED_EXPLORATORY', fabrication='NOT_CHECKED')
    state = dict(
        pattern_coordinates=uv, shape_weights=weights,
        tissue_height=tissue_height, tissue_priority=tissue_priority,
        flow_attenuation=flow, cap_mask=caps,
        source_height=result['source_height'], desired_height=result['desired_height'],
        actual_increment=delta, local_gain=result['local_gain'], post_mirror_gain=post_gain,
        inherited_late_phase=phase, inherited_late_normalized_z=inherited_z,
        **pairs)
    # Drop large transient normal/graph/recovery arrays before native integrity.
    del result, coarse_mesh, coarse_chart, coarse, fields, weights, coarse_flow
    gc.collect()
    record = late.core.save(target, out, chart, context, state)
    with np.load(target/'control_quad.npz', allow_pickle=False) as saved:
        if not np.array_equal(saved['xyz'], out.xyz) or not np.array_equal(saved['faces'], mesh.faces):
            raise ValueError('Actual ornament controls readback differs.')
    receipt = dict(schema=SCHEMA, status='PASS', elapsed_seconds=time.perf_counter()-started,
                   generation_json_sha256=sha(target/'generation.json'),
                   actual_control_sha256=record['control_file_sha256'],
                   actual_geometry_sha256=record['geometry_file_sha256'],
                   source_assets=source_info, source_control_sha256=parent_info['control_file_sha256'],
                   added_through_holes=0, original_end_caps_bitwise_exact=True,
                   baseline_geometry_smoothed=False, old_final_xyz_read_or_pulled_back=False,
                   self_intersection='NOT_CHECKED_EXPLORATORY', fabrication='NOT_CHECKED')
    late.core.write(target/'ORNAMENT_EXECUTION_RECEIPT.json', receipt)
    print('DONE ACTUAL-PARENT ORNAMENT', args.output_stage,
          'seconds='+str(round(receipt['elapsed_seconds'], 3)), flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--input-stage', choices=('G06_MIDDLE', 'G07_FINAL'), default='G06_MIDDLE')
    parser.add_argument('--output-stage', default='G06_ORNAMENT')
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE)
    parser.add_argument('--tissue', type=Path, default=DEFAULT_TISSUE)
    parser.add_argument('--radius', type=float, default=.30)
    parser.add_argument('--mandel-period', type=float, default=.24)
    parser.add_argument('--tissue-period', type=float, default=.48)
    parser.add_argument('--tissue-amplitude', type=float, default=.060)
    parser.add_argument('--max-faces', type=int, default=2_000_000)
    parser.add_argument('--max-analysis-faces', type=int, default=100_000)
    args = parser.parse_args()
    if (min(args.radius, args.mandel_period, args.tissue_period) <= 0 or
            args.tissue_amplitude < 0 or min(args.max_faces, args.max_analysis_faces) < 1 or
            Path(args.output_stage).name != args.output_stage):
        parser.error('Positive physical parameters/budgets and a simple output stage name required.')
    run(args)


if __name__ == '__main__':
    main()
