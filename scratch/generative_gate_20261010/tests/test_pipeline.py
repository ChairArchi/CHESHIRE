import sys,json,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np,pytest,trimesh
from gateflow.input import create_neutral,load,sha
from gateflow.pipeline import run
from gateflow.engine import validate,observe,smooth_graph

def config():
 return dict(schema='cheshire-generative/1',seed=23,field_radius=.12,feedback=.4,region_gain=[1.,1.,1.2,.6],max_polygons=20000,opening_retention=.85,render_resolution=128,stages=[dict(op='extrusion_growth',count=5,spacing=.15,rounds=2,fraction=.1,turn=.24),dict(op='cc',weights=dict(wf=.04,we=-.02,w1=.1),contrast=.05)])

def test_neutral_contract_and_hash_guard(tmp_path):
 p=create_neutral(tmp_path/'input');g=load(p)
 assert g.manifest['source_kind']=='synthetic_neutral_fixture'
 assert set(g.roles)=={0,1,2}
 assert validate(g.mesh,20000)['watertight']
 with (p/'mesh.obj').open('a') as f:f.write('\n# tamper\n')
 with pytest.raises(ValueError,match='hash'):load(p)

def test_end_to_end_determinism_seed_and_no_overwrite(tmp_path):
 p=create_neutral(tmp_path/'input');c=config()
 a=run(p,c,tmp_path/'a',no_render=True);b=run(p,c,tmp_path/'b',no_render=True);v=run(p,c,tmp_path/'variant',seed=71,no_render=True)
 assert a['status']==b['status']==v['status']=='COMPLETE'
 assert a['result_sha256']==b['result_sha256']
 assert a['result_sha256']!=v['result_sha256']
 assert a['final']['watertight'] and a['final']['zero_area_faces']==0
 assert all(s['checks']['symmetry_max_error']<1e-10 for s in a['stages'])
 assert a['final']['exported_obj_symmetry_max_error']<1e-12
 assert a['opening_residual_volume']<1e-9
 before=sha(tmp_path/'a/result.obj')
 with pytest.raises(FileExistsError):run(p,c,tmp_path/'a',no_render=True)
 assert sha(tmp_path/'a/result.obj')==before

def test_current_geometry_feedback_is_causal(tmp_path):
 p=create_neutral(tmp_path/'input');c=config()
 live=run(p,c,tmp_path/'live',no_render=True)
 frozen=copy.deepcopy(c);frozen['observation_mode']='frozen'
 old=run(p,frozen,tmp_path/'frozen',no_render=True)
 assert live['result_sha256']!=old['result_sha256']
 a=np.load(tmp_path/'live/02_cc/observations.npz');b=np.load(tmp_path/'frozen/02_cc/observations.npz')
 assert np.max(np.abs(a['face_field']-b['face_field']))>1e-4

def test_second_input_same_code_and_config(tmp_path):
 a=create_neutral(tmp_path/'a');b=create_neutral(tmp_path/'b',width=3.1,opening_width=1.8,depth=.8)
 c=config();ra=run(a,c,tmp_path/'ra',no_render=True);rb=run(b,c,tmp_path/'rb',no_render=True)
 assert ra['config_sha256']==rb['config_sha256']
 assert ra['input_sha256']!=rb['input_sha256'] and ra['result_sha256']!=rb['result_sha256']

def test_budget_unknown_operator_and_nonfinite_rejected(tmp_path):
 p=create_neutral(tmp_path/'input');c=config();c['stages']=[{'op':'not_a_real_operator'}]
 with pytest.raises(ValueError):run(p,c,tmp_path/'bad',no_render=True)
 c=config();c['feedback']=float('nan')
 with pytest.raises(ValueError):run(p,c,tmp_path/'nan',no_render=True)
 c=config();c['max_polygons']=10
 with pytest.raises(ValueError,match='budget'):run(p,c,tmp_path/'tiny',no_render=True)

def test_new_child_surface_is_used_by_next_growth(tmp_path):
 p=create_neutral(tmp_path/'input');c=config();c['stages'].insert(1,dict(op='extrusion_growth',frontier_only=True,count=5,spacing=.03,rounds=2,fraction=.13,turn=.25))
 a=run(p,c,tmp_path/'run',no_render=True)
 first=np.load(tmp_path/'run/01_extrusion_growth/operator_state.npz')
 second=json.loads((tmp_path/'run/02_extrusion_growth/stage.json').read_text())
 assert len(first['generated_faces'])>0 and second['operator']['initial_cap_count']>0
 assert second['checks']['polygons']>a['stages'][0]['checks']['polygons']

def test_libigl_measurements_are_saved_and_nonconstant(tmp_path):
 p=create_neutral(tmp_path/'input');run(p,config(),tmp_path/'run',no_render=True)
 a=np.load(tmp_path/'run/02_cc/observations.npz')
 assert np.isfinite(a['libigl_curvature']).all()
 assert np.ptp(a['libigl_curvature'])>1e-3
 assert a['principal_direction'].shape==a['positions'].shape

def test_headless_tissue_creates_real_porosity_and_symmetry(tmp_path):
 p=create_neutral(tmp_path/'input');c=config();c['max_polygons']=50000
 c['stages']=[dict(op='tissue',thickness=.009)]
 result=run(p,c,tmp_path/'tissue',no_render=True)
 mesh=trimesh.load(tmp_path/'tissue/result.obj',process=False)
 assert mesh.is_watertight and mesh.euler_number<0
 assert result['stages'][0]['operator']['operator'].startswith('object.polyhedral_wireframe')
 assert result['final']['exported_obj_symmetry_max_error']<1e-12
 assert result['final']['components']==1

def test_disconnected_vertex_fans_are_separated_without_moving_geometry():
 from gateflow.engine import from_tri,separate_vertex_fans
 a=trimesh.creation.icosphere(subdivisions=0);b=a.copy();b.apply_translation([3,0,0])
 mesh=trimesh.util.concatenate([a,b]);v=np.array(mesh.vertices);f=np.array(mesh.faces)
 # Join distinct shells at one topological vertex. No shared edge exists.
 f[f==len(a.vertices)]=0;used=np.unique(f);lookup=np.full(len(v),-1,int);lookup[used]=np.arange(len(used))
 m=from_tri(trimesh.Trimesh(v[used],lookup[f],process=False));out,count=separate_vertex_fans(m)
 assert count==1 and len(out.xyz)==len(m.xyz)+1
 assert np.array_equal(np.sort(np.unique(out.xyz,axis=0),axis=0),np.sort(np.unique(m.xyz,axis=0),axis=0))

def test_fold_directions_and_strengths_vary_with_actual_geometry(tmp_path):
 from gateflow.engine import fold_field
 p=create_neutral(tmp_path/'input');g=load(p);field=smooth_graph(np.random.default_rng(23).normal(size=len(g.mesh.xyz)),g.mesh,.1)
 field=np.tanh(field/max(np.std(field),1e-8));obs=observe(g.mesh,field,g.roles,config())
 a,meta,state=fold_field(g.mesh,obs,dict(radius=.2,angle=1.0,direction_phase=.2,domains=20),1,20000)
 b,_,other=fold_field(g.mesh,obs,dict(radius=.2,angle=1.0,direction_phase=1.4,domains=20),1,20000)
 assert len(state['axes'])>=4 and np.ptp(state['angles'])>1e-4
 assert np.linalg.matrix_rank(state['axes'])>=2
 assert np.linalg.norm(a.xyz-b.xyz)>1e-4

def test_selective_component_projection_keeps_target_and_reads_component(tmp_path):
 from gateflow.engine import tessellate,validate
 from gateflow import runtime
 p=create_neutral(tmp_path/'input');g=load(p)
 field=np.tanh(g.mesh.xyz[:,2]*2-1);obs=observe(g.mesh,field,g.roles,config());obs['openings']=g.openings;obs['structural_roles']=g.roles
 component=runtime.PROJECT/'components/fiber14/component.json'
 spec=dict(component=str(component),depth=1.1,selective=True,keep_target=True,fraction=.2,max_cells=40)
 out,meta,state=tessellate(g.mesh,obs,spec,1.,50000)
 assert 0<meta['selected_target_faces']<len(g.mesh.faces)
 assert meta['keep_target'] and state['selected_target_faces'].sum()==meta['selected_target_faces']
 assert meta['retained_target_max_coordinate_error']==0 and meta['retained_target_topology_identical']
 assert validate(out,50000)['watertight']
 assert len(out.faces)==len(g.mesh.faces)+meta['selected_target_faces']*meta['component_faces']
 changed=json.loads(component.read_text());changed['mapping']['xy_scale'][0]*=.7
 alternate=tmp_path/'changed_component.json';alternate.write_text(json.dumps(changed));spec['component']=str(alternate)
 other,other_meta,_=tessellate(g.mesh,obs,spec,1.,50000)
 assert other_meta['component_sha256']!=meta['component_sha256']
 assert not np.allclose(out.xyz,other.xyz)


def test_local_fans_and_fold_extrusion_respond_to_current_surface(tmp_path):
 from gateflow.engine import cc,pleat_flow,normal_extrude
 from gateflow.symmetry import symmetry_error
 g=load(create_neutral(tmp_path/'input'));m=g.mesh
 cfg=config();field=np.zeros(len(m.xyz));roles=g.roles
 for i in range(2):
  obs=observe(m,field,roles,cfg)
  m,_,state=cc(m,obs,dict(weights=dict(wf=0,we=0),contrast=0,edge_contrast=0),1,20000)
  roles=roles[state['parent_face']];field=np.zeros(len(m.xyz))
 obs=observe(m,field,roles,cfg);obs['openings']=g.openings
 spec=dict(frequency=4,amount=.8,convergence=.08,flow_angle=1.2,flow_smoothing=.04,fan_count=3,fan_radius=.16,fan_strength=1.,regional_contrast=.4)
 folded,_,state=pleat_flow(m,obs,spec,1,20000)
 uniform,_,_=pleat_flow(m,obs,dict(spec,fan_count=0,regional_contrast=0),1,20000)
 assert len(state['fan_centers'])>=3 and np.ptp(state['fan_potential'])>1e-3
 assert np.ptp(state['regional_gain'])>.1
 assert np.linalg.norm(folded.xyz-uniform.xyz)>1e-3
 assert symmetry_error(folded)<1e-10
 updated=observe(folded,field,roles,cfg)
 grown,_,state2=normal_extrude(folded,updated,dict(amount=.3,ridge_focus=True),1,20000)
 assert np.ptp(state2['resolved_gain'])>.1 and np.count_nonzero(state2['resolved_gain']==0)>0
 assert validate(grown,20000)['watertight']
 updated['openings']=g.openings
 _,_,again=pleat_flow(grown,updated,spec,1,20000)
 assert not np.allclose(state['phase'],again['phase'])


def test_regional_response_uses_opening_roles_and_current_geometry(tmp_path):
 from gateflow.engine import regional_response
 g=load(create_neutral(tmp_path/'input'));m=g.mesh
 obs=observe(m,np.zeros(len(m.xyz)),g.roles,config());obs['openings']=g.openings;obs['structural_roles']=g.roles
 gain,st=regional_response(m,obs,{})
 assert np.ptp(gain)>.1
 assert st['region_opening'].max()>.99 and st['region_opening'].min()<.1
 assert st['region_transition'].max()>.9
 other=dict(obs,structural_roles=np.zeros_like(g.roles))
 changed,other_st=regional_response(m,other,{})
 assert np.max(other_st['region_transition'])==0
 assert np.linalg.norm(gain-changed)>.1
 other=dict(obs,openings=[p+np.array([0,.3]) for p in g.openings])
 changed,other_st=regional_response(m,other,{})
 assert not np.allclose(st['region_opening'],other_st['region_opening'])


def test_blender_twist_is_scoped_symmetric_and_preserves_topology(tmp_path):
 from gateflow.engine import support_twist
 from gateflow.symmetry import symmetry_error
 g=load(create_neutral(tmp_path/'input'));m=g.mesh
 obs=observe(m,np.zeros(len(m.xyz)),g.roles,config());obs['structural_roles']=g.roles
 out,meta,st=support_twist(m,obs,dict(angle=1.2),1,20000)
 assert np.array_equal(out.faces,m.faces)
 assert np.linalg.norm(out.xyz-m.xyz)>.01 and symmetry_error(out)<1e-10
 top=m.xyz[:,2]>=np.quantile(m.xyz[:,2],.9)
 assert np.max(np.linalg.norm(out.xyz[top]-m.xyz[top],axis=1))<1e-6
 assert not meta['smoothing'] and not meta['topology_changed']
 assert validate(out,20000)['watertight']

def test_blender_crease_subdivision_preserves_corners_better_than_uncreased():
 from cheshire.reference_subdivision import cube
 from gateflow.engine import crease_subdivide
 from scipy.spatial import cKDTree
 m=cube(1.);obs=observe(m,np.zeros(len(m.xyz)),np.zeros(len(m.faces),int),config())
 sharp,meta,st=crease_subdivide(m,obs,dict(crease=1.),1,20000)
 smooth,_,_=crease_subdivide(m,obs,dict(crease=0.),1,20000)
 ds=cKDTree(sharp.xyz).query(m.xyz)[0].max();du=cKDTree(smooth.xyz).query(m.xyz)[0].max()
 assert ds<1e-6 and du>.01
 assert len(sharp.faces)==len(smooth.faces)==24
 assert meta['crease_count']==12
 assert validate(sharp,20000)['watertight']

def test_checkpoint_resume_matches_full_execution_and_rejects_other_prefix(tmp_path):
 p=create_neutral(tmp_path/'input');prefix=config();prefix['stages']=[dict(op='cc',weights=dict(wf=.025,we=0),contrast=0,edge_contrast=0)]
 run(p,prefix,tmp_path/'prefix',no_render=True)
 full=copy.deepcopy(prefix);full['stages'].append(dict(op='normal_extrude',amount=.035,ridge_focus=True))
 direct=run(p,full,tmp_path/'direct',no_render=True)
 resumed=run(p,full,tmp_path/'resumed',no_render=True,resume_stage=tmp_path/'prefix/01_cc')
 assert direct['result_sha256']==resumed['result_sha256']
 assert resumed['resumed_from']['completed_prefix_stages']==1
 assert len(resumed['stages'])==1 and resumed['stages'][0]['index']==2
 wrong=copy.deepcopy(full);wrong['stages'][0]['weights']['wf']=.3
 with pytest.raises(ValueError,match='prefix'):
  run(p,wrong,tmp_path/'wrong',no_render=True,resume_stage=tmp_path/'prefix/01_cc')

def test_opening_flow_orients_actual_tissue_component(tmp_path):
 from gateflow.engine import tessellate
 from gateflow import runtime
 g=load(create_neutral(tmp_path/'input'));obs=observe(g.mesh,np.zeros(len(g.mesh.xyz)),g.roles,config())
 obs['openings']=g.openings;obs['structural_roles']=g.roles
 spec=dict(component=str(runtime.PROJECT/'components/strand_curved/component.json'),selective=True,keep_target=True,max_cells=20,fraction=.15,orientation='opening_flow',rotation_shift=1,offset=.8)
 out,meta,st=tessellate(g.mesh,obs,spec,1,20000)
 assert np.ptp(st['rotation_weights'])>.5
 assert meta['orientation']=='opening_flow' and meta['retained_target_topology_identical']
 assert validate(out,20000)['watertight']

def test_actual_tissue_last_unused_and_overlay_have_distinct_face_composition(tmp_path):
 from gateflow.engine import tessellate,surface
 from gateflow.tissue_comparison import retained_faces,metrics
 from gateflow import runtime
 from scipy.spatial import cKDTree
 g=load(create_neutral(tmp_path/'input'));m=g.mesh
 selected=np.zeros(len(m.faces),bool);selected[[10,11,12,13]]=True
 obs=dict(field=np.zeros(len(m.xyz)),openings=g.openings,projection_selection=selected)
 spec=dict(component=str(runtime.PROJECT/'components/simple_micro_cell/component.json'),depth=1.6,offset=.35,overlap=1.,orientation='opening_flow')
 outputs={}
 for name,combine,keep in [('last','LAST',False),('unused','UNUSED',False),('overlay','LAST',True)]:
  out,meta,state=tessellate(m,obs,dict(spec,combine_mode=combine,keep_target=keep),1,20000)
  outputs[name]=out
  check=retained_faces(m,out,selected)
  assert check['selected_original_faces_remaining']==(4 if keep else 0)
  assert check['unused_original_faces_remaining']==(len(m.faces)-4 if name!='last' else 0)
  basic=metrics(surface(out))
  assert basic['watertight']==(name!='unused')
  if name=='unused':assert basic['boundary_edges']>0
 for name in ['unused','overlay']:
  assert cKDTree(outputs[name].xyz).query(outputs['last'].xyz)[0].max()<1e-7
 assert len(outputs['overlay'].faces)-len(outputs['unused'].faces)==4
