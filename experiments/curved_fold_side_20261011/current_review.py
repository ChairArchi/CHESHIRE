"""Compact final boards and fold retention; no repeated precision testing."""
from pathlib import Path
import json,sys
import numpy as np
import trimesh
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import review
ROOT=review.ROOT

def views(path):return [ROOT/path/'preview'/(v+'.png') for v in review.VIEWS]

def main():
    out=ROOT/'review'
    final=['W06_SYMMETRIC_SMOOTH/G01','GEO01_FAN_MEMORY/G03','GEO02_CHEVRON_MEMORY/G03','GEO03_NESTED_RETURN/G01']
    review.board(out/'final_geometric_comparison.png',['Soft deep valley','Three fold fans','Chevron fold fans','Additional nested return'],
                 [(v,[ROOT/n/'preview'/(v+'.png') for n in final]) for v in review.VIEWS],620)
    review.board(out/'recommended_views.png',review.VIEWS,[('GEO01 / three selected fold fans',views('GEO01_FAN_MEMORY/G03'))],800)
    review.board(out/'soft_vs_angular.png',['V04 / angular deep cup','W06 / rounded deep cup'],
                 [(v,[ROOT/n/'preview'/(v+'.png') for n in ['V04_SYMMETRIC_CUP/G01','W06_SYMMETRIC_SMOOTH/G01']]) for v in review.VIEWS],650)
    review.board(out/'older_to_current.png',['Old A','S02 mirrored strong','W06 deep / rounded','GEO01 local folds'],
                 [(v,[review.OLD/'A_FOLD/G03/preview'/(v+'.png')]+[ROOT/n/'preview'/(v+'.png') for n in ['S02_STRONG_FRONT_MIRROR/G01','W06_SYMMETRIC_SMOOTH/G01','GEO01_FAN_MEMORY/G03']]) for v in review.VIEWS],550)
    for name in ['V04_SYMMETRIC_CUP','W06_SYMMETRIC_SMOOTH']:
        paths=[name+'/G01','F_'+name+'/G01','F_'+name+'/G02']
        review.board(out/(name+'_field_progression.png'),['Input','1 subdivision + field pass 1','Same mesh + field pass 2'],
                     [(v,[ROOT/n/'preview'/(v+'.png') for n in paths]) for v in review.VIEWS],580)
    for name in ['GEO01_FAN_MEMORY','GEO02_CHEVRON_MEMORY']:
        review.board(out/(name+'_progression.png'),['Input','G1 lower valley','G2 upper shoulder','G3 side binding'],
                     [(v,[ROOT/'W06_SYMMETRIC_SMOOTH/G01/preview'/(v+'.png')]+[ROOT/name/f'G{gen:02}/preview'/(v+'.png') for gen in [1,2,3]]) for v in review.VIEWS],500)
    # Actual physical-Z section segments; common axes, all loops shown, no cleanup.
    names=['W06_SYMMETRIC_SMOOTH/G01','GEO01_FAN_MEMORY/G03','GEO02_CHEVRON_MEMORY/G03','F_W06_SYMMETRIC_SMOOTH/G02']
    labels=['W06 soft input','GEO01 fan folds','GEO02 chevron folds','F_W06 field pass 2']
    zs=[2.5,4.0,6.1,8.3];size=360
    im=Image.new('RGB',(size*4,60+size*4),'#f6f5ef');d=ImageDraw.Draw(im);font=ImageFont.truetype(review.FONT,18)
    for i,label in enumerate(labels):d.text((size*i+12,15),label,fill='#203039',font=font)
    for c,name in enumerate(names):
        m=review.mesh(ROOT/name)
        for r,z in enumerate(zs):
            ox=c*size+size/2;oy=60+r*size+size/2
            d.line((ox-145,oy,ox+145,oy),fill='#d8d6ce');d.line((ox,oy-145,ox,oy+145),fill='#d8d6ce')
            d.text((c*size+10,60+r*size+8),f'physical Z={z:g}',fill='#203039',font=font)
            segments=trimesh.intersections.mesh_plane(m,[0,0,1],[0,0,z])
            for p in segments:
                d.line([(ox+70*q[0],oy-70*q[1]) for q in p],fill='#245e68',width=1)
    im.save(out/'current_actual_sections.png')
    g=np.load(ROOT/'W03_PLEAT_CONTROL/G01/checkpoint.npz');ch=g['chart'];birth=g['xyz']
    theta=np.arctan2(ch[:,2],ch[:,1]);centre=(abs(ch[:,1])<1e-12)&(abs(ch[:,2])>.99)
    lower=centre&(ch[:,0]>.36)&(ch[:,0]<.50)
    upper=centre&(ch[:,0]>.73)&(ch[:,0]<.87)
    results={}
    for name in ['GEO01_FAN_MEMORY/G03','GEO02_CHEVRON_MEMORY/G03','GEO03_NESTED_RETURN/G01']:
        x=np.load(ROOT/name/'checkpoint.npz')['xyz'];delta=np.linalg.norm(x-birth,axis=1)
        meta=json.loads((ROOT/name/'generation.json').read_text())
        results[name]=dict(lower_valley_centreline_vertices=int(lower.sum()),lower_centreline_max_movement=float(delta[lower].max()),
                          upper_valley_centreline_vertices=int(upper.sum()),upper_centreline_max_movement=float(delta[upper].max()),
                          maximum_total_displacement=float(delta.max()),generation_metadata=meta)
    results['scope']='Stored material centreline coordinates, not every fold angle or a unique physical-Z groove depth. Actual section board shows all loops including intersections.'
    review.dump(out/'current_fold_retention.json',results)
    print('CURRENT BOARDS COMPLETE',flush=True)
if __name__=='__main__':main()
