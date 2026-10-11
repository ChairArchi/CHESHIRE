"""Small local review package; raw geometry stays on E. No mass hash audit."""
from pathlib import Path
import json, shutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
ROOT=Path('E:/CHESHIRE_DATA/terminal_fold_20261011')
DOC=REPO/'docs/terminal_fold_20261011'

def main():
    for p in (DOC/'images',DOC/'technical'):p.mkdir(parents=True,exist_ok=True)
    for p in (ROOT/'review/catalogue').glob('*.png'):shutil.copy2(p,DOC/'images'/p.name)
    for p in (ROOT/'review').glob('*.png'):
        if p.name in ('repeat_actual_sections.png','repeat_endpoint_sections.png','terminal_comparison.png'):
            shutil.copy2(p,DOC/'images'/p.name)
    records=[]
    for p in sorted(ROOT.glob('*/G*/geometry.npz')):
        folder=p.parent;meta=json.loads((folder/'generation.json').read_text(encoding='utf8'))
        item=dict(folder=str(folder),geometry=str(p),checkpoint=str(folder/'checkpoint.npz'),
                  mesh=str(folder/'gate.ply'),generation_file=str(folder/'generation.json'),
                  candidate=meta.get('candidate'),stage=meta.get('stage',meta.get('generation')),
                  vertices=meta.get('physical_vertices',meta.get('vertices')),
                  triangles=meta.get('physical_triangles',meta.get('triangles')),
                  minimum_area_pass=meta.get('minimum_area_pass'),
                  preview={v:str(folder/'preview'/(v+'.png')) for v in ('front','oblique','side')
                           if (folder/'preview'/(v+'.png')).exists()})
        for name in ('control_quad.npz','core_validation.json','column.blend','operation_fields.npz'):
            if (folder/name).exists():item[name]=str(folder/name)
        records.append(item)
        if (folder/'core_validation.json').exists():shutil.copy2(folder/'core_validation.json',DOC/'technical'/(folder.parent.name+'_'+folder.name+'_validation.json'))
    for p in (ROOT/'review/catalogue').glob('*.json'):shutil.copy2(p,DOC/'technical'/p.name)
    for p in (ROOT/'review').glob('*.json'):shutil.copy2(p,DOC/'technical'/p.name)
    data=dict(data_root=str(ROOT),branch='experiment/terminal-fold-field-20261011',
              source_commit='cb5cee36a919c366a7b6ae381e802aa3a351c404',
              code=[str(p.relative_to(REPO)).replace('\\','/') for p in HERE.glob('*.py')],
              records=records,scope='Actual local outputs, including failures and unused input adapters. No raw mesh copied into the repository; no new mass hash audit.')
    (DOC/'INDEX.json').write_text(json.dumps(data,indent=2),encoding='utf8')
    print('PACKAGED',len(records),'actual checkpoints',DOC,flush=True)

if __name__=='__main__':main()
