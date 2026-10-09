"""Immutable Task33 baseline evidence; reads Task01--32 without changing them."""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path('E:/CHESHIRE_DATA/task33')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)


def verify(manifest):
    d = json.loads(Path(manifest).read_text(encoding='utf-8'))
    root = Path(d['root'])
    for item in d['files']:
        p = root / item['path']
        if p.stat().st_size != item['bytes'] or sha(p) != item['sha256']:
            raise ValueError('Historical artifact changed: ' + str(p))
    return {'manifest': str(manifest), 'manifest_sha256': sha(manifest),
            'verified_files': len(d['files']), 'root': str(root)}


def preserve(tag):
    records = [verify('E:/CHESHIRE_DATA/task32/preservation/task31_before.json'),
               verify('E:/CHESHIRE_DATA/task32/FINAL_ARTIFACTS.json')]
    bundle = Path('E:/CHESHIRE_DATA/task32/preservation/repository_final.bundle')
    result = subprocess.run(['git', '-c', 'safe.directory=' + REPO.as_posix(),
                             'bundle', 'verify', str(bundle)], cwd=REPO,
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    tracked = subprocess.check_output(['git', '-c', 'safe.directory=' + REPO.as_posix(),
                                      'ls-files', '-z'], cwd=REPO).split(b'\0')
    sources = {p.decode(): sha(REPO / p.decode()) for p in tracked if p and (REPO / p.decode()).is_file()}
    record = dict(UTC=datetime.now(timezone.utc).isoformat(), prior=records,
                  head=subprocess.check_output(['git', '-c', 'safe.directory=' + REPO.as_posix(), 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
                  tracked_files=sources, bundle=str(bundle), bundle_sha256=sha(bundle),
                  bundle_verification=dict(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr),
                  recovery='Existing independent Task32 clone/native-state replay evidence retained; old datasets referenced by verified SHA256, not duplicated.')
    write_new(ROOT / 'preservation' / (tag + '.json'), record)
    print(json.dumps(dict(tag=tag, verified=[r['verified_files'] for r in records], bundle_exit=result.returncode, tracked=len(sources))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if not args.tag.replace('_', '').isalnum():
        raise ValueError('Safe tag required')
    preserve(args.tag)
