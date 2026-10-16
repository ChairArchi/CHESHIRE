"""Same193-sampling source-only comparison; original kernel unchanged."""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,sys
import numpy as np
from scipy.interpolate import PchipInterpolator
from layout_methods import measure_sections,compare_sections
from layout_methods_v2 import guards_at_same_material_scale,append_six_major_lobe_events
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
def read(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
def run(output):
 root=Path(output).resolve()
 if root.exists():raise FileExistsError(root)
 root.mkdir(parents=True)
 old=module("selective_v2_existing_driver",HERE.parent/"overlapping_fold_layout_20261017/replay_overlap.py")
 replay=old.load_module("selective_v2_original_replay",REPO/"experiments/end_rule_revision_20261014/replay.py")
 early=replay.early;sd=early.seed;legacy=sd.source.old.repair.legacy;original=copy.deepcopy(legacy.EVENTS)
 _,_,_,cfg,_=replay.exact_original_seed((1.,)*8);sampling=dict(rings=193,sectors=16,radius=.78)
 mesh,chart=sd.variation.carrier(sampling)
 def evaluate(events):
  with old.scoped_attributes([(legacy,"EVENTS",copy.deepcopy(events))]):return sd.legacy_core(chart,copy.deepcopy(cfg),"SPAN")
 baseline,baseparts=evaluate(original);profile=measure_sections(baseline,chart);guards=guards_at_same_material_scale(profile)
 warp=PchipInterpolator([0,.15,.33,.50,.70,.85,1],[0,.18,.34,.51,.72,.86,1])
 newevents,proposal=append_six_major_lobe_events(original,guards,warp)
 kcat=read(HERE.parent/"overlapping_fold_layout_20261017/overlap_recipes.json")
 oldk=next(r for r in kcat["recipes"] if r["id"]=="K08")
 k_events=old.resolved_seed_events(original,oldk["seed_events"])
 hierarchy=read(HERE/"selective_recipes.json")["candidates"]["S08_LOBES"]["resolved_legacy_events"]
 hierarchy={int(k):v for k,v in hierarchy.items()}
 cases=[("B193",original,dict(strategy="Original complete two-primary/three-ancillary source at same193 sampling")),
        ("L08_PRIMARY_193",newevents,proposal),
        ("K08_193",k_events,dict(strategy="Frozen previous all-eight-G1 source at same193 sampling")),
        ("S08_HIER_193",hierarchy,dict(strategy="Frozen v1 hierarchical eight-total source at same193 sampling"))]
 sources={str(REPO/k):v for k,v in early.code_hashes().items()}
 sources.update({str(HERE/n):sha(HERE/n) for n in ("layout_methods.py","layout_methods_v2.py","generate_selective_v2.py")})
 write(root/"BASELINE_GUARDS.json",dict(profile=profile.tolist(),guards=guards,guard_minimum_separation_material_t=4/48,
       same_material_scale_as49=True,carrier_sampling=sampling,source_code_sha256=sources))
 results=[]
 guardmask=np.logical_or.reduce([(chart[:,0]>=g["interval"][0])&(chart[:,0]<=g["interval"][1]) for g in guards])
 for cid,events,method in cases:
  folder=root/cid;folder.mkdir();xyz,parts=evaluate(events)
  actual=copy.deepcopy(mesh);actual.xyz=xyz;actual.surface="mean";actual.anchors[:,0]=np.arange(len(actual.faces));actual._chart_for_receipt=chart
  native=early.ancestry.task36_growth.native(actual);tri=native.faces[:,:3]
  checks=early.core.quick_checks(actual,native.xyz,tri)
  if not checks["passed"]:raise ValueError("Original geometry gate failed: "+cid)
  pairs=early.prior.helpers.existing.symmetry(chart);sym,fp=early.actual_symmetry(actual,dict(X=pairs[0],Y=pairs[1]))
  np.savez_compressed(folder/"control_quad.npz",xyz=xyz,faces=actual.faces,chart=chart,classes=actual.classes,rest=actual.rest,anchors=actual.anchors,generation=np.array(0),surface=np.array("mean"))
  np.savez_compressed(folder/"geometry.npz",xyz=native.xyz,faces=tri)
  delta=xyz-baseline;dist=np.linalg.norm(delta,axis=1)
  np.savez_compressed(folder/"operation_fields.npz",**parts,baseline_xyz=baseline,actual_added_delta=delta,waist_guard_vertex_mask=guardmask,
                      mirror_x_vertex_pairs=pairs[0],mirror_y_vertex_pairs=pairs[1],mirror_x_face_pairs=fp["X"],mirror_y_face_pairs=fp["Y"])
  exact=bool(np.array_equal(xyz[guardmask],baseline[guardmask]))
  if cid=="L08_PRIMARY_193" and not exact:raise ValueError("Support-based exact waist source proof failed.")
  rec=dict(schema="CHESHIRE_SELECTIVE_STRONG_MAJOR_SOURCE_V2",candidate=cid,source_G=0,carrier_sampling=sampling,
           original_seed_recipe=cfg,original_legacy_events=original,resolved_legacy_events=events,proposal=method,
           primary_event_count=len(events[1]),total_event_count=sum(len(v) for v in events.values()),
           checks=checks,symmetry=sym,waist_guards=guards,waist_comparison=compare_sections(profile,measure_sections(xyz,chart),guards),
           exact_full_original_guard_controls=exact,guard_controls=int(guardmask.sum()),
           guard_proof_scope="Actual material source controls only; horizontal-plane interpolation separately audited",
           actual_change=dict(affected_controls=int((dist>1e-12).sum()),fraction_affected=float(np.mean(dist>1e-12)),
                              fraction_delta_above_point1=float(np.mean(dist>.1)),maximum_delta=float(dist.max()),RMS_delta=float(np.sqrt(np.mean(dist**2)))),
           same_original_source_kernel=True,postXYZ_geometry_mask=False,new_primitive=False,smoothing=False,
           fresh_field_cache=False,no_G4_replay=True,self_intersections_certified=False,
           actual_files={n:dict(path=str(folder/n),sha256=sha(folder/n)) for n in ("geometry.npz","control_quad.npz","operation_fields.npz")},
           source_code_sha256=sources)
  write(folder/"generation.json",rec);results.append(rec)
  print("SELECTIVE_V2_G0_READY",cid,str(folder/"geometry.npz"),"guard_exact",exact,json.dumps(rec["actual_change"]),flush=True)
 write(root/"RECEIPT.json",dict(schema="CHESHIRE_SELECTIVE_STRONG_MAJOR_COMPARISON_V2",candidates=[r["candidate"] for r in results],
       same_sampling=sampling,source_code_sha256=sources,actual_geometry_frozen=True,self_intersections_certified=False))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args();run(a.output)

