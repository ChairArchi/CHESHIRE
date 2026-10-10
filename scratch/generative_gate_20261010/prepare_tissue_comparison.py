"""Choose a magnified camera from actual selected faces, never modify meshes."""
from pathlib import Path
import json
import numpy as np
from gateflow.input import load

ROOT=Path(__file__).resolve().parent
g=load(ROOT/'inputs/neutral')
before=np.load(ROOT/'runs/hierarchy_microfold23/19_crease_subdivide/state.npz')
op=np.load(ROOT/'runs/micro_simple_tissue23/20_tessellate/operator_state.npz')
xyz=before['xyz'];faces=before['faces'];selected=op['selected_target_faces'].astype(bool)
centroids=xyz[faces[selected]].mean(1)
eligible=centroids[(centroids[:,0]>0)&(centroids[:,1]>0)&(centroids[:,2]>.5)]
# Select a real mapped face near the support/lintel transition, on the front.
goal=np.array([.21,.1,.72])
chosen=eligible[np.argmin(np.linalg.norm(eligible-goal,axis=1))]
lo=xyz.min(0);hi=xyz.max(0);center=(lo+hi)/2;span=max(hi-lo)
# Export transform is documented by gateflow.input, inspect the actual instance.
world_center=center*g.scale+g.origin
focus=dict(center=world_center.tolist(),span=float(span*g.scale),target=((chosen-center)/span).tolist(),ortho_scale=.16,
           source='Selected front target face near support/lintel; common camera for before/after',
           projected_cell_edge_quantiles=np.quantile(np.linalg.norm(xyz[faces[selected,1]]-xyz[faces[selected,0]],axis=1),[.1,.5,.9]).tolist())
(ROOT/'tissue_focus.json').write_text(json.dumps(focus,indent=2))
print(json.dumps(focus,indent=2))
