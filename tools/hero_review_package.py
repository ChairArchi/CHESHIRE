"""Compact Task24 review packet; full meshes remain separately accessible."""
import argparse
from copy import deepcopy
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from cross_cell_crease_study import read,write,file_hash,digest
from hero_design_views import latest
from hero_design_sprint import verify_frozen_inputs
from cheshire.artifact_root import ArtifactRoot

NAMES=['H1','H2_R1','H3_R3']


def copy(source,target):
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)


def effective_parameters(recipe):
    result=[]
    for spec in recipe['networks']:
        kind=spec['generator']
        common=dict(target_y_ratio=-.65,profile='CONSTANT',sharpness=4.)
        if kind in ('N2','N3','N4'):
            defaults=dict(common,quiet_below=.55,max_steps=80,length_ratio=.85,
                turn_cost=1.4,source_cost=.8,cell_reward=.15,dihedral_cost=.25,
                max_turn=.85,seed_xz=[-.32,.91],direction=[1.,0.,0.])
            constants=dict(trace_front_preference=.5,seed_lintel_support=.3,
                N3_seed_dihedral_reward=.65 if kind=='N3' else 0.,seed_direction_cost=.3)
        else:
            defaults=dict(common,quiet_below=.5,turn_cost=1.4,source_cost=.8,
                front_cost=.8,dihedral_cost=.25,cell_reward=.15,
                minimum_seed_support=.05 if kind=='N1' else .3,minimum_target_support=.05)
            constants=dict(positive_directed_edge_Dijkstra=True)
        effective={**defaults,**spec}
        if kind=='N5':
            sign=-1 if spec.get('side','left')=='left' else 1
            effective['architectural_arm_targets']=[[0,.96],[sign*.47,.98],[sign*.39,.56]]
        if kind=='N1':
            effective['architectural_targets']={
                'outer_lintel':[[-.46,.98],[0,1.],[.46,.98]],
                'opening_rim':[[-.28,.72],[0,.78],[.28,.72]],
                'support_shoulder_lintel':[[-.40,.60],[-.36,.90],[0,.98],[.36,.90],[.40,.60]]}[spec.get('relation','outer_lintel')]
        result.append(dict(generator=kind,effective=effective,implementation_constants=constants))
    return dict(id=recipe['id'],recipe=digest(recipe),networks=result,
        source_lintel_centroid_height=.74,source_front_normal_y=-.25,
        event_selector_defaults=dict(z_min=0.,z_max=1.5,normal_y_min=0.,area_ratio_min=0.,depth_min=0),
        event_rule='Each explicit step overrides these defaults. Normal_y test is absolute. Heights use original C0 z origin/height; selection is not a geometry clamp.',
        local_polygon_tolerance=1e-9,spacing='One immediate face-neighbor ring when spacing=1.',
        crease_decay='max(s-1,0), all listed finite integer schedules use verified COMPAS parity.',
        seed=None,parameters_inherited_from_frozen_C07='inputs/backbone.json and full frozen lineage.',
        exact_per_point_placement='designs/<id>/attempt_*/S*_operator.json.gz',
        source_of_defaults='src/cheshire/crease_routing.py, ornament.py; frozen source revision and source hashes retained.')


def package(root):
    verify_frozen_inputs(ArtifactRoot(root))
    review=root/'review';review.mkdir(parents=True,exist_ok=True)
    rows=[]
    for name in NAMES:
        directory=latest(root,name);s=read(directory/'summary.json')
        if s['status']!='SUCCESS':raise ValueError('Only completed final meshes enter the packet.')
        if not all(file_hash(directory/n)==h for n,h in s['exports'].items()):raise ValueError('Export hash mismatch.')
        native=read(root/'dcc'/(name+'_import_evidence.json'))
        if not all(native[k] for k in ['actual_native_file_read','exact_XYZ_oriented_faces','headless_RhinoDoc_open']):
            raise ValueError('Native readiness evidence missing.')
        copy(directory/(name+'.obj'),root/'meshes'/(name+'.obj'))
        copy(root/'recipes'/(name+'.json'),review/'recipes'/(name+'.json'))
        copy(directory/'summary.json',review/'verification'/(name+'_summary.json'))
        copy(root/'dcc'/(name+'_import_evidence.json'),review/'verification'/(name+'_import_evidence.json'))
        runner_hash=s['source']['source_files']['examples/hero_design_sprint.py']
        executed=root/'cache/source_snapshots'/runner_hash/'examples/hero_design_sprint.py'
        if not executed.exists() or file_hash(executed)!=runner_hash:
            raise ValueError('Actual execution runner snapshot missing.')
        copy(executed,review/'source/execution'/('hero_design_sprint_'+runner_hash+'.py'))
        rows.append(dict(id=name,design=root_relative(root,directory),
            recipe='recipes/'+name+'.json',OBJ='meshes/'+name+'.obj',
            OBJ_sha256=file_hash(root/'meshes'/(name+'.obj')),native='dcc/'+name+'.3dm',
            native_sha256=file_hash(root/'dcc'/(name+'.3dm')),statistics=s['statistics'],
            runtime_seconds=s['runtime_seconds'],source=s['source'],
            full_views='renders/final/'+name+'_multiview.png',native_clay='renders/native/'+name+'_oblique_fit.png'))
    selection=dict(status='PARTIAL',lead='H1',three_distinct_generated_compositions=True,
        three_convincing_Hero_gates_achieved=False,heroes=rows,
        reason='Distinct actual morphology and usable exports; coherent multiscale Hero quality remains below target.',
        renderer='Existing System.Drawing polygon preview; actual native .3dm reimport used for native clay; actual Rhino viewport/beauty render unverified.')
    write(root/'selection.json',selection)
    write(root/'resolved_parameters.json',[effective_parameters(read(root/'recipes'/(n+'.json'))) for n in NAMES])
    copy(ROOT/'docs/TASK24_RESULTS.md',root/'FINAL_REPORT.md')
    copy(root/'FINAL_REPORT.md',review/'FINAL_REPORT.md')
    mapping=read(root/'source_map.json')
    functions={'R20':'coherent_refinements + downstream','X10':'declare','X01':'declare','X02':'declare',
        'Y07':'continue_large_taper (X07 E2 tail)','Y19':'continue_large_taper (R19 E2 tail)'}
    text=['# Task24 verified source map','',
        'All six are complete recipes or checkpoint continuations. Supported recipe input: exact frozen C07 + its history/signatures/anchors. They are not six independently concatenable operators.','',
        '| ID | Defining function in examples/cross_cell_crease_capability.py | Recipe | Actual checkpoint | Final output | Reference views |',
        '|---|---|---|---|---|---|']
    for r in mapping:
        text.append('| '+r['id']+' | '+functions[r['id']]+' | references/'+r['id']+'.json | '+r['checkpoint']+' | '+r['output_stage']+' | references/'+r['id']+'_oblique.png |')
        for view in ('front','oblique','node'):
            p=Path(r['images'][('front','oblique','node').index(view)])
            if p.exists():copy(p,review/'references'/(r['id']+'_'+view+'.png'))
        copy(root/'references'/(r['id']+'.json'),review/'references'/(r['id']+'.json'))
    text.extend(['','Execution: cross_cell_crease_study.load/choose_faces/terminal_networks; CreaseRouter.generate; folded_crease_once; vocabulary_event. Geometry checkpoints retain actual mesh, positive construction history/events, anchors, branch signatures and surviving crease fragments. Affected event edges have no implemented crease semantics.','',
        'Y19 order = relative visual judgment of matched normal offsets and selective downstream events, not a sorting or spatial-field algorithm.','',
        'C0 origin: examples/carrier_scale_study.py:initialise + rhino/carrier_study.py:coarse_gate. Fixed architectural dimensions, origin measured from the prior dense gate. Original physical units / ALICE mesh identity are not present.'])
    (root/'SOURCE_MAP.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    copy(root/'SOURCE_MAP.md',review/'SOURCE_MAP.md')
    for p in (root/'inputs').iterdir():copy(p,review/'inputs'/p.name)
    for n in ['selection.json','input_identity.json','provenance_resolution.json','source_map.json',
        'resolved_parameters.json','independent_reproduction.json','crown_reproduction.json',
        'geometry_observations.json','revision_decisions.json']:
        if (root/n).exists():copy(root/n,review/n)
    for p in (root/'renders/final').glob('*.png'):copy(p,review/'images'/p.name)
    copy(root/'renders/final/camera_manifest.json',review/'images/camera_manifest.json')
    for name in NAMES:
        copy(root/'renders/native'/(name+'_oblique_fit.png'),review/'images'/(name+'_native_clay.png'))
    copy(root/'renders/native/camera_manifest.json',review/'images/native_camera_manifest.json')
    copy(root/'dcc/viewport_attempt.json',review/'verification/viewport_attempt.json')
    copy(ROOT/'output/task24_pytest_final.txt',review/'verification/full_pytest.txt')
    for folder,pattern in [('examples','hero_design_*.py'),('tools','hero_*.*'),('tests','test_hero_composition.py')]:
        for p in (ROOT/folder).glob(pattern):copy(p,review/'source'/folder/p.name)
    copy(ROOT/'docs/TASK24_RESULTS.md',review/'source/docs/TASK24_RESULTS.md')
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    changed=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
    revision=dict(baseline='140932fb6cbcaec4a1d27665fb99bf0e0a806fc3',source_commit=sha,
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
        working_tree_clean=not changed,
        execution_note='Generation occurred at the baseline plus Task24 source file bytes; requests record both. Final commit records the released source. No remote publication.',
        task24_source_sha256={p.relative_to(ROOT).as_posix():file_hash(p) for p in
            [ROOT/'examples/hero_design_sprint.py',ROOT/'examples/hero_design_views.py',ROOT/'tools/hero_rhino_export.ps1',
             ROOT/'tools/hero_review_package.py',ROOT/'tests/test_hero_composition.py',ROOT/'docs/TASK24_RESULTS.md']})
    write(root/'source_revision.json',revision);copy(root/'source_revision.json',review/'source_revision.json')
    with (root/'FINAL_REPORT.md').open('a',encoding='utf-8') as stream:
        stream.write('\nFinal source revision: `'+sha+'`; branch `'+revision['branch']+'`.\n')
    copy(root/'FINAL_REPORT.md',review/'FINAL_REPORT.md')
    manifest={root_relative(review,p):dict(bytes=p.stat().st_size,sha256=file_hash(p))
        for p in sorted(review.rglob('*')) if p.is_file() and p.name!='package_manifest.json'}
    if any(Path(n).suffix.lower() in ('.dll','.obj','.3dm') for n in manifest):
        raise ValueError('Heavy meshes / DLL must stay out of compact review packet.')
    write(review/'package_manifest.json',manifest)
    archive=root/'CHESHIRE_TASK24_REVIEW.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(review.rglob('*')):
            if p.is_file():z.write(p,root_relative(review,p))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('Review ZIP CRC failed.')
    record=dict(file=str(archive),bytes=archive.stat().st_size,sha256=file_hash(archive),files=len(manifest)+1,
        native_files=[str(root/'dcc'/(n+'.3dm')) for n in NAMES],meshes_separate=True)
    write(root/'review_archive.json',record)
    print(record,flush=True)
    return selection,revision


def root_relative(root,path):return path.relative_to(root).as_posix()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    package(a.output_root.resolve())
