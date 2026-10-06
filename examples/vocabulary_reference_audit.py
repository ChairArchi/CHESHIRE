"""Recover actual pre-event geometry to audit early constructor-order changes.

This removes only recorded new children and restores their recorded parent
cycles. It never changes study outputs or derives missing semantic lineage.
"""
from collections import Counter
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from subdivision_capability_study import read,write
from ornament_study import digest
from vocabulary_review import STUDY,gz_read,cases

def oriented_polygons(data):
    xyz={v['id']:tuple(v['xyz']) for v in data['vertices']}
    def cycle(face):
        p=tuple(xyz[k] for k in face['vertices'])
        return min(p[i:]+p[:i] for i in range(len(p)))
    return Counter(cycle(f) for f in data['faces'])

def audit():
    original=read(STUDY/'references/HERO.json'); rows=[]
    for name in ('A_D06','A_D07','A_D08','A_R06','A_R07','A_R09'):
        case=STUDY/'A'/name/'attempt_001'; summary=read(case/'summary.json')
        data=read(case/'terminal.json'); events=gz_read(case/'terminal_lineage.json.gz')['events']
        added=[e for e in events if e['stage_index']==11]
        child_ids={c['id'] for e in added for c in e['children']}
        faces=[f for f in data['faces'] if f['id'] not in child_ids]
        faces.extend(dict(id=e['parent_face'],vertices=e['local_frame']['ordered_corner_ids']) for e in added)
        count=summary['stages'][9]['statistics']['vertex_count']
        recovered=dict(vertices=data['vertices'][:count],faces=sorted(faces,key=lambda f:f['id']))
        recorded=summary['stages'][9]['geometry_sha256']
        assert digest(recovered)==recorded, 'Recovery must match the recorded pre-event geometry.'
        geometry_equal=oriented_polygons(recovered)==oriented_polygons(original)
        vertex_equal=Counter(tuple(v['xyz']) for v in recovered['vertices'])==Counter(tuple(v['xyz']) for v in original['vertices'])
        assert geometry_equal and vertex_equal
        rows.append(dict(id=name,recovered_ordered_sha256=digest(recovered),original_ordered_sha256=digest(original),
            ordered_identity=digest(recovered)==digest(original),exact_oriented_geometry_up_to_key_renumbering=geometry_equal,
            exact_vertex_coordinate_multiset=vertex_equal,source_hashes=read(case/'versions.json') if (case/'versions.json').exists() else None))
    controls=[]
    for case in sorted((STUDY/'F/TASK20_HERO_CONTROL').glob('attempt_*')):
        if not (case/'terminal.json').exists(): continue
        s=read(case/'summary.json'); same=read(case/'terminal.json')==original
        assert same
        original_case=ROOT/'output/task20/study/B/HERO_ROLE_ASSEMBLY/attempt_001'
        semantic={}
        for name in ('terminal_lineage.json.gz','terminal_signatures.json.gz'):
            current=gz_read(case/name)
            if (original_case/name).exists():
                previous=gz_read(original_case/name)
                assert current==previous
                semantic[name]=dict(exact_decoded_payload=True,original_payload_sha256=digest(previous),current_payload_sha256=digest(current))
        controls.append(dict(id=case.parent.name,status=s['status'],exact_ordered_geometry=same,sha256=s['output_sha256'],original_semantic_payload_comparison=semantic))
    promotions=[]
    for case in cases('F'):
        if not case.parent.name.startswith('F_'): continue
        name=case.parent.name[2:]; phase='A' if name.startswith('A_') else 'B' if name.startswith('B') else 'C'
        previous=next(p for p in cases(phase) if p.parent.name==name)
        a=read(previous/'terminal.json'); b=read(case/'terminal.json')
        assert oriented_polygons(a)==oriented_polygons(b)
        assert Counter(tuple(v['xyz']) for v in a['vertices'])==Counter(tuple(v['xyz']) for v in b['vertices'])
        promotions.append(dict(id=case.parent.name,source=name,exact_oriented_geometry_up_to_keys=True,ordered_identity=a==b,
            original_contacts=read(previous/'terminal_crossings.json')['sampled_transverse_crossings'],promoted_contacts=read(case/'terminal_crossings.json')['sampled_transverse_crossings'],
            sampling_scope='Changed constructor/key order can change the evenly spaced face sample; no geometric improvement is inferred from different contact counts.'))
    result=dict(early_order_correction='Early cohorts coordinated direction but also reordered face construction. Face cycles/XYZ were identical up to keys; corrected routing now preserves the existing selector order. No early result was replaced.',
        early_actual_results=rows,corrected_real_whole_gate_controls=controls,actual_promoted_geometry_identity=promotions)
    write(STUDY/'reference_identity_audit.json',result); print('reference identity',len(rows),'early actual geometries',len(controls),'corrected controls')

if __name__=='__main__': audit()
