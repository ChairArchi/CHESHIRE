"""One-step additive/shoulder-growth intervention on the SAME V01 G7 input."""
import argparse,json,shutil,sys
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task35_research import ROOT,SOURCES,checkpoint,preflight
from task33_preserve import sha,write_new
from hero_design_sprint import guarded
from cheshire.task35_columns import refold
from task35_analyze import material_edge,child_valleys,region


def probe(tag):
    job=ROOT/'candidates/V01_COLUMN';source=job/'G7_PRE';request=json.loads((job/'request.json').read_text());cost=preflight(request)
    dest=ROOT/'diagnostics'/tag;dest.mkdir(parents=True,exist_ok=False);write_new(dest/'request.json',dict(source_stage=str(source),source_sha256=sha(source/'mesh.npz'),base_recipe=request,intervention='Only positive-growth coupling in this last operation. Earlier formation/refolding and incoming geometry fixed.'))
    write_new(dest/'preflight.json',cost);identities={}
    for rel in SOURCES+['tools/task35_probe.py','tools/task35_analyze.py']:
        target=dest/'source'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/rel,target);identities[rel]=sha(target)
    write_new(dest/'source_identity.json',identities)
    state=dict(np.load(source/'formation_state.npz'));outputs={};controls={}
    for coupling in ['additive','shoulders']:
        out,c,features=refold(state,state,'regional',dict(request['refold'],growth_coupling=coupling));stage=dest/('G7_'+coupling.upper())
        checkpoint(stage,out,7,dict(operation='Same-incoming-mesh single-step counterfactual',growth_coupling=coupling),source,controls=c,features=dict(source_stage=str(source),source_mesh_sha256=sha(source/'mesh.npz'),features=features))
        outputs[coupling]=out;controls[coupling]=c
    reference=dict(np.load(job/'G3_FORM/formation_state.npz'));parent=dict(np.load(job/'G4_FOLD/formation_state.npz'));tracks=[]
    for s in reference['s']:
        if not 400<=s*4000<=3600:continue
        pi=int(np.flatnonzero(np.isclose(parent['s'],s,atol=1e-14,rtol=0))[0]);ri=int(np.flatnonzero(np.isclose(state['s'],s,atol=1e-14,rtol=0))[0]);_,p=material_edge(parent,pi);counts={};depths={}
        for name,out in outputs.items():
            _,v=material_edge(out,ri);valleys=child_valleys(p,v);counts[name]=len(valleys);depths[name]=[v['depth'] for v in valleys]
        tracks.append(dict(original_z=float(s*4000),region=region(s*4000),valley_counts=counts,depths=depths))
    sites=[]
    for z in [420,465,510,2725,3062.5,3175]:
        row=int(np.argmin(abs(state['s']*4000-z)));sites.append(dict(original_z=float(state['s'][row]*4000),
            radial_control_ranges={k:[float(c['requested_signed_distance'][row].min()),float(c['requested_signed_distance'][row].max())] for k,c in controls.items()}))
    write_new(dest/'result.json',dict(source_mesh_sha256=sha(source/'mesh.npz'),
        additive_reproduces_original_native_sha=sha(dest/'G7_ADDITIVE/mesh.npz')==sha(job/'G7_FOLD/mesh.npz'),
        sites=sites,material_tracks=tracks,coverage={k:sum(bool(t['valley_counts'][k]) for t in tracks) for k in outputs},denominator=len(tracks),
        actual_scalar_sum_error_max=float(abs(controls['shoulders']['requested_signed_distance']-controls['shoulders']['primary_fold_component']-controls['shoulders']['growth_after_coupling']).max()),
        limits='Last-operation counterfactual, not a complete recursive candidate; material-edge evidence is finite and separate from actual triangle-section audits.',producer_sha256=sha(Path(__file__))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if not a.tag.replace('_','').isalnum():raise ValueError('Fresh safe tag required.')
    if a.worker:probe(a.tag)
    else:
        preflight(json.loads((ROOT/'candidates/V01_COLUMN/request.json').read_text()));logs=ROOT/'logs'/('probe_'+a.tag)
        if logs.exists():raise FileExistsError(logs)
        result=guarded(['--worker','--tag',a.tag],logs,worker_script=Path(__file__));write_new(ROOT/'resources'/('probe_'+a.tag+'.json'),result);print(json.dumps(result))
        if result['exit_code']:raise SystemExit(result['exit_code'])
