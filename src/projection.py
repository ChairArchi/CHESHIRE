"""Independent frame-to-solid parallel ray mapping. No subdivision code."""
import numpy as np

def frame():
    # Parameter-domain sampling only: never CC/DS or recursive refinement.
    xs=np.linspace(-1.1,1.1,17); zs=np.linspace(-1.8,1.8,17)
    points=[]; faces=[]; ids={}
    for j in range(16):
        for i in range(16):
            if 4<=i<12 and 4<=j<12: continue
            f=[]
            for a,b in [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]:
                if (a,b) not in ids:
                    ids[a,b]=len(points); points.append((xs[a],-2.5,zs[b]))
                f.append(ids[a,b])
            faces.append(f)
    return np.array(points),faces

def target(depth=.9):
    # Independent capped 32-sided elliptical prism, no opening.
    angles=np.arange(32)*2*np.pi/32
    v=np.array([(1.4*np.cos(a),depth*np.sin(a),z) for z in [-2.2,2.2] for a in angles])
    f=[list(reversed(range(32))),list(range(32,64))]
    f += [[i,(i+1)%32,(i+1)%32+32,i+32] for i in range(32)]
    return v,f

def triangulate(faces):
    return np.array([[f[0],f[i],f[i+1]] for f in faces for i in range(1,len(f)-1)])

def project(points,tv,tf):
    """p -> p + min{t>=0 : p+t(0,1,0) intersects a target triangle} d.

    Moller-Trumbore triangle intersection, two-sided, no hardcoded cylinder
    equation or bounding-box transfer. Missed rays are errors.
    """
    triangles=triangulate(tf); tris=tv[triangles]; a=tris[:,0]
    e1=tris[:,1]-a; e2=tris[:,2]-a; direction=np.array([0.,1.,0.])
    h=np.cross(np.broadcast_to(direction,e2.shape),e2)
    determinant=np.einsum('ij,ij->i',e1,h); valid=np.abs(determinant)>1e-12
    inv=np.zeros_like(determinant); inv[valid]=1/determinant[valid]
    output=[]; receipts=[]
    for p in points:
        s=p-a; u=inv*np.einsum('ij,ij->i',s,h); q=np.cross(s,e1)
        b=inv*(q@direction); distance=inv*np.einsum('ij,ij->i',e2,q)
        mask=valid&(u>=-1e-10)&(b>=-1e-10)&(u+b<=1+1e-10)&(distance>=0)
        candidates=np.where(mask,distance,np.inf); k=int(np.argmin(candidates))
        if not np.isfinite(candidates[k]): raise ValueError('Input ray misses target')
        hit=p+distance[k]*direction
        bary=(1-u[k]-b[k])*tris[k,0]+u[k]*tris[k,1]+b[k]*tris[k,2]
        assert np.linalg.norm(hit-bary)<1e-9
        output.append(hit); receipts.append((k,float(distance[k]),float(u[k]),float(b[k])))
    return np.array(output),receipts

def save_obj(v,f,path):
    with open(path,'w',encoding='utf8') as out:
        for p in v: out.write('v '+' '.join(f'{x:.10g}' for x in p)+'\n')
        for face in f: out.write('f '+' '.join(str(i+1) for i in face)+'\n')

def check_frame(v,f):
    edges={}
    for face in f:
        for i,a in enumerate(face):
            e=tuple(sorted((a,face[(i+1)%len(face)]))); edges[e]=edges.get(e,0)+1
    boundary=[e for e,n in edges.items() if n==1]; adj={}
    for a,b in boundary: adj.setdefault(a,[]).append(b); adj.setdefault(b,[]).append(a)
    assert all(len(x)==2 for x in adj.values())
    components=0; visited=set()
    for seed in adj:
        if seed in visited: continue
        components+=1; stack=[seed]
        while stack:
            a=stack.pop()
            if a in visited: continue
            visited.add(a); stack.extend(adj[a])
    assert components==2 and len(v)-len(edges)+len(f)==0
    return dict(vertices=len(v),faces=len(f),boundary_loops=components,euler=0)
