"""Independent connected face-patch extrusion AFTER the saved fold stage."""
import json
import numpy as np
import fluted_generation as common
ROOT=common.ROOT/'independent_extrusion_results'
data=json.loads((ROOT/'g01/mesh.json').read_text());state=json.loads((ROOT/'g01/strip_state.json').read_text())
v=np.array(data['vertices']);faces=data['faces'];rings=np.array(state['rings']);n=rings.shape[1]
radius=np.linalg.norm(v[rings][:,:,:2],axis=2).mean(1)
z=v[rings][:,:,2].mean(1)
# Narrow, almost cylindrical bands are selected from the current geometry.
necks=[j for j in range(len(rings)-1) if max(radius[j:j+2])<.30*radius.max() and abs(radius[j+1]-radius[j])<.03 and z[j+1]-z[j]>.055]
neck_z=[float((z[j]+z[j+1])/2) for j in necks]
candidates=[j for j in range(len(rings)-1) if abs(radius[j+1]-radius[j])>.04]
groups=[]
for j in candidates:
    if not groups or j!=groups[-1][-1]+1 or np.sign(radius[j+1]-radius[j])!=np.sign(radius[j]-radius[j-1]):groups.append([j])
    else:groups[-1].append(j)
bands=[max(group,key=lambda j:abs(radius[j+1]-radius[j])*(radius[j]+radius[j+1])) for group in groups]
verts=v.tolist();removed=set();added=[];events=[]
for j in bands:
    for sector in range(8):
        possible=[(sector*(n//8)+k)%n for k in range(n//8)]
        # A broad actual face, avoiding nonconvex groove-spanning patch extrusion.
        indices=[max(possible,key=lambda i:np.linalg.norm(v[rings[j,(i+1)%n]]-v[rings[j,i]]))]
        selected=[j*n+i for i in indices];patch=[faces[f] for f in selected]
        keys=sorted(set(k for face in patch for k in face));points=v[keys];center=points.mean(0)
        radial=np.r_[center[:2],0.];radial/=np.linalg.norm(radial)
        # Neighbouring broad body determines axial direction, independently of folding.
        direction=-np.sign(radius[j+1]-radius[j])
        size=float(np.clip(np.mean(radius[j:j+2])*1.2,.45,1.05))
        # Base-adjacent growth needs a shallower straight direction to clear the foot.
        axial_ratio=.25 if center[2]<v[:,2].min()+.18*np.ptp(v[:,2]) else .5
        shift=radial*size+np.array([0,0,direction*size*axial_ratio])
        mapping={};stem={}
        for key,p in zip(keys,points):
            q=center+(p-center)*.6+shift;mapping[key]=len(verts);verts.append(q.tolist())
        boundary={}
        for face in patch:
            for a,b in zip(face,face[1:]+face[:1]):
                if (b,a) in boundary:del boundary[b,a]
                else:boundary[a,b]=True
        for face in patch:added.append([mapping[k] for k in face])
        for a,b in boundary:
            added.append([a,b,mapping[b],mapping[a]])
        removed.update(selected);events.append(dict(parent_faces=selected,shift=shift.tolist(),cap_scale=.6))
mesh=common.Mesh.from_vertices_and_faces(verts,[f for i,f in enumerate(faces) if i not in removed]+added)
common.OUT=common.ROOT/'large_straight_clear_results';common.OUT.mkdir(exist_ok=True)
common.save(mesh,2,dict(operation='independent connected patch extrusion after frozen fold output',selected_neck_bands=bands,extrusions=len(events),smoothing=False,events=events))
