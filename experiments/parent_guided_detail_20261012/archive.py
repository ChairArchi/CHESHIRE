"""Archive lightweight evidence; keep large scientific geometry on E."""
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
    parser.add_argument('--meso-root', type=Path, required=True)
    parser.add_argument('--active-root', type=Path, required=True)
    parser.add_argument('--dest', type=Path, required=True)
    args = parser.parse_args()
    sources = [
        (args.root/'RECIPE.json', 'parent_recipe.json'),
        (args.root/'VERIFICATION.json', 'VERIFICATION.json'),
        (args.root/'RENDER_VERIFICATION.json', 'RENDER_VERIFICATION.json'),
        (args.root/'metrics/summary.json', 'parent_metrics.json'),
        (args.meso_root/'ABLATION_RECIPE.json', 'meso_recipe.json'),
        (args.meso_root/'ABLATION_VERIFICATION.json', 'ABLATION_VERIFICATION.json'),
        (args.active_root/'RECIPE.json', 'active_recipe.json'),
        (args.active_root/'SUMMARY.json', 'ACTIVE_FOLDS_SUMMARY.json'),
        (args.active_root/'ACTIVE_VERIFICATION.json', 'ACTIVE_VERIFICATION.json'),
        (args.root.parent/'tests_new_20261012.txt', 'tests_new_20261012.txt'),
        (REPO/'output/parent_guided_detail_20261012_tests.txt', 'tests_initial_66.txt'),
        (Path('E:/CHESHIRE_DATA/storage_migration_20261012_parent_guided/SUMMARY.json'), 'STORAGE_MIGRATION.json'),
        (args.root/'images/SOURCE_LIST.json', 'images/SOURCE_LIST.json'),
        (args.root/'images/ALTERNATIVES_SOURCE_LIST.json', 'images/ALTERNATIVES_SOURCE_LIST.json'),
    ]
    for case in ('SPAN', 'COUNTER'):
        for index in (0, 1):
            sources.append((args.root/case/f'actual_parent_{index}.npz', f'{case}/actual_parent_{index}.npz'))
        sources.append((args.root/case/'guided_colonies.npz', f'{case}/guided_colonies.npz'))
        for stage in (4, 5):
            sources.append((args.active_root/case/f'G{stage:02d}_incoming_curves.npz', f'{case}/G{stage:02d}_incoming_curves.npz'))
        for mode in ('BASELINE', 'VALLEY_PRIORITY', 'FLOW_CHAIN'):
            sources.append((args.root/mode/case/'G06/generation.json', f'{case}/{mode}.json'))
        sources.append((args.meso_root/'MESO_ONLY_PATCH'/case/'G06/generation.json', f'{case}/MESO_ONLY_PATCH.json'))
        sources.append((args.active_root/'ACTIVE_FOLDS'/case/'G06/generation.json', f'{case}/ACTIVE_FOLDS.json'))
        for view in ('front_micro', 'oblique_micro', 'side_micro', 'front'):
            for suffix in ('', '_alternatives'):
                name = f'{case}_{view}{suffix}.png'
                sources.append((args.root/'images'/name, 'images/'+name))
    missing = [str(source) for source, _ in sources if not source.is_file()]
    if missing:
        raise FileNotFoundError('\n'.join(missing))
    if args.dest.exists():
        raise FileExistsError('Earlier archive preserved: '+str(args.dest))
    args.dest.mkdir(parents=True)
    records = []
    for source, relative in sources:
        destination = args.dest/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if digest(source) != digest(destination):
            raise ValueError('Evidence copy differs: '+str(source))
        records.append(dict(source=str(source.resolve()), archive=relative,
            bytes=source.stat().st_size, sha256=digest(destination)))
    source_hashes = {str(path.relative_to(REPO)): digest(path)
        for path in sorted(HERE.glob('*')) if path.is_file()}
    source_hashes.update({str(path.relative_to(REPO)): digest(path)
        for path in sorted((REPO/'tests').glob('test_parent_guided*.py'))})
    source_hashes['tests/test_guidance_parent.py'] = digest(REPO/'tests/test_guidance_parent.py')
    identity = dict(large_outputs=dict(main=str(args.root.resolve()),
        meso_only=str(args.meso_root.resolve()), active_folds=str(args.active_root.resolve())),
        source_hashes=source_hashes, copied_evidence=records,
        scientific_meshes='Large control/native geometry remains on E; generation hashes and verified replay link it to this evidence.')
    (args.dest/'SOURCE_LIST.json').write_text(json.dumps(identity, ensure_ascii=False, indent=2), encoding='utf8')
    print('ARCHIVED', len(records), args.dest, flush=True)


if __name__ == '__main__':
    main()
