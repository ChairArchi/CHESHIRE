"""Diagnose the marked striations, then author local converging valley pleats.

Finite geometry experiment, not elastic buckling. The original W01 formula
has no high-frequency periodic pleat term. A new explicit alternating signed
section is evaluated in material coordinates, with axial taper and fan width.
"""
from pathlib import Path
import copy,shutil,sys
import numpy as np
import trimesh
from scipy.signal import find_peaks
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import a_repair as repair, smooth_deep
base=repair.base;legacy=repair.legacy

def continuous(chart):
    ch=chart.copy();ch[:,1:]=abs(ch[:,1:]);theta=np.arctan2(ch[:,2],ch[:,1])
    xyz=np.column_stack([.78*np.cos(theta),.78*np.sin(theta),10*ch[:,0]])
    caps=np.linalg.norm(ch[:,1:],axis=1)<.99;xyz[caps,:2]=.78*ch[caps,1:]
    original=legacy.EVENTS;events=copy.deepcopy(original)
    for gen,items in events.items():
        for item in items:
            for key in ('expansion','reexpansion','constriction','return_depth'):
                item[key]*=(1.65 if key in ('expansion','reexpansion') else 1.35 if key=='constriction' else 1.50) if gen==1 else 1.25
    legacy.EVENTS=events
    try:
        memory=np.zeros(len(ch));birth=None
        for gen in (1,2,3):
            xyz+=sum(smooth_deep.smooth_event(ch,e) for e in events[gen])*(1-memory)[:,None]
            for e in events[gen]:memory=np.maximum(memory,repair.line_memory(ch,e)*(1-memory))
            if birth is None:birth=xyz.copy()
        offset,protection=smooth_deep.smooth_valley(ch)
        xyz=birth+offset+(xyz-birth)*(1-protection)[:,None]
    finally:legacy.EVENTS=original
    xyz[:,0]*=np.where(chart[:,1]<0,-1,1);xyz[:,1]*=np.where(chart[:,2]<0,-1,1)
    return xyz

def diagnose(root):
    g=np.load(root/'W06_SYMMETRIC_SMOOTH/G01/checkpoint.npz');ch=g['chart'];tri=g['faces'];xyz=g['xyz']
    exact=continuous(ch);difference=np.linalg.norm(exact-xyz,axis=1)
    assert difference.max()<1e-10, difference.max()
    cm=trimesh.Trimesh(ch,tri,process=False);rows=[];series=[]
    for s in [.38,.40,.42,.44,.46,.48]:
        segments,ids=trimesh.intersections.mesh_plane(cm,[1,0,0],[s,0,0],return_faces=True)
        bc=trimesh.triangles.points_to_barycentric(np.repeat(ch[tri[ids]],2,axis=0),segments.reshape(-1,3))
        pos=(bc[:,:,None]*np.repeat(xyz[tri[ids]],2,axis=0)).sum(1)
        points=segments.reshape(-1,3);angle=np.arctan2(points[:,2],points[:,1])-np.pi/2
        choose=(abs(angle)<.6);angle=angle[choose];pos=pos[choose]
        order=np.argsort(angle);angle=angle[order];pos=pos[order]
        a=np.linspace(-.59,.59,1601);target=np.column_stack([np.full(len(a),s),np.cos(a+np.pi/2),np.sin(a+np.pi/2)])
        analytic=continuous(target);sample=np.interp(a,angle,pos[:,1]);error=sample-analytic[:,1]
        peaks,_=find_peaks(error,prominence=.0005);valleys,_=find_peaks(-error,prominence=.0005)
        rows.append(dict(material_height=s,maximum_Y_tessellation_error=float(abs(error).max()),
                         alternating_error_peaks=len(peaks),alternating_error_valleys=len(valleys)))
        series.append((s,a,sample,analytic[:,1],error))
    base.dump(root/'review/marked_striation_diagnosis.json',dict(
        exact_formula_at_stored_vertices_max_error=float(difference.max()),sections=rows,
        finding='No periodic pleat term in W01 continuous formula. Finite triangular interpolation deviates between samples; rendered striations are not proof of resolved crease geometry.',
        scope='Material-height sections, not constant physical-Z cuts. Measures interpolation, not a physical instability or every cause of the rendered pattern.'))
    from PIL import Image,ImageDraw,ImageFont
    im=Image.new('RGB',(1100,950),'#f6f5ef');d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
    d.text((25,15),'Marked valley: actual mesh minus authored continuous surface (Y error, x1000)',fill='#203039',font=font)
    for k,(s,a,sample,y,error) in enumerate(series):
        by=110+k*138;d.text((20,by-50),f'material s={s:.2f}',fill='#203039',font=font)
        d.line((240,by,1050,by),fill='#bbb9b0')
        points=list(zip(240+(a+.59)/1.18*810,by-error*2000))
        d.line(points,fill='#b45b34',width=2)
        d.text((20,by-20),f'max |error|={max(abs(error)):.5f}',fill='#203039',font=font)
    im.save(root/'review/marked_striation_diagnosis.png')

def pleat_field(chart):
    s=chart[:,0];theta=np.arctan2(chart[:,2],chart[:,1]);front=np.where(chart[:,2]<0,-1,1)
    d=np.arctan2(np.sin(theta-front*np.pi/2),np.cos(theta-front*np.pi/2))
    # A finite fan: narrower toward the lower constriction, opens toward the lip.
    width=.42+.16*np.clip((s-.34)/.16,0,1)
    q=d/width;envelope=legacy.window(q,.72,1.)*legacy.window(s-.43,.045,.105)
    envelope[np.linalg.norm(chart[:,1:],axis=1)<.99]=0
    # Even phase gives identical X mirror; front/back vector changes sign.
    phase=np.pi*10*q
    folded=2/np.pi*np.arcsin(.92*np.cos(phase))/ (2/np.pi*np.arcsin(.92))
    move=np.zeros((len(chart),3));move[:,1]=front*envelope*folded
    return move,envelope

def generate(root):
    # Interpolating one existing triangle refinement increases angular sampling.
    # Existing vertices are unchanged. No smoothing or coordinate averaging of old V.
    source=root/'W06_SYMMETRIC_SMOOTH/G01';g=np.load(source/'checkpoint.npz')
    xyz,tri=g['xyz'],g['faces'];chart=g['chart']
    xyz,tri,attributes=trimesh.remesh.subdivide(xyz,tri,vertex_attributes={'chart':chart})
    chart=attributes['chart']
    assert np.array_equal(xyz[:len(g['xyz'])],g['xyz'])
    unit,envelope=pleat_field(chart)
    for name,amplitude in [('W03_PLEAT_CONTROL',0.),('W04_VALLEY_PLEATS',.045),('W05_STRONG_PLEATS',.085)]:
        out=xyz+amplitude*unit;folder=root/name/'G01';folder.mkdir(parents=True,exist_ok=True);assert not list(folder.iterdir())
        m=trimesh.Trimesh(out,tri,process=False);assert np.isfinite(out).all() and m.is_watertight
        np.savez_compressed(folder/'geometry.npz',xyz=out,faces=tri)
        np.savez_compressed(folder/'checkpoint.npz',xyz=out,faces=tri,chart=chart)
        np.savez_compressed(folder/'operation_fields.npz',pleat_envelope=envelope,displacement=amplitude*unit)
        m.export(folder/'gate.ply');shutil.copy2(__file__,folder/'valley_pleats_recipe.py')
        base.dump(folder/'generation.json',dict(candidate=name,stage='G01',source='W06_SYMMETRIC_SMOOTH/G01',
            operation='Surface-exact triangle midpoint refinement, then authored converging alternating valley section',
            added_pleat_amplitude=amplitude,cycles_across_full_fan=10,axial_centre=.43,axial_half_support=.105,
            refinement_preserves_old_vertices_and_piecewise_planar_surface=True,
            radial_depth_unchanged_before_pleats=True,physical_vertices=len(out),physical_triangles=len(tri),
            minimum_triangle_area=float(m.area_faces.min()),minimum_area_threshold=1e-12,
            minimum_area_pass=bool(m.area_faces.min()>1e-12),
            self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED',
            separate_geometric_smoothing=False,CC_coordinate_averaging=False,physical_buckling_solver=False))
        print('GENERATED',name,len(out),len(tri), 'area',m.area_faces.min(),flush=True)

if __name__=='__main__':
    root=Path(repair.ROOT);diagnose(root);generate(root)
