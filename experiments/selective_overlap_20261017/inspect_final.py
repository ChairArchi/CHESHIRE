"""Inspect/export a fresh selective-source G5 finish without changing geometry.

The actual G5 parent and final NPY records are mandatory. Native centroid fans,
parent V/E/F lineage, material chart, symmetry, fixed masks and full PLY
readback are independently checked. Proper intersections are not certified.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
QA_PATH = HERE.parent / "inherited_rule_variations_20261017/inspect_inherited.py"
QA_SHA = "0a0286c7374e1130ed23cb641bce6d8e35d69b34678b07fb087373a34068d664"
if hashlib.sha256(QA_PATH.read_bytes()).hexdigest() != QA_SHA:
    raise ValueError("Immutable native QA dependency changed")
spec = importlib.util.spec_from_file_location("selective_final_native_qa", QA_PATH)
q = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = q
spec.loader.exec_module(q)
SCHEMA = "CHESHIRE_SELECTIVE_ACTUAL_HOST_MANDEL_TISSUE_FINISH_V1"
CHUNK = 131072
FOLD5_PATH = HERE.parent/"coherent_fold_detail_20261013/fold_operator.py"
FOLD5_SHA = "ae759519969b3989788013025575fbbf7c7f79eafd787a97b1851cf0b649183f"
SECTION_PATH = HERE/"inspect_layout.py"
SECTION_SHA = "c09ff79b55154f1ce0f9e45e9bd1fac5fd917bafa699fcc28d5b87ffdb4137bc"


def file_bindings(value):
    """Collect explicit record and absolute-path/hash mappings recursively."""
    result = {}
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
            result[str(Path(value["path"]).resolve())] = value["sha256"]
        for key, item in value.items():
            if isinstance(key, str) and Path(key).is_absolute():
                if isinstance(item, str) and len(item) == 64:
                    result[str(Path(key).resolve())] = item
                elif isinstance(item, dict) and isinstance(item.get("sha256"), str):
                    result[str(Path(key).resolve())] = item["sha256"]
                    if item.get("snapshot"):
                        result[str(Path(item["snapshot"]).resolve())] = item["sha256"]
            result.update(file_bindings(item))
    elif isinstance(value, list):
        for item in value:
            result.update(file_bindings(item))
    return result


def checked_array(record):
    path = q.checked(record["path"], record["sha256"])
    a = np.load(path, mmap_mode="r", allow_pickle=False)
    if not isinstance(a, np.ndarray):
        raise ValueError("Final array records must point to individual NPY arrays")
    if "shape" in record and list(a.shape) != list(record["shape"]):
        raise ValueError("Final NPY shape differs from its bound record")
    if "dtype" in record and np.dtype(record["dtype"]) != a.dtype:
        raise ValueError("Final NPY dtype differs from its bound record")
    if record.get("array_sha256") and q.ah(a) != record["array_sha256"]:
        raise ValueError("Final raw array hash differs")
    return a


def check_split(parent, child, evidence):
    """Validate exact V/E/F children with vector edge lookup, no large dict."""
    nq, nv = len(parent["faces"]), len(parent["xyz"])
    with np.load(evidence, allow_pickle=False) as z:
        edges, pf = z["input_edges"], z["parent_face"]
    pq = parent["faces"]
    all_edges = np.sort(np.stack((pq, np.roll(pq, -1, axis=1)), axis=2).reshape(-1, 2), axis=1)
    expected = np.unique(all_edges, axis=0)
    if not np.array_equal(edges, expected) or not np.array_equal(pf, np.repeat(np.arange(nq), 4)):
        raise ValueError("Actual G4/G5 parent/edge lineage differs")
    keys = edges[:, 0].astype(np.uint64)*np.uint64(nv)+edges[:, 1]
    if len(child["xyz"]) != nv+len(edges)+nq or child["faces"].shape != (4*nq, 4):
        raise ValueError("Actual G4/G5 V/E/F counts differ")
    if not q.exact(child["chart"][:nv], parent["chart"]):
        raise ValueError("Retained parent material coordinates changed")
    for first in range(0, nq, CHUNK):
        end = min(first+CHUNK, nq)
        f = pq[first:end]
        e = np.sort(np.stack((f, np.roll(f, -1, axis=1)), axis=2), axis=2)
        index = np.searchsorted(keys, e[:, :, 0].astype(np.uint64)*np.uint64(nv)+e[:, :, 1])
        cycles = np.stack((nv+np.roll(index, 1, axis=1), f, nv+index,
                           np.broadcast_to((nv+len(edges)+np.arange(first, end))[:, None], f.shape)), axis=2).reshape(-1, 4)
        if not np.array_equal(child["faces"][4*first:4*end], cycles):
            raise ValueError("Actual G5 child corner cycles differ")
        if not q.exact(child["chart"][nv+len(edges)+first:nv+len(edges)+end], parent["chart"][f].mean(axis=1)):
            raise ValueError("Actual G5 face-point material chart differs")
    for first in range(0, len(edges), CHUNK):
        end = min(first+CHUNK, len(edges))
        if not q.exact(child["chart"][nv+first:nv+end], parent["chart"][edges[first:end]].mean(axis=1)):
            raise ValueError("Actual G5 edge-point material chart differs")
    return dict(passed=True, parent_generation=4, output_generation=5,
                actual_parent_quads=nq, actual_child_quads=len(child["faces"]),
                exact_parent_corner_cycles=True, exact_material_VEF_transport=True)


def orientations(final, parent, faces):
    reversed_count, degenerate_count = 0, 0
    for first in range(0, len(faces), CHUNK):
        ids = faces[first:first+CHUNK]
        a, b = final[ids], parent[ids]
        ac, bc = a.mean(axis=1), b.mean(axis=1)
        an = np.cross(a-ac[:, None], np.roll(a, -1, axis=1)-ac[:, None])
        bn = np.cross(b-bc[:, None], np.roll(b, -1, axis=1)-bc[:, None])
        dot = np.einsum("fki,fki->fk", an, bn)
        reversed_count += int(np.sum((dot <= 0) | ~np.isfinite(dot)))
        degenerate_count += int(np.sum(np.linalg.norm(an, axis=2) <= 0))
    if reversed_count or degenerate_count:
        raise ValueError("Final detail reverses/degenerates actual parent native fans")
    return dict(reversed_native_fans=reversed_count, degenerate_native_fans=degenerate_count,
                reference="Actual saved selected-source G5; no quad-diagonal display claim.")


def representative_sections(parent, final, faces):
    """Three same-world-plane comparisons; select relevant quads in chunks."""
    q.checked(SECTION_PATH, SECTION_SHA)
    name = "selective_final_section_measurement"
    spec = importlib.util.spec_from_file_location(name, SECTION_PATH)
    helper = importlib.util.module_from_spec(spec)
    sys.modules[name] = helper
    spec.loader.exec_module(helper)

    def measure(xyz, z):
        selected = []
        for first in range(0, len(faces), CHUNK):
            f = faces[first:first+CHUNK]
            heights = xyz[f, 2]
            hit = (heights.min(axis=1) <= z) & (heights.max(axis=1) > z)
            selected.append(f[hit])
        f = np.concatenate(selected)
        centres = xyz[f].mean(axis=1)
        x = np.concatenate((xyz, centres))
        centre_ids = np.broadcast_to((len(xyz)+np.arange(len(f)))[:, None], f.shape)
        t = np.stack((f, np.roll(f, -1, axis=1), centre_ids), axis=2).reshape(-1, 3)
        return helper.section(x, t, z)

    rows = []
    for z in (2.8, 4.95, 7.8):
        a, b = measure(parent, z), measure(final, z)
        row = dict(world_Z=z, actual_G5_parent=a, finished=b)
        if a["valid"] and b["valid"]:
            row.update(area_proxy_ratio=abs(b["signed_section_area_proxy"])/abs(a["signed_section_area_proxy"]),
                       XY_max_width_ratio=(np.asarray(b["exact_native_XY_envelope_width"])/a["exact_native_XY_envelope_width"]).tolist(),
                       XY_arc_P10_P90_width_ratio=(np.asarray(b["boundary_arc_quadrature_XY_P10_P90_width"])/a["boundary_arc_quadrature_XY_P10_P90_width"]).tolist(),
                       first_exit_interpretation_valid=bool(a["central_first_exit_interpretation_valid"] and b["central_first_exit_interpretation_valid"]))
            if row["first_exit_interpretation_valid"]:
                row["median_first_exit_radius_ratio"] = b["first_boundary_radius_P10_P50_P90"][1]/a["first_boundary_radius_P10_P50_P90"][1]
        rows.append(row)
    return dict(world_planes=rows, reference="Actual G5 before final decoration, not G0 coordinate identity.",
                scope="Stored centroid-fan triangle sections; algebraic area/first-exit proxies, no physical-solid or aesthetic certificate.",
                measurement_helper=q.record(SECTION_PATH))


def export_ply(path, x, t):
    if x.dtype != np.dtype("float64") or len(x) >= 2**32:
        raise ValueError("Float64 XYZ / uint32 vertex-index budget required")
    header = ("ply\nformat binary_little_endian 1.0\ncomment Actual selective-source G5 finished native centroid-fan surface\n"
              f"element vertex {len(x)}\nproperty double x\nproperty double y\nproperty double z\n"
              f"element face {len(t)}\nproperty list uchar uint vertex_indices\nend_header\n").encode("ascii")
    dt = np.dtype([("count", "u1"), ("indices", "<u4", (3,))])
    with Path(path).open("xb") as stream:
        stream.write(header)
        for first in range(0, len(x), CHUNK):
            np.asarray(x[first:first+CHUNK], dtype="<f8").tofile(stream)
        for first in range(0, len(t), CHUNK):
            part = t[first:first+CHUNK]
            block = np.empty(len(part), dtype=dt)
            block["count"], block["indices"] = 3, part
            block.tofile(stream)
    vertices = np.memmap(path, mode="r", offset=len(header), dtype="<f8", shape=x.shape)
    faces = np.memmap(path, mode="r", offset=len(header)+24*len(x), dtype=dt, shape=(len(t),))
    for first in range(0, len(x), CHUNK):
        if not np.array_equal(vertices[first:first+CHUNK].view(np.uint64), x[first:first+CHUNK].view(np.uint64)):
            raise ValueError("PLY XYZ binary readback differs")
    for first in range(0, len(t), CHUNK):
        block = faces[first:first+CHUNK]
        if not np.all(block["count"] == 3) or not np.array_equal(block["indices"], t[first:first+CHUNK]):
            raise ValueError("PLY actual native triangles differ")
    expected = len(header)+24*len(x)+13*len(t)
    if Path(path).stat().st_size != expected:
        raise ValueError("PLY payload size differs")
    del vertices, faces
    return dict(**q.record(path), bytes=expected, float64_coordinates_bit_exact=True,
                uint32_native_triangles_exact=True, full_payload_readback=True)


def inspect(args):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.id):
        raise ValueError("A plain candidate identifier is required")
    source_folder, final_folder = args.source_g5.resolve(), args.final.resolve()
    receipt_path = final_folder/"RECEIPT.json"
    receipt = q.read(receipt_path)
    if receipt["schema"] != SCHEMA or receipt.get("status") != "PASS":
        raise ValueError("A completed actual selected-source finish is required")
    bound = file_bindings(receipt)
    source_info = q.read(source_folder/"generation.json")
    if source_info["subdivision_generation"] != 5 or not source_info["checks"]["passed"]:
        raise ValueError("Actual passing generation-five source required")
    q.checked(FOLD5_PATH, FOLD5_SHA)
    declared = source_info.get("geometry_code_sha256", {})
    matches = [digest for name, digest in declared.items() if name.replace("\\", "/").endswith("experiments/coherent_fold_detail_20261013/fold_operator.py")]
    if matches != [FOLD5_SHA]:
        raise ValueError("The actual G5 source does not bind the original DIRECTIONAL operator")
    for name, key in (("control_quad.npz", "control_file_sha256"), ("evidence.npz", "evidence_file_sha256")):
        p = source_folder/name
        q.checked(p, source_info[key])
    for name in ("control_quad.npz", "evidence.npz", "generation.json"):
        p = source_folder/name
        if bound.get(str(p)) != q.sha(p):
            raise ValueError("Final receipt is not bound to the actual G5 input: " + name)
    arrays = receipt["arrays"]
    actual = {name: checked_array(arrays[name]) for name in ("CONTROL_XYZ", "CONTROL_QUADS", "CHART", "NATIVE_XYZ", "NATIVE_FACES")}
    control = dict(xyz=actual["CONTROL_XYZ"], faces=actual["CONTROL_QUADS"], chart=actual["CHART"])
    with np.load(source_folder/"control_quad.npz", allow_pickle=False) as z:
        parent = {key: z[key] for key in ("xyz", "faces", "chart")}
    if not q.exact(control["faces"], parent["faces"]) or not q.exact(control["chart"], parent["chart"]):
        raise ValueError("Final decoration altered topology or material chart")
    native = q.native_fans(control, actual["NATIVE_XYZ"], actual["NATIVE_FACES"])
    orientation = orientations(control["xyz"], parent["xyz"], control["faces"])
    quality = q.topology(actual["NATIVE_XYZ"], actual["NATIVE_FACES"])
    symmetry = q.symmetry(control, actual["NATIVE_XYZ"], source_folder/"evidence.npz")
    # All guard masks belong to the actual new source, not old completed IDs.
    protections = {}
    for name in ("CAP_MASK", "WAIST_GUARD_MASK", "FLOW_PROTECTION"):
        if name not in arrays:
            continue
        weight = checked_array(arrays[name])
        if weight.shape != (len(parent["xyz"]),) or not np.isfinite(weight).all():
            raise ValueError("Invalid final protected-source mask")
        if weight.min() < 0 or weight.max() > 1+1e-12:
            raise ValueError("Protected-source weights must lie in [0,1]")
        mask = weight.astype(bool) if weight.dtype.kind == "b" else weight >= 1-1e-12
        exact = q.exact(control["xyz"][mask], parent["xyz"][mask])
        if not exact:
            raise ValueError("Final finish changed a fully protected source coordinate")
        protections[name] = dict(fully_protected_controls=int(mask.sum()), exact_source_coordinates=True,
                                  record=arrays[name])
    g4_folder = source_folder.parent/"G04_NEUTRAL"
    g4_info = q.read(g4_folder/"generation.json")
    q.checked(g4_folder/"control_quad.npz", g4_info["control_file_sha256"])
    if source_info.get("source_control_sha256", source_info.get("parent_control_sha256")) != g4_info["control_file_sha256"]:
        raise ValueError("G5 source is not bound to the actual selected G4 parent")
    with np.load(g4_folder/"control_quad.npz", allow_pickle=False) as z:
        g4 = {key: z[key] for key in ("xyz", "faces", "chart")}
    lineage = check_split(g4, parent, source_folder/"evidence.npz")
    sections = representative_sections(parent["xyz"], control["xyz"], control["faces"])
    source_files = []
    for path, digest in bound.items():
        if not path.lower().endswith((".py", ".json", ".npz")):
            continue
        q.checked(path, digest)
        source_files.append(dict(path=path, sha256=digest))
    result = dict(schema="CHESHIRE_SELECTIVE_G5_FINAL_EXPORT_AND_QA_V1", id=args.id,
                  actual_generation=5, parent_generation=4, status="PASS", actual_geometry=native,
                  quality=quality, native_orientation=orientation, actual_symmetry=symmetry,
                  G4_to_G5_lineage=lineage, unchanged_final_topology_and_chart=True,
                  original_directional_operator=q.record(FOLD5_PATH),
                  protected_source_coordinates=protections, source_bindings_verified=source_files,
                  representative_G5_parent_sections=sections,
                  source_G5={name:q.record(source_folder/name) for name in ("control_quad.npz", "evidence.npz", "generation.json")},
                  final_receipt=q.record(receipt_path), final_arrays=arrays,
                  inspector=q.record(__file__), native_QA_dependency=q.record(QA_PATH),
                  self_intersection_certified=False, fabrication_certified=False, user_adopted=False)
    if args.output:
        out = args.output.resolve()
        if out.exists():
            raise FileExistsError("Preserved export exists; use a fresh output folder")
        out.mkdir(parents=True)
        result["model"] = export_ply(out/("CHESHIRE_"+args.id+"_G5_NATIVE_FULL.ply"), actual["NATIVE_XYZ"], actual["NATIVE_FACES"])
        q.write(out/"SELECTIVE_FINAL_EXPORT_AND_QA.json", result)
    print(json.dumps({k:result[k] for k in ("schema", "status", "actual_geometry", "quality", "model") if k in result}, ensure_ascii=True, allow_nan=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-g5", type=Path, required=True)
    parser.add_argument("--final", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--id", default="L08_SELECTIVE")
    inspect(parser.parse_args())
