"""Verify actual edge-free pair image data separately from PNG time metadata.

The original strict probe and its outputs are preserved. This independent
verifier checks actual saved PNG pixels and compressed IDAT image payloads,
then binds them to the executed probe's geometry/normal/edge readbacks.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import struct

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('verified_fast_native_adapter', HERE/'fast_render.py')
fast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fast)
digest = fast.digest


def chunks(path):
    data = Path(path).read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Actual PNG signature required.')
    cursor, image, other, text = 8, [], [], []
    while cursor < len(data):
        length = struct.unpack('>I', data[cursor:cursor+4])[0]
        kind = data[cursor+4:cursor+8]
        payload = data[cursor+8:cursor+8+length]
        if kind == b'IDAT':
            image.append(payload)
        elif kind in (b'tEXt', b'zTXt', b'iTXt'):
            text.append(dict(type=kind.decode('ascii'), sha256=hashlib.sha256(payload).hexdigest(),
                             text=payload.decode('latin1')))
        else:
            other.append(data[cursor:cursor+12+length])
        cursor += 12+length
    if cursor != len(data) or not image:
        raise ValueError('Complete actual PNG chunks required.')
    return b''.join(image), b''.join(other), text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pair-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, output = args.pair_root.resolve(), args.output.resolve()
    snapshot = output.with_name(output.stem+'_SOURCE_verify_fast_render_pair.py')
    if output.exists() or snapshot.exists():
        raise FileExistsError('Earlier independent verification is preserved.')
    receipt_path = root/'EQUIVALENCE_RECEIPT.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf8'))
    if (receipt['executed_code_sha256']['probe'] != digest(HERE/'fast_render_probe.py') or
            receipt['executed_code_sha256']['fast_renderer'] != fast.code_hashes() or
            digest(receipt['fixture']['geometry']) != receipt['fixture']['geometry_sha256']):
        raise ValueError('Executed actual probe, native fixture or adapter source changed.')
    results = receipt['results']
    a, b = results['preserved_edges'], results['edge_free']
    paths = [root/name/'front.png' for name in ('preserved_edges', 'edge_free')]
    for path, record in zip(paths, (a, b)):
        if digest(path) != record['images'][0]['sha256']:
            raise ValueError('Actual rendered PNG changed.')
    payload_a, nontext_a, text_a = chunks(paths[0])
    payload_b, nontext_b, text_b = chunks(paths[1])
    with Image.open(paths[0]) as image:
        rgba_a = np.asarray(image.convert('RGBA'))
    with Image.open(paths[1]) as image:
        rgba_b = np.asarray(image.convert('RGBA'))
    checks = dict(geometry_and_flat_flags_bit_identical=a['geometry_signature'] == b['geometry_signature'],
        actual_face_normals_bit_identical=a['face_normals_sha256'] == b['face_normals_sha256'],
        Blender_decoded_pixel_readbacks_bit_identical=a['pixel_sha256'] == b['pixel_sha256'],
        independent_decoded_RGBA_bit_identical=np.array_equal(rgba_a, rgba_b),
        compressed_PNG_IDAT_payload_bit_identical=payload_a == payload_b,
        nontext_PNG_chunks_bit_identical=nontext_a == nontext_b,
        cameras_identical=a['actual_views'] == b['actual_views'],
        materials_lights_samples_conditions_identical=a['conditions'] == b['conditions'],
        original_edge_graph_present=a['Blender_edges_after_render'] > 0,
        fast_edge_graph_absent_after_Cycles=b['Blender_edges_after_render'] == 0)
    passed = all(checks.values())
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(__file__, snapshot)
    result = dict(kind='INDEPENDENT_ACTUAL_EDGE_FREE_PAIR_VERIFICATION', passed=passed, checks=checks,
        actual_probe_receipt=dict(path=str(receipt_path), sha256=digest(receipt_path)),
        PNG_files=[dict(path=str(path), sha256=digest(path)) for path in paths],
        IDAT_sha256=hashlib.sha256(payload_a).hexdigest(),
        PNG_file_bytes_identical=digest(paths[0]) == digest(paths[1]),
        metadata_only_differences=dict(preserved=text_a, edge_free=text_b),
        explanation='Blender writes per-render Date/RenderTime text metadata. Image pixels and '
            'compressed IDAT payloads are independently verified instead of requiring timestamp equality.',
        original_probe_and_outputs_modified=False, actual_design_rendered=False,
        executed_code_sha256=dict(verifier=digest(__file__), fast_renderer=fast.code_hashes()),
        source_snapshot=dict(path=str(snapshot), sha256=digest(snapshot)))
    with open(output, 'x', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(passed=passed, checks=checks, receipt=str(output))), flush=True)
    if not passed:
        raise ValueError('Independent actual edge-free equivalence checks failed.')


if __name__ == '__main__':
    main()
