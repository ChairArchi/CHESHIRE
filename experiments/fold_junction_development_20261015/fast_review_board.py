"""Native-pixel 900px NESTED02 / candidate board for verified fast receipts.

Default output is two unscaled 900px close-view panels. The unchanged review
board implementation runs through isolated globals with fast receipt checks.
Existing scripts, module globals, source PNGs and outputs remain unchanged.
"""
from pathlib import Path
import argparse
import importlib.util
import shutil
import sys
import types

HERE = Path(__file__).resolve().parent
PRESERVED = HERE / 'review_board.py'
PRESERVED_SHA = '460a8c76543575e62acc6819259c33a2c7ba8d3b8afb6f0484d3fa41f74c2067'
PACKAGE = HERE / 'fast_package.py'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


package = module('fast_board_verified_export_adapter', PACKAGE)
preserved = module('fast_board_frozen_pixel_workflow', PRESERVED)
render, digest = package.render, package.digest


def execution_hashes():
    if digest(PRESERVED) != PRESERVED_SHA:
        raise ValueError('Frozen native-pixel board implementation changed.')
    return dict(board_adapter=digest(__file__), preserved_board_sha256=PRESERVED_SHA,
                verified_fast_package_dependencies=package.execution_hashes())


def isolated_board_main():
    namespace = dict(preserved.__dict__)
    facade = types.SimpleNamespace(**{key:value for key,value in render.__dict__.items()
                                      if not key.startswith('__')})
    facade.code_hashes = execution_hashes
    namespace.update(__file__=str(Path(__file__).resolve()), PACKAGE=PACKAGE, render=facade,
                     package=types.SimpleNamespace(checked_render=package.checked_render))
    return types.FunctionType(preserved.main.__code__, namespace, 'verified_fast_board_main')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--variant', default='RECURSIVE')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--views', nargs='+', choices=render.VIEWS, default=['close_oblique'])
    parser.add_argument('--caption', default='')
    args = parser.parse_args()
    output = args.output.resolve()
    hashes = execution_hashes()
    command = [str(Path(__file__).resolve()), '--root', str(args.root.resolve()),
        '--variant', args.variant, '--output', str(output), '--views', *args.views]
    if args.caption:
        command.extend(['--caption', args.caption])
    original_argv = sys.argv
    try:
        sys.argv = command
        isolated_board_main()()
    finally:
        sys.argv = original_argv
    dependencies = {}
    for source, label in ((PRESERVED, 'preserved_review_board'),
                          (PACKAGE, 'fast_package'), (package.FAST_PATH, 'fast_render')):
        target = output.with_name(output.stem + '_SOURCE_' + label + '.py')
        if target.exists():
            raise FileExistsError('Earlier board dependency snapshot is preserved.')
        shutil.copyfile(source, target)
        if digest(target) != digest(source):
            raise ValueError('Board dependency snapshot differs.')
        dependencies[label] = dict(source=str(source), snapshot=str(target), sha256=digest(source))
    if execution_hashes() != hashes:
        raise ValueError('Executed board dependencies changed.')
    receipt = output.with_suffix('.json')
    record = dict(kind='VERIFIED_FAST_RENDER_NATIVE_PIXEL_BOARD_ADAPTER',
        board=dict(path=str(output), sha256=digest(output)),
        board_receipt=dict(path=str(receipt), sha256=digest(receipt)),
        actual_reference='NESTED02 preserved actual PNG, as bound by fast render source_binding.',
        actual_candidate='Selected verified actual fast-rendered native mesh PNG.',
        preserved_dependency_snapshots=dependencies, executed_code_sha256=hashes,
        isolated_function_globals=True, old_module_globals_modified=False,
        source_PNGs_modified=False, resizing=False, cropping=False, retouching=False,
        complete_saved_RGB_pixel_roundtrip='Verified by the unchanged preserved board workflow.')
    adapter_receipt = output.with_name(output.stem + '_ADAPTER.json')
    package.preserved.write_json(adapter_receipt, record)
    print('VERIFIED_FAST_PIXEL_BOARD_DONE ' + str(output), flush=True)


if __name__ == '__main__':
    main()
