"""One read-only native strip measurement on the longest saved phase curve."""
from pathlib import Path
import argparse
import hashlib
import json
import time

import numpy as np

from native_strip_surface import NativeSurface
import native_strip_surface


REPO = Path(__file__).resolve().parents[2]
GRAPH = REPO/'docs/hansmeyer_reconstruction_20261015/phase_curve_probe01/PHASE_CURVE_GRAPH.json'
OUTPUT = REPO/'docs/hansmeyer_reconstruction_20261015/native_strip_probe01'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8*1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('One new immutable measurement directory required.')
    started = time.perf_counter()
    receipt = json.loads(GRAPH.read_text(encoding='utf8'))
    saved_graph = Path(receipt['evidence']['path'])
    if sha(saved_graph) != receipt['evidence']['sha256']:
        raise ValueError('Saved native curve graph changed.')
    with np.load(saved_graph, allow_pickle=False) as saved:
        graph = {key:saved[key] for key in saved.files}
    control = Path(receipt['source_control'])
    evidence = control.parent/'evidence.npz'
    owner = control.parents[1]/'G03_SIDEWALL/evidence.npz'
    paths = (GRAPH, saved_graph, control, evidence, owner,
             Path(native_strip_surface.__file__).resolve(), Path(__file__).resolve())
    hashes = {str(path):sha(path) for path in paths}
    for path in (control, evidence, owner):
        if hashes[str(path)] != receipt['sources'][str(path)]:
            raise ValueError('Immutable control source binding differs.')
    with np.load(control, allow_pickle=False) as saved:
        xyz, quads, chart = saved['xyz'], saved['faces'], saved['chart']
    with np.load(evidence, allow_pickle=False) as saved:
        phase = saved['directional_phase']
    with np.load(owner, allow_pickle=False) as saved:
        mask = np.repeat(saved['face_event_ids'] == 0, 64)
    surface = NativeSurface(xyz, quads, phase, mask, chart)
    built = time.perf_counter()
    candidates = [component for component in receipt['components']
                  if component['status'] in ('CLOSED_REGULAR_LOOP', 'REGULAR_OPEN_CURVE')]
    chosen = max(candidates, key=lambda item:(item['physical_arc_length'], -item['component']))
    nodes = np.flatnonzero(graph['node_component'] == chosen['component'])
    order = nodes[np.argsort(graph['node_arc_s'][nodes])]
    periodic = chosen['status'] == 'CLOSED_REGULAR_LOOP'
    curve = surface.resample_curve(graph, order, 33, periodic=periodic)
    height = float(np.ptp(xyz[:, 2]))
    strip = surface.measure_strip(curve['triangle_ids'], curve['barycentric'],
        samples=33, max_half_width=.03*height, curve_s=curve['s'],
        periodic=periodic, tangents=curve['tangent'])
    unique, counts = np.unique(strip['status'], return_counts=True)
    summary = dict(stations=33, cross_samples_per_station=33,
        source_covered_rows=int(np.count_nonzero(strip['valid'].all(axis=1))),
        confirmed_actual_positive_crest_rows=int(strip['confirmed'].sum()),
        status_counts=dict(zip(unique.tolist(), counts.tolist())),
        confirmed_width_quantiles=np.quantile(strip['width'][strip['confirmed']], [0., .5, 1.]).tolist() if strip['confirmed'].any() else None,
        confirmed_prominence_quantiles=np.quantile(strip['prominence'][strip['confirmed']], [0., .5, 1.]).tolist() if strip['confirmed'].any() else None,
        surface_build_seconds=built-started, elapsed_seconds=time.perf_counter()-started)
    for path in paths:
        if sha(path) != hashes[str(path)]:
            raise ValueError('Read-only source or executed helper changed.')
    args.output.mkdir(parents=True)
    payload = args.output/'NATIVE_STRIP.npz'
    arrays = {key:value for key,value in strip.items() if isinstance(value, np.ndarray)}
    arrays.update(curve_triangle_ids=curve['triangle_ids'], curve_barycentric=curve['barycentric'],
                  original_contour_node_order=order)
    np.savez_compressed(payload, **arrays)
    report = dict(kind='ONE_ACTUAL_NATIVE_STRIP_MEASUREMENT', date='2026-10-15',
        sources_and_sha256=hashes, source_hashes_verified_after_read=True,
        component=chosen, selection='Longest actual saved regular SOURCE phase component by physical arc, no camera selection.',
        curve_samples='33 uniform physical arc stations on saved native graph; tangent from the exact native contour segment, not coarse sample chords.',
        search='1.35*pi/actual intrinsic phase-gradient norm; one physical safety ceiling .03*incoming full height. No parameter sweep.',
        geometry_generated=False, source_geometry_modified=False, render_generated=False,
        adjacency=surface.adjacency_metadata, measurement=strip['metadata'], summary=summary,
        evidence=dict(path=str(payload.resolve()), sha256=sha(payload)))
    (args.output/'NATIVE_STRIP.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
