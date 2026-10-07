"""Task26 compact manifests, actual-file archives and release identity."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
from time import perf_counter
import zipfile

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'examples'))
from progressive_gates import parent_directory,BASELINE
from cross_cell_crease_study import read,write,file_hash

PRESENTATION=['INPUT_ROUND','ROUND_EARLY_G1','ROUND_GROOVE_G2','ROUND_GROOVE_SMOOTH_G3','FOLD_DISTRIBUTED_SMOOTH_G5','LEAD_BALANCED_G7']
SOURCES=['examples/progressive_gates.py','examples/generational_folding.py','src/cheshire/progressive_gates.py',
    'src/cheshire/crease_folding.py','src/cheshire/fold_continuation.py','tests/test_progressive_gates.py',
    'tools/progressive_gate_views.py','tools/progressive_gate_evidence.py','tools/progressive_gate_native.ps1',
    'tools/progressive_gate_package.py','tools/progressive_gate_native_monitor.py','pyproject.toml','THIRD_PARTY_NOTICES.md']


def manifest(root):
    for row in read(root/'input_identity.json')['inputs']:
        d=root/'inputs'/row['id']
        if file_hash(d/'geometry.json.gz')!=row['geometry'] or file_hash(d/'state.json.gz')!=row['state']:
            raise ValueError('Task26 matched input identity changed.')
    rows=[]
    paths=list((root/'inputs').glob('*/summary.json'))+list((root/'probes').glob('*/summary.json'))+list((root/'designs').glob('*/attempt_*/summary.json'))
    for p in sorted(paths):
        summary=read(p);d=p.parent;name=d.name if d.parent.name in ('inputs','probes') else d.parent.name
        recipe=summary.get('recipe',{});success=summary['status']=='SUCCESS'
        rows.append(dict(id=name,attempt=d.name,status=summary['status'],checkpoint=str(d),parent=recipe.get('parent',summary.get('parent')),
            input=summary.get('input'),operation=recipe.get('declaration',summary.get('operation','Input geometry')),
            resolved_parameters=summary.get('resolved_support'),generation=summary.get('generation'),
            dimensions=summary.get('statistics',{}).get('bounding_box'),vertices=summary.get('statistics',{}).get('vertex_count'),
            faces=summary.get('statistics',{}).get('face_count'),symmetry=summary.get('symmetry'),reason=summary.get('reason'),
            files={x.name:dict(path=str(x),bytes=x.stat().st_size,sha256=file_hash(x)) for x in d.iterdir() if x.is_file()},
            presentation=name in PRESENTATION and success,model_label='Design surface / shared original unresolved units; not print-ready volume.'))
    lookup={row['id']:row for row in rows if row['status']=='SUCCESS'}
    for row in rows:
        name=row['id'];seen=set()
        while name in lookup and not name.startswith(('INPUT_','PROBE_')):
            if name in seen:raise ValueError('Cyclic saved stage ancestry.')
            seen.add(name);name=lookup[name]['parent']
        row['input_identity']=name
        if name and name.startswith('INPUT_'):
            row['input_geometry_sha256']=file_hash(root/'inputs'/name/'geometry.json.gz')
        row['mesh_sha256']=row['files'].get('geometry.json.gz',{}).get('sha256')
    captures=[]
    for p in sorted((root/'renders').glob('*/camera_manifest.json')):
        if p.parent.name in ('initial','macro_symmetry'):continue
        for row in read(p)['records']:captures.append({**row,'manifest':str(p)})
    write(root/'stage_manifest.json',dict(baseline=BASELINE,stages=rows,captures=captures,presentation=PRESENTATION,
        stage_policy='Real saved ancestor sequence, omitted generations remain checkpoints. Same original scale and one camera/material/light per comparison.',
        preserved_early_capture_note='initial and macro_symmetry RGB use genuine GPU occlusion, but auxiliary depth normalization was superseded after orthographic bug verification; corrected initial_v2 and later manifests are used.',
        model_readiness='Design surfaces only; no thickness, fabrication repair or structural validation.',release_identity='release.json records final local SHA after commit.'))


def archive(path,entries):
    t=perf_counter();expected={}
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for name,p in sorted(entries.items()):
            z.write(p,name);expected[name]=file_hash(p)
    with zipfile.ZipFile(path) as z:
        bad=z.testzip()
        if bad:raise ValueError('ZIP CRC failed '+bad)
        import hashlib
        for name,h in expected.items():
            actual=hashlib.sha256()
            with z.open(name) as f:
                for chunk in iter(lambda:f.read(1024**2),b''):actual.update(chunk)
            if actual.hexdigest()!=h:raise ValueError('ZIP payload SHA mismatch '+name)
    return dict(path=str(path),bytes=path.stat().st_size,sha256=file_hash(path),payloads=len(expected),
        actual_archive_reread_CRC_and_payload_SHA256=True,seconds=perf_counter()-t)


def package(root,lead):
    manifest(root);sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    status=subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True)
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=REPO,text=True).strip()
    write(root/'release.json',dict(baseline=BASELINE,final_local_commit=sha,branch=branch,working_tree=status,
        clean=not bool(status),sources={n:file_hash(REPO/n) for n in SOURCES},lead=lead,
        native=str(root/'dcc'/(lead+'.3dm')),OBJ=str(parent_directory(root,lead)/(lead+'.obj'))))
    review={};model={};directory=parent_directory(root,lead)
    def add(target,p,base=root):
        if p.is_file():target[p.relative_to(base).as_posix()]=p
    for n in ['FINAL_REPORT.md','TASK26_HANDOFF.md','TASK26_STOP_HANDOFF.md','release.json','stage_manifest.json','input_identity.json']:
        add(review,root/n)
    for p in (root/'recipes').rglob('*.json'):add(review,p)
    for p in (root/'brief/references').glob('*.png'):add(review,p)
    for p in (root/'analysis').glob('*.json'):add(review,p)
    for p in (root/'analysis/sections').glob('*.json'):add(review,p)
    for p in (root/'logs').glob('*/process.json'):add(review,p)
    for p in (root/'test_logs').glob('*.txt'):add(review,p)
    for p in (root/'dcc').glob('*_import_evidence.json'):add(review,p)
    for row in read(root/'stage_manifest.json')['stages']:
        d=Path(row['checkpoint'])
        for n in ['summary.json','request.json','resource_preflight.json','route_comparison.json']:add(review,d/n)
    # Key scenes/manifests and full quality PNGs, not hundreds of MB of render
    # geometry/index/depth arrays. Those remain external with identity records.
    tags=['initial_v2','controls','revised','progression_selected','lead','geometry','profile_probe','balanced_comparison']
    for tag in tags:
        d=root/'renders'/tag
        for p in d.glob('*_sheet.png'):add(review,p)
        for p in d.glob('*manifest.json'):add(review,p)
    for p in (root/'renders/lead').glob('*.png'):add(review,p)
    for p in (root/'renders/geometry').glob('*.png'):add(review,p)
    for p in (root/'source_snapshots').rglob('*.py'):add(review,p);add(model,p)
    for n in SOURCES:review['source/'+n]=REPO/n
    for n in ['docs/TASK26_RESULTS.md','docs/TASK26_HANDOFF.md','docs/TASK26_STOP_HANDOFF.md']:review['source/'+n]=REPO/n
    for n in ['geometry.json.gz','state.json.gz','operator.json.gz','request.json','summary.json','resource_preflight.json',lead+'.obj']:
        add(model,directory/n)
    for p in [root/'dcc'/(lead+'.3dm'),root/'dcc'/(lead+'_import_evidence.json'),root/'release.json',root/'stage_manifest.json',root/'FINAL_REPORT.md']:
        add(model,p)
    for name in PRESENTATION:
        d=parent_directory(root,name)
        if name.startswith('INPUT_'):
            for p in d.iterdir():add(model,p)
    for n in SOURCES:model['source/'+n]=REPO/n
    for p in (root/'recipes').rglob('*.json'):add(model,p)
    a=archive(root/'CHESHIRE_TASK26_REVIEW.zip',review);b=archive(root/'CHESHIRE_TASK26_MODEL.zip',model)
    write(root/'deliverables.json',dict(review=a,model=b,lead=lead,final_local_commit=sha,working_tree_clean=not bool(status)))
    print('Archives verified',a['bytes'],b['bytes'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--lead',default='LEAD_BALANCED_G7')
    p.add_argument('--manifest-only',action='store_true');a=p.parse_args()
    if a.manifest_only:manifest(a.output_root)
    else:package(a.output_root,a.lead)
