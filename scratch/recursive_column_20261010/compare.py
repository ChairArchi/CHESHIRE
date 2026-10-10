from pathlib import Path
import json,hashlib
import numpy as np,trimesh
ROOT=Path(__file__).resolve().parent/'runs/trial01'
levels=np.linspace(.03,7.97,160)
def silhouette(mesh,angle):
    direction=np.array([np.cos(angle),np.sin(angle)])
    out=[]
    for z in levels:
        seg=trimesh.intersections.mesh_plane(mesh,[0,0,1],[0,0,z]);pts=seg[:,:,:2].reshape((-1,2));s=pts@direction;out.append([s.min(),s.max()])
    return np.array(out)
def get(folder):return trimesh.load(folder/'column.obj',force='mesh',process=True)
seed=get(ROOT/'01_fluted_seed');metrics={}
for mode in ('recursive','seed_only'):
    previous=seed;before_hash=json.loads((ROOT/'01_fluted_seed/generation.json').read_text())['sha256'];rows=[]
    for g in range(1,5):
        folder=ROOT/mode/f'g{g:02d}';current=get(folder);report=json.loads((folder/'generation.json').read_text())
        assert report['parent_sha256']==before_hash
        assert report['sha256']==hashlib.sha256((folder/'state.json').read_bytes()).hexdigest()
        prev_state=json.loads((ROOT/'01_fluted_seed/state.json' if g==1 else ROOT/mode/f'g{g-1:02d}/state.json').read_text())
        previous_ids={f['id']:f for f in prev_state['faces']}
        for event in report['events']:
            assert event['parent'] in previous_ids
            if mode=='recursive':assert previous_ids[event['parent']]['born']==g-1
            else:assert previous_ids[event['parent']]['born']==0
        views={}
        for label,angle in [('front',0),('oblique',np.pi/6)]:
            a=silhouette(previous,angle);b=silhouette(current,angle);d=np.abs(b-a)
            views[label]=dict(max_boundary_change=float(d.max()),mean_boundary_change=float(d.mean()),changed_height_fraction=float(np.mean(d.max(1)>1e-5)),projected_area_change=float(np.trapezoid((b[:,1]-b[:,0])-(a[:,1]-a[:,0]),levels)))
        for ext in ('obj','ply'):
            m=trimesh.load(folder/('column.'+ext),force='mesh',process=True)
            assert m.is_watertight and m.is_winding_consistent and len(m.split())==1
        rows.append(dict(generation=g,selected_faces=report['selected_faces'],new_parent_faces=report['selected_from_previous_generation'],polygon_faces=report['faces'],volume=float(current.volume),volume_change=float(current.volume-previous.volume),views=views))
        previous=current;before_hash=report['sha256']
    metrics[mode]=rows
a=get(ROOT/'recursive/g04');b=get(ROOT/'seed_only/g04')
metrics['comparison']=dict(same_initial_state=True,same_selected_faces_per_generation=[8,16,16,24],same_final_polygon_faces=418,recursive_volume=float(a.volume),seed_only_volume=float(b.volume),front_final_max_boundary_difference=float(np.abs(silhouette(a,0)-silhouette(b,0)).max()),limitations=['proper crossing check omits coplanar overlaps','silhouettes sampled at 160 heights','seed-only ablation removes child-face targeting, not every possible neighboring influence'])
(ROOT/'comparison.json').write_text(json.dumps(metrics,indent=2));print(json.dumps(metrics,indent=2))
