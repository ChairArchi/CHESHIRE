"""Finite terminal release / meso return study on the actual GEO01 checkpoint.

Authored geometric return sections, not an origami or material solver. The
PCHIP section and rounded angular cusp reuse smooth_deep; terminal support
deliberately omits its old endpoint suppression. No XYZ smoothing or new
subdivision. The exact existing triangles and fold fans remain the substrate.
"""
from pathlib import Path
import argparse, json, shutil, sys
import numpy as np
import trimesh

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'curved_fold_side_20261011'))
import smooth_deep
OLD=Path('E:/CHESHIRE_DATA/curved_fold_side_20261011')
ROOT=Path('E:/CHESHIRE_DATA/terminal_fold_20261011')

def dump(path,obj):
    path.write_text(json.dumps(obj,indent=2),encoding='utf8')

def terminal(ch,top=False,continuous=False):
    """Opposing X wings at foot, Y wings at capital; cap interiors follow rim.

    PCHIP interpolates signed radial and axial return controls. No clamp to
    original cylinder, including the terminal rim. Interior cap points use
    radial material coordinates and a bowl depth, retaining closed topology.
    """
    s=1-ch[:,0] if top else ch[:,0]
    cx,cy=abs(ch[:,1]),abs(ch[:,2]);rho=np.hypot(cx,cy)
    theta=np.arctan2(cy,cx)
    d=np.pi/2-theta if top else theta
    q=np.clip(d/1.72,0,1)
    q=(np.sqrt(q*q+.12**2)-.12)/(np.sqrt(1+.12**2)-.12)
    wave=1-1.5*q+.5*q**3
    knots=[0,.018,.055,.105,.19]
    from scipy.interpolate import PchipInterpolator
    def p(values):return np.nan_to_num(PchipInterpolator(knots,values,extrapolate=False)(s))
    amp=1.10 if top else 1.
    radial_controls=[.42,.58,.35,-.12,0] if continuous else [.62,.72,-.13,.27,0]
    minor_controls=[.16,.19,.12,-.04,0] if continuous else [.17,.20,-.06,.10,0]
    axial_controls=[.34,.28,-.18,0,0] if continuous else [.24,.34,-.16,.05,0]
    radial=amp*(p(radial_controls)*wave + p(minor_controls)*(1-wave))
    axial=amp*p(axial_controls)*wave
    v=np.zeros((len(ch),3))
    v[:,0]=radial*np.divide(cx,rho,out=np.zeros_like(cx),where=rho>1e-12)*rho
    v[:,1]=radial*np.divide(cy,rho,out=np.zeros_like(cy),where=rho>1e-12)*rho
    # Concave end closure, continuous at the rim. This is still a closed solid
    # surface; it does not assert a thin developable sheet or useful thickness.
    cap=(rho<.999999)&(s<1e-8)
    axial[cap]=axial[cap]*rho[cap]**2+(.70 if continuous else .55)*(1-rho[cap]**2)
    v[:,2]=(-1 if top else 1)*axial
    return v

def source():
    g=np.load(OLD/'GEO01_FAN_MEMORY/G03/checkpoint.npz')
    old=np.load(OLD/'W06_SYMMETRIC_SMOOTH/G01/checkpoint.npz')
    _,_,tag=trimesh.remesh.subdivide(old['xyz'],old['faces'],vertex_attributes={
        'macro':old['memory'][:,None],'valley':old['valley_protection'][:,None]})
    assert len(g['xyz'])==len(tag['macro'])
    return g,tag

def save(name,gen,xyz,tri,ch,protection,fields,metadata):
    folder=ROOT/name/f'G{gen:02}';folder.mkdir(parents=True,exist_ok=True)
    if (folder/'geometry.npz').exists():raise FileExistsError(folder)
    m=trimesh.Trimesh(xyz,tri,process=False)
    assert np.isfinite(xyz).all() and m.is_watertight
    np.savez_compressed(folder/'geometry.npz',xyz=xyz,faces=tri)
    np.savez_compressed(folder/'checkpoint.npz',xyz=xyz,faces=tri,chart=ch,
                        memory=protection,valley_protection=fields['valley_protection'])
    np.savez_compressed(folder/'operation_fields.npz',**fields)
    m.export(folder/'gate.ply');shutil.copy2(__file__,folder/'recipe.py')
    dump(folder/'generation.json',dict(candidate=name,generation=gen,**metadata,
        vertices=len(xyz),triangles=len(tri),minimum_triangle_area=float(m.area_faces.min()),
        minimum_area_threshold=1e-12,minimum_area_pass=bool(m.area_faces.min()>1e-12),
        smoothing=False,new_subdivision=False,physical_fold_solver=False,
        self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED'))
    print(name,gen,'max delta',float(np.linalg.norm(fields['actual_displacement'],axis=1).max()),
          'min area',m.area_faces.min(),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--terminals-only',action='store_true');p.add_argument('--continuous',action='store_true');args=p.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True)
    g,t=source();x=g['xyz'];tri=g['faces'];ch=g['chart'];can=ch.copy();can[:,1:]=abs(can[:,1:])
    signs=np.where(ch[:,1:]<0,-1.,1.)
    # Both terminals are released, including old endpoint macro-memory tags.
    end=terminal(can)+terminal(can,True);end[:,:2]*=signs
    y=x+end
    protection=np.maximum(g['memory'],np.maximum(t['macro'][:,0],t['valley'][:,0]))
    protection[(ch[:,0]<.19)|(ch[:,0]>.81)]*=np.clip(1-np.maximum(
        (.19-ch[(ch[:,0]<.19)|(ch[:,0]>.81),0])/.19,
        (ch[(ch[:,0]<.19)|(ch[:,0]>.81),0]-.81)/.19),0,1)
    common=dict(actual_displacement=end,terminal_displacement=end,
                macro_protection=t['macro'][:,0],valley_protection=t['valley'][:,0],
                pleat_protection=g['memory'],meso_zone=np.zeros(len(x)))
    if args.continuous:
        end=terminal(can,continuous=True)+terminal(can,True,continuous=True);end[:,:2]*=signs
        e=dict(id='BROAD_DIAGONAL_RETURN',direction=np.pi/4,height=.635,span=.050,
               expansion=.28,constriction=.14,reexpansion=.23,return_depth=.25,
               overlap_width=.65,sweep=.10,mirror=False)
        move=smooth_deep.smooth_event(can,e)*(1-protection)[:,None];move[:,:2]*=signs
        fields=dict(common,actual_displacement=end+move,terminal_displacement=end,meso_displacement=move,
                    meso_zone=(np.linalg.norm(move,axis=1)>.001).astype(float))
        save('CONTINUOUS_RETURN',3,x+end+move,tri,ch,protection,fields,dict(source=str(OLD/'GEO01_FAN_MEMORY/G03'),
            operation='Terminal return-profile revision after actual render; broad lower-amplitude diagonal return',
            radial_controls=[.42,.58,.35,-.12,0],minor_radial_controls=[.16,.19,.12,-.04,0],
            axial_controls=[.34,.28,-.18,0,0],material_knots=[0,.018,.055,.105,.19],cap_bowl_depth=.70,
            reason='Initial terminal trial read as detached plates; delay constriction and remove repeated flares',events=[e],
            original_endpoint_cylinder_constraint=False))
        return
    if not (ROOT/'FREE_TERMINALS/G01/geometry.npz').exists():
        save('FREE_TERMINALS',1,y,tri,ch,protection,common,dict(source=str(OLD/'GEO01_FAN_MEMORY/G03'),
            operation='Signed radial/axial terminal return profiles; bottom X pair, top Y pair; concave closed caps',
            original_endpoint_cylinder_constraint=False,old_interior_geometry_unchanged_between_s=[.19,.81]))
    if args.terminals_only:return
    alternatives=[('AXIAL_LINK',[
        dict(id='FOOT_LINK',direction=0.,height=.17,span=.050,expansion=.34,constriction=.16,reexpansion=.24,return_depth=.28,overlap_width=1.05,sweep=.12,mirror=False),
        dict(id='CAPITAL_LINK',direction=np.pi/2,height=.87,span=.042,expansion=.35,constriction=.15,reexpansion=.25,return_depth=.29,overlap_width=1.05,sweep=-.10,mirror=False)]),
        ('DIAGONAL_RETURN',[
        dict(id='DIAGONAL_SHOULDER',direction=np.pi/4,height=.635,span=.048,expansion=.46,constriction=.23,reexpansion=.36,return_depth=.39,overlap_width=.53,sweep=.12,mirror=False)])]
    for name,events in alternatives:
        move=sum(smooth_deep.smooth_event(can,e) for e in events)
        # Existing fan cores and deep valley cores are held. Diagonal and
        # terminal-adjacent free material can respond between those cores.
        move*=(1-protection)[:,None];move[:,:2]*=signs
        fields=dict(common,actual_displacement=end+move,meso_displacement=move,
                    meso_zone=(np.linalg.norm(move,axis=1)>.001).astype(float))
        save(name,2,y+move,tri,ch,protection,fields,dict(source='FREE_TERMINALS/G01',
            operation='Existing rounded expansion/constriction/return sections on selected material bands',events=events,
            changed_vertices_over_01=int((np.linalg.norm(move,axis=1)>.01).sum()),
            protected_core_max_movement=float(np.linalg.norm(move[protection>=1-1e-12],axis=1).max())))

if __name__=='__main__':main()
