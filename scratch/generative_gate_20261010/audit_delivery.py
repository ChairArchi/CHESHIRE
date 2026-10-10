"""Collect run evidence without rewriting historical run manifests."""
from pathlib import Path
import json,hashlib
import numpy as np
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parent
names=['region_fans23','region_fibers23','region_fans_wide23','hierarchy_base23','hierarchy_twist23','hierarchy_sixfold23','hierarchy_microfold23','micro_simple_tissue23','micro_exposed_tissue23']
report={'runs':{},'limits':['Basic validity is not a self-intersection or fabrication certificate.','Tissue output is a multi-shell assembly, not a fused solid.']}
for name in names:
 path=ROOT/'runs'/name/'run.json'
 if not path.is_file():continue
 r=json.loads(path.read_text());report['runs'][name]={k:r[k] for k in ['status','input_sha256','config_sha256','result_sha256','elapsed_seconds','final'] if k in r}
p=ROOT/'runs/region_fibers23'
if (p/'12_tessellate/state.npz').is_file():
 before=np.load(p/'11_cc/state.npz');after=np.load(p/'12_tessellate/state.npz')
 distances=cKDTree(after['xyz']).query(before['xyz'])[0]
 report['tissue_target_preservation_after_symmetry']={'max_distance_to_preserved_target_vertex':float(distances.max()),'target_vertex_count':len(before['xyz']),'scope':'Immediately after Tissue and symmetry; before final opening Boolean'}
report['same_config_different_input']={
 'config_identical':report['runs']['region_fans23']['config_sha256']==report['runs']['region_fans_wide23']['config_sha256'],
 'input_different':report['runs']['region_fans23']['input_sha256']!=report['runs']['region_fans_wide23']['input_sha256'],
 'result_different':report['runs']['region_fans23']['result_sha256']!=report['runs']['region_fans_wide23']['result_sha256']}
for name in ['micro_simple_tissue23','micro_exposed_tissue23']:
 p=ROOT/'runs'/name/'20_tessellate'
 if not (p/'state.npz').is_file():continue
 before=np.load(ROOT/'runs/hierarchy_microfold23/19_crease_subdivide/state.npz');after=np.load(p/'state.npz')
 distances=cKDTree(after['xyz']).query(before['xyz'])[0]
 stage=json.loads((p/'stage.json').read_text())
 report[name+'_target_preservation']={'max_distance_after_symmetry':float(distances.max()),'target_vertex_count':len(before['xyz']),'before_symmetry_coordinate_error':stage['operator']['retained_target_max_coordinate_error'],'before_symmetry_topology_identical':stage['operator']['retained_target_topology_identical'],'selected_faces':stage['operator']['selected_target_faces'],'scope':'Tissue stage; final opening Boolean can cut geometry','input':'Unmodified simple porous cell, not a bundle motif'}
environment=json.loads((ROOT/'environment.json').read_text())
report['original_sources_unchanged']={path:hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in environment['sources'].items()}
comparison=ROOT/'runs/tissue_composition23/comparison.json'
if comparison.is_file():
 r=json.loads(comparison.read_text())
 report['tissue_composition_comparison']={'status':r['status'],'selected_faces':r['selected_target_faces'],'selection_fraction':r['selection_fraction'],'sources_unchanged':r.get('sources_unchanged'),
  'variants':{name:data['checks'] for name,data in r['variants'].items()}}
(ROOT/'validation_summary.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='runs'},indent=2))
