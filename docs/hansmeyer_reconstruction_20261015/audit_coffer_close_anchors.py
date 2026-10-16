"""Read-only normal/screen/along-node explanation of existing close anchors."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

import numpy as np


REPO = Path(__file__).resolve().parents[2]
HERE = REPO/'experiments/hansmeyer_reconstruction_20261015'
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('readonly_coffer_v7', HERE/'run_spine_reconstruction_v7.py')
v7 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v7)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError('New-only audit output.')
    receipt = json.loads((args.root/'RECEIPT.json').read_text(encoding='utf8'))
    previous = json.loads(args.audit.read_text(encoding='utf8'))
    anchors = previous['source_anchors'][:8]
    with np.load(receipt['variants']['REFERENCE_NESTED']['control_quad'], allow_pickle=False) as z:
        xyz, chart = z['xyz'], z['chart']
    camera_position = np.asarray([-18.,28.,12.]); target = np.asarray([-.6,.72,6.6])
    forward = target-camera_position; forward /= np.linalg.norm(forward)
    right = np.cross(forward,[0.,0.,1.]); right /= np.linalg.norm(right)
    up = np.cross(right,forward)
    query_chart = []
    for anchor in anchors:
        ids = np.asarray(anchor['G7_quad_control_ids']); k = anchor['candidate_native_fan_corner']
        p, c = xyz[ids], chart[ids]
        native_points = np.stack((p[k],p[(k+1)%4],p.mean(axis=0)))
        normal = np.cross(native_points[1]-native_points[0],native_points[2]-native_points[0]); normal /= np.linalg.norm(normal)
        bary = np.asarray(anchor['candidate_native_barycentric'])
        source_chart = bary@np.stack((c[k],c[(k+1)%4],c.mean(axis=0)))
        query_chart.append(source_chart)
        displacement = np.asarray(anchor['displacement'])
        dn = float(displacement@normal)
        screen = np.asarray([displacement@right,-displacement@up])*900/1.25
        anchor.update(baseline_G7_native_fan_normal=normal.tolist(),
            displacement_normal_to_baseline_G7_fan=dn,
            displacement_tangential_to_baseline_G7_fan=float(np.linalg.norm(displacement-dn*normal)),
            frozen_close_displacement_pixels_xy=screen.tolist(), frozen_close_displacement_pixels_length=float(np.linalg.norm(screen)),
            source_chart=source_chart.tolist(), source_field_memberships=[])
    del xyz, chart
    query_chart = np.asarray(query_chart)
    for parent_index, info in enumerate(receipt['foundation']):
        saved = json.loads(Path(info['evidence']['description']).read_text(encoding='utf8'))
        tree = saved['tree']['formation']
        names = ('source_chart_transfer','quads_refined','delta_refined','logical_refined',
                 'logical_s','logical_chi','node_height','usable_base_width')
        with np.load(saved['array_file'], allow_pickle=False) as z:
            state = {key:z[tree[key]['npz_key']] for key in names}
        atlas = v7.BucketAtlas(state['source_chart_transfer'],state['quads_refined'],
                              state['delta_refined'],state['logical_refined'],verify_global=False)
        for sx,sy in ((1.,1.),(-1.,1.),(1.,-1.),(-1.,-1.)):
            query = query_chart.copy(); query[:,1] *= sx; query[:,2] *= sy
            delta,logical,valid = atlas.evaluate(query)
            taper = v7.spine.quintic((1-np.abs(logical[:,2]))/.22)*valid
            s = logical[:,0]*info['total_length']
            if not info['periodic']:
                pitch = np.asarray(info['formation']['node_pitch_quantiles'])[[0,-1]]
                taper *= v7.spine.quintic(s/(1.5*pitch[0]))*v7.spine.quintic((info['total_length']-s)/(1.5*pitch[1]))
            for i in np.flatnonzero(taper>0.):
                u = float(logical[i,2]); chi = float(np.interp(s[i],state['logical_s'],state['logical_chi']))
                node = float((.5+.5*np.cos(2*np.pi*chi))**2)
                h = float(np.interp(s[i],state['logical_s'],state['node_height']))
                section = float(np.interp(u,v7.spine.U_KNOTS,v7.spine.NECK_N+node*(v7.spine.NODE_N-v7.spine.NECK_N)))
                field_delta = delta[i]*np.asarray([sx,sy,1.])*taper[i]
                normal = np.asarray(anchors[i]['baseline_G7_native_fan_normal'])
                actual_delta = np.asarray(anchors[i]['displacement'])
                anchors[i]['source_field_memberships'].append(dict(parent_index=parent_index,component=info['component'],
                    phase_level=info['phase_level'],reflection=[sx,sy],support_taper=float(taper[i]),
                    parent_arc_fraction=float(logical[i,0]),parent_arc_s=float(s[i]),across_u=u,
                    along_node_chi=chi,node_envelope=node,nominal_height=h,
                    nominal_usable_base_width=float(np.interp(s[i],state['logical_s'],state['usable_base_width'])),
                    initial_cage_section_N_over_H=section,
                    saved_continuous_refined_field_delta=field_delta.tolist(),
                    saved_field_normal_to_baseline_G7_fan=float(field_delta@normal),
                    field_vs_native_interpolated_delta_error=float(np.linalg.norm(field_delta-actual_delta))))
    for anchor in anchors:
        anchor['source_field_memberships'].sort(key=lambda m:m['support_taper'],reverse=True)
    report = dict(kind='COFFER_EXISTING_CLOSE_ANCHOR_NORMAL_SCREEN_AND_NODE_PHASE_AUDIT',root=str(args.root),anchors=anchors,
        method='The already-registered G7 native fan/control IDs provide its actual baseline normal and unchanged source chart. Actual saved candidate−baseline anchor displacement is resolved into normal/tangent and frozen900px orthographic screen basis. Stored certified coffer source fields are queried by exact atlas membership to explain along-node phase; no nearest projection, new measurement or geometry is produced.',
        limitations=['All eight locations were inherited from old G6 ray hits. They are approximate registered source anchors, not new candidate image samples.',
            'Pixel displacement is geometric projection, without an occlusion test or claim that ornament contrast equals point movement.',
            'Continuous source-field queries and actual G7 fan interpolation can differ, particularly near support edges. Their difference is explicitly reported; exact equality is not asserted.',
            'Initial cage N/H explains intended node/neck section; it is not an exact post-subdivision visible pocket-depth measurement.',
            'Normal direction is the actual accepted G7 native fan normal at the registered anchor, not a smoothed or independently fitted ridge normal.',
            'No collision, full normal-angle scan or beauty certificate.'])
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(output=str(args.output),anchors=[dict(label=a['label'],delta=a['displacement_length'],
        normal=a['displacement_normal_to_baseline_G7_fan'],screen_pixels=a['frozen_close_displacement_pixels_length'],
        memberships=[dict(component=m['component'],u=m['across_u'],chi=m['along_node_chi'],node=m['node_envelope'],taper=m['support_taper']) for m in a['source_field_memberships']]) for a in anchors]),indent=2))


if __name__=='__main__': main()
