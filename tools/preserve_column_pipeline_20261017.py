"""Preserve the retained 2026-10-16 G7 pipeline's small evidence in this repo.

Read-only E inputs; C repository writes only. No model rebuild, large-model
rehash, recipe alteration, or git operation is performed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

REPO = Path(__file__).resolve().parents[1]
EXPERIMENT = Path('E:/CHESHIRE_DATA/experiments/generation_mirror_hybrid_20261016')
EXPORT = Path('E:/CHESHIRE_DATA/exports/20261016/COLUMN_GENERATION_MIRROR_HYBRID')
EARLY = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay')
NESTED = Path('E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial02')
MODEL_SHA = 'ed40809e09ac8afd0a4be6369ada572add7b2dd24fb71aaad7b63be7481363ef'
BUNDLE_SHA = '19fd39c96ae42c6a2b19fa4591d13ec5693083406b1c99adeef42d6c3767533b'
SCHEMA = 'CHESHIRE_RETAINED_ORIGINAL_G7_PIPELINE_CHECKPOINT_V1'
STAGES = ('G00_INPUT', 'G01_ANCESTRY', 'G02_OVERLAP', 'G03_WALL',
          'G03_ROOT', 'G03_SIDEWALL', 'G04_NEUTRAL', 'G05_DIRECTIONAL',
          'G06_DEPTH08', 'G06_MIDDLE', 'G07_SURFACE')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def preserve(output):
    output = Path(output).resolve()
    if not output.is_relative_to(REPO/'docs') or output.drive.upper() != REPO.drive.upper():
        raise ValueError('Checkpoint writes must stay inside this C repository docs tree.')
    manifest_path = output/'frozen_baseline_manifest.json'
    if manifest_path.exists():
        raise FileExistsError('Preserve the completed checkpoint: '+str(manifest_path))
    model = read(EXPORT/'MODEL_RECEIPT.json')
    readback = read(EXPORT/'MODEL_READBACK.json')
    if model['model_sha256'] != MODEL_SHA or readback['model_sha256'] != MODEL_SHA:
        raise ValueError('Retained model receipt differs from the selected baseline.')
    for key in ('vertices', 'triangles', 'bytes'):
        if model[key] != readback[key]:
            raise ValueError('Model receipt/readback disagree: '+key)
    if not all(readback[k] for k in ('complete_vertex_readback_exact',
                                    'complete_triangle_readback_exact', 'binary_length_exact')):
        raise ValueError('Existing complete native readback did not pass.')
    model_path = Path(model['model'])
    if not model_path.is_file() or model_path.stat().st_size != model['bytes']:
        raise ValueError('External retained model is missing or has a different size.')
    copied = []

    def copy(source, relative, expected=None):
        source = Path(source).resolve()
        observed = sha(source)
        if expected is not None and observed != expected:
            raise ValueError('Recorded small dependency changed: '+str(source))
        dest = output/relative
        if not dest.resolve().is_relative_to(output):
            raise ValueError('Invalid checkpoint member path.')
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            if sha(dest) != observed:
                raise FileExistsError('Different checkpoint artifact exists: '+str(dest))
        else:
            shutil.copyfile(source, dest)
        if sha(dest) != observed:
            raise ValueError('Checkpoint copy SHA differs: '+str(dest))
        copied.append(dict(path=relative, source=str(source), sha256=observed,
                           bytes=dest.stat().st_size, copy_sha_verified=True))
        return dest

    archive_name = 'CHESHIRE_GENERATION_MIRROR_PIPELINE_PROTOTYPE.zip'
    archive = copy(EXPERIMENT/archive_name, 'algorithm/'+archive_name, BUNDLE_SHA)
    bundle_manifest = read(EXPERIMENT/'ALGORITHM_BUNDLE_MANIFEST.json')
    if bundle_manifest['bundle_sha256'] != BUNDLE_SHA:
        raise ValueError('Original algorithm bundle manifest changed.')
    copy(EXPERIMENT/'ALGORITHM_BUNDLE_MANIFEST.json', 'algorithm/ALGORITHM_BUNDLE_MANIFEST.json')
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or z.testzip() is not None:
            raise ValueError('Preserved algorithm ZIP failed duplicate/CRC checks.')
        for name, expected in bundle_manifest['files'].items():
            if hashlib.sha256(z.read(name)).hexdigest() != expected:
                raise ValueError('Algorithm archive member SHA differs: '+name)
    for name in ('MODEL_RECEIPT.json', 'MODEL_READBACK.json'):
        copy(EXPORT/name, 'provenance/export/'+name)
    relatives = (
        'RECEIPT.json', 'FORMATION.json', 'CLASSIFICATION.json',
        'INTERLEAVED_COARSE_RECEIPT.json', 'GEOMETRY_QUALITY.json',
        'PRESERVATION_AUDIT.json', 'COARSE_STAGE_RECOVERY.json', 'FINAL_RECOVERY.json',
        'INDEPENDENT_APPLICATION_AUDIT.json', 'INDEPENDENT_CLASSIFICATION_AUDIT.json',
        'INDEPENDENT_PAPER_COMPONENT_AUDIT.json', 'INDEPENDENT_VERIFICATION_PROTOCOL.json',
        'history_classification/CLASSIFICATION_RECEIPT.json',
        'history_classification/TISSUE_HOSTS.json',
        'component/PAPER_COMPONENT_RECEIPT.json', 'component/SEED_TO_SOLID_VALIDATION.json',
        'paper_tissue/ACTUAL_TISSUE_RECEIPT.json',
        'paper_tissue/ACTUAL_TISSUE_GENERATED_CELL.json',
        'paper_tissue/paper_derived_component.json',
        'paper_tissue_native/RAW_TISSUE_RECEIPT.json',
        'MACRO_FLOW_QA/MACRO_FLOW_QA.json')
    for relative in relatives:
        copy(EXPERIMENT/relative, 'provenance/hybrid/'+relative)
    copy(NESTED/'RECEIPT.json', 'provenance/NESTED_RECEIPT.json')
    copy(EARLY/'RECIPE.json', 'provenance/original_process/RECIPE.json')
    front = next(x for x in model['images'] if x.get('style') == 'gray' and x.get('view') == 'front')
    copy(EXPORT/front['relative_copy'], 'preview/original_front.png', front['sha256'])

    ordered, code = [], {}
    for stage in STAGES:
        folder = EARLY/'states'/stage
        info = read(folder/'generation.json')
        copy(folder/'generation.json', 'provenance/original_process/'+stage+'/generation.json')
        ordered.append(dict(stage=stage, actual_generation=info['subdivision_generation'],
            control_vertices=info['control_vertices'], control_quads=info['control_quads'],
            external_control=str(folder/'control_quad.npz'),
            recorded_control_sha256=info['control_file_sha256'],
            receipt='provenance/original_process/'+stage+'/generation.json'))
        for relative, expected in info.get('geometry_code_sha256', {}).items():
            path = REPO/relative
            observed = sha(path)
            if observed != expected:
                raise ValueError('Stable original operator source changed: '+relative)
            code[str(path)] = dict(recorded_sha256=expected, observed_sha256=observed,
                                  current_source_matches=True, origin='Original G0-to-G7_SURFACE stage binding')
    nested, hybrid = read(NESTED/'RECEIPT.json'), read(EXPERIMENT/'RECEIPT.json')
    for label, receipt in (('NESTED', nested), ('HYBRID', hybrid)):
        for _key, item in receipt['source_snapshots'].items():
            source, snapshot, expected = Path(item['source']), Path(item['snapshot']), item['sha256']
            if sha(source) != expected or sha(snapshot) != expected:
                raise ValueError('Retained executed source snapshot differs: '+str(source))
            code[str(source)] = dict(recorded_sha256=expected, observed_sha256=expected,
                current_source_matches=True, snapshot=str(snapshot),
                snapshot_sha_verified=True, origin=label+' actual executed source binding')
    nv = nested['variants']['NESTED']
    ordered.extend([
        dict(stage='G7_PRIMARY_MIDDLE_WEIGHT_AND_NESTED', actual_generation=7,
             operation='Actual G7_SURFACE + inherited actual G6 MIDDLE lift; primary gain .95+.35*p; fresh CHILD then SMALL',
             external_control=nv['control_quad'], recorded_control_sha256=nv['control_quad_sha256'],
             original_LINKED_WIDE_or_global_micro_FLOW_included=False,
             receipt='provenance/NESTED_RECEIPT.json'),
        dict(stage='HISTORY_CLASSIFICATION', operation='Actual earlier-stage shape evidence changes SOURCE5 and Tissue host selection; no feature-birth claim',
             receipt='provenance/hybrid/history_classification/CLASSIFICATION_RECEIPT.json'),
        dict(stage='G6_COARSE_MANDEL_PAIRED_CC', operation='New coarse Mandel on actual G6; true paired neutral CC displacement difference, projected onto original G7 normals; NESTED underlay retained',
             receipt='provenance/hybrid/INTERLEAVED_COARSE_RECEIPT.json'),
        dict(stage='PAPER_ORIGIN_ACTUAL_TISSUE_AND_FRESH_FINE', operation='Actual paper component -> actual Tissue topmost height-grid adapter + fresh fine Mandel; guards and local recovery against actual safe22',
             full_paper_handles_or_overhangs_transferred=False,
             receipt='provenance/hybrid/FORMATION.json'),
        dict(stage='FULL_NATIVE_EXPORT', operation='Original G7 quads rendered/exported as four arithmetic-centre fan triangles each',
             receipt='provenance/export/MODEL_RECEIPT.json')])
    quality = read(EXPERIMENT/'GEOMETRY_QUALITY.json')
    manifest = dict(schema=SCHEMA, status='PRESERVED',
        preserved_at_utc=datetime.now(timezone.utc).isoformat(),
        baseline='G7_GENERATION_MIRROR_HYBRID_FULL',
        latest_instruction='Retain the existing liked original pipeline and checkpoint GitHub; stop new overlap or replay generation.',
        external_model=dict(path=str(model_path), recorded_sha256=MODEL_SHA,
            bytes=model['bytes'], vertices=model['vertices'], triangles=model['triangles'],
            large_file_copied=False, large_file_rehashed_by_this_tool=False,
            digest_provenance='Agreement of original MODEL_RECEIPT.json and complete MODEL_READBACK.json; only current file existence/size checked here'),
        preserved_files=copied, copied_file_count=len(copied),
        copied_bytes=sum(x['bytes'] for x in copied),
        algorithm_archive=dict(path='algorithm/'+archive_name, sha256=BUNDLE_SHA,
            all_member_CRC_verified=True, manifest_member_SHA_verified=len(bundle_manifest['files']),
            duplicate_member_names=0, standalone_geometry_replay_performed=False),
        full_original_process_order=ordered, original_carrier=dict(rings=25,sectors=16,radius=.78),
        source_code_bindings=code,
        validation_scope=dict(rendered_native_fan=quality,
            full_large_model_revalidation_performed=False,
            original_model_readback_preserved=True, global_self_intersection_certified=False,
            fabrication_certified=False),
        deferred_and_not_baseline=dict(
            shortened_G5_final_pipeline=True, selective193_overlap_experiments=True,
            additional_early_layout_or_Mandel_mass_overlap=True,
            new25_or49_source_generation=True, whole_CC1_or_structural_rebuild_replacement=True,
            policy='Existing experiments remain separate research archives; no new generation is requested.'),
        preservation_tool=dict(path=Path(__file__).relative_to(REPO).as_posix(),sha256=sha(__file__)),
        source_files_modified=False, geometry_rebuilt=False, E_drive_writes=False,
        git_operations_performed=False)
    output.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(status='PRESERVED', manifest=str(manifest_path),
        copied_files=len(copied), copied_bytes=manifest['copied_bytes'],
        verified_source_bindings=len(code), algorithm_CRC=True,
        archive_member_SHA_count=len(bundle_manifest['files']),
        geometry_rebuilt=False, E_drive_writes=False, git_operations=False), indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=REPO/'docs/column_pipeline_20261017')
    args = parser.parse_args()
    preserve(args.output)
