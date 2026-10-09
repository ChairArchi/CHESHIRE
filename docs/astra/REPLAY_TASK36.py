"""Path-only replay adapter; preserves the Task36 algorithm and RAM guard.
All output goes into a fresh Astra experiment directory, never a historical root.
"""
import argparse,json,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(REPO/'src'),str(REPO/'tools'),str(REPO/'examples')]
import task36_research as research
from hero_design_sprint import guarded

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate',choices=['U01_INTERVAL_SAFE_G8','W03_BODY_RECURSIVE_G8'],required=True)
    parser.add_argument('--tag',required=True)
    parser.add_argument('--generations',type=int,choices=range(1,9),default=8)
    parser.add_argument('--worker',action='store_true')
    args=parser.parse_args()
    if not args.tag.replace('_','').isalnum():raise ValueError('Fresh alphanumeric/underscore tag required.')
    parent=Path('E:/CHESHIRE_DATA/astra/experiments').resolve()
    root=(parent/args.tag).resolve()
    if root.parent!=parent:raise ValueError('Output must be one new Astra experiment directory.')
    research.ROOT=root
    recipe=REPO/'studies/task36/definitions'/(args.candidate+'.json')
    request=json.loads(recipe.read_text(encoding='utf-8'))
    request['generations']=args.generations
    if args.worker:
        saved=json.loads((root/'replay_request.json').read_text())
        if saved!=request:raise ValueError('Worker request identity changed.')
        research.run(request,args.tag)
        if not (root/'candidates'/args.tag/'completed.json').exists():raise RuntimeError('Geometry rejected; retained diagnostics are not a completed candidate.')
        return
    research.preflight(request)
    root.mkdir(parents=False,exist_ok=False)
    (root/'replay_request.json').write_text(json.dumps(request,indent=2)+'\n')
    result=guarded(['--candidate',args.candidate,'--tag',args.tag,'--generations',str(args.generations),'--worker'],root/'logs/run',worker_script=Path(__file__))
    (root/'execution.json').write_text(json.dumps(result,indent=2)+'\n')
    if result['exit_code']:raise SystemExit(result['exit_code'])
    print(root,flush=True)

if __name__=='__main__':main()
