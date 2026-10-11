"""Check actual geometry response, shared controls and saved-operation replay."""
from pathlib import Path
import argparse
import json

import numpy as np

import study
from region_fold import proposal


def run(roots,output):
    result=[]
    for root in roots:
        case_recipes=[]
        for case in ('SPAN','COUNTER'):
            for mode in ('CONTROL','GROOVE','RETURN'):
                folder=root/mode/case/'G03'
                metadata=json.loads((folder/'generation.json').read_text())
                assert metadata['quick_integrity']=='PASS'
                case_recipes.append(metadata['recipe'])
                with np.load(folder/'operation_fields.npz') as data:
                    reference,chart,actual=data['reference_xyz'],data['chart'],data['delta']
                guides=[]
                for i in (0,1):
                    with np.load(folder/f'guide_{i}.npz') as data:
                        guides.append({key:data[key] for key in data.files})
                delta,_=proposal(reference,chart,guides,mode='GROOVE' if mode=='CONTROL' else mode,
                    depth_ratio=0 if mode=='CONTROL' else .28,angle=.65)
                existing=study.anchor.t.prior.helpers.existing
                existing.reflect(delta,chart,existing.symmetry(chart))
                error=float(np.abs(delta-actual).max())
                assert error<1e-12
                result.append(dict(root=str(root),case=case,mode=mode,replay_max_error=error,
                    geometry_sha256=study.digest(folder/'geometry.npz'),source_sha256=metadata['source_control_sha256']))
        assert all(recipe==case_recipes[0] for recipe in case_recipes)
        # Different actual inputs must give different guide positions or frames,
        # rather than merely reapplying the same authored coordinate vectors.
        for i in (0,1):
            with np.load(root/'GROOVE'/'SPAN'/'G03'/f'guide_{i}.npz') as a, np.load(root/'GROOVE'/'COUNTER'/'G03'/f'guide_{i}.npz') as b:
                assert not np.array_equal(a['centres'],b['centres'])
    output.write_text(json.dumps(dict(status='PASS',cases=result,
        scope='Same saved reference + exact guide records replay; shared coefficients verified per root. Not an independent fresh-environment install or self-intersection audit.'),indent=2),encoding='utf8')
    print('VERIFIED',len(result),'saved operations; same coefficients on both inputs; geometry-responsive guides')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--roots',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run([r.resolve() for r in args.roots],args.output.resolve())
