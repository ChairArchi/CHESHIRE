"""Compact exact replay of two single-surface G5 finishing recipes on two inputs.

Atlas, colony frames and recipes are copied. Large controls, operation fields
and native arrays are regenerated from the already packaged WALL G3 parents and
compared against every original per-array hash. No detached component geometry
is included, and a successful numeric replay is not an aesthetic verdict.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import shutil

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KINDS = ('BOLD_DETAIL', 'INTEGRATED')
CASES = ('SPAN', 'COUNTER')
FILES = ('control_quad.npz', 'operation_fields.npz', 'geometry.npz')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def arrays(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def array_hashes(data):
    return {key: dict(shape=list(value.shape), dtype=value.dtype.str,
        sha256=hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest())
        for key, value in data.items()}


def expected_arrays(sources):
    result = {}
    for kind, source in sources.items():
        result[kind] = {}
        for case in CASES:
            result[kind][case] = {}
            for mode in (kind, 'CONTROL'):
                folder = source/mode/case/'G05'
                result[kind][case][mode] = {}
                for name in FILES:
                    result[kind][case][mode][name] = array_hashes(arrays(folder/name))
    return result


def validate_colony_sources(colonies, source_native):
    triangles = source_native.faces[:, :3]
    ids, bary = colonies['primary_source_triangle_ids'], colonies['primary_source_barycentric']
    primary_xyz = np.einsum('ni,nij->nj', bary, source_native.xyz[triangles[ids]])
    primary_error = float(np.max(np.abs(primary_xyz-colonies['primary_source_xyz']), initial=0.))
    primary = colonies['levels'] == 0
    primary_centres_error = float(np.max(np.abs(colonies['centres'][primary]-colonies['primary_source_xyz']), initial=0.))
    secondary = colonies['levels'] == 1
    secondary_error = float(np.max(np.abs(colonies['centres'][secondary]-
        source_native.xyz[colonies['native_vertex_ids'][secondary]]), initial=0.))
    frame = np.stack([colonies['tangents'], colonies['bitangents'], colonies['normals']], axis=2)
    frame_error = float(np.max(np.abs(np.einsum('nji,njk->nik', frame, frame)-np.eye(3))))
    return dict(primary_native_reconstruction_max_error=primary_error,
        primary_centres_max_error=primary_centres_error, secondary_native_centres_max_error=secondary_error,
        pooled_frame_orthogonality_max_error=frame_error,
        passed=bool(max(primary_error, primary_centres_error, secondary_error, frame_error) < 1e-12))


def verify(destination, expected, progress=False):
    import bulb_detail as bulb
    destination = Path(destination).resolve()
    copy_receipt = json.loads((destination/'COPY_RECEIPT.json').read_text(encoding='utf8'))
    copied = copy_receipt['copied_assets']
    if not copied or len({entry['path'] for entry in copied}) != len(copied):
        raise ValueError('Nonempty, unique finish asset inventory required.')
    for entry in copied:
        asset = (destination/entry['path']).resolve()
        if not asset.is_relative_to(destination) or not asset.is_file():
            raise ValueError('Missing or external finish asset: '+entry['path'])
        if asset.stat().st_size != entry['bytes'] or sha(asset) != entry['sha256']:
            raise ValueError('Copied finish asset hash differs: '+entry['path'])
    if set(expected) != set(KINDS) or any(set(expected[kind]) != set(CASES) for kind in KINDS):
        raise ValueError('Exactly two declared recipes and SPAN/COUNTER cases are required.')
    atlas = arrays(destination/'atlas/power8.npz')
    records = []
    t = bulb.study.previous.anchor.t
    for case in CASES:
        source = destination.parent/'WALL'/case/'G03'
        mesh, chart, tags = t.load(source)
        if mesh.generation != 3:
            raise ValueError('Actual packaged WALL G3 parent required: '+case)
        source_native = t.growth.native(mesh)
        out, outchart, outtags = mesh, chart, tags
        for _ in range(2):
            out, outchart, outtags, operator = t.memory.refine(out, outchart, outtags)
        reference = out.xyz.copy()
        initial_native = t.growth.native(out)
        incoming_surface = trimesh.Trimesh(initial_native.xyz, initial_native.faces[:, :3], process=False)
        incoming_normals = incoming_surface.vertex_normals[:len(reference)].copy()
        inactive_topology = dict(components=int(incoming_surface.body_count),
            watertight=bool(incoming_surface.is_watertight),
            winding_consistent=bool(incoming_surface.is_winding_consistent),
            physical_vertices=len(initial_native.xyz))
        if (inactive_topology['components'] != 1 or not inactive_topology['watertight'] or
            not inactive_topology['winding_consistent']):
            raise ValueError('Inactive reference must be one connected closed oriented surface: '+case)
        del incoming_surface
        control_base = dict(faces=out.faces, chart=outchart, classes=out.classes, rest=out.rest,
            anchors=out.anchors, generation=np.array(out.generation), surface=np.array(out.surface), memory=outtags)
        operation_base = dict(reference_xyz=reference, chart=outchart, incoming_normals=incoming_normals,
            input_edges=operator['input_edges'], parent_face=operator['parent_face'])
        inactive_delta = np.zeros_like(reference)
        existing = t.prior.helpers.existing
        existing.reflect(inactive_delta, outchart, existing.symmetry(outchart))
        inactive = dict(**{'control_quad.npz': dict(control_base, xyz=reference),
            'operation_fields.npz': dict(operation_base, pre_reflection_delta=np.zeros_like(reference), delta=inactive_delta),
            'geometry.npz': dict(xyz=initial_native.xyz, faces=initial_native.faces[:, :3])})
        inactive_hashes = {name: array_hashes(data) for name, data in inactive.items()}
        del initial_native, inactive, inactive_delta
        for kind in KINDS:
            folder = destination/kind/case/'G05'
            metadata = json.loads((folder/'generation.json').read_text(encoding='utf8'))
            if (metadata['candidate'] != kind or metadata['input_case'] != case or
                metadata['output_generation'] != 5 or metadata['inactive_refinement_passes'] != 2):
                raise ValueError('Declared single-surface G5 recipe metadata differs.')
            source_hash_matches = sha(source/'control_quad.npz') == metadata['source_control_sha256']
            colonies = arrays(folder/'colonies.npz')
            colony_provenance = validate_colony_sources(colonies, source_native)
            delta, fields = bulb.apply_colonies(reference, outchart, incoming_normals, colonies,
                atlas, metadata['maximum_height'], recipe=metadata['variant_recipe'])
            raw = delta.copy()
            existing = t.prior.helpers.existing
            pairs = existing.symmetry(outchart)
            existing.reflect(delta, outchart, pairs)
            fields['final_symmetric_height'] = bulb.reflect_scalar(fields['height'].copy(), outchart, pairs)
            out.xyz = reference+delta
            native = t.growth.native(out)
            actual = {'control_quad.npz': dict(control_base, xyz=out.xyz),
                'operation_fields.npz': dict(operation_base, pre_reflection_delta=raw, delta=delta, **fields),
                'geometry.npz': dict(xyz=native.xyz, faces=native.faces[:, :3])}
            checks = {name: array_hashes(data) == expected[kind][case][kind][name]
                for name, data in actual.items()}
            inactive_checks = {name: hashes == expected[kind][case]['CONTROL'][name]
                for name, hashes in inactive_hashes.items()}
            # Exact native topology is inherited from the inactive reference;
            # no vertices/faces or disconnected decoration are appended.
            topology_inherited = bool(
                len(native.xyz) == inactive_topology['physical_vertices'] and
                array_hashes({'faces': native.faces[:, :3]})['faces'] == inactive_hashes['geometry.npz']['faces'] and
                array_hashes({'faces': out.faces})['faces'] == inactive_hashes['control_quad.npz']['faces'])
            maximum = float(np.linalg.norm(delta, axis=1).max())
            bounded = maximum <= metadata['maximum_height']+1e-12
            passed = (source_hash_matches and colony_provenance['passed'] and all(checks.values()) and
                all(inactive_checks.values()) and bounded and topology_inherited)
            record = dict(recipe=kind, case=case, passed=bool(passed),
                source_control_sha256_matches=source_hash_matches, exact_saved_array_hashes=checks,
                exact_inactive_control_hashes=inactive_checks, colony_source_provenance=colony_provenance,
                control_vertices=len(out.xyz), physical_vertices=len(native.xyz), physical_triangles=len(native.faces),
                no_appended_surface_topology=topology_inherited, inactive_reference_topology=inactive_topology,
                maximum_displacement=maximum,
                maximum_displacement_bound=metadata['maximum_height'], bound_passed=bool(bounded))
            records.append(record)
            if progress:
                print('COMPACT_FINISH', kind, case, 'PASS' if passed else 'FAIL', checks, flush=True)
            del native, actual, delta, raw, fields, colonies
            gc.collect()
        del source_native, out, mesh, incoming_normals, reference, control_base, operation_base
        gc.collect()
    result = dict(status='PASS' if len(records) == 4 and all(record['passed'] for record in records) else 'FAIL',
        expected_recipes=list(KINDS), expected_cases=list(CASES), verified_copied_asset_hashes=len(copied), records=records,
        scope='All original control, operation and native arrays are regenerated exactly from packaged WALL G3 parents, two inactive refinements, actual native normals, saved atlas/colony frames and recipe JSON. One inherited connected surface; no appended component geometry.',
        excluded=['aesthetic success', 'self-intersection validity', 'fabrication', 'infinite Mandelbulb boundary'])
    if result['status'] != 'PASS':
        raise ValueError('Compact finish replay failed: '+json.dumps(result))
    return result


def package(sources, destination):
    sources = {kind: path.resolve() for kind, path in sources.items()}
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError('Existing finish review preserved: '+str(destination))
    if not destination.is_relative_to(REPO):
        raise ValueError('Finish review must remain inside this worktree.')
    atlas_files = [source/'atlas/power8.npz' for source in sources.values()]
    if len({sha(path) for path in atlas_files}) != 1:
        raise ValueError('Shared atlas files are not byte-identical; cannot omit a distinct atlas.')
    pairs = [(sources['BOLD_DETAIL']/'atlas'/name, Path('atlas')/name) for name in ('power8.npz', 'recipe.json')]
    for kind, source in sources.items():
        for case in CASES:
            for name in ('colonies.npz', 'generation.json'):
                pairs.append((source/kind/case/'G05'/name, Path(kind)/case/'G05'/name))
        for name in ('verification.json', 'source_reference_verification.json', 'SUMMARY.json'):
            pairs.append((source/name, Path('receipts')/kind/name))
        pairs.append((source/'bulb_detail.py', Path('source_snapshots')/kind/'bulb_detail.py'))
    missing = [str(path) for path, _ in pairs if not path.is_file()]
    if missing:
        raise FileNotFoundError('Finish recipe artifacts absent: '+json.dumps(missing))
    expected = expected_arrays(sources)
    destination.mkdir(parents=True)
    (destination/'.gitattributes').write_bytes(b'# Preserve copied recipe bytes and hashes.\n* -text\n')
    copied = []
    for source, relative in pairs:
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        digest = sha(source)
        if sha(target) != digest:
            raise ValueError('Copied finish asset differs: '+str(relative))
        copied.append(dict(path=relative.as_posix(), bytes=target.stat().st_size,
            sha256=digest, source=source.relative_to(REPO).as_posix()))
    receipt = dict(copied_assets=copied, copied_bytes=sum(r['bytes'] for r in copied),
        expected_original_arrays=expected, source_parents='../WALL/{SPAN,COUNTER}/G03',
        shared_atlas_sha256=sha(atlas_files[0]), no_detached_component_assets=True,
        omission='All four G5 control/native/operation arrays and matched inactive controls are exactly reproduced on demand, avoiding high-resolution duplicate arrays.',
        replay_command='python -B experiments/fold_visible_gate_20261012/compactpackage_finish.py --verify docs/fold_visible_gate_20261012/review/finish')
    (destination/'COPY_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf8')
    replay = verify(destination, expected, progress=True)
    (destination/'compact_finish_replay.json').write_text(json.dumps(replay, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(destination=str(destination), copied_bytes=receipt['copied_bytes'],
        copied_assets=len(copied), compact_finish_replay=replay['status']), indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bold-source', type=Path)
    parser.add_argument('--integrated-source', type=Path)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--write-proof', action='store_true', help='Save a missing successful replay receipt; never overwrite an existing receipt.')
    args = parser.parse_args()
    if args.verify:
        receipt = json.loads((args.verify/'COPY_RECEIPT.json').read_text(encoding='utf8'))
        replay = verify(args.verify, receipt['expected_original_arrays'], progress=True)
        if args.write_proof:
            proof = args.verify/'compact_finish_replay.json'
            with proof.open('x', encoding='utf8') as stream:
                stream.write(json.dumps(replay, indent=2)+'\n')
        print(json.dumps(replay, indent=2))
    else:
        if args.bold_source is None or args.integrated_source is None or args.destination is None:
            parser.error('--bold-source, --integrated-source and --destination required for creation')
        package(dict(BOLD_DETAIL=args.bold_source, INTEGRATED=args.integrated_source), args.destination)
