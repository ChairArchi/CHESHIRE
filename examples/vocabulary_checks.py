"""One delivery suite with real DLL and an external, fresh pytest temp root."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output/task21'

def main(dll,temp):
    if not dll.is_file(): raise ValueError('Explicit official DLL required.')
    temp=temp.resolve()
    if temp.is_relative_to(ROOT) or temp.exists(): raise ValueError('Fresh pytest temp outside the repository required for repository-identity rejection tests.')
    OUT.mkdir(parents=True,exist_ok=True); env=os.environ.copy(); env['CHESHIRE_MOLA_DLL']=str(dll.resolve())
    command=[str(ROOT/'.venv/Scripts/python.exe'),'-m','pytest','-q','--basetemp',str(temp),'-o','cache_dir=output/task21/pytest-cache-full']
    started=time.monotonic()
    with (OUT/'full_pytest.txt').open('w',encoding='utf-8') as stream:
        result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
    record=dict(command=command,exit_code=result.returncode,seconds=round(time.monotonic()-started,2),
        full_suite_runs=1,real_Mola_tests='Executed with explicit official DLL; inspect full_pytest.txt for actual result',
        temporary_directory_scope='External fresh temp is required by the existing wrong-repository identity test; no test or guard weakened.')
    (OUT/'test_record.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print((OUT/'full_pytest.txt').read_text(encoding='utf-8'),flush=True)
    if result.returncode: raise SystemExit(result.returncode)
    diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
    (OUT/'diff_check.txt').write_text('git diff --check\n'+diff.stdout+diff.stderr+f'\nexit {diff.returncode}\n',encoding='utf-8')
    raise SystemExit(diff.returncode)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--dll',type=Path,required=True); parser.add_argument('--temp',type=Path,required=True)
    args=parser.parse_args(); main(args.dll,args.temp)
