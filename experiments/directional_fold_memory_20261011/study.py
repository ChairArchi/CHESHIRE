"""Two finite sculpture studies; no origami solver or generic growth engine.

A: authored direction/height events on the existing closed column topology.
B: existing finite Mandelbulb signal, normal displacement in selected shoulders.
Legacy tags are authored feature bands, not automatically detected creases.
Old vertices survive existing bilinear refinement; inherited tags attenuate NEW
displacement. No CC coordinates or separate smoothing are used in this study.
"""
from pathlib import Path
import argparse, json, shutil, sys
import numpy as np

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'iaac_mandelbrot_20261011'
sys.path.insert(0, str(OLD))
import study as base
import column_study as column
import variation_study as variation
from cheshire import task33_folds as folds
from cheshire.reference_subdivision import topology, fields, unit, ArrayMesh

DEFAULT_ROOT = 'E:/CHESHIRE_DATA/directional_fold_memory_20261011'
# Heights are material s, axial return and radial amplitudes are physical units.
# Each event has separate direction, height, spread, expansion, constriction,
# re-expansion, return, overlap and direction sweep. Not identical stacked nodes.
EVENTS = {
    1: [dict(id='LOW_X', direction=0., height=.255, span=.090,
             expansion=.70, constriction=.28, reexpansion=.38, return_depth=.48,
             overlap_width=1.00, sweep=.25, mirror=True),
        dict(id='HIGH_X', direction=0., height=.755, span=.070,
             expansion=.49, constriction=.24, reexpansion=.64, return_depth=.42,
             overlap_width=.88, sweep=-.32, mirror=True)],
    2: [dict(id='FRONT_LINK', direction=np.pi/2, height=.455, span=.115,
             expansion=.60, constriction=.24, reexpansion=.40, return_depth=.55,
             overlap_width=1.03, sweep=0., mirror=False),
        dict(id='BACK_RETURN', direction=-np.pi/2, height=.600, span=.090,
             expansion=.44, constriction=.20, reexpansion=.58, return_depth=.46,
             overlap_width=.92, sweep=0., mirror=False)],
    3: [dict(id='DIAGONAL_SHOULDER', direction=.68, height=.655, span=.105,
             expansion=.31, constriction=.13, reexpansion=.40, return_depth=.31,
             overlap_width=.67, sweep=.20, mirror=True)],
}
PRESERVATION = 1.0

def window(x, inner, outer):
    """Compact scalar band with exact plateau, no filtering of geometry."""
    t = np.clip((np.abs(x)-inner)/(outer-inner), 0, 1)
    return 1-t*t*(3-2*t)

def angle_distance(theta, centre):
    return np.arctan2(np.sin(theta-centre), np.cos(theta-centre))

def event_values(chart, event):
    s = chart[:, 0]; theta = np.arctan2(chart[:, 2], chart[:, 1])
    h = event['height']; span = event['span']; width = event['overlap_width']
    # Actual deformed direction is distinct from the material scalar profiles.
    centre = event['direction'] + event['sweep']*np.sin(np.pi*(s-h)/(.32))
    centres = [centre, np.pi-centre] if event['mirror'] else [centre]
    wave = np.zeros(len(chart)); tag = np.zeros(len(chart))
    for c in centres:
        d = angle_distance(theta, c)
        main = window(d, .12, width)
        # Flanking negative shoulders make a ridge/valley relation, not just a bulb.
        side = window(np.abs(d)-.87*width, .035, .22*width)
        wave += main-.24*side
        ridge = window(d, .09, .23)
        valley = window(np.abs(d)-.87*width, .025, .13)
        axial = window(s-h, span*1.25, span*1.95)
        tag = np.maximum(tag, np.maximum(ridge, valley)*axial)
    u = (s-h)/span
    radial = (event['expansion']*np.exp(-((u+.80)/.86)**2)
              -event['constriction']*np.exp(-(u/.33)**2)
              +event['reexpansion']*np.exp(-((u-.78)/.75)**2))
    # Paired axial lobes turn back through the binding; independently adjustable.
    axial_return = event['return_depth']*(np.exp(-((u+.38)/.54)**2)
                                         -np.exp(-((u-.38)/.54)**2))
    radial_direction = np.column_stack([np.cos(theta),np.sin(theta),np.zeros(len(s))])
    move = radial_direction*(radial*wave)[:,None]
    move[:,2] = axial_return*wave
    ends = window(s-.5, .40, .49)
    cap = np.linalg.norm(chart[:,1:],axis=1)<1e-10
    move *= ends[:,None]; move[cap]=0; tag[cap]=0
    return move, tag, radial, axial_return

def folded_event_values(chart, event):
    """Finite bent section panels; not a crease-constraint or inextensible solver.

    This deliberately replaces the two Gaussian bulges used in the rejected
    first trials. Polygonal section turns form a lip and recessed return, and
    the crease height changes across each directional panel. No global caps or
    independently stacked shells are introduced.
    """
    s=chart[:,0];theta=np.arctan2(chart[:,2],chart[:,1]);h=event['height']
    width=event['overlap_width'];span=event['span']
    centre=event['direction']+event['sweep']*np.sin(np.pi*(s-h)/.32)
    centres=[centre,np.pi-centre] if event['mirror'] else [centre]
    move=np.zeros((len(chart),3));tag=np.zeros(len(chart))
    knots=np.array([-2.2,-1.4,-.75,-.35,-.15,.15,.35,.75,1.3,2.])
    e=event['expansion'];c=event['constriction'];r=event['reexpansion']
    radial_values=[0,.10*e,.62*e,e,.30*e,-c,-.35*c,r,.4*r,0]
    return_values=event['return_depth']*np.array([0,0,.20,1,.60,-.60,-1,-.20,0,0])
    for centre in centres:
        d=angle_distance(theta,centre)
        triangular=np.maximum(0,1-np.abs(d)/width)
        flank=window(np.abs(d)-.90*width,.02,.15*width)
        wave=triangular-.15*flank
        # A single fold edge rises sideways, instead of closing as a horizontal
        # circumferential ring. Adjacent directions have different heights.
        local_h=h+.050*np.clip(np.abs(d)/width,0,1)**1.4
        u=(s-local_h)/span
        radial=np.interp(u,knots,radial_values,left=0,right=0)*wave
        zreturn=np.interp(u,knots,return_values,left=0,right=0)*wave
        move[:,0]+=np.cos(theta)*radial;move[:,1]+=np.sin(theta)*radial
        move[:,2]+=zreturn
        axial=window(s-local_h,span*1.25,span*1.95)
        ridge=window(d,.075,.19)
        valley=window(np.abs(d)-.90*width,.02,.11)
        # Include the curved axial lip itself, across the selected direction.
        lip=window(u+.35,.035,.16)*window(d,width*.52,width*.88)
        tag=np.maximum(tag,np.maximum(np.maximum(ridge,valley)*axial,lip))
    cap=np.linalg.norm(chart[:,1:],axis=1)<1e-10
    move*=window(s-.5,.40,.49)[:,None];move[cap]=0;tag[cap]=0
    return move,tag

def refine(mesh, chart, memory):
    t = topology(mesh)
    out, state, _, _ = folds.refine(mesh, dict(carrier=mesh.rest,chart=chart),
                                   carrier_smoothing=False,smooth_geometry=False)
    inherited = base.interpolate_chart(memory,t,len(mesh.faces)) if memory.shape[1] else np.zeros((len(out.xyz),0))
    assert np.array_equal(out.xyz[:len(mesh.xyz)],mesh.xyz)
    return out, state['chart'], inherited

def load_state(root, candidate, stage):
    folder=root.resolve(candidate+'/'+stage); mesh,chart=base.load(folder)
    a=np.load(folder/'memory.npz')
    info=json.loads((folder/'memory.json').read_text(encoding='utf8'))
    return mesh,chart,a['weights'],info['names'],info['landmarks']

def save(root,candidate,stage,mesh,chart,memory,names,landmarks,record,meta):
    # Existing save routine checks finite coordinates, area, and closed topology.
    base.save(root,candidate,stage,mesh,chart,record,dict(meta,
        legacy_preservation_weight=PRESERVATION,
        tag_source='Authored ridge/valley bands; not automatic crease detection',
        solver='Coordinate sculpture, not physical origami',
        refinement='Existing Task33 bilinear; no CC coordinate averaging',
        separate_geometric_smoothing=False, CC_coordinate_averaging=False),
        mirror_callback=column.reflect)
    folder=root.resolve(candidate+'/'+stage)
    np.savez_compressed(folder/'memory.npz',weights=memory)
    base.dump(folder/'memory.json',dict(names=names,landmarks=landmarks))
    shutil.copy2(__file__,folder/'memory_recipe.py')

def apply_with_memory(mesh, chart, memory, proposed):
    incoming=mesh.xyz.copy()
    legacy=memory.max(1) if memory.shape[1] else np.zeros(len(chart))
    factor=1-PRESERVATION*legacy
    factor[legacy>=1-1e-12]=0
    mesh.xyz=incoming+proposed*factor[:,None]
    column.reflect(mesh,chart)
    delta=np.linalg.norm(mesh.xyz-incoming,axis=1)
    core=legacy>=1-1e-12
    metrics=dict(protected_core_vertices=int(core.sum()),
        core_max_actual_movement=float(delta[core].max()) if core.any() else None,
        core_max_unprotected_proposal=float(np.linalg.norm(proposed[core],axis=1).max()) if core.any() else None,
        changed_vertex_fraction=float((delta>1e-9).mean()),
        weighted_displacement_max=float(delta.max()),
        vertex_rms_displacement=float(np.sqrt((delta**2).mean())),
        memory_scope='Position retention of authored core vertices, not a proof of preserved dihedral angle or panel developability')
    return dict(legacy_weight=legacy,proposal=proposed,applied_displacement=mesh.xyz-incoming,
                memory_factor=factor),metrics

def landmark_record(mesh,landmarks):
    result={}
    for name,feature in landmarks.items():
        ids=np.array(feature['ids'],dtype=int);birth=np.array(feature['birth_positions'])
        delta=np.linalg.norm(mesh.xyz[ids]-birth,axis=1)
        result[name]=dict(vertices=len(ids),max_movement_from_birth=float(delta.max()),
                          rms_movement_from_birth=float(np.sqrt((delta**2).mean())))
    return result

def run_a(root, name='A_FOLD'):
    cfg=variation.recipe('MEMORY_COMMON',rings=25,sectors=32,radius=.78)
    mesh,chart=variation.carrier(cfg)
    memory=np.zeros((len(mesh.xyz),0));names=[];landmarks={}
    save(root,name,'G00',mesh,chart,memory,names,landmarks,{},
         dict(operation='Unchanged existing 25x32 closed cylinder',recipe=cfg))
    history=[]
    for generation in (1,2,3):
        refinement_passes=(2 if generation==1 else 1 if generation==2 else 0)
        for _ in range(refinement_passes):mesh,chart,memory=refine(mesh,chart,memory)
        moves=[];tags=[]
        for event in EVENTS[generation]:
            move,tag=folded_event_values(chart,event); moves.append(move);tags.append(tag)
        record,metrics=apply_with_memory(mesh,chart,memory,np.sum(moves,axis=0))
        # Tags attach to the actually formed surface, and follow future refinement.
        # Some masked event bands were unable to develop fully; retain this fact.
        for event,tag in zip(EVENTS[generation],tags):
            tag=tag*record['memory_factor']
            ids=np.flatnonzero(tag>=1-1e-12)
            names.append(event['id']);memory=np.column_stack([memory,tag])
            if len(ids):landmarks[event['id']]=dict(ids=ids.tolist(),birth_positions=mesh.xyz[ids].tolist())
        stage=f'G{generation:02}'
        metrics['landmarks']=landmark_record(mesh,landmarks)
        meta=dict(operation='Selected direction + bent panel section + curved-height lip and recessed axial return',
                  events=EVENTS[generation],design_generation=generation,
                  refinement_passes=refinement_passes,parent=name+'/G%02d'%(generation-1),**metrics)
        save(root,name,stage,mesh,chart,memory,names,landmarks,record,meta)
        history.append(dict(stage=stage,**metrics))
    base.dump(root.resolve(name+'/history.json'),history)

def run_b(root,source):
    candidate,stage=source.split('/')
    mesh,chart,memory,names,landmarks=load_state(root,candidate,stage)
    # A already has 193x256 material sampling. Retain its exact topology for B:
    # unnecessary re-tessellation of nonplanar quad-centre fans can change the
    # physical surface even when the old control points stay fixed.
    s=chart[:,0];theta=np.arctan2(chart[:,2],chart[:,1]);incoming=mesh.xyz.copy()
    # The bands follow known legacy fold shoulders, not the whole circumference.
    zone1=window(s-.455,.065,.155)*window(np.abs(angle_distance(theta,np.pi/2))-.57,.12,.32)
    c=.68+.20*np.sin(np.pi*(s-.655)/.32)
    d=np.minimum(np.abs(angle_distance(theta,c)),np.abs(angle_distance(theta,np.pi-c)))
    zone2=window(s-.655,.055,.13)*window(d-.38,.10,.24)
    zone=np.maximum(zone1,zone2)
    zone[np.linalg.norm(chart[:,1:],axis=1)<1e-10]=0
    # Finite, explainable Mandelbulb signal already used in the preceding study.
    # Domain is continuous over the body; no random noise or repeated modules.
    p=incoming.copy();p[:,0]=np.abs(p[:,0])
    domain=np.column_stack([(p[:,0]-.72)*2.1,(p[:,1]-.58)*1.9,(p[:,2]-5.6)*.85])
    signal,escape_count,inside=base.escape_field(domain,power=5,iterations=18,bailout=4.)
    normals=fields(mesh)['nv']
    proposed=normals*(.115*signal*zone)[:,None]
    record,metrics=apply_with_memory(mesh,chart,memory,proposed)
    record.update(detail_zone=zone,finite_inside=inside,escape_count=escape_count,
                  fractal_signal=signal)
    metrics['landmarks']=landmark_record(mesh,landmarks)
    save(root,'B_LOCAL','G01',mesh,chart,memory,names,landmarks,record,
         dict(operation='Existing finite Mandelbulb signed scalar -> local normal displacement',
              source=source,amplitude=.115,power=5,iterations=18,
              detail_regions='Front linking fold shoulders and front diagonal upper shoulders only',
              active_zone_fraction=float((zone>0).mean()),
              field_semantics='Finite escape signal, not a distance or physical fold',**metrics))

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default=DEFAULT_ROOT)
    p.add_argument('--phase',choices=['A','B'],required=True);p.add_argument('--source',default='A_FOLD/G03')
    args=p.parse_args();root=base.ArtifactRoot(Path(args.root));root.path.mkdir(parents=True,exist_ok=True)
    if args.phase=='A':
        base.dump(root.resolve('parameters.json'),dict(A=EVENTS,B=dict(amplitude=.115,power=5,iterations=18),
            legacy_preservation_weight=PRESERVATION,originals_preserved=True,
            source_branch='experiment/iaac-mandelbrot-growth-20261011',source_commit='c373e32f10636d73fd54e261911140b4dfdb67bc',
            A_refinement_passes=[2,1,0],
            first_trial='A: coarser sampling [1,1,0] retained; angular shoulder faceting limits visual judgement',
            second_trial='A_REFINED: Gaussian events with denser sampling; puffed reading remains',
            final_A='A_FOLD: finite piecewise bent sections, direction-dependent curved lip heights; no smoothing'))
        run_a(root)
    else:run_b(root,args.source)

if __name__=='__main__':main()
