"""Copy lightweight proven evidence; leave all large pilot arrays on E."""
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
    parser.add_argument('--parent-root', type=Path, required=True)
    parser.add_argument('--dest', type=Path, required=True)
    parser.add_argument('--fan-root', type=Path)
    args = parser.parse_args()
    if args.dest.exists():
        raise FileExistsError('Earlier archive preserved.')
    entries = [(args.root/name, name) for name in
        ('RECIPE.json', 'SUMMARY.json', 'VERIFICATION.json', 'RENDER_VERIFICATION.json', 'VISUAL_REVIEW.txt')]
    entries += [(args.parent_root/'VERIFICATION.json', 'PARENT_VERIFICATION.json'),
        (args.root.parent/'tests_broad_20261012.txt', 'tests_broad_20261012.txt')]
    for case in ('SPAN', 'COUNTER'):
        entries += [(args.root/case/name, f'{case}/{name}') for name in
            ('actual_patch.npz', 'G04_incoming_frame.npz', 'G05_incoming_frame.npz', 'SUMMARY.json')]
        entries.append((args.parent_root/'BASELINE'/case/'G06/generation.json', f'{case}/BASELINE.json'))
        for mode in ('CLEAR_ONLY', 'BROAD_ACTIVE'):
            entries.append((args.root/mode/case/'G06/generation.json', f'{case}/{mode}.json'))
        for mode in ('BASELINE', 'CLEAR_ONLY', 'BROAD_ACTIVE'):
            entries.append((args.root/mode/case/'G06/views/receipt.json', f'{case}/{mode}_render_receipt.json'))
    entries.extend((path, 'images/'+path.name) for path in sorted((args.root/'images').glob('*')))
    if args.fan_root:
        entries.extend((args.fan_root/name, 'rooted_fans/'+name) for name in
            ('RECIPE.json', 'SUMMARY.json', 'VERIFICATION.json', 'RENDER_VERIFICATION.json', 'VISUAL_REVIEW.txt'))
        entries.append((args.root.parent/'tests_broad_fans_20261012.txt', 'tests_broad_fans_20261012.txt'))
        for case in ('SPAN', 'COUNTER'):
            for name in ('G06_incoming_frame.npz', 'G06_incoming_curves.npz'):
                entries.append((args.fan_root/case/name, f'rooted_fans/{case}/{name}'))
            entries.append((args.fan_root/'ROOTED_FANS'/case/'G06/generation.json', f'rooted_fans/{case}/ROOTED_FANS.json'))
            entries.append((args.fan_root/'ROOTED_FANS'/case/'G06/views/receipt.json', f'rooted_fans/{case}/ROOTED_FANS_render_receipt.json'))
        entries.extend((path, 'rooted_fans/images/'+path.name) for path in sorted((args.fan_root/'images').glob('*')))
    if any(not source.is_file() for source, _ in entries):
        raise FileNotFoundError('Complete evidence and test/visual records are required.')
    for name in ('VERIFICATION.json', 'RENDER_VERIFICATION.json'):
        receipt = json.loads((args.root/name).read_text(encoding='utf8'))
        if not (receipt.get('passed') is True or receipt.get('status') == 'PASS'):
            raise ValueError('Verification is incomplete: '+name)
        if args.fan_root:
            fine_receipt = json.loads((args.fan_root/name).read_text(encoding='utf8'))
            if not (fine_receipt.get('passed') is True or fine_receipt.get('status') == 'PASS'):
                raise ValueError('Fine-fold verification is incomplete: '+name)
    args.dest.mkdir(parents=True)
    copied = []
    for source, relative in entries:
        target = args.dest/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        checksum = digest(source)
        if checksum != digest(target):
            raise ValueError('Archive checksum mismatch: '+str(source))
        copied.append(dict(source=str(source.resolve()), archive=relative,
            bytes=target.stat().st_size, sha256=checksum))
    code = (list(HERE.glob('*.py'))
        + list((REPO/'tests').glob('test_broad_shoulder_*.py'))
        + list((REPO/'tests').glob('test_broad_rooted_*.py')))
    manifest = dict(large_outputs=str(args.root.resolve()), parent_outputs=str(args.parent_root.resolve()),
        fine_outputs=str(args.fan_root.resolve()) if args.fan_root else None,
        base_commit='191fec7df4595405820f47e1f7c43b94865dd742',
        source_hashes={str(path.relative_to(REPO)): digest(path) for path in code}, copied_evidence=copied,
        large_array_scope='Actual control/native and stage displacement arrays remain at the E output root; no rerender or regeneration in this archive operation')
    (args.dest/'SOURCE_LIST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8')
    print('ARCHIVED', len(copied), 'lightweight evidence files', flush=True)


if __name__ == '__main__':
    main()
