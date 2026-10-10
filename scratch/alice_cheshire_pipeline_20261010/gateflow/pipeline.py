from . import runtime
from .input import load,write,digest
from .geometry import *
from .operators import REGISTRY
from .render import render
from pathlib import Path
import json,time,hashlib,traceback,importlib.metadata

def export(m,path,g):
    # Return to the declared input units; preserve the canonical target frame.
    actual=m.copy();actual.vertices=actual.vertices*g.scale+g.origin
    actual.export(path.with_suffix('.obj'),digits=16);actual.export(path.with_suffix('.ply'))
    return dict(obj_sha256=digest(path.with_suffix('.obj')),ply_sha256=digest(path.with_suffix('.ply')))

def run(input_path,config,output,seed=None,no_render=False):
    start=time.perf_counter();out=Path(output).resolve()
    if out.exists():raise FileExistsError('Refusing existing run directory: '+str(out))
    cfg=json.loads(json.dumps(config));cfg['seed']=cfg['seed'] if seed is None else int(seed)
    if cfg.get('schema')!='cheshire-gateflow/1':raise ValueError('Unknown config schema')
    if not 0<cfg['max_faces']<=500000 or not 0<cfg['max_seconds']<=1200:raise ValueError('Invalid resource budget')
    if len(cfg['stages'])>8 or any(s['op'] not in REGISTRY for s in cfg['stages']):raise ValueError('Unknown operator or too many stages')
    g=load(input_path);out.mkdir(parents=True)
    write(out/'config.json',cfg);write(out/'input_provenance.json',dict(**g.provenance,unit=g.unit,normalization_origin=g.origin.tolist(),normalization_scale=g.scale,profiles=g.profiles,role_names=['support_left','support_right','overhead','upper_context','other']))
    source_hashes={str(p):digest(p) for p in [runtime.REPO/'src/cheshire/reference_subdivision.py',runtime.REPO/'src/cheshire/polygon_dual_subdivision.py',runtime.REPO/'src/cheshire/mola.py',runtime.ASTRA/'src/cheshire/freedom_domains.py'] if p.exists()}
    stages=[];run_info=dict(status='RUNNING',input=g.provenance,seed=cfg['seed'],config_sha256=digest(out/'config.json'),source_hashes=source_hashes,stages=stages,limitations=['Basic topology and Manifold validity; no exhaustive self-contact/clearance certification.','Source role transport after topology changes uses nearest triangle centroid, not exact lineage.'])
    try:
      current,prep=prepare(g,cfg['prepare']);check(current,cfg['max_faces']);guard=opening_solid(g,cfg['opening_retention'])
      initial_intersection=solid(current)^guard
      removed=float(initial_intersection.volume())
      current=from_solid(solid(current)-guard)
      ci=check(current,cfg['max_faces']);stages.append(dict(stage='prepare',preparation=prep,opening_guard_removed_volume=removed,**ci))
      export(current,out/'input_prepared',g)
      np.savez_compressed(out/'source_observations.npz',vertices=g.mesh.vertices,faces=g.mesh.faces,face_roles=g.labels)
      framing=np.array([current.bounds[0]-.09,current.bounds[1]+.09])
      if not no_render:render(current,out/'input_views',cfg['render_resolution'],framing)
      rng=np.random.default_rng(cfg['seed'])
      for i,spec in enumerate(cfg['stages']):
        if time.perf_counter()-start>cfg['max_seconds']:raise TimeoutError('Run time budget exceeded before next stage')
        folder=out/f'{i+1:02}_{spec["op"]}';folder.mkdir()
        obs=observe(current,g,cfg,rng);np.savez_compressed(folder/'observations.npz',**obs)
        before_hash=hashlib.sha256(np.asarray(current.vertices).tobytes()+np.asarray(current.faces).tobytes()).hexdigest()
        failures=[];accepted=False
        for attenuation in [1.,.5,.25]:
          try:
            result,meta,state=REGISTRY[spec['op']](current,obs,spec,attenuation,cfg['max_faces'])
            check(result,cfg['max_faces'])
            s=solid(result);obstructed=float((s^guard).volume());result=from_solid(s-guard)
            info=check(result,cfg['max_faces'])
            if info['components']>ci['components']:raise ValueError('Operator disconnected the gate')
            if result.volume<current.volume*.60:raise ValueError('Operator removed over 40 percent volume')
            residual=abs(float((solid(result)^guard).volume()))
            if residual>1e-9:raise ValueError('Opening guard still obstructed')
            accepted=True;break
          except (ValueError,RuntimeError) as e:failures.append(dict(attenuation=attenuation,error=str(e)))
        if not accepted:raise RuntimeError('Operator failed at all allowed strengths: '+str(failures))
        current=result;ci=info
        np.savez_compressed(folder/'operator_state.npz',**state)
        record=dict(stage=spec['op'],index=i+1,attenuation=attenuation,failed_attempts=failures,input_geometry_sha256=before_hash,observation_source='actual_previous_stage_mesh',role_counts=np.bincount(obs['role'],minlength=5).tolist(),bend_quantiles=np.quantile(obs['bend'],[0,.5,.9,1]).tolist(),gain_quantiles=np.quantile(obs['gain'],[0,.5,.9,1]).tolist(),opening_removed_volume=obstructed,opening_residual_volume=residual,operator=meta,**info)
        record.update(export(current,folder/'mesh',g));stages.append(record);write(folder/'stage.json',record)
        print(json.dumps({'stage':spec['op'],'faces':len(current.faces),'attenuation':attenuation,'elapsed':time.perf_counter()-start}),flush=True)
      hashes=export(current,out/'result',g)
      # Re-read exported OBJ; checks apply to the delivered artifact, not only arrays.
      reloaded=trimesh.load(out/'result.obj',process=False,force='mesh');delivered=check(reloaded,cfg['max_faces'])
      if not no_render:render(current,out/'views',cfg['render_resolution'],framing)
      run_info.update(status='COMPLETE',elapsed_seconds=time.perf_counter()-start,final=delivered,files=hashes,versions={k:importlib.metadata.version(k) for k in ['numpy','scipy','trimesh','manifold3d','compas','pyrender']})
      write(out/'run.json',run_info);return run_info
    except Exception as e:
      run_info.update(status='FAILED',error=str(e),traceback=traceback.format_exc(),elapsed_seconds=time.perf_counter()-start);write(out/'run.json',run_info);raise
