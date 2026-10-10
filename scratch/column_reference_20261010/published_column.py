"""Plain column -> extended CC/DS, Hansmeyer (2010), equations 1-6.

No reference-profile loft, flute cutter, fin primitives, parent restoration,
or post-smoothing. Coefficients are documented experimental schedules.
"""
import argparse,json
import numpy as np
import fluted_generation as common
from cheshire.weighted_doosabin import weighted_doosabin_once
from cheshire.generational_subdivision import generational_subdivide_once
from cheshire.execution import ExecutionBudget

def seed(carrier=None):
    vertices=[[x,y,z] for z in [0.,8/3,16/3,8.] for x,y in [(-1.,-1.),(1.,-1.),(1.,1.),(-1.,1.)]]
    faces=[[4*j+i,4*j+(i+1)%4,4*(j+1)+(i+1)%4,4*(j+1)+i] for j in range(3) for i in range(4)]
    faces.extend([[3,2,1,0],[12,13,14,15]])
    if carrier:
        areas=carrier.get('areas',[1.,1.,1.,1.]);ratios=carrier.get('ratios',[1.,1.,1.,1.])
        if len(areas)!=4 or len(ratios)!=4 or any(not np.isfinite(x) or x<=0 for x in areas+ratios):raise ValueError('Four positive finite station areas and ratios required')
        for j,(area,ratio) in enumerate(zip(areas,ratios)):
            for k in range(4):
                vertices[4*j+k][0]*=float(np.sqrt(area*ratio))
                vertices[4*j+k][1]*=float(np.sqrt(area/ratio))
        if carrier.get('equal_volume',False):
            volume=common.triangles(vertices,faces).volume
            factor=float(np.sqrt(32./volume))
            for v in vertices:v[0]*=factor;v[1]*=factor
    return common.Mesh.from_vertices_and_faces(vertices,faces)

SCHEDULE=[
    dict(scheme='cc',w1=-.6,w2=-.7,wf=.055,we=-.012,wp=.005),
    dict(scheme='ds',face=[-.35,-.012],edge=[0.,0.],vertex=[0.,0.]),
    dict(scheme='ds',face=[.10,-.012],edge=[.25,.105],vertex=[.20,.050]),
    dict(scheme='cc',w1=-.3,w2=-.3,wf=.035,we=-.012,wp=.012),
    dict(scheme='cc',w1=.0,w2=-.5,w3=.5,w4=.2,wf=-.008,we=.032,wp=.015),
    dict(scheme='ds',face=[.20,.014],edge=[.1,.030],vertex=[.1,.025]),
]

def run(config,output):
    mesh=seed(config.get('carrier'));common.OUT=common.ROOT/output;common.OUT.mkdir(exist_ok=True)
    (common.OUT/'config.json').write_text(json.dumps(config,indent=2))
    common.save(mesh,0,dict(seed='connected rectangular carrier, three equal axial cells',carrier=config.get('carrier',dict(areas=[1.]*4,ratios=[1.]*4)),handmade_ornament=False))
    budget=ExecutionBudget(config.get('max_faces',300000),config.get('max_vertices',300000))
    origins=None;families=None;previous=None
    for g,row in enumerate(config['schedule']):
        per={f:sum(np.linalg.norm(np.array(mesh.vertex_coordinates(a))-mesh.vertex_coordinates(b)) for a,b in mesh.face_halfedges(f)) for f in mesh.faces()}
        # Optional position field is paper section 3.2.1, not shape primitives.
        # Default uniform matches section 3.1 and isolates the core operators.
        factor={f:1. for f in mesh.faces()}
        if config.get('position_variation'):
            allz=[mesh.vertex_coordinates(v)[2] for v in mesh.vertices()];lo,hi=min(allz),max(allz)
            for f in mesh.faces():
                z=(mesh.face_centroid(f)[2]-lo)/(hi-lo)
                factor[f]=float(np.interp(z,[0.,.25,.5,.75,1.],[.6,1.25,.75,1.1,.65]))
        scale={f:float(per[f]*factor[f]*config['extrusion_gain']) for f in mesh.faces()}
        # Opt-in preservation-period trial: geometry-dependent late growth budget.
        # This is a current-face heuristic, NOT persistent parent/child age control.
        local_info=None
        if config.get('late_geometry_control') and g+1>=5:
            keys=list(mesh.faces());normals={f:np.asarray(mesh.face_normal(f)) for f in keys}
            bend=np.array([np.mean([max(0.,1-float(np.dot(normals[f],normals[n]))) for n in mesh.face_neighbors(f)] or [0.]) for f in keys])
            perimeter=np.array([per[f] for f in keys]);weight=np.array([scale[f] for f in keys])
            raw=np.clip((.5+.5*np.sqrt(np.median(perimeter)/np.maximum(perimeter,1e-12)))/(1+2*bend),.25,2.)
            gain=raw/np.average(raw,weights=weight)
            for f,m in zip(keys,gain):scale[f]*=float(m)
            np.savez_compressed(common.OUT/f'g{g+1:02d}_growth_field.npz',face_ids=keys,perimeter=perimeter,bend=bend,multiplier=gain)
            local_info=dict(rule='clip((.5+.5*sqrt(median_perimeter/perimeter))/(1+2*mean_neighbor_normal_bend),.25,2); normalized by original face displacement scale',range=[float(gain.min()),float(gain.max())],mean_weighted=float(np.average(gain,weights=weight)),semantic_parent_hierarchy=False)
        if row['scheme']=='cc':
            pw={'face':{},'edge':{},'corner':{}}
            for f in mesh.faces():pw['face'][f]={'wf':row['wf']*scale[f]}
            for a,b in mesh.edges():
                fs=[mesh.halfedge[a][b],mesh.halfedge[b][a]]
                pw['edge'][(a,b)]={'we':row['we']*sum(scale[f] for f in fs)/2}
            for v in mesh.vertices():
                fs=mesh.vertex_faces(v);pw['corner'][v]={'wp':row['wp']*sum(scale[f] for f in fs)/len(fs)}
            weights={k:row.get(k,0.) for k in ['w1','w2','w3','w4']}
            # Eq 4 only applies with genuine immediately preceding CC origins.
            result=generational_subdivide_once(mesh,weights,point_weights=pw,origin_lineage=origins if previous=='cc' else None,current_generation=g,budget=budget)
            origins=result.origin_lineage;families=None
            participation=result.metadata['later_generation_face_stencil']
            participation={k:v for k,v in participation.items() if k not in ['applications','fallbacks']}
        else:
            families=families if previous=='ds' else None
            params={};mapping={'FACE_DERIVED':'face','EDGE_DERIVED':'edge','VERTEX_DERIVED':'vertex'}
            for f in mesh.faces():
                label=mapping[families[f]['class']] if families else 'face'
                w1,w10=row[label];params[f]={'w1':w1,'w10':w10*scale[f]}
            result=weighted_doosabin_once(mesh,face_families=families,face_weights=params,current_generation=g,budget=budget)
            families=result.face_families;origins=None
            participation=dict(input_families=result.metadata['input_family_counts'],output_families=result.metadata['family_counts'],unsupported_polygons=result.metadata['fallback_faces'])
        previous=row['scheme'];mesh=result.mesh
        common.save(mesh,g+1,dict(operator=row,participation=participation,extrusion_gain=config['extrusion_gain'],normal_scale='current face perimeter; incident mean for edge/vertex',restored_parent_vertices=0,final_smoothing=False,late_geometry_control=local_info))
        (common.OUT/f'g{g+1:02d}'/'operator_metadata.json').write_text(json.dumps(result.metadata))
    return mesh

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='published_column_results');p.add_argument('--gain',type=float,default=1.);p.add_argument('--generations',type=int,default=6);p.add_argument('--config');p.add_argument('--position-variation',action='store_true');a=p.parse_args()
    config=json.loads(common.Path(a.config).read_text()) if a.config else dict(schedule=SCHEDULE[:a.generations],extrusion_gain=a.gain,position_variation=a.position_variation,source='Hansmeyer, Subdivision Beyond Smoothness, 2010, equations 1-6; coefficients are not supplied for the published column')
    run(config,a.output)
