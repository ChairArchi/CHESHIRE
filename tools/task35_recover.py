"""Independent Task35 bundle recovery and full byte-exact native-state replay.

Installed dependencies are referenced read-only; this is not an offline
dependency distribution. Existing candidates are never overwritten.
"""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'tools'))
from task33_preserve import sha,write_new
ROOT=Path('E:/CHESHIRE_DATA/task35')


def recover(bundle,candidate,tag):
    bundle=Path(bundle).resolve()
    if not all(v.replace('_','').isalnum() for v in (candidate,tag)):raise ValueError('Safe fresh tags required.')
    dest=ROOT/'preservation'/tag;dest.mkdir(parents=True,exist_ok=False)
    temporary=Path('C:/Users/Public/Documents/ESTsoft/CreatorTemp').resolve();clone=temporary/('task35_recovered_'+tag)
    if clone.exists() or not clone.resolve().is_relative_to(temporary):raise ValueError('Fresh contained clone required.')
    def checked(command,cwd=None):
        result=subprocess.run(command,cwd=cwd,capture_output=True,text=True)
        if result.returncode:
            write_new(dest/'failure.json',dict(command=command,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
            raise RuntimeError(result.stderr or result.stdout)
        return dict(command=command,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)
    verified=checked(['git','-c','safe.directory='+REPO.as_posix(),'bundle','verify',str(bundle)],REPO)
    cloned=checked(['git','clone','--branch','experiment/task35-sectional-column',str(bundle),str(clone)])
    fsck=checked(['git','-C',str(clone),'-c','safe.directory='+clone.as_posix(),'fsck','--full'])
    job=ROOT/'candidates'/candidate;overlay=[]
    for relative,digest in json.loads((job/'source_identity.json').read_text()).items():
        source=job/'source'/relative;target=(clone/relative).resolve()
        if not target.is_relative_to(clone.resolve()) or sha(source)!=digest:raise ValueError('Invalid producer snapshot.')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        if sha(target)!=digest:raise ValueError('Overlay SHA differs.')
        overlay.append(dict(path=relative,sha256=digest))
    checked([sys.executable,'-B','-m','venv','--without-pip',str(clone/'.venv')])
    dependency=REPO/'.venv/Lib/site-packages'
    (clone/'.venv/Lib/site-packages/task35_recovery.pth').write_text(str(clone/'src')+'\n'+str(dependency)+'\n',encoding='utf-8')
    python=clone/'.venv/Scripts/python.exe'
    probe=checked([str(python),'-B','-c','import cheshire.task35_columns as f; print(f.__file__)'],clone)
    if Path(probe['stdout'].strip()).resolve()!=clone/'src/cheshire/task35_columns.py':raise ValueError('Original source imported instead of clone.')
    replay_tag='INDEPENDENT_'+tag
    replay=checked([str(python),'-B',str(clone/'tools/task35_research.py'),'--action','run',
                    '--request',str(job/'request.json'),'--tag',replay_tag],clone)
    regenerated=ROOT/'candidates'/replay_tag;proof=[];feature_proof=[]
    for stage in sorted(job.glob('G*')):
        for source in sorted(stage.glob('*.npz')):
            target=regenerated/stage.name/source.name
            if not target.exists() or sha(source)!=sha(target):raise ValueError('Native-state byte replay differs: '+str(source))
            proof.append(dict(path=str(source.relative_to(job)),sha256=sha(source)))
        if (stage/'features.json').exists():
            original=json.loads((stage/'features.json').read_text());new=json.loads((regenerated/stage.name/'features.json').read_text())
            if original['features']!=new['features'] or original['source_mesh_sha256']!=new['source_mesh_sha256']:raise ValueError('Measured source feature replay differs.')
            feature_proof.append(dict(stage=stage.name,rows=len(original['features']),source_mesh_sha256=original['source_mesh_sha256'],values_equal=True,
                limits='Absolute source_stage path changes in the independent candidate; geometric feature values, native edge IDs/weights and source mesh identity match exactly.'))
    write_new(dest/'recovery.json',dict(candidate=candidate,bundle=str(bundle),bundle_sha256=sha(bundle),
        bundle_verification=verified,clone=cloned,fsck=fsck,source_import_probe=probe,producer_overlay=overlay,
        native_replay=replay,regenerated_candidate=str(regenerated),byte_exact_npz_files=proof,feature_replay=feature_proof,
        recovered_head=checked(['git','-C',str(clone),'-c','safe.directory='+clone.as_posix(),'rev-parse','HEAD'])['stdout'].strip(),
        dependency_library_readonly=str(dependency),producer_sha256=sha(Path(__file__)),
        limits='Fresh clone and checkout-local venv; no package installation. Source and every native NPZ recovered, but installed dependencies remain a separate prerequisite.'))
    print(candidate,len(proof),'NPZ files replayed byte-exactly from independent clone',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True)
    args=p.parse_args();recover(args.bundle,args.candidate,args.tag)
