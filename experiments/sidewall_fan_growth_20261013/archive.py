"""Copy existing lightweight sidewall evidence without touching large arrays."""
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
        'RENDER_VERIFICATION.json', 'VISUAL_REVIEW.txt')]
    entries += [(root.parent/'tests_final_20261013.txt', 'tests_final_20261013.txt')]
    for case in ('SPAN', 'COUNTER'):
        for stage in ('G03_events', 'G04', 'G05'):
            relative = f'SIDEWALL_FAN/{case}/{stage}/generation.json'
            entries.append((root/relative, relative))
        relative = f'SIDEWALL_FAN/{case}/G03_events/events.json'
        entries.append((root/relative, relative))
        relative = f'SIDEWALL_FAN/{case}/G05/views/receipt.json'
        entries.append((root/relative, relative))
    entries += [(path, 'images/'+path.name) for path in sorted((root/'images').iterdir()) if path.is_file()]
    if any(not source.is_file() for source, _ in entries):
        raise FileNotFoundError('Complete generation/verification/visual records required.')
    actual = json.loads((root/'VERIFICATION.json').read_text(encoding='utf8'))
    rendering = json.loads((root/'RENDER_VERIFICATION.json').read_text(encoding='utf8'))
    if actual.get('status') != 'PASS' or rendering.get('passed') is not True:
        raise ValueError('Actual geometry and renderer verification must both PASS.')
    dest.mkdir(parents=True)
    copied = []
    for source, relative in entries:
        target = dest/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        checksum = digest(source)
        if digest(target) != checksum:
            raise ValueError('Copied bytes differ: '+str(source))
        copied.append(dict(source=str(source), archive=relative, bytes=target.stat().st_size,
            sha256=checksum))
    paths = list(HERE.glob('*.py')) + list((REPO/'tests').glob('test_sidewall_fan_*.py'))
    value = dict(base_commit='d016293aa0e77346c5f697126800d3af856e5ea3',
        large_outputs=str(root), copied_evidence=copied,
        source_hashes={str(path.relative_to(REPO)): digest(path) for path in paths},
        scope='Exact lightweight copies only. Actual controls/native/evidence and new 8 original renders remain on E; reference 16 original renders remain in the preserved connected pilot.')
    (dest/'SOURCE_LIST.json').write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')
    print('ARCHIVED', len(copied), 'lightweight evidence files', flush=True)


if __name__ == '__main__':
    main()
