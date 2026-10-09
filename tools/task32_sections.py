"""Standalone Matplotlib section evidence from retained geometry-plane segments.

Requires the optional study-plots extra; never reads/modifies an active mesh.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plot(request,output):
    request=Path(request);output=Path(output)
    if output.suffix!='.png' or output.exists() or output.with_suffix('.pdf').exists():
        raise ValueError('Fresh PNG/PDF output required.')
    data=json.loads(request.read_text(encoding='utf-8'));items=data['items'];records=[]
    fig,axes=plt.subplots(len(items),3,figsize=(15,3.2*len(items)),squeeze=False,layout='constrained')
    columns=[('mid_depth',[0,2],(-2.8,2.0),(0,4.0),'X / 1000','Z / 1000'),
             ('z1300',[0,1],(-2.8,2.0),(-1.5,.5),'X / 1000','Y / 1000'),
             ('z3050',[0,1],(-2.8,2.0),(-1.5,.5),'X / 1000','Y / 1000')]
    for i,item in enumerate(items):
        path=Path(item['sections']);records.append(dict(**item,sha256=sha(path)))
        with np.load(path) as state:
            for j,(name,dims,xlim,ylim,xlabel,ylabel) in enumerate(columns):
                ax=axes[i,j];segments=state[name][:,:,dims]/1000
                ax.add_collection(LineCollection(segments,colors='#264765',linewidths=.65))
                ax.set(xlim=xlim,ylim=ylim,xlabel=xlabel,ylabel=ylabel,title=item['label']+' / '+name)
                ax.set_aspect('equal');ax.grid(alpha=.18)
    fig.suptitle('Actual geometry sections; shared axes within each column\nOriginal model coordinates / 1000; physical unit unresolved',fontsize=13)
    output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(output,dpi=180);fig.savefig(output.with_suffix('.pdf'));plt.close(fig)
    manifest=dict(items=records,request_sha256=sha(request),script_sha256=sha(__file__),
        renderer='Matplotlib line segments; no mesh repair, no smoothing or invented contours',
        matplotlib=importlib.metadata.version('matplotlib'),numpy=np.__version__,
        output_sha256=sha(output),pdf_sha256=sha(output.with_suffix('.pdf')))
    with output.with_suffix('.json').open('x',encoding='utf-8') as stream:json.dump(manifest,stream,indent=2)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();plot(a.request,a.output)
