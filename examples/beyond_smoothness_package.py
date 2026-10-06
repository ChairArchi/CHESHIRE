"""Curated first-party review archive; external binaries/settings never included."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from beyond_smoothness_verify import read,write
from cheshire.artifact_root import ArtifactRoot

def sha256(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def package(root,archive):
    selection=read(root.resolve('study/selection.json'))
    chosen={r['id'] for r in selection['finalists']}|set(selection.get('heroes',[]))|set(selection.get('replays',[]))
    entries={}
    def add(path,name):
        if path.is_file(): entries[name]=path
    for folder in ('src','tests','rhino','tools'):
        for p in sorted((ROOT/folder).rglob('*')):
            if '__pycache__' not in p.parts and (p.suffix in ('.py','.ps1') or folder=='src' and p.suffix=='.json'):
                add(p,'source/'+p.relative_to(ROOT).as_posix())
    # Earlier first-party fixtures/recipes are causal test inputs, not raw screens.
    tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    for name in tracked:
        if Path(name).suffix=='.json' and Path(name).parts[0] in ('studies','tests','examples','rhino'):
            add(ROOT/name,'source/'+name)
    for p in sorted((ROOT/'examples').glob('*.py')): add(p,'source/'+p.relative_to(ROOT).as_posix())
    for name in ('pyproject.toml','README.md','.gitignore','docs/BEYOND_SMOOTHNESS_REFERENCE.md','docs/BEYOND_SMOOTHNESS_STUDY.md','THIRD_PARTY_NOTICES.md'):
        add(ROOT/name,'source/'+name)
    for p in sorted((ROOT/'studies/task22').rglob('*')): add(p,'source/'+p.relative_to(ROOT).as_posix())
    # Complete frozen inputs make the Task22 grammar independent of an old output folder.
    for directory in ('inputs','cache/source_snapshots'):
        for p in sorted(root.resolve(directory).rglob('*')): add(p,'artifacts/'+root.reference(p))
    for p in sorted(root.resolve('study').glob('*')):
        if p.suffix in ('.json','.csv'): add(p,'artifacts/'+root.reference(p))
    add(root.resolve('final_comparison_plan.json'),'artifacts/final_comparison_plan.json')
    for phase in ('CONTROL','DISTANCE','PLANARITY','GATE','F','R','HERO','REPLAY','REFERENCE'):
        latest={sorted(case.glob('attempt_*/summary.json'))[-1].parent for case in root.resolve('study/'+phase).glob('*') if list(case.glob('attempt_*/summary.json'))}
        for p in sorted(root.resolve('study/'+phase).glob('*/attempt_*/*')):
            if p.name in ('summary.json','request.json','branch_signatures.json'):
                add(p,'artifacts/'+root.reference(p))
            if p.parent in latest and (p.parent.parent.name in chosen or phase=='REFERENCE'):
                if p.suffix in ('.gz','.obj','.json') and p.name!='worker_identity.json': add(p,'artifacts/'+root.reference(p))
        # Keep diagnostic error logs and sampling JSON, omit redundant raw audit meshes.
        for p in sorted(root.resolve('study/'+phase).glob('*/attempt_*/audit_*/crossing_audit.json')):
            add(p,'artifacts/'+root.reference(p))
    for p in sorted(root.resolve('renders').glob('*')):
        if p.suffix not in ('.png','.json'): continue
        if '_sheet_' in p.name or p.name.startswith(('REFERENCE_','FINAL_')) or any(('_'+n+'_') in p.name for n in chosen):
            add(p,'artifacts/'+root.reference(p))
    for p in sorted(root.resolve('logs').rglob('*')):
        if p.is_file() and p.name!='preflight.json' and p.suffix in ('.txt','.json'):
            # Existing process records contain only PIDs/births/counts, not environment dumps.
            add(p,'artifacts/'+root.reference(p))
    manifest=dict(policy='First-party code/evidence only. No third-party binaries/source/papers, environment dumps or local settings.',
        omitted='Redundant raw screening geometry; the full dataset remains at the configured external root.',
        entries=[dict(path=name,bytes=p.stat().st_size,sha256=sha256(p)) for name,p in sorted(entries.items())])
    # Validate inventory before creating the archive.
    for name in entries:
        parts={part.lower() for part in Path(name).parts}
        if parts & {'.git','.venv','__pycache__','vendor','upstream','.aws','.vscode'} or Path(name).suffix.lower() in ('.dll','.gha','.exe','.pdb','.zip','.pdf'):
            raise ValueError('Forbidden review entry: '+name)
    archive=Path(archive); archive.parent.mkdir(parents=True,exist_ok=True)
    if archive.exists(): raise ValueError('Refuse to overwrite an existing review archive.')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
        for name,p in sorted(entries.items()): bundle.write(p,name)
        bundle.writestr('REVIEW_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
        bundle.writestr('REVIEW_MANIFEST.md','# Task 22 review\n\n'
            'Start with source/docs/BEYOND_SMOOTHNESS_STUDY.md and the reference contract.\n\n'
            '- Baseline: 0090fc816c8d7a1bcb755114a859c295047c7b0b.\n'
            '- Result: reproducible local creases and nested ornament; no Grotesque gate candidate.\n'
            '- Evidence: actual fixed-camera headless polygon projections; Rhino host not tested.\n'
            '- Recipes, motif/lock evidence and compact phase tables: source/studies/task22/.\n'
            '- Frozen inputs, first-party source revisions and selected actual checkpoints: artifacts/.\n'
            '- Publication, protected-ref checks, full tests and diff/audit logs: artifacts/logs/.\n'
            '- REVIEW_MANIFEST.json records byte counts and SHA256 for every curated file.\n\n'
            'The artifacts directory is relocatable. Use the existing venv and an official external\n'
            'HDMola assembly for the old Mola finishes. No assembly, environment, upstream source,\n'
            'paper, local settings or redundant raw screening geometry is distributed.\n'
            'The full screening dataset remains at the separately configured external root.\n')
        bundle.writestr('README_REVIEW.txt','Read source/docs/BEYOND_SMOOTHNESS_STUDY.md first.\n'
            'artifacts/ is a relocatable subset of the configured output root.\n'
            'Frozen inputs and selected checkpoints are real meshes; images are fixed headless projections.\n'
            'All exact recipes and summaries are included; omitted screening geometry is documented.\n'
            'Use the official external DLL separately for old Mola finishes; none is redistributed.\n')
    result=dict(bytes=archive.stat().st_size,sha256=sha256(archive),entries=len(entries)+3)
    write(root.resolve('logs/review_zip.json'),result); print(result)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output-root',type=Path,required=True); parser.add_argument('--archive',type=Path,required=True)
    args=parser.parse_args(); package(ArtifactRoot(args.output_root),args.archive)
