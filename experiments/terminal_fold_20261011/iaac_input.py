"""Lower resolution inputs for genuine repeated public-flow experiments.

These are new sampled inputs, not a decimation of the authoritative old mesh.
No pleats or legacy holds are forwarded to the following growth process.
"""
from pathlib import Path
import argparse,copy,importlib.util,json,sys
import numpy as np
import trimesh
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('terminal_design_recipe',HERE/'study.py')
design=importlib.util.module_from_spec(spec);spec.loader.exec_module(design)
old=design.smooth_deep
repair=old.repair
variation=repair.variation
ROOT=design.ROOT

def initial(chart):
    c=chart.copy();c[:,1:]=abs(c[:,1:]);theta=np.arctan2(c[:,2],c[:,1]);norm=np.linalg.norm(c[:,1:],axis=1)
    xyz=np.column_stack([.78*c[:,1],.78*c[:,2],10*c[:,0]])
    side=norm>.99;xyz[side,:2]=.78*np.column_stack([np.cos(theta[side]),np.sin(theta[side])])
    events=copy.deepcopy(repair.legacy.EVENTS)
    for gen,items in events.items():
        for e in items:
            for key in ('expansion','reexpansion','constriction','return_depth'):
                e[key]*=(1.65 if key in ('expansion','reexpansion') else 1.35 if key=='constriction' else 1.50) if gen==1 else 1.25
    memory=np.zeros(len(c));birth=None
    for gen in (1,2,3):
        xyz+=sum(old.smooth_event(c,e) for e in events[gen])*(1-memory)[:,None]
        if gen==1:birth=xyz.copy()
        for e in events[gen]:memory=np.maximum(memory,repair.line_memory(c,e)*(1-memory))
    # Match the prior deep front cup design, mirrored analytically. The
    # tags are used only in preparing this input and are discarded afterwards.
    old_events=repair.legacy.EVENTS;repair.legacy.EVENTS=events
    try:offset,protect=old.smooth_valley(c)
    finally:repair.legacy.EVENTS=old_events
    xyz=birth+offset+(xyz-birth)*(1-protect)[:,None]
    xyz+=design.terminal(c,continuous=True)+design.terminal(c,True,continuous=True)
    xyz[:,:2]*=np.where(chart[:,1:]<0,-1.,1.)
    xyz[abs(chart[:,1])<1e-12,0]=0.;xyz[abs(chart[:,2])<1e-12,1]=0.
    return xyz

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--quad',action='store_true');parser.add_argument('--matched-cylinder',action='store_true');args=parser.parse_args()
    for name,rings,sectors,folded in [('IAAC_INPUT',97,64,True),('IAAC_CYLINDER_INPUT',17,32,False)]:
        if args.matched_cylinder:
            if folded:continue
            name='IAAC_CYLINDER_MATCHED_INPUT';rings,sectors=97,64
        if args.quad:name=name.replace('INPUT','QUAD_INPUT')
        cfg=dict(rings=rings,sectors=sectors,radius=.78)
        m,ch=variation.carrier(cfg);q=m.faces
        # Symmetric face-centre fans avoid arbitrary diagonal bias. The
        # incoming analytic fold is sampled once; later splits use real mesh.
        chart=np.vstack([ch,ch[q].mean(1)])
        centre=np.arange(len(q))+len(ch)
        faces=np.stack([q,np.roll(q,-1,axis=1),np.broadcast_to(centre[:,None],q.shape)],axis=-1).reshape(-1,3)
        xyz=initial(chart) if folded else np.column_stack([.78*chart[:,1],.78*chart[:,2],10*chart[:,0]])
        control_xyz=initial(ch) if folded else m.xyz
        if args.quad:xyz=np.vstack([control_xyz,control_xyz[q].mean(1)])
        folder=ROOT/name/'G00';folder.mkdir(parents=True,exist_ok=True)
        if (folder/'geometry.npz').exists():raise FileExistsError(folder)
        mesh=trimesh.Trimesh(xyz,faces,process=False)
        assert mesh.is_watertight and np.isfinite(xyz).all()
        np.savez_compressed(folder/'geometry.npz',xyz=xyz,faces=faces)
        np.savez_compressed(folder/'checkpoint.npz',xyz=xyz,faces=faces,chart=chart)
        if args.quad:np.savez_compressed(folder/'control_quad.npz',xyz=control_xyz,faces=q,chart=ch)
        mesh.export(folder/'gate.ply')
        design.dump(folder/'generation.json',dict(candidate=name,stage='G00',operation='New analytic input sampling, symmetric quad centre fans',
            folded=folded,rings=rings,sectors=sectors,vertices=len(xyz),triangles=len(faces),
            minimum_triangle_area=float(mesh.area_faces.min()),minimum_area_threshold=1e-12,
            minimum_area_pass=bool(mesh.area_faces.min()>1e-12),
            quad_control=bool(args.quad),physical_surface='Quad face-centre triangle fans' if args.quad else 'Analytically sampled face-centre triangle fans',
            legacy_masks_forwarded=False,pleats=False,subdivision_passes_total=0,
            source='Existing smooth_deep section recipe plus released continuous terminals' if folded else 'Existing variation.carrier circular column',
            limitation='New lower-resolution sampled input; not exact preservation or decimation of old GEO01 surface',
            self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED'))
        print('INPUT',name,len(xyz),len(faces),mesh.area_faces.min(),flush=True)

if __name__=='__main__':main()
