"""Publication/export plots from Task34 native segments, without geometric edits."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


def plots(analysis):
    analysis=Path(analysis);report=json.loads((analysis/'measurements.json').read_text());stages=report['stages']
    dest=analysis/'figures';dest.mkdir(exist_ok=False)
    # The same data coordinates and axes are used in every stage column.
    names=['Z650','Z1300','Z2200','Z3050','PIER_X','JOINT']
    limits=[((-3000,2200),(-1400,1400))]*4+[((-1400,1400),(0,4400)),((-1700,1700),(-1400,1400))]
    fig,axes=plt.subplots(len(names),len(stages),figsize=(3.4*len(stages),3*len(names)),squeeze=False)
    for col,stage in enumerate(stages):
        data=np.load(analysis/(stage['id']+'_cuts.npz'))
        for row,name in enumerate(names):
            ax=axes[row,col];ax.add_collection(LineCollection(data[name+'_UV'],colors='#153f60',linewidths=.7))
            ax.set_xlim(*limits[row][0]);ax.set_ylim(*limits[row][1]);ax.set_aspect('equal');ax.grid(alpha=.18)
            if row==0:ax.set_title(stage['id'],fontsize=10)
            ax.set_ylabel(name+' | project units');ax.tick_params(labelsize=7)
    fig.suptitle('Actual native triangle / world-plane intersections | fixed axes across stages',fontsize=15)
    fig.tight_layout(rect=(0,0,1,.97));fig.savefig(dest/'ACTUAL_TRIANGLE_CUTS.png',dpi=160);fig.savefig(dest/'ACTUAL_TRIANGLE_CUTS.pdf');plt.close(fig)
    material=[s for s in stages if 'material_sections' in s and s['id']!='G0_CARRIER']
    labels=['PIER_BULGE','JOINT_BULGE','LINTEL'];colours=['#8c8c8c','#176c95','#cd6a22','#3f8f5e','#873d90']
    fig,axes=plt.subplots(3,2,figsize=(16,12))
    for row,label in enumerate(labels):
        for k,stage in enumerate(material):
            data=np.load(analysis/(stage['id']+'_material_edges.npz'));xy=data[label+'_xy'];raw=data[label+'_excess']
            axes[row,0].plot(*np.r_[xy,xy[:1]].T,label=stage['id'],color=colours[k%len(colours)],linewidth=1)
            axes[row,1].plot(np.arange(512)*360/512,raw,label=stage['id'],color=colours[k%len(colours)],linewidth=1)
        axes[row,0].set(xlim=(-1100,1100),ylim=(-1000,1000),title=label+' | projected ACTUAL material edges',xlabel='Guide cross-axis units',ylabel='Depth Y units',aspect='equal')
        axes[row,1].set(xlim=(0,180),ylim=(-75,650),title=label+' | raw radius minus rest radius',xlabel='Material angle (degrees)',ylabel='Project units')
        for ax in axes[row]:ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Fixed material samples | edges need not lie in a plane after longitudinal motion',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.97));fig.savefig(dest/'MATERIAL_EDGE_DEPTHS.png',dpi=180);fig.savefig(dest/'MATERIAL_EDGE_DEPTHS.pdf');plt.close(fig)
    # A fixed close range exposes the local secondary fold without rescaling depth.
    fig,axes=plt.subplots(3,1,figsize=(12,11))
    for ax,label in zip(axes,labels):
        for k,stage in enumerate(material):
            data=np.load(analysis/(stage['id']+'_material_edges.npz'))
            ax.plot(np.arange(512)*360/512,data[label+'_excess'],label=stage['id'],color=colours[k%len(colours)])
        ax.set(xlim=(40,80),ylim=(100,600),title=label,xlabel='Material angle (degrees)',ylabel='Raw excess / project units');ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(dest/'SAME_SHOULDER_DETAIL.png',dpi=180);plt.close(fig)
    print(dest)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('analysis');plots(p.parse_args().analysis)
