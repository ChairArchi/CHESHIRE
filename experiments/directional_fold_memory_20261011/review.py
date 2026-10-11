"""Small review artifacts from actual saved geometry. No image generation."""
from pathlib import Path
import argparse, importlib.util, json, sys
import numpy as np
from scipy.spatial import cKDTree
import trimesh
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageColor

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'iaac_mandelbrot_20261011'))
import study as base
from cheshire.reference_subdivision import topology,fields
ROOT=Path('E:/CHESHIRE_DATA/directional_fold_memory_20261011')
OLDROOT=Path('E:/CHESHIRE_DATA/iaac_mandelbrot_20261011')
FONT='C:/Windows/Fonts/arial.ttf'

def dump(path,data):base.dump(path,data)
def load(folder):
    a=np.load(folder/'geometry.npz')
    return trimesh.Trimesh(a['xyz'],a['faces'],process=False)

def board(path,columns,rows,size=600):
    canvas=Image.new('RGB',(size*len(columns),54+len(rows)*(size+42)),(235,235,232))
    d=ImageDraw.Draw(canvas);font=ImageFont.truetype(FONT,20)
    for c,label in enumerate(columns):d.text((c*size+18,16),label,fill=(20,25,30),font=font)
    for r,(label,images) in enumerate(rows):
        y=54+r*(size+42);d.text((18,y+10),label,fill=(20,25,30),font=font)
        for c,image in enumerate(images):
            with Image.open(image) as im:canvas.paste(im.convert('RGB').resize((size,size)),(c*size,y+42))
    canvas.save(path)

def boards(root):
    out=root/'review';out.mkdir(exist_ok=True)
    views=['front','oblique','side']
    def imgs(folder):return [folder/'preview'/f'{v}.png' for v in views]
    board(out/'A_B_three_views.png',views,[
        ('A / G3: bent panel + legacy memory',imgs(root/'A_FOLD/G03')),
        ('B / local field detail: same topology',imgs(root/'B_LOCAL/G01'))],700)
    board(out/'profile_comparison.png',views,[
        ('Earlier D02 + field G2 + CC (different input; visual reference only)',imgs(OLDROOT/'input_field/DIRECTIONAL_FIELD/G02_CC')),
        ('A refined / G3: rounded expansion (puffed reading remains)',imgs(root/'A_REFINED/G03')),
        ('A fold / G3: same event locations, bent sections',imgs(root/'A_FOLD/G03'))],600)
    stages=['G00','G01','G02','G03']
    board(out/'A_progression.png',stages,[
        (v,[root/('A' if s=='G00' else 'A_FOLD')/s/'preview'/f'{v}.png' for s in stages])
        for v in views],480)
    board(out/'sampling_trial.png',['coarse Gaussian','dense Gaussian','dense bent section'],[
        (v,[root/c/'G03/preview'/f'{v}.png' for c in ['A','A_REFINED','A_FOLD']]) for v in views],500)
    for c in ('A_FOLD/G03','B_LOCAL/G01'):
        name='A_final' if c.startswith('A_') else 'B_final'
        board(out/(name+'_views.png'),views,[(name,imgs(root/c))],650)
    # Actual unretouched crops of existing renders; crop coordinates identical.
    rows=[]
    for c,label in [('A_REFINED/G03','rounded trial'),('A_FOLD/G03','A folded'),('B_LOCAL/G01','B local detail')]:
        paths=[]
        for v in ['front','oblique','side']:
            target=out/(c.replace('/','_')+'_'+v+'_crop.png')
            with Image.open(root/c/'preview'/f'{v}.png') as im:im.crop((265,130,540,460)).save(target)
            paths.append(target)
        rows.append((label,paths))
    board(out/'fold_detail_comparison.png',views,rows,440)

def measurements(root):
    out=root/'review';out.mkdir(exist_ok=True)
    cases=[('G1','A_FOLD/G01','#3574b4'),('G2','A_FOLD/G02','#e8a430'),
           ('A G3','A_FOLD/G03','#173b30'),('B','B_LOCAL/G01','#b72f5d')]
    heights=[2.2,4.5,6.5,7.6]
    canvas=Image.new('RGB',(2240,660),(249,248,244));draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype(FONT,22)
    for i,z in enumerate(heights):
        x=i*560
        draw.text((x+28,24),f'Actual mesh section: z={z}',fill='#202530',font=font)
        draw.rectangle((x+30,85,x+530,585),outline='#b0b0b0')
        draw.line((x+280,85,x+280,585),fill='#dddddd');draw.line((x+30,335,x+530,335),fill='#dddddd')
        draw.text((x+240,592),'X / Y',fill='#555555',font=font)
    stats={};memory={}
    for label,rel,color in cases:
        folder=root/rel;m=load(folder);sections=[]
        for index,z in enumerate(heights):
            segments=trimesh.intersections.mesh_plane(m,[0,0,1],[0,0,z])
            if len(segments):
                xy=segments[:,:,:2]
                projected=xy.copy();projected[:,:,0]=index*560+280+xy[:,:,0]*148
                projected[:,:,1]=335-xy[:,:,1]*148
                for segment in projected:draw.line([tuple(p) for p in segment],fill=color,width=2)
                ext=np.ptp(xy.reshape(-1,2),axis=0)
                sections.append(dict(z=z,width=float(ext[0]),depth=float(ext[1]),depth_width=float(ext[1]/ext[0]),segments=len(xy)))
        control,chart=base.load(folder);t=topology(control);f=fields(control,t)
        weights=np.load(folder/'memory.npz')['weights'];info=json.loads((folder/'memory.json').read_text(encoding='utf8'))
        feature_angles={}
        for i,name in enumerate(info['names']):
            core=weights[:,i]>=1-1e-12
            edges=core[t['edges']].all(1)
            a=f['angles'][edges]
            feature_angles[name]=dict(core_edges=int(edges.sum()),dihedral_p90=float(np.quantile(a,.9)) if len(a) else None,
                diagnostic='Authored band edges; not a detected crease angle or pass threshold')
        dz=control.xyz[t['edges'][:,1],2]-control.xyz[t['edges'][:,0],2]
        ds=chart[t['edges'][:,1],0]-chart[t['edges'][:,0],0]
        ordered=np.abs(ds)>1e-10
        stats[rel]=dict(sections=sections,axial_edges=int(ordered.sum()),
                       reverse_axial_edges=int(((dz*ds<0)&ordered).sum()),
                       reverse_definition='Actual dz opposite to increasing material height; not self-intersection',
                       bounds=m.bounds.tolist())
        memory[rel]=dict(landmarks=json.loads((folder/'generation.json').read_text(encoding='utf8')).get('landmarks'),
                        feature_band_angles=feature_angles)
    for i,(label,_,color) in enumerate(cases):draw.text((30+i*240,628),label,fill=color,font=font)
    canvas.save(out/'sections.png')
    # Projection silhouettes are unions of actual mesh triangles, not hulls.
    masks={};width,height=360,920
    for label,rel,color in cases:
        m=load(root/rel);tris=np.asarray(m.vertices)[m.faces]
        masks[rel]=[]
        for axis in (0,1):
            xy=tris[:,:,[axis,2]].copy();xy[:,:,0]=(xy[:,:,0]+1.8)/3.6*(width-1)
            xy[:,:,1]=(10.3-xy[:,:,1])/10.6*(height-1)
            im=Image.new('L',(width,height),0);draw=ImageDraw.Draw(im)
            for triangle in xy:draw.polygon([tuple(p) for p in triangle],fill=255)
            masks[rel].append(np.asarray(im)>0)
    canvas=Image.new('RGB',(820,1040),(249,248,244));draw=ImageDraw.Draw(canvas)
    for axis in (0,1):
        draw.text((30+410*axis,15),['Front: X/Z','Side: Y/Z'][axis],fill='#202530',font=font)
        layer=np.zeros((height,width,4),dtype=np.uint8)
        for label,rel,color in cases:
            arr=masks[rel][axis]
            inset=np.asarray(Image.fromarray(arr.astype('uint8')*255).filter(ImageFilter.MinFilter(3)))>0
            edge=arr&~inset;layer[edge,:3]=ImageColor.getrgb(color);layer[edge,3]=255
        im=Image.fromarray(layer);canvas.paste(im,(25+410*axis,55),im)
    draw=ImageDraw.Draw(canvas)
    for i,(label,_,color) in enumerate(cases):draw.text((25+200*i,995),label,fill=color,font=font)
    canvas.save(out/'silhouettes.png')
    a,b=load(root/'A_FOLD/G03'),load(root/'B_LOCAL/G01')
    assert np.array_equal(a.faces,b.faces)
    delta=np.linalg.norm(b.vertices-a.vertices,axis=1)
    op=np.load(root/'B_LOCAL/G01/operation_fields.npz')
    zone=op['detail_zone'];inactive=zone==0
    control_delta=np.linalg.norm(op['applied_displacement'],axis=1)
    unchanged_face=(control_delta[np.load(root/'A_FOLD/G03/checkpoint.npz')['faces']]==0).all(1)
    native_nv=len(zone);native_delta=delta[native_nv:]
    stats['A_to_B']=dict(same_triangle_connectivity=True,
        unchanged_outside_zone_control_vertices=int(inactive.sum()),
        outside_zone_control_max_movement=float(control_delta[inactive].max()),
        unchanged_control_faces=int(unchanged_face.sum()),
        physical_fan_centres_on_unchanged_faces_max_movement=float(native_delta[unchanged_face].max()),
        physical_vertices_changed_fraction=float((delta>1e-9).mean()),physical_max_movement=float(delta.max()),
        active_zone_signal_range=[float(op['fractal_signal'][zone>0].min()),float(op['fractal_signal'][zone>0].max())],
        active_zone_inside_fraction=float(op['finite_inside'][zone>0].mean()),
        silhouette_pixel_difference={['front','side'][i]:float(np.logical_xor(masks['A_FOLD/G03'][i],masks['B_LOCAL/G01'][i]).sum()/np.logical_or(masks['A_FOLD/G03'][i],masks['B_LOCAL/G01'][i]).sum()) for i in (0,1)},
        fabrication='Thickness, stability and structural performance NOT_CHECKED')
    dump(out/'measurements.json',stats);dump(out/'memory_metrics.json',memory)

def validate(root):
    checker=Path('C:/Users/USER/CHESHIRE/worktrees/gate-synthesis-20261011/scratch/gate_synthesis_20261011/check_mesh.py')
    spec=importlib.util.spec_from_file_location('existing_check',checker);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    results={}
    for rel in ('A_FOLD/G03','B_LOCAL/G01'):
        folder=root/rel;m=load(folder)
        existing=folder/'gate.validation.json'
        r=json.loads(existing.read_text(encoding='utf8')) if existing.exists() else module.check(folder/'gate.ply',exact=True)
        # The render uses saved float64 arrays whereas PLY exports float32.
        # Check that authoritative surface explicitly; reuse the PLY check.
        pairs=np.asarray(module.cgal.remesh_self_intersections(np.asarray(m.vertices,dtype=np.float64),
            np.asarray(m.faces,dtype=np.int64),detect_only=True,first_only=True)[2])
        actual=dict(source='geometry.npz float64 triangles: exact render source',
                    self_intersections='CONFIRMED' if len(pairs) else 'No intersection pairs found',
                    first_witness_triangle_ids=pairs.tolist(),
                    scope='CGAL detect_only=True first_only=True; not an intersection count')
        if len(pairs):actual['witness_triangle_centres']=np.asarray(m.vertices)[m.faces[pairs[0]]].mean(1).tolist()
        r['authoritative_saved_surface']=actual
        reflected=np.asarray(m.vertices)*[-1,1,1];dist,ids=cKDTree(m.vertices).query(reflected)
        target=np.sort(ids[m.faces],axis=1);original=np.sort(m.faces,axis=1)
        def ordered(a):return a[np.lexsort(a[:,::-1].T)]
        symmetry=dict(vertex_reflection_max_error=float(dist.max()),
                      vertex_pairing_involutive=bool(np.array_equal(ids[ids],np.arange(len(ids)))),
                      reflected_triangles_match=bool(np.array_equal(ordered(target),ordered(original))))
        dump(folder/'symmetry.json',symmetry);r['symmetry']=symmetry;results[rel]=r
    dump(root/'review/validation.json',results)

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['boards','measurements','validate']);p.add_argument('--root',default=str(ROOT))
    args=p.parse_args();root=Path(args.root);(root/'review').mkdir(exist_ok=True)
    {'boards':boards,'measurements':measurements,'validate':validate}[args.phase](root)

if __name__=='__main__':main()
