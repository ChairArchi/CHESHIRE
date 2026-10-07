"""Build the Task25 review/model packets from completed files, never geometry.

Review images remain labelled polygon projections; native reread evidence is
separate. Every included payload is hashed and both ZIPs are actually reread.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'examples'))
from cross_cell_crease_study import read,write,file_hash

SOURCE_FILES=[
    'examples/generational_folding.py','examples/hero_design_sprint.py',
    'src/cheshire/crease_folding.py','src/cheshire/fold_continuation.py',
    'src/cheshire/fold_placement.py','tests/test_fold_continuation.py',
    'tools/folding_native.ps1','tools/folding_views.py',
    'tools/lintel_ancestry.py','tools/folding_review_package.py',
    'tools/folding_geometry_evidence.py',
]


def measurements(root):
    rows=[]
    for path in sorted((root/'designs').glob('*/attempt_*/summary.json')):
        summary=read(path);directory=path.parent;name=directory.parent.name
        row=dict(id=name,attempt=directory.name,status=summary['status'],
            summary=str(path),summary_sha256=file_hash(path))
        if summary['status']=='SUCCESS':
            for filename,record in summary['artifacts'].items():
                actual=directory/filename
                if actual.stat().st_size!=record['bytes'] or file_hash(actual)!=record['sha256']:
                    raise ValueError('Actual completed artifact changed: '+str(actual))
            row.update(statistics=summary['statistics'],times=summary['times'],
                elapsed_operation_to_exports_seconds=summary['elapsed_seconds'],
                resource_forecast=summary['resource_forecast'],generation=summary['generation'],
                OBJ_validation=summary['OBJ_validation'],artifacts=summary['artifacts'])
            if directory==sorted(directory.parent.glob('attempt_*'))[-1]:
                row['process']=read(root/'logs'/name/'process.json')
        else:
            row.update(reason=summary['reason'],last_preserved_input=summary['last_preserved_input'])
            if (directory/'resource_preflight.json').exists():
                row['resource_forecast']=read(directory/'resource_preflight.json')
        rows.append(row)
    write(root/'analysis/measurements.json',dict(records=rows,
        scope='Generator process-tree plus driver peak is sampled by the existing guard. Native host measurement is separate. No shader/renderer RAM inferred from generator peak.'))
    return rows


def archive(path,files):
    entries={}
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as packet:
        for name,source in sorted(files.items()):
            packet.write(source,name)
            entries[name]=dict(bytes=source.stat().st_size,sha256=file_hash(source))
        packet.writestr('PACKET_MANIFEST.json',json.dumps(dict(payloads=entries,
            scope='All payloads except this self-describing manifest.'),indent=2))
    with zipfile.ZipFile(path) as actual:
        if actual.testzip() is not None:raise ValueError('ZIP CRC failure.')
        for name,record in entries.items():
            data=actual.read(name)
            if len(data)!=record['bytes'] or sha256(data).hexdigest()!=record['sha256']:
                raise ValueError('Actual ZIP payload differs: '+name)
    return dict(path=str(path),bytes=path.stat().st_size,sha256=file_hash(path),
        actual_ZIP_CRC_and_payload_hashes=True,payload_count=len(entries))


def package(root,lead,attempt):
    measurements(root)
    checkpoint=root/'designs'/lead/attempt
    summary=read(checkpoint/'summary.json')
    if summary['status']!='SUCCESS':raise ValueError('Lead must be an actual completed whole gate.')
    native=root/'dcc'/(lead+'.3dm');proof=read(root/'dcc'/(lead+'_import_evidence.json'))
    if not all(proof[k] for k in ('actual_native_file_read','exact_XYZ_oriented_faces','headless_document_open')):
        raise ValueError('Native opening/reread missing.')
    if proof['native_sha256']!=file_hash(native) or proof['OBJ_sha256']!=file_hash(checkpoint/(lead+'.obj')):
        raise ValueError('Selected native evidence does not match actual files.')
    (root/'meshes').mkdir(exist_ok=True);lead_obj=root/'meshes'/(lead+'.obj')
    if lead_obj.exists() and file_hash(lead_obj)!=file_hash(checkpoint/(lead+'.obj')):
        raise ValueError('Existing named lead OBJ differs; preserve it rather than overwrite.')
    if not lead_obj.exists():shutil.copyfile(checkpoint/(lead+'.obj'),lead_obj)
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    status=subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True)
    versions=read(checkpoint/'request.json')['code']
    write(root/'source_revision.json',dict(final_revision=revision,working_tree_clean=not status,
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=REPO,text=True).strip(),
        baseline='385ec86c1f18ee1e2e0d61e2b32c524ceccfb683',
        generation_commit_record=versions['commit'],
        generation_file_hashes=versions['source_files'],
        generation_source_snapshots=str(root/'source_snapshots'),
        release_source_hashes={n:file_hash(REPO/n) for n in SOURCE_FILES},
        note='Runs preceded the final commit. Their actual source bytes are frozen by per-file SHA256; commit record alone is insufficient to identify uncommitted generation code.'))
    review={}
    for source,name in [(REPO/'docs/TASK25_RESULTS.md','FINAL_REPORT.md'),
                        (REPO/'docs/TASK25_HANDOFF.md','TASK25_HANDOFF.md')]:
        (root/name).write_text(source.read_text(encoding='utf-8').replace('(../studies/','(studies/'),encoding='utf-8')
        review[name]=root/name
        review['docs/'+source.name]=source
    for source in sorted((REPO/'studies/task25').rglob('*')):
        if source.is_file():review['studies/task25/'+source.relative_to(REPO/'studies/task25').as_posix()]=source
    for n in SOURCE_FILES:review['source/'+n]=REPO/n
    for n in ['input_identity.json','source_revision.json']:
        review[n]=root/n
    for source in sorted((root/'recipes').glob('*.json')):review['recipes/'+source.name]=source
    # Camera-space mesh JSON lives beside analysis metadata; do not collect the
    # entire folder. Review contains references/evidence, not those large meshes.
    for n in ['ancestry_map.json','ancestry_plan.json','resource_calibration.json',
              'scouting_decision.json','rhino_display_failure.json',
              'whole_execution_equivalence.json','measurements.json',
              'folding_support.json','curvature_displacement.json',
              'native_sections_manifest.json']:
        review['analysis/'+n]=root/'analysis'/n
    for n in ['SOURCE_MAP.md','DESIGN_DECISION.md']:
        if (root/'analysis'/n).exists():review['analysis/'+n]=root/'analysis'/n
    for source in sorted((root/'analysis/dcc_failure').glob('*')):
        if source.is_file():review['analysis/dcc_failure/'+source.name]=source
    for source in sorted((root/'analysis/sections').glob('*.json')):
        review['analysis/sections/'+source.name]=source
    for source in sorted((root/'analysis').glob('*.svg')):review['analysis/'+source.name]=source
    for source in sorted((root/'analysis').glob('*comparison*.png')):review['images/ancestry/'+source.name]=source
    for n in ['backbone_detail.png','ancestry_detail.png','ancestry_underside.png','ancestry_detail_angle.png','ancestry_whole.png','scouting_whole.png','scouting_detail.png']:
        if (root/'analysis'/n).exists():review['images/ancestry/'+n]=root/'analysis'/n
    for tag in ['first_comparison','scouting','second_comparison','curvature_comparison','amplified_comparison','final','geometry_evidence']:
        folder=root/'renders'/tag
        for pattern in ['comparison_*.png','camera_manifest.json','projection_plan.json','*overlay.png']:
            for source in sorted(folder.glob(pattern)):
                review['images/'+tag+'/'+source.name]=source
    for source in sorted((root/'brief/references').glob('*.png')):
        review['references/'+source.name]=source
    review['verification/pytest_full.txt']=REPO/'output/task25_pytest_final.txt'
    for source in sorted((root/'dcc').glob('*_import_evidence.json')):
        review['dcc/'+source.name]=source
    for source in sorted((root/'designs').glob('*/attempt_*/*.json')):
        if source.name not in ['new_support_route.json']:
            review['runs/'+source.relative_to(root/'designs').as_posix()]=source
    # Exact generation source closure: de-duplicate repeated hashes across runs.
    # Include the selected request's closure in review; all historical snapshots
    # remain external. No DLL or large mesh/checkpoint is placed in review.
    for n,h in versions['source_files'].items():
        source=root/'source_snapshots'/h/n
        if file_hash(source)!=h:raise ValueError('Frozen generation source snapshot changed.')
        review['generation_source/'+n]=source
    review_record=archive(root/'CHESHIRE_TASK25_REVIEW.zip',review)
    model={}
    for filename in [lead+'.obj','geometry.json.gz','state.json.gz','request.json','summary.json']:
        model['checkpoint/'+filename]=checkpoint/filename
    model['dcc/'+native.name]=native
    model['dcc/'+lead+'_import_evidence.json']=root/'dcc'/(lead+'_import_evidence.json')
    model['TASK25_HANDOFF.md']=root/'TASK25_HANDOFF.md'
    model['source_revision.json']=root/'source_revision.json'
    for source in sorted((root/'recipes').glob('*.json')):model['recipes/'+source.name]=source
    model_record=archive(root/'CHESHIRE_TASK25_MODEL.zip',model)
    deliverables=dict(lead=lead,attempt=attempt,revision=revision,
        OBJ=dict(path=str(lead_obj),bytes=lead_obj.stat().st_size,sha256=file_hash(lead_obj)),
        native=dict(path=str(native),bytes=native.stat().st_size,sha256=file_hash(native)),
        review=review_record,model=model_record,
        units='None / original coordinates; Z up; no rescaling',
        model_resume='Use checkpoint/geometry.json.gz with checkpoint/state.json.gz. OBJ/3DM alone omit generation state.',
        source_input_closure='Baseline frozen inputs and input_identity.json remain in '+str(root/'inputs')+'; review/model packets are not the entire historical archive.')
    write(root/'deliverables.json',deliverables);print(json.dumps(deliverables,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--lead');p.add_argument('--attempt',default='attempt_001');p.add_argument('--measurements-only',action='store_true')
    a=p.parse_args()
    if a.measurements_only:measurements(a.output_root)
    else:
        if not a.lead:p.error('--lead is required for packaging')
        package(a.output_root,a.lead,a.attempt)
