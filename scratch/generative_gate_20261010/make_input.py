import argparse
from pathlib import Path
from gateflow.input import create_neutral
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
p.add_argument('--width',type=float,default=2.6);p.add_argument('--height',type=float,default=3.2);p.add_argument('--depth',type=float,default=.65);p.add_argument('--opening-width',type=float,default=1.4);p.add_argument('--opening-height',type=float,default=2.4)
a=p.parse_args();print(create_neutral(a.output,a.width,a.height,a.depth,a.opening_width,a.opening_height))
