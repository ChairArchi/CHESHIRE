"""Small review package: actual render boards and vertex/face mirror checks.

No geometry changes, retouching, smoothing, or fabrication certification.
Exact intersection tests use the existing project checker separately.
"""
from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from review_boards import board, ROOT


def mirror_check(folder):
    mesh = trimesh.load(folder / 'gate.ply', process=False, force='mesh')
    points = np.asarray(mesh.vertices)
    reflected = points * [-1, 1, 1]
    distance, ids = cKDTree(points).query(reflected)
    faces = {tuple(sorted(f)) for f in mesh.faces.tolist()}
    face_match = all(tuple(sorted(ids[f])) in faces for f in mesh.faces)
    result = dict(file='gate.ply', tolerance=1e-10,
                  max_vertex_mirror_error=float(distance.max()),
                  mirror_face_connectivity=bool(face_match),
                  passed=bool(distance.max() <= 1e-10 and face_match))
    (folder / 'symmetry.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print(folder.relative_to(ROOT), result)


def main():
    review = ROOT / 'review'
    selected = ['directional/D01_STAGGERED/CC2',
                'directional/D02_INTERLEAVED/CC2',
                'variations/V24_TURN/G04']
    factorial = ['CYLINDER_NO_FIELD', 'CYLINDER_FIELD',
                 'DIRECTIONAL_NO_FIELD', 'DIRECTIONAL_FIELD']
    selected += ['input_field/' + name + '/G02_CC' for name in factorial]
    for path in selected:
        mirror_check(ROOT / path)
    cases = [('Field / V24 G4', 'variations/V24_TURN/G04'),
             ('Uniform pleats / F04 CC', 'folded/F04_FAN/G00_CC'),
             ('Offset folds / D01 CC2', 'directional/D01_STAGGERED/CC2'),
             ('Stronger return / D02 CC2', 'directional/D02_INTERLEAVED/CC2')]
    for view in ('front', 'oblique', 'side'):
        board([(label, ROOT / path / 'preview' / (view + '.png'))
               for label, path in cases], review / ('fold_logic_' + view + '.png'),
              cols=4, cell=(320, 610),
              title=view + ' / actual meshes / same camera and material')
    for name in ('D01_STAGGERED', 'D02_INTERLEAVED'):
        entries = [(stage + ' / ' + view,
                    ROOT / 'directional' / name / stage / 'preview' / (view + '.png'))
                   for view in ('front', 'oblique', 'side')
                   for stage in ('CAGE', 'CC1', 'CC2')]
        board(entries, review / (name + '_stages.png'), cols=3, cell=(320, 590),
              title=name + ' / explicit cage -> CC1 -> CC2 / NO fractal growth')
    for view in ('front', 'oblique', 'side'):
        entries = [(name.replace('_', ' '), ROOT / 'input_field' / name / 'G02_CC' /
                    'preview' / (view + '.png')) for name in factorial]
        board(entries, review / ('input_field_' + view + '.png'), cols=4, cell=(320, 610),
              title='Same topology / 2 refinements + 1 CC / ' + view)
    entries = [(name + ' / ' + stage, ROOT / 'input_field' / name / stage /
                'preview' / 'oblique.png')
               for name in ('CYLINDER_FIELD', 'DIRECTIONAL_FIELD')
               for stage in ('G01', 'G02', 'G02_CC')]
    board(entries, review / 'input_field_stages.png', cols=3, cell=(320, 590),
          title='Actual growth stages / G1 -> G2 -> presentation CC / oblique')


if __name__ == '__main__':
    main()
