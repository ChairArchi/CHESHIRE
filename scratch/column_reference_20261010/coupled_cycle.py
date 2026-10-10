"""One explicit cycle: parent mass evolution -> fold -> independent child growth.
Parent evolution is a shape-preserving-sign curvature amplification hypothesis.
All positions derive from current ring geometry; no replacement radius profile.
"""
import json,argparse,subprocess,sys
import numpy as np
import fluted_generation as common
from recursive_strips import evolve

def run(gain,output):
    source=common.ROOT/'fluted_generation_results/g00/mesh.json'
    data=json.loads(source.read_text());v=np.array(data['vertices']);original=v.copy()
    levels=np.unique(v[:,2]);ids=[np.flatnonzero((abs(v[:,2]-z)<1e-7)&(np.linalg.norm(v[:,:2],axis=1)>1e-7)) for z in levels]
    radius=np.array([np.linalg.norm(v[k,:2],axis=1).mean() for k in ids]);events=[]
    for j in range(1,len(levels)-1):
        t=(levels[j]-levels[j-1])/(levels[j+1]-levels[j-1])
        interpolated=(1-t)*radius[j-1]+t*radius[j+1]
        departure=radius[j]-interpolated
        delta=float(np.clip(gain*departure,-.22*radius[j],.22*radius[j]))
        v[ids[j],:2]*=1+delta/radius[j]
        events.append(dict(ring=j,original_radius=float(radius[j]),neighbor_interpolated_radius=float(interpolated),radial_change=delta))
    parent=output/'parent';parent.mkdir(exist_ok=True,parents=True);common.OUT=parent
    mesh=common.Mesh.from_vertices_and_faces(v.tolist(),data['faces'])
    common.save(mesh,0,dict(operation='parent ring curvature amplification from actual adjacent sections',gain=gain,events=events,max_parent_displacement=float(np.linalg.norm(v-original,axis=1).max()),smoothing=False))
    folded=output/'folded';evolve(parent/'g00/mesh.json',folded,.3,8.,1,False)
    subprocess.run([sys.executable,'-B',str(common.ROOT/'based_child_refinement.py'),'--input-root',str(folded),'--output',str(output/'children')],check=True)
    (output/'cycle.json').write_text(json.dumps(dict(parent_source=str(source),phases=['parent/g00','folded/g01','children/g02'],parent_gain=gain,interpretation='Parent changes first; child sites and dimensions are recomputed from changed parent geometry.',limitations=['ring-structured column input','one cycle; not a generic full gate system','growth still uses D8 sector grouping inherited from the selected prototype','not recovered Hansmeyer coefficients']),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--gain',type=float,default=.4);p.add_argument('--output',type=common.Path,default=common.ROOT/'coupled_cycle_results');a=p.parse_args();run(a.gain,a.output.resolve())
