"""Three controlled recipes using the existing CC, topology and PNG renderer.

Run from any directory with the repository's NumPy/Pillow environment.
Generate: python run.py generate
Render:   python run.py render
No parameter search. No alternative subdivision implementation.
"""
from pathlib import Path
import sys,json,time,gc,hashlib,platform
import numpy as np
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from subdivision import Mesh,cc,check,save_obj,topology
from render import render,font

RECIPE=json.loads((HERE/'recipe.json').read_text(encoding='utf8'))
OUT=ROOT/'output'/'illustration1'

def write_manifest():
    import PIL
    files=[HERE/'recipe.json',HERE/'run.py',ROOT/'src/subdivision.py',ROOT/'src/render.py']
    manifest=dict(python=platform.python_version(),numpy=np.__version__,pillow=PIL.__version__,
                  interpreter=sys.executable,branch='research/hansmeyer-cleanroom',
                  source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                  recipe_tuning_after_generation=False,total_generation_tracks=3)
    (OUT/'run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')

def seed():
    return Mesh(np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],
                          [-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]],float),
                [[3,2,1,0],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]],
                ['P']*8,['F']*6)

def provider(control):
    def get(g,p,group='F',standard=False):
        # p and group intentionally ignored: same numerical weights everywhere.
        if control=='standard_cc': return {k:0. for k in ('w1','w2','w3','w4','w10','w11','w12')}
        w={k:float(RECIPE[k][g-1]) for k in ('w1','w2','w3','w4','w10','w11','w12')}
        if control=='weights_only': w['w12']=0.
        return w
    return get

def geometry_metrics(m):
    # Measurements only; does not move any vertex or alter any face.
    q=np.asarray(m.f,dtype=np.int64); p=m.v[q]
    area_vector=np.cross(p,np.roll(p,-1,axis=1)).sum(axis=1)
    lengths=np.linalg.norm(area_vector,axis=1)
    assert np.isfinite(m.v).all() and np.all(lengths>1e-12)
    unit=area_vector/lengths[:,None]
    edges,_,_=topology(m)
    ef=np.array([[uses[0][0],uses[1][0]] for uses in edges.values()])
    angles=np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i',unit[ef[:,0]],unit[ef[:,1]]),-1,1)))
    assert len(m.v)-len(edges)+len(m.f)==2
    radius=np.linalg.norm(m.v,axis=1)
    return dict(vertices=len(m.v),faces=len(m.f),edges=len(edges),euler=2,
                bounds=[m.v.min(0).tolist(),m.v.max(0).tolist()],
                radius_range=[float(radius.min()),float(radius.max())],
                dihedral_median=float(np.median(angles)),dihedral_p90=float(np.quantile(angles,.9)),
                fraction_dihedral_above45=float(np.mean(angles>45)),
                min_polygon_area_vector=float(lengths.min()))

def load(control,g):
    with np.load(OUT/control/f'G{g}.npz',allow_pickle=False) as z:
        return Mesh(z['vertices'].copy(),z['faces'].tolist(),z['kinds'].tolist())

def generate():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'generation_results.json').exists():
        raise RuntimeError('Existing run preserved. Do not overwrite or expand this experiment silently.')
    # Minimum mathematical checks: masks sum to 1 for each own scheduled row.
    for g in range(1,9):
        w=provider('weights_only')(g,np.zeros(3))
        assert abs(((1+w['w3'])+(1-w['w3']))*(1+w['w4'])/4+2*(1-w['w4'])/4-1)<1e-12
        assert abs(2*(1+w['w1'])/4+2*(1-w['w1'])/4-1)<1e-12
        for n in [3,4]: assert abs(((1+w['w2'])+(2-w['w2'])+(n-3))/n-1)<1e-12
    report={}; first={}
    for control in RECIPE['controls']:
        directory=OUT/control; directory.mkdir(exist_ok=True)
        m=seed(); rows=[]; w=provider(control)
        for g in range(9):
            start=time.perf_counter()
            if g: m=cc(m,g,weight_provider=w)
            assert len(m.f)==6*4**g and len(m.v)==6*4**g+2
            stats=geometry_metrics(m); stats['generation']=g
            if control!='standard_cc':
                with np.load(OUT/'standard_cc'/f'G{g}.npz',allow_pickle=False) as z:
                    assert np.array_equal(z['faces'],np.asarray(m.f))
                    stats['rms_displacement_from_standard']=float(np.sqrt(np.mean(np.sum((m.v-z['vertices'])**2,axis=1))))
            if g==1: first[control]=m.v.copy()
            np.savez_compressed(directory/f'G{g}.npz',vertices=m.v,faces=np.asarray(m.f,np.int64),kinds=np.asarray(m.kinds,dtype='U1'))
            if g in RECIPE['comparison_generations']: save_obj(m,directory/f'G{g}.obj')
            stats['seconds_including_save']=round(time.perf_counter()-start,3); rows.append(stats)
            print(json.dumps(dict(control=control,**stats)),flush=True)
            del stats; gc.collect()
        report[control]=rows
        del m;gc.collect()
    assert np.allclose(first['standard_cc'][:8],seed().v*5/9)
    # Same w1-w4, only w12 differs: face/edge points must remain equal at G1.
    n=8
    assert np.allclose(first['weights_vertex_normal'][n:],first['weights_only'][n:])
    assert np.allclose(first['weights_vertex_normal'][:n]-first['weights_only'][:n],
                       seed().v*(8/3)*RECIPE['w12'][0])
    report['checks']=['finite vertices and nondegenerate polygon normals every G',
                      'closed oppositely oriented two-face edges and Euler 2 every G',
                      'expected CC counts and identical control connectivity',
                      'affine mask sums', 'known standard cube G1 corner',
                      'vertex-only G1 displacement; unchanged G1 face/edge points']
    report['limits']='Combinatorial checks do not prove absence of self-intersections or solid/print validity. No self-intersection repair.'
    (OUT/'generation_results.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    write_manifest()

def camera_max(v):
    r=np.array([.87,-.49,0]);r/=np.linalg.norm(r)
    t=np.array([.47,.83,.29]);t/=np.linalg.norm(t)
    u=np.cross(r,t);u/=np.linalg.norm(u)
    return float(np.max(np.abs(v@r))),float(np.max(np.abs(v@u)))

def render_all():
    if not (OUT/'generation_results.json').exists():raise RuntimeError('Generate first')
    maxx=maxy=0.
    for control in RECIPE['controls']:
        for g in RECIPE['comparison_generations']:
            with np.load(OUT/control/f'G{g}.npz',allow_pickle=False) as z:
                a,b=camera_max(z['vertices']);maxx=max(maxx,a);maxy=max(maxy,b)
    size=(680,740);scale=min((size[0]/2-45)/maxx,(size[1]/2-105)/maxy)
    visual=dict(size=size,scale=scale,camera_right=[.87,-.49,0],camera_toward=[.47,.83,.29],
                light=[-.35,.65,.68],center=[0,0,0],independent_rescaling=False,
                shade='flat per actual polygon; triangle z-buffer; no geometry smoothing')
    (OUT/'camera.json').write_text(json.dumps(visual,indent=2),encoding='utf8')
    rows=[]
    for control in RECIPE['controls']:
        images=[]
        for g in RECIPE['comparison_generations']:
            start=time.perf_counter();m=load(control,g)
            im=render(m.v,m.f,OUT/control/f'G{g}.png',f'{control.replace("_"," ")} | G{g}',scale=scale,size=size)
            images.append(im)
            print(f'rendered {control} G{g}: {time.perf_counter()-start:.1f}s',flush=True)
            del m;gc.collect()
        rows.append(images)
    tile=(408,444);board=Image.new('RGB',(tile[0]*5,100+tile[1]*3),'white');d=ImageDraw.Draw(board)
    d.text((20,12),'Illustration 1 capability test | ONE cube | CC only | G0 / G2 / G4 / G6 / G8',font=font(27),fill=(25,35,45))
    d.text((20,56),'Own fixed uniform schedules | same camera, light and absolute scale | no DS or vertex fusing',font=font(22),fill=(70,80,90))
    for j,row in enumerate(rows):
        for i,im in enumerate(row):board.paste(im.resize(tile,Image.Resampling.LANCZOS),(i*tile[0],100+j*tile[1]))
    board.save(OUT/'comparison.png')
    # G1/G3 aid onset inspection, not extra parameter experiments.
    onset=[]
    for control in RECIPE['controls'][1:]:
        pair=[]
        for g in [1,3]:
            m=load(control,g)
            pair.append(render(m.v,m.f,OUT/control/f'G{g}.png',f'{control.replace("_"," ")} | G{g}',scale=scale,size=size))
        onset.append(pair)
    image=Image.new('RGB',(680*2,100+740*2),'white');d=ImageDraw.Draw(image)
    d.text((20,20),'Onset inspection | SAME recipe | G1 / G3',font=font(27),fill=(25,35,45))
    for j,row in enumerate(onset):
        for i,im in enumerate(row):image.paste(im,(i*680,100+j*740))
    image.save(OUT/'onset.png')
    # Same camera/light, a fixed 2x magnification for all three G8 controls.
    # This is an explicitly labeled center view without per-object auto-fit.
    detail=[]
    for control in RECIPE['controls']:
        m=load(control,8)
        detail.append(render(m.v,m.f,OUT/control/'G8_center_detail.png',f'{control.replace("_"," ")} | G8 CENTER 2x',scale=scale*2,size=(1000,1060)))
    board=Image.new('RGB',(3000,1120),'white');d=ImageDraw.Draw(board)
    d.text((20,12),'G8 center details | 2x scale of main board | same camera and light | no per-object auto-fit',font=font(27),fill=(25,35,45))
    for i,im in enumerate(detail):board.paste(im,(1000*i,60))
    board.save(OUT/'G8_details.png')

if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ('generate','render'):raise SystemExit('Usage: run.py generate|render')
    generate() if sys.argv[1]=='generate' else render_all()
