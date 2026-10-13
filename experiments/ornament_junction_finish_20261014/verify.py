"""Verify saved local-finish preservation against actual original arrays."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

import numpy as np


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    proof_path = root/'PRESERVATION_VERIFICATION.json'
    if proof_path.exists():
        raise FileExistsError('Earlier verification preserved.')
    summary = json.loads((root/'SUMMARY.json').read_text(encoding='utf-8'))
    folder = Path(summary['folder'])
    info = json.loads((folder/'generation.json').read_text(encoding='utf-8'))
    source = Path(info['source'])
    if (digest(folder/'generation.json') != summary['generation_json_sha256'] or
            digest(folder/'control_quad.npz') != info['control_file_sha256'] or
            digest(folder/'evidence.npz') != info['evidence_file_sha256'] or
            digest(source/'control_quad.npz') != info['source_control_sha256'] or
            digest(source/'generation.json') != info['source_generation_json_sha256']):
        raise ValueError('Saved actual source/output hashes disagree.')
    unchanged = {}
    with np.load(source/'control_quad.npz', allow_pickle=False) as a, np.load(folder/'control_quad.npz', allow_pickle=False) as b:
        for key in ['faces', 'chart', 'classes', 'rest', 'anchors', 'generation', 'surface']:
            unchanged[key] = bool(np.array_equal(a[key], b[key]))
        original, actual = a['xyz'], b['xyz']
    with np.load(folder/'evidence.npz', allow_pickle=False) as data:
        mask = data['full_mask']
        anchors = data['coarse_radial_anchor_mask']
        delta = data['displacement_vector']
    outside_count = changed_count = outside_changed = 0
    max_displacement = max_radius_change = max_selected_radius_change = 0.
    reconstructed_exact = True
    for start in range(0, len(actual), 262144):
        stop = min(start+262144, len(actual))
        x, y = original[start:stop], actual[start:stop]
        selected = mask[start:stop] > 0
        changed = np.any(x != y, axis=1)
        changed_count += int(changed.sum())
        outside_count += int((~selected).sum())
        outside_changed += int((changed & ~selected).sum())
        max_displacement = max(max_displacement, float(np.linalg.norm(y-x, axis=1).max()))
        radius_change = np.abs(np.linalg.norm(y[:, :2], axis=1)-np.linalg.norm(x[:, :2], axis=1))
        max_radius_change = max(max_radius_change, float(radius_change.max()))
        max_selected_radius_change = max(max_selected_radius_change, float(radius_change[selected].max(initial=0.)))
        reconstructed_exact &= bool(np.array_equal(x+delta[start:stop], y))
    anchor_exact = bool(np.array_equal(original[:len(anchors)][anchors], actual[:len(anchors)][anchors]))
    bound = info['operator_metadata']['displacement_bound']
    passed = all(unchanged.values()) and outside_changed == 0 and anchor_exact and reconstructed_exact and max_displacement <= bound*(1+1e-12)
    proof = dict(date='2026-10-14', timezone='Asia/Seoul', passed=bool(passed),
        source=str(source), source_control_sha256=info['source_control_sha256'],
        output_generation_sha256=summary['generation_json_sha256'], output_control_sha256=info['control_file_sha256'],
        output_evidence_sha256=info['evidence_file_sha256'], unchanged_associations=unchanged,
        original_control_count=len(original), actual_changed_control_count=changed_count,
        outside_mask_control_count=outside_count, outside_mask_changed_count=outside_changed,
        fixed_original_coarse_anchor_count=int(anchors.sum()), fixed_original_coarse_anchors_exact=anchor_exact,
        actual_source_plus_saved_delta_exact=reconstructed_exact,
        maximum_actual_displacement=max_displacement, displacement_bound=bound,
        maximum_actual_radius_change=max_radius_change, maximum_selected_radius_change=max_selected_radius_change,
        code_sha256=digest(__file__),
        scope='Saved actual array comparison, all source controls and unchanged associations. Radial anchor preservation is not a guarantee that every newer tip or silhouette pixel is fixed. No geometry generation, full replay, collision repair or aesthetic certification.')
    proof_path.write_text(json.dumps(proof, indent=2)+'\n', encoding='utf-8')
    snapshot = root/'source_snapshot_validation'/Path(__file__).name
    snapshot.parent.mkdir(exist_ok=True)
    shutil.copyfile(__file__, snapshot)
    if not passed:
        raise ValueError('Saved local preservation verification failed.')
    print('LOCAL_PRESERVATION_PASS', changed_count, 'changed;', outside_count, 'outside fixed;', max_displacement, 'max motion', flush=True)


if __name__ == '__main__':
    main()
