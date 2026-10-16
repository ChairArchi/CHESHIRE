"""Read-only retained UV bounds and saved same-parent mirror-field agreement."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

import numpy as np

REPO=Path(__file__).resolve().parents[2]
HERE=REPO/'experiments/hansmeyer_reconstruction_20261015'
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('readonly_mirror_v7',HERE/'run_spine_reconstruction_v7.py')
v7=importlib.util.module_from_spec(spec);spec.loader.exec_module(v7)


def stats(x):
    return dict(count=len(x),probabilities=[0,.1,.5,.9,.99,1],values=np.quantile(x,[0,.1,.5,.9,.99,1]).tolist()) if len(x) else dict(count=0)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise FileExistsError('New-only audit output.')
    receipt=json.loads((args.root/'RECEIPT.json').read_text(encoding='utf8'))
    rows=[]
    for info in receipt['foundation']:
        saved=json.loads(Path(info['evidence']['description']).read_text(encoding='utf8'))
        ft=saved['tree']['foundation'];t=saved['tree']['formation']
        with np.load(saved['array_file'],allow_pickle=False) as z:
            uv=z[ft['source_uv0']['npz_key']]
            curve_uv=z[ft['source_curve']['uv']['npz_key']]
            s0=z[ft['source_curve']['s']['npz_key']]
            st={k:z[t[k]['npz_key']] for k in ('source_chart_transfer','quads_refined','delta_refined','logical_refined','logical_s','logical_chi','node_height')}
        row=dict(component=info['component'],periodic=info['periodic'],phase_origin=info['phase_origin'],node_count=info['node_count'],
            curve_uv_bounds=[curve_uv.min(0).tolist(),curve_uv.max(0).tolist()],
            full_footprint_uv_bounds=[uv.reshape(-1,2).min(0).tolist(),uv.reshape(-1,2).max(0).tolist()],
            curve_uv_first=curve_uv[0].tolist(),curve_uv_last=curve_uv[-1].tolist(),physical_arc_interval=[float(s0[0]),float(s0[-1])],
            mirror_component_orbit=info['mirror_component_orbit'],same_parent_reflection_checks=[])
        if info['component'] in (25,40):
            q0=v7.tube.qgrid(len(uv),info['periodic'])
            centre=uv.reshape(-1,2)[q0].mean(1)
            query=np.column_stack((centre[:,0],np.cos(centre[:,1]),np.sin(centre[:,1])))
            atlas=v7.BucketAtlas(st['source_chart_transfer'],st['quads_refined'],st['delta_refined'],st['logical_refined'],verify_global=False)
            d0,l0,v0=atlas.evaluate(query)
            def budget(logical,valid):
                s=logical[:,0]*info['total_length']
                side=v7.spine.quintic((1-np.abs(logical[:,2]))/.22)*valid
                end=np.ones(len(s))
                if not info['periodic']:
                    pitch=np.asarray(info['formation']['node_pitch_quantiles'])[[0,-1]]
                    end=v7.spine.quintic(s/(1.5*pitch[0]))*v7.spine.quintic((info['total_length']-s)/(1.5*pitch[1]))
                chi=np.interp(s,st['logical_s'],st['logical_chi'])
                height=np.interp(s,st['logical_s'],st['node_height'])
                node=(.5+.5*np.cos(2*np.pi*chi))**2
                return side*end,node,height
            c0,n0,h0=budget(l0,v0)
            for name,sx,sy in (('mirror_x',-1.,1.),('mirror_y',1.,-1.),('mirror_xy',-1.,-1.)):
                mirrored=query.copy();mirrored[:,1]*=sx;mirrored[:,2]*=sy
                d1,l1,v1=atlas.evaluate(mirrored)
                c1,n1,h1=budget(l1,v1)
                both=v0&v1&(c0>1e-6)&(c1>1e-6)
                core=both&(c0>.99)&(c1>.99)&(h0>.020)&(h1>.020)
                e=np.linalg.norm(d0*c0[:,None]-d1*np.asarray([sx,sy,1.])*c1[:,None],axis=1)
                row['same_parent_reflection_checks'].append(dict(reflection=name,coarse_quad_centres=len(query),
                    positive_support_in_both_fields=int(both.sum()),strong_core_in_both=int(core.sum()),
                    both_support_node_envelope_difference=stats(abs(n0[both]-n1[both])),
                    both_support_taper_difference=stats(abs(c0[both]-c1[both])),
                    both_support_tapered_field_reflection_error=stats(e[both]),
                    strong_core_node_envelope_difference=stats(abs(n0[core]-n1[core])),
                    strong_core_tapered_field_reflection_error=stats(e[core])))
        rows.append(row)
    report=dict(kind='COFFER_RETAINED_SOURCE_UV_AND_SAME_PARENT_REFLECTION_REVIEW',root=str(args.root),parents=rows,
        method='Read saved certified source UV and forming fields. Existing convex coarse-quad interior centres are evaluated by the stored exact-membership atlas, then reflected in the unchanged material chart. Overlap counts describe actual sampled positive support in the same source domain, not nearest-world matches. Saved phase interpolation and mirrored/tapered savedδ compare reflection agreement; no new geometry or model test.',
        limitations=['Interior-centre sampling can demonstrate overlap where found; zero hits do not prove continuous footprints disjoint.',
            'Same-parent reflected overlap is legitimate if it represents the same self-symmetric chain with agreeing phase/field. Disagreement can make maximum-confidence transfer select competing fields.',
            'No visual smoothness or collision certificate.'])
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
