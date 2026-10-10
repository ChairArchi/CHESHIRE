"""Reuse fixed physical cameras and existing interval validation, in new archive."""
import sys,argparse,json,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'tools'),str(R/'examples')]
from astra_evaluate import evaluate
from hero_design_sprint import guarded
def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if not a.tag.replace('_','').isalnum():raise ValueError('Safe tag required')
    root=Path('E:/CHESHIRE_DATA/astra_freedom/evaluation')/a.tag
    if a.worker:evaluate(json.loads((root/'request.json').read_text()),root);return
    root.mkdir(parents=True,exist_ok=False);shutil.copy2(a.request,root/'request.json');shutil.copy2(R/'tools/astra_evaluate.py',root/'evaluator_source.py')
    result=guarded(['--request',str(root/'request.json'),'--tag',a.tag,'--worker'],root/'logs/run',worker_script=Path(__file__))
    (root/'execution.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    if result['exit_code']:raise SystemExit(result['exit_code'])
if __name__=='__main__':main()
