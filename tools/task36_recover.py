"""Independent Git-bundle code recovery and full native sequence replay.

Dependencies are read from the original local venv; no network/pip installs.
This proves code/input recovery on this host, not a portable offline environment.
"""
import argparse,json,subprocess,sys,shutil,uuid
from pathlib import Path
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_preserve import sha,write_new
ROOT=Path('E:/CHESHIRE_DATA/task36')


def recover(candidate,tag,bundle):
    job=ROOT/'candidates'/candidate;dest=ROOT/'preservation'/tag;dest.mkdir(parents=True,exist_ok=False)
    clone=Path('C:/Users/Public/Documents/ESTsoft/CreatorTemp')/('task36_recovery_'+uuid.uuid4().hex[:12]);branch='experiment/task36-neutral-recursive'
    result=subprocess.run(['git','clone','--branch',branch,str(bundle),str(clone)],capture_output=True,text=True)
    write_new(dest/'clone.json',dict(code=result.returncode,stdout=result.stdout,stderr=result.stderr,bundle_sha256=sha(bundle),clone=str(clone)))
    if result.returncode:raise RuntimeError('Bundle clone failed.')
    git=['git','-c','safe.directory='+clone.as_posix()]
    fsck=subprocess.run(git+['fsck','--full'],cwd=clone,capture_output=True,text=True)
    write_new(dest/'fsck.json',dict(code=fsck.returncode,stdout=fsck.stdout,stderr=fsck.stderr))
    if fsck.returncode:raise RuntimeError('Recovered Git object validation failed.')
    identities=json.loads((job/'source_identity.json').read_text())
    for relative,digest in identities.items():
        src=job/'source'/relative;target=clone/relative;target.parent.mkdir(parents=True,exist_ok=True)
        if sha(src)!=digest:raise ValueError('Producer overlay integrity failed.')
        shutil.copy2(src,target)
        if sha(target)!=digest:raise ValueError('Overlay copy mismatch.')
    # Existing Rhino support imports enforce <repo>/.venv/Scripts/python.exe.
    # Honour that runtime identity in the fresh clone; never bypass its guard.
    env=clone/'.venv';subprocess.run([sys.executable,'-m','venv','--without-pip',str(env)],check=True)
    site=env/'Lib/site-packages';(site/'local_recovery.pth').write_text(str(REPO/'.venv/Lib/site-packages')+'\nimport sys; sys.path.insert(0, '+repr(str(clone/'src'))+')\n',encoding='utf8')
    python=env/'Scripts/python.exe';probe=subprocess.check_output([str(python),'-B','-c','import cheshire.task36_growth as m; print(m.__file__)'],cwd=clone,text=True).strip()
    if not Path(probe).is_relative_to(clone):raise ValueError('Recovery imported original code.')
    request=job/'request.json';run=subprocess.run([str(python),'-B',str(clone/'tools/task36_research.py'),'--action','run','--request',str(request),'--tag',tag],cwd=clone,capture_output=True,text=True)
    write_new(dest/'execution.json',dict(code=run.returncode,stdout=run.stdout,stderr=run.stderr,imported_module=probe,original_dependency_site=str(REPO/'.venv/Lib/site-packages')))
    if run.returncode:raise RuntimeError('Recovered producer failed; logs retained.')
    copy=ROOT/'candidates'/tag
    if not (copy/'completed.json').exists():raise RuntimeError('Recovered sequence rejected; see retained diagnostics.')
    checks=[]
    for source in sorted(job.glob('G*/*.npz')):
        relative=source.relative_to(job);other=copy/relative
        checks.append(dict(file=relative.as_posix(),sha256=sha(source),replayed_sha256=sha(other),exact=sha(source)==sha(other)))
    value=dict(candidate=candidate,tag=tag,bundle_sha256=sha(bundle),recipe_sha256=sha(request),native_state_checks=checks,all_npz_byte_exact=all(r['exact'] for r in checks),
        code_overlay=identities,limitation='Full generation replay on this host with unchanged local dependency packages. Dependency wheels/DLL/runtime are not bundled.')
    write_new(dest/'recovery.json',value)
    if not value['all_npz_byte_exact']:raise ValueError('Recovered state differs.')
    print(candidate,'recovered exact NPZ',len(checks),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);p.add_argument('--bundle',type=Path,required=True);a=p.parse_args();recover(a.candidate,a.tag,a.bundle)
