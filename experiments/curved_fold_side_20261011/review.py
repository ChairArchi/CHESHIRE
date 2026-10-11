"""Actual mesh review; small charts and boards, core checks on selections only."""
from pathlib import Path
import argparse,json,sys,time
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent
ROOT=Path('E:/CHESHIRE_DATA/curved_fold_side_20261011')
OLD=Path('E:/CHESHIRE_DATA/directional_fold_memory_20261011')
FONT='C:/Windows/Fonts/arial.ttf'
VIEWS=['front','oblique','side']

def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def mesh(folder):
    g=np.load(folder/'geometry.npz');return trimesh.Trimesh(g['xyz'],g['faces'],process=False)
def board(path,columns,rows,size=380):
    canvas=Image.new('RGB',(size*len(columns),52+(size+35)*len(rows)),(235,235,231))
    d=ImageDraw.Draw(canvas);font=ImageFont.truetype(FONT,18)
    for c,label in enumerate(columns):d.text((c*size+12,15),label,fill='#202a30',font=font)
    for r,(label,paths) in enumerate(rows):
        y=52+r*(size+35);d.text((12,y+7),label,fill='#202a30',font=font)
        for c,p in enumerate(paths):
            with Image.open(p) as im:canvas.paste(im.convert('RGB').resize((size,size)),(c*size,y+35))
    canvas.save(path)

def catalogue():
    out=ROOT/'review';out.mkdir(exist_ok=True)
    cs=sorted(ROOT.glob('C*/G02'));rs=sorted(ROOT.glob('R*/G01'))
    for name,folders,size in [('curve_catalogue',cs,340),('reflection_catalogue',rs,430)]:
        board(out/(name+'.png'),[p.parent.name for p in folders],[(v,[p/'preview'/(v+'.png') for p in folders]) for v in VIEWS],size)
    board(out/'matched_sampling.png',['Same surface / uniform rows','Same surface / crease-aligned rows'],
          [(v,[ROOT/p/'G02/preview'/(v+'.png') for p in ['C00_UNALIGNED','C01_ALIGNED']]) for v in VIEWS],520)

def roughness(m):
    # Orientation-filtered only; includes occluded edges. Not a visible-image score.
    normals=m.face_normals;adj=m.face_adjacency;edges=m.face_adjacency_edges
    angles=np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i',normals[adj[:,0]],normals[adj[:,1]]),-1,1)))
    length=np.linalg.norm(m.vertices[edges[:,0]]-m.vertices[edges[:,1]],axis=1)
    result={}
    for name,view in [('front',[0,1,0]),('side',[-1,0,0])]:
        choose=(normals[adj[:,0]]@view>.1)&(normals[adj[:,1]]@view>.1)
        for subtype,mask in [('all_edges',choose),('quad_fan_internal',choose&(adj[:,0]//4==adj[:,1]//4))]:
            a=angles[mask];l=length[mask]
            result[name+'_'+subtype]=dict(edges=len(a),angle_p95=float(np.percentile(a,95)) if len(a) else None,
                length_fraction_over_30_deg=float(l[a>30].sum()/l.sum()) if l.sum() else None)
    return result

def diagnostics():
    out=ROOT/'review';out.mkdir(exist_ok=True)
    results={}
    for name,folder in [('OLD_A_FOLD_G3',OLD/'A_FOLD/G03'),('C00_UNALIGNED',ROOT/'C00_UNALIGNED/G02'),('C01_ALIGNED',ROOT/'C01_ALIGNED/G02')]:
        results[name]=roughness(mesh(folder))
    results['scope']='Descriptive dihedral diagnostics, no ray occlusion; not aesthetic pass thresholds. C00/C01 same continuous geometry, same counts, different mesh alignment.'
    dump(out/'sampling_diagnostics.json',results)

def a_comparison():
    out=ROOT/'review';out.mkdir(exist_ok=True)
    paths=[ROOT/n/s for n,s in [('P00_BROAD_MEMORY','G03'),('P01_LINE_MEMORY','G03'),('P02_CONNECTED_PANELS','G03'),
                              ('P03_OVERLAP','G03'),('P04_EIGHT_GUIDES','G01'),('P05_SIXTEEN_GUIDES','G01')]]
    board(out/'A_repair_catalogue.png',['A original']+[p.parent.name for p in paths],
          [(v,[OLD/'A_FOLD/G03/preview'/(v+'.png')]+[p/'preview'/(v+'.png') for p in paths]) for v in VIEWS],380)
    diagnostics={p.parent.name:roughness(mesh(p)) for p in paths}
    dump(out/'A_repair_dihedral_diagnostics.json',diagnostics)

def silhouette_comparison(names):
    out=ROOT/'review';out.mkdir(exist_ok=True)
    models=[('Original A',mesh(OLD/'A_FOLD/G03'),'#a86c44')]+[(n,mesh(ROOT/n),c) for n,c in zip(names,['#147a78','#613b97','#2674b5'])]
    canvas=Image.new('RGB',(1000,1090),'#f7f6f0');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype(FONT,20)
    masks={};stats={}
    for axis in (0,1):
        draw.text((25+axis*500,18),['Front / XZ','Side / YZ'][axis],fill='#202a30',font=font)
        for label,m,color in models:
            p=np.array(m.triangles[:,:,[axis,2]]);p[:,:,0]=p[:,:,0]*110+225;p[:,:,1]=990-p[:,:,1]*93
            im=Image.new('L',(450,990),0);d=ImageDraw.Draw(im)
            for t in p:d.polygon([tuple(q) for q in t],fill=255)
            mask=np.asarray(im)>0;masks[label,axis]=mask
            from PIL import ImageFilter,ImageColor
            inner=np.asarray(im.filter(ImageFilter.MinFilter(3)))>0;edge=mask&~inner
            rgba=np.zeros((990,450,4),np.uint8);rgba[edge,:3]=ImageColor.getrgb(color);rgba[edge,3]=255
            layer=Image.fromarray(rgba);canvas.paste(layer,(25+500*axis,50),layer)
            if label!='Original A':
                old=masks['Original A',axis];stats.setdefault(label,{})[['front','side'][axis]]=float(np.logical_xor(old,mask).sum()/np.logical_or(old,mask).sum())
    draw=ImageDraw.Draw(canvas)
    for k,(label,_,color) in enumerate(models):draw.text((25+k*320,1050),label,fill=color,font=font)
    canvas.save(out/'A_preserved_silhouettes.png');dump(out/'silhouette_differences.json',dict(pixel_xor_over_union=stats,scope='Union of actual projected triangles. Silhouette retention is not full surface or shadow equivalence.'))

def validate(folder):
    start=time.time();m=mesh(folder);xyz=np.asarray(m.vertices);tri=np.asarray(m.faces)
    edge_count=np.bincount(m.edges_unique_inverse)
    components=trimesh.graph.connected_components(m.face_adjacency,nodes=np.arange(len(tri)),min_len=1)
    distance,pairs=cKDTree(xyz).query(xyz*[-1,1,1])
    actual=np.sort(tri,1);reflected=np.sort(pairs[tri],1)
    def sortrows(a):return a[np.lexsort((a[:,2],a[:,1],a[:,0]))]
    r=dict(folder=str(folder),vertices=len(xyz),triangles=len(tri),finite=bool(np.isfinite(xyz).all()),
           components=len(components),boundary_edges=int((edge_count==1).sum()),nonmanifold_edges=int((edge_count>2).sum()),
           watertight=bool(m.is_watertight),winding_consistent=bool(m.is_winding_consistent),minimum_triangle_area=float(m.area_faces.min()),
           minimum_area_threshold=1e-12,minimum_area_pass=bool(m.area_faces.min()>1e-12),
           mirror_max_distance=float(distance.max()),mirror_pairing_involution=bool(np.array_equal(pairs[pairs],np.arange(len(xyz)))),
           reflected_triangle_set_identical=bool(np.array_equal(sortrows(actual),sortrows(reflected))),
           checker_input='Authoritative float64 geometry.npz, identical to renderer input',fabrication_thickness_structure='NOT_CHECKED')
    yd,yp=cKDTree(xyz).query(xyz*[1,-1,1])
    r['front_back_reflection']=dict(maximum_vertex_distance=float(yd.max()),pairing_involution=bool(np.array_equal(yp[yp],np.arange(len(xyz)))),
        reflected_triangle_set_identical=bool(np.array_equal(sortrows(actual),sortrows(np.sort(yp[tri],1)))))
    sys.path.insert(0,'C:/Users/USER/CHESHIRE/scratch/generative_gate_20261010/deps')
    from igl.copyleft import cgal
    witness=np.asarray(cgal.remesh_self_intersections(xyz.astype(np.float64),tri.astype(np.int64),detect_only=True,first_only=True)[2])
    r.update(self_intersection='CONFIRMED' if len(witness) else 'NO_PAIRS_DETECTED',first_witness_triangle_ids=witness.tolist(),
             intersection_scope='CGAL detect_only first_only. Positive is a witness, not an exhaustive count; zero does not certify fabrication.',elapsed_seconds=time.time()-start)
    if len(witness):r['witness_centres']=m.triangles_center[witness].tolist()
    if (folder/'crease_curves.npz').exists():
        g=np.load(folder/'crease_curves.npz');old=np.load(folder.parent/'G01/crease_curves.npz')
        d,_=cKDTree(xyz).query(old['curves'].reshape(-1,3));r['G1_crease_max_distance_to_actual_vertices']=float(d.max())
    dump(folder/'core_validation.json',r);print(json.dumps(r),flush=True);return r

def selected(names):
    out=ROOT/'review';out.mkdir(exist_ok=True)
    finals=[ROOT/n for n in names]
    rows=[('Previous A / G3',[OLD/'A_FOLD/G03/preview'/(v+'.png') for v in VIEWS])]
    rows += [(str(p.relative_to(ROOT)),[p/'preview'/(v+'.png') for v in VIEWS]) for p in finals]
    board(out/'selected_comparison.png',VIEWS,rows,600)
    results=[validate(p) for p in finals];dump(out/'core_validation.json',results)
    for p in finals:
        if not all((p.parent/g/'preview/front.png').exists() for g in ['G01','G02','G03']):
            board(out/(p.parent.name+'_views.png'),VIEWS,[(p.parent.name,[p/'preview'/(v+'.png') for v in VIEWS])],750)
            continue
        board(out/(p.parent.name+'_progression.png'),['G1 / original creases','G2 / front-back events','G3 / internal crease'],
              [(v,[p.parent/g/'preview'/(v+'.png') for g in ['G01','G02','G03']]) for v in VIEWS],440)
        board(out/(p.parent.name+'_views.png'),VIEWS,[(p.parent.name,[p/'preview'/(v+'.png') for v in VIEWS])],750)

def sections(names):
    canvas=Image.new('RGB',(2000,740),'#f7f6f0');d=ImageDraw.Draw(canvas);font=ImageFont.truetype(FONT,22)
    items=[('Previous A',OLD/'A_FOLD/G03','#a86c44')]+[(name,ROOT/name,color) for name,color in zip(names,['#147a78','#613b97','#2674b5'])]
    models=[(label,mesh(p),color) for label,p,color in items]
    for k,z in enumerate([2.3,4.5,6.,7.8]):
        x0=k*500+250;y0=355;scale=110
        d.text((k*500+20,20),f'Actual section z={z:.1f}',fill='#202a30',font=font)
        d.line((x0-205,y0,x0+205,y0),fill='#cccccc');d.line((x0,y0-205,x0,y0+205),fill='#cccccc')
        for label,m,color in models:
            segments=trimesh.intersections.mesh_plane(m,[0,0,1],[0,0,z])
            for seg in segments:
                points=[(x0+float(p[0])*scale,y0-float(p[1])*scale) for p in seg];d.line(points,fill=color,width=2)
    for k,(label,_,color) in enumerate(models):d.text((30+k*650,675),label,fill=color,font=font)
    canvas.save(ROOT/'review/actual_sections.png')

def main():
    p=argparse.ArgumentParser();p.add_argument('--catalogue',action='store_true');p.add_argument('--diagnostics',action='store_true');p.add_argument('--a-comparison',action='store_true');p.add_argument('--silhouettes',nargs='*');p.add_argument('--selected',nargs='*');args=p.parse_args()
    if args.catalogue:catalogue()
    if args.diagnostics:diagnostics()
    if args.a_comparison:a_comparison()
    if args.silhouettes:silhouette_comparison(args.silhouettes)
    if args.selected:selected(args.selected);sections(args.selected)
if __name__=='__main__':main()
