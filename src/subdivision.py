"""Independent closed-manifold CC/DS implementation; Hansmeyer 2010 eqs. 1-6.

No generation code or parameters imported from previous work.
Normals: unit polygon normal * perimeter; edge/vertex normals are arithmetic
means of incident scaled polygon normals (an explicit implementation choice).
"""
from dataclasses import dataclass
import numpy as np

@dataclass
class Mesh:
    v: np.ndarray
    f: list
    kinds: list = None
    groups: list = None

def column():
    v = np.array([(x,y,z) for z in np.linspace(-2,2,5)
                  for x,y in [(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)]])
    f = [[3,2,1,0], [16,17,18,19]]
    for k in range(4):
        for j in range(4):
            a=4*k+j; b=4*k+(j+1)%4
            f.append([a,b,b+4,a+4])
    return Mesh(v,f,['P']*len(v),['F']*len(f))

def topology(m):
    edges={}; vf=[[] for _ in m.v]; ve=[[] for _ in m.v]
    for fi,f in enumerate(m.f):
        for i,a in enumerate(f):
            vf[a].append(fi); b=f[(i+1)%len(f)]; e=tuple(sorted((a,b)))
            edges.setdefault(e,[]).append((fi,a,b))
    for e,uses in edges.items():
        if len(uses)!=2 or uses[0][1:]!=uses[1][1:][::-1]:
            raise ValueError('Expected closed, consistently wound two-manifold')
        for a in e: ve[a].append(e)
    return edges,vf,ve

def normals(m):
    result=[]
    for f in m.f:
        p=m.v[f]; n=np.cross(p,np.roll(p,-1,axis=0)).sum(axis=0)
        length=np.linalg.norm(n)
        if length<1e-12: raise ValueError('Degenerate face')
        result.append(n/length*np.linalg.norm(p-np.roll(p,-1,axis=0),axis=1).sum())
    return np.array(result)

def settings(g,p,group='F',standard=False):
    if standard: return dict(w1=0.,w2=0.,w3=0.,w4=0.,w10=0.,w11=0.,w12=0.)
    # Own fixed test settings, NOT Hansmeyer's unpublished settings.
    t=np.clip((p[2]+2)/4,0,1)
    spatial=.65+.7*t  # paper 3.2.1: linear interpolation of two axis sets
    w1=[-.6,.8,-.35][g-1]
    # DS's source-face classes F/E/V can carry distinct subsequent weights.
    w1 += dict(F=0.,E=.3,V=-.2)[group]
    return dict(w1=w1*spatial,w2=[.3,-.5,.4][g-1]*spatial,
                w3=[0.,.65,-.4][g-1],w4=[0.,-.3,.5][g-1],
                w10=[.035,-.025,.02][g-1]*spatial,
                w11=[-.012,.018,-.009][g-1]*spatial,
                w12=[.008,-.012,.006][g-1]*spatial)

def cc(m,g,standard=False,weight_provider=None):
    # Optional experiment recipe; default preserves the original checkpoint.
    resolve=weight_provider or settings
    edges,vf,ve=topology(m); nf=normals(m); fp=[]
    for fi,f in enumerate(m.f):
        p=m.v[f]; w=resolve(g,p.mean(axis=0),standard=standard)
        kinds=[m.kinds[i] for i in f] if m.kinds else []
        if len(f)==4 and sorted(kinds)==['E','E','F','V']:
            # eq. 4: retain provenance of the V,E,F,E corners.
            pv=p[kinds.index('V')]; pf=p[kinds.index('F')]
            pe=p[[i for i,k in enumerate(kinds) if k=='E']].sum(axis=0)
            q=((pv*(1+w['w3'])+pf*(1-w['w3']))*(1+w['w4'])
               +pe*(1-w['w4']))/4
        else: q=p.mean(axis=0) # eq. 1, also when a DS switch removes CC tags
        fp.append(q+nf[fi]*w['w10'])
    fp=np.array(fp); ep={}; vp=[]
    for e,uses in edges.items():
        p=m.v[list(e)]; ids=[u[0] for u in uses]
        w=resolve(g,p.mean(axis=0),standard=standard)
        ep[e]=((fp[ids].sum(axis=0)*(1+w['w1'])
                +p.sum(axis=0)*(1-w['w1']))/4
               +nf[ids].mean(axis=0)*w['w11']) # eq. 2
    for i,p in enumerate(m.v):
        n=len(vf[i]); w=resolve(g,p,standard=standard)
        # E in eq. 3 interpreted as ORIGINAL edge midpoints (standard CC R).
        # Paper prose is ambiguous; using new edge points fails standard CC.
        r=np.mean([m.v[list(e)].mean(axis=0) for e in ve[i]],axis=0)
        q=(fp[vf[i]].mean(axis=0)*(1+w['w2'])
           +2*r*(1-w['w2']/2)+(n-3)*p)/n
        vp.append(q+nf[vf[i]].mean(axis=0)*w['w12'])
    vs=list(vp)+list(ep.values())+list(fp)
    ei={e:len(m.v)+j for j,e in enumerate(edges)}
    offset=len(m.v)+len(edges); faces=[]
    for fi,f in enumerate(m.f):
        for j,a in enumerate(f):
            b=f[(j+1)%len(f)]; c=f[(j-1)%len(f)]
            faces.append([a,ei[tuple(sorted((a,b)))],offset+fi,ei[tuple(sorted((c,a)))]])
    return Mesh(np.array(vs),faces,['V']*len(vp)+['E']*len(ep)+['F']*len(fp),['F']*len(faces))

def ds(m,g,standard=False):
    edges,vf,ve=topology(m); nf=normals(m); corners={}; vs=[]; faces=[]; groups=[]
    for fi,f in enumerate(m.f):
        p=m.v[f]; n=len(f)
        if n not in (3,4): raise ValueError('Modified DS only specified for tri/quads')
        w=settings(g,p.mean(axis=0),(m.groups or ['F']*len(m.f))[fi],standard)
        for j,a in enumerate(f):
            if n==4:
                q=((2.25+2*w['w1'])*p[j]+(.75-w['w1'])*(p[(j-1)%n]+p[(j+1)%n])+.25*p[(j+2)%n])/4
            else:
                q=2/3*p[j]*(1+w['w1']/2)+(p[(j+1)%n]+p[(j+2)%n])*(1-w['w1'])/6
            corners[fi,a]=len(vs); vs.append(q+nf[fi]*w['w10'])
        faces.append([corners[fi,a] for a in f]); groups.append('F')
    # Edge faces are wound opposite to the adjacent inset-face edges.
    for e,uses in edges.items():
        fi,a,b=uses[0]; fj,_,_=uses[1]
        faces.append([corners[fi,b],corners[fi,a],corners[fj,a],corners[fj,b]]); groups.append('E')
    # Traverse directed halfedges around each old vertex to construct its face.
    for a,incident in enumerate(vf):
        successor={}
        for fi in incident:
            f=m.f[fi]; b=f[(f.index(a)+1)%len(f)]
            successor[fi]=next(u[0] for u in edges[tuple(sorted((a,b)))] if u[0]!=fi)
        ring=[]; fi=incident[0]
        while fi not in ring: ring.append(fi); fi=successor[fi]
        if len(ring)!=len(incident): raise ValueError('Broken DS vertex fan')
        faces.append([corners[fi,a] for fi in reversed(ring)]); groups.append('V')
    return Mesh(np.array(vs),faces,None,groups)

def check(m):
    e,_,_=topology(m)
    assert np.isfinite(m.v).all()
    assert len(m.v)-len(e)+len(m.f)==2
    normals(m)
    return dict(vertices=len(m.v),edges=len(e),faces=len(m.f),euler=2,
                bounds=[m.v.min(axis=0).tolist(),m.v.max(axis=0).tolist()])

def save_obj(m,path):
    with open(path,'w',encoding='utf8') as out:
        for v in m.v: out.write('v '+' '.join(f'{x:.10g}' for x in v)+'\n')
        for f in m.f: out.write('f '+' '.join(str(i+1) for i in f)+'\n')
