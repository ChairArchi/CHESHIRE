"""Join short chains of adjacent quads before building raised shared frames."""
import numpy as np

def build(data, maximum=3):
    vertices=np.asarray(data['vertices']);quads=data['faces'];owners={}
    axes=[];normals=[];centers=[]
    for i,q in enumerate(quads):
        p=vertices[q];u=(p[1]-p[0]+p[2]-p[3])*.5;v=(p[3]-p[0]+p[2]-p[1])*.5
        axis=u if np.linalg.norm(u)>np.linalg.norm(v) else v
        axes.append(axis/max(np.linalg.norm(axis),1e-12))
        n=np.cross(u,v);normals.append(n/max(np.linalg.norm(n),1e-12));centers.append(p.mean(0))
        for a,b in zip(q,q[1:]+q[:1]):owners.setdefault(tuple(sorted((a,b))),[]).append(i)
    neighbors=[[] for q in quads]
    for edge,ids in owners.items():
        if len(ids)==2:
            a,b=ids;delta=centers[b]-centers[a];delta/=max(np.linalg.norm(delta),1e-12)
            alignment=min(abs(np.dot(delta,axes[a])),abs(np.dot(delta,axes[b])))
            if alignment>.6 and abs(np.dot(axes[a],axes[b]))>.65 and np.dot(normals[a],normals[b])>.25:
                neighbors[a].append((alignment,b));neighbors[b].append((alignment,a))
    available=set(range(len(quads)));groups=[]
    while available:
        seed=min(available);available.remove(seed);group=[seed]
        while len(group)<maximum:
            candidates=[(score,b) for a in (group[0],group[-1]) for score,b in neighbors[a] if b in available]
            if not candidates:break
            _,b=max(candidates);available.remove(b)
            if any(k==b for _,k in neighbors[group[-1]]):group.append(b)
            else:group.insert(0,b)
        groups.append(group)
    out=vertices.tolist();faces=[];relief=[0.]*len(out);lengths=[]
    for group in groups:
        directed={}
        for i in group:
            q=quads[i]
            for a,b in zip(q,q[1:]+q[:1]):
                if (b,a) in directed:del directed[(b,a)]
                else:directed[(a,b)]=True
        next_vertex={a:b for a,b in directed};start=min(next_vertex);loop=[start]
        while next_vertex[loop[-1]]!=start:
            loop.append(next_vertex[loop[-1]])
            if len(loop)>len(directed):raise ValueError('Non-simple strip boundary')
        if len(loop)!=len(directed):raise ValueError('Strip boundary has multiple loops')
        p=vertices[loop];center=p.mean(0);crest=len(out)
        # Each crown now spans an actual chain of faces instead of one cell.
        for point in p:out.append((center+(point-center)*.78).tolist());relief.append(.0025)
        inner=len(out)
        for point in p:out.append((center+(point-center)*.48).tolist());relief.append(0.)
        n=len(loop)
        for k in range(n):
            t=(k+1)%n
            faces.extend([[loop[k],loop[t],crest+t,crest+k],[crest+k,crest+t,inner+t,inner+k]])
        lengths.append(len(group))
    used=sorted(set(x for q in faces for x in q));remap={v:i for i,v in enumerate(used)}
    return [out[i] for i in used],[[remap[i] for i in q] for q in faces],[relief[i] for i in used],lengths
