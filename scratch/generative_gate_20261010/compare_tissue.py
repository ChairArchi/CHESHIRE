"""Run the same Tissue mapping with overlay, UNUSED, and LAST composition."""
import argparse
from gateflow import runtime
from gateflow.tissue_comparison import run
p=argparse.ArgumentParser()
p.add_argument('--target-stage',required=True)
p.add_argument('--mapping-stage',required=True)
p.add_argument('--input',required=True)
p.add_argument('--output',required=True)
a=p.parse_args()
r=run(a.target_stage,a.mapping_stage,a.input,a.output)
print(r['status'])
