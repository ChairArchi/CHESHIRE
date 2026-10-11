"""Three authored folded masses on the existing closed quad carrier.

Reuse smooth_deep's signed radial/axial PCHIP returns. Proportion, direction,
axial support and concave end closure are finite design settings, not a new
folding solver or a reconstruction of undisclosed IAAC input equations.
No coordinate smoothing, legacy holdout, separate shells or thin terminal disks.
"""
from pathlib import Path
import argparse, importlib.util, json, shutil, sys
import numpy as np
import trimesh
from scipy.interpolate import PchipInterpolator

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'terminal_fold_20261011'))
spec = importlib.util.spec_from_file_location('column_input_source', HERE.parent / 'terminal_fold_20261011/iaac_input.py')
source = importlib.util.module_from_spec(spec); spec.loader.exec_module(source)
old = source.old
variation = source.variation
from cheshire import task33_folds
ROOT = Path('E:/CHESHIRE_DATA/column_development_20261011')

def event(name, direction, height, span, expansion, constriction, reexpansion, depth, width, sweep):
    return dict(id=name, direction=direction, height=height, span=span,
                expansion=expansion, constriction=constriction, reexpansion=reexpansion,
                return_depth=depth, overlap_width=width, sweep=sweep, mirror=False)

RECIPES = {
    'SPAN': dict(radius=[.66,.92,.78,.63,.66,.73,.88,.64], valley=.43,
        events=[event('LOW_X',0,.22,.115,.95,.29,.62,.65,1.14,.24),
                event('HIGH_Y',np.pi/2,.70,.145,.82,.27,.90,.72,1.10,-.20),
                event('DIAGONAL_BRIDGE',.70,.47,.145,.49,.16,.51,.46,.94,.24)]),
    'WEAVE': dict(radius=[.72,.98,.82,.72,.74,.78,.94,.68], valley=.47,
        events=[event('LOW_X',0,.19,.10,1.00,.30,.64,.70,1.14,.23),
                event('MIDDLE_Y',np.pi/2,.43,.135,.76,.27,.60,.68,1.12,-.15),
                event('UPPER_DIAGONAL',.65,.64,.13,.64,.23,.68,.60,.90,.28),
                event('HIGH_X',0,.83,.095,.65,.24,.82,.66,1.10,-.24)]),
    'COUNTER': dict(radius=[.76,1.02,.86,.77,.72,.82,1.02,.72], valley=.50,
        events=[event('LOW_Y',np.pi/2,.24,.14,.92,.27,.82,.72,1.15,-.25),
                event('HIGH_X',0,.73,.15,.97,.30,.84,.78,1.18,.28),
                event('LONG_DIAGONAL',.80,.49,.18,.62,.18,.59,.57,.95,-.26)]),
}

def compact_profile(s, values):
    return np.nan_to_num(PchipInterpolator([0,.035,.08,.15,.24], values, extrapolate=False)(s))

def end_returns(c):
    """Deep bowl/saddle closure; cap centres remain part of the same solid."""
    s = c[:,0]; rho = np.linalg.norm(c[:,1:], axis=1)
    theta = np.arctan2(c[:,2], c[:,1])
    result = np.zeros((len(c),3))
    for top in (False, True):
        t = 1-s if top else s
        wave = .5 + .5 * np.cos(2*theta) * (-1 if top else 1)
        radial = compact_profile(t,[0,.16,.26,-.08,0]) * (.35+.65*wave)
        result[:,:2] += radial[:,None] * c[:,1:]
        axial = compact_profile(t,[.18,.33,-.28,.07,0]) * (.25+.75*wave)
        cap = t < 1e-10
        # Rim has different heights by direction; interior turns inward by .88.
        axial[cap] = axial[cap]*rho[cap]**2 + .88*(1-rho[cap]**2)
        result[:,2] += (-1 if top else 1)*axial
    return result

def evaluate(chart, recipe):
    c = chart.copy(); c[:,1:] = np.abs(c[:,1:])
    theta = np.arctan2(c[:,2], c[:,1]); rho = np.linalg.norm(c[:,1:],axis=1)
    radius = PchipInterpolator([0,.06,.14,.28,.50,.72,.90,1],recipe['radius'])(c[:,0])
    proportional = np.column_stack([radius*c[:,1],radius*c[:,2],10*c[:,0]])
    major = sum(old.smooth_event(c,e) for e in recipe['events'][:2])
    bridge = sum(old.smooth_event(c,e) for e in recipe['events'][2:])
    valley = np.zeros_like(proportional)
    for e in recipe['events'][:2]:
        # Existing deep-cup relation: a valley between two opposing wings.
        axis = np.pi/2 if e['direction'] < .1 else 0.
        d = np.abs(theta-axis); q=np.clip(d/.90,0,1); wave=(1-q*q)**2
        local_h=e['height']+.05*np.clip(abs(theta-e['direction'])/e['overlap_width'],0,1)**1.4
        axial=old.curve((c[:,0]-local_h)/e['span'],[0,.15,.65,1,1,.95,.65,.35,.12,0])
        axis_index=1 if axis>1 else 0
        valley[:,axis_index]-=recipe['valley']*wave*axial
    valley[rho<.99]=0
    terminal=end_returns(c)
    parts=dict(proportion=proportional,major_return=major,overrunning_return=bridge,
               deep_valley=valley,terminal_return=terminal)
    signs=np.where(chart[:,1:]<0,-1.,1.)
    for value in parts.values():
        value[:,:2]*=signs
        value[abs(chart[:,1])<1e-12,0]=0
        value[abs(chart[:,2])<1e-12,1]=0
    xyz=sum(parts.values())
    return xyz,parts

def legacy_core(chart, recipe, name):
    """Keep the proven deep-cup construction; change proportion and termini."""
    c=chart.copy();c[:,1:]=abs(c[:,1:])
    warped=c.copy()
    targets=[0,.18,.34,.51,.72,.86,1] if name=='SPAN' else [0,.12,.29,.49,.68,.86,1]
    warped[:,0]=PchipInterpolator([0,.15,.33,.50,.70,.85,1],targets)(c[:,0])
    previous=source.initial(warped)
    previous_end=source.design.terminal(warped,continuous=True)+source.design.terminal(warped,True,continuous=True)
    previous_cylinder=np.column_stack([.78*warped[:,1],.78*warped[:,2],10*warped[:,0]])
    proven_fold=previous-previous_end-previous_cylinder
    radius=PchipInterpolator([0,.06,.14,.28,.50,.72,.90,1],recipe['radius'])(c[:,0])
    proportional=np.column_stack([radius*c[:,1],radius*c[:,2],10*c[:,0]])
    rho=np.linalg.norm(c[:,1:],axis=1)
    cap=(c[:,0]<1e-10)|(c[:,0]>1-1e-10)
    # A sampled radial return, rather than a fan spanning one flat disk.
    folded_radius=PchipInterpolator([0,.25,.5,.75,1],[0,.27,.62,1.10,1])(rho[cap])
    proportional[cap,:2]*=np.divide(folded_radius,rho[cap],out=np.ones_like(folded_radius),where=rho[cap]>1e-12)[:,None]
    terminal=end_returns(c)
    theta=np.arctan2(c[cap,2],c[cap,1])
    wave=.5+.5*np.cos(2*theta)*np.where(c[cap,0]>.5,-1,1)
    depth=PchipInterpolator([0,.25,.5,.75,1],[.88,.86,.70,.30,.18])(rho[cap])
    terminal[cap,2]=np.where(c[cap,0]>.5,-1,1)*depth*(.75+.25*wave)
    bridge=.36*old.smooth_event(c,recipe['events'][-1])
    parts=dict(proportion=proportional,proven_deep_fold=proven_fold,overrunning_return=bridge,terminal_return=terminal)
    for value in parts.values():
        value[:,:2]*=np.where(chart[:,1:]<0,-1.,1.)
        value[abs(chart[:,1])<1e-12,0]=0;value[abs(chart[:,2])<1e-12,1]=0
    return sum(parts.values()),parts

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--names',nargs='+',choices=tuple(RECIPES),default=list(RECIPES))
    p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--refined-caps',action='store_true',help='Refine the coarse closed carrier twice before analytic folding, so caps have interior samples. New R1 folders.')
    p.add_argument('--legacy-core',action='store_true',help='Use proven deep cup construction in new R2 inputs, with redesigned cap return and axial proportion.')
    p.add_argument('--coarse-input',action='store_true',help='One carrier split instead of two, for a separate R2 control-density comparison.')
    args=p.parse_args()
    for name in args.names:
        if args.legacy_core and name=='COUNTER': continue
        label=name+'_COARSE' if args.coarse_input else name+'_R2' if args.legacy_core else name+'_R1' if args.refined_caps else name
        folder=args.root/'inputs'/label/'G00'
        if (folder/'geometry.npz').exists(): raise FileExistsError(folder)
        if args.refined_caps or args.legacy_core:
            mesh,chart=variation.carrier(dict(rings=25,sectors=16,radius=.78))
            for _ in range(1 if args.coarse_input else 2):
                mesh,state,_,_=task33_folds.refine(mesh,dict(carrier=mesh.xyz,chart=chart),carrier_smoothing=False,smooth_geometry=False)
                chart=state['chart']
            # Inherited chord coordinates are material directions, not a
            # polygonal physical radius. Only sidewall points are unitized.
            side=(chart[:,0]>1e-10)&(chart[:,0]<1-1e-10)
            chart[side,1:]/=np.linalg.norm(chart[side,1:],axis=1)[:,None]
        else:
            mesh,chart=variation.carrier(dict(rings=97,sectors=64,radius=.78))
        recipe=json.loads(json.dumps(RECIPES[name]))
        if args.refined_caps or args.legacy_core:
            recipe['radius'][0]*=1.10;recipe['radius'][-1]*=1.10
            recipe['events'][-1]['span']*=1.35
            recipe['events'][-1]['return_depth']*=1.12
        xyz,parts=(legacy_core(chart,recipe,name) if args.legacy_core else evaluate(chart,recipe)); q=mesh.faces
        physical_xyz=np.vstack([xyz,xyz[q].mean(1)])
        physical_chart=np.vstack([chart,chart[q].mean(1)])
        centre=np.arange(len(q))+len(xyz)
        tri=np.stack([q,np.roll(q,-1,axis=1),np.broadcast_to(centre[:,None],q.shape)],axis=-1).reshape(-1,3)
        physical=trimesh.Trimesh(physical_xyz,tri,process=False)
        if not np.isfinite(xyz).all() or not physical.is_watertight: raise ValueError('Invalid new mass')
        folder.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(folder/'geometry.npz',xyz=physical_xyz,faces=tri)
        np.savez_compressed(folder/'checkpoint.npz',xyz=physical_xyz,faces=tri,chart=physical_chart)
        np.savez_compressed(folder/'control_quad.npz',xyz=xyz,faces=q,chart=chart)
        np.savez_compressed(folder/'operation_fields.npz',**parts)
        physical.export(folder/'gate.ply');shutil.copy2(__file__,folder/'recipe.py')
        metadata=dict(candidate=label,stage='G00',operation='Authored proportion + overlapping signed PCHIP returns + deep concave saddle ends',
            recipe=recipe,vertices=len(physical_xyz),triangles=len(tri),control_vertices=len(xyz),control_quads=len(q),
            minimum_triangle_area=float(physical.area_faces.min()),minimum_area_threshold=1e-12,
            minimum_area_pass=bool(physical.area_faces.min()>1e-12),components=int(trimesh.graph.connected_component_labels(physical.face_adjacency).max()+1),
            watertight=physical.is_watertight,physical_fold_solver=False,separate_geometric_smoothing=False,CC_coordinate_averaging=False,
            legacy_masks_forwarded=False,pleats=False,endpoint_cylinder_lock=False,cap_return_depth=.88,
            input_carrier_bilinear_splits=(1 if args.coarse_input else 2) if args.refined_caps or args.legacy_core else 0,cap_interior_sampling=bool(args.refined_caps or args.legacy_core),
            proven_legacy_deep_cup_core=bool(args.legacy_core),initial_fold_memory_only=bool(args.legacy_core),
            self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED',
            source='Existing smooth_deep signed PCHIP radial/axial events and rounded angular cusp; new finite recipe values',
            iaac_scope='Initial geometry as separate design variable; our initial mass, not recovered IAAC equations')
        (folder/'generation.json').write_text(json.dumps(metadata,indent=2),encoding='utf8')
        print('INPUT',label,len(physical_xyz),len(tri),'area',physical.area_faces.min(),flush=True)

if __name__=='__main__': main()
