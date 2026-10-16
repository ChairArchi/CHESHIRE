"""Read preserved actual controls only: axial reversals on material meridians."""
from pathlib import Path
import json
import numpy as np

ROOT = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states')

def main():
    result = {}
    for stage in ('G00_INPUT', 'G01_ANCESTRY', 'G02_OVERLAP', 'G03_WALL', 'G03_ROOT', 'G03_SIDEWALL', 'G04_NEUTRAL'):
        folder = ROOT/stage
        with np.load(folder/'control_quad.npz', allow_pickle=False) as data:
            xyz, chart, faces = data['xyz'], data['chart'], data['faces']
        edge = np.concatenate((faces[:, [0,1]], faces[:, [1,2]], faces[:, [2,3]], faces[:, [3,0]]))
        edge.sort(axis=1)
        edge = np.unique(edge, axis=0)
        delta_chart = chart[edge[:,1]]-chart[edge[:,0]]
        # Keep sidewall meridians only, never all cap edges / radial chart lines.
        side = np.all(np.linalg.norm(chart[edge,1:], axis=2) > .98, axis=1)
        meridian = side & (np.linalg.norm(delta_chart[:,1:], axis=1) < 1e-9) & (abs(delta_chart[:,0]) > 1e-10)
        chosen = edge[meridian]
        dt = delta_chart[meridian,0]
        dzdt = (xyz[chosen[:,1],2]-xyz[chosen[:,0],2])/dt
        zmid = xyz[chosen,2].mean(axis=1)
        tmid = chart[chosen,0].mean(axis=1)
        bad = dzdt < 0
        q = np.quantile(dzdt,[0,.01,.05,.5,.95,1]).tolist()
        row = dict(vertices=len(xyz), quads=len(faces), meridian_edges=len(chosen),
                   negative_axial_edges=int(bad.sum()), negative_fraction=float(bad.mean()),
                   dz_dt_quantiles=q,
                   negative_material_t_range=[float(tmid[bad].min()),float(tmid[bad].max())],
                   negative_actual_z_range=[float(zmid[bad].min()),float(zmid[bad].max())])
        if stage in ('G03_ROOT','G03_SIDEWALL'):
            with np.load(folder/'evidence.npz',allow_pickle=False) as data:
                keys=[k for k in data.files if any(w in k for w in ('face_event','face_role','vertex_birth','vertex_origin','inherited_root'))]
                row['lineage_keys']=keys
                for key in ('face_event_ids','face_roles'):
                    if key in data.files:
                        values, counts = np.unique(data[key], return_counts=True)
                        row[key+'_counts']={str(int(k)):int(v) for k,v in zip(values,counts)}
        result[stage]=row
        print(stage, json.dumps(row),flush=True)
    path=Path(__file__).with_name('diagnosis_axial_results.json')
    if path.exists(): raise FileExistsError(path)
    path.write_text(json.dumps(result,indent=2),encoding='utf8')

if __name__=='__main__': main()
