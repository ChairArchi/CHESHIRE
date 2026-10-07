"""Compact factual tables; visual judgments are recorded separately by reviewer."""
import argparse
import csv
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'examples'))
from cross_cell_crease_study import read, write


def table(root, phase):
    result = []
    for case in sorted((root/'study'/phase).glob('*')):
        if not case.is_dir(): continue
        attempts = sorted(case.glob('attempt_*'))
        if not attempts or not (attempts[-1]/'summary.json').exists(): continue
        p = attempts[-1]; s = read(p/'summary.json'); stages = s['stages']
        r = stages[-1] if stages else {}; nets = r.get('networks', [])
        result.append(dict(id=case.name, phase=phase, attempt=p.relative_to(root).as_posix(),
            status=s['status'], reason=s.get('reason'), family=s.get('recipe', {}).get('family'),
            faces=r.get('statistics', {}).get('face_count'), stage=r.get('stage'), contact=r.get('geometry_state'),
            crossings=r.get('crossings', {}).get('sampled_transverse_crossings'), cap=r.get('crossings', {}).get('sample_limit_reached'),
            any_contact=any(x['crossings']['sampled_transverse_crossings'] for x in stages),
            cap_ever=any(x['crossings']['sample_limit_reached'] for x in stages),
            design_eligible=s.get('design_eligible', False), networks=nets,
            degenerate=len(r.get('diagnostics', {}).get('degenerate_fan_faces', [])),
            opposed=len(r.get('diagnostics', {}).get('opposed_fan_normals', [])),
            bilinear=len(r.get('diagnostics', {}).get('bilinear_admissibility_warning_faces', [])),
            output_sha256=s.get('output_sha256'), seconds=s.get('process', {}).get('seconds'),
            peak_bytes=s.get('process', {}).get('peak_process_tree_plus_driver_bytes'),
            ornament=s.get('ornament'), monitor=r.get('monitor')))
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output-root', type=Path, required=True); p.add_argument('--phase', required=True)
    a=p.parse_args(); rows=table(a.output_root,a.phase)
    write(a.output_root/'study'/('table_'+a.phase+'.json'), rows)
    for r in rows:
        n=r['networks']; print(r['id'],r['status'],r['faces'],r['contact'],r['crossings'],
            'eligible='+str(r['design_eligible']), 'cells='+str([x['parent_cell_count'] for x in n]),
            'c0='+str([x['C0_face_count'] for x in n]), 'contrast='+str([round(x['visible_crease_survival_ratio'],3) for x in n]),
            'junction='+str([x['junctions'] for x in n]))
