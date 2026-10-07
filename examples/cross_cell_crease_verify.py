"""Actual installed-source identity and exact closed-fixture parity gate."""
from copy import deepcopy
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'examples'))
from compas.datastructures import Mesh
from compas.geometry import Box
import compas
from cheshire.artifact_root import ArtifactRoot
from cheshire.creases import crease_subdivide_once, make_network
from cross_cell_crease_study import raw_mesh, mesh_to_data, file_hash, read, write, BASELINE


def verify(root):
    assert compas.__version__ == '2.15.1'
    cases = [('cube', Mesh.from_shape(Box(2, 2, 2))), ('column', Mesh.from_shape(Box(1, 1, 6))),
        ('U_gate', raw_mesh(read(root.resolve('inputs/C0.json'))))]
    checks = []
    for name, source in cases:
        original = deepcopy(source.__data__)
        vertex = min(source.vertices()); neighbors = source.vertex_neighbors(vertex)
        edges = [(vertex, v) for v in neighbors]
        networks = (make_network(source, 'parity', edges, 2, {'rule': 'first-original-corner-star'}),)
        actual = source; reference = source.copy()
        for edge in edges: reference.edge_attribute(edge, 'crease', 2)
        for i in range(3):
            expected = reference.subdivided(scheme='catmullclark', k=1)
            step = crease_subdivide_once(actual, networks, current_generation=i)
            assert mesh_to_data(expected) == mesh_to_data(step.mesh)
            assert all((expected.edge_attribute(e.vertices, 'crease') or 0) == e.sharpness for n in step.networks for e in n.edges)
            checks.append(dict(fixture=name, generation=i+1, exact_coordinates=True, exact_oriented_topology=True,
                exact_decay_and_descendants=True, faces=step.mesh.number_of_faces()))
            actual = step.mesh; networks = step.networks; reference = expected
        assert source.__data__ == original
    report = dict(status='PASS', baseline=BASELINE, COMPAS=compas.__version__,
        installed_source='compas/datastructures/mesh/subdivision.py',
        installed_source_sha256=file_hash(ROOT/'.venv/Lib/site-packages/compas/datastructures/mesh/subdivision.py'),
        tests=checks, ordering_differences=[], source_immutable=True,
        fractional_contract='Modern finite Uniform transitions, independently tested; not original variable Chaikin appendix.')
    write(root.resolve('study/verification.json'), report)
    print('PASS:9 exact COMPAS closed-fixture generation comparisons; installed source fingerprint recorded.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('--output-root', type=Path, required=True)
    verify(ArtifactRoot(parser.parse_args().output_root))
