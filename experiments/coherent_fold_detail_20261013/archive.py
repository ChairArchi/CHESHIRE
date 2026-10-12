"""Archive only completed, hash-linked lightweight coherent-rule evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MODES = ('COHERENT', 'DIRECTIONAL', 'ROLE_CURVATURE')
CASES = ('SPAN', 'COUNTER')


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
    verification = json.loads((root/'VERIFICATION.json').read_text(encoding='utf8'))
    rendering = json.loads((root/'RENDER_VERIFICATION.json').read_text(encoding='utf8'))
    if verification['status'] != 'PASS' or rendering['passed'] is not True:
        raise ValueError('Complete actual replay and render correspondence required.')
    entries = [(root/name, name) for name in ('RECIPE.json', 'source_index.json', 'SUMMARY.json',
        'VERIFICATION.json', 'RENDER_VERIFICATION.json', 'VISUAL_REVIEW.txt')]
    entries.append((root.parent/'tests_final_20261013.txt', 'tests_final_20261013.txt'))
    for mode in MODES:
        for case in CASES:
            name = f'{mode}/{case}/G05/generation.json'
            entries.append((root/name, name))
            name = f'{mode}/{case}/G05/views/receipt.json'
            entries.append((root/name, name))
    entries.extend((path, 'images/'+path.name) for path in sorted((root/'images').iterdir()) if path.is_file())
    if any(not source.is_file() for source, _ in entries):
        raise FileNotFoundError('Complete existing artifacts required.')
    dest.mkdir(parents=True)
    copied = []
    for source, relative in entries:
        target = dest/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        checksum = digest(source)
        if digest(target) != checksum:
            raise ValueError('Copied bytes differ: '+str(source))
        copied.append(dict(source=str(source), archive=relative, bytes=target.stat().st_size, sha256=checksum))
    paths = list(HERE.glob('*.py')) + list((REPO/'tests').glob('test_coherent_fold_*.py'))
    manifest = dict(base_commit='d4eb66497dee172697dfa4c653d5bd403afa6dd3',
        large_outputs=str(root), copied_evidence=copied,
        source_hashes={str(path.relative_to(REPO)): digest(path) for path in paths},
        scope='Exact lightweight evidence copies. All six actual control/native/evidence states and new 24 original renders remain on E; old 8 COMBINED originals are referenced, not regenerated.')
    (dest/'SOURCE_LIST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8')
    print('ARCHIVED', len(copied), 'lightweight evidence files', flush=True)


if __name__ == '__main__':
    main()
