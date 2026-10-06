"""Real polygon projections with frozen cameras, and compact comparative tables."""
import argparse
from collections import Counter
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
for f in ('rhino','examples','tools'): sys.path.insert(0,str(ROOT/f))
from cheshire.artifact_root import ArtifactRoot
from cheshire.sharp_subdivision import topology_motifs
from compas.datastructures import Mesh
from exchange import validate_mesh_data
from beyond_smoothness_verify import read,write

def study_mesh(data):
    # Task-local headless display ceiling; the existing Rhino demo stays at 50k.
    validate_mesh_data(data,max_vertices=600000,max_faces=300000,allow_polygons=True)
    mesh=Mesh()
    for v in data['vertices']:
        mesh.add_vertex(key=v['id'],x=v['xyz'][0],y=v['xyz'][1],z=v['xyz'][2])
    for f in data['faces']: mesh.add_face(f['vertices'],fkey=f['id'])
    return mesh

def prepare(root,phases,selected=(),checkpoints=False):
    root=ArtifactRoot(root); frames=[]; sheets=[]; tables=[]
    camera=read(ROOT/'studies/task21/camera.json')['bounds']; image_root=root.resolve('renders'); image_root.mkdir(parents=True,exist_ok=True)
    for phase in phases:
        pictures=[]
        for case in sorted(root.resolve('study/'+phase).glob('*')):
            attempts=sorted(case.glob('attempt_*/summary.json'))
            if not attempts: continue
            directory=attempts[-1].parent; summary=read(attempts[-1]); geometry_path=directory/'terminal.json'
            stages=summary.get('stages',[]); last=stages[-1] if stages else {}; d=last.get('diagnostics',{})
            tables.append(dict(id=case.name,phase=phase,status=summary['status'],geometry_state=summary.get('geometry_state'),
                family=summary.get('recipe',{}).get('family'),input=summary.get('recipe',{}).get('input'),reason=summary.get('reason'),
                stages=len(stages),geometry_sha256=summary.get('output_sha256'),statistics=summary.get('terminal_statistics'),
                dihedral=d.get('dihedral_degrees'),high_dihedral_edge_fraction=d.get('high_dihedral_edge_fraction'),
                local_normal_variation=d.get('local_normal_variation'),distributions=d.get('distributions'),motifs=d.get('motif_histogram'),
                fan_warnings=len(d.get('opposed_fan_normals',[])),bilinear_warnings=len(d.get('bilinear_admissibility_warning_faces',[])),
                degenerate=len(d.get('degenerate_fan_faces',[])),crossings=last.get('crossings'),cross_cell_sharp_components=d.get('cross_cell_sharp_components'),
                monitor=last.get('monitor'),seconds=summary.get('runtime_seconds'),process=summary.get('process'),artifact=root.reference(directory)))
            if not geometry_path.exists(): continue
            gate=summary.get('recipe',{}).get('input') in ('C0','C07','ORDERED_CORE')
            views=('front','oblique') if gate else ('oblique',)
            for view in views:
                target='renders/'+phase+'_'+case.name+'_'+view+'.png'
                bounds=camera[view] if gate else [-2.2,2.2,-3.8,3.8]
                data=read(geometry_path)
                outside=sum(not(bounds[0]<=v['xyz'][0]+(.65*v['xyz'][1] if view!='front' else 0)<=bounds[1]
                    and bounds[2]<=v['xyz'][2]+(.30*v['xyz'][1] if view!='front' else 0)<=bounds[3]) for v in data['vertices'])
                tables[-1].setdefault('outside_fixed_camera_vertices',{})[view]=outside
                label=case.name+' '+(summary.get('geometry_state') or 'NOT_MEASURED')+(f' CLIPPED:{outside}V' if outside else '')
                frames.append(dict(mesh=root.reference(geometry_path),file=target,label=label,
                    camera=view,bounds=bounds,width=600,height=600))
                if view=='oblique': pictures.append(target)
            if case.name in selected:
                geometry=read(geometry_path); mesh=study_mesh(geometry); lineage=read(directory/'terminal_lineage.json.gz')
                motif=topology_motifs(mesh); classes={s.key():i for i,s in enumerate(sorted(set(motif.values())))}
                codes={f:classes[motif[mesh.face_vertices(f)[0]].key()] for f in mesh.faces()}
                high_faces=set(d.get('high_dihedral_faces',[]))
                modes={'motif':(codes,'Color = first ordered corner topology motif; see legend JSON'),
                    'sharp':({f:6 if f in high_faces else 0 for f in mesh.faces()},'red: adjacent to >=45 degree edge / gray: other'),
                    'ancestry':({f:12+min(lineage['source_cells'].get(str(f),[0]))%24 for f in mesh.faces()},'Repeating colors: frozen source-cell ID modulo24; full IDs in lineage'),
                    'lock':({f:4 if any(v in {v for group in summary['recipe'].get('locks',{}).get('groups',{}).values() for v in group['vertices']} for v in mesh.face_vertices(f)) else 0 for f in mesh.faces()},'green: incident to literal tagged corner descendant / gray: other')}
                contacts={f for pair in last.get('crossings',{}).get('contacts',[]) for f in pair['faces']}
                bilinear=set(d.get('bilinear_admissibility_warning_faces',[])); fan=set(d.get('opposed_fan_normals',[]))
                modes['warnings']=({f:6 if f in contacts else 7 if f in bilinear else 3 if f in fan else 0 for f in mesh.faces()},
                    'red: sampled contact face / yellow: bilinear warning / purple: opposed fan / gray: other; no collision certificate')
                # Lock vertices are explicit in the per-case source graph, not inferred from XYZ.
                groups=read(directory/'source_graph.json')['locking_group']; locked={v for g in groups.values() for v in g['vertices']}
                active=summary['recipe']['schedule']['generations']<=summary['recipe']['locks']['iterations']
                modes['lock']=({f:(4 if active else 2) if any(v in locked for v in mesh.face_vertices(f)) else 0 for f in mesh.faces()},'green: active tagged corner / orange: released tag / gray: other; no edge/face propagation')
                write(root.resolve('renders/'+phase+'_'+case.name+'_motif_legend.json'),classes)
                for mode,(codes,legend) in modes.items():
                    display_path=geometry_path; label=case.name+' '+mode
                    if mode=='lock' and summary['recipe'].get('finish'):
                        # Locks apply to CC, not terminal Mola geometry. Do not
                        # infer event-descendant tag membership from integer IDs.
                        checkpoint=directory/('G'+str(summary['recipe']['schedule']['generations'])+'.json.gz')
                        locked_mesh=study_mesh(read(checkpoint))
                        codes={f:(4 if active else 2) if any(v in locked for v in locked_mesh.face_vertices(f)) else 0 for f in locked_mesh.faces()}
                        display_path=root.resolve('renders/'+phase+'_'+case.name+'_lock_checkpoint.json')
                        write(display_path,read(checkpoint)); label+=' pre-finish CC'
                        legend+=' / pre-finish CC checkpoint; no Mola tag inference'
                    codepath='renders/'+phase+'_'+case.name+'_'+mode+'.json'; write(root.resolve(codepath),codes)
                    frames.append(dict(mesh=root.reference(display_path),file='renders/'+phase+'_'+case.name+'_'+mode+'.png',
                        label=label,camera='oblique',bounds=camera['oblique'] if gate else [-2.2,2.2,-3.8,3.8],
                        width=600,height=600,depthfile=codepath,legend=legend))
                for name in ('detail','wireframe'):
                    frames.append(dict(mesh=root.reference(geometry_path),file='renders/'+phase+'_'+case.name+'_'+name+'.png',label=case.name+' '+name,
                        camera='front',bounds=camera['detail'] if gate else [-2.2,2.2,-3.8,3.8],width=600,height=600,wireframe=name=='wireframe'))
                if checkpoints:
                    sequence=[]
                    for checkpoint in ('G0','G1','G2','G3','G5','G6'):
                        actual=directory/(checkpoint+'.json.gz')
                        if not actual.exists(): continue
                        path='renders/'+phase+'_'+case.name+'_'+checkpoint+'.json'; write(root.resolve(path),read(actual))
                        target='renders/'+phase+'_'+case.name+'_'+checkpoint+'.png'; sequence.append(target)
                        frames.append(dict(mesh=path,file=target,label=case.name+' '+checkpoint,camera='oblique',
                            bounds=camera['oblique'] if gate else [-2.2,2.2,-3.8,3.8],width=600,height=600))
                    sheets.append(dict(file='renders/'+phase+'_'+case.name+'_sequence.png',title=case.name+' actual generation sequence / same camera and scale',images=sequence,columns=3,width=600,height=600))
        for start in range(0,len(pictures),12):
            sheets.append(dict(file='renders/'+phase+f'_sheet_{start//12+1:02d}.png',title=phase+' actual meshes / fixed camera and scale / includes retained failures',images=pictures[start:start+12],columns=3,width=600,height=600))
    write(root.resolve('projection_plan.json'),dict(frames=frames,sheets=sheets))
    write(root.resolve('study/comparison_table.json'),tables)
    print('Plan',len(frames),'frames',len(sheets),'sheets; table',len(tables),'cases',dict(Counter(r['status'] for r in tables)))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output-root',required=True,type=Path); parser.add_argument('--phases',nargs='+',required=True); parser.add_argument('--selected',nargs='*',default=[])
    parser.add_argument('--checkpoints',action='store_true')
    args=parser.parse_args(); prepare(args.output_root,args.phases,args.selected,args.checkpoints)
