import argparse,json
from pathlib import Path
from gateflow.pipeline import run
p=argparse.ArgumentParser(description="ALICE -> CHESHIRE reusable operator runner")
p.add_argument("--input",required=True,type=Path,help="ALICE atlas.json, or a gate exchange directory with structural semantics")
p.add_argument("--config",type=Path,default=Path(__file__).parent/"configs/default.json")
p.add_argument("--output",required=True,type=Path,help="New run directory; overwrites refused")
p.add_argument("--seed",type=int)
p.add_argument("--no-render",action="store_true")
a=p.parse_args()
r=run(a.input,json.loads(a.config.read_text()),a.output,a.seed,a.no_render)
print(json.dumps({"status":r["status"],"output":str(a.output),"final":r["final"]}))
