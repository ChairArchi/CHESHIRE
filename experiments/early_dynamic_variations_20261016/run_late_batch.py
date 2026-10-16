"""Regenerate existing late operators sequentially on selected actual parents."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time

STAGES=('G05_DIRECTIONAL','G06_DEPTH08','G06_MIDDLE','G07_SURFACE',
        'G07_LINKED_RAW','G07_LINKED_FINISHED','G07_WIDE_RAW','G07_FINAL')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--ids',nargs='+',required=True)
    p.add_argument('--through',choices=['G06_MIDDLE','G07_FINAL'],default='G06_MIDDLE')
    a=p.parse_args()
    driver=Path(__file__).with_name('late_detail_adapter.py')
    results=[]
    logs=a.root/'logs'
    for ident in a.ids:
        target=a.root/'variants'/ident
        for stage in STAGES[:STAGES.index(a.through)+1]:
            dest=target/'states'/stage
            if dest.exists():
                if not (dest/'LATE_EXECUTION_RECEIPT.json').exists():
                    raise RuntimeError('Incomplete existing stage preserved: '+str(dest))
                continue
            log=logs/(ident+'_'+stage+'.log')
            started=time.perf_counter()
            cmd=[sys.executable,'-B','-X','utf8',str(driver),'--root',str(target),'--stage',stage]
            with log.open('w',encoding='utf8') as f:
                r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            row=dict(id=ident,stage=stage,returncode=r.returncode,elapsed_seconds=time.perf_counter()-started,log=str(log))
            results.append(row)
            print(json.dumps(row),flush=True)
            (a.root/'LATE_BATCH_PROGRESS.json').write_text(json.dumps(results,indent=2),encoding='utf8')
            if r.returncode:raise RuntimeError('Late actual-parent generation failed; see '+str(log))


if __name__=='__main__':main()
