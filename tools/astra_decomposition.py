"""Independent controlled ablations of the preserved Task36 operator.

No historical source is edited. The adapter changes explicit recipe values,
output root and strengthens every contact check to include shared vertices.
"""
import argparse,json,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
import task36_research as old
import task36_contacts as contact_module
from hero_design_sprint import guarded

def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--generations',type=int,default=5)
    p.add_argument('--case',choices=['C00_ORIGINAL','C01_BLEND','C02_DIAGONAL','C03_COMBINED','C04_REST'],required=True)
    p.add_argument('--worker',action='store_true');a=p.parse_args()
    if not a.tag.replace('_','').isalnum():raise ValueError('Safe fresh tag required.')
    root=Path('E:/CHESHIRE_DATA/astra_research/decomposition')/a.tag
    old.ROOT=root
    original=contact_module.contacts
    def inclusive(mesh,**kwargs):
        kwargs.update(interval=True,include_shared=True)
        return original(mesh,**kwargs)
    contact_module.contacts=inclusive
    old.SOURCES=old.SOURCES+['tools/astra_decomposition.py']
    request=json.loads((REPO/'studies/task36/definitions/U01_INTERVAL_SAFE_G8.json').read_text())
    request['generations']=a.generations
    if a.case in ['C01_BLEND','C03_COMBINED','C04_REST']:request['parameters']['averaging_gain']=.65
    if a.case in ['C02_DIAGONAL','C03_COMBINED','C04_REST']:request['parameters']['diagonal_tension']=.2
    if a.case=='C04_REST':request['parameters']['source']='rest'
    request['astra_explanation']={'C00_ORIGINAL':'Preserved signed decomposition baseline, inclusive checker.',
      'C01_BLEND':'Averaging gain .65: I+.65*(weighted-I), no subtraction-only anti-smoothing.',
      'C02_DIAGONAL':'Only class diagonal tension reduced 1.6 to .2; original decomposition retained.',
      'C03_COMBINED':'Combine the two separately tested changes.',
      'C04_REST':'Combined operator with frozen neutral feature observation; placement remains current.'}[a.case]
    if a.worker:
        if request!=json.loads((root/'request.json').read_text()):raise ValueError('Recipe changed.')
        old.run(request,a.case)
        return
    root.parent.mkdir(parents=True,exist_ok=True)
    old.preflight(request);root.mkdir(parents=True,exist_ok=False)
    (root/'request.json').write_text(json.dumps(request,indent=2),encoding='utf8')
    result=guarded(['--tag',a.tag,'--generations',str(a.generations),'--case',a.case,'--worker'],root/'logs/run',worker_script=Path(__file__))
    (root/'execution.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    status='COMPLETE' if (root/'candidates'/a.case/'completed.json').exists() else 'REJECTED_OR_INTERRUPTED'
    print(a.case,status,result,flush=True)
    if result['exit_code']:raise SystemExit(result['exit_code'])
if __name__=='__main__':main()
