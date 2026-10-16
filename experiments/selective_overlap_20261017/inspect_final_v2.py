"""Final native QA/export plus independent cached Tissue unit-contract proof.

The previously tested native exporter is retained byte-for-byte. This wrapper
checks the physical-to-unit Tissue conversion and the full desired deposition
formula before any model is exported. Input geometry is never modified.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

import numpy as np
from scipy.interpolate import RectBivariateSpline


HERE = Path(__file__).resolve().parent
BASE = HERE/"inspect_final.py"
BASE_SHA = "207619e3aaf89ce76a93198aed47a011c784710894e7d1705ee7cc47b00309cb"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != BASE_SHA:
    raise ValueError("The immutable native QA/export dependency changed")
spec = importlib.util.spec_from_file_location("selective_native_export_retained", BASE)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)


def unit_height(grid, raw, u, v):
    maximum = float(np.max(raw))
    if not np.isfinite(raw).all() or raw.min() < 0 or maximum <= 0:
        raise ValueError("Actual Tissue raw height grid must be finite/nonnegative/nonconstant")
    spline = RectBivariateSpline(grid, grid, raw/maximum, s=0)
    return np.clip(spline.ev(u, v), 0., 1.), maximum


def tissue_contract(final):
    receipt = base.q.read(Path(final)/"RECEIPT.json")
    if receipt["schema"] != base.SCHEMA or receipt.get("status") != "PASS":
        raise ValueError("A completed actual finish is required")
    arrays = receipt["arrays"]
    asset = receipt["source_assets"]["tissue"]
    grid_path = base.q.checked(asset["height_grid"]["path"], asset["height_grid"]["sha256"])
    provenance_path = base.q.checked(asset["receipt"]["path"], asset["receipt"]["sha256"])
    provenance = base.q.read(provenance_path)
    if not provenance.get("actual_Tissue_call_succeeded") or provenance["height_grid_sha256"] != base.q.sha(grid_path):
        raise ValueError("Actual upstream Tissue provenance is not bound to the grid")
    with np.load(grid_path, allow_pickle=False) as z:
        uv, raw = z["uv"], z["height"]
    if uv.ndim != 1 or raw.shape != (len(uv), len(uv)) or uv[0] != 0 or uv[-1] != 1 or not np.all(np.diff(uv) > 0):
        raise ValueError("Actual Tissue grid coordinates are invalid")
    maximum = float(raw.max())
    if not np.isfinite(raw).all() or raw.min() < 0 or maximum <= 0:
        raise ValueError("Actual Tissue raw height grid is invalid")
    normal_grid = raw/maximum
    if not np.isclose(asset.get("raw_height_max", np.nan), maximum, rtol=0, atol=1e-15) or not np.isclose(asset.get("height_normalization_factor", np.nan), 1/maximum, rtol=1e-14, atol=0) or asset.get("normalized_height_max") != 1:
        raise ValueError("Declared Tissue unit-normalization metadata differs from the actual source grid")
    spline = RectBivariateSpline(uv, uv, normal_grid, s=0)
    data = {k:base.checked_array(arrays[k]) for k in
            ("PATTERN_COORDINATES", "TISSUE_HEIGHT", "TISSUE_PRIORITY", "MANDEL_SOURCE_HEIGHT",
             "NORMAL_SAFETY_CAP", "FLOW_PROTECTION", "FIXED_MASK", "DESIRED_HEIGHT")}
    n = len(data["TISSUE_HEIGHT"])
    if data["PATTERN_COORDINATES"].shape != (n, 2) or any(a.shape != (n,) for k, a in data.items() if k != "PATTERN_COORDINATES"):
        raise ValueError("Actual deposited scalar fields have different vertex counts")
    recipe = receipt["recipe"]
    amplitude = float(receipt["existing_ornament_recipe"]["tissue_amplitude"])*float(receipt["existing_ornament_recipe"]["length_scale"])
    long_period, cross_period = (float(recipe[k]) for k in ("tissue_longitudinal_period", "tissue_transverse_period"))
    max_sample_error = max_formula_error = 0.
    rejected_raw_scale_samples = 0
    height_min, height_max = float("inf"), float("-inf")
    full_peak_contribution = 0.
    for first in range(0, n, base.CHUNK):
        end = min(first+base.CHUNK, n)
        physical = data["PATTERN_COORDINATES"][first:end]
        u, v = np.mod(physical[:, 0]/long_period, 1.), np.mod(physical[:, 1]/cross_period, 1.)
        expected = np.clip(spline.ev(u, v), 0., 1.)
        actual = data["TISSUE_HEIGHT"][first:end]
        if not np.isfinite(actual).all() or actual.min() < 0 or actual.max() > 1:
            raise ValueError("Normalized actual Tissue samples leave [0,1]")
        err = float(np.max(np.abs(expected-actual)))
        max_sample_error = max(max_sample_error, err)
        rejected_raw_scale_samples += int(np.sum(np.abs(expected-actual) > 1e-10))
        height_min, height_max = min(height_min, float(actual.min())), max(height_max, float(actual.max()))
        priority = data["TISSUE_PRIORITY"][first:end]
        tissue = np.minimum(amplitude, data["NORMAL_SAFETY_CAP"][first:end])*actual*priority
        full_peak_contribution = max(full_peak_contribution, float(np.max(tissue)))
        desired = (data["MANDEL_SOURCE_HEIGHT"][first:end]*(1-priority)+tissue)*(1-data["FLOW_PROTECTION"][first:end])
        desired[data["FIXED_MASK"][first:end].astype(bool)] = 0.
        max_formula_error = max(max_formula_error, float(np.max(np.abs(desired-data["DESIRED_HEIGHT"][first:end]))))
    if max_sample_error > 1e-10:
        raise ValueError("Actual Tissue unit-height samples were not normalized by the physical raw grid maximum: maxerror="+str(max_sample_error))
    if max_formula_error > 1e-12:
        raise ValueError("Desired deposition does not apply Tissue physical amplitude/priority exactly once: maxerror="+str(max_formula_error))
    return dict(passed=True, actual_upstream_Tissue_receipt=base.q.record(provenance_path),
                raw_physical_grid=base.q.record(grid_path), raw_physical_maximum=maximum,
                independently_normalized_grid_maximum=float(normal_grid.max()),
                all_saved_control_samples_checked=n, normalized_height_range=[height_min, height_max],
                maximum_normalized_sample_error=max_sample_error, sample_mismatches_above_1e_minus10=rejected_raw_scale_samples,
                physical_tissue_amplitude=amplitude, maximum_pre_flow_Tissue_contribution=full_peak_contribution,
                maximum_desired_formula_error=max_formula_error,
                physical_amplitude_and_priority_applied_once=True,
                normalization="raw physical height / its actual maximum before normalized component evaluation",
                historical_actual_Tissue_asset_reused=True, fresh_Tissue_invocations_claimed=False)


def main(args):
    assets = tissue_contract(args.final)
    output = args.output
    args.output = None
    result = base.inspect(args)
    result["actual_Tissue_unit_contract_QA"] = assets
    result["inspector"] = base.q.record(__file__)
    result["retained_native_exporter"] = base.q.record(BASE)
    if output:
        out = output.resolve()
        if out.exists():
            raise FileExistsError("Preserved export exists; use a fresh output folder")
        out.mkdir(parents=True)
        records = result["final_arrays"]
        x = np.load(records["NATIVE_XYZ"]["path"], mmap_mode="r", allow_pickle=False)
        t = np.load(records["NATIVE_FACES"]["path"], mmap_mode="r", allow_pickle=False)
        result["model"] = base.export_ply(out/("CHESHIRE_"+args.id+"_G5_NATIVE_FULL.ply"), x, t)
        base.q.write(out/"SELECTIVE_FINAL_EXPORT_AND_QA.json", result)
    print(json.dumps(dict(status=result["status"], actual_geometry=result["actual_geometry"],
                          Tissue_unit_contract=assets, model=result.get("model")), ensure_ascii=True, allow_nan=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-g5", type=Path, required=True)
    parser.add_argument("--final", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--id", default="L08_PRIMARY_193")
    main(parser.parse_args())
