"""Standalone actual triangle-cut figures. No shape rendering or smoothing."""
import argparse,json,os
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


def plot(root,tag,audit,ids):
    dest=root/'plots'/tag;dest.mkdir(parents=True,exist_ok=False)
    colours=plt.get_cmap('viridis')(np.linspace(.1,.9,len(ids)))
    data=[dict(np.load(root/'validation'/audit/(i+'_cuts.npz'))) for i in ids]
    keys=['Z500','Z1000','Z1500','Z2000','Z2500','Z3000','Z3500','XZ','YZ','DIAGONAL']
    keys=[k for k in keys if k in data[0]]
    fig,axes=plt.subplots(2,5,figsize=(22,10));axes=axes.ravel()
    for ax,key in zip(axes,keys):
        for d,label,c in zip(data,ids,colours):
            lines=d[key]
            xy=lines[:,:,[0,1]] if key.startswith('Z') else lines[:,:,[0,2]] if key=='XZ' else lines[:,:,[1,2]] if key=='YZ' else np.stack([(lines[:,:,0]+lines[:,:,1])/2**.5,lines[:,:,2]],axis=-1)
            ax.add_collection(LineCollection(xy,colors=[c],linewidths=.65,label=label))
        ax.set_title(key+' | native triangle intersection');ax.set_aspect('equal');ax.autoscale();ax.grid(alpha=.15)
        if key.startswith('Z'):ax.set_xlim(-1600,1600);ax.set_ylim(-1600,1600)
        else:ax.set_xlim(-1700,1700);ax.set_ylim(0,4000)
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=3,fontsize=8)
    fig.suptitle('Fixed world sections; finite samples, no material-ancestry or continuous-ridge certificate')
    fig.tight_layout(rect=[0,.07,1,.96]);fig.savefig(dest/'ACTUAL_SECTIONS.png',dpi=160);fig.savefig(dest/'ACTUAL_SECTIONS.svg');plt.close(fig)
    (dest/'manifest.json').write_text(json.dumps(dict(audit=audit,ids=ids,geometry='Raw native triangle-plane segments; no profile smoothing.',python=os.sys.version),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('E:/CHESHIRE_DATA/task36'));p.add_argument('--tag',required=True);p.add_argument('--audit',required=True);p.add_argument('--ids',nargs='+',required=True);a=p.parse_args();plot(a.root,a.tag,a.audit,a.ids)
