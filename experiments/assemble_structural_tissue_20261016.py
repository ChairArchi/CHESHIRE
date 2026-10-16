"""Whole-context assembly using the explicitly liked hybrid native geometry."""
from pathlib import Path
import argparse, json, shutil, sys, time
import numpy as np

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'src'))
from cheshire.structural_assembly import assemble_triangle_replacements
from cheshire.ornament_assembly import file_hash, record

BASE = Path(r'E:\CHESHIRE_DATA\experiments\generation_mirror_hybrid_20261016')
HANDOFF = Path(r'E:\CHESHIRE_DATA\handoffs\CHESHIRE_20261016_GENERATION_MIRROR_HYBRID.json')
SOURCE = {
    'XYZ':dict(path=str(BASE/'working_arrays/NATIVE_XYZ.npy'),sha256='60604f3bb2119b77ecb4b5f7d317c61bce3a7cf593032aa28127bc6d3df30ab4'),
    'TRIANGLES':dict(path=str(BASE/'working_arrays/NATIVE_FACES.npy'),sha256='86b6a4e7ac66d9d160a7ee2ac5f26495b5824189cfbfff1a7fec49f77fbf8049')}


def main(index_path, output):
    started = time.perf_counter()
    index = json.loads(index_path.read_text(encoding='utf-8-sig'))
    loaded = {}
    for name, source in SOURCE.items():
        if file_hash(source['path']) != source['sha256']:
            raise ValueError('The chosen liked hybrid source changed: '+name)
        loaded[name] = np.load(source['path'],mmap_mode='r')
    patches = []
    for row in index['patches']:
        path = Path(row['path'])
        if file_hash(path) != row['sha256']:
            raise ValueError('Reviewed structural patch changed.')
        with np.load(path,allow_pickle=False) as archive:
            patches.append({key:archive[key] for key in archive.files})
    assembly = assemble_triangle_replacements(loaded['XYZ'],loaded['TRIANGLES'],patches,output)
    snapshots = output/'source_snapshot'
    snapshots.mkdir()
    source_snapshots = {}
    for path in (Path(__file__).resolve(),REPO/'src/cheshire/structural_assembly.py',
                 REPO/'src/cheshire/ornament_assembly.py'):
        target = snapshots/path.name
        shutil.copyfile(path,target)
        source_snapshots[str(path)] = dict(source=str(path),snapshot=str(target),sha256=file_hash(target))
    result = dict(kind='LIKED_HYBRID_NATIVE_FULL_XYZ_STRUCTURAL_TISSUE_REBUILD',
        prototype=True,user_adopted=False,baseline_kind='GENERATION_MIRROR_HYBRID_G7_NATIVE_FANS',
        baseline_handoff=record(HANDOFF),baseline_arrays=SOURCE,
        previous_global_hybrid_geometry_is_actual_base=True,
        old22_or_wholeCC1_substitution=False,
        patch_index=record(index_path),assembly=assembly,
        source_snapshots=source_snapshots,
        formulation='Exact liked hybrid exterior. Selected generation-lineage macro disks are replaced with full XYZ closed-backed folded donor surfaces plus new collars. No topmost-ray or height-only transfer of the donor.',
        actual_full_XYZ_donor_surface_transferred=True,
        donor_overhangs_and_layered_lips_retained=True,
        source_119_handle_topology_not_copied=True,
        continuous_closed_backskin=True,actual_added_handles=0,
        global_CC_smoothing_added=False,
        original_microfacet_normal_constraint=False,
        all_old_microdetail_inside_rebuilt_disks_not_preserved=True,
        earlier_generation_lineage_used_for_region_selection=True,
        entire_G5_G6_generation_operator_replayed=False,
        color=dict(quad_classes=assembly['arrays']['QUAD_CLASSES'],
                   triangle_classes=assembly['arrays']['TRIANGLE_CLASSES'],
                   palette=['unchanged liked hybrid','full XYZ folded donor','rebuilt flow collar','new collar ribs']),
        global_self_intersection_certified=False,manufacturing_strength_certified=False,
        elapsed_seconds=time.perf_counter()-started)
    (output/'SYNTHESIS_RECEIPT.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('LIKED_HYBRID_STRUCTURAL_WHOLE_READY',assembly['counts'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--patch-index',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    main(args.patch_index,args.out)
