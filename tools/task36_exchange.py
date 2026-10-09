"""Exact native OBJ exchange, requiring a matching strict full audit first."""
import argparse,json,sys
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task29_search import load_mesh
from task33_preserve import sha,write_new
ROOT=Path('E:/CHESHIRE_DATA/task36')


def deliver(candidate,audit_file):
    job=ROOT/'candidates'/candidate;stage=Path(json.loads((job/'completed.json').read_text())['final_stage'])
    certificate=json.loads(audit_file.read_text());m=load_mesh(stage);e=certificate['embedding']
    if 'interval overlap' not in certificate['contacts'].get('narrow_phase',''):raise ValueError('Supplementary noncoplanar interval audit required.')
    if not certificate['contacts'].get('shared_vertex_pairs_included'):raise ValueError('Final shared-pair interior interval audit required.')
    if any(c['crossings_touches_overlaps'] for c in certificate['cuts']):raise ValueError('Unresolved actual section crossing/touch/overlap; no validated exchange.')
    if certificate['mesh_sha256']!=sha(stage/'mesh.npz') or Path(certificate['stage']).resolve()!=stage.resolve():raise ValueError('Certificate/source identity mismatch.')
    if certificate['contacts']['transverse_contacts'] or not certificate['contacts']['all_triangles_sampled'] or e['degenerate_triangles'] or e['invalid_vertex_links'] or e['orphan_vertices'] or e['connected_components']!=1 or e['Euler']!=2 or certificate['end_plane_z_error']>1e-10:raise ValueError('Native geometry failed exchange requirements.')
    if any(v['geometry_max']>1e-8 or not v['bijective'] or v['oriented_face_cycle_failures'] for v in certificate['symmetry'].values()):raise ValueError('Symmetry requirement failed.')
    dest=ROOT/'deliverables'/candidate;dest.mkdir(parents=True,exist_ok=False);path=dest/'column.obj'
    with path.open('w',encoding='ascii',newline='\n') as out:
        out.write('# CHESHIRE Task36 exact native triangles; X/Y cross-section, Z vertical; project units unresolved\n')
        for p in m.xyz:out.write('v '+' '.join(format(float(v),'.17g') for v in p)+'\n')
        for f in m.faces[:,:3]:out.write('f '+' '.join(str(int(v)+1) for v in f)+'\n')
    vi=fi=0
    with path.open(encoding='ascii') as inp:
        for line in inp:
            if line.startswith('v '):
                if not np.array_equal(np.array([float(v) for v in line[2:].split()]),m.xyz[vi]):raise ValueError('OBJ vertex roundtrip failed.')
                vi+=1
            elif line.startswith('f '):
                if [int(v)-1 for v in line[2:].split()]!=m.faces[fi,:3].tolist():raise ValueError('OBJ oriented triangle roundtrip failed.')
                fi+=1
    assert vi==len(m.xyz) and fi==len(m.faces)
    write_new(dest/'exchange.json',dict(candidate=candidate,stage=str(stage),native_sha256=sha(stage/'mesh.npz'),obj_sha256=sha(path),vertices=vi,triangles=fi,all_coordinates_bit_exact=True,all_oriented_triangles_exact=True,audit_sha256=sha(audit_file),
        coordinates='X/Y width/depth; Z=0..4000 vertical. Unresolved project units; no rescaling. Closed caps, no fabrication/strength claim.',
        exclusions=certificate['contacts']['exclusions']))
    write_new(dest/'recipe.json',json.loads((job/'request.json').read_text()));print(candidate,vi,fi,sha(path),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--audit',type=Path,required=True);a=p.parse_args();deliver(a.candidate,a.audit)
