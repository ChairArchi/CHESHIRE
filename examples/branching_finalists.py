"""Explicit promotions/local revisions after actual matched-geometry review."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"examples"))
from subdivision_capability_study import read,write
from branching_recipes import references
from cheshire.branching import BranchingRecipe

STUDY=ROOT/"output/task20/study"


def finalists(names):
    decisions=[]
    for name in names:
        data=read(STUDY/"recipes"/(name+".json")); data["id"]="F_"+name
        data["mechanism"]+=" Exact primary grammar replay with compact full checkpoint retention."
        BranchingRecipe.from_data(data)
        write(STUDY/"recipes"/(data["id"]+".json"),data)
        decisions.append(dict(id=data["id"],parent=name,change="No geometry parameter change; full downstream checkpoints",reason="Actual visual/branch/technical comparison, not face-count ranking"))
    write(STUDY/"finalist_decision.json",decisions)


def refine(names):
    decisions=[]
    for name in names:
        original=read(STUDY/"recipes"/(name+".json"))
        for variant in ("CONTRAST","QUIET_DOWN","STRONGER_TAPER"):
            data=deepcopy(original); data["id"]=name+"_"+variant; changed=[]
            for step in data["steps"]:
                if step["kind"]!="branch_table": continue
                for rule in step["rules"]:
                    if rule["action"]=="quiet": continue
                    if variant=="CONTRAST":
                        if rule["action"]=="TaperedExtrusion":
                            rule["parameters"].update(height_ratio=.26,fraction=.22)
                        else: rule["parameters"]["width_ratio"]=.12
                    elif variant=="QUIET_DOWN":
                        rule["when"].update(normal_axis="z",normal_absolute=False,
                            normal_min=max(0,rule["when"].get("normal_min",-1)) if rule["when"].get("normal_axis")=="z" else 0)
                        if rule["when"].get("normal_max",1)<rule["when"]["normal_min"]:
                            rule["action"]="quiet"; rule["parameters"]={}
                    elif rule["action"]=="TaperedExtrusion":
                        rule["parameters"]["fraction"]=.48
                    else: rule["parameters"]["width_ratio"]=.12
                    changed.append(dict(table=step["id"],rule=rule["id"],action=rule["action"],when=rule["when"],parameters=rule["parameters"]))
            data["mechanism"]+=f" Explicit local {variant} revision of descendants only; frozen backbone unchanged."
            BranchingRecipe.from_data(data); write(STUDY/"recipes"/(data["id"]+".json"),data)
            decisions.append(dict(id=data["id"],parent=name,change=variant,changed_rules=changed))
    write(STUDY/"refinement_decision.json",decisions)


def finish(names):
    results=[]
    for name in names:
        data=read(STUDY/"recipes"/(name+".json"))
        if data["finish_mode"]!="FINISH_NONE": raise ValueError("Identical no-finish input required.")
        data["id"]=name+"_ONE_DS"; data["finish_mode"]="FINISH_RESTRAINED_DS"
        data["finish"]={**deepcopy(references()["F_C06_BOLDER_MESO"]["stages"][5]),"id":"terminal_DS"}
        data["mechanism"]+=" Compare one exact saved standard DS terminal stage with the identical pre-finish result."
        BranchingRecipe.from_data(data); write(STUDY/"recipes"/(data["id"]+".json"),data)
        results.append(dict(id=data["id"],pre_finish=name,change="One exact C06 standard DS stage; no other change"))
    write(STUDY/"finish_decision.json",results)


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--finalists",nargs="+"); parser.add_argument("--refine",nargs="+"); parser.add_argument("--finish",nargs="+")
    args=parser.parse_args()
    if args.finalists: finalists(args.finalists)
    elif args.refine: refine(args.refine)
    elif args.finish: finish(args.finish)
    else: parser.error("Choose promotions or bounded local revisions after visual review")
