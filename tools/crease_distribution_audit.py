"""Task23 distribution audit; prior exclusions and protected refs remain intact."""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def audit(target):
    files=sorted(set(git('ls-files','--cached','--others','--exclude-standard').splitlines()))
    forbidden=[]; paths=[]; secrets=[]; images=[]
    for name in files:
        path=Path(name); parts={p.lower() for p in path.parts}
        if path.suffix.lower() in ('.dll','.gha','.exe','.pdb','.zip','.7z','.rar') or parts & {'.git','.venv','output','vendor','upstream','node_modules','.vscode','.aws','__pycache__'} or path.name=='local_settings.json': forbidden.append(name)
        if path.suffix.lower() in ('.png','.jpg','.jpeg','.gif'):
            images.append(name)
            if not name.startswith(tuple(f'studies/task{i}/evidence/' for i in (18,19,20,21,22,23))): forbidden.append(name)
        else:
            text=(ROOT/name).read_text(encoding='utf-8')
            if re.search(r'[A-Za-z]:[\\/](?:Users|Program Files)[\\/]',text): paths.append(name)
            if re.search(r'(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)',text): secrets.append(name)
    protected=dict(main='9a948d7e34ee0113930ad771e58281850608a624',task19='838490b8aafb9c2f2961b18b3cda0e89435fd087',
        task20='9afa414eca1353a7678432538902f55d87edcd41',task21='0090fc816c8d7a1bcb755114a859c295047c7b0b',
        task22='66cb4f90d0b15834d358db5ce2569c813379b0b1',task17='ec5c3bcd0efd9aac08dfe4a6a813ab2aaf35ce20')
    actual=dict(main=git('rev-parse','main'),task19=git('rev-parse','experiment/task19-ornament-capability'),
        task20=git('rev-parse','experiment/task20-differentiated-branching'),task21=git('rev-parse','experiment/task21-vocabulary-sandbox'),
        task22=git('rev-parse','experiment/task22-beyond-smoothness'),task17=git('rev-parse','checkpoint/task17-subdivision-base^{}'))
    assert actual==protected,actual
    checkpoint_tag=git('rev-parse','checkpoint/task17-subdivision-base')
    assert checkpoint_tag=='2234c1e7e6cf1eab7346dd69cf14423018dcc10d'
    assert git('branch','--show-current')=='experiment/task23-cross-cell-crease-hero'
    assert subprocess.run(['git','check-ignore','output/task23/study','output/local_settings.json'],cwd=ROOT,capture_output=True).returncode==0
    result=dict(policy='Existing distribution exclusions/path/secret checks; Task23 evidence permission and protected Task22 ref added.',
        files=len(files),forbidden_artifacts=forbidden,machine_path_candidates=paths,secrets=secrets,
        permitted_first_party_projection_images=images,protected_refs=actual,checkpoint_tag_object=checkpoint_tag,
        no_LICENSE_added='LICENSE' not in files,publication='PASS' if not(forbidden or paths or secrets) else 'FAIL')
    target=Path(target); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2)); assert result['publication']=='PASS'
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--report',type=Path,required=True); audit(parser.parse_args().report)
