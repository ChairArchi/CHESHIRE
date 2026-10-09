"""Generation counts, carrier freedom, actual material-edge curves and ancestry."""
import argparse,json,sys
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from cheshire.reference_subdivision import ArrayMesh,topology,fields
from task33_preserve import sha,write_new
from task35_analyze import THETA,child_valleys,envelope_retention
ROOT=Path('E:/CHESHIRE_DATA/task36')


def collect(candidate,tag):
    job=ROOT/'candidates'/candidate;done=json.loads((job/'completed.json').read_text());final=len(done['history'])
    dest=ROOT/'measurements'/tag;dest.mkdir(parents=True,exist_ok=False);rows=[];profiles={};curves={}
    for g in range(final+1):
        stage=job/('G0_CARRIER' if g==0 else f'G{g}_FOLD');z=np.load(stage/'quad_state.npz')
        m=ArrayMesh(*(z[k] for k in ['xyz','faces','classes','rest','anchors']),int(z['generation']));x=m.xyz;rest=m.rest
        t=topology(m);f=fields(m,t)
        original=np.array([[-1,-1],[1,-1],[1,1],[-1,1]],float)*500
        corner_displacement=np.linalg.norm(x[:12]-np.array([[*xy,h] for h in [0,2000,4000] for xy in original]),axis=1)
        outside=np.any(abs(x[:,:2])>500+1e-9,axis=1)
        root_normals=np.array([[0,0,-1],[0,-1,0],[1,0,0],[0,1,0],[-1,0,0],[0,-1,0],[1,0,0],[0,1,0],[-1,0,0],[0,0,1]])
        angles=np.degrees(np.arccos(np.clip(np.sum(f['nf']*root_normals[m.anchors[:,0]],axis=1),-1,1)))
        row=dict(generation=g,stage=str(stage),native_sha256=sha(stage/'mesh.npz'),operator_vertices=len(x),operator_edges=len(t['edges']),operator_quads=len(m.faces),native_vertices=len(x)+len(m.faces),native_triangles=4*len(m.faces),
            extents=np.ptp(x,axis=0).tolist(),original_corner_max_move=float(corner_displacement.max()),outside_original_xy_box=int(outside.sum()),
            original_corner_xy_max=float(abs(x[:12,:2]).max()),all_xy_max=float(abs(x[:,:2]).max()),incoming_normals_from_G0_degrees=np.quantile(angles,[0,.5,.95,1]).tolist())
        if g:
            o=np.load(stage/'operator_state.npz');pre=np.load(job/f'G{g}_PRE/quad_state.npz')['xyz'];delta=np.linalg.norm(x-pre,axis=1)
            nv=len(o['incoming_point_classes']);ne=len(o['input_edges'])
            row['actual_participation']={name:dict(points=len(v),moving=int((v>1e-9).sum()),distance=np.quantile(v,[0,.5,.95,1]).tolist()) for name,v in [('retained',delta[:nv]),('edge',delta[nv:nv+ne]),('face',delta[nv+ne:])]}
            if 'local_point_factor' in o:row['local_factor']=dict(limited=int((o['local_point_factor']<1).sum()),zero=int((o['local_point_factor']==0).sum()),quantiles=np.quantile(o['local_point_factor'],[0,.5,.95,1]).tolist())
            row['actual_parent_quads_verified']=bool(np.array_equal(m.faces[:,1],o['parent_corner']))
        if g>=3:
            for h in range(500,3501,250):
                ids=np.flatnonzero(abs(rest[:,2]-h)<1e-9);angle=np.arctan2(rest[ids,1],rest[ids,0])%(2*np.pi);order=np.argsort(angle);ids=ids[order];angle=angle[order]
                if len(ids)<4 or np.any(np.diff(angle)<1e-12):raise ValueError('Material ring identity ambiguity.')
                # Each neighbour pair must be an actual operator/native edge.
                pairs=np.sort(np.column_stack([ids,np.roll(ids,-1)]),axis=1);key=t['edges'][:,0]*len(x)+t['edges'][:,1]
                if not np.isin(pairs[:,0]*len(x)+pairs[:,1],key).all():raise ValueError('Material curve contains a non-edge shortcut.')
                right=np.searchsorted(angle,THETA,side='right')%len(ids);left=(right-1)%len(ids);span=(angle[right]-angle[left])%(2*np.pi);offset=(THETA-angle[left])%(2*np.pi);w=offset/span
                xyz=(1-w[:,None])*x[ids[left]]+w[:,None]*x[ids[right]];base=(1-w[:,None])*rest[ids[left]]+w[:,None]*rest[ids[right]]
                signal=np.linalg.norm(xyz[:,:2],axis=1)-np.linalg.norm(base[:,:2],axis=1)
                profiles[(g,h)]=signal;curves[f'G{g}_Z{h}_xyz']=xyz;curves[f'G{g}_Z{h}_edge_ids']=np.column_stack([ids[left],ids[right]]);curves[f'G{g}_Z{h}_weight']=w
        rows.append(row);print(candidate,'metrics',g,flush=True)
    hierarchy=[]
    for g in range(4,final+1):
        for h in range(500,3501,250):
            a=profiles[(g-1,h)];b=profiles[(g,h)]
            hierarchy.append(dict(generation=g,material_height=h,child_valleys=child_valleys(a,b),envelope_retention=envelope_retention(a,b)))
    np.savez_compressed(dest/'material_curves.npz',**curves)
    write_new(dest/'generations.json',rows);write_new(dest/'material_hierarchy.json',dict(rows=hierarchy,
        method='2048 material-angle samples of verified actual native edge curves. XYZ interpolation uses source IDs/weights. Radial excess and prominence15; no smoothing. Curves can be nonplanar, unlike fixed-world triangle cuts.',
        limits='Finite radial projections do not certify continuous ridges, all parent basins, or Euclidean closest-surface fold depth.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args();collect(a.candidate,a.tag)
