"""Package a bounded two-input review from preserved, completed local runs.

Does not generate, repair or render geometry. Existing files must be identical;
different artifacts are never silently replaced. Large full runs stay in output/.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_identical_or_new(source, target):
    if target.exists():
        if digest(source) != digest(target):
            raise FileExistsError('Different review artifact preserved: '+str(target))
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def angles(vectors):
    return np.degrees(np.arccos(np.clip(np.sum(vectors[:-1]*vectors[1:],axis=1),-1,1)))


def run(transverse, longitudinal, coherent, replay, output):
    variants = dict(transverse=transverse, longitudinal_native=longitudinal,
                    longitudinal_region=coherent)
    summary = dict(base_revision='8a4cc2e4367802123d6f5fd24e70620259463642',
        selected='longitudinal_region / GROOVE', variants={}, frames=[],
        fresh_packaged_input_replay=[], sources={}, tests=dict(passed=9,
        command='python -B -m pytest -q tests/test_fold_region_growth.py -p no:cacheprovider',
        scope='New experiment tests only; historical suite was not rerun'))
    for name, root in variants.items():
        summary['variants'][name]=json.loads((root/'basin_summary.json').read_text())
        # Metadata wording was corrected after measuring; only the semantic
        # description is changed in the review copy, never the preserved run.
        for case in ('SPAN','COUNTER'):
            for mode in ('CONTROL','GROOVE','RETURN'):
                folder=root/mode/case/'G03'
                for group in ('preview','detail'):
                    copy_identical_or_new(folder/group/'render_receipt.json',
                        output/'render_receipts'/name/mode/case/(group+'.json'))
                if (folder/'render_reuse.json').exists():
                    copy_identical_or_new(folder/'render_reuse.json',
                        output/'render_receipts'/name/mode/case/'reuse.json')
            for mode in ('GROOVE','RETURN'):
                data=json.loads((root/mode/case/'G03/basin_measurements.json').read_text())
                data['detection']='Unfiltered native triangle samples; prominence 4% of measured shoulder arc; location matching in transverse material coordinate'
                path=output/'measurements'/name/(case+'_'+mode+'.json')
                path.parent.mkdir(parents=True,exist_ok=True)
                encoded=json.dumps(data,indent=2).encode('utf8')
                if path.exists() and path.read_bytes()!=encoded:
                    raise FileExistsError(str(path))
                path.write_bytes(encoded)
    checkpoints=('control_quad.npz','geometry.npz','generation.json',
                 'operation_fields.npz','guide_0.npz','guide_1.npz')
    for case in ('SPAN','COUNTER'):
        lead=coherent/'GROOVE'/case/'G03'
        for file in checkpoints+('measured_profiles.npz',):
            copy_identical_or_new(lead/file,output/'review_assets'/('GROOVE_'+case+'_G03')/file)
        for file in ('control_quad.npz','geometry.npz','generation.json'):
            copy_identical_or_new(coherent/'CONTROL'/case/'G03'/file,
                output/'review_assets'/('CONTROL_'+case+'_G03')/file)
        metadata=json.loads((lead/'generation.json').read_text())
        summary['sources'][case]=dict(input_sha256=metadata['source_control_sha256'],
            maximum_displacement=metadata['maximum_displacement'],
            inherited_controls_moved=metadata['inherited_controls_moved'],
            minimum_triangle_area=metadata['minimum_triangle_area'],
            reflection_error=metadata['geometric_reflection_error'],
            quick_integrity=metadata['quick_integrity'], measured_guides=metadata['measured_guides'])
        for file in checkpoints:
            a,b=lead/file,replay/'GROOVE'/case/'G03'/file
            # generation.json contains source paths; compare numerical archives.
            if a.suffix=='.npz':
                with np.load(a) as x,np.load(b) as y:
                    equal=set(x.files)==set(y.files) and all(np.array_equal(x[k],y[k]) for k in x.files)
                assert equal, (case,file)
                summary['fresh_packaged_input_replay'].append(dict(case=case,file=file,arrays_identical=equal))
        for index in (0,1):
            record=dict(case=case,guide=index)
            for name,root in (('native',longitudinal),('region',coherent)):
                with np.load(root/'GROOVE'/case/'G03'/f'guide_{index}.npz') as guide:
                    record[name]={field:dict(median=float(np.median(angles(guide[field]))),
                        maximum=float(angles(guide[field]).max()),
                        adjacent_over_45_degrees=int((angles(guide[field])>45).sum()))
                        for field in ('tangent','normal')}
            summary['frames'].append(record)
        for group in ('whole','detail'):
            copy_identical_or_new(coherent/'images'/(case.lower()+'_'+group+'.png'),
                output/'images'/(case.lower()+'_'+group+'.png'))
        copy_identical_or_new(transverse/'images'/(case.lower()+'_detail.png'),
            output/'images'/('transverse_'+case.lower()+'_detail.png'))
    summary['scope']='Finite two-input G2-to-G3 research. Not recursive, arbitrary-mesh, origami, self-intersection or fabrication certification.'
    summary_path=output/'SUMMARY.json'
    encoded=json.dumps(summary,indent=2).encode('utf8')
    if summary_path.exists() and summary_path.read_bytes()!=encoded:
        raise FileExistsError(str(summary_path))
    summary_path.write_bytes(encoded)
    files={str(p.relative_to(REPO)).replace('\\','/'):dict(bytes=p.stat().st_size,sha256=digest(p))
        for p in sorted(output.rglob('*')) if p.is_file() and p.name!='MANIFEST.json'}
    files.update({str(p.relative_to(REPO)).replace('\\','/'):dict(bytes=p.stat().st_size,sha256=digest(p))
        for p in sorted(HERE.glob('*.py'))})
    test=REPO/'tests/test_fold_region_growth.py'
    files[str(test.relative_to(REPO)).replace('\\','/')]=dict(bytes=test.stat().st_size,sha256=digest(test))
    attributes=REPO/'.gitattributes'
    files['.gitattributes']=dict(bytes=attributes.stat().st_size,sha256=digest(attributes))
    (output/'MANIFEST.json').write_text(json.dumps(dict(files=files),indent=2),encoding='utf8')
    print('PACKAGED',len(files),'files',sum(v['bytes'] for v in files.values()),'bytes')
    print(json.dumps(summary['sources'],indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('transverse','longitudinal','coherent','replay','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    run(*(getattr(args,name).resolve() for name in ('transverse','longitudinal','coherent','replay','output')))
