"""Independent local Git-bundle + exact producer-overlay + native replay test.

Dependencies are referenced read-only from the original installed environment;
this tests source/state recovery, not a standalone dependency distribution.
"""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'tools'))
from task33_preserve import ROOT,sha,write_new


def recover(bundle,candidate,tag):
    bundle=Path(bundle).resolve()
    if not all(v.replace('_','').isalnum() for v in (candidate,tag)):raise ValueError('Safe tags required.')
    dest=ROOT/'preservation'/tag;dest.mkdir(parents=True,exist_ok=False)
    temporary=Path('C:/Users/Public/Documents/ESTsoft/CreatorTemp').resolve()
    clone=temporary/('task33_recovered_'+tag)
    if clone.exists() or not clone.resolve().is_relative_to(temporary):raise ValueError('Fresh contained clone required.')
    def checked(command,cwd=None,env=None):
        result=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True)
        if result.returncode:
            write_new(dest/('failure_'+str(len(list(dest.glob('failure_*.json'))))+'.json'),dict(command=command,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
            raise RuntimeError(result.stderr or result.stdout)
        return dict(command=command,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)
    verified=checked(['git','-c','safe.directory='+REPO.as_posix(),'bundle','verify',str(bundle)],REPO)
    cloned=checked(['git','clone','--branch','experiment/task33-deep-folds',str(bundle),str(clone)])
    fsck=checked(['git','-C',str(clone),'-c','safe.directory='+clone.as_posix(),'fsck','--full'])
    head=checked(['git','-C',str(clone),'-c','safe.directory='+clone.as_posix(),'rev-parse','HEAD'])['stdout'].strip()
    job=ROOT/'candidates'/candidate;overlay=[]
    for relative,digest in json.loads((job/'source_identity.json').read_text()).items():
        target=(clone/relative).resolve();source=job/'source'/relative
        if not target.is_relative_to(clone.resolve()) or sha(source)!=digest:raise ValueError('Invalid producer overlay path or SHA.')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        if sha(target)!=digest:raise ValueError('Producer overlay restoration mismatch.')
        overlay.append(dict(path=relative,sha256=digest))
    checked([sys.executable,'-B','-m','venv','--without-pip',str(clone/'.venv')])
    dependency=REPO/'.venv/Lib/site-packages'
    pth=clone/'.venv/Lib/site-packages/task33_recovery.pth'
    pth.write_text(str(clone/'src')+'\n'+str(dependency)+'\n',encoding='utf-8')
    probe=checked([str(clone/'.venv/Scripts/python.exe'),'-B','-c',
        'import cheshire.task33_folds as f; print(f.__file__)'],clone)
    if Path(probe['stdout'].strip()).resolve()!=clone/'src/cheshire/task33_folds.py':
        raise ValueError('Recovered interpreter imported the original checkout instead of the clone.')
    request=dest/'request.json';write_new(request,dict(candidate=candidate))
    # The checkout-local venv satisfies the existing worker identity guard.
    replay_tag='INDEPENDENT_'+tag
    replay=checked([str(clone/'.venv/Scripts/python.exe'),'-B',str(clone/'tools/task33_research.py'),
        '--action','evidence','--request',str(request),'--tag',replay_tag],clone)
    proof=ROOT/'preservation'/(replay_tag+'.json')
    write_new(dest/'recovery.json',dict(candidate=candidate,bundle=str(bundle),bundle_sha256=sha(bundle),
        bundle_verification=verified,clone=cloned,fsck=fsck,restored_checkout=str(clone),head=head,
        producer_source_overlay=overlay,source_import_probe=probe,native_replay=replay,native_proof=str(proof),native_proof_sha256=sha(proof),
        dependency_library_readonly=str(dependency),environment='Fresh checkout-local venv, no package installs; installed dependencies referenced read-only. Not an independent dependency backup.'))
    print(candidate,'independent source/state recovery verified',head,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args();recover(a.bundle,a.candidate,a.tag)
