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


def progression(data,output):
    with np.load(data) as z:d={k:z[k].copy() for k in z.files}
    generations=sorted({int(k.split('_')[0][1:]) for k in d})
    top=100*np.ceil((max(v[:,1].max() for v in d.values())+30)/100)
    fig,axes=plt.subplots(3,len(generations),figsize=(17,9),constrained_layout=True)
    for row,s in enumerate([.06531,.15031,.24531]):
        for column,g in enumerate(generations):
            ax=axes[row,column]
            for kind,colour,style in [('PRE','#88949a','--'),('FOLD','#803d6c','-')]:
                p=d[f'G{g}_{kind}_s{s}'];ax.plot(p[:,0],p[:,1],style,color=colour,lw=1.2,label=kind)
            ax.set(xlim=(-1,1),ylim=(-30,top),xlabel='Same material u',ylabel='Actual mesh depth',title=f'G{g}: s={s:.5f}')
            ax.grid(alpha=.2);ax.legend(frameon=False,fontsize=8)
    fig.suptitle('Actual checkpoint progression — fixed cuts and scales\nDashed: immediately before reconstruction; solid: after. No shading or per-panel normalization.',fontsize=14)
    for suffix in ['.png','.pdf']:
        path=Path(output).with_suffix(suffix)
        if path.exists():raise FileExistsError(path)
        path.parent.mkdir(parents=True,exist_ok=True);fig.savefig(path,dpi=200,facecolor='white')
    plt.close(fig)


def tracks(data,output):
    import json
    with np.load(data) as z:d={k:z[k].copy() for k in z.files}
    records=json.loads(Path(data).with_name('tracks.json').read_text())['rows']
    q=d['q'];cuts=[d[f'cut_{i}'] for i in range(len(q))]
    fig,axes=plt.subplots(1,3,figsize=(16,9),constrained_layout=True)
    image=axes[0].pcolormesh(cuts[0][:,0],q,np.array([c[:,3] for c in cuts]),shading='nearest',cmap='magma',vmin=0,vmax=900)
    fig.colorbar(image,ax=axes[0],label='Actual final mesh depth')
    for label in [-1,0,1]:
        parents=[next(p for p in r['parents'] if p['label']==label) for r in records]
        axes[0].plot([p['u'] for p in parents],q,color='cyan',lw=1.1)
        xyz=np.array([p['xyz_on_final_surface'] for p in parents])
        axes[1].plot(xyz[:,0],xyz[:,2],color='#803d6c',lw=1.4,label='Parent reference paths on final mesh' if label==-1 else None)
    meso=[];fine=[]
    for r,c in zip(records,cuts):
        for p in r['parents']:
            for child in p['children']:
                meso.append(child['xyz'])
                axes[0].plot(child['u'],r['s'],'.',color='#57edba',ms=1.9)
                if child['fine_split']:
                    for side in ['left_u','right_u']:
                        u=child['fine_split'][side]
                        fine.append([np.interp(u,c[:,0],c[:,k]) for k in [4,5,6]])
    for c in cuts:axes[1].plot(c[:,4],c[:,6],color='#aaaaaa',lw=.3,alpha=.5)
    meso=np.asarray(meso);fine=np.asarray(fine)
    axes[1].scatter(meso[:,0],meso[:,2],s=3,color='#bd7527',label='Actual meso maxima')
    axes[1].scatter(fine[:,0],fine[:,2],s=2,color='#256f83',label='Resolved fine split maxima')
    axes[0].set(xlim=(-.98,.98),ylim=(q[0],q[-1]),xlabel='Same material u',ylabel='Material arc q',title='Actual sampled depth and macro/meso paths')
    axes[1].set(xlim=(-2800,-350),ylim=(0,3600),aspect='equal',xlabel='Actual world X',ylabel='Actual world Z',title='Native XYZ front projection, left half')
    axes[1].legend(frameon=False,fontsize=8)
    spans=[r['three_inner_parent_span'] for r in records]
    axes[2].plot(q,spans,color='#803d6c',label='Span of three inner macro ridges')
    axes[2].set(xlim=(q[0],q[-1]),ylim=(0,650),xlabel='Material arc q',ylabel='Actual tangent-projected span',title='Broad → binding → broad → binding')
    for x in [.15,.43]:axes[2].axvline(x,color='#777777',ls='--',lw=.8)
    for ax in axes:ax.grid(alpha=.15)
    fig.suptitle('65 actual triangle cuts — sampled ridge relationships\nLines connect finite samples, not certified differential ridges; absent fine splits are not filled in.',fontsize=14)
    for suffix in ['.png','.pdf']:
        path=Path(output).with_suffix(suffix)
        if path.exists():raise FileExistsError(path)
        path.parent.mkdir(parents=True,exist_ok=True);fig.savefig(path,dpi=200,facecolor='white')
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--baseline',type=Path);p.add_argument('--progression',action='store_true');p.add_argument('--tracks',action='store_true');a=p.parse_args()
    if a.progression:progression(a.data,a.output)
    elif a.tracks:tracks(a.data,a.output)
    else:plot(a.data,a.output,a.baseline)
