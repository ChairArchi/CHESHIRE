"""Standalone fixed-scale mesh section figures; plotting only, no CHESHIRE runtime imports."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


def plot(data,output,baseline=None):
    with np.load(data) as z:d={k:z[k].copy() for k in z.files}
    fig,axes=plt.subplots(3,3,figsize=(15,11),constrained_layout=True)
    colours=['#27688a','#dc8240','#803d6c']
    for row,s in enumerate([.06531,.15031,.24531]):
        ax=axes[row,0]
        for label,c in zip(['macro','meso','final'],colours):
            p=d[f's{s}_{label}'];ax.plot(p[:,0],p[:,1],label=label,color=c,lw=1.4)
        ax.set(xlim=(-1,1),ylim=(-30,900),xlabel='Material section u',ylabel='Actual mesh depth (project units)',title=f'Same material cut s={s:.5f}')
        ax.grid(alpha=.2);ax.legend(frameon=False,fontsize=9)
        ax=axes[row,1]
        for label,c in zip(['macro','meso','final'],colours):
            p=d[f's{s}_{label}'];ax.plot(p[:,0],p[:,1],label=label,color=c,lw=1.5)
        ax.set(xlim=(-.35,.35),ylim=(100,900),xlabel='Material section u (fixed magnification)',ylabel='Actual mesh depth',title='Nested fold detail; identical axes')
        ax.grid(alpha=.2)
        ax=axes[row,2];height=[650,1300,2200][row]
        paths=[(d,'#803d6c','Task33')]
        if baseline:
            with np.load(baseline) as b:paths.insert(0,({k:b[k] for k in b.files},'#77828c','Task31 G5'))
        for values,c,label in paths:
            seg=values['world_z'+str(height)]
            seg=seg[np.all(seg[:,:,0]<-400.036865234375,axis=1)]
            seg=seg[:,:,[0,1]].copy();seg[:,:,0]+=1950.036865234375;seg[:,:,1]+=18.533447265625
            ax.add_collection(LineCollection(seg,colors=c,lw=.9,label=label))
        ax.set(xlim=(-900,900),ylim=(-1400,1400),aspect='equal',xlabel='X relative to left support',ylabel='Y relative to input plane',title=f'Actual world-plane section Z={height}')
        ax.grid(alpha=.2);ax.legend(frameon=False,fontsize=9)
    fig.suptitle('Task33 — actual triangle cuts, nested folds and Task31 comparison\nMaterial cuts can be nonplanar; world Z cuts at right are planar. Original project units remain unresolved.',fontsize=14)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    for suffix in ['.png','.pdf']:
        target=output.with_suffix(suffix)
        if target.exists():raise FileExistsError(target)
        fig.savefig(target,dpi=200,facecolor='white')
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--baseline',type=Path);a=p.parse_args()
    plot(a.data,a.output,a.baseline)
