"""Verified OBJ exchange from an explicit Task33 triangle checkpoint.

OBJ is a design exchange, never a substitute for native state. Streamed
round-trip validation checks every double coordinate and oriented face.
"""
import json,sys
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task29_search import load_mesh
from task33_preserve import ROOT,sha,write_new


def deliver(candidate,tag):
    validation=ROOT/'validation'/(candidate+'_EXPORT_FULL')/'TRIANGLES.json'
    audit=json.loads(validation.read_text());stage=Path(audit['stage'])
    checks=audit['contacts'];geometry=audit['embedding']
    if not checks['all_triangles_sampled'] or checks['transverse_contacts'] or checks['cap_reached']:
        raise ValueError('Explicit triangular surface must first pass its full transverse diagnostic.')
    if geometry['degenerate_triangles'] or geometry['invalid_vertex_links'] or geometry['orphan_vertices']:
        raise ValueError('Invalid native triangle geometry or links.')
    if sha(stage/'mesh.npz')!=audit['mesh_sha256']:raise ValueError('Audited native mesh changed.')
    mesh=load_mesh(stage)
    if not np.all(mesh.faces[:,3]==-1):raise ValueError('Explicit native triangles required.')
    dest=ROOT/'deliverables'/tag;dest.mkdir(parents=True,exist_ok=False);obj=dest/'gate.obj'
    with obj.open('x',encoding='ascii',newline='\n') as stream:
        stream.write('# CHESHIRE Task33; original unresolved project units. Native state is authoritative.\n')
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
            if this!=kind:verify();kind=this
            block.append(line[2:])
            if len(block)==100000:verify()
        verify()
    if nv!=len(mesh.xyz) or nf!=len(mesh.faces):raise ValueError('OBJ counts differ.')
    write_new(dest/'exchange.json',dict(candidate=candidate,source_native_stage=str(stage),source_native_sha256=sha(stage/'mesh.npz'),
        validation=str(validation),validation_sha256=sha(validation),obj_sha256=sha(obj),obj_bytes=obj.stat().st_size,
        exact_roundtrip_vertices=nv,exact_roundtrip_oriented_triangles=nf,producer_sha256=sha(Path(__file__)),
        limits='No Rhino GUI import claim. Original project units unresolved. Full transverse diagnostic excludes coplanar, tangent and shared-vertex contacts; no solid certification. Recover native operator/material/fold/lineage state from checkpoints and Git/source snapshots, not OBJ.'))
    print(tag,'OBJ round-trip exact',nv,nf,flush=True)
