"""Review saved actual renders; core geometry checks only by explicit selection."""
from pathlib import Path
import argparse
import contextlib
import io
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'curved_fold_side_20261011'))
import review

ROOT = Path('E:/CHESHIRE_DATA/fold_band_growth_20261011')
BASE = Path('E:/CHESHIRE_DATA/column_development_20261011')


def views(path):
    return [path / 'preview' / (v + '.png') for v in review.VIEWS]


def matched(path, labels, folders, size=560):
    for folder in folders:
        for image in views(folder):
            if not image.exists():
                raise FileNotFoundError(image)
    review.board(path, labels, [(v, [f / 'preview' / (v + '.png') for f in folders])
                               for v in review.VIEWS], size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--role-flows', nargs='*', default=[])
    parser.add_argument('--extra-flows', nargs='*', default=[])
    parser.add_argument('--validate', nargs='*', default=[])
    args = parser.parse_args()
    out = args.root / 'review'
    out.mkdir(parents=True, exist_ok=True)
    flows = {name: BASE / 'inputs/SPAN_R2/G00'
             for name in ('BAND_COUPLED', 'BAND_REGIONAL')}
    for name in args.role_flows + args.extra_flows:
        record = json.loads((args.root / name / 'G01/generation.json').read_text(encoding='utf8'))
        source = Path(record['source'])
        flows[name] = source.parent if source.suffix else source
    matched(out / 'band_final_comparison.png',
            ['Independent field / G3', 'Coupled field / G3', 'Regional coupled / G3'],
            [BASE / 'SPAN_RETURN_FINE/G03', args.root / 'BAND_COUPLED/G03',
             args.root / 'BAND_REGIONAL/G03'])
    matched(out / 'band_early_comparison.png',
            ['Independent field / G1', 'Coupled field / G1', 'Regional coupled / G1'],
            [BASE / 'SPAN_RETURN_FINE/G01', args.root / 'BAND_COUPLED/G01',
             args.root / 'BAND_REGIONAL/G01'], 500)
    if args.role_flows:
        matched(out / 'role_final_comparison.png',
                ['Coarse input / G0', 'Field + return / G3'] + [n + ' / G3' for n in args.role_flows],
                [BASE / 'inputs/SPAN_COARSE/G00', BASE / 'SPAN_RETURN_COARSE/G03'] +
                [args.root / n / 'G03' for n in args.role_flows], 500)
    records = {}
    for name, source in flows.items():
        stages = sorted(p for p in (args.root / name).glob('G[0-9][0-9]')
                        if (p / 'generation.json').exists())
        input_file = source / 'generation.json'
        render_source = source
        if not input_file.exists():
            input_file = source / 'provenance.json'
            provenance = json.loads(input_file.read_text(encoding='utf8'))
            if provenance.get('exact_same_xyz_faces_chart') is not True:
                raise ValueError('Input render alias lacks exact-surface provenance: ' + str(source))
            render_source = Path(provenance['source']).parent
        folders = [render_source] + stages
        input_label = 'M1 / field-derived input' if source.parent.name == 'FIELD_SEED' else 'G0 / input'
        stage_labels = [('S' + str(i + 1)) if source.parent.name == 'FIELD_SEED' else p.name
                        for i, p in enumerate(stages)]
        matched(out / (name + '_progression.png'), [input_label] + stage_labels, folders, 440)
        records[name] = dict(source_folder=str(source), input_render_folder=str(render_source),
            input=json.loads(input_file.read_text(encoding='utf8')),
            stages={folder.name: json.loads((folder / 'generation.json').read_text(encoding='utf8'))
                    for folder in stages})
    if 'ROLE_ABSOLUTE' in args.extra_flows:
        matched(out / 'role_scale_G1_comparison.png',
                ['Sparse input / G0', 'Support scale / G1', 'Model-unit scale / G1'],
                [flows['ROLE_ABSOLUTE'], args.root / 'ROLE_SPARSE_VERTEX_FACE/G01',
                 args.root / 'ROLE_ABSOLUTE/G01'], 500)
        matched(out / 'role_absolute_selection.png',
                ['Folded input / G0', 'Model-unit offset / G2', 'Model-unit offset / G3'],
                [flows['ROLE_ABSOLUTE'], args.root / 'ROLE_ABSOLUTE/G02',
                 args.root / 'ROLE_ABSOLUTE/G03'], 560)
    if all(name in args.extra_flows for name in ('CURVE_CIRCLE', 'CURVE_SWEEP')):
        matched(out / 'curve_hybrid_comparison.png',
                ['After field / M1', 'M1 + circle / S2', 'M1 + sweep / S2'],
                [args.root / 'FIELD_SEED/G01', args.root / 'CURVE_CIRCLE/G02',
                 args.root / 'CURVE_SWEEP/G02'], 560)
        matched(out / 'curve_early_comparison.png',
                ['After field / M1', 'M1 + circle / S1', 'M1 + sweep / S1'],
                [args.root / 'FIELD_SEED/G01', args.root / 'CURVE_CIRCLE/G01',
                 args.root / 'CURVE_SWEEP/G01'], 500)
    if 'FULL_LOOP' in args.extra_flows:
        matched(out / 'integrated_loop_comparison.png',
                ['Field every cycle / G3', 'Field once + role twice', 'Role + field every cycle / G3'],
                [args.root / 'FIELD_SEED/G03', args.root / 'CURVE_CIRCLE/G02',
                 args.root / 'FULL_LOOP/G03'], 560)
    if 'MASS_CURVE' in args.extra_flows:
        matched(out / 'mass_curve_failure.png',
                ['Before common mass movement', 'Common mass movement / G1'],
                [args.root / 'FIELD_SEED/G01', args.root / 'MASS_CURVE/G01'], 560)
    if 'RADIAL_SPARSE' in args.extra_flows:
        matched(out / 'radial_failure.png',
                ['Same folded input', 'Nearest-outside / G2', 'Signed radial / G2: stopped'],
                [args.root / 'inputs/SPAN_SPARSE/G00', args.root / 'FIELD_SEED/G02',
                 args.root / 'RADIAL_SPARSE/G02'], 500)
    late = ('FULL_LOOP', 'ANCESTRY_LOOP', 'DUAL_FIELD_LOOP', 'FIELD_STAGED')
    if all(name in args.extra_flows for name in late):
        matched(out / 'late_mechanisms_G2.png',
                ['Birth-role + field / G2', 'Ancestry + field / G2',
                 'Weighted DS + field / G2', 'Staged field / G2'],
                [args.root / name / 'G02' for name in late], 500)
    if 'ANCESTRY_STAGED' in args.extra_flows:
        matched(out / 'ancestry_staged_final.png',
                ['Ancestry / fixed 18 / G3', 'Ancestry / 4-8-18 / G3'],
                [args.root / 'ANCESTRY_LOOP/G03', args.root / 'ANCESTRY_STAGED/G03'], 560)
    if 'ANCESTRY_RETURN' in args.extra_flows:
        matched(out / 'authored_return_comparison.png',
                ['Ancestry / G2', 'Ancestry / G3', 'Ancestry + authored return / G3'],
                [args.root / 'ANCESTRY_LOOP/G02', args.root / 'ANCESTRY_LOOP/G03',
                 args.root / 'ANCESTRY_RETURN/G03'], 560)
    if all(name in args.extra_flows for name in ('ANCESTRY_LOOP', 'ANCESTRY_STAGED', 'DUAL_FIELD_LOOP')):
        matched(out / 'selected_directions.png',
                ['Ancestry + staged field / G3', 'Ancestry / fixed field / G3', 'Weighted DS / G2'],
                [args.root / 'ANCESTRY_STAGED/G03', args.root / 'ANCESTRY_LOOP/G03',
                 args.root / 'DUAL_FIELD_LOOP/G02'], 560)
    check_file = out / 'core_validation.json'
    checks = json.loads(check_file.read_text(encoding='utf8')) if check_file.exists() else {}
    for name in args.validate:
        folder = args.root / name
        with contextlib.redirect_stdout(io.StringIO()):
            checks[name] = review.validate(folder)
        check = checks[name]
        print('CORE', name, check['components'], check['watertight'],
              check['mirror_max_distance'], check['self_intersection'], flush=True)
    if checks:
        review.dump(check_file, checks)
    review.dump(out / 'comparison_index.json', dict(
        root=str(args.root), baseline=str(BASE), flows=records,
        baseline_field_comparison='Same SPAN_R2 sampled input, same split/field/return schedule; new field vector coupling and activation change.',
        role_comparison='SPAN_COARSE input; role-dependent normal offsets replace field and authored return. Not an isolated scalar change or exact IAAC reproduction.',
        curve_comparison='Same FIELD_SEED actual input for circle/sweep; one earlier finite-field pass then two birth-role offset subdivisions. No field is reevaluated during the two offset stages. Physical attractor curves are fixed in model space.',
        integrated_loop_comparison='FIELD_SEED and FULL_LOOP start from the same SPAN_SPARSE sampled input and use the same field recipe/fraction/budget/target refinement. FULL_LOOP adds one circle-activated role-placement layer before field motion in EACH cycle. The sequential curve comparison changes role depth and timing too, so it is a design comparison, not a single-variable test.',
        topology_comparison='QUAD_NEAREST/TRI_NEAREST use the same actual initial triangle surface, same counts per physical stage and same coarse-target field. Quad render fans are not controls; triangle fans become controls. No original IAAC triangular rule is claimed.',
        ancestry_comparison='Existing Task36 weighted ancestry placement replaces the birth-role layer. Standard CC averaging gain is zero; weighted stencil coordinate combinations remain. Task36 terminal plane constraints are explicit and the subsequent field is free to move eligible terminal points.',
        field_staging='Internal escape schedule 4/8/18 changes finite occupancy and outside-target geometry. It is not a pure frequency filter or a recovered IAAC schedule. Growth cycles remain three.',
        authored_return='ANCESTRY_RETURN adds one existing, deliberately authored PCHIP radial/axial waist return after the G3 field. It is not a fold emerging from the fractal equation.',
        explicit_core_checks=checks,
        preserved_geometry='geometry.npz is authoritative float64; gate.ply is the exchange copy; control_quad.npz is the next-generation input.',
        render='Same existing camera, flat mesh normals and material; no image synthesis or geometric smoothing modifier.',
        fabrication='Thickness, structural capacity and fabrication NOT_CHECKED'))
    print('REVIEW_COMPLETE', str(out), flush=True)


if __name__ == '__main__':
    main()
