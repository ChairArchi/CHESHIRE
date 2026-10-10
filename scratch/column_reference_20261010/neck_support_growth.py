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
bands=necks
verts=v.tolist();removed=set();added=[];events=[]
for j in bands:
    neck_center=(z[j]+z[j+1])/2
    window=[k for k in range(len(rings)-1) if abs((z[k]+z[k+1])/2-neck_center)<.04*np.ptp(z)]
    context=radius[abs(z-neck_center)<.10*np.ptp(z)]
    target_radius=float(np.max(context)*.82)
    for sector in range(8):
        indices=[(sector*(n//8)+k)%n for k in range(1,n//8-1)]
        selected=[k*n+i for k in window for i in indices];patch=[faces[f] for f in selected]
        keys=sorted(set(k for face in patch for k in face));points=v[keys];center=points.mean(0)
        radial=np.r_[center[:2],0.];radial/=np.linalg.norm(radial)
        # Neighbouring broad body determines axial direction, independently of folding.
        growth=max(target_radius-float(np.mean(radius[j:j+2])),.25)
        shift=radial*growth
        mapping={};stem={}
        for key,p in zip(keys,points):
            q=center+(p-center)*.96+shift*.22;stem[key]=len(verts);verts.append(q.tolist())
            q=center+(p-center)*.68+shift;mapping[key]=len(verts);verts.append(q.tolist())
        boundary={}
        for face in patch:
            for a,b in zip(face,face[1:]+face[:1]):
                if (b,a) in boundary:del boundary[b,a]
                else:boundary[a,b]=True
        for face in patch:added.append([mapping[k] for k in face])
        for a,b in boundary:
            added.append([a,b,stem[b],stem[a]])
            added.append([stem[a],stem[b],mapping[b],mapping[a]])
        removed.update(selected);events.append(dict(parent_faces=selected,shift=shift.tolist(),cap_scale=.68,neck_center=float(neck_center),context_target_radius=target_radius,neck_radius=float(radius[j]),support_bands=window))
allfaces=[f for i,f in enumerate(faces) if i not in removed]+added
used=sorted(set(k for face in allfaces for k in face));lookup={k:i for i,k in enumerate(used)}
mesh=common.Mesh.from_vertices_and_faces([verts[k] for k in used],[[lookup[k] for k in face] for face in allfaces])
common.OUT=common.ROOT/'neck_support_growth_results';common.OUT.mkdir(exist_ok=True)
common.save(mesh,2,dict(operation='independent connected patch extrusion after frozen fold output',selected_neck_bands=bands,extrusions=len(events),smoothing=False,events=events))
