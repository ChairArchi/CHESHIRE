"""Package real Task-21 evidence and verify each included byte."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output/task21'; STUDY=OUT/'study'
TARGET=ROOT.parent/'CHESHIRE_TASK21_REVIEW.zip'
BASE='9afa414eca1353a7678432538902f55d87edcd41'; BRANCH='experiment/task21-vocabulary-sandbox'
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def sha(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): result.update(chunk)
    return result.hexdigest()

def main():
    assert not TARGET.exists(), 'Preserve any existing review archive.'
    temporary=TARGET.with_suffix('.zip.tmp'); assert not temporary.exists()
    commit=git('rev-parse','HEAD'); assert git('status','--porcelain')=='' and git('branch','--show-current')==BRANCH
    record=json.loads((OUT/'delivery_record.json').read_text(encoding='utf-8'))
    assert record['commit']==commit and record['remote_experimental_branch']==commit
    assert record['distribution_audit']=='PASS' and record['full_suite']['exit_code']==0
    files=[ROOT/name for name in git('ls-files').splitlines()]; excluded=[]
    complete={'F','R','HERO','REPLAY','references','recipes','requests','logs','views','backbone_crossing_check'}
    early={'A_D06','A_D07','A_D08','A_R06','A_R07','A_R09'}
    for path in STUDY.rglob('*'):
        if not path.is_file(): continue
        relative=path.relative_to(STUDY); include=relative.parts[0] in complete or len(relative.parts)==1
        if relative.parts[0] in {'A','B','C'}:
            include=True
            if path.name in {'terminal.json','terminal.obj','terminal_lineage.json.gz','terminal_signatures.json.gz'}:
                include=relative.parts[0]=='A' and relative.parts[1] in early and path.name!='terminal.obj'
        if path.name=='response.json' or path.suffix=='.signature': include=False
        if path.name.endswith('_checkpoint_cache.json'): include=False
        if include: files.append(path)
        else: excluded.append(path.relative_to(ROOT).as_posix())
    top={'operator_reflection.json','operator_probes.json','operator_probes_initial.json','operator_acceptance.json',
        'probe_stdout.txt','wrapper_probe_stdout.txt','focused_pytest.txt','focused_pytest_final.txt','full_pytest.txt','test_record.json',
        'diff_check.txt','distribution_audit.json','delivery_record.json','task21.patch','REVIEW_MANIFEST.md',
        'FINAL_REPORT.md','host_status.json','worker_python.txt','resume_check.txt','delivery_visual_review.json'}
    files.extend(p for p in OUT.iterdir() if p.is_file() and p.name in top)
    files.extend(p for p in (OUT/'probe_views').rglob('*') if p.is_file() and p.suffix!='.signature')
    files.extend(p for p in (OUT/'nonlinear').rglob('*') if p.is_file() and p.suffix!='.signature')
    files=sorted(set(files),key=lambda p:p.relative_to(ROOT).as_posix()); inventory=[]
    secret=re.compile(rb'(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
    for path in files:
        relative=path.relative_to(ROOT)
        assert path.is_file() and not any(p.lower() in {'.git','.venv','__pycache__','.pytest_cache','upstream','vendor','.aws','.vscode'} for p in relative.parts)
        assert path.suffix.lower() not in {'.dll','.gha','.exe','.pdb','.zip','.7z','.rar'} and path.name!='local_settings.json'
        if path.suffix.lower() in {'.txt','.json','.csv','.md','.py','.ps1','.toml','.patch'}: assert not secret.search(path.read_bytes()),relative
        inventory.append(dict(path='CHESHIRE/'+relative.as_posix(),bytes=path.stat().st_size,sha256=sha(path)))
    metadata=dict(source_commit=commit,branch=BRANCH,baseline=BASE,files=inventory,
        excluded_scratch_files=sorted(excluded),complete_geometry_phases=['F','R','HERO','REPLAY'],
        preserved_early_Hero_geometry_audit_cases=sorted(early),
        exclusions='External binaries/upstream code, settings/secrets, old archives, caches, redundant primary geometry and sampled-response meshes. Primary routing/events, tables, contacts, views and recipes remain.',
        inventory_self_hash='Excluded to avoid self-reference')
    print('Archive',len(files),'files',sum(r['bytes'] for r in inventory),'uncompressed bytes',flush=True); started=time.monotonic()
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=4,allowZip64=True) as archive:
        for i,(path,entry) in enumerate(zip(files,inventory),1):
            archive.write(path,entry['path'])
            if i%400==0: print('Archived',i,'/',len(files),flush=True)
        archive.writestr('CHESHIRE/ARCHIVE_INVENTORY.json',json.dumps(metadata,indent=2)+'\n')
    with zipfile.ZipFile(temporary) as archive:
        assert len(archive.namelist())==len(set(archive.namelist()))
        assert set(archive.namelist())=={r['path'] for r in inventory}|{'CHESHIRE/ARCHIVE_INVENTORY.json'}
        assert archive.testzip() is None
        for i,entry in enumerate(inventory,1):
            value=hashlib.sha256(); count=0
            with archive.open(entry['path']) as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''): count+=len(chunk); value.update(chunk)
            assert count==entry['bytes'] and value.hexdigest()==entry['sha256'],entry['path']
            if i%800==0: print('Verified',i,'/',len(files),flush=True)
        assert json.loads(archive.read('CHESHIRE/ARCHIVE_INVENTORY.json'))==metadata
    temporary.replace(TARGET)
    result=dict(path=str(TARGET),bytes=TARGET.stat().st_size,sha256=sha(TARGET),entries=len(inventory)+1,
        integrity='PASS all member CRC/size/SHA256',source_commit=commit,seconds=round(time.monotonic()-started,2))
    (OUT/'delivery.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__': main()
