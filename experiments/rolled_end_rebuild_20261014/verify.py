"""Read-only preservation and radial-envelope checks of saved rebuilt ends."""
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
        raise ValueError('Actual source/output hashes disagree.')
    unchanged = {}
    with np.load(source/'control_quad.npz', allow_pickle=False) as a, np.load(folder/'control_quad.npz', allow_pickle=False) as b:
        for key in ['faces', 'chart', 'classes', 'rest', 'anchors', 'generation', 'surface']:
            unchanged[key] = bool(np.array_equal(a[key], b[key]))
        original, actual, chart = a['xyz'], b['xyz'], a['chart']
    with np.load(folder/'evidence.npz', allow_pickle=False) as data:
        mask, delta = data['full_mask'], data['displacement_vector']
    outside_count = changed_count = outside_changed = 0
    max_displacement = max_radius_change = 0.
    reconstructed_exact = True
    old_peaks, new_peaks, counts = {}, {}, {}
    for start in range(0, len(actual), 262144):
        stop = min(start+262144, len(actual))
        x, y = original[start:stop], actual[start:stop]
        selected = mask[start:stop] > 0
        changed = np.any(x != y, axis=1)
        changed_count += int(changed.sum())
        outside_count += int((~selected).sum())
        outside_changed += int((changed & ~selected).sum())
        max_displacement = max(max_displacement, float(np.linalg.norm(y-x, axis=1).max()))
        r0, r1 = np.linalg.norm(x[:, :2], axis=1), np.linalg.norm(y[:, :2], axis=1)
        max_radius_change = max(max_radius_change, float(np.abs(r1-r0).max()))
        reconstructed_exact &= bool(np.array_equal(x+delta[start:stop], y))
        c = chart[start:stop][selected]
        theta = np.arctan2(np.abs(c[:, 2]), np.abs(c[:, 1]))
        keys = np.floor(c[:, 0]/.02).astype(int)*64+np.floor(theta/.08).astype(int)
        for k in np.unique(keys):
            hit = keys == k
            key = int(k)
            old_peaks[key] = max(old_peaks.get(key, -np.inf), float(r0[selected][hit].max()))
            new_peaks[key] = max(new_peaks.get(key, -np.inf), float(r1[selected][hit].max()))
            counts[key] = counts.get(key, 0)+int(hit.sum())
    bins = [dict(material_t_bin=k//64, material_theta_bin=k%64, controls=counts[k],
        original_radius_maximum=old_peaks[k], rebuilt_radius_maximum=new_peaks[k],
        peak_change=new_peaks[k]-old_peaks[k]) for k in sorted(counts)]
    changes = np.array([a['peak_change'] for a in bins])
    declared = info['operator_metadata'].get('displacement_bound', .025*info['operator_metadata']['physical_height'])
    passed = all(unchanged.values()) and outside_changed == 0 and reconstructed_exact and max_displacement <= declared*(1+1e-12) and changed_count > 0
    proof = dict(date='2026-10-14', timezone='Asia/Seoul', passed=bool(passed),
        source=str(source), source_control_sha256=info['source_control_sha256'],
        output_generation_sha256=summary['generation_json_sha256'], output_control_sha256=info['control_file_sha256'],
        output_evidence_sha256=info['evidence_file_sha256'], unchanged_associations=unchanged,
        original_control_count=len(original), actual_changed_control_count=changed_count,
        outside_mask_control_count=outside_count, outside_mask_changed_count=outside_changed,
        actual_source_plus_saved_delta_exact=reconstructed_exact,
        maximum_actual_displacement=max_displacement, displacement_bound=declared,
        maximum_actual_radius_change=max_radius_change,
        radial_envelope_bins=bins, radial_envelope_bin_widths=dict(material_t=.02, material_theta_radians=.08),
        maximum_absolute_binned_peak_change=float(np.abs(changes).max(initial=0.)),
        rms_binned_peak_change=float(np.sqrt(np.mean(changes*changes))) if len(changes) else 0.,
        code_sha256=digest(__file__),
        scope='Actual saved arrays, all source controls and unchanged associations. Binned radial peaks measure protrusion-envelope changes; they do not certify visual quality, exact volume or continuity. Individual end shapes may change by user decision. No full independent replay or self-intersection certification.')
    proof_path.write_text(json.dumps(proof, indent=2)+'\n', encoding='utf-8')
    snapshot = root/'source_snapshot_validation'/Path(__file__).name
    snapshot.parent.mkdir(exist_ok=True)
    shutil.copyfile(__file__, snapshot)
    if not passed:
        raise ValueError('Saved preservation verification failed.')
    print('REBUILT_END_PRESERVATION_PASS', changed_count, 'changed;', outside_count, 'outside fixed;', max_displacement, 'max motion', flush=True)


if __name__ == '__main__':
    main()
