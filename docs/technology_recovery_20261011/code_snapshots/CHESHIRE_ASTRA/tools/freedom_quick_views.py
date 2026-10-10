"""Quick actual native renders, labels distinguish unchecked/invalid from valid."""
import sys,json,argparse,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'tools'),str(R/'examples')]
from astra_evaluate import render,sha
from task29_search import load_mesh
from hero_design_sprint import guarded
def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
    root=Path('E:/CHESHIRE_DATA/astra_freedom/quick_views')/a.tag
    if not a.tag.replace('_','').isalnum():raise ValueError('Safe tag required')
    if not a.worker:
        root.mkdir(parents=True,exist_ok=False);shutil.copy2(a.request,root/'request.json')
        r=guarded(['--request',str(root/'request.json'),'--tag',a.tag,'--worker'],root/'logs/run',worker_script=Path(__file__))
        (root/'execution.json').write_text(json.dumps(r,indent=2))
        if r['exit_code']:raise SystemExit(r['exit_code'])
        return
    import pyrender
    from PIL import Image
    renderer=pyrender.OffscreenRenderer(600,600);images=[];records=[]
    try:
        for item in json.loads(a.request.read_text()):
            stage=Path(item['stage']);m=load_mesh(stage);label=item['id'];assert label.endswith('_G'+str(m.generation))
            d=root/label;d.mkdir(exist_ok=False)
            val=json.loads((stage/'validation.json').read_text()) if (stage/'validation.json').exists() else {}
            status=val.get('status','UNCHECKED')
            warning=' INVALID' if status=='EXPERIMENTAL_INVALID' or val.get('contacts',{}).get('transverse_contacts',0)>0 else ' UNCHECKED' if not val else ''
            images+=render(m,d,label,renderer,item.get('target',[0,0,2000]),item.get('width',5000),warning)
            if item.get('detail',False):render(m,d,label+'_detail',renderer,item.get('detail_target',[0,0,1000]),1800,warning)
            records.append(dict(**item,native_sha256=sha(stage/'mesh.npz'),generation=m.generation,status=status,camera_width=item.get('width',5000),artifact_sha256={p.name:sha(p) for p in d.iterdir()}))
            print(label,flush=True)
    finally:renderer.delete()
    sheet=Image.new('RGB',(1800,600*(len(images)//3)),'white')
    for i,im in enumerate(images):sheet.paste(im,((i%3)*600,(i//3)*600))
    sheet.save(root/'comparison.png');(root/'summary.json').write_text(json.dumps(records,indent=2))
if __name__=='__main__':main()
