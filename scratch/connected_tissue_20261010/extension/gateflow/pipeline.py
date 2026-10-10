from . import runtime
from .input import load,write,sha
from .engine import *
from .render import render,sheet
from .symmetry import reflect,symmetry_error,vertex_values
from pathlib import Path
import json,time,hashlib,traceback

def save(m,path,g):
    tm=surface(m);tm.vertices=tm.vertices*g.scale+g.origin;tm.export(path.with_suffix('.obj'),digits=16);tm.export(path.with_suffix('.ply'));return tm

def run(input_path,config,output,seed=None,no_render=False,resume_stage=None):
    start=time.perf_counter();out=Path(output).resolve()
    if out.exists():raise FileExistsError('Output must be NEW: '+str(out))
    cfg=json.loads(json.dumps(config,allow_nan=False));cfg['seed']=cfg['seed'] if seed is None else int(seed)
    if cfg.get('schema')!='cheshire-generative/1' or any(s['op'] not in OPS for s in cfg['stages']):raise ValueError('Invalid config or operator')
    if not 0<=cfg['feedback']<=1 or not 0<cfg['max_polygons']<=3000000 or len(cfg['stages'])>32:raise ValueError('Invalid budget/feedback')
    g=load(input_path);out.mkdir(parents=True);write(out/'config.json',cfg);write(out/'input.json',g.manifest)
    current=g.mesh;roles=g.roles.copy();frontier=np.zeros(len(current.faces),bool);rng=np.random.default_rng(cfg['seed'])
    field=smooth_graph(rng.normal(size=len(current.xyz)),current,cfg['field_radius'])
    field=np.tanh(field/max(np.std(field),1e-8))
    if symmetry_error(current)>1e-8:raise ValueError('Current input contract requires bilateral geometry about X=0')
    # Symmetric field on the actual input; reflected roles remain left/right.
    pos=current.xyz.copy();pos[:,0]=np.abs(pos[:,0]);field=field[cKDTree(current.xyz).query(pos)[1]]
    start_stage=0;resume_record=None
    if resume_stage is not None:
        resume_path=Path(resume_stage).resolve();source_run=json.loads((resume_path.parent/'run.json').read_text());source_cfg=json.loads((resume_path.parent/'config.json').read_text());source_step=json.loads((resume_path/'stage.json').read_text())
        start_stage=int(source_step['index'])
        if source_run['status']!='COMPLETE' or source_run['input_sha256']!=g.manifest['mesh_sha256']:raise ValueError('Resume requires completed run with identical input')
        if source_run['seed']!=cfg['seed'] or source_cfg['stages'][:start_stage]!=cfg['stages'][:start_stage]:raise ValueError('Resume prefix/seed does not match requested recipe')
        if start_stage>=len(cfg['stages']):raise ValueError('Resume recipe has no remaining stages')
        statefile=resume_path/'state.npz';st=np.load(statefile)
        current=ArrayMesh(st['xyz'],st['faces'],st['classes'],st['rest'],st['anchors'],int(st['generation']));field=st['field'];roles=st['roles'];frontier=st['frontier'] if 'frontier' in st else np.zeros(len(current.faces),bool)
        resume_record=dict(stage_path=str(resume_path),state_sha256=sha(statefile),source_run_sha256=sha(resume_path.parent/'run.json'),completed_prefix_stages=start_stage,frontier_restored='frontier' in st)
    fixed_field=field.copy();fixed_xyz=current.xyz.copy();fixed_tree=cKDTree(fixed_xyz)
    record=dict(symmetry='X=0 positive-half polygon clipping and seam-welded reflection after EVERY stage; source center restored on export',status='RUNNING',input_kind=g.manifest['source_kind'],input_sha256=g.manifest['mesh_sha256'],seed=cfg['seed'],config_sha256=sha(out/'config.json'),stages=[],limitations=['Visual design prototype, not structural or fabrication certification.','Basic topology checks do not certify absence of all self contacts.','Voxel fuse explicitly changes representation and loses sub-voxel details; no exact lineage claim.'])
    record['resumed_from']=resume_record
    record['code_sha256']={str(f.relative_to(runtime.PROJECT)):sha(f) for f in sorted((runtime.PROJECT/'gateflow').glob('*.py'))}
    images=[];framing=np.array([g.mesh.xyz.min(0)-.16,g.mesh.xyz.max(0)+.16])
    try:
      info=validate(current,cfg['max_polygons']);save(g.mesh,out/'input_mesh',g)
      if resume_record:save(current,out/'resume_mesh',g)
      if not no_render:render(surface(current),out/'00_input',cfg['render_resolution'],framing);images.append((out/'00_input/front.png','00 / RESUMED TARGET' if resume_record else '00 / NEUTRAL INPUT'))
      for i,spec in enumerate(cfg['stages'][start_stage:],start=start_stage):
        folder=out/f'{i+1:02}_{spec["op"]}';folder.mkdir()
        obs=observe(current,field,roles,cfg)
        obs['input_mesh']=g.mesh
        obs['openings']=g.openings
        obs['frontier']=frontier
        obs['structural_roles']=roles
        if cfg.get('observation_mode','current')=='frozen':
          # Diagnostic: frozen initial scalar field on current sample positions.
          obs['field']=fixed_field[fixed_tree.query(current.xyz)[1]]
          mask=current.faces>=0;obs['face_field']=(obs['field'][np.maximum(current.faces,0)]*mask).sum(1)/mask.sum(1)
        np.savez_compressed(folder/'observations.npz',field=obs['field'],face_field=obs['face_field'],signed_curvature=obs['signed_curvature'],feedback_signal=obs['feedback_signal'],roles=roles,positions=current.xyz,libigl_curvature=obs['libigl_curvature'],principal_direction=obs['principal_direction'],libigl_bad_vertices=obs['libigl_bad_vertices'])
        attempts=[]
        for attenuation in [1.,.5,.25]:
          try:
            result,meta,state=OPS[spec['op']](current,obs,spec,attenuation,cfg['max_polygons']);checks=validate(result,cfg['max_polygons']);break
          except (ValueError,RuntimeError) as e:attempts.append(dict(attenuation=attenuation,error=str(e)))
        else:raise RuntimeError(str(attempts))
        field=transport(current,result,obs['field']);roles=roles[state['parent_face']] if 'parent_face' in state else role_transport(current,result,roles)
        if 'generated_faces' in state:
            frontier=np.zeros(len(result.faces),bool);frontier[state['generated_faces']]=True
        elif 'parent_face' in state:frontier=frontier[state['parent_face']]
        elif 'parent_faces' in state:
            parents=state['parent_faces'];frontier=np.any(frontier[np.maximum(parents,0)]&(parents>=0),axis=1)
        elif len(result.faces)!=len(frontier):frontier=np.zeros(len(result.faces),bool)
        raw=result
        result,symstate=reflect(raw)
        field=vertex_values(symstate,field)
        roles=roles[symstate['symmetry_parent_face']];frontier=frontier[symstate['symmetry_parent_face']]
        flipped=symstate['symmetry_reflected_face'];original_roles=roles.copy()
        roles[flipped & (original_roles==0)]=1;roles[flipped & (original_roles==1)]=0
        state.update(symstate);checks=validate(result,cfg['max_polygons']);checks['symmetry_max_error']=symmetry_error(result)
        current=result
        np.savez_compressed(folder/'operator_state.npz',**state)
        np.savez_compressed(folder/'state.npz',xyz=current.xyz,faces=current.faces,classes=current.classes,rest=current.rest,anchors=current.anchors,generation=current.generation,field=field,roles=roles,frontier=frontier)
        tm=save(current,folder/'mesh',g)
        step=dict(index=i+1,op=spec['op'],parameters=spec,attenuation=attenuation,failed_attempts=attempts,observed_geometry='Actual previous-stage mesh',curvature_backend=obs['curvature_backend'],field_std=float(np.std(obs['field'])),signed_curvature_quantiles=np.quantile(obs['signed_curvature'],[0,.5,.9,1]).tolist(),operator=meta,checks=checks,mesh_sha256=sha(folder/'mesh.obj'))
        record['stages'].append(step);write(folder/'stage.json',step)
        if not no_render:render(surface(current),folder/'views',cfg['render_resolution'],framing);images.append((folder/'views/front.png',f'{i+1:02} / {spec["op"].upper()}'))
        print(json.dumps(dict(stage=spec['op'],polygons=len(current.faces),vertices=len(current.xyz),seconds=time.perf_counter()-start)),flush=True)
      # Opening protection uses the supplied polygon, never a generated arch template.
      tm=surface(current);s=md.Manifold(md.Mesh64(np.asarray(tm.vertices),np.asarray(tm.faces,dtype=np.uint64)))
      if s.status()!=md.Error.NoError:raise ValueError('Final Boolean input rejected: '+str(s.status()))
      guards=[]
      for profile in g.openings:
        center=profile.mean(0);profile=center+(profile-center)*cfg['opening_retention']
        # Extend to the input floor to keep a passable central portal.
        profile[np.isclose(profile[:,1],profile[:,1].min()),1]=g.mesh.xyz[:,2].min()-.05
        guards.append(md.CrossSection([profile]).extrude(4).rotate((90,0,0)).translate((0,2,0)))
      guard=md.Manifold.batch_boolean(guards,md.OpType.Add);removed=abs(float((s^guard).volume()));s=s-guard
      if s.status()!=md.Error.NoError or s.is_empty():raise ValueError('Final opening Boolean failed')
      raw=s.to_mesh64();tm=trimesh.Trimesh(np.array(raw.vert_properties)[:,:3],np.array(raw.tri_verts),process=False)
      cc=trimesh.graph.connected_components(tm.face_adjacency,nodes=np.arange(len(tm.faces)))
      areas=np.array([tm.area_faces[a].sum() for a in cc]);largest=int(np.argmax(areas));discarded=float((areas.sum()-areas[largest])/areas.sum())
      if cfg.get('final_component_policy','largest')=='largest' and discarded>.03:raise ValueError('Opening clipping disconnected over 3% surface area')
      if len(cc)>1 and cfg.get('final_component_policy','largest')=='largest':tm=tm.submesh([cc[largest]],append=True,repair=False)
      if cfg.get('final_component_policy','largest')=='all':discarded=0.
      current,_=reflect(from_tri(tm,current.generation))
      post_symmetry_components_removed=0;post_symmetry_discarded_surface_fraction=0.
      if cfg.get('final_component_policy','largest')=='largest':
        post=surface(current);parts=trimesh.graph.connected_components(post.face_adjacency,nodes=np.arange(len(post.faces)))
        if len(parts)>1:
          areas=np.array([post.area_faces[a].sum() for a in parts]);keep=int(np.argmax(areas));fraction=float((areas.sum()-areas[keep])/areas.sum())
          if fraction>.03:raise ValueError('Symmetry processing disconnected over 3% surface area')
          current=from_tri(post.submesh([parts[keep]],append=True,repair=False),current.generation)
          if symmetry_error(current)>1e-7:raise ValueError('Component selection would break bilateral symmetry')
          post_symmetry_components_removed=len(parts)-1;post_symmetry_discarded_surface_fraction=fraction
      final=validate(current,cfg['max_polygons']);final['symmetry_max_error']=symmetry_error(current);save(current,out/'result',g)
      delivered=trimesh.load(out/'result.obj',force='mesh',process=False);final['obj_reload_checks']=validate(from_tri(delivered),cfg['max_polygons'])
      ply=trimesh.load(out/'result.ply',force='mesh',process=False);final['ply_reload_checks']=validate(from_tri(ply),cfg['max_polygons'])
      dv=np.asarray(delivered.vertices).copy();dv[:,0]=2*g.origin[0]-dv[:,0]
      final['exported_obj_symmetry_max_error']=float(cKDTree(delivered.vertices).query(dv)[0].max())
      if not no_render:render(surface(current),out/'views',cfg['render_resolution'],framing);images.append((out/'views/front.png','FINAL / OPENING GUARD'));sheet(images,out/'progression.png',columns=4)
      record.update(status='COMPLETE',elapsed_seconds=time.perf_counter()-start,final=final,opening_removed_volume=removed,opening_disconnected_components_removed=(len(cc)-1 if cfg.get('final_component_policy','largest')=='largest' else 0),final_component_policy=cfg.get('final_component_policy','largest'),opening_discarded_surface_fraction=discarded,opening_residual_volume=abs(float((s^guard).volume())),result_sha256=sha(out/'result.obj'))
      record.update(post_symmetry_components_removed=post_symmetry_components_removed,post_symmetry_discarded_surface_fraction=post_symmetry_discarded_surface_fraction)
      write(out/'run.json',record);return record
    except Exception as e:
      record.update(status='FAILED',error=str(e),traceback=traceback.format_exc());write(out/'run.json',record);raise
