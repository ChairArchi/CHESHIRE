"""Package selected actual Task23 evidence; never distribute runtime binaries."""
import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'examples'))
from cross_cell_crease_study import read, write, digest, file_hash
from cross_cell_crease_views import best_attempt

MACHINE_PATH = re.compile(r'[A-Za-z]:[\\/](?:Users|Program Files)[\\/]', re.I)
SECRET = re.compile(r'(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
PROOFS = ('verification.json', 'retained_reproduction.json', 'retained_selection.json',
          'task23_camera.json', 'large_taper_probe.json', 'override_interrupted_attempts.json')


def prepare(root):
    """Small tracked evidence only; geometry remains in the external root."""
    destination = ROOT/'studies/task23'
    for name in PROOFS:
        value = read(root/'study'/name)
        assert not MACHINE_PATH.search(json.dumps(value)), name
        write(destination/name, value)
    write(destination/'test_result.json', read(destination/'selection.json')['test_result'])
    controls = []
    for name in ('CTRL_cube_04', 'CTRL_column_04', 'CTRL_U_gate_04'):
        d = best_attempt(root, 'CONTROL', name); s = read(d/'summary.json')
        assert s['status'] == 'SUCCESS'
        controls.append(dict(case=name, artifact=d.relative_to(root).as_posix(),
            recipe=s['recipe'], geometry_sha256=s['output_sha256'],
            final_contrast=s['stages'][-1]['networks'][0]['visible_crease_survival_ratio']))
    write(destination/'morphology_library.json', dict(version=1,
        previous_library=dict(path='studies/task21/morphology_library.json', sha256=file_hash(ROOT/'studies/task21/morphology_library.json')),
        crease_fragments=[dict(id='LONG_CREASE', scope='Closed verified control cages only; not a proven whole-gate transplant',
            operator='Reference COMPAS integer crease CC', sharpness=6, generations=6, successful_contexts=controls,
            lineage_contract='Two exact structural descendants per edge, finite Uniform decay; available constructive ancestry only',
            known_failure_boundaries=['A05 whole-gate reference route loses threshold contrast.',
                'Maintaining a crease does not create a new fold or a coherent meso hierarchy.'])],
        excluded=dict(SHOULDER_FAN_CREASE='Gate fans remain swollen or fragmented.',
            CREASE_JUNCTION='Angular convergence demonstrated, useful hierarchical nodes not established.',
            CREASE_ROOF='Local reinforcement only.', CREASE_NESTED_ORNAMENT='Actual depth, insufficient visual hierarchy.',
            VARIABLE_SHARPNESS_RIDGE='No demonstrated morphological improvement.'),
        contract='Separate context-bound Task23 extension; existing Task21 entries and validator are unchanged.'))
    evidence = destination/'evidence'; evidence.mkdir(exist_ok=True)
    pictures = {'whole_gate.png': 'CAPABILITY/ATLAS_front_FINAL_01.png',
        'node_detail.png': 'CAPABILITY/ATLAS_node_FINAL_01.png',
        'retained_wire.png': 'CAPABILITY/R20_E5_wire.png',
        'retained_network.png': 'CAPABILITY/R20_E5_front_network.png',
        'retained_sharpness.png': 'CAPABILITY/R20_E5_sharpness.png',
        'retained_ancestry.png': 'CAPABILITY/R20_E5_ancestry.png',
        'retained_depth.png': 'CAPABILITY/R20_E5_depth.png',
        'control_initial.png': 'CONTROL/CTRL_cube_04_G0_front.png',
        'control_sixth.png': 'CONTROL/CTRL_cube_04_G6_front.png'}
    images = []
    for name, relative in pictures.items():
        source = root/'renders'/relative; shutil.copyfile(source, evidence/name)
        images.append(dict(file='evidence/'+name, source='renders/'+relative, sha256=file_hash(source)))
    write(destination/'tracked_evidence.json', dict(images=images,
        kind='Actual headless polygon projections; same camera/scale/light; overlays include hidden edges',
        limitations='Painter sorting/first-triangle normals approximate shading, particularly on intersections; fixed camera clips extreme branches.'))
    logs = root/'review_logs'; logs.mkdir(exist_ok=True)
    exports = []
    for filename in ('task23_full_pytest.txt', 'task23_identity_recheck.txt'):
        source = ROOT/'output'/filename
        raw = source.read_bytes()
        text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
        text = text.replace(ROOT.as_posix(), '<repository>').replace(str(ROOT), '<repository>')
        assert not MACHINE_PATH.search(text), filename
        target = logs/filename; target.write_text(text, encoding='utf-8')
        exports.append(dict(file=filename, original_sha256=file_hash(source), exported_sha256=file_hash(target),
            redaction='Only local repository path prefix replaced by <repository>; failure/status unchanged.'))
    write(logs/'test_log_export.json', exports)
    print('Prepared', len(images), 'tracked actual images, control fragment and honest test evidence')


def package(root, archive, preflight=False):
    """Selected artifact closure, explicit omissions and byte inventory."""
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        raise ValueError('Review archive already exists; do not overwrite a delivered package.')
    if not preflight:
        publication = read(root/'study/publication.json')
        assert publication['push']['status'] == 'PASS'
        assert publication['distribution_audit'] == 'PASS'
    files = {}; omissions = []; versions = {}; reconstructions = []

    def add(path, name):
        path = Path(path); assert path.is_file(), str(path)
        assert name not in files or files[name] == path, name
        assert '..' not in Path(name).parts
        files[name] = path

    def checkpoints(directory, stages, terminal=False):
        base = 'data/'+directory.relative_to(root).as_posix()
        for stage in stages:
            for suffix in ('.json.gz', '_lineage.json.gz', '_signatures.json.gz', '_networks.json'):
                path = directory/(stage+suffix)
                if path.exists(): add(path, base+'/'+path.name)
            operator = directory/(stage+'_operator.json.gz')
            if operator.exists():
                text = json.dumps(read(operator), separators=(',', ':'))
                if MACHINE_PATH.search(text):
                    omissions.append(dict(file=base+'/'+operator.name, canonical_sha256=digest(read(operator)),
                        reason='Runtime backend annotation contains external local DLL path. Original is retained externally; omitted, not silently rewritten. Geometry/history/events are included.'))
                else: add(operator, base+'/'+operator.name)
        for name in ('summary.json', 'request.json', 'branch_signatures.json'):
            path = directory/name
            if path.exists(): add(path, base+'/'+name)
        if terminal:
            for name in ('terminal.obj', 'terminal.json', 'terminal_lineage.json.gz',
                         'terminal_signatures.json.gz', 'terminal_networks.json'):
                path = directory/name
                if path.exists(): add(path, base+'/'+name)
        request = read(directory/'request.json') if (directory/'request.json').exists() else {}
        for relative, sha in request.get('code', {}).get('source_files', {}).items():
            current = ROOT/relative
            if current.exists() and file_hash(current) == sha: continue
            original = root/'cache/source_snapshots'/sha/relative
            assert original.exists() and file_hash(original) == sha, relative
            add(original, 'source_revisions/'+sha+'/'+relative)
            versions[(relative, sha)] = True
        omissions.append(dict(file=base+'/worker_identity.json', reason='Machine-specific runtime identity is intentionally excluded. Saved summaries retain original artifact hashes; ZIP inventory is the transport identity.'))

    names = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    for name in names:
        p = Path(name)
        include = (p.parts[0] in ('src', 'tests', 'examples', 'tools', 'rhino') and p.suffix in ('.py', '.ps1', '.md'))
        include |= name in ('pyproject.toml', 'README.md', '.gitignore')
        include |= name.startswith('studies/task23/')
        include |= name in ('studies/task21/camera.json', 'studies/task21/morphology_library.json')
        include |= name in ('docs/CROSS_CELL_CREASE_REFERENCE.md', 'docs/CROSS_CELL_CREASE_STUDY.md')
        if include: add(ROOT/name, 'CHESHIRE/'+name)
    for path in sorted((root/'inputs').iterdir()):
        if path.is_file(): add(path, 'data/inputs/'+path.name)
    selection = read(ROOT/'studies/task23/selection.json')
    for item in selection['finalists']:
        d = best_attempt(root, item['phase'], item['id']); s = read(d/'summary.json')
        stage = item.get('stage', s['stages'][-1]['stage'])
        stages = list(dict.fromkeys(['G0', stage]))
        checkpoints(d, stages, terminal=not item.get('stage'))
        add(root/'study/recipes'/(item['id']+'.json'), 'data/study/recipes/'+item['id']+'.json')
        prepared = s['recipe'].get('prepared_substrate')
        if prepared:
            pd = root/prepared['artifact']; checkpoints(pd, ['G0', prepared['stage']])
            # A saved continuation is not claimed independently portable with omitted runtime annotations.
            if s['recipe'].get('continuation_of'):
                original = deepcopy(read(root/'study/recipes'/(s['recipe']['continuation_of']+'.json')))
                original['id'] = item['id']+'_FULL_DECLARATION'
                original['policy_override'] = True
                original['assessment'] = 'Unrolled full declaration from the actually completed prefix/tail; not independently replayed. R20 is the independently verified portable recipe.'
                reconstructions.append(original)
        prefix = item['id']+'_'+stage+'_'
        for picture in (root/'renders'/item['phase']).glob(prefix+'*.png'):
            add(picture, 'data/'+picture.relative_to(root).as_posix())
        metric=root/'renders'/item['phase']/(prefix+'high_angle_metrics.json')
        if metric.exists(): add(metric, 'data/'+metric.relative_to(root).as_posix())
        # Initial images retain actual parent boundaries and routing seeds.
        for picture in (root/'renders'/item['phase']).glob(item['id']+'_G0_*.png'):
            add(picture, 'data/'+picture.relative_to(root).as_posix())
    for phase, case in (('HERO', 'RETAINED_GATE_GRAMMAR'), ('REPLAY', 'RETAINED_GATE_REPLAY')):
        d = best_attempt(root, phase, case); s = read(d/'summary.json')
        checkpoints(d, [row['stage'] for row in s['stages']] if phase == 'HERO' else ['G0'], terminal=True)
        add(root/'study/recipes'/(case+'.json'), 'data/study/recipes/'+case+'.json')
    for case in ('CTRL_cube_03', 'CTRL_cube_04', 'CTRL_cube_08', 'CTRL_cube_10'):
        d = best_attempt(root, 'CONTROL', case); s = read(d/'summary.json')
        checkpoints(d, ['G0', s['stages'][-1]['stage']])
        for image in (root/'renders/CONTROL').glob(case+'_*.png'):
            add(image, 'data/'+image.relative_to(root).as_posix())
    # Compact failures/interrupted evidence; not all screening geometry.
    for phase in ('DESIGN', 'REFINE', 'CAPABILITY'):
        rows = read(ROOT/'studies/task23'/('table_'+phase.lower()+'.json'))
        for row in rows:
            if row['status'] == 'SUCCESS': continue
            d = root/row['attempt']; s = read(d/'summary.json')
            checkpoints(d, [s['stages'][-1]['stage']] if s['stages'] else [])
    for path in (root/'study').glob('*.json'):
        if path.name not in ('plan.json', 'downstream_declarations.json', 'refinement_declarations.json'):
            add(path, 'data/study/'+path.name)
    for path in (root/'review_logs').iterdir():
        if path.is_file(): add(path, 'logs/'+path.name)
    for name in ('FINAL_REPORT.md', 'REVIEW_MANIFEST.md'):
        add(root/name, name)
    inventory = []; text_audited = 0
    # Verify exclusions before creating the final archive, so a failed audit
    # cannot leave a partial delivery with the requested final filename.
    for name, path in sorted(files.items()):
        assert path.suffix.lower() not in ('.dll', '.gha', '.exe', '.pdb', '.zip'), name
        content = path.read_bytes()
        checked = gzip.decompress(content) if path.name.endswith('.json.gz') else content
        if path.suffix in ('.py', '.ps1', '.md', '.toml', '.txt', '.json', '.gz', '.patch') or path.name == '.gitignore':
            text = checked.decode('utf-8-sig')
            assert not MACHINE_PATH.search(text), name
            assert not SECRET.search(text), name
            text_audited += 1
        inventory.append(dict(file=name, bytes=len(content), sha256=hashlib.sha256(content).hexdigest()))
    if preflight:
        result = dict(status='PASS', action='Pre-publication payload audit only; no archive created',
            payload_files=len(inventory), bytes=sum(row['bytes'] for row in inventory), text_files_audited=text_audited)
        print(json.dumps(result, indent=2)); return result
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for name, path in sorted(files.items()):
            content = path.read_bytes()
            compression = zipfile.ZIP_STORED if path.suffix in ('.gz', '.png') else zipfile.ZIP_DEFLATED
            bundle.writestr(name, content, compress_type=compression)
        bundle.writestr('checkpoint_omissions.json', json.dumps(omissions, indent=2)+'\n')
        bundle.writestr('unrolled_continuation_declarations.json', json.dumps(reconstructions, indent=2)+'\n')
        bundle.writestr('source_revisions.json', json.dumps([dict(file=n, sha256=h) for n,h in sorted(versions)], indent=2)+'\n')
        bundle.writestr('INVENTORY.json', json.dumps(inventory, indent=2)+'\n')
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert len(bundle.namelist()) == len(set(bundle.namelist()))
    result = dict(status='PASS', archive=str(archive), bytes=archive.stat().st_size, sha256=file_hash(archive),
        payload_files=len(inventory), auxiliary_files=4, text_files_audited=text_audited,
        omitted_runtime_annotations=len(omissions), first_party_revision_files=len(versions),
        scope='Selected actual geometry only; no all-screen geometry, runtime identities, binaries, upstream source, environments, old ZIPs or large cache.')
    write(root/'study/review_archive.json', result)
    print(json.dumps(result, indent=2)); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output-root', type=Path, required=True)
    p.add_argument('--prepare', action='store_true'); p.add_argument('--archive', type=Path)
    p.add_argument('--preflight', action='store_true')
    a = p.parse_args()
    if a.prepare: prepare(a.output_root)
    elif a.archive: package(a.output_root, a.archive, a.preflight)
    else: p.error('Choose --prepare or --archive')
