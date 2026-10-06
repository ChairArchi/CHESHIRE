"""Task-20 data-driven sibling routing; all geometry uses verified Task-19 words."""
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import fsum, isfinite

from .ornament import (OrnamentRecipe, OrnamentStage, SELECTOR_KEYS,
    select_event_faces, run_ornament)

ROLES = {"FRAME_SIDE", "INNER_CAP", "EXTRUSION_SIDE", "EXTRUSION_CAP"}
FINISHES = {"FINISH_NONE", "FINISH_RESTRAINED_CC", "FINISH_RESTRAINED_DS"}
EXTRA_KEYS = {"depth", "parent_operator", "normal_axis", "normal_min", "normal_max", "normal_absolute", "area_ratio_max"}


def content_hash(data):
    return sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class BranchRule:
    id: str
    when: dict
    action: str
    parameters: dict

    def __post_init__(self):
        if not self.id or self.action not in {"quiet", "InsetFrame", "TaperedExtrusion"}:
            raise ValueError("Unknown branch action.")
        if set(self.when) - (SELECTOR_KEYS | EXTRA_KEYS):
            raise ValueError("Undeclared branch selector; manual face IDs are forbidden.")
        if self.when.get("role") not in ROLES or not self.when.get("event_stage"):
            raise ValueError("Branch routing requires a constructive stage/child role.")
        if "depth" in self.when and (type(self.when["depth"]) is not int or self.when["depth"] < 1):
            raise ValueError("Branch depth must be a positive integer.")
        if "normal_axis" in self.when and self.when["normal_axis"] not in ("x", "y", "z"):
            raise ValueError("Orientation uses a normalized world-axis dot product.")
        if self.when.get("normal_min", -1) > self.when.get("normal_max", 1):
            raise ValueError("Reversed orientation bounds.")
        if self.when.get("parent_operator") not in (None, "InsetFrame", "TaperedExtrusion"):
            raise ValueError("Unknown parent event operator.")
        if self.action == "quiet":
            if self.parameters:
                raise ValueError("Quiet has no geometry parameters.")
        else:
            OrnamentStage(self.id, self.action, self.parameters, {})
            values=list(self.parameters.values())
            if not values or not all(isinstance(v,(float,int)) and isfinite(v) for v in values):
                raise ValueError("Finite explicit event parameters required.")
        object.__setattr__(self, "when", deepcopy(self.when))
        object.__setattr__(self, "parameters", deepcopy(self.parameters))


@dataclass(frozen=True)
class BranchTable:
    id: str
    rules: tuple[BranchRule, ...]
    fallback: str = "quiet"

    def __post_init__(self):
        if not self.id or not self.rules or len({r.id for r in self.rules}) != len(self.rules):
            raise ValueError("BranchTable needs ordered, uniquely named rules.")
        if self.fallback != "quiet":
            raise ValueError("Explicit quiet fallback required.")

    def to_data(self):
        return asdict(self)

    @classmethod
    def from_data(cls, data):
        return cls(data["id"], tuple(BranchRule(**r) for r in data["rules"]), data["fallback"])


@dataclass(frozen=True)
class BranchingRecipe:
    id: str
    family: str
    mechanism: str
    backbone: dict
    backbone_stages: int
    steps: tuple[BranchTable | OrnamentStage, ...]
    finish_mode: str = "FINISH_NONE"
    finish: OrnamentStage | None = None

    def __post_init__(self):
        base=OrnamentRecipe.from_data(self.backbone)
        if not self.id or not self.mechanism or not 1 <= self.backbone_stages <= len(base.stages):
            raise ValueError("Exact serialized backbone and retained prefix required.")
        if self.finish_mode not in FINISHES:
            raise ValueError("Unknown finish policy.")
        expected={"FINISH_RESTRAINED_CC":"CC", "FINISH_RESTRAINED_DS":"DS"}.get(self.finish_mode)
        if (expected is None) != (self.finish is None) or (self.finish and self.finish.operator != expected):
            raise ValueError("FINISH_NONE has no finish; other policies allow exactly one declared stage.")
        if any(isinstance(s,OrnamentStage) and s.operator not in ("CC","DS") for s in self.steps):
            raise ValueError("All downstream topology events must be in a BranchTable.")
        names=[s.id for s in self.compile().stages]
        if len(names)!=len(set(names)):
            raise ValueError("Unique compiled stage IDs required.")
        object.__setattr__(self,"backbone",deepcopy(self.backbone))

    def to_data(self):
        return dict(id=self.id,family=self.family,mechanism=self.mechanism,
            backbone=deepcopy(self.backbone),backbone_sha256=content_hash(self.backbone),
            backbone_stages=self.backbone_stages,
            steps=[dict(kind="branch_table",**s.to_data()) if isinstance(s,BranchTable) else dict(kind="subdivision",**asdict(s)) for s in self.steps],
            finish_mode=self.finish_mode,finish=asdict(self.finish) if self.finish else None)

    @classmethod
    def from_data(cls,data):
        if content_hash(data["backbone"])!=data["backbone_sha256"]:
            raise ValueError("Frozen backbone hash mismatch.")
        steps=[]
        for s in data["steps"]:
            row={k:v for k,v in s.items() if k!="kind"}
            if s["kind"]=="branch_table": steps.append(BranchTable.from_data(row))
            elif s["kind"]=="subdivision": steps.append(OrnamentStage(**row))
            else: raise ValueError("Unknown grammar step.")
        return cls(data["id"],data["family"],data["mechanism"],data["backbone"],data["backbone_stages"],tuple(steps),
            data["finish_mode"],OrnamentStage(**data["finish"]) if data["finish"] else None)

    def compile(self):
        stages=list(OrnamentRecipe.from_data(self.backbone).stages[:self.backbone_stages])
        for step in self.steps:
            if isinstance(step,OrnamentStage): stages.append(step)
            else:
                active=[r for r in step.rules if r.action!="quiet"]
                if not active: raise ValueError("A table must declare an event route; fallback is quiet.")
                stages.extend(OrnamentStage(step.id+"__"+r.id,r.action,r.parameters,{}) for r in active)
        if self.finish: stages.append(self.finish)
        return OrnamentRecipe(self.id,self.family,self.mechanism,tuple(stages))


class BranchRouter:
    """Snapshot, first-match routing. A sibling round cannot consume its own output."""
    def __init__(self,recipe):
        self.tables={s.id:s for s in recipe.steps if isinstance(s,BranchTable)}
        self.stages={s.id+"__"+r.id:(s.id,r.id) for s in self.tables.values() for r in s.rules if r.action!="quiet"}
        self.allocations={}
        self.reports={}

    def handles(self,stage_id):
        return stage_id in self.stages

    def _allocate(self,table,mesh,history,source,families,events):
        available=set(mesh.faces()); assignments={}; report=[]
        event_operator={e["stage"]:e["operator"] for e in events}
        mean=fsum(mesh.face_area(f) for f in mesh.faces())/mesh.number_of_faces()
        for rule in table.rules:
            base={k:v for k,v in rule.when.items() if k in SELECTOR_KEYS}
            # Quiet routing still respects constructive roles but does not need
            # verified event-face eligibility; no geometry is attempted on it.
            selection=select_event_faces(mesh,history,base,source,families)
            matches=[]
            for f in selection["selected_ids"]:
                if f not in available: continue
                row=history[f]; w=rule.when
                if "depth" in w and row["depth"]!=w["depth"]: continue
                if "parent_operator" in w and event_operator.get(w["event_stage"])!=w["parent_operator"]: continue
                if "area_ratio_max" in w and mesh.face_area(f)>mean*w["area_ratio_max"]: continue
                if "normal_axis" in w:
                    component=mesh.face_normal(f)["xyz".index(w["normal_axis"])]
                    if w.get("normal_absolute",False): component=abs(component)
                    if not w.get("normal_min",-1)<=component<=w.get("normal_max",1): continue
                matches.append(f)
            available.difference_update(matches); assignments[rule.id]=matches
            report.append(dict(rule=asdict(rule),matched_ids=matches,eligibility_excluded=selection["excluded_counts"]))
        report.append(dict(fallback=table.fallback,matched_ids=sorted(available)))
        self.allocations[table.id]=assignments
        self.reports[table.id]=dict(table=table.to_data(),table_sha256=content_hash(table.to_data()),rules=report,
            semantics="First matching rule on the pre-round mesh; quiet fallback; eligibility exclusions are explicit.")

    def select(self,mesh,history,stage,source,families,events):
        table_id,rule_id=self.stages[stage.id]
        if table_id not in self.allocations:
            self._allocate(self.tables[table_id],mesh,history,source,families,events)
        selected=self.allocations[table_id][rule_id]
        if not set(selected)<=set(mesh.faces()): raise ValueError("Sibling snapshot face disappeared.")
        return dict(selected_ids=selected,quiet_if_empty=True,branch_routing=self.reports[table_id],rule_id=rule_id,
            excluded=[],excluded_counts={},selector="Serialized BranchTable")


class BranchSignatures:
    """Positive control-cage mixture of constructive paths, never a coordinate label.

    Fractions are lineage mass per face. Mixed DS faces retain all positive paths;
    they are not classified as a pure cap. Subdivision appends no token.
    """
    def __init__(self,source):
        self.faces={f:{():1.0} for f in source.faces()}
        self.event_counts=Counter()

    def advance(self,parents,stage):
        result={}; cache={}
        for child,refs in parents.items():
            key=tuple((p.key,p.weight) for p in refs)
            if key not in cache:
                row=defaultdict(float)
                for p in refs:
                    for path,weight in self.faces[p.key].items(): row[path]+=p.weight*weight
                cache[key]=dict(row)
            result[child]=cache[key]
        for event in stage.get("events",[]):
            parent=self.faces[event["parent_face"]]
            event["parent_branch_signatures"]=[dict(path=list(p),weight=w) for p,w in sorted(parent.items())]
            event_paths=set()
            for child in event["children"]:
                token=event["operator"]+":"+child["role"]
                result[child["id"]]={(*p,token):w for p,w in parent.items()}
                event_paths.update(result[child["id"]])
            self.event_counts.update(event_paths)
        self.faces=result

    def diagnostics(self,history,events):
        masses=defaultdict(float); presence=Counter(); regions=defaultdict(set)
        for face,paths in self.faces.items():
            for path,weight in paths.items():
                masses[path]+=weight; presence[path]+=1
                if path:
                    for source in history[face]["source"]: regions[source].add(path)
        ornament=fsum(w for p,w in masses.items() if p)
        rows=[dict(path=list(p),terminal_face_mass=w,terminal_face_presence=presence[p],events=self.event_counts[p]) for p,w in sorted(masses.items())]
        # Shared roots connected through positive parent mixtures are one event
        # component. Count roots separately rather than calling them disjoint.
        representatives={}; roots={}; nested=set()
        def find(k):
            while representatives[k]!=k:
                representatives[k]=representatives[representatives[k]]; k=representatives[k]
            return k
        for e in events:
            parents=e["parent_event_ids"]
            branch=set().union(*(roots[k] for k in parents)) if parents else {e["id"]}
            roots[e["id"]]=branch
            for k in branch: representatives.setdefault(k,k)
            if parents:
                nested.update(branch); first=min(branch)
                for k in branch: representatives[find(k)]=find(first)
        return dict(unique_branch_signatures=sum(bool(p) for p in masses),signatures=rows,
            dominant_signature_fraction=max((w for p,w in masses.items() if p),default=0)/ornament if ornament else 0,
            ornament_face_mass=ornament,maximum_branch_depth=max(map(len,masses),default=0),
            independent_nested_event_components=len({find(k) for k in nested}),nested_root_count=len(nested),
            source_C0_regions_with_multiple_signatures=sorted(s for s,paths in regions.items() if len(paths)>1),
            counting="Face mass uses positive control-cage lineage weights; presence and event counts overlap; empty path excluded from dominance.")

    def to_data(self):
        paths=sorted({p for rows in self.faces.values() for p in rows})
        ids={p:i for i,p in enumerate(paths)}
        return dict(paths=[list(p) for p in paths],faces={f:[[ids[p],w] for p,w in sorted(rows.items())] for f,rows in self.faces.items()})


def run_branching(source,recipe,*,dll_path,budget,publish=None):
    tracker=BranchSignatures(source); router=BranchRouter(recipe)
    def retain(mesh,history,events,anchors,parents,vertex_parents,stage):
        tracker.advance(parents,stage)
        stage["branches"]=tracker.diagnostics(history,events)
        if publish: publish(mesh,history,events,anchors,parents,vertex_parents,stage,tracker)
    result=run_ornament(source,recipe.compile(),dll_path=dll_path,budget=budget,publish=retain,routing=router)
    result.update(signatures=tracker,branch_tables=router.reports)
    return result
