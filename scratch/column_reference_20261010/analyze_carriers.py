"""Controlled carrier comparison. Envelope measures are NOT solid section area."""
import json
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parent
cases={'uniform':'published_column_vertex7_results','area':'carrier_area_results','aspect':'carrier_aspect_results'}
report={};curves={};reference=None
for name,folder in cases.items():
    p=ROOT/folder;config=json.loads((p/'config.json').read_text())
    signature={k:config[k] for k in ['schedule','extrusion_gain','position_variation']}
    if reference is None:reference=signature
    assert signature==reference,'Generation rule changed across cases'
    d0=json.loads((p/'g00/mesh.json').read_text());d7=json.loads((p/'g07/mesh.json').read_text())
    v0=np.array(d0['vertices']);v7=np.array(d7['vertices'])
    assert d0['faces']==[[4*j+i,4*j+(i+1)%4,4*(j+1)+(i+1)%4,4*(j+1)+i] for j in range(3) for i in range(4)]+[[3,2,1,0],[12,13,14,15]]
    f7=np.array([[f[0],f[i],f[i+1]] for f in d7['faces'] for i in range(1,len(f)-1)])
    mesh=trimesh.Trimesh(v7,f7,process=False)
    stations=v0[::4,2];wx=np.array([np.ptp(v0[j:j+4,0]) for j in range(0,16,4)]);wy=np.array([np.ptp(v0[j:j+4,1]) for j in range(0,16,4)])
    zs=np.linspace(.04,7.96,61);source_x=np.interp(zs,stations,wx);source_y=np.interp(zs,stations,wy)
    envelope=[]
    for z in zs:
        lines=trimesh.intersections.mesh_plane(mesh,[0,0,1],[0,0,z])
        if len(lines):envelope.append(np.ptp(lines.reshape(-1,3),axis=0)[:2].tolist())
        else:envelope.append([float('nan'),float('nan')])
    envelope=np.array(envelope)
    before=np.sqrt(source_x*source_y);after=np.sqrt(envelope[:,0]*envelope[:,1]);gain=float(np.dot(before,after)/np.dot(before,before))
    normalized_error=float(np.sqrt(np.mean((after/gain-before)**2))/np.mean(before))
    tree=cKDTree(v7);mirror=[]
    for axis in (0,1):
        reflected=v7.copy();reflected[:,axis]*=-1;mirror.append(float(tree.query(reflected)[0].max()))
    d3=json.loads((p/'g03/mesh.json').read_text());v3=np.array(d3['vertices'])
    meta3=json.loads((p/'g03/operator_metadata.json').read_text())
    assert [r['id'] for r in meta3['points']]==list(range(len(v3)))
    meta4=json.loads((p/'g04/operator_metadata.json').read_text())
    corners=[r for r in meta4['points'] if r['point_class']=='corner']
    bands=[]
    for lo,hi in zip(np.linspace(0,8,9)[:-1],np.linspace(0,8,9)[1:]):
        values=[r['weights']['wp'] for r in corners if lo<=v3[r['source'],2]<hi]
        bands.append(dict(z=[float(lo),float(hi)],count=len(values),mean=float(np.mean(values)) if values else None,max=float(max(values)) if values else None))
    report[name]=dict(folder=str(p),initial_volume=json.loads((p/'g00/validation.json').read_text())['volume'],station_z=stations.tolist(),station_area=(wx*wy).tolist(),station_aspect=(wx/wy).tolist(),carrier_area_range_between_stations=[float((source_x*source_y).min()),float((source_x*source_y).max())],height=8.,initial_vertices=16,initial_faces=14,output_faces=len(d7['faces']),output_extents=np.ptp(v7,axis=0).tolist(),bilateral_vertex_error_xy=mirror,normalized_envelope_profile_rms=normalized_error,aspect_log_rms=float(np.sqrt(np.mean(np.log((envelope[:,0]/envelope[:,1])/(source_x/source_y))**2))),generation4_vertex_extrusion_by_height=bands)
    curves[name]=dict(z=zs.tolist(),carrier_width_x=source_x.tolist(),carrier_width_y=source_y.tolist(),output_envelope_x=envelope[:,0].tolist(),output_envelope_y=envelope[:,1].tolist())
    print(name,report[name]['output_extents'],report[name]['bilateral_vertex_error_xy'],flush=True)
out=ROOT/'carrier_comparison'
(out/'measurements.json').write_text(json.dumps(dict(cases=report,controls=reference,limitations=['Section envelope is the bounding rectangle, not material area.','Normalized profile error is a diagnostic, not a score of design quality.','Actual extrusion distances vary with current mesh perimeter even though coefficients are fixed.','Nonplanar quads are fan-triangulated consistently for these section measurements.']),indent=2))
(out/'section_curves.json').write_text(json.dumps(curves))
