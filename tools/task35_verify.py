"""Full unchanged regression criteria, dependency identities and RAM record."""
import argparse,json,os,re,sys,importlib.metadata as metadata
from pathlib import Path
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO),str(REPO/'tools'),str(REPO/'examples')]
from task33_preserve import sha,write_new
from hero_design_sprint import guarded,windows_memory
ROOT=Path('E:/CHESHIRE_DATA/task35')


def main(worker,tag):
    if not tag.replace('_','').isalnum():raise ValueError('Fresh safe test-evidence tag required.')
    os.environ['CHESHIRE_MOLA_DLL']='C:/Users/USER/Libraries/HDMola/1.0.0/HDMola.dll'
    os.environ['PYTHONNET_RUNTIME']='coreclr'
    if worker:
        import pytest
        raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp','C:/Users/Public/Documents/ESTsoft/CreatorTemp/task35_pytest_'+tag]))
    dest=ROOT/tag
    if dest.exists():raise FileExistsError('Regression evidence is immutable.')
    memory=windows_memory()
    if memory['status']!='MEASURED' or 4*1024**3>.55*memory['available_bytes']:raise MemoryError('Regression RAM reserve insufficient.')
    result=guarded(['--worker','--tag',tag],dest,worker_script=Path(__file__))
    versions={}
    for name in ['numpy','scipy','trimesh','pyrender','compas','pythonnet','pytest','Pillow','numba','psutil']:
        m=metadata.metadata(name);versions[name]=dict(version=metadata.version(name),license=m.get('License-Expression') or m.get('License','')[:2000],homepage=m.get('Home-page'))
    write_new(dest/'result.json',dict(**result,available_before=memory,forecast_bytes=4*1024**3,
        python=sys.version,dependency_metadata=versions,DLL=dict(path=os.environ['CHESHIRE_MOLA_DLL'],sha256=sha(Path(os.environ['CHESHIRE_MOLA_DLL']))),
        test_sha256={p.as_posix():sha(p) for p in sorted(Path('tests').rglob('*.py'))},producer_sha256=sha(Path(__file__)),
        criteria='Entire existing test suite, no criteria changes, disables or forced skips; original MOLA/CoreCLR configuration.'))
    print(json.dumps(result),flush=True)
    raise SystemExit(result['exit_code'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--tag',default='tests_final');a=p.parse_args();main(a.worker,a.tag)
