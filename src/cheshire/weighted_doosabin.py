"""Isolated weighted Doo-Sabin; COMPAS supplies standard positions/topology.

Only published triangle/quad positions are weighted. Other polygons keep the
actual COMPAS standard corner positions, with explicit fallback records.
"""
from collections import Counter
from dataclasses import dataclass
from math import cos, hypot, isfinite, pi
from time import perf_counter

from compas.datastructures import Mesh

from .execution import ExecutionBudget, check_execution_budget
from .lineage import LineageMap, ParentRef
from .validation import inspect_mesh, validate_mesh, validate_lineage_coverage
from .weighted_subdivision import _extrude

FACE_DERIVED="FACE_DERIVED"
EDGE_DERIVED="EDGE_DERIVED"
VERTEX_DERIVED="VERTEX_DERIVED"
FAMILIES=(FACE_DERIVED,EDGE_DERIVED,VERTEX_DERIVED)
SUFFIX={FACE_DERIVED:"face",EDGE_DERIVED:"edge",VERTEX_DERIVED:"vertex"}
PARAMETERS=tuple(f"{name}_{kind}" for kind in SUFFIX.values() for name in ("w1","w10"))
STANDARD={key:0.0 for key in PARAMETERS}


@dataclass(frozen=True)
class DooSabinResult:
    mesh: Mesh
    metadata: dict
    lineage: LineageMap
    face_families: dict
    corner_parents: dict


def weighted_corner(points, corner, normal, *, w1, w10):
    """Published cyclic quad/triangle rules, in coordinate units; no n-gon rule."""
    n=len(points)
    p=points[corner]; next_p=points[(corner+1)%n]; previous=points[(corner-1)%n]
    if n==4:
        opposite=points[(corner+2)%n]
        xyz=[(p[i]*(2.25+2*w1)+(next_p[i]+previous[i])*(.75-w1)+.25*opposite[i])/4 for i in range(3)]
    elif n==3:
        xyz=[(2/3)*p[i]*(1+w1/2)+(1/6)*(next_p[i]+previous[i])*(1-w1) for i in range(3)]
    else:
        raise ValueError("Weighted Doo-Sabin corner rules support only triangles/quads.")
    return _extrude(xyz,normal,w10)


def _cycle(vertices):
    """Oriented topology signature, invariant to cyclic starting corner only."""
    i=vertices.index(min(vertices))
    return tuple(vertices[i:]+vertices[:i])


def _sampling_coefficients(n,corner):
    # Positive STANDARD control-cage associations, not weighted geometry or
    # semantic interpolation. General coefficients are COMPAS's standard DS.
    return [(n+5)/(4*n) if j==corner else (3+2*cos(2*pi*(corner-j)/n))/(4*n) for j in range(n)]


def weighted_doosabin_once(mesh,weights=None,*,face_families=None,budget=None,current_generation=0):
    """Closed oriented manifold only; no invented open-boundary/crease rule.

    Family labels are assigned while constructing the returned faces from
    source topology. Expected cycles are verified against public COMPAS DS.
    Correspondence uses source iteration/corner order, never XYZ proximity.
    """
    started=perf_counter()
    before=inspect_mesh(mesh)
    estimate=dict(estimated_output_vertices=sum(len(mesh.face_vertices(f)) for f in mesh.faces()),
                  estimated_output_faces=before["face_count"]+before["edge_count"]+before["vertex_count"])
    assessment={**estimate,**check_execution_budget(budget or ExecutionBudget(50000,50000),
        input_vertices=before["vertex_count"],input_faces=before["face_count"],
        current_generation=current_generation,**estimate)}
    if assessment["status"]!="SAFE":
        raise ValueError("Doo-Sabin blocked: "+" ".join(assessment["reasons"]))
    problems=validate_mesh(mesh)
    if problems or not mesh.is_valid() or not mesh.is_manifold() or not mesh.is_closed():
        raise ValueError("Doo-Sabin requires finite, valid, closed manifold input; open boundaries are unsupported. "+" ".join(problems))
    if any(mesh.vertex_degree(v)<3 for v in mesh.vertices()) or any(len(mesh.face_vertices(f))<3 for f in mesh.faces()):
        raise ValueError("Doo-Sabin requires at least three corners per face and three incident edges per vertex.")
    if any(mesh.edge_attribute(e,"crease") for e in mesh.edges()):
        raise ValueError("Doo-Sabin crease semantics are unsupported.")
    if weights is not None and not isinstance(weights,dict):
        raise ValueError("Doo-Sabin weights must be a dictionary of finite family parameters.")
    values={**STANDARD,**(weights or {})}
    if set(values)!=set(STANDARD) or any(type(w) not in (int,float) or not isfinite(w) for w in values.values()):
        raise ValueError("Doo-Sabin weights must contain only the six finite family parameters.")
    faces=list(mesh.faces())
    if face_families is not None:
        if set(face_families)!=set(faces) or any(not isinstance(r,dict) or r.get("class") not in FAMILIES or type(r.get("generation")) is not int or r["generation"]!=current_generation for r in face_families.values()):
            raise ValueError("Face families must cover the current mesh with immediate-generation origin records.")
    backend=mesh.subdivided(scheme="doosabin",k=1)
    if backend.number_of_vertices()!=estimate["estimated_output_vertices"] or backend.number_of_faces()!=estimate["estimated_output_faces"]:
        raise ValueError("Unexpected COMPAS Doo-Sabin growth.")
    children={}; pending=[]; vertex_parents={}; corner_parents={}; points=[]; fallback=[]
    backend_faces=list(backend.faces())
    output=Mesh()
    for index,f in enumerate(faces):
        old=mesh.face_vertices(f); new=backend.face_vertices(backend_faces[index])
        if len(old)!=len(new):
            raise ValueError("COMPAS source-face corner correspondence changed.")
        family=face_families[f]["class"] if face_families is not None else "SOURCE_FACE"
        suffix=SUFFIX[family] if family in SUFFIX else "face"
        requested=dict(w1=values["w1_"+suffix],w10=values["w10_"+suffix])
        supported=len(old) in (3,4)
        effective=requested if supported else dict(w1=0.0,w10=0.0)
        normal=mesh.face_normal(f)
        if any(not isfinite(n) for n in normal) or (effective["w10"] and hypot(*normal)==0):
            raise ValueError("Undefined face normal for requested DS extrusion.")
        if not supported:
            fallback.append(dict(generation=current_generation+1,face=f,valence=len(old),family=family,
                reason="Unsupported weighted polygon: actual COMPAS STANDARD placement, no extrusion",requested=requested))
        coordinates=mesh.face_coordinates(f)
        for corner,(v,child) in enumerate(zip(old,new)):
            if child in corner_parents:
                raise ValueError("COMPAS face-corner identities are not distinct.")
            xyz=(backend.vertex_coordinates(child) if not effective["w1"] and not effective["w10"] else
                 weighted_corner(coordinates,corner,normal,**effective))
            if not all(isfinite(x) for x in xyz):
                raise ValueError("Weighted DS produced non-finite coordinates.")
            output.add_vertex(key=child,x=xyz[0],y=xyz[1],z=xyz[2])
            children[f,v]=child; corner_parents[child]=v
            coefficients=_sampling_coefficients(len(old),corner)
            vertex_parents[child]=[ParentRef(parent,w) for parent,w in zip(old,coefficients)]
            points.append(dict(id=child,source_face=f,source_corner=v,input_family=family,
                requested=requested,effective=effective,weighted_supported=supported))
        pending.append((FACE_DERIVED,f,list(new),[f]))
    for v in mesh.vertices():
        incident=mesh.vertex_faces(v,ordered=True)
        pending.append((VERTEX_DERIVED,v,[children[f,v] for f in reversed(incident)],incident))
    for u,v in mesh.edges():
        a,b=mesh.halfedge[u][v],mesh.halfedge[v][u]
        pending.append((EDGE_DERIVED,[u,v],[children[a,u],children[b,u],children[b,v],children[a,v]],[a,b]))
    actual={_cycle(backend.face_vertices(f)):f for f in backend.faces()}
    if len(actual)!=len(pending) or set(actual)!={_cycle(corners) for _,_,corners,_ in pending}:
        raise ValueError("DS family construction does not match COMPAS oriented topology.")
    face_parents={}; origins={}
    for family,source,corners,parents in pending:
        key=actual[_cycle(corners)]
        output.add_face(corners,fkey=key,origin_class=family,origin_generation=current_generation+1)
        origins[key]=dict(class_=family,generation=current_generation+1,source=source)
        origins[key]["class"]=origins[key].pop("class_")
        face_parents[key]=[ParentRef(f,1/len(parents)) for f in parents]
    lineage=LineageMap(vertex_parents=vertex_parents,face_parents=face_parents)
    coverage=validate_lineage_coverage(mesh,output,lineage)
    if coverage or not output.is_valid() or not output.is_manifold() or not output.is_closed() or len(output.connected_vertices())!=len(mesh.connected_vertices()):
        raise ValueError("Unexpected DS output topology/lineage: "+" ".join(coverage))
    return DooSabinResult(output,dict(generation=current_generation+1,backend="COMPAS 2.15.1 public Mesh.subdivided(doosabin)",
        input=before,output=inspect_mesh(output),budget=assessment,weights=values,
        family_counts=dict(Counter(r["class"] for r in origins.values())),
        input_family_counts=dict(Counter(face_families[f]["class"] if face_families else "SOURCE_FACE" for f in faces)),
        fallback_faces=len(fallback),fallbacks=fallback,
        fallback_groups=[dict(valence=n,family=family,count=count) for (n,family),count in sorted(Counter((r["valence"],r["family"]) for r in fallback).items())],
        points=points,lineage_coverage=coverage,components_before=len(mesh.connected_vertices()),components_after=len(output.connected_vertices()),
        boundary_policy="Closed manifold only; open boundary and crease input rejected explicitly",
        seed_policy="No previous DS family: SOURCE_FACE uses the declared FACE pair; CC handoff is explicitly reseeded",
        source_association="Actual face/edge/vertex construction; positive STANDARD control-cage parents separate from signed weighted geometry",
        semantic_lineage="NOT IMPLEMENTED",elapsed_seconds=perf_counter()-started),lineage,origins,corner_parents)
