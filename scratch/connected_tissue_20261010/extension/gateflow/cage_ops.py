"""Low-polygon parent/child study inferred from the supplied image sequence."""
import numpy as np
from compas.datastructures import Mesh
from cheshire.mola import extrude_tapered_once
from cheshire.execution import ExecutionBudget
from .engine import op,ArrayMesh,mean_incident,runtime
from .symmetry import symmetric_displacement

@op('cage_ribs')
def cage_ribs(m,obs,spec,attenuation,budget):
    move=np.zeros_like(m.xyz)
    for role in (0,1):
        weight=mean_incident(np.repeat((obs['structural_roles']==role).astype(float),obs['t']['n']),obs['t']['a'],len(m.xyz))
        ids=np.flatnonzero(weight>0)
        lo=m.xyz[ids].min(0);hi=m.xyz[ids].max(0);center=(lo+hi)*.5
        h=np.clip((m.xyz[:,2]-lo[2])/max(hi[2]-lo[2],1e-9),0,1)
        radial=m.xyz[:,:2]-center[:2];theta=np.arctan2(radial[:,1],radial[:,0])
        ridge=np.maximum(1-4*np.abs(np.mod(spec.get('ribs',4)*theta/(2*np.pi)+.125,1)-.5),0)
        if 'knots' in spec:
            shifted=np.clip(h+spec.get('stagger',.12)*np.sin(3*theta),0,1)
            scale=np.interp(shifted,spec['knots'],spec['scales'])
            # Keep a visible longitudinal rib while the neighboring panel changes.
            scale=1+(scale-1)*(1-spec.get('spine_retention',.6)*ridge)
        else:scale=spec.get('core_scale',.65)+spec.get('rib_height',.6)*ridge
        fade=weight*np.clip(h/.045,0,1)*np.clip((1-h)/.045,0,1)
        move[:,:2]+=radial*((scale-1)*fade*attenuation)[:,None]
    move=symmetric_displacement(m,move)
    return ArrayMesh(m.xyz+move,m.faces.copy(),m.classes.copy(),m.rest.copy(),m.anchors.copy(),m.generation+1),dict(operator='Low-poly longitudinal ribs / staggered local section changes; no subdivision'),dict(displacement=move)

@op('cage_children')
def cage_children(m,obs,spec,attenuation,budget):
    triangles=[];parents=[]
    # Planar triangles permit real MOLA extrusion without flattening warped quads.
    for parent,q in enumerate(m.faces):
        q=q[q>=0]
        for k in range(1,len(q)-1):triangles.append([int(q[0]),int(q[k]),int(q[k+1])]);parents.append(parent)
    parents=np.asarray(parents);tri=np.asarray(triangles);p=m.xyz[tri]
    normals=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);area=np.linalg.norm(normals,axis=1)*.5
    normals/=np.maximum(2*area[:,None],1e-12);centers=p.mean(1)
    allowed=np.isin(obs['structural_roles'][parents],spec.get('roles',[0,1]))
    if spec.get('frontier_only',False):allowed &= obs['frontier'][parents]
    allowed &= np.abs(normals[:,2])>=spec.get('min_vertical_normal',0.)
    score=area*(.3+np.abs(normals[:,2]))
    choices=np.flatnonzero(allowed);order=choices[np.argsort(-score[choices],kind='stable')];selected=[]
    for i in order:
        if not selected or np.linalg.norm(centers[selected]-centers[i],axis=1).min()>spec.get('spacing',.08):selected.append(int(i))
        if len(selected)>=spec.get('count',20):break
    if not selected:raise ValueError('No parent faces for low-poly child growth')
    mesh=Mesh.from_vertices_and_faces(m.xyz.tolist(),triangles)
    result=extrude_tapered_once(mesh,selected_faces=selected,height_ratio={i:spec.get('height_ratio',.48)*attenuation for i in selected},fraction={i:spec.get('fraction',.3) for i in selected},dll_path=runtime.REPO.parent/'Libraries/HDMola/1.0.0/HDMola.dll',budget=ExecutionBudget(budget,budget),source_is_result=True)
    # MOLA explicitly identifies the cap vertices belonging to each selected parent.
    for parent,parameters in result.parameters.items():
        keys=parameters['upper_vertex_ids'];pts=np.asarray([result.mesh.vertex_coordinates(i) for i in keys]);pivot=pts.mean(0)
        n=normals[parent];up=np.array([0.,0.,1.]);tangent=up-n*np.dot(up,n);length=np.linalg.norm(tangent)
        if length>1e-9:tangent/=length
        direction=1. if n[2]>=0 else -1.
        shift=tangent*direction*spec.get('axial_shift',.7)*parameters['height']
        axis=np.cross(n,tangent);axis/=max(np.linalg.norm(axis),1e-9);angle=spec.get('cap_turn',.35)*direction
        rel=pts-pivot
        rotated=rel*np.cos(angle)+np.cross(axis,rel)*np.sin(angle)+axis*(rel@axis)[:,None]*(1-np.cos(angle)) if length>1e-9 else rel
        for key,xyz in zip(keys,pivot+rotated+shift):result.mesh.vertex_attributes(key,'xyz',xyz.tolist())
    v,fs=result.mesh.to_vertices_and_faces();q=np.full((len(fs),max(4,max(map(len,fs)))),-1,int)
    for i,f in enumerate(fs):q[i,:len(f)]=f
    facekeys=list(result.mesh.faces());parent_face=np.asarray([parents[result.lineage.face_parents[k][0].key] for k in facekeys])
    generated=np.asarray([i for i,k in enumerate(facekeys) if result.face_roles[k] in ('side','cap')],int)
    out=ArrayMesh(np.asarray(v),q,np.full(len(v),-1,np.int8),np.asarray(v),np.full((len(q),3),-1,int),m.generation+1)
    return out,dict(operator='Actual HDMola tapered face extrusion; child-cap rotation and axial translation',selected=len(selected),selected_on_previous_generation=int(obs['frontier'][parents[selected]].sum()),frontier_only=spec.get('frontier_only',False),backend=result.backend,triangulation='Planarization only; no smoothing or dense subdivision'),dict(parent_face=parent_face,generated_faces=generated,selected_parent_faces=parents[selected])
