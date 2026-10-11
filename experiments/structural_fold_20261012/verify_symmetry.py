"""Read actual solid symmetry using two directed Boolean differences per axis.

Fixed acceptance: sum of difference volumes <= 1e-12 + 1e-10 * reference
volume. This is a solid-volume comparison, not vertex/triangle-set matching,
an exhaustive self-intersection test, or a thickness/fabrication check.
"""
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('structural_symmetry_source', HERE/'study.py')
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)
ABSOLUTE_TOLERANCE = 1e-12
RELATIVE_TOLERANCE = 1e-10


def residual_info(residual):
    valid = residual.status() == study.md.Error.NoError
    return dict(status=str(residual.status()), valid=valid,
        empty=bool(residual.is_empty()),
        components=len(residual.decompose()) if valid else None,
        volume=float(residual.volume()) if valid else None)


def verify(folder):
    folder = Path(folder).resolve()
    destination = folder/'symmetry_validation.json'
    if destination.exists():
        raise FileExistsError('Existing validation preserved: '+str(destination))
    source = study.solid(study.load(folder))
    source_volume = float(source.volume())
    rows = {}
    for axis, normal in (('X', (1., 0., 0.)), ('Y', (0., 1., 0.))):
        mirror = source.mirror(normal)
        forward = residual_info(source-mirror)
        reverse = residual_info(mirror-source)
        valid = forward['valid'] and reverse['valid']
        reference_volume = max(abs(source_volume), abs(float(mirror.volume())))
        absolute = abs(forward['volume'])+abs(reverse['volume']) if valid else None
        tolerance = ABSOLUTE_TOLERANCE+RELATIVE_TOLERANCE*reference_volume
        passed = valid and reference_volume > 0 and absolute <= tolerance
        rows[axis] = dict(reflection_plane=axis+'=0', source_minus_mirror=forward,
            mirror_minus_source=reverse, symmetric_difference_volume=absolute,
            relative_symmetric_difference_volume=absolute/reference_volume if valid and reference_volume > 0 else None,
            reference_volume=reference_volume, allowed_absolute_volume=tolerance,
            verdict='PASS' if passed else 'FAIL')
    record = dict(folder=str(folder), method='Sum of volumes of A minus reflected A and reflected A minus A; all residual components retained',
        source_status=str(source.status()), source_volume=source_volume,
        absolute_tolerance=ABSOLUTE_TOLERANCE, relative_tolerance=RELATIVE_TOLERANCE,
        threshold_rule='difference_volume <= absolute_tolerance + relative_tolerance * max(abs(source_volume), abs(mirror_volume))',
        axes=rows, verdict='PASS' if all(r['verdict'] == 'PASS' for r in rows.values()) else 'FAIL',
        vertex_or_triangle_set_matching_used=False,
        scope='Volume symmetry within the declared tolerance; does not certify identical triangulations or bound maximum surface distance.',
        self_intersection='NOT_CHECKED', thickness_structure_fabrication='NOT_CHECKED')
    destination.write_text(json.dumps(record, indent=2), encoding='utf8')
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, help='Existing result folder containing geometry.npz')
    verify(parser.parse_args().folder)
