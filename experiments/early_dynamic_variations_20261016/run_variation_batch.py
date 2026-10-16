"""Isolated-process early mesh replay batch; failures and previous files survive."""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import time


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()


def write(p,v):
    Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--catalog',type=Path,required=True)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--workers',type=int,default=2)
    p.add_argument('--only',nargs='*')
    p.add_argument('--driver',type=Path)
    p.add_argument('--batch-name',default='BATCH')
    a=p.parse_args()
    catalog=json.loads(a.catalog.read_text(encoding='utf8'))
    recipes=catalog['recipes']
    if a.only:recipes=[r for r in recipes if r['id'] in a.only]
    if len({r['id'] for r in recipes})!=len(recipes):raise ValueError('Duplicate variation ids.')
    src=Path(__file__).parent
    driver=a.driver or src/'macro_replay.py'
    out=a.root/'variants'
    out.mkdir(parents=True,exist_ok=True)
    config=a.root/'recipes'
    config.mkdir(exist_ok=True)
    logs=a.root/'logs'
    logs.mkdir(exist_ok=True)
    started=time.perf_counter()
    def run(r):
        path=config/(r['id']+'.json')
        if path.exists():
            if json.loads(path.read_text(encoding='utf8'))!=r:raise ValueError('Recipe changed: '+r['id'])
        else:write(path,r)
        target=out/r['id']
        receipt=target/'RECEIPT.json'
        if target.exists():
            return dict(id=r['id'],status='PRESERVED_EXISTING',receipt=str(receipt),root=str(target))
        log=logs/(r['id']+'.log')
        t=time.perf_counter()
        cmd=[sys.executable,'-B','-X','utf8',str(driver),'--recipe',str(path),'--output',str(target)]
        with log.open('w',encoding='utf8') as f:
            result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        row=dict(id=r['id'],status='COMPLETED' if result.returncode==0 else 'FAILED_PRESERVED',
            exit_code=result.returncode,root=str(target),log=str(log),elapsed_seconds=time.perf_counter()-t)
        print(json.dumps(row,ensure_ascii=False),flush=True)
        return row
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        pending={pool.submit(run,r):r['id'] for r in recipes}
        for future in concurrent.futures.as_completed(pending):
            try:rows.append(future.result())
            except Exception as e:rows.append(dict(id=pending[future],status='RUNNER_ERROR',error=repr(e)))
            write(a.root/(a.batch_name+'_PROGRESS.json'),dict(results=rows,total=len(recipes)))
    rows.sort(key=lambda r:r['id'])
    write(a.root/(a.batch_name+'_RECEIPT.json'),dict(kind='ISOLATED_ACTUAL_EARLY_MESH_REPLAY_BATCH',results=rows,
        source_catalog=str(a.catalog),catalog_sha256=sha(a.catalog),driver_sha256=sha(driver),
        elapsed_seconds=time.perf_counter()-started))


if __name__=='__main__':main()
