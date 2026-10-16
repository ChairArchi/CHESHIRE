"""Read-only cached spine mass/phase forensics; does not form a mesh."""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from scipy.ndimage import gaussian_filter1d
import run_spine_reconstruction_v4 as runner
import recursive_spine_operator as op

def unit(a):
 n=np.linalg.norm(a,axis=1)
 return a/np.maximum(n[:,None],1e-30)
def quant(a):
 a=np.asarray(a)
 return dict(count=len(a),q=np.quantile(a,[0,.1,.5,.9,1]).tolist()) if len(a) else dict(count=0,q=[])
def frame_at(s,frame,target):
 return unit(np.column_stack([np.interp(target,s,frame[:,j]) for j in range(3)]))
def metrics(delta,logical,f,n,b,length):
 s=f['logical_s']; ss=logical[:,0]*length
 nn=frame_at(s,n,ss);bb=frame_at(s,b,ss)
 h=np.interp(ss,s,f['node_height']);base=np.interp(ss,s,f['usable_base_width'])
 pitch=1.5*f['requested_base_width'];end=op.quintic(ss/(1.5*pitch[0]))*op.quintic((length-ss)/(1.5*pitch[-1]))
 chi=np.interp(ss,s,f['logical_chi']);wave=(.5+.5*np.cos(2*np.pi*chi))**2
 dn=np.einsum('ij,ij->i',delta,nn);db=np.einsum('ij,ij->i',delta,bb)
 core=(end>.99)&(h>.020)
 result=dict(points=len(delta),interior_visible_budget_points=int(core.sum()),N_all=quant(dn),absB_all=quant(np.abs(db)),norm_all=quant(np.linalg.norm(delta,axis=1)))
 for name,u in [('centre',0.),('inner',.22),('paired_crown',.5),('outer',.75)]:
  take=core&(np.abs(np.abs(logical[:,2])-u)<.035)
  node=take&(wave>.8);neck=take&(wave<.02)
  y=dn[take]/h[take];xx=np.column_stack((np.ones(take.sum()),np.cos(2*np.pi*chi[take]),np.cos(4*np.pi*chi[take])))
  fit=np.linalg.lstsq(xx,y,rcond=None)[0] if take.sum()>3 else np.zeros(3)
  result[name]=dict(points=int(take.sum()),node_N=quant(dn[node]),neck_N=quant(dn[neck]),node_N_over_H=quant(dn[node]/h[node]),neck_N_over_H=quant(dn[neck]/h[neck]),absB=quant(np.abs(db[take])),absB_over_base=quant(np.abs(db[take])/base[take]),harmonic_fit_N_over_H=fit.tolist(),fitted_peak_minus_neck_over_H=float(2*fit[1]),fitted_peak_N_over_H=float(fit.sum()),fitted_neck_N_over_H=float(fit[0]-fit[1]+fit[2]))
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 receipt=json.loads((a.root/'RECEIPT.json').read_text());pre=json.loads((a.root/'PREFLIGHT.json').read_text())
 with np.load(a.root/'SPARSE_DELTA.npz',allow_pickle=False) as z:ids=z['ids'];delivered=z['delta']
 carrier=Path(receipt['variants']['REFERENCE_NESTED']['control_quad'])
 with np.load(carrier,allow_pickle=False) as z:chart=z['chart'][ids]
 result=dict(kind='READ_ONLY_CACHED_SPINE_MASS_FORENSICS',source_receipt=str(a.root/'RECEIPT.json'),source_receipt_sha256=runner.sha(a.root/'RECEIPT.json'),script_sha256=runner.sha(Path(__file__)),no_mesh_formation=True,projection='Signed N/B projected onto exact operator pooled source-curve frames, interpolated in carried physical arc. Core statistics require end envelope>.99 and nominal H>.020.',parents=[])
 for info in pre['selected']:
  sources={};state=runner.load_tree(info['evidence']['description'],sources);f=state['formation'];e=state['foundation'];curve=e['source_curve'];s=f['logical_s'];length=info['total_length'];rows=len(s)
  normal=curve['normal'];t=curve['tangent'].copy();t-=normal*np.einsum('ij,ij->i',t,normal)[:,None];t=unit(t);across=np.cross(normal,t)
  sigma=.5*np.median(1.5*.65*f['parent_width'])/np.median(np.diff(s));n=unit(gaussian_filter1d(normal,sigma,axis=0,mode='nearest'));b=gaussian_filter1d(across,sigma,axis=0,mode='nearest');b=unit(b-n*np.einsum('ij,ij->i',b,n)[:,None])
  initial=f['formed_cage']-f['xyz0'];logical0=np.stack((np.broadcast_to((s/length)[:,None],(rows,9)),np.zeros((rows,9)),np.broadcast_to(op.U_KNOTS,(rows,9))),axis=-1).reshape(-1,3)
  reconstructed=f['normal_delta'][:,:,None]*n[:,None]+f['across_delta'][:,:,None]*b[:,None]
  q=f['quads_refined'];atlas=runner.BucketAtlas(f['source_chart_transfer'],q,f['delta_refined'],f['logical_refined'],verify_global=False)
  predicted,logical,valid=atlas.evaluate(chart);taper=op.quintic((1-np.abs(logical[:,2]))/.22)*valid
  ss=logical[:,0]*length;pp=np.asarray(info['formation']['node_pitch_quantiles'])[[0,-1]]
  taper*=op.quintic(ss/(1.5*pp[0]))*op.quintic((length-ss)/(1.5*pp[1]));take=valid&(taper>1e-6)
  actual=delivered[take];rawpred=predicted[take];tp=taper[take];errors=np.linalg.norm(actual-rawpred*tp[:,None],axis=1)
  parent=dict(component=info['component'],phase=info['phase_level'],sources=sources,frames_reconstruct_initial_max_error=float(np.abs(initial-reconstructed).max()),rows=rows,cells=int(f['cell_count']),rows_per_cell=rows/int(f['cell_count']),height=quant(f['node_height']),parent_depth=quant(f['actual_parent_depth']),height_over_depth=quant(f['node_height']/f['actual_parent_depth']),usable_base=quant(f['usable_base_width']),usable_over_requested=quant(f['usable_base_width']/f['requested_base_width']),coarse=metrics(initial.reshape(-1,3),logical0,f,n,b,length),after_two_CC=metrics(f['delta_refined'],f['logical_refined'],f,n,b,length),actual_G7_delivered=metrics(actual,logical[take],f,n,b,length),transfer=dict(actual_control_ids=len(actual),matched_field_max_error=float(errors.max()),matched_field_error=quant(errors),transfer_taper=quant(tp),actual_norm_over_un_tapered_prediction=quant(np.linalg.norm(actual,axis=1)/np.maximum(np.linalg.norm(rawpred,axis=1),1e-30))))
  result['parents'].append(parent)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2),encoding='utf8')
 print(a.output)
 for p in result['parents']:
  print('PARENT',p['component'],'Hmed',p['height']['q'][2],'Dmed',p['parent_depth']['q'][2],'transfer_maxerror',p['transfer']['matched_field_max_error'],'actual_controls',p['transfer']['actual_control_ids'])
  for stage in ('coarse','after_two_CC','actual_G7_delivered'):
   print(stage,{u:round(p[stage][u]['fitted_peak_minus_neck_over_H'],5) for u in ('centre','inner','paired_crown','outer')})
if __name__=='__main__':main()
