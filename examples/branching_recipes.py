"""44 discrete Task-20 role grammars, loaded from exact Task-19 evidence."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"examples"))
from subdivision_capability_study import read
from cheshire.branching import BranchRule,BranchTable,BranchingRecipe
from cheshire.ornament import OrnamentStage


def references():
    rows=read(ROOT/"studies/task19/recipes.json")
    return {r["id"]:r for r in rows if r["id"] in ("F_C07_RETAIN_TERMINAL_EVENT","F_C06_BOLDER_MESO","F_B03")}


def primary_recipes():
    refs=references(); base=refs["F_C07_RETAIN_TERMINAL_EVENT"]
    c06=refs["F_C06_BOLDER_MESO"]; b03=refs["F_B03"]
    cc=OrnamentStage(**{**base["stages"][5],"id":"inter_CC"})
    ds=OrnamentStage(**{**c06["stages"][5],"id":"inter_DS"})
    ordered=OrnamentStage(**{**b03["stages"][4],"id":"ordered_DS"})
    handoff=OrnamentStage(**{**b03["stages"][2],"id":"ordered_handoff_DS"})
    result=[]
    def rule(id,role,action,parent="event_2",depth=2,**gates):
        when=dict(role=role,event_stage=parent,depth=depth,z_min=.08,z_max=1.3,**gates)
        parameters=({} if action=="quiet" else dict(width_ratio=.08) if action=="InsetFrame" else dict(height_ratio=.16,fraction=.30))
        return BranchRule(id,when,action,parameters)
    def table(id,*rules): return BranchTable(id,tuple(rules),"quiet")
    def add(family,index,text,steps,finish=None):
        mode="FINISH_NONE" if finish is None else "FINISH_RESTRAINED_"+finish.operator
        result.append(BranchingRecipe(f"{family}{index:02d}",family,text,base,5,tuple(steps),mode,finish))
    def split(cap="InsetFrame",side="TaperedExtrusion",**gates):
        return table("split",rule("cap","INNER_CAP",cap),rule("side","FRAME_SIDE",side,**gates))
    def cap_child(parent,first):
        return "INNER_CAP" if first=="InsetFrame" else "EXTRUSION_CAP"
    def descent(cap="InsetFrame",side="TaperedExtrusion",inverse=False):
        return table("descend",rule("cap_child",cap_child("split__cap",cap),"TaperedExtrusion" if cap=="InsetFrame" else "InsetFrame",parent="split__cap",depth=3),
            rule("side_child",cap_child("split__side",side),"InsetFrame" if side=="TaperedExtrusion" else "TaperedExtrusion",parent="split__side",depth=3))
    # A: siblings receive different words, different subsequent handoffs or quiet.
    add("A",1,"Inner caps become rings while frame sides become short fins; no finish.",[split()])
    add("A",2,"Inner caps rise while frame sides receive shallow inset tessellation; no finish.",[split("TaperedExtrusion","InsetFrame")])
    add("A",3,"Cap rings and side fins receive different terminal child actions directly.",[split(),descent()])
    add("A",4,"Inverse sibling actions descend through caps with complementary terminal words.",[split("TaperedExtrusion","InsetFrame"),descent("TaperedExtrusion","InsetFrame")])
    add("A",5,"Cap rings subdivide with exact C07 standard CC before micro caps; sides end as fins.",[split(),cc,table("micro",rule("cap","INNER_CAP","TaperedExtrusion",parent="split__cap",depth=3))])
    add("A",6,"Inverse split receives one standard DS handoff before terminal cap rings.",[split("TaperedExtrusion","InsetFrame"),ds,table("micro",rule("cap","EXTRUSION_CAP","InsetFrame",parent="split__cap",depth=3))])
    add("A",7,"Ring caps end quietly while side fins receive an additional inner frame.",[split(),table("micro",rule("side","EXTRUSION_CAP","InsetFrame",parent="split__side",depth=3))])
    add("A",8,"Primary cap rings and side fins compare one exact C07 standard CC finish.",[split()],OrnamentStage(**{**asdict(cc),"id":"terminal_CC"}))
    add("A",9,"Primary cap rings and side fins compare one standard DS finish.",[split()],OrnamentStage(**{**asdict(ds),"id":"terminal_DS"}))
    # B: depth-aware descent, never global alternation without a role predicate.
    add("B",1,"Depth-2 frame siblings split; only ring caps continue to depth-4 raised micro caps.",[split(),table("micro",rule("cap","INNER_CAP","TaperedExtrusion",parent="split__cap",depth=3))])
    add("B",2,"Depth-2 raised cap siblings split; extrusion caps gain rings at depth 4.",[split("TaperedExtrusion","InsetFrame"),table("micro",rule("cap","EXTRUSION_CAP","InsetFrame",parent="split__cap",depth=3))])
    add("B",3,"Depth-3 extrusion side descendants receive a small inset while caps terminate.",[split(),table("micro",rule("side","EXTRUSION_SIDE","InsetFrame",parent="split__side",depth=3))])
    add("B",4,"Depth-3 frame-side descendants of cap rings rise while inner caps stay quiet.",[split(),table("micro",rule("rim","FRAME_SIDE","TaperedExtrusion",parent="split__cap",depth=3))])
    add("B",5,"Inherited original extrusion sides stay at depth 1 and grow distinct flanking fins beside depth-3 cap rings.",[table("older",rule("flank","EXTRUSION_SIDE","TaperedExtrusion",parent="event_1",depth=1,normal_axis="z",normal_min=-.5,normal_max=.5)),split()])
    add("B",6,"Raised depth-3 caps branch into frames after CC while inset-side descendants terminate.",[split("TaperedExtrusion","InsetFrame"),cc,table("micro",rule("cap","EXTRUSION_CAP","InsetFrame",parent="split__cap",depth=3))])
    add("B",7,"Side fins descend through standard DS then cap frames; cap-ring branch stays quiet.",[split(),ds,table("micro",rule("side","EXTRUSION_CAP","InsetFrame",parent="split__side",depth=3))])
    add("B",8,"Both child routes remain visible at depth 4 without an intervening subdivision.",[split(),descent()],OrnamentStage(**{**asdict(ds),"id":"terminal_DS"}))
    add("B",9,"Depth-2 cap rings grow only upward frame-side micros while lateral fins stop.",[split(),table("micro",rule("rim","FRAME_SIDE","TaperedExtrusion",parent="split__cap",depth=3,normal_axis="z",normal_min=.25))])
    # C: broad world-axis classes couple geometric condition to constructive role.
    options=[("z",.25,1,"z",-.35,.35), ("z",-1,-.25,"z",-.35,.35),
        ("z",-.25,.25,"z",.25,1), ("x",-.35,.35,"x",.35,1),
        ("x",-.35,.35,"x",-1,-.35), ("y",.35,1,"z",-.35,.35),
        ("y",-1,-.35,"z",-.35,.35)]
    for i,(ca,lo,hi,sa,slo,shi) in enumerate(options,1):
        step=table("split",rule("cap","INNER_CAP","InsetFrame",normal_axis=ca,normal_min=lo,normal_max=hi),
            rule("side","FRAME_SIDE","TaperedExtrusion",normal_axis=sa,normal_min=slo,normal_max=shi))
        add("C",i,f"Cap {ca}-dot interval [{lo},{hi}] receives rings; frame-side {sa}-dot [{slo},{shi}] receives fins; all other siblings quiet.",[step,descent()])
    step=table("split",rule("cap","INNER_CAP","TaperedExtrusion",normal_axis="z",normal_absolute=True,normal_max=.4),
        rule("side","FRAME_SIDE","InsetFrame",normal_axis="z",normal_min=.25))
    add("C",8,"Lateral caps rise while upward side siblings remain angular frames.",[step])
    step=table("split",rule("up","INNER_CAP","InsetFrame",normal_axis="z",normal_min=.25),
        rule("down","INNER_CAP","quiet",normal_axis="z",normal_max=-.25),
        rule("oblique","INNER_CAP","TaperedExtrusion",normal_axis="z",normal_min=-.25,normal_max=.25),
        rule("side","FRAME_SIDE","TaperedExtrusion",normal_axis="z",normal_absolute=True,normal_max=.35))
    add("C",9,"Upward caps form rings, lateral caps rise, downward caps terminate, lateral frame sides form fins.",[step])
    # D: exact saved downstream DS rows, globally declared rather than invented local DS.
    for i,(middle,cap,side,nested,family) in enumerate([
        (ds,"InsetFrame","TaperedExtrusion",False,None),
        (ds,"TaperedExtrusion","InsetFrame",True,None),
        (ordered,"InsetFrame","TaperedExtrusion",False,None),
        (ordered,"TaperedExtrusion","InsetFrame",True,"FACE_DERIVED"),
        (handoff,"InsetFrame","TaperedExtrusion",True,"FACE_DERIVED"),
        (None,"InsetFrame","TaperedExtrusion",True,None),
        (None,"TaperedExtrusion","InsetFrame",True,None),
        (ds,"InsetFrame","quiet",True,"FACE_DERIVED"),
        (ordered,"quiet","TaperedExtrusion",False,None)],1):
        t=table("split",rule("cap","INNER_CAP",cap,**({"family":family} if family else {})),rule("side","FRAME_SIDE",side))
        steps=[middle,t] if middle else [t,ordered if i==6 else ds]
        if nested and cap!="quiet":
            # Import exact C06 event parameters, without interpolating schedules.
            r=rule("cap",cap_child("split__cap",cap),"TaperedExtrusion" if cap=="InsetFrame" else "InsetFrame",parent="split__cap",depth=3)
            parameters=deepcopy(c06["stages"][4 if r.action=="TaperedExtrusion" else 6]["parameters"])
            steps.append(table("micro",BranchRule(r.id,r.when,r.action,parameters)))
        add("D",i,f"Frozen C07 composes exact {middle.id if middle else 'inter-event DS'} with C06-like cap nesting and ordered quiet/side routes.",steps)
    # E: deliberate pruning, not random or field-generated variation.
    for i,(role,axis,lo,hi,area,second) in enumerate([
        ("INNER_CAP","z",.25,1,0,True),("INNER_CAP","z",-.25,.25,0,True),
        ("FRAME_SIDE","z",-.35,.35,0,True),("FRAME_SIDE","x",.35,1,0,False),
        ("INNER_CAP","y",-1,-.35,.8,True),("FRAME_SIDE","y",-1,-.35,.4,False),
        ("INNER_CAP","z",-1,1,1.2,True),("FRAME_SIDE","z",-1,1,.8,True)],1):
        action="InsetFrame" if role=="INNER_CAP" else "TaperedExtrusion"
        steps=[table("prune",rule("active",role,action,normal_axis=axis,normal_min=lo,normal_max=hi,area_ratio_min=area))]
        if second: steps.append(table("micro",rule("active",cap_child("prune__active",action),"TaperedExtrusion" if action=="InsetFrame" else "InsetFrame",parent="prune__active",depth=3)))
        add("E",i,f"Only {role} with {axis}-dot [{lo},{hi}] and relative area >= {area} continues; sibling roles stop explicitly.",steps)
    assert len(result)==44
    return result
