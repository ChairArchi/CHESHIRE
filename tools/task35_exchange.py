"""Task35 OBJ exchange; same strict native checks as the Task33 writer.

Keeps Task33's frozen writer untouched and labels Task35 exchange correctly.
OBJ cannot substitute for formation, controls, operator or lineage state.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task29_search import load_mesh
from task33_preserve import sha,write_new
ROOT=Path('E:/CHESHIRE_DATA/task35')


def deliver(candidate,tag):
    if not all(v.replace('_','').isalnum() for v in (candidate,tag)):raise ValueError('Safe fresh tags required.')
    validation=ROOT/'validation'/(candidate+'_EXPORT_FULL')/'TRIANGLES.json';audit=json.loads(validation.read_text())
    stage=Path(audit['stage']);checks=audit['contacts'];geometry=audit['embedding']
    if not checks['all_triangles_sampled'] or checks['transverse_contacts'] or checks['cap_reached']:raise ValueError('Full triangular transverse diagnostic must pass.')
    if geometry['degenerate_triangles'] or geometry['invalid_vertex_links'] or geometry['orphan_vertices']:raise ValueError('Invalid native geometry.')
    if not geometry['finite'] or geometry['connected_components']!=1 or geometry['Euler']!=2:raise ValueError('One finite closed column required.')
    if audit['end_buffer_xyz_error']!=0 or any(v['geometry_max']>1e-8 or v['oriented_triangle_cycle_failures'] for v in audit['symmetry'].values()):raise ValueError('Column boundary/symmetry checks must pass.')
    if any(v['non_cycle_nodes'] or v['crossings_touches_overlaps'] for v in audit['cuts']):raise ValueError('Audited triangle cuts must remain simple cycles.')
    if sha(stage/'mesh.npz')!=audit['mesh_sha256']:raise ValueError('Audited mesh changed.')
    mesh=load_mesh(stage)
    if not np.all(mesh.faces[:,3]==-1):raise ValueError('Explicit native triangles required.')
    dest=ROOT/'deliverables'/tag;dest.mkdir(parents=True,exist_ok=False);obj=dest/'column.obj'
    with obj.open('x',encoding='ascii',newline='\n') as stream:
        stream.write('# CHESHIRE Task35 '+candidate+'; unresolved original project units; native state authoritative.\n')
        for begin in range(0,len(mesh.xyz),100000):np.savetxt(stream,mesh.xyz[begin:begin+100000],fmt='v %.17g %.17g %.17g')
        for begin in range(0,len(mesh.faces),100000):np.savetxt(stream,mesh.faces[begin:begin+100000,:3]+1,fmt='f %d %d %d')
    nv=nf=0;block=[];kind=None
    def verify():
        nonlocal nv,nf,block
        if not block:return
        values=np.fromstring(' '.join(block),sep=' ',dtype=float if kind=='v' else np.int64).reshape(-1,3)
        if kind=='v':
            if not np.array_equal(values,mesh.xyz[nv:nv+len(values)]):raise ValueError('OBJ coordinate round-trip differs.')
            nv+=len(values)
        else:
            if not np.array_equal(values-1,mesh.faces[nf:nf+len(values),:3]):raise ValueError('OBJ oriented face round-trip differs.')
            nf+=len(values)
        block=[]
    with obj.open(encoding='ascii') as stream:
        for line in stream:
            if line.startswith('#'):continue
            this=line[0]
            if this not in ('v','f'):raise ValueError('Unexpected OBJ record.')
            if kind!=this:verify();kind=this
            block.append(line[2:])
            if len(block)==100000:verify()
        verify()
    if nv!=len(mesh.xyz) or nf!=len(mesh.faces):raise ValueError('OBJ counts differ.')
    state=dict(np.load(stage/'formation_state.npz'))
    np.savez_compressed(dest/'connection_sections.npz',bottom=state['grid'][0],top=state['grid'][-1],theta=state['theta'])
    write_new(dest/'connection_frame.json',dict(axes='X width / Y depth / Z vertical; right-handed',height=4000,
        unit='Unresolved original project unit; no mm claim',half_width=450,half_depth=250,
        bottom_origin=[0,0,0],top_origin=[0,0,4000],outward_normals={'bottom':[0,0,-1],'top':[0,0,1]},
        loop_order='Increasing material theta, CCW viewed from +Z; clockwise from bottom outward normal.',
        fixed_original_material_buffers=[['bottom',0,240],['top',3760,4000]],
        coarse_section='Closed octagon, angularly subdivided without geometry smoothing; physical end coordinates common to all cases.',
        prerequisites='Structured monotone mean-height column chart, actual incoming XY sections, original rest/material chart, fixed reference radius sqrt(450*250), declared finite schedule; not an arbitrary unstructured gate deformation solver.',
        limits='Caps remain closed. Connection topology and lintel construction are not implemented in Task35.'))
    write_new(dest/'exchange.json',dict(candidate=candidate,source_native_stage=str(stage),source_native_sha256=sha(stage/'mesh.npz'),
        validation=str(validation),validation_sha256=sha(validation),obj_sha256=sha(obj),obj_bytes=obj.stat().st_size,
        exact_roundtrip_vertices=nv,exact_roundtrip_oriented_triangles=nf,producer_sha256=sha(Path(__file__)),
        limits='No Rhino GUI import claim, units unresolved. Full transverse diagnostic excludes coplanar/tangent/shared-vertex contacts and does not certify a solid. Native state is needed for continuation.'))
    print(candidate,nv,nf,'OBJ round-trip exact',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True)
    args=p.parse_args();deliver(args.candidate,args.tag)
