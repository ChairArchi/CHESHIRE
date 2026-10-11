"""Finite render batch, no scheduler, waiting service, or external automation."""
from pathlib import Path
import argparse, concurrent.futures, json, subprocess, sys, time
HERE=Path(__file__).resolve().parent
DEFAULT='E:/CHESHIRE_DATA/iaac_mandelbrot_20261011'
BLENDER='C:/Users/USER/CHESHIRE/scratch/generative_gate_20261010/external/blender-4.5.4-windows-x64/blender.exe'

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default=DEFAULT)
    p.add_argument('--folders',nargs='*');p.add_argument('--workers',type=int,default=2)
    p.add_argument('--final',action='store_true');args=p.parse_args();root=Path(args.root)
    folders=[root/f for f in args.folders] if args.folders else sorted(root.glob('variations/V*/G02'))
    folders=[f for f in folders if (f/'geometry.npz').exists()]
    logs=root/'render_logs';logs.mkdir(exist_ok=True)
    def run(folder):
        output=folder if args.final else folder/'preview'
        if all((output/(v+'.png')).exists() for v in ('front','oblique','side')):
            return dict(folder=str(folder),status='ALREADY_RENDERED')
        name='_'.join(folder.relative_to(root).parts);start=time.time()
        with (logs/(name+'.log')).open('w') as out,(logs/(name+'.err.log')).open('w') as err:
            command=[BLENDER,'--background','--factory-startup','--threads','8',
                '--python-exit-code','1','--python',str(HERE/'column_render.py'),'--',str(folder)]
            if args.final:command.append('final')
            result=subprocess.run(command,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
        record=dict(folder=str(folder),returncode=result.returncode,elapsed_seconds=time.time()-start,
            complete=all((output/(v+'.png')).exists() for v in ('front','oblique','side')))
        print(json.dumps(record),flush=True);return record
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(run,folders):results.append(result)
    (logs/('final_batch.json' if args.final else 'preview_batch.json')).write_text(json.dumps(results,indent=2))
    assert all(r.get('complete',r.get('status')=='ALREADY_RENDERED') for r in results)

if __name__=='__main__':main()
