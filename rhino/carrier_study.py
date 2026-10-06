"""Task 15 carriers and measurements; Task 14 geometry rules stay unchanged."""
from collections import Counter
from copy import deepcopy
from math import dist, fsum, isfinite
from statistics import median

from compas.datastructures import Mesh
from compas.geometry import volume_polyhedron
from cheshire.execution import ExecutionBudget
from cheshire.subdivision import subdivide_quad_once
from cheshire.validation import inspect_mesh, validate_mesh
from weighted_study import SCHEDULES, generation_weights, run_candidate

DIMENSIONS = dict(width=4000.0, height=3500.0, depth=500.0,
                  opening_width=2200.0, opening_height=2600.0)
BUDGET = ExecutionBudget(50000, 50000, 6)


def coarse_gate(origin=(0.0, 0.0, 0.0)):
    """Boundary of five explicitly adjacent rectangular cells, not separate boxes.

    Grid corner identities are shared by construction. Internal cell interfaces
    are never emitted. All 22 exterior faces are planar, outward wound quads.
    The architectural opening is open to the ground; the solid's mesh is closed.
    """
    if len(origin) != 3 or not all(isfinite(x) for x in origin):
        raise ValueError("Carrier origin must be three finite coordinates.")
    xs, ys, zs = [-2000., -1100., 1100., 2000.], [-250., 250.], [0., 2600., 3500.]
    cells = {(0,0), (2,0), (0,1), (1,1), (2,1)}
    mesh, ids = Mesh(), {}
    def face(corners):
        keys=[]
        for corner in corners:
            if corner not in ids:
                i,j,k=corner
                p=[xs[i]+origin[0], ys[j]+origin[1], zs[k]+origin[2]]
                ids[corner]=mesh.add_vertex(x=p[0],y=p[1],z=p[2])
            keys.append(ids[corner])
        mesh.add_face(keys)
    for i,k in sorted(cells, key=lambda cell:(cell[1],cell[0])):
        if (i-1,k) not in cells:
            face([(i,0,k),(i,0,k+1),(i,1,k+1),(i,1,k)])
        if (i+1,k) not in cells:
            face([(i+1,0,k),(i+1,1,k),(i+1,1,k+1),(i+1,0,k+1)])
        face([(i,0,k),(i+1,0,k),(i+1,0,k+1),(i,0,k+1)])
        face([(i,1,k),(i,1,k+1),(i+1,1,k+1),(i+1,1,k)])
        if (i,k-1) not in cells:
            face([(i,0,k),(i,1,k),(i+1,1,k),(i+1,0,k)])
        if (i,k+1) not in cells:
            face([(i,0,k+1),(i+1,0,k+1),(i+1,1,k+1),(i,1,k+1)])
    if validate_mesh(mesh) or not mesh.is_valid() or not mesh.is_manifold() or not mesh.is_closed() or len(mesh.connected_vertices()) != 1:
        raise ValueError("Constructed carrier did not meet the connected closed-manifold contract.")
    return mesh


def carrier_ladder(c0):
    c1=subdivide_quad_once(c0,budget=BUDGET).mesh
    c2=subdivide_quad_once(c1,budget=BUDGET).mesh
    return dict(C0=c0,C1=c1,C2=c2)


def distribution(values):
    values=sorted(values)
    def quantile(q):
        index=(len(values)-1)*q
        lo=int(index); hi=min(lo+1,len(values)-1)
        return values[lo]*(hi-index)+values[hi]*(index-lo) if hi != lo else values[lo]
    return dict(min=values[0],q25=quantile(.25),median=median(values),q75=quantile(.75),max=values[-1],mean=fsum(values)/len(values))


def carrier_statistics(mesh):
    xyz={v:mesh.vertex_coordinates(v) for v in mesh.vertices()}
    extraordinary=[dict(id=v,valence=mesh.vertex_degree(v),xyz=xyz[v]) for v in mesh.vertices()
                   if not mesh.is_vertex_on_boundary(v) and mesh.vertex_degree(v) != 4]
    values=list(xyz.values())
    low=[min(p[i] for p in values) for i in range(3)]
    high=[max(p[i] for p in values) for i in range(3)]
    keys=list(mesh.vertices()); indices={v:i for i,v in enumerate(keys)}
    return dict(**inspect_mesh(mesh),components=len(mesh.connected_vertices()),bbox_min=low,bbox_max=high,
        face_area=distribution(mesh.face_area(f) for f in mesh.faces()),
        edge_length=distribution(dist(xyz[u],xyz[v]) for u,v in mesh.edges()),
        valence_histogram=dict(sorted(Counter(mesh.vertex_degree(v) for v in mesh.vertices()).items())),
        extraordinary_vertex_count=len(extraordinary),extraordinary_vertices=extraordinary,
        signed_volume=volume_polyhedron(([xyz[v] for v in keys],[[indices[v] for v in mesh.face_vertices(f)] for f in mesh.faces()])) if mesh.is_closed() else None,
        face_area_note="COMPAS polygon area; nonplanar generated quads are a polygonal approximation.",
        signed_volume_note="COMPAS polygonal/fan volume, not exact bilinear-patch integration or a validity certificate.")


def expanded_schedule(schedule, generations=6):
    """Serialize every generation explicitly, even the repeated fine tail."""
    return [generation_weights(schedule,g) for g in range(1,generations+1)]


LOCAL_SCHEDULES = {
    "L0_reference_fold": expanded_schedule(SCHEDULES["fold_probe"]),
    "L1_soft_fold": expanded_schedule([
        dict(wf=.32,w1=-1.15,we=-.14,w2=-.9,wp=.05),
        dict(wf=.18,w1=-.95,we=-.075,w2=-.75,wp=.025),
        dict(wf=.10,w1=-.60,we=-.04,w2=-.4,wp=.012)]),
    "L2_shallow_edges": expanded_schedule([
        dict(wf=.36,w1=-1.15,we=-.08,w2=-.9,wp=.05),
        dict(wf=.18,w1=-.95,we=-.04,w2=-.75,wp=.025),
        dict(wf=.10,w1=-.6,we=-.025,w2=-.4,wp=.012)]),
    "L3_soft_interpolation": expanded_schedule([
        dict(wf=.34,w1=-.95,we=-.12,w2=-.7,wp=.045),
        dict(wf=.16,w1=-.75,we=-.06,w2=-.5,wp=.02),
        dict(wf=.08,w1=-.5,we=-.03,w2=-.3,wp=.01)]),
    "L4_macro_corner": expanded_schedule([
        dict(wf=.30,w1=-1.0,we=-.08,w2=-.7,wp=.10),
        dict(wf=.16,w1=-.85,we=-.05,w2=-.6,wp=.045),
        dict(wf=.08,w1=-.55,we=-.025,w2=-.35,wp=.015)]),
    "L5_gentle_fold": expanded_schedule([
        dict(wf=.26,w1=-.9,we=-.08,w2=-.65,wp=.035),
        dict(wf=.14,w1=-.75,we=-.045,w2=-.5,wp=.018),
        dict(wf=.07,w1=-.45,we=-.025,w2=-.25,wp=.008)]),
}


def run_uniform(mesh,schedule,*,generations=6,publish=None):
    """All carrier scales use the same schedule and Task 14 global-edge scaling."""
    return run_candidate(mesh,study="U",schedule=expanded_schedule(schedule,6),
                         generations=generations,budget=BUDGET,publish=publish)


def topology_warning_association(mesh, warnings):
    """Compare warning rates near current extraordinary vertices; no causality."""
    extraordinary={v for v in mesh.vertices() if not mesh.is_vertex_on_boundary(v) and mesh.vertex_degree(v) != 4}
    nearby=extraordinary | {n for v in extraordinary for n in mesh.vertex_neighbors(v)}
    near={f for f in mesh.faces() if set(mesh.face_vertices(f)) & nearby}
    flagged=set(warnings)
    examples=[]
    for f in [*sorted(flagged & near)[:3],*sorted(flagged-near)[:3],*sorted(near-flagged)[:3]]:
        examples.append(dict(face=f,warning=f in flagged,near_extraordinary=f in near,
            corners=[dict(id=v,valence=mesh.vertex_degree(v),boundary=mesh.is_vertex_on_boundary(v),xyz=mesh.vertex_coordinates(v)) for v in mesh.face_vertices(f)]))
    return dict(definition="Face incident to an extraordinary vertex or its one-hop neighbor; current topology, no inferred semantic lineage.",
        extraordinary_vertices=sorted(extraordinary),near_faces=len(near),far_faces=mesh.number_of_faces()-len(near),
        near_warning_faces=len(flagged & near),far_warning_faces=len(flagged-near),examples=examples,
        interpretation="Observational association only; no attribution of cause and no valence-dependent weights.")


def generation_schedules():
    """Eight explicit experiments on the selected C0, no spatial modulation.

    Fixed control repeats the seed's G1 ratios. All extrusions still use the
    unchanged Task14 generation-global mean edge scaling, not fixed distances.
    """
    seed=LOCAL_SCHEDULES["L4_macro_corner"]
    def rows(values):
        return [dict(zip(("wf","w1","we","w2","wp"),v)) for v in values]
    return {
        "T00_fixed": [deepcopy(seed[0]) for _ in range(6)],
        "T01_seed": deepcopy(seed),
        "T02_macro_attenuation": rows([
            (.38,-.95,-.08,-.65,.10),(.12,-.65,-.035,-.45,.025),(.06,-.45,-.025,-.25,.012),
            (.045,-.35,-.015,-.15,.008),(.02,-.25,-.01,-.1,.005),(.015,-.25,-.008,-.1,.003)]),
        "T03_meso_interpolation": rows([
            (.30,-1.,-.08,-.7,.10),(.14,-1.25,-.04,-1.,.035),(.10,-1.45,-.025,-1.15,.025),
            (.045,-.85,-.015,-.6,.01),(.025,-.6,-.01,-.35,.008),(.02,-.5,-.008,-.3,.005)]),
        "T04_edge_then_face": rows([
            (.28,-.9,-.04,-.65,.10),(.10,-1.15,-.095,-.7,.03),(.14,-.8,-.025,-1.,.05),
            (.055,-.6,-.035,-.5,.01),(.028,-.45,-.01,-.3,.006),(.018,-.4,-.008,-.25,.004)]),
        "T05_corner_then_edge": rows([
            (.28,-.95,-.065,-.6,.14),(.12,-.9,-.05,-.8,.075),(.08,-1.15,-.065,-.9,.02),
            (.045,-.75,-.025,-.55,.01),(.025,-.45,-.01,-.25,.005),(.018,-.4,-.008,-.2,.004)]),
        "T06_delayed_meso": rows([
            (.28,-.95,-.065,-.6,.075),(.17,-.75,-.035,-.55,.04),(.18,-1.2,-.075,-1.1,.06),
            (.06,-.7,-.025,-.5,.02),(.03,-.5,-.01,-.25,.005),(.02,-.4,-.008,-.2,.003)]),
        "T07_alternating_sign": rows([
            (.30,-1.,-.08,-.7,.10),(.08,-.8,-.07,-.5,.02),(-.10,-1.,.04,-.8,-.018),
            (.055,-.6,-.02,-.4,.012),(-.028,-.4,.012,-.25,-.006),(.018,-.35,-.008,-.2,.004)]),
    }


def schedule_extensions():
    """Two retained follow-ups: stable fixed control and stronger fine tail.

    Added after T00's constant strong weights crossed, without overwriting it.
    These bring the generation phase to ten schedules (16 unique task-wide).
    """
    seed=LOCAL_SCHEDULES["L4_macro_corner"]
    fine=deepcopy(generation_schedules()["T03_meso_interpolation"])
    fine[3]=dict(wf=.11,w1=-.75,we=-.04,w2=-.6,wp=.018)
    fine[4]=dict(wf=.08,w1=-.6,we=-.025,w2=-.4,wp=.008)
    fine[5]=dict(wf=.04,w1=-.45,we=-.012,w2=-.25,wp=.004)
    return {"T08_fixed_moderate":[deepcopy(seed[1]) for _ in range(6)],
            "T09_meso_fine":fine}
