"""Task-19 experimental grammar. Existing operators and global budgets are untouched.

Topology ancestry is constructive. A mixed DS face keeps the union of event
ancestry, but only common role tokens qualify for strict descendant selection.
No geometric coefficient is misrepresented as a semantic interpolation weight.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass
from functools import lru_cache
from math import dist, fsum, hypot, isfinite, sqrt

from compas.datastructures import Mesh

from .execution import ExecutionBudget, check_execution_budget
from .lineage import LineageMap, ParentRef
from .mola import _check_mesh, _cross, _dot, _load_backend, _subtract
from .rules import Rule, evaluate_face_rule
from .subdivision import _require_bilinear_quad
from .validation import validate_lineage_coverage
from .generational_subdivision import generational_subdivide_once
from .weighted_doosabin import weighted_doosabin_once

OPERATORS = ("CC", "DS", "InsetFrame", "TaperedExtrusion")
SELECTOR_KEYS = {"z_min", "z_max", "normal_y_min", "area_ratio_min", "family", "role", "event_stage", "depth_min", "source_region"}


@dataclass(frozen=True)
class OrnamentStage:
    id: str
    operator: str
    parameters: dict
    selector: dict | None = None

    def __post_init__(self):
        if not self.id or self.operator not in OPERATORS:
            raise ValueError("Unknown ornament stage/operator.")
        if self.operator in OPERATORS[2:]:
            if self.selector is None or set(self.selector) - SELECTOR_KEYS:
                raise ValueError("Event selectors must use declared rules; face IDs are forbidden.")
        elif self.selector is not None:
            raise ValueError("Subdivision is global in this experiment.")
        allowed = {"CC": {"ratios", "schedule", "row"}, "DS": {"ratios", "schedule", "row"},
            "InsetFrame": {"width_ratio"}, "TaperedExtrusion": {"height_ratio", "fraction"}}[self.operator]
        if set(self.parameters)-allowed:
            raise ValueError("Undeclared stage parameter; manual face IDs are forbidden.")
        object.__setattr__(self, "parameters", deepcopy(self.parameters))
        object.__setattr__(self, "selector", deepcopy(self.selector))


@dataclass(frozen=True)
class OrnamentRecipe:
    id: str
    family: str
    mechanism: str
    stages: tuple[OrnamentStage, ...]

    def __post_init__(self):
        if not self.id or not self.mechanism or not self.stages or len({s.id for s in self.stages}) != len(self.stages):
            raise ValueError("Recipe requires unique stage IDs and an intended mechanism.")

    def to_data(self):
        return asdict(self)

    @classmethod
    def from_data(cls, data):
        return cls(data["id"], data["family"], data["mechanism"], tuple(OrnamentStage(**s) for s in data["stages"]))


def source_history(mesh):
    return {f: dict(source={f: 1.0}, events=(), roles=(), depth=0, operator_depth=0) for f in mesh.faces()}


def propagate_history(history, parents):
    """Positive control-cage ancestry; retain distinct mixed-event branches."""
    result = {}
    cache = {}
    for child, refs in parents.items():
        signature = tuple((p.key, p.weight) for p in refs)
        if signature in cache:
            result[child] = cache[signature]
            continue
        rows = [history[p.key] for p in refs]
        weights = {}
        for p, row in zip(refs, rows):
            for source, weight in row["source"].items():
                weights[source] = weights.get(source, 0.0) + p.weight*weight
        common = set(rows[0]["roles"])
        for row in rows[1:]:
            common.intersection_update(row["roles"])
        record = dict(source=weights, events=tuple(sorted(set().union(*(r["events"] for r in rows)))),
            roles=tuple(sorted(common)), depth=max(r["depth"] for r in rows),
            operator_depth=max(r["operator_depth"] for r in rows)+1)
        cache[signature] = record
        result[child] = record
    return result


def local_polygon(mesh, face):
    """Explicit nonplanar contract: convex projected tri/quad, admissible bilinear quad.

    Retain all source XYZ. Mola uses its first-triangle normal for extrusion.
    No projection, triangulation or repair is performed on the mesh.
    """
    keys = mesh.face_vertices(face)
    if len(keys) not in (3, 4) or len(set(keys)) != len(keys):
        raise ValueError("Only distinct triangle/quad event faces are verified.")
    xyz = mesh.face_coordinates(face)
    center = [fsum(p[a] for p in xyz)/len(xyz) for a in range(3)]
    scale = max(dist(p, center) for p in xyz)
    if not isfinite(scale) or scale <= 0:
        raise ValueError("Degenerate local scale.")
    local = [[(p[a]-center[a])/scale for a in range(3)] for p in xyz]
    normal = _cross(_subtract(local[1], local[0]), _subtract(local[2], local[0]))
    length = hypot(*normal)
    if length < 1e-9:
        raise ValueError("Degenerate first-triangle normal.")
    normal = [v/length for v in normal]
    for i, p in enumerate(local):
        if _dot(_cross(_subtract(p,local[i-1]),_subtract(local[(i+1)%len(local)],p)),normal) <= 1e-9:
            raise ValueError("Nonconvex/degenerate projected event face.")
    if len(local)==4:
        _require_bilinear_quad([_subtract(p,local[0]) for p in local], face)
    area2 = fsum(_dot(_cross(p,local[(i+1)%len(local)]),normal) for i,p in enumerate(local))
    return keys, center, scale, local, normal, sqrt(area2/2)


@lru_cache(maxsize=1)
def _inset_backend(dll_path):
    _, metadata = _load_backend(dll_path)
    import clr
    from System import Array, Object, Single
    assembly = clr.AddReference(dll_path)
    vec = assembly.GetType("Mola.Vec3", True)
    ctor = next(c for c in vec.GetConstructors() if [str(p.ParameterType.FullName) for p in c.GetParameters()]==["System.Single"]*3)
    method = next(m for m in assembly.GetType("FaceSubdivision",True).GetMethods() if m.Name=="Offset" and
        [str(p.ParameterType.FullName) for p in m.GetParameters()]==["Mola.Vec3[]","System.Single"])
    def execute(points, width):
        vectors = Array.CreateInstance(vec,len(points))
        for i,p in enumerate(points):
            vectors.SetValue(ctor.Invoke(Array[Object]([Single(v) for v in p])), i)
        faces = method.Invoke(None,Array[Object]([vectors,Single(-width)]))
        return [[[float(vec.GetField(a).GetValue(p)) for a in ("x","y","z")] for p in face] for face in faces]
    return execute, {**metadata,"inset_signature":str(method)}


def select_event_faces(mesh, history, selector, source, families=None):
    """Existing Rule handles centroid height; explicit family/role/area gates follow."""
    if set(selector)-SELECTOR_KEYS:
        raise ValueError("Undeclared selector or manual face IDs.")
    xyz = [source.vertex_coordinates(v) for v in source.vertices()]
    z0 = min(p[2] for p in xyz); height = max(p[2] for p in xyz)-z0
    rule = Rule("ornament-height", "normalized_source_height", "face", "between",
        selector.get("z_min",0), selector.get("z_max",1.5))
    allowed = set(evaluate_face_rule(mesh,{v:(mesh.vertex_coordinates(v)[2]-z0)/height for v in mesh.vertices()},rule)["selected_keys"])
    mean_area = fsum(mesh.face_area(f) for f in mesh.faces())/mesh.number_of_faces()
    selected, excluded = [], []
    for f in mesh.faces():
        row=history[f]; reason=None
        if f not in allowed: reason="height Rule"
        elif abs(mesh.face_normal(f)[1]) < selector.get("normal_y_min",0): reason="normal orientation"
        elif mesh.face_area(f) < mean_area*selector.get("area_ratio_min",0): reason="relative area"
        elif row["depth"] < selector.get("depth_min",0): reason="ornament depth"
        elif selector.get("family") and (families or {}).get(f,{}).get("class")!=selector["family"]: reason="subdivision family"
        elif selector.get("role") and (selector["event_stage"],selector["role"]) not in row["roles"]: reason="strict common descendant role"
        elif selector.get("source_region"):
            region=selector["source_region"]
            centers=[source.face_centroid(k) for k in row["source"]]
            is_lintel=all(p[2]>=z0+.74*height for p in centers)
            if (region=="lintel" and not is_lintel) or (region=="supports" and is_lintel): reason="C0 source-region ancestry"
            elif region not in ("lintel","supports"): raise ValueError("Unknown source region.")
        if reason is None:
            try: local_polygon(mesh,f)
            except ValueError as error: reason=str(error)
        if reason: excluded.append(dict(id=f,reason=reason))
        else: selected.append(f)
    return dict(rule=asdict(rule),selector=deepcopy(selector),selected_ids=selected,excluded=excluded,
        excluded_counts=dict(Counter(r["reason"] for r in excluded)))


def topology_event(mesh, history, stage, *, selected_faces, dll_path, budget, families=None, stage_index=1):
    """Selected parent disks replaced with Mola's ordered sides+cap, never welded.

    Offset sampling parents identify the constructive corner, not offset XYZ.
    Taper sampling parents identify the positive inset cage before normal offset.
    """
    _check_mesh(mesh)
    selected=list(selected_faces)
    if len(set(selected))!=len(selected) or not set(selected)<=set(mesh.faces()):
        raise ValueError("Invalid event selection.")
    if stage.operator not in OPERATORS[2:]: raise ValueError("Not a topology event.")
    growth=sum(len(mesh.face_vertices(f)) for f in selected)
    assessment=check_execution_budget(budget,input_faces=mesh.number_of_faces(),input_vertices=mesh.number_of_vertices(),
        estimated_output_faces=mesh.number_of_faces()+growth,estimated_output_vertices=mesh.number_of_vertices()+growth,current_generation=stage_index-1)
    if assessment["status"]!="SAFE": raise ValueError("Event budget: "+" ".join(assessment["reasons"]))
    output=Mesh(); vertex_parents={}; face_parents={}; corner_parents={}; roles={}; events=[]
    for v in mesh.vertices():
        x,y,z=mesh.vertex_coordinates(v); output.add_vertex(key=v,x=x,y=y,z=z)
        vertex_parents[v]=[ParentRef(v,1.0)]; corner_parents[v]=v
    chosen=set(selected)
    for f in mesh.faces():
        if f not in chosen:
            output.add_face(mesh.face_vertices(f),fkey=f); face_parents[f]=[ParentRef(f,1.0)]
    next_v=max(mesh.vertices(),default=-1)+1; next_f=max(mesh.faces(),default=-1)+1
    for f in selected:
        keys,center,scale,local,normal,area_length=local_polygon(mesh,f); n=len(keys)
        if stage.operator=="TaperedExtrusion":
            height=stage.parameters["height_ratio"]; fraction=stage.parameters["fraction"]
            if not 0<height<=.5 or not 0<fraction<.9: raise ValueError("Conservative taper range required.")
            execute,backend=_load_backend(dll_path)
            raw=execute(local,height*area_length,fraction)
            oracle=[[(1-fraction)*p[a]+height*area_length*normal[a] for a in range(3)] for p in local]
            side_role,cap_role="EXTRUSION_SIDE","EXTRUSION_CAP"
        else:
            width=stage.parameters["width_ratio"]
            if not 0<width<=.2: raise ValueError("Inset width_ratio must be in (0,.2].")
            execute,backend=_inset_backend(dll_path)
            raw=execute(local,width*min(dist(p,local[(i+1)%n]) for i,p in enumerate(local)))
            oracle=None; side_role,cap_role="FRAME_SIDE","INNER_CAP"
        if len(raw)!=n+1 or len(raw[-1])!=n or any(len(side)!=4 for side in raw[:-1]):
            raise ValueError("Mola returned unexpected side/cap topology.")
        upper=raw[-1]
        if any(not isfinite(v) for face in raw for p in face for v in p): raise ValueError("Nonfinite Mola output.")
        if oracle and any(dist(p,q)>3e-6 for p,q in zip(upper,oracle)):
            raise ValueError("Mola first-triangle-normal taper oracle mismatch.")
        for i,side in enumerate(raw[:-1]):
            expected=[local[i],local[(i+1)%n],upper[(i+1)%n],upper[i]]
            if any(dist(p,q)>3e-6 for p,q in zip(side,expected)):
                raise ValueError("Mola side order/shared cap-corner contract failed.")
        # Reject collapsed/reversed caps and oversized offsets; no fixing.
        for i,p in enumerate(upper):
            if _dot(_cross(_subtract(p,upper[i-1]),_subtract(upper[(i+1)%n],p)),normal)<=1e-9:
                raise ValueError("Mola cap reverses/collapses.")
        if stage.operator=="InsetFrame":
            for p in upper:
                if any(_dot(_cross(_subtract(local[(i+1)%n],q),_subtract(p,q)),normal)<-3e-6 for i,q in enumerate(local)):
                    raise ValueError("Inset cap escapes projected convex source boundary.")
        top=[]
        for i,p in enumerate(upper):
            key=next_v; next_v+=1; top.append(key)
            xyz=[center[a]+scale*p[a] for a in range(3)]
            output.add_vertex(key=key,x=xyz[0],y=xyz[1],z=xyz[2]); corner_parents[key]=keys[i]
            vertex_parents[key]=([ParentRef(v,fraction/n+(1-fraction if v==keys[i] else 0)) for v in keys]
                if stage.operator=="TaperedExtrusion" else [ParentRef(keys[i],1.0)])
        event_id=f"{stage.id}:parent:{f}"
        children=[]
        for i in range(n+1):
            cycle=[keys[i],keys[(i+1)%n],top[(i+1)%n],top[i]] if i<n else top
            child=next_f; next_f+=1; output.add_face(cycle,fkey=child)
            face_parents[child]=[ParentRef(f,1.0)]
            roles[child]=(stage.id,side_role if i<n else cap_role)
            children.append(dict(id=child,role=roles[child][1]))
        parent=history[f]
        events.append(dict(id=event_id,stage=stage.id,stage_index=stage_index,operator=stage.operator,parent_face=f,
            source_C0_ancestry=parent["source"],parent_family=(families or {}).get(f),
            parent_event_ids=parent["events"],ornament_depth=parent["depth"]+1,children=children))
    lineage=LineageMap(vertex_parents,face_parents)
    problems=validate_lineage_coverage(mesh,output,lineage)
    if problems: raise ValueError("Event lineage: "+" ".join(problems))
    _check_mesh(output)
    if output.is_closed()!=mesh.is_closed() or len(output.connected_vertices())!=len(mesh.connected_vertices()):
        raise ValueError("Event altered boundary/components unexpectedly.")
    next_history=propagate_history(history,face_parents)
    for event in events:
        for child in event["children"]:
            key=child["id"]; row=next_history[key]
            next_history[key]={**row,"events":tuple(sorted((*row["events"],event["id"]))),
                "roles":tuple(sorted((*row["roles"],roles[key]))),"depth":event["ornament_depth"]}
    return dict(mesh=output,history=next_history,lineage=lineage,events=events,corner_parents=corner_parents,
        backend=backend if selected else None,assessment=assessment)


def depth_diagnostics(history, events):
    regions={str(d):sorted({s for row in history.values() if row["depth"]>=d for s in row["source"]}) for d in (1,2,3)}
    roots={e["id"] for e in events if not e["parent_event_ids"]}
    nested={p for e in events if e["ornament_depth"]>=2 for p in e["parent_event_ids"] if p in roots}
    return dict(maximum=max((r["depth"] for r in history.values()),default=0),
        face_counts=dict(sorted(Counter(r["depth"] for r in history.values()).items())),source_regions_at_least=regions,
        event_count=len(events),event_depth_counts=dict(Counter(e["ornament_depth"] for e in events)),
        independent_nested_trees=len(nested),operator_lineage_depth=max((r["operator_depth"] for r in history.values()),default=0))


def run_ornament(source, recipe, *, dll_path, budget, publish=None, routing=None):
    """Serial deterministic grammar; caller retains each completed checkpoint.

    CC/DS stencil equations are reused verbatim. Event-created faces inherit
    a parent's existing DS routing label; that is recorded as inheritance,
    never claimed to be a newly constructed DS family. CC new event vertices
    have no invented point class, so unsupported later stencils report fallback.
    """
    original=deepcopy(source.__data__)
    mesh=source; history=source_history(source); events=[]; families=None; origins=None
    anchors={v:v for v in source.vertices()}; generation=0; stages=[]
    for index,stage in enumerate(recipe.stages,1):
        record=dict(stage=stage.to_data() if hasattr(stage,"to_data") else asdict(stage),stage_index=index)
        try:
            if stage.operator in ("CC","DS"):
                scale=fsum(dist(mesh.vertex_coordinates(u),mesh.vertex_coordinates(v)) for u,v in mesh.edges())/mesh.number_of_edges()
                ratios=stage.parameters["ratios"]
                weights={k:v*scale if k in ("wf","we","wp") or k.startswith("w10_") else v for k,v in ratios.items()}
                if stage.operator=="CC":
                    step=generational_subdivide_once(mesh,weights,origin_lineage=origins,budget=budget,current_generation=generation)
                    origins=step.origin_lineage; families=None
                    parents={r["id"]:[ParentRef(r["source_face"],1.0)] for r in step.metadata["face_sources"]}
                    vertex_parents={v:[ParentRef(k,w) for k,w in rows] for v,rows in step.sampling_parents.items()}
                    next_anchors={v:anchors.get(v) for v in step.mesh.vertices()}
                else:
                    step=weighted_doosabin_once(mesh,weights,face_families=families,budget=budget,current_generation=generation)
                    parents=step.lineage.face_parents; vertex_parents=step.lineage.vertex_parents
                    families=step.face_families; origins=None
                    next_anchors={v:anchors.get(p) for v,p in step.corner_parents.items()}
                history=propagate_history(history,parents); generation+=1
                record.update(global_mean_edge_length=scale,effective_weights=weights,
                    fallback_faces=step.metadata.get("fallback_faces",0),fallback_groups=step.metadata.get("fallback_groups",[]),
                    seed_policy=step.metadata.get("seed_policy"),later_classification=step.metadata.get("later_generation"))
                mesh=step.mesh
            else:
                selection=(routing.select(mesh,history,stage,source,families,events)
                    if routing is not None and routing.handles(stage.id) else
                    select_event_faces(mesh,history,stage.selector,source,families))
                record["selection"]=selection
                if not selection["selected_ids"] and not selection.get("quiet_if_empty",False):
                    raise ValueError("Empty deterministic event selector; no ornament generated.")
                step=topology_event(mesh,history,stage,selected_faces=selection["selected_ids"],dll_path=dll_path,
                    budget=budget,families=families,stage_index=index)
                parents=step["lineage"].face_parents; vertex_parents=step["lineage"].vertex_parents
                if not selection["selected_ids"]:
                    # A declared branch may have no eligible faces. This is an
                    # explicit quiet action, preserving history and routing labels.
                    step["history"]=history
                    step["mesh"]=mesh
                    record["quiet"]=True
                if families is not None and selection["selected_ids"]:
                    families={f:{**families[refs[0].key],"inherited_through_event":stage.id} for f,refs in parents.items()}
                next_anchors={v:anchors.get(p) for v,p in step["corner_parents"].items()}
                mesh=step["mesh"]; history=step["history"]; events.extend(step["events"])
                record.update(backend=step["backend"],events=step["events"],budget=step["assessment"])
            anchors=next_anchors
            record.update(subdivision_generation=generation,ornament=depth_diagnostics(history,events))
            if publish: publish(mesh,history,events,anchors,parents,vertex_parents,record)
            stages.append(record)
        except (ValueError,ArithmeticError) as error:
            record["failure"]=str(error); stages.append(record)
            return dict(status="TECHNICAL_STOP",reason=f"{stage.id}: {error}",mesh=mesh,history=history,events=events,
                stages=stages,source_immutable=source.__data__==original)
    if source.__data__!=original: raise AssertionError("Source mutated.")
    return dict(status="SUCCESS",reason="All declared stages completed",mesh=mesh,history=history,events=events,
        stages=stages,source_immutable=True)
