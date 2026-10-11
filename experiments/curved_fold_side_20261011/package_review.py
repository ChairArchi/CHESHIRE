"""Small local review package. No raw geometry, hash audit or publication."""
from pathlib import Path
import json,shutil,sys
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import review
ROOT=review.ROOT;TREE=HERE.parents[1]
DOC=TREE/'docs/curved_fold_side_20261011'

def main():
    out=ROOT/'review';out.mkdir(exist_ok=True)
    def imgs(p):return [p/'preview'/(v+'.png') for v in review.VIEWS]
    old=review.OLD/'A_FOLD/G03';lead=ROOT/'P06_CREASE_MESH/G03'
    review.board(out/'A_vs_P06_three_views.png',review.VIEWS,[('A original: retained reference',imgs(old)),('P06: same fold locations/amplitudes, connected panels + crease mesh',imgs(lead))],700)
    review.board(out/'side_construction_comparison.png',['A original','P02: connected transition','P06: crease-conforming mesh'],
                 [('Side / same camera',[old/'preview/side.png',ROOT/'P02_CONNECTED_PANELS/G03/preview/side.png',lead/'preview/side.png'])],650)
    review.board(out/'P02_P06_matched_formula.png',['P02: uniform material sampling','P06: crease-conforming sampling'],
                 [(v,[ROOT/'P02_CONNECTED_PANELS/G03/preview'/(v+'.png'),lead/'preview'/(v+'.png')]) for v in review.VIEWS],500)
    # Position memory on same actual triangulation across P06 generations.
    g1=np.load(ROOT/'P06_CREASE_MESH/G01/checkpoint.npz');g3=np.load(lead/'checkpoint.npz')
    core=g1['memory']>=1-1e-12;delta=np.linalg.norm(g3['xyz']-g1['xyz'],axis=1)
    review.dump(out/'P06_memory.json',dict(G1_protected_core_vertices=int(core.sum()),G1_to_G3_core_max_movement=float(delta[core].max()),
        same_triangle_connectivity=bool(np.array_equal(g1['faces'],g3['faces'])),scope='Position retention only; fold angles and intrinsic metric not preserved.'))
    # Reuse final checks, record the unchanged area criterion without repeating CGAL.
    records=json.loads((out/'core_validation.json').read_text(encoding='utf8'))
    for record in records:
        record['minimum_area_threshold']=1e-12;record['minimum_area_pass']=record['minimum_triangle_area']>1e-12
        # Preserve failures in the same criteria; field trials do not pass.
    review.dump(out/'core_validation.json',records)
    trials=[]
    for p in sorted(ROOT.glob('*/G*/generation.json')):
        item=json.loads(p.read_text(encoding='utf8'));item['folder']=str(p.parent)
        item['rendered_views']=[v for v in review.VIEWS if (p.parent/'preview'/(v+'.png')).exists()]
        if (p.parent/'core_validation.json').exists():item['final_validation']=json.loads((p.parent/'core_validation.json').read_text(encoding='utf8'))
        trials.append(item)
    review.dump(out/'trial_index.json',trials)
    review.dump(out/'failed_trials.json',[
        dict(trial='C02 / C07 per-panel concavity',result='Not selected: repeated horizontal scallops/ribs, contrary to fold hierarchy goal.'),
        dict(trial='R01/R02/R04 developable inputs + reflection',result='Metric principle demonstrated; simple stepped pipes, insufficient A fold language. No precise intersection checks on these intermediate controls.'),
        dict(trial='P04/P05 meridian reconstruction',result='Guide positions retained exactly, but sparse guides polygonize front and lose fine valleys. Not selected.'),
        dict(trial='P06 initial full-domain clipping',result='Stopped before export: asymmetric tessellation at crossing curves, reflected chart pairing max distance 0.00813391622838586. Fixed by canonical-half construction, not averaging.'),
        dict(trial='P06 final',result='Partial visual improvement, not a complete success. Upper multi-fold junction remains fragmented; exact checker confirms intersection near z=7.67.'),
        dict(trial='R03 final',result='Strong fold but blunt large kinks, intersection confirmed. Reflected vertices match; clipped triangle sets do not exactly match. Not selected as lead.'),
        dict(trial='V03/W01 added valley',result='Y symmetry discrepancy found after adding swept valley map. Preserved unchanged. V04/W06 keep the front and rebuild the reflected half; no averaging.'),
        dict(trial='W02 amplification',result='Amplified nearby later folds, not the thin striations the user subsequently marked. Preserved as a different experiment, not the requested solution.'),
        dict(trial='W05 strong pleats',result='Controlled real pleats, but stronger amplitude reads as a conspicuous grille. Retained diagnostic, not lead.'),
        dict(trial='F_V04/F_W06 field follow-up',result='Macro landmarks survive, but broad nearest-outside movement produces angular rocky facets and modifies surrounding valleys. G1/G2 minimum-area criterion fails; intersections confirmed at G2. Not the recommended aesthetic path.'),
        dict(trial='GEO03 additional nested return',result='Existing local return operators work beside protected features, but visual gain over GEO01 is limited. Do not call this a new successful design generation.')])
    DOC.mkdir(parents=True,exist_ok=True);images=DOC/'images';images.mkdir(exist_ok=True)
    names=['A_vs_P06_three_views.png','side_construction_comparison.png','P02_P06_matched_formula.png',
           'curve_catalogue.png','reflection_catalogue.png','A_repair_catalogue.png','matched_sampling.png',
           'P06_CREASE_MESH_progression.png','C04_OBLIQUE_CREASE_views.png','actual_sections.png','A_preserved_silhouettes.png',
           'side_symmetry_catalogue.png','T01_radical_progression.png','soft_vs_angular.png','older_to_current.png',
           'valley_pleats_comparison.png','valley_pleats_detail.png','marked_striation_diagnosis.png',
           'V04_SYMMETRIC_CUP_field_progression.png','W06_SYMMETRIC_SMOOTH_field_progression.png',
           'GEO01_FAN_MEMORY_progression.png','GEO02_CHEVRON_MEMORY_progression.png',
           'final_geometric_comparison.png','recommended_views.png','current_actual_sections.png']
    for name in names:shutil.copy2(out/name,images/name)
    technical=DOC/'technical';technical.mkdir(exist_ok=True)
    for name in ['core_validation.json','trial_index.json','failed_trials.json','sampling_diagnostics.json','A_repair_dihedral_diagnostics.json',
                 'conforming_formula_check.json','silhouette_differences.json','P06_memory.json','T01_memory.json',
                 'marked_striation_diagnosis.json','local_pleat_intersections.json','current_fold_retention.json']:
        shutil.copy2(out/name,technical/name)
    review.dump(DOC/'INDEX.json',dict(branch='experiment/curved-fold-side-20261011',base_commit='2d9d602f619448aa416faf79ae8bba29f7aff9cf',
        output_root=str(ROOT),previous_reference=str(old),candidate_endpoints=len({r['candidate'] for r in trials}),stored_mesh_checkpoints=len(trials),
        primary=dict(folder=str(ROOT/'GEO01_FAN_MEMORY/G03'),actual_mesh=str(ROOT/'GEO01_FAN_MEMORY/G03/gate.ply'),
                     authoritative_float64=str(ROOT/'GEO01_FAN_MEMORY/G03/geometry.npz'),checkpoint=str(ROOT/'GEO01_FAN_MEMORY/G03/checkpoint.npz'),
                     blender_scene=str(ROOT/'GEO01_FAN_MEMORY/G03/column.blend'),status='Design exploration: self-intersection confirmed; not fabrication validated'),
        retained_comparisons=['W06_SYMMETRIC_SMOOTH/G01','GEO02_CHEVRON_MEMORY/G03','GEO03_NESTED_RETURN/G01','F_W06_SYMMETRIC_SMOOTH/G02'],
        principle_reference=str(ROOT/'C04_OBLIQUE_CREASE/G02'),research=str(HERE/'RESEARCH.md'),publication='LOCAL_ONLY',
        camera=dict(front=[0,32,5],oblique=[-18,28,16],side=[-32,0,5],target=[0,0,5],orthographic_scale=12,resolution=800,samples=16),
        rendering='Actual stored triangle mesh, geometric flat normals, uniform material; no normal maps, textures, smoothing modifiers or generated images.',
        raw_geometry_policy='E drive only; small review package contains source, images and JSON.' ))
    copies=ROOT/'source_final';copies.mkdir(exist_ok=True)
    for p in HERE.iterdir():
        if p.suffix in ('.py','.md'):shutil.copy2(p,copies/p.name)
    print('PACKAGED',DOC,'checkpoints',len(trials),flush=True)
if __name__=='__main__':main()
