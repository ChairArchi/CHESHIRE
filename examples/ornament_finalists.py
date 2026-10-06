"""Explicit visually reviewed finalist/refinement recipes, no face picking."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"examples"))
from subdivision_capability_study import read,write
from ornament_recipes import event,sub
from cheshire.ornament import OrnamentRecipe,OrnamentStage

STUDY=ROOT/"output/task19/study"

def finalists(names):
    decisions=[]
    for name in names:
        original=OrnamentRecipe.from_data(read(STUDY/"recipes"/(name+".json")))
        stages=list(original.stages)
        last=[s for s in stages if s.operator in ("InsetFrame","TaperedExtrusion")][-1]
        number=int(last.id.split("_")[1])+1
        # A09 intentionally retains the incompatible DS -> CC boundary.
        # B07 already exceeds screening budget; one deeper declared finish suffices.
        if name not in ("A09","B07"):
            last_role="INNER_CAP" if last.operator=="InsetFrame" else "EXTRUSION_CAP"
            next_op="TaperedExtrusion" if last.operator=="InsetFrame" else "InsetFrame"
            stages.append(event(number,next_op,role=last_role,parent=number-1,area=0,width=.07,height=.10,fraction=.4))
            scheme=stages[-2].operator
            # Depth-three screens already carry fine detail; retain a new fourth
            # event unsmoothed rather than multiplying it into denser repetition.
            if number<=3:
                stages.append(sub(scheme,6,scheme+"_STANDARD",label="deep_finish"))
        recipe=OrnamentRecipe("F_"+name,original.family,original.mechanism+" Deep comparison adds one explicit descendant scale where budgets permit.",tuple(stages))
        write(STUDY/"recipes"/(recipe.id+".json"),recipe.to_data())
        decisions.append(dict(id=recipe.id,parent=name,reason="Visual morphology/structural diversity and explicit ancestry; no metric ranking",
            deep_change="Retain observed boundary" if name=="A09" else "Complete screened budget-limited finish" if name=="B07" else "Additional descendant event plus one standard finish",
            maximum_faces=250000))
    write(STUDY/"finalist_decision.json",decisions)

def refinements(names):
    decisions=[]
    for name in names:
        original=read(STUDY/"recipes"/(name+".json"))
        # Three local readable alternatives, not a Cartesian sweep.
        for variant in ("RETAIN_TERMINAL_EVENT","BOLDER_MESO","WIDER_NESTED_FRAME"):
            data=deepcopy(original); data["id"]=name+"_"+variant
            if variant=="RETAIN_TERMINAL_EVENT":
                if data["stages"][-1]["operator"] in ("CC","DS"): data["stages"].pop()
                elif data["stages"][-2]["operator"] in ("CC","DS"): data["stages"].pop(-2)
                data["mechanism"]+=" Omit the last subdivision surrounding the terminal event to test detail erasure."
            elif variant=="BOLDER_MESO":
                for s in data["stages"]:
                    if s["operator"]=="TaperedExtrusion":
                        s["parameters"]["height_ratio"]=min(.40,s["parameters"]["height_ratio"]*1.5)
                        s["parameters"]["fraction"]=max(.18,s["parameters"]["fraction"]-.08)
                data["mechanism"]+=" Increase taper height modestly and retain wider caps at all declared scales."
            else:
                for s in data["stages"]:
                    if s["operator"]=="InsetFrame" and s["id"]!="event_1":
                        s["parameters"]["width_ratio"]=min(.18,s["parameters"]["width_ratio"]*1.5)
                data["mechanism"]+=" Widen only descendant inset frames to test meso/micro separation."
            recipe=OrnamentRecipe.from_data(data); write(STUDY/"recipes"/(recipe.id+".json"),recipe.to_data())
            decisions.append(dict(id=recipe.id,parent=name,change=variant))
    write(STUDY/"refinement_decision.json",decisions)

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--finalists",nargs="+"); parser.add_argument("--refine",nargs="+")
    args=parser.parse_args()
    if args.finalists: finalists(args.finalists)
    elif args.refine: refinements(args.refine)
    else: parser.error("Choose finalists or refinements after reviewing actual outputs")
