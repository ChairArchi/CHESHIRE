"""Exact disk replacement on an existing native triangle surface.

The incoming interior can have a new topology and large normal rotations.
Only a connected genus-zero disk and an exact directed outer seam are required.
Geometry intersection and donor backskin checks belong to the graft producer.
"""
from pathlib import Path
import json
import numpy as np
from .ornament_assembly import validate_patch, record


def validate_triangle_replacement(xyz, triangles, patch):
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ValueError('The preserved carrier must use its actual native triangles.')
    audit = validate_patch(xyz, triangles, patch, position_tolerance=0.)
    audit['removed_native_triangles'] = audit.pop('removed_quads')
    if audit['added_handles'] != 0:
        raise ValueError('A closed-backed replacement must introduce no through handles.')
    return audit


def assemble_triangle_replacements(base_xyz, base_triangles, patches, folder,
                                   *, chunk=65536, progress=print):
    """Keep every exterior native triangle exact, stitch disks, compact unused XYZ.

    Patch keys are vertices, triangles, host_vertex_ids (-1 for new points),
    removed_host_face_ids (native triangle IDs), and optional triangle_classes
    or tri_class_ids from the full-XYZ graft kernel.
    Original interior vertices may disappear: this is a structural replacement,
    not a displacement of every old material control.
    """
    if not patches:
        raise ValueError('At least one actual replacement is required.')
    root = Path(folder)
    root.mkdir(parents=True, exist_ok=False)

    def disk(name, shape, dtype, fill=None):
        a = np.lib.format.open_memmap(root/(name+'.npy'), mode='w+', shape=shape, dtype=dtype)
        if fill is not None:
            a.fill(fill)
        return a

    nv, nf = len(base_xyz), len(base_triangles)
    keep = np.ones(nf, bool)
    audits = []
    extra = total_patch_triangles = 0
    for i, patch in enumerate(patches):
        audit = validate_triangle_replacement(base_xyz, base_triangles, patch)
        removed = np.asarray(patch['removed_host_face_ids'], np.int64)
        if not np.all(keep[removed]):
            raise ValueError('Structural replacement disks overlap.')
        keep[removed] = False
        audits.append(audit)
        extra += audit['new_vertices']
        total_patch_triangles += len(patch['triangles'])
        progress('STRUCTURAL_DISK_VALIDATED', i, audit['removed_native_triangles'],
                 audit['new_triangles'], flush=True)

    surviving = int(keep.sum())
    nout = surviving + total_patch_triangles
    temporary = disk('UNCOMPACTED_XYZ', (nv+extra, 3), np.float64)
    triangles = disk('TRIANGLES', (nout, 3), np.int64)
    classes = disk('TRIANGLE_CLASSES', (nout,), np.int16, fill=0)
    sources = disk('SOURCE_TRIANGLE_IDS', (nout,), np.int64, fill=-1)
    for a in range(0, nv, chunk):
        b = min(a+chunk, nv)
        temporary[a:b] = base_xyz[a:b]
    pos = 0
    for a in range(0, nf, chunk):
        ids = np.arange(a, min(a+chunk, nf), dtype=np.int64)[keep[a:a+chunk]]
        n = len(ids)
        triangles[pos:pos+n] = base_triangles[ids]
        sources[pos:pos+n] = ids
        pos += n
    vpos = nv
    ranges = []
    for patch in patches:
        binding = np.asarray(patch['host_vertex_ids'], np.int64)
        fresh = binding < 0
        n = int(fresh.sum())
        mapping = binding.copy()
        mapping[fresh] = np.arange(vpos, vpos+n, dtype=np.int64)
        temporary[vpos:vpos+n] = np.asarray(patch['vertices'])[fresh]
        local = np.asarray(patch['triangles'], np.int64)
        if 'triangle_classes' in patch and 'tri_class_ids' in patch:
            if not np.array_equal(patch['triangle_classes'], patch['tri_class_ids']):
                raise ValueError('Replacement triangle classification aliases disagree.')
        tags = np.asarray(patch.get('triangle_classes',
                         patch.get('tri_class_ids', np.ones(len(local), np.int16))))
        if tags.shape != (len(local),):
            raise ValueError('Replacement triangle tag count differs.')
        triangles[pos:pos+len(local)] = mapping[local]
        classes[pos:pos+len(local)] = tags
        ranges.append([pos, pos+len(local)])
        pos += len(local)
        vpos += n
    if pos != nout or vpos != len(temporary):
        raise ValueError('Structural allocation count differs.')
    used = disk('USED_UNCOMPACTED_VERTICES', (len(temporary),), np.bool_, fill=False)
    for a in range(0, nout, chunk):
        used[triangles[a:a+chunk].ravel()] = True
    mapping = disk('OLD_TO_NEW', (len(temporary),), np.int64)
    np.cumsum(used, dtype=np.int64, out=mapping)
    final_nv = int(mapping[-1])
    mapping -= 1
    mapping[~used] = -1
    xyz = disk('XYZ', (final_nv, 3), np.float64)
    pos = 0
    for a in range(0, len(temporary), chunk):
        values = temporary[a:a+chunk][used[a:a+chunk]]
        xyz[pos:pos+len(values)] = values
        pos += len(values)
    for a in range(0, nout, chunk):
        triangles[a:a+chunk] = mapping[triangles[a:a+chunk]]
    quads = disk('QUADS', (0, 4), np.int64)
    quad_classes = disk('QUAD_CLASSES', (0,), np.int16)
    for array in (temporary, triangles, classes, sources, used, mapping, xyz, quads, quad_classes):
        array.flush()
    receipt = dict(kind='NATIVE_TRIANGLE_STRUCTURAL_DISK_REPLACEMENT',
        counts=dict(vertices=final_nv, quads=0, triangles=nout,
            base_vertices=nv, base_triangles=nf, removed_native_triangles=nf-surviving,
            new_patch_triangles=total_patch_triangles,
            discarded_unreferenced_vertices=int((~used).sum())),
        patch_audits=audits, patch_triangle_output_ranges=ranges,
        added_handles=0, native_exterior_triangles_preserved_exactly=True,
        surviving_original_vertex_coordinates_bit_exact=True,
        original_interior_material_vertices_may_be_removed=True,
        original_microfacet_normal_hemisphere_constraint=False,
        no_implicit_quad_diagonal_retriangulation=True,
        connection_proof='An independently closed connected native carrier has disjoint disks replaced with connected genus-zero one-boundary surfaces sharing the exact directed host seams.',
        global_self_intersection_certified=False,
        arrays={key:record(root/(key+'.npy')) for key in
                ('XYZ','QUADS','TRIANGLES','QUAD_CLASSES','TRIANGLE_CLASSES','SOURCE_TRIANGLE_IDS','OLD_TO_NEW')})
    (root/'ASSEMBLY_RECEIPT.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    return receipt
