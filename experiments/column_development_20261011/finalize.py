"""Package small review artifacts; validate only explicitly selected meshes."""
from pathlib import Path
import argparse, contextlib, io, json, shutil, sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'curved_fold_side_20261011'))
import review
ROOT=Path('E:/CHESHIRE_DATA/column_development_20261011')
DOCS=HERE.parents[1]/'docs/column_development_20261011'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--validate',nargs='*',default=[])
    args=p.parse_args()
    checks={}
    for name in args.validate:
        with contextlib.redirect_stdout(io.StringIO()): check=review.validate(ROOT/name)
        checks[name]=check
        print('VALIDATE',name,'components',check['components'],'closed',check['watertight'],
              'X/Y',check['mirror_max_distance'],check['front_back_reflection']['maximum_vertex_distance'],
              'area_pass',check['minimum_area_pass'],'intersection',check['self_intersection'],flush=True)
    if checks: review.dump(ROOT/'review/final_validation.json',checks)
    image_dir=DOCS/'images';technical=DOCS/'technical'
    image_dir.mkdir(parents=True,exist_ok=True);technical.mkdir(parents=True,exist_ok=True)
    for path in (ROOT/'review').glob('*.png'): shutil.copy2(path,image_dir/path.name)
    for path in (ROOT/'review').glob('*.json'): shutil.copy2(path,technical/path.name)
    entries=[]
    for metadata in sorted(ROOT.glob('**/generation.json')):
        folder=metadata.parent
        item=json.loads(metadata.read_text(encoding='utf8'))
        entries.append(dict(candidate=item['candidate'],stage=item['stage'],folder=str(folder),
            vertices=item.get('vertices'),triangles=item.get('triangles'),
            files={name:str(folder/name) for name in ('gate.ply','geometry.npz','checkpoint.npz','control_quad.npz','operation_fields.npz','generation.json','recipe.py') if (folder/name).exists()},
            previews={v:str(folder/'preview'/(v+'.png')) for v in review.VIEWS},
            blender=str(folder/'column.blend') if (folder/'column.blend').exists() else None))
    review.dump(DOCS/'INDEX.json',dict(output_root=str(ROOT),checkpoints=entries,
        original_catalogue='E:/CHESHIRE_DATA/terminal_fold_20261011',
        branch='experiment/column-fold-development-20261011',
        source_code=str(HERE),scope='Actual file pointers; no repeat hash audit. Large meshes remain on E. OBJ not exported.'))
    print('PACKAGED',len(entries),'actual checkpoints',str(DOCS),flush=True)

if __name__=='__main__': main()
