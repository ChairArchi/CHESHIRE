"""Standalone plots of measured Task35 native cuts; no generated geometry."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
ROOT=Path('E:/CHESHIRE_DATA/task35')


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def plot(candidate,measurement,validation,tag,audit_id=None):
    source=ROOT/'measurements'/measurement;data=json.loads((source/'result.json').read_text());curves=dict(np.load(source/'actual_curves.npz'))
    cut_path=ROOT/'validation'/validation/((audit_id or candidate)+'_cuts.npz');cuts=dict(np.load(cut_path));dest=ROOT/'plots'/tag;dest.mkdir(parents=True,exist_ok=False)
    theta=curves['theta']*180/np.pi;stages=['G3_FORM','G4_FOLD','G7_FOLD'];colours=['#8a8a86','#cc7a22','#146c9a'];records=[]
    def save(fig,name):
        fig.tight_layout();path=dest/name;fig.savefig(path,dpi=170);plt.close(fig);records.append(dict(path=str(path),sha256=digest(path)))
    fig,axes=plt.subplots(1,3,figsize=(11,7),sharey=True)
    for ax,name,columns,title in zip(axes,['XZ','YZ','DIAGONAL'],[[0,2],[1,2],None],['Actual Y=0 cut','Actual X=0 cut','Actual X=Y cut']):
        for stage,c in zip(stages,colours):
            xyz=curves['LONG_'+stage+'_'+name+'_segments'];uv=xyz[:,:,columns] if columns else np.stack([(xyz[:,:,0]+xyz[:,:,1])/np.sqrt(2),xyz[:,:,2]],axis=-1)
            ax.add_collection(LineCollection(uv,linewidths=.6,color=c,label=stage))
        ax.set(xlim=(-1400,1400),ylim=(0,4000),title=title,xlabel='project units');ax.set_aspect('equal');ax.grid(alpha=.2)
    axes[0].legend(fontsize=7);fig.suptitle(candidate+' | real triangle surface intersections');save(fig,'LONGITUDINAL_TRIANGLE_CUTS.png')
    fig,axes=plt.subplots(3,1,figsize=(12,10),sharex=True)
    for ax,name in zip(axes,['XZ','YZ','DIAGONAL']):
        for stage,c in zip(stages,colours):ax.plot(curves['axial_z'],curves['LONG_'+stage+'_'+name+'_radius'],color=c,lw=1,label=stage)
        ax.plot(curves['axial_z'],curves['LONG_REST_'+name+'_radius'],color='#bbbbbb',ls='--',label='REST')
        ax.set(title=name+' positive half of actual cut',ylim=(0,1500),ylabel='physical radial extent');ax.grid(alpha=.2)
    axes[0].legend();axes[-1].set(xlim=(0,4000),xlabel='World Z / project units')
    fig.suptitle(candidate+' | world sections, not material ancestry');save(fig,'AXIAL_TRIANGLE_PROFILES.png')
    fig,axes=plt.subplots(2,4,figsize=(15,8));heights=[900,1500,1900,2120,2380,2520,3000]
    for ax,z in zip(axes.flat,heights):
        for name,c in zip(stages,colours):
            key=f'Z{z}_segments' if name=='G7_FOLD' else f'{name}_Z{z}_segments'
            ax.add_collection(LineCollection(curves[key][:,:,:2],color=c,label=name,linewidths=.9))
        ax.set(xlim=(-1200,1200),ylim=(-1000,1000),title=f'World Z={z}+.12345',xlabel='X',ylabel='Y');ax.set_aspect('equal');ax.grid(alpha=.2)
    axes.flat[-1].axis('off');axes.flat[0].legend(fontsize=7)
    fig.suptitle(candidate+' | fixed-world actual triangle cuts, NOT material ancestry');save(fig,'TRANSVERSE_TRIANGLE_CUTS.png')
    fig,axes=plt.subplots(7,1,figsize=(12,16));selected=[]
    for ax,z in zip(axes,[900,1500,1900,2120,2380,2520,3000]):
        track=min(data['material_tracks'],key=lambda t:abs(t['original_z']-z));idx=None
        for k in curves:
            if k.startswith('M') and k.endswith('_G3_FORM_xyz'):
                candidate_idx=k.split('_')[0][1:];xyz=curves[k]
                if abs(xyz[:,2].mean()-track['observations']['G3_FORM']['mean_actual_z'])<1e-8:idx=candidate_idx;break
        if idx is None:raise ValueError('Material curve identity missing.')
        for name,c in zip(stages,colours):ax.plot(theta,curves[f'M{idx}_{name}_excess'],label=name,color=c,lw=1)
        for v in track['small_inside_middle']:
            angle=theta[v['valley']]
            if angle<=90:ax.scatter(angle,curves[f'M{idx}_G7_FOLD_excess'][v['valley']],s=20,color='#a2203d',zorder=5)
        ax.set(xlim=(0,90),ylim=(-300,850),ylabel='radial excess',title=f"Original material Z={track['original_z']:.2f}; {track['region']} | final mean Z={track['observations']['G7_FOLD']['mean_actual_z']:.2f}")
        ax.grid(alpha=.2);selected.append(dict(requested_reference_z=z,original_material_z=track['original_z'],material_curve_id=idx))
    axes[0].legend();axes[-1].set_xlabel('Material angle in degrees (not spatial polar angle)')
    fig.suptitle(candidate+' | inherited native-edge samples; red=finite internal valley >=15 units');save(fig,'MATERIAL_HIERARCHY.png')
    fig,axes=plt.subplots(3,1,figsize=(11,10),sharex=True)
    for stage,c in zip(['G3_FORM','G4_FOLD','G7_FOLD'],colours):
        s=dict(np.load(ROOT/'candidates'/candidate/stage/'formation_state.npz'));controls=dict(np.load(ROOT/'candidates'/candidate/stage/'control_state.npz'));z=s['s']*4000
        axes[0].plot(z,controls['read_broadness'],label=stage,color=c)
        axes[1].plot(z,controls['read_slope'],color=c)
        axes[2].plot(z,np.max(controls['total_applied_distance'],axis=1),color=c)
    for ax,label in zip(axes,['Measured incoming broadness','Measured incoming dR/dZ','Actual max XYZ movement / row']):ax.set(ylabel=label);ax.grid(alpha=.2)
    axes[0].legend();axes[-1].set(xlim=(0,4000),xlabel='Original material height / project units')
    fig.suptitle(candidate+' | feature → control evidence');save(fig,'REGIONAL_CONTROLS.png')
    (dest/'manifest.json').write_text(json.dumps(dict(candidate=candidate,measurement_sha256=digest(source/'result.json'),curve_sha256=digest(source/'actual_curves.npz'),
        triangle_cut_sha256=digest(cut_path),producer_sha256=digest(__file__),selected_material_tracks=selected,files=records,
        limits='Identical physical plot limits. Triangle cuts and native-edge ancestry are distinct. Named planes use the preregistered +.12345 offset. No curve smoothing.'),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--measurement',required=True);p.add_argument('--validation',required=True);p.add_argument('--tag',required=True);p.add_argument('--audit-id');a=p.parse_args();plot(a.candidate,a.measurement,a.validation,a.tag,a.audit_id)
