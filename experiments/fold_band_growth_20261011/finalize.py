"""Copy only compact review images/records; all large geometry stays on E:."""
from pathlib import Path
import json
import shutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ROOT = Path('E:/CHESHIRE_DATA/fold_band_growth_20261011')
DOC = REPO / 'docs/fold_band_growth_20261011'
NAMES = ('BAND_COUPLED', 'BAND_REGIONAL', 'ROLE_VERTEX_FACE',
         'ROLE_EDGE_FACE', 'ROLE_SPARSE_VERTEX_FACE', 'ROLE_ABSOLUTE',
         'FIELD_SEED', 'CURVE_CIRCLE', 'CURVE_SWEEP', 'MASS_CURVE', 'FULL_LOOP',
         'RADIAL_SPARSE', 'QUAD_NEAREST', 'TRI_NEAREST', 'DUAL_FIELD_LOOP',
         'FIELD_STAGED', 'ANCESTRY_LOOP', 'ANCESTRY_STAGED', 'ANCESTRY_RETURN')
COMPACT_IMAGES = (
    'selected_directions.png', 'ANCESTRY_LOOP_progression.png',
    'ANCESTRY_STAGED_progression.png', 'DUAL_FIELD_LOOP_progression.png',
    'authored_return_comparison.png', 'late_mechanisms_G2.png',
    'radial_failure.png', 'topology_G02_comparison.png',
    'band_final_comparison.png', 'curve_hybrid_comparison.png',
    'integrated_loop_comparison.png', 'role_absolute_selection.png',
    'mass_curve_failure.png', 'ancestry_staged_final.png')


def main():
    (DOC / 'images').mkdir(parents=True, exist_ok=True)
    (DOC / 'technical').mkdir(exist_ok=True)
    for name in COMPACT_IMAGES:
        image = ROOT / 'review' / name
        shutil.copy2(image, DOC / 'images' / image.name)
    for record in (ROOT / 'review').glob('*.json'):
        shutil.copy2(record, DOC / 'technical' / record.name)
    shutil.copy2(HERE / 'research_notes.md', DOC / 'SOURCE_NOTES.md')
    for memo in (ROOT / 'visual_review').glob('*.md'):
        shutil.copy2(memo, DOC / 'technical' / memo.name)
    artifacts = {}
    for name in NAMES:
        artifacts[name] = {}
        for stage in sorted((ROOT / name).glob('G[0-9][0-9]')):
            artifacts[name][stage.name] = {
                'actual_mesh': str(stage / 'gate.ply'),
                'authoritative_geometry': str(stage / 'geometry.npz'),
                'checkpoint': str(stage / 'checkpoint.npz'),
                'operation_fields': str(stage / 'operation_fields.npz'),
                'generation_record': str(stage / 'generation.json'),
                'blender_scene': str(stage / 'column.blend'),
                'renders': {v: str(stage / 'preview' / (v + '.png'))
                            for v in ('front', 'oblique', 'side')},
            }
            controls = [stage / n for n in ('control_quad.npz', 'control_poly.npz', 'checkpoint.npz')]
            control = next(p for p in controls if p.exists())
            artifacts[name][stage.name]['next_generation_control'] = str(control)
            artifacts[name][stage.name]['control_topology'] = {
                'control_quad.npz': 'quad', 'control_poly.npz': 'mixed polygon',
                'checkpoint.npz': 'triangle'}[control.name]
            if (stage / 'ds_lineage.npz').exists():
                artifacts[name][stage.name]['DS_lineage'] = str(stage / 'ds_lineage.npz')
                artifacts[name][stage.name]['DS_operator_log'] = str(stage / 'ds_operator_log.json')
            if (stage / 'core_validation.json').exists():
                artifacts[name][stage.name]['core_validation'] = str(stage / 'core_validation.json')
            if (stage / 'attractor_curves.npz').exists():
                artifacts[name][stage.name]['attractor_curves'] = str(stage / 'attractor_curves.npz')
    index = dict(output_root=str(ROOT), branch='experiment/fold-band-growth-20261011',
                 predecessor_commit='d724e65', actual_artifacts=artifacts,
                 sources=dict(fine='E:/CHESHIRE_DATA/column_development_20261011/inputs/SPAN_R2/G00',
                              coarse='E:/CHESHIRE_DATA/column_development_20261011/inputs/SPAN_COARSE/G00',
                              sparse=str(ROOT / 'inputs/SPAN_SPARSE/G00')),
                 source_code=str(HERE), source_notes=str(DOC / 'SOURCE_NOTES.md'),
                 full_review_images=str(ROOT / 'review'), compact_review_images=list(COMPACT_IMAGES),
                 core_checks=str(DOC / 'technical/core_validation.json'),
                 representative='ANCESTRY_STAGED/G03', co_lead='ANCESTRY_LOOP/G03',
                 quieter_comparison='ANCESTRY_LOOP/G02',
                 geometric_cell_comparison='DUAL_FIELD_LOOP/G02',
                 prior_role_comparison=['ROLE_ABSOLUTE/G02', 'ROLE_ABSOLUTE/G03'],
                 field_comparison='BAND_COUPLED/G03',
                 public_flow_comparisons=['CURVE_CIRCLE/G02', 'CURVE_SWEEP/G02'],
                 public_flow_count='FIELD_SEED/G01: one split+field pass; curve G01/G02: two further split+role passes. Total growth three, finite field evaluated once at 18 internal escape iterations.',
                 integrated_loop='FULL_LOOP/G03: three cycles, each with ONE quad split + circle-activated V/F placement + finite field reevaluation. Three paired cycles, not six growth cycles.',
                 stopped_failure='MASS_CURVE/G01: common normal response changed the mass but weakened the deep folds; G2 was not generated.',
                 late_branch_stops=dict(RADIAL_SPARSE='G2: sawtooth/thorn bands; no G3',
                     QUAD_NEAREST='G2: topology comparison only, weak macro/meso gain; no G3',
                     TRI_NEAREST='G2: topology comparison only, weak macro/meso gain; no G3',
                     DUAL_FIELD_LOOP='G3 retained as roughness limit; G2 is clearer'),
                 staged_field='FIELD_STAGED and ANCESTRY_STAGED: three growth cycles, internal finite escape iterations 4/8/18. Occupancy and targets change, not just detail frequency.',
                 authored_followup='ANCESTRY_RETURN/G03: one existing explicitly authored PCHIP waist return after the field. Not fractal-emergent folding; G1/G2 mesh-identical renders reused with a saved record. Silhouette changed, but cuff/belt interrupts continuity: not selected as a lead.',
                 format='Actual PLY + authoritative NPZ + quad checkpoint + Blender. No OBJ export in this study.',
                 next_input_variations='Deferred by user; SPAN_SPARSE is the same analytic recipe at lower sampling density, not a new input design.',
                 scope='Compact copy only, no repeated hash audit or full regressions. No geometry deletion or automatic continuation.')
    (DOC / 'INDEX.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf8')
    print('COMPACT_REVIEW_SAVED', DOC, flush=True)


if __name__ == '__main__':
    main()
