"""36 structural Task-19 grammars, no arbitrary face IDs or parameter grid."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"rhino"))
from generational_study import choreographies, BEST_SCHEDULE
from subdivision_capability import refinements
from cheshire.ornament import OrnamentRecipe, OrnamentStage

CC=choreographies()[BEST_SCHEDULE]["schedule"]
DS={name:row["schedule"] for name,row in refinements().items() if name in ("R13_restrained_insets","R15_restrained_edge_frames")}

def sub(op,row=1,schedule=None,label=None):
    schedule=schedule or ("C11" if op=="CC" else "R15_restrained_edge_frames")
    ratios=({k:0.0 for k in CC[0]} if schedule=="CC_STANDARD" else
        {k:0.0 for k in DS["R15_restrained_edge_frames"][0]} if schedule=="DS_STANDARD" else
        CC[row-1] if op=="CC" else DS[schedule][row-1])
    return OrnamentStage(label or f"{op}_{row}",op,dict(schedule=schedule,row=row,ratios=ratios))

def event(number,op="InsetFrame",*,role=None,parent=1,family=None,width=.10,height=.18,fraction=.3,region=None,area=.5):
    selector=dict(z_min=.08,z_max=1.30,normal_y_min=.28,area_ratio_min=area)
    if role: selector.update(role=role,event_stage=f"event_{parent}",depth_min=1)
    if family: selector["family"]=family
    if region: selector["source_region"]=region
    parameters=dict(width_ratio=width) if op=="InsetFrame" else dict(height_ratio=height,fraction=fraction)
    return OrnamentStage(f"event_{number}",op,parameters,selector)

def primary_recipes():
    result=[]
    def add(family,index,mechanism,stages):
        result.append(OrnamentRecipe(f"{family}{index:02d}",family,mechanism,tuple(stages)))
    # The tuples express discrete handoff, descendant-role and finish choices.
    for i,(macro,middle,role,finish,region,width) in enumerate([
        (1,"CC","INNER_CAP","CC",None,.10),(2,"CC","INNER_CAP","CC",None,.10),
        (1,"DS","INNER_CAP","DS",None,.10),(2,"DS","INNER_CAP","DS",None,.10),
        (2,"CC","FRAME_SIDE","CC",None,.08),(2,"DS","FRAME_SIDE","DS",None,.08),
        (1,"CC","INNER_CAP","CC","lintel",.14),(2,"DS","INNER_CAP","DS","supports",.14),
        (2,"DS","INNER_CAP","CC",None,.20)],1):
        stages=[sub("CC",g,label=f"macro_CC_{g}") for g in range(1,macro+1)]
        stages += [event(1,width=width,region=region),sub(middle,macro+1 if middle=="CC" else 3,"CC_STANDARD" if middle=="CC" else None,label="articulation"),
            event(2,"TaperedExtrusion",role=role,area=0,height=.22 if role=="INNER_CAP" else .10),
            sub(finish,4,"CC_STANDARD" if finish=="CC" else "R15_restrained_edge_frames",label="finish")]
        add("A",i,f"C11 G{macro} masses contain inset frames; {middle} descendants of {role} receive a smaller tapered event before {finish} finish.",stages)
    for i,(macro,ds_count,family,op,ds_name,nested) in enumerate([
        (2,1,"FACE_DERIVED","TaperedExtrusion","R15_restrained_edge_frames",False),
        (2,1,"EDGE_DERIVED","TaperedExtrusion","R15_restrained_edge_frames",False),
        (2,1,"VERTEX_DERIVED","TaperedExtrusion","R15_restrained_edge_frames",False),
        (3,1,"FACE_DERIVED","InsetFrame","R13_restrained_insets",False),
        (3,1,"EDGE_DERIVED","InsetFrame","R13_restrained_insets",False),
        (3,1,"VERTEX_DERIVED","InsetFrame","R13_restrained_insets",False),
        (2,2,"FACE_DERIVED","InsetFrame","R15_restrained_edge_frames",True),
        (3,2,"EDGE_DERIVED","TaperedExtrusion","R13_restrained_insets",True),
        (2,2,"VERTEX_DERIVED","InsetFrame","R15_restrained_edge_frames",True)],1):
        stages=[sub("CC",g,label=f"macro_CC_{g}") for g in range(1,macro+1)]
        stages += [sub("DS",macro+g,ds_name,label=f"handoff_DS_{g}") for g in range(1,ds_count+1)]
        stages += [event(1,op,family=family,height=.16,area=.25),sub("DS",5,ds_name,label="articulation")]
        if nested:
            stages += [event(2,"TaperedExtrusion" if op=="InsetFrame" else "InsetFrame",
                role="INNER_CAP" if op=="InsetFrame" else "EXTRUSION_CAP",area=0,height=.12),
                sub("DS",6,ds_name,label="finish")]
        add("B",i,f"C11 G{macro} hands off to {ds_count} {ds_name} step(s); only {family} receives {op}, followed by descendant DS articulation.",stages)
    for i,(macro,first,middle,role,third,region) in enumerate([
        (1,"TaperedExtrusion","CC","EXTRUSION_CAP",False,None),
        (2,"TaperedExtrusion","CC","EXTRUSION_CAP",False,None),
        (1,"TaperedExtrusion","DS","EXTRUSION_CAP",False,None),
        (2,"TaperedExtrusion","DS","EXTRUSION_SIDE",False,None),
        (1,"InsetFrame","CC","INNER_CAP",True,None),
        (2,"InsetFrame","DS","INNER_CAP",True,None),
        (2,"TaperedExtrusion","CC","EXTRUSION_CAP",True,"lintel"),
        (1,"TaperedExtrusion","DS","EXTRUSION_CAP",True,"supports"),
        (2,"TaperedExtrusion","DS","EXTRUSION_CAP",True,None)],1):
        second="InsetFrame" if first=="TaperedExtrusion" else "TaperedExtrusion"
        stages=[sub("CC",g,label=f"macro_CC_{g}") for g in range(1,macro+1)]
        stages += [event(1,first,height=.26,width=.13,region=region),
            sub(middle,macro+1 if middle=="CC" else 3,"CC_STANDARD" if middle=="CC" else None,label="articulation"),event(2,second,role=role,area=0,height=.16,width=.08)]
        if third:
            stages += [sub(middle,4,"CC_STANDARD" if middle=="CC" else "DS_STANDARD",label="nested_articulation"),
                event(3,first,role="INNER_CAP" if second=="InsetFrame" else "EXTRUSION_CAP",parent=2,area=0,height=.10,width=.07)]
        stages += [sub(middle,5,"CC_STANDARD" if middle=="CC" else "R15_restrained_edge_frames",label="finish")]
        add("C",i,f"{first} on C11 G{macro} contains {middle} {role} descendants receiving the different {second} event"+(" and a third nested event." if third else "."),stages)
    for i,(macro,family,ds_name,middle,region,width) in enumerate([
        (1,"FACE_DERIVED","R15_restrained_edge_frames",True,None,.10),
        (2,"FACE_DERIVED","R15_restrained_edge_frames",True,None,.10),
        (2,"EDGE_DERIVED","R15_restrained_edge_frames",True,None,.08),
        (2,"VERTEX_DERIVED","R15_restrained_edge_frames",True,None,.08),
        (1,"FACE_DERIVED","R13_restrained_insets",True,None,.10),
        (2,"EDGE_DERIVED","R13_restrained_insets",True,None,.10),
        (2,"FACE_DERIVED","R15_restrained_edge_frames",False,"lintel",.14),
        (2,"FACE_DERIVED","R13_restrained_insets",False,"supports",.14),
        (3,"VERTEX_DERIVED","R15_restrained_edge_frames",True,None,.15)],1):
        stages=[sub("DS",g,ds_name,label=f"macro_DS_{g}") for g in range(1,macro+1)]
        stages += [event(1,family=family,width=width,region=region,area=.25)]
        if middle: stages += [sub("DS",min(macro+1,4),ds_name,label="articulation")]
        stages += [event(2,"TaperedExtrusion",role="INNER_CAP",area=0,height=.18,fraction=.4),
            sub("DS",5,ds_name,label="finish")]
        add("D",i,f"{ds_name} G{macro} {family} frames contain tapered inner-cap ornaments with {'intervening DS' if middle else 'direct role recursion'} and restrained DS finish.",stages)
    return result

if __name__=="__main__":
    import json
    print(json.dumps([r.to_data() for r in primary_recipes()],indent=2))
