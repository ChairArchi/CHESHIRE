"""Collect hash-verified replay sources/assets without changing any source.

This archive restores the recorded workspace. It is not a relocation adapter
and makes no standalone replay or other-computer portability claim.
"""
from __future__ import annotations

import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EXP = Path('E:/CHESHIRE_DATA/experiments/selective_overlap_20261017')
SCHEMA = 'CHESHIRE_SELECTIVE_RECORDED_WORKSPACE_REPLAY_BUNDLE_V1'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def collect_replay_bundle(add_file, *, finish=None, experiment_root=EXP,
                          repository=REPO):
    """Call ``add_file(path, archive_name)`` once per unique archive member.

    Return a JSON-safe manifest. The caller should add that manifest and
    ``reproduction_instructions(manifest)`` using ZipFile.writestr. ``finish``
    must point to the completed finish output for a final bundle; None provides
    an explicitly incomplete, source/early/G5 preflight only. No file is written
    here. Duplicate sources must have identical SHA256 or collection fails.
    """
    repo, exp = Path(repository).resolve(), Path(experiment_root).resolve()
    run = exp/'full_pipeline/L08_PRIMARY_193'
    files, duplicates, external = {}, [], []
    finish_entrypoint = None

    def add(path, name=None, expected=None, purpose=''):
        path = Path(path).resolve()
        if not path.is_file():
            raise FileNotFoundError('Required replay dependency: '+str(path))
        observed = sha(path)
        if expected is not None and observed != expected:
            raise ValueError('Replay dependency SHA differs: '+str(path))
        if name is None:
            if path.is_relative_to(repo):
                name = 'repo/'+path.relative_to(repo).as_posix()
            else:
                name = 'workspace_assets/'+path.drive.rstrip(':')+'/'+Path(*path.parts[1:]).as_posix()
        if name in files:
            if files[name]['sha256'] != observed:
                raise ValueError('Conflicting executed source versions: '+name)
            duplicates.append(dict(archive_path=name, matching_source=str(path)))
            return
        files[name] = dict(archive_path=name, source_path=str(path),
                           sha256=observed, bytes=path.stat().st_size, purpose=purpose)
        add_file(path, name)

    def source(original, snapshot, expected, stage):
        original, snapshot = Path(original).resolve(), Path(snapshot).resolve()
        if not original.is_relative_to(repo):
            raise ValueError('Executed Python source outside declared repository: '+str(original))
        if sha(original) != expected:
            raise ValueError('Current executed source changed: '+str(original))
        add(snapshot, 'repo/'+original.relative_to(repo).as_posix(), expected,
            'Verified executed '+stage+' Python snapshot; restore under repo/')

    source_root = exp/'source_candidates_v2'
    source_manifest = read(source_root/'SOURCE_SNAPSHOTS.json')
    for original, item in source_manifest['sources'].items():
        source(original, item['path'], item['sha256'], 'G0')
    early = read(run/'RECIPE.json')
    for original, item in early['source_snapshots'].items():
        source(original, item['snapshot'], item['sha256'], 'G0-to-G4')
    g5 = read(run/'G5_ONLY_RECIPE.json')
    for relative, expected in g5['geometry_code_sha256'].items():
        source(repo/relative, run/'g5_only_source_snapshot'/relative, expected, 'G5')

    if finish is not None:
        finish = Path(finish).resolve()
        result = read(finish/'RECEIPT.json')
        if result.get('status') != 'PASS' or result.get('actual_generation') != 5:
            raise ValueError('Completed actual-G5 finish receipt required.')
        for original, item in result['geometry_code'].items():
            source(original, item['snapshot'], item['sha256'], 'finish')
            if Path(original).name.startswith('finish_selective'):
                finish_entrypoint = Path(original).relative_to(repo).as_posix()
        assets = result['source_assets']
        for section in ('mandel', 'tissue'):
            for key in ('receipt', 'arrays', 'height_grid'):
                if key in assets[section]:
                    item = assets[section][key]
                    add(item['path'], expected=item['sha256'], purpose='Exact finish runtime asset')
        for item in assets['tissue'].get('source_provenance', {}).values():
            add(item['path'], expected=item['sha256'], purpose='Finish load_assets validates this actual Tissue source provenance')
        add(finish/'RECEIPT.json', purpose='Completed actual G5 finish execution record')

    # Controllers share the real original relative tree, not a separate folder
    # whose HERE.parents imports would resolve to nonexistent sibling modules.
    for path in sorted(HERE.glob('*.py')):
        add(path, purpose='Selective-overlap controller/review/QA source')
    for relative in ('experiments/selective_overlap_20261017/selective_recipes.json',
                     'experiments/selective_overlap_20261017/selective_recipes_v2.json',
                     'experiments/selective_overlap_20261017/pipeline_recipe.json',
                     'experiments/overlapping_fold_layout_20261017/overlap_recipes.json'):
        add(repo/relative, purpose='Required original-source comparison or actual pipeline recipe')
    docs = repo/'docs/generation_workflow_20261013'
    for path in sorted(docs.rglob('*.json')):
        add(path, purpose='Original selected_receipts/late.recipe_proof frozen recipe verification')
    lineage = read(docs/'LINEAGE.json')
    for node in lineage['nodes'][:7]:
        add(node['receipt'], expected=node['receipt_sha256'], purpose='Original selected early receipt, required at its recorded workspace path')
    for item in early['historical_recipe_references'].values():
        add(item['path'], expected=item['sha256'], purpose='Actual early replay selected receipt')
    original25 = Path(lineage['nodes'][0]['receipt']).parent
    for name in ('control_quad.npz', 'operation_fields.npz', 'generation.json'):
        add(original25/name, purpose='Small original25 exact_original_seed assets required by G0 comparison regeneration')

    for name in ('RECEIPT.json', 'SOURCE_SNAPSHOTS.json', 'BASELINE_GUARDS.json', 'SELECTIVE_RECIPES_V2.json'):
        add(source_root/name, purpose='Frozen source generation/controller evidence')
    for path in sorted((source_root/'L08_PRIMARY_193').iterdir()):
        if path.is_file():
            add(path, purpose='Authoritative selected193 G0 runtime arrays and receipt; original paths are hash-bound')
    for name in ('RECIPE.json', 'RECIPE_EARLY.json', 'STAGES_EARLY.json', 'RECEIPT.json', 'G5_ONLY_RECIPE.json'):
        add(run/name, purpose='Actual early/G5 recipe and replay bindings')
    for stage in sorted((run/'states').iterdir()):
        if stage.is_dir():
            for path in sorted(stage.glob('*.json')):
                add(path, purpose='Small actual stage metadata; dense stage arrays are regenerated')

    # Actual selected target grids are small (~2 MB together). Include and
    # rehash those; only genuinely large alternative grids remain external.
    for stage in ('G01_ANCESTRY', 'G02_OVERLAP'):
        info = read(run/'states'/stage/'generation.json')
        cache = info['field_cache']
        base = Path(cache['path'])
        add(base/'field.json', expected=cache['field_json_sha256'], purpose='Small immutable finite-field cache parameters')
        grid = base/'outside_grid.npz'
        if not grid.is_file():
            raise FileNotFoundError('Required external finite-field target grid: '+str(grid))
        if grid.stat().st_size <= 16*1024**2:
            add(grid, expected=cache['outside_grid_sha256'],
                purpose='Exact finite outside target grid; restore at recorded E workspace path')
        else:
            external.append(dict(path=str(grid), bytes=grid.stat().st_size,
                sha256=cache['outside_grid_sha256'], included=False,
                checksum_source=str(run/'states'/stage/'generation.json'),
                checksum_rehashed_by_collector=False,
                purpose='Original finite outside target grid required unchanged; intentionally external large asset above16MiB'))
    versions = {}
    for package in ('numpy', 'scipy', 'trimesh', 'compas', 'psutil', 'matplotlib'):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            pass
    return dict(schema=SCHEMA, scope='Recorded original workspace replay source-and-small-asset archive',
        repository_path=str(repo), experiment_root=str(exp),
        finish_collected=finish is not None, finish_entrypoint=finish_entrypoint,
        status='COLLECTED' if finish is not None else 'PREFLIGHT_FINISH_PENDING',
        files=list(files.values()), matching_duplicate_sources=duplicates,
        external_large_dependencies=external, python=sys.version,
        platform=platform.platform(), observed_library_versions=versions,
        original_sources_modified=False, other_computer_portability_claimed=False,
        automatic_absolute_path_relocation=False, standalone_unzip_replay_verified=False,
        fresh_G0_constructor_replay_source_included=True,
        actual_G4_replay_source_included=True, actual_G5_operator_source_included=True,
        late_G6_or_G7_replay_claimed=False,
        final_Tissue_semantics='Existing actual component height-grid reuse; no new plugin call or full-XYZ source graft',
        archive_restore_policy='Restore repo/ relative tree and explicitly restore workspace_assets at source_path only in a separate/reviewed workspace. Frozen absolute paths/hashes are intentionally retained.')


def reproduction_instructions(manifest):
    """Plain text instructions; preserves every existing artifact by default."""
    return ('CHESHIRE selective-overlap recorded-workspace replay archive\n\n'
        'Scope: source and small assets for the recorded workspace; not a standalone other-computer package.\n'
        'repo/ is one complete relative Python import tree (experiments/, src/, docs/).\n'
        'workspace_assets/ records small original absolute-path dependencies. The manifest maps each file to its source_path and SHA256.\n'
        'Do not overwrite existing artifacts. Use a separate reviewed reconstruction workspace; path rebasing is not implemented here.\n'
        'The selected F02/F03 outside_grid.npz caches are included as workspace_assets with verified SHA256 and original E paths. Only grids above16MiB are external, if any, and are listed explicitly in the manifest.\n'
        'Observe the recorded Python/library versions. Bit-exact replay across library/platform changes has not been asserted.\n\n'
        'Original recorded stages (choose fresh output roots):\n'
        '1. experiments/selective_overlap_20261017/generate_selective_v2.py --output FRESH_SOURCE_COMPARISON\n'
        '   Re-evaluates the original constructor and 193-ring baseline/selected/comparator sources.\n'
        '2. experiments/selective_overlap_20261017/replay_selective.py --recipe experiments/selective_overlap_20261017/pipeline_recipe.json --output FRESH_PIPELINE\n'
        '   Binds the authoritative frozen193 G0 receipt and executes actual original G1/G2/WALL/ROOT/SIDEWALL/G4.\n'
        '3. experiments/selective_overlap_20261017/advance_directional_g5.py --root FRESH_PIPELINE\n'
        '   One unchanged actual DIRECTIONAL G4-to-G5 subdivision. No G6/G7.\n'
        '4. '+(manifest.get('finish_entrypoint') or 'experiments/selective_overlap_20261017/finish_selective.py')+' --help\n'
        '   Use final receipt parameters with a fresh output; cached finite Mandel and actual Tissue height-grid assets are included.\n\n'
        'The source recipe and receipt paths remain exactly as recorded. Repointing a frozen receipt requires a separately recorded adapter and new bindings.\n'
        'This collection verifies dependency hashes and identical duplicate source versions; it does not claim a fresh unzip replay was executed.\n'
        'Prototype limits: self-intersection/fabrication certification is absent. Tissue height-grid reuse does not transfer original 3D handles or overhangs.\n')
