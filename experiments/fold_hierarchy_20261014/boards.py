"""Verify two separate matched comparisons without mixing hierarchy and texture claims."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fold_hierarchy_board_renderer', HERE / 'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def verify(root):
    root = Path(root).resolve()
    binding, bare, current, candidates = render.saved_state(root)
    hashes = render.code_hashes()
    rendered = {}
    for state in ('HIERARCHY', 'FINISHED'):
        receipt_path = root / (state + '_FLAT/views/receipt.json')
        receipt = render.read_json(receipt_path)
        expected = candidates[state]['variant']
        reference = bare if state == 'HIERARCHY' else current
        if (receipt.get('state') != state + '_FLAT' or receipt.get('source_binding') != binding or
                receipt.get('candidate_binding') != candidates[state] or receipt.get('comparison_reference') != reference or
                receipt.get('saved_geometry') != expected or
                Path(receipt.get('geometry_path', '')).resolve() != Path(expected['geometry']).resolve() or
                receipt.get('code_sha256') != hashes or receipt.get('geometry_unchanged_in_renderer') is not True or
                receipt.get('geometry_processing') is not False or receipt.get('geometry_smoothing') is not False or
                receipt.get('shading') != 'ALL_FLAT_NATIVE_TRIANGLES' or receipt.get('smooth_shading') is not False or
                receipt.get('smooth_polygons') != 0 or receipt.get('normal_maps') is not False or
                receipt.get('modifiers') != [] or receipt.get('remesh') is not False or
                receipt.get('Boolean_fusion') is not False or receipt.get('ornaments_added') is not False or
                receipt.get('selective_mask_dependency') is not False or
                receipt.get('source_growth_generation') != 7 or receipt.get('new_source_growth_G8') is not False or
                receipt.get('generator_validation_evidence') != expected.get('validation')):
            raise ValueError('Actual candidate render provenance differs: ' + state)
        render.verify_snapshot(receipt['render_source_snapshot'])
        counts, readback = render.display_proof(receipt, expected)
        render.require_close(receipt['conditions'], binding['reference_conditions'])
        render.require_close(receipt['conditions'], render.base.expected_conditions())
        render.require_close(receipt['views'], binding['views'])
        if receipt['version'] != binding['reference_Blender_version']:
            raise ValueError('Source/candidate Blender versions differ.')
        images = render.image_records(receipt, receipt_path, binding, False)
        rendered[state] = dict(state=state + '_FLAT', saved_geometry=expected, images=images,
            geometry_counts=counts, display_readback=readback)
    return dict(passed=True, root=str(root), source_binding=binding, candidate_bindings=candidates,
        comparisons=dict(hierarchy=dict(states=[bare, rendered['HIERARCHY']],
            scope='Bare source versus hierarchy-only control update; no applied comb finish in either body.'),
            final=dict(states=[current, rendered['FINISHED']],
            scope='Accepted detailed design versus combined new hierarchy and larger surface finish; source and candidate topology differ.')),
        actual_views=binding['actual_reference_views'], conditions=binding['reference_conditions'],
        reused_bare_reference_images=4, reused_accepted_design_images=4,
        new_hierarchy_images=4, new_finished_images=4, source_images=16,
        new_variant_native_triangle_indices_identical=True,
        each_body_saved_coordinate_index_readback_verified=True, all_flat_flags_verified_per_body=True,
        geometry_unchanged_by_renderer=True, native_topology_equal_in_final_comparison=False,
        generator_validation_evidence={state: candidates[state]['variant'].get('validation') for state in candidates},
        generator_validation_scope='Carried from actual hash-bound generator receipt; not independently rerun by image verifier.',
        aesthetic_success_certified=False, global_collision_freedom_certified=False,
        crop=False, resize=False, modifiers=[], normal_maps=False, renderer_geometry_processing=False,
        selective_mask_dependency=False, source_growth_generation=7, new_source_growth_G8=False,
        render_code_sha256=hashes, boards_code_sha256=render.digest(__file__),
        scope='Two separate matched-camera/all-flat comparisons. Hierarchy and final design are not merged into a false single-variable comparison. Native saved-array readbacks and source PNG hashes are verified independently for each body; no geometry processing or synthesized image.')


def snapshot_source(root):
    source = Path(__file__).resolve()
    relative = Path('experiments') / HERE.name / source.name
    target = root / 'source_snapshot_boards' / relative
    checksum = render.digest(source)
    if target.exists():
        if render.digest(target) != checksum:
            raise ValueError('Earlier boards snapshot differs.')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    record = dict(source=str(source), relative_path=relative.as_posix(), snapshot=str(target), sha256=checksum)
    verify_snapshot(record)
    return record


def verify_snapshot(record):
    if (record.get('sha256') != render.digest(__file__) or
            any(render.digest(record[key]) != record['sha256'] for key in ('source', 'snapshot'))):
        raise ValueError('Boards source/snapshot changed.')


def compose(proof):
    root = Path(proof['root'])
    if (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Earlier verification preserved.')
    snapshot = snapshot_source(root)
    title = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 27)
    label = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 23)
    labels = dict(hierarchy=('Bare source | all-flat', 'Dominant parent folds | all-flat'),
                  final=('Current detailed design | all-flat', 'Hierarchy + larger comb | all-flat'))
    all_boards = []
    for comparison, evidence in proof['comparisons'].items():
        output = root / ('images_' + comparison)
        if output.exists():
            raise FileExistsError('Earlier comparison boards preserved.')
        output.mkdir()
        boards = []
        for view in proof['actual_views']:
            canvas = Image.new('RGB', (1800, 1020), 'white')
            draw = ImageDraw.Draw(canvas)
            draw.text((24, 12), 'SPAN | ' + view + ' | ' + comparison + ' comparison', font=title, fill='black')
            sources = []
            for column, state in enumerate(evidence['states']):
                draw.text((column * 900 + 24, 61), labels[comparison][column], font=label, fill='black')
                item = next(image for image in state['images'] if image['view'] == view)
                if render.digest(item['path']) != item['sha256']:
                    raise ValueError('Actual PNG changed during board composition.')
                with Image.open(item['path']) as image:
                    if image.size != (900, 900) or image.format != 'PNG':
                        raise ValueError('Actual 900-square PNG required.')
                    canvas.paste(image.convert('RGB'), (column * 900, 105))
                sources.append(dict(state=state['state'], **item))
            path = output / ('SPAN_' + view + '.png')
            canvas.save(path)
            boards.append(dict(comparison=comparison, view=view, output=str(path), sha256=render.digest(path), sources=sources))
        evidence['boards'] = boards
        all_boards.extend(boards)
        (output / 'SOURCE_LIST.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    verify_snapshot(snapshot)
    proof.update(boards=all_boards, comparison_boards=8, boards_source_snapshot=snapshot)
    (root / 'RENDER_VERIFICATION.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=render.DEFAULT_ROOT)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    proof = verify(args.root)
    if not args.verify_only:
        compose(proof)
    print('FOLD_HIERARCHY_MATCHED_RENDER_PASS: 8 preserved references + 8 actual new PNGs; two separate comparisons', flush=True)


if __name__ == '__main__':
    main()
