"""Evaluate selective source layouts through the unchanged original SPAN constructor."""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,sys
import numpy as np
from scipy.interpolate import PchipInterpolator
from layout_methods import measure_sections,waist_guards,compact_events,phase_events,compare_sections
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def run(output):
    root=Path(output).resolve()
    if root.exists():raise FileExistsError(root)
    root.mkdir(parents=True)
    old=module("selective_existing_driver",HERE.parent/"overlapping_fold_layout_20261017/replay_overlap.py")
    replay=old.load_module("selective_original_replay",REPO/"experiments/end_rule_revision_20261014/replay.py")
    early=replay.early;sd=early.seed;legacy=sd.source.old.repair.legacy
    original=copy.deepcopy(legacy.EVENTS)
    _,_,_,cfg,_=replay.exact_original_seed((1.,)*8)
    carrier=dict(rings=49,sectors=16,radius=.78)
    mesh,chart=sd.variation.carrier(carrier)
    def evaluate(events):
        with old.scoped_attributes([(legacy,"EVENTS",copy.deepcopy(events))]):
            return sd.legacy_core(chart,copy.deepcopy(cfg),"SPAN")
    baseline,baseparts=evaluate(original)
    primary_events={1:copy.deepcopy(original[1]),2:[],3:[]}
    primary,primary_parts=evaluate(primary_events)
    profile=measure_sections(baseline,chart);guards=waist_guards(profile)
    warp=PchipInterpolator([0,.15,.33,.50,.70,.85,1],[0,.18,.34,.51,.72,.86,1])
    recipes=[]
    for cid,n in (("S06_LOBES",4),("S08_LOBES",6)):
        events,proposal=compact_events(original,guards,warp,n);recipes.append((cid,events,proposal))
    events,proposal=phase_events(original,guards,warp);recipes.append(("S08_PHASE",events,proposal))
    source_hashes=early.code_hashes()
    sources={str(REPO/k):v for k,v in source_hashes.items()}
    sources.update({str(HERE/n):sha(HERE/n) for n in ("layout_methods.py","generate_selective.py")})
    write(root/"BASELINE_WAIST_MEASUREMENTS.json",dict(profile_columns=["material_t","equivalent_area_radius","maximum_radius","signed_polygon_area_abs","median_physical_Z"],profile=profile.tolist(),guards=guards,
         sampling=carrier,method="Actual original49 carrier section polygons; material sections, not horizontal plane intersections",original_primary_events=original[1]))
    results=[]
    for cid,events,proposal in recipes:
        folder=root/cid;folder.mkdir()
        xyz,parts=evaluate(events)
        actual=copy.deepcopy(mesh);actual.xyz=xyz;actual.surface="mean";actual.anchors[:,0]=np.arange(len(actual.faces))
        native=early.ancestry.task36_growth.native(actual);tri=native.faces[:,:3]
        actual._chart_for_receipt=chart
        checks=early.core.quick_checks(actual,native.xyz,tri)
        if not checks["passed"]:raise ValueError("Original source geometry gate failed: "+cid)
        pairs=early.prior.helpers.existing.symmetry(chart)
        symmetry,face_pairs=early.actual_symmetry(actual,dict(X=pairs[0],Y=pairs[1]))
        np.savez_compressed(folder/"control_quad.npz",xyz=xyz,faces=actual.faces,chart=chart,classes=actual.classes,rest=actual.rest,anchors=actual.anchors,generation=np.array(0),surface=np.array("mean"))
        np.savez_compressed(folder/"geometry.npz",xyz=native.xyz,faces=tri)
        delta=xyz-primary;dist=np.linalg.norm(delta,axis=1)
        np.savez_compressed(folder/"operation_fields.npz",**parts,primary_only_xyz=primary,secondary_delta=delta,
                            guard_vertex_mask=np.logical_or.reduce([(chart[:,0]>=g["interval"][0])&(chart[:,0]<=g["interval"][1]) for g in guards]))
        newprofile=measure_sections(xyz,chart);guard_stats=compare_sections(profile,newprofile,guards)
        rec=dict(schema="CHESHIRE_SELECTIVE_ORIGINAL_FOLD_SOURCE_V1",candidate=cid,source_G=0,carrier_sampling=carrier,
                 original_seed_recipe=cfg,original_legacy_events=original,resolved_legacy_events=events,proposal=proposal,
                 unchanged_original_primary_two=True,existing_initial_memory_valley_recomputed=True,
                 post_XYZ_mask_or_projection=False,new_primitive=False,smoothing=False,field_layout_changed=False,
                 checks=checks,symmetry=symmetry,waist_comparison=guard_stats,
                 secondary_visible_geometry=dict(controls_affected=int((dist>1e-12).sum()),fraction_affected=float(np.mean(dist>1e-12)),
                     fraction_delta_above_point1=float(np.mean(dist>.1)),maximum_delta=float(dist.max()),RMS_delta=float(np.sqrt(np.mean(dist**2)))),
                 closed_source_only=True,self_intersection_certified=False,
                 actual_files={n:dict(path=str(folder/n),sha256=sha(folder/n)) for n in ("geometry.npz","control_quad.npz","operation_fields.npz")},source_code_sha256=sources)
        write(folder/"generation.json",rec);results.append(rec)
        print("SELECTIVE_G0_READY",cid,str(folder/"geometry.npz"),json.dumps(rec["secondary_visible_geometry"]),json.dumps(guard_stats),flush=True)
    write(root/"RECEIPT.json",dict(schema="CHESHIRE_SELECTIVE_FOLD_G0_COMPARISON_V1",candidates=[r["candidate"] for r in results],
        parent_source_kernel_unchanged=True,all_actual_source_checks_passed=True,source_code_sha256=sources,
        field_overlap_not_applied=True,self_intersection_certified=False))
    return results
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args();run(a.output)

