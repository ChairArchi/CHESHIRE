"""Opt-in literal equations 7/10/11 over the unchanged Extended CC backend."""
from collections import Counter, deque
from copy import deepcopy
from dataclasses import dataclass
from math import fsum, isfinite

from .generational_subdivision import generational_subdivide_once
from .attributes import _curvature, _face_normal

WEIGHTS=('wf','w1','we','w2','wp','w3','w4','w6','w7')


def finite(value):
    if type(value) not in (int,float) or not isfinite(value):
        raise ValueError('Finite real value required.')
    return float(value)


def equation7(iteration, a, b, q):
    """a + b*(i-1)**q; positive exponent makes the first value exactly a."""
    if type(iteration) is not int or iteration<1: raise ValueError('Iteration starts at one.')
    a,b,q=map(finite,(a,b,q))
    if q<=0: raise ValueError('A positive trend exponent is required; no ambiguous zero power.')
    value=a+b*(iteration-1)**q
    if not isfinite(value): raise ValueError('Nonfinite trend result.')
    return value


def compile_schedule(specifications, generations):
    """Explicit finite horizon, all nine controls, no silent extrapolation."""
    if type(generations) is not int or generations<1 or set(specifications)-set(WEIGHTS):
        raise ValueError('Declared weights and positive generation count required.')
    declarations=[]; rows=[{} for _ in range(generations)]
    for name in WEIGHTS:
        specification=deepcopy(specifications.get(name,dict(mode='DISCRETE',values=[0.]*generations)))
        mode=specification.get('mode')
        if mode=='DISCRETE':
            if set(specification)!={'mode','values'} or len(specification['values'])!=generations:
                raise ValueError('Discrete values must cover exactly the requested horizon.')
            values=[finite(v) for v in specification['values']]
        elif mode=='EQ7_TREND':
            if set(specification)!={'mode','a','b','q'}: raise ValueError('Eq7 requires exactly a/b/q.')
            values=[equation7(i,specification['a'],specification['b'],specification['q']) for i in range(1,generations+1)]
        else: raise ValueError('Unknown schedule mode.')
        declarations.append(dict(name=name,**specification,resulting_values=values))
        for row,value in zip(rows,values): row[name]=value
    return dict(generations=generations,weights=declarations,rows=rows,
        indexing='Sharp-stage iteration begins at one; no evaluation beyond the serialized horizon.')


@dataclass(frozen=True,order=True)
class MotifSignature:
    vertex_valence:int
    incident_face_count:int
    def key(self): return f'({self.vertex_valence},{self.incident_face_count})'


def topology_motifs(mesh):
    return {v:MotifSignature(mesh.vertex_degree(v),len(mesh.vertex_faces(v))) for v in mesh.vertices()}


def validate_motif_map(mapping):
    import re
    if not isinstance(mapping,dict): raise ValueError('Explicit motif-value mapping required.')
    result={}
    for key,value in mapping.items():
        if not isinstance(key,str) or not re.fullmatch(r'\([0-9]+,[0-9]+\)',key):
            raise ValueError('Canonical (valence,incident_faces) motif key required.')
        result[key]=finite(value)
    return result


def motif_values(mesh,mapping,default=0.):
    mapping=validate_motif_map(mapping); default=finite(default)
    return {v:mapping.get(signature.key(),default) for v,signature in topology_motifs(mesh).items()}


def equation10(face_point, vertices, values, weight):
    """Literal unnormalized sum using the input face's original corners."""
    weight=finite(weight); vertices=list(vertices); values=list(values)
    if len(vertices)!=len(values) or not vertices: raise ValueError('One motif value per face corner required.')
    q=[finite(x) for x in face_point]
    if len(q)!=3 or any(len(p)!=3 for p in vertices): raise ValueError('XYZ points required.')
    values=list(map(finite,values)); vertices=[[finite(x) for x in p] for p in vertices]
    if weight==0 or all(u==0 for u in values): return list(face_point)
    return [finite(q[a]+weight*fsum((p[a]-q[a])*u for p,u in zip(vertices,values))) for a in range(3)]


def equation11(edge_point, p1, p2, u1, u2, weight):
    """Literal two-endpoint sum; never an averaged or normalized variant."""
    return equation10(edge_point,[p1,p2],[u1,u2],weight)


def source_graph_distance(mesh,seeds):
    """Original control graph edge hops, independent of XYZ and tessellation."""
    seeds=sorted(set(seeds))
    if not seeds or not set(seeds)<=set(mesh.vertices()): raise ValueError('Known source graph seeds required.')
    distances={v:None for v in mesh.vertices()}; queue=deque(seeds)
    for v in seeds: distances[v]=0
    while queue:
        v=queue.popleft()
        for n in sorted(mesh.vertex_neighbors(v)):
            if distances[n] is None: distances[n]=distances[v]+1; queue.append(n)
    maximum=max(d for d in distances.values() if d is not None)
    return dict(hops=distances,normalized={v:None if d is None else d/maximum if maximum else 0. for v,d in distances.items()},
        seeds=seeds,normalization_maximum_hops=maximum,
        scope='Frozen original control graph; later samples inherit positive control-cage association, not a Euclidean metric or diffusion.')


def inherit_scalar(values,sampling):
    result={}
    for child,parents in sampling.items():
        if any(values[v] is None for v,w in parents if w>0): result[child]=None
        else: result[child]=fsum(values[v]*w for v,w in parents)
    return result


def normal_variation_values(mesh):
    """Reuse the verified incident-normal proxy; not differential curvature."""
    normals={f:_face_normal(mesh,f) for f in mesh.faces()}
    return {v:_curvature(mesh,v,mesh.vertex_neighbors(v),mesh.is_vertex_on_boundary(v),normals) for v in mesh.vertices()}


def intrinsic_overrides(mesh,modulation,scalar):
    """CHESHIRE linear interpolation of selected existing controls only."""
    if not modulation: return {},{},dict(mode='NONE')
    if modulation.get('mode') not in ('SOURCE_GRAPH_DISTANCE','NORMAL_VARIATION'):
        raise ValueError('Unknown intrinsic modulation.')
    controls=modulation['controls']
    if set(controls)-set(WEIGHTS[:7]): raise ValueError('Intrinsic experiment modulates existing Eq1-4 controls only.')
    if set(scalar)!=set(mesh.vertices()) or any(v is None or not 0<=finite(v)<=1 for v in scalar.values()):
        raise ValueError('Defined normalized intrinsic samples required; no guessed boundary value.')
    pairs={name:[finite(v) for v in pair] for name,pair in controls.items()}
    if any(len(pair)!=2 for pair in pairs.values()): raise ValueError('Weight min/max pair required.')
    overrides={'face':{},'edge':{},'corner':{}}; later={}
    counts=Counter()
    def row(vertices,names):
        t=fsum(scalar[v] for v in vertices)/len(vertices)
        counts['samples']+=1
        return {name:pairs[name][0]+t*(pairs[name][1]-pairs[name][0]) for name in names if name in pairs}
    for f in mesh.faces():
        vertices=mesh.face_vertices(f); overrides['face'][f]=row(vertices,['wf'])
        later[f]=row(vertices,['w3','w4'])
    for u,v in mesh.edges(): overrides['edge'][(u,v)]=row([u,v],['w1','we'])
    for v in mesh.vertices(): overrides['corner'][v]=row([v],['w2','wp'])
    return overrides,later,dict(mode=modulation['mode'],controls=pairs,samples=counts['samples'],
        scalar_min=min(scalar.values()),scalar_max=max(scalar.values()),
        semantics='Linear min/max interpolation; generated point samples average input-corner scalar values. This interpolation is CHESHIRE-defined.')


@dataclass(frozen=True)
class SharpResult:
    mesh:object
    metadata:dict
    sampling_parents:dict
    origin_lineage:dict
    lock_groups:dict


def sharp_subdivide_once(mesh,weights=None,*,u_map=None,unknown_u=0.,lock_groups=None,
        lock_iteration=None,origin_lineage=None,point_weights=None,face_weights=None,budget=None,current_generation=0,
        vertex_u_scale=None):
    """Existing CC/Eq4 first; literal Eq10/11 offsets, then tagged corner locks.

    Modified face/edge points are not fed back into the existing same-generation
    Eq2/3 rules. All reference sums use original input XYZ. Positive sampling
    remains a construction association, separate from signed geometry and u.
    """
    requested=weights or {}
    if set(requested)-set(WEIGHTS): raise ValueError('Unknown sharp subdivision weight.')
    values={name:finite(requested.get(name,0.)) for name in WEIGHTS}
    u=motif_values(mesh,u_map or {},unknown_u)
    if vertex_u_scale is not None:
        if set(vertex_u_scale)!=set(mesh.vertices()): raise ValueError('Explicit source-support scale for every input vertex required.')
        for v,scale in vertex_u_scale.items(): u[v]*=finite(scale)
    groups=deepcopy(lock_groups or {}); iteration=lock_iteration if lock_iteration is not None else current_generation+1
    if type(iteration) is not int or iteration<1: raise ValueError('Lock iteration starts at one.')
    locked=set()
    for name,group in groups.items():
        if not name or set(group)!={'vertices','iterations'} or type(group['iterations']) is not int or group['iterations']<0:
            raise ValueError('Named corner group and nonnegative lock duration required.')
        if any(type(v) is not int for v in group['vertices']) or not set(group['vertices'])<=set(mesh.vertices()):
            raise ValueError('Lock group must contain known input corner descendants.')
        if iteration<=group['iterations']: locked.update(group['vertices'])
    motifs=topology_motifs(mesh)
    base=generational_subdivide_once(mesh,{k:values[k] for k in WEIGHTS[:7]},origin_lineage=origin_lineage,
        point_weights=point_weights,face_weights=face_weights,budget=budget,current_generation=current_generation)
    applications=[]
    for point in base.metadata['points']:
        child=point['id']; kind=point['point_class']; source=point['source']; before=base.mesh.vertex_coordinates(child)
        if kind=='face':
            parents=mesh.face_vertices(source); used=values['w6']
            after=equation10(before,[mesh.vertex_coordinates(v) for v in parents],[u[v] for v in parents],used)
        elif kind=='edge':
            parents=source; used=values['w7']
            after=equation11(before,*(mesh.vertex_coordinates(v) for v in parents),*(u[v] for v in parents),used)
        else: parents=[source]; used=0.; after=before
        is_locked=kind=='corner' and source in locked
        if is_locked: after=mesh.vertex_coordinates(source)
        if after!=before: base.mesh.vertex_attributes(child,'xyz',after)
        applications.append(dict(point=child,kind=kind,input_vertices=parents,motif_u=[u[v] for v in parents],
            attraction_weight=used,base_xyz=before,result_xyz=after,locked=is_locked))
    from .validation import inspect_mesh,validate_mesh
    if validate_mesh(base.mesh) or not base.mesh.is_valid() or not base.mesh.is_manifold():
        raise ValueError('Sharp placement failed finite/manifold contract; no repair.')
    metadata={**base.metadata,'name':'CHESHIRE isolated literal motif-attraction CC',
        'output':inspect_mesh(base.mesh),'equation_mode':'LITERAL_EQ10_EQ11_UNNORMALIZED',
        'weights':values,'u_map':validate_motif_map(u_map or {}),'unknown_u':finite(unknown_u),
        'source_support_scale':vertex_u_scale,
        'input_motif_histogram':dict(Counter(s.key() for s in motifs.values())),
        'output_motif_histogram':dict(Counter(s.key() for s in topology_motifs(base.mesh).values())),
        'motif_applications':applications,'locking':dict(iteration=iteration,groups=groups,active_vertices=sorted(locked),
            semantics='Tagged input vertices retain positions only through the persistent CC corner descendants for the first L sharp iterations. New edge/face points are not tagged. No projection or edge-strengthening rule.'),
        'geometry_vs_lineage':'Positive original control-cage association is unchanged; semantic inheritance NOT IMPLEMENTED.'}
    return SharpResult(base.mesh,metadata,base.sampling_parents,base.origin_lineage,groups)
