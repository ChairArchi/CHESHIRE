"""Preserve split render runs and verify matched, uncropped native views."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
from PIL import Image


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('receipt_renderer', HERE.parent/'fold_visible_gate_20261012/render.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
VIEWS = ('front_micro', 'oblique_micro', 'side_micro', 'front')
MODES = ('BASELINE', 'VALLEY_PRIORITY', 'FLOW_CHAIN')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def archive_span(root):
    for mode in MODES:
        folder = root/mode/'SPAN/G06/views'
        source, target = folder/'receipt.json', folder/'receipt_front_oblique_micro.json'
        if target.exists() or set(read(source)['views']) != {'front_micro', 'oblique_micro'}:
            raise ValueError('Expected the preserved initial SPAN micro run: '+str(folder))
        shutil.copy2(source, target)


def merge_span(root):
    for mode in MODES:
        folder = root/mode/'SPAN/G06/views'
        oldpath, currentpath = folder/'receipt_front_oblique_micro.json', folder/'receipt.json'
        newpath = folder/'receipt_front_side_micro.json'
        old, new = read(oldpath), read(currentpath)
        if newpath.exists() or set(old['views']) != {'front_micro', 'oblique_micro'} or set(new['views']) != {'front', 'side_micro'}:
            raise ValueError('Expected two distinct saved render runs: '+str(folder))
        for key in ('engine', 'version', 'resolution', 'samples', 'material', 'modifiers', 'normal_maps'):
            if old[key] != new[key]:
                raise ValueError('Render settings differ: '+key)
        if Path(old['source']).resolve() != Path(new['source']).resolve():
            raise ValueError('Render source differs.')
        shutil.copy2(currentpath, newpath)
        merged = dict(new, views={**old['views'], **new['views']},
            merged_from=[str(oldpath), str(newpath)])
        write(currentpath, merged)


def verify(root, meso, active):
    result = dict(passed=True, resolution=900, samples=24, crop=False,
        material='Existing uniform mineral; flat geometric normals', states=[])
    for case in ('SPAN', 'COUNTER'):
        folders = [(mode, root/mode/case/'G06') for mode in MODES]
        folders += [('MESO_ONLY_PATCH', meso/'MESO_ONLY_PATCH'/case/'G06'),
                    ('ACTIVE_FOLDS', active/'ACTIVE_FOLDS'/case/'G06')]
        for mode, folder in folders:
            receipt_path = folder/'views/receipt.json'
            receipt = read(receipt_path)
            if (receipt['resolution'] != 900 or receipt['samples'] != 24 or
                receipt['engine'] != 'Blender Cycles' or receipt['material'] != result['material'] or
                receipt['modifiers'] != [] or receipt['normal_maps'] is not False or
                Path(receipt['source']).resolve() != (folder/'geometry.npz').resolve()):
                raise ValueError('Nonmatching native render: '+str(folder))
            files = []
            for view in VIEWS:
                expected = json.loads(json.dumps(renderer.COL_VIEWS[view]))
                if receipt['views'].get(view) != expected:
                    raise ValueError('Camera differs: '+str(folder)+' '+view)
                path = folder/'views'/f'{view}.png'
                with Image.open(path) as im:
                    if im.size != (900, 900):
                        raise ValueError('Image dimensions differ: '+str(path))
                    im.verify()
                files.append(dict(view=view, path=str(path), sha256=digest(path)))
            result['states'].append(dict(input_case=case, candidate=mode,
                render_receipt_sha256=digest(receipt_path), geometry_file_sha256=digest(folder/'geometry.npz'),
                generation_sha256=digest(folder/'generation.json'), images=files))
    target = root/'RENDER_VERIFICATION.json'
    if target.exists():
        raise FileExistsError('Earlier render verification preserved.')
    write(target, result)
    print('RENDER_VERIFICATION_PASS', len(result['states']), 'states, 40 images', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--action', choices=('archive-span', 'merge-span', 'verify'), required=True)
    p.add_argument('--meso-root', type=Path)
    p.add_argument('--active-root', type=Path)
    args = p.parse_args()
    if args.action == 'archive-span':
        archive_span(args.root)
    elif args.action == 'merge-span':
        merge_span(args.root)
    else:
        if not args.meso_root or not args.active_root:
            p.error('Both alternative roots required.')
        verify(args.root, args.meso_root, args.active_root)
