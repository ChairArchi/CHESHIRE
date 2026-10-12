"""Preserve lightweight evidence; keep all actual control/native arrays on E."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--dest', type=Path, required=True)
    args = parser.parse_args()
    root, dest = args.root.resolve(), args.dest.resolve()
    if dest.exists():
        raise FileExistsError('Earlier archive preserved.')
    entries = [(root/name, name) for name in (
        'RECIPE.json', 'source_index.json', 'SUMMARY.json', 'VERIFICATION.json',
        'VERIFICATION_RECHECK_01.json', 'RENDER_VERIFICATION.json', 'VISUAL_REVIEW.txt')]
    entries += [(root.parent/name, name) for name in (
        'PREFLIGHT.json', 'tests_recheck_20261013.txt', 'verification_trial01.log',
        'verification_recheck_01.log')]
    for mode in ('SMOOTH_CONTROL', 'ROOT_ONLY', 'BRANCHED'):
        for case in ('SPAN', 'COUNTER'):
            for stage in ('G03_events', 'G04', 'G05'):
                relative = f'{mode}/{case}/{stage}/generation.json'
                entries.append((root/relative, relative))
            relative = f'{mode}/{case}/G03_events/events.json'
            entries.append((root/relative, relative))
            relative = f'{mode}/{case}/G05/views/receipt.json'
            entries.append((root/relative, relative))
    entries += [(path, 'images/'+path.name) for path in sorted((root/'images').iterdir()) if path.is_file()]
    if any(not source.is_file() for source, _ in entries):
        raise FileNotFoundError('Complete actual/visual/test records are required.')
    passed = json.loads((root/'VERIFICATION_RECHECK_01.json').read_text(encoding='utf8'))
    render = json.loads((root/'RENDER_VERIFICATION.json').read_text(encoding='utf8'))
    failed = json.loads((root/'VERIFICATION.json').read_text(encoding='utf8'))
    if passed['status'] != 'PASS' or render['passed'] is not True or failed['status'] != 'FAIL':
        raise ValueError('Keep the original metadata-contract failure and the successful recheck.')
    if passed['verifier_module_sha256'] != digest(HERE/'verify.py'):
        raise ValueError('Successful verifier code has changed.')
    dest.mkdir(parents=True)
    copied = []
    for source, relative in entries:
        target = dest/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        checksum = digest(source)
        if digest(target) != checksum:
            raise ValueError('Archive bytes differ: '+str(source))
        copied.append(dict(source=str(source), archive=relative,
            bytes=target.stat().st_size, sha256=checksum))
    code = list(HERE.glob('*.py')) + list((REPO/'tests').glob('test_connected_fold_*.py'))
    manifest = dict(base_commit='0ff7387fcfe2fb00cbc0b5d45858576bff664d44',
        large_outputs=str(root), started='2026-10-12', reviewed='2026-10-13',
        source_hashes={str(path.relative_to(REPO)): digest(path) for path in code},
        copied_evidence=copied,
        scope='Exact copies of existing evidence; actual control/native/evidence arrays and 24 original renders remain on E. No generation or rendering during archive.',
        visual_decision='ROOT_ONLY PARTIAL; BRANCHED hierarchy FAIL; neither replaces the accepted column or gate.')
    (dest/'SOURCE_LIST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8')
    print('ARCHIVED', len(copied), 'lightweight evidence files', flush=True)


if __name__ == '__main__':
    main()
