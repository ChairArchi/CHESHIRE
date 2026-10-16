"""Deterministic early-parent experiments: baseline plus eighteen variants."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np


def _axial_knots(nodes, phase, family):
    source = np.linspace(0, 1, nodes+2)
    p = np.arange(nodes+1)
    if family == "fan":
        intervals = np.linspace(0.78, 1.24, nodes+1)
    else:
        intervals = 1+0.24*np.cos(phase+p*(1.3 if family == "overlap" else 1.9))
    target = np.r_[0, np.cumsum(intervals)/intervals.sum()]
    return [source.tolist(), target.tolist()]


def variant_recipes():
    """Return independent dicts suitable for macro_replay's individual JSON."""
    recipes = [dict(id="B00", label_ko="기준형 · 기존 초기 연산",
                    family="baseline", length_scale=1.0, macro_fields={})]
    designs = {
        "overlap": [
            (3, 1.00, 0.10, 0.23, 0.42, 0.50),
            (4, 1.10, 0.45, 0.19, 0.48, 0.58),
            (5, 1.20, 0.90, 0.16, 0.55, 0.64),
            (6, 1.30, 1.30, 0.14, 0.58, 0.70),
            (4, 1.40, 1.70, 0.22, 0.65, 0.75),
            (5, 1.50, 2.10, 0.18, 0.60, 0.80)],
        "fan": [
            (3, 1.00, 0.20, 0.23, 0.45, 0.45),
            (4, 1.10, 0.70, 0.20, 0.50, 0.50),
            (5, 1.20, 1.10, 0.17, 0.58, 0.60),
            (6, 1.30, 1.50, 0.145, 0.62, 0.65),
            (4, 1.40, 1.90, 0.22, 0.68, 0.70),
            (5, 1.50, 2.30, 0.19, 0.65, 0.75)],
        "mirrored_twist": [
            (3, 1.00, 0.00, 0.24, 0.40, 0.35),
            (4, 1.10, 0.40, 0.20, 0.48, 0.40),
            (5, 1.20, 0.80, 0.18, 0.55, 0.50),
            (6, 1.30, 1.20, 0.15, 0.60, 0.55),
            (4, 1.40, 1.60, 0.23, 0.62, 0.60),
            (5, 1.50, 2.00, 0.20, 0.66, 0.65)]}
    labels = {"overlap": "큰 주름 겹침", "fan": "부채형 위계", "mirrored_twist": "반사 비틀림"}
    prefixes = {"overlap": "O", "fan": "F", "mirrored_twist": "T"}
    # Actual G0->G1 and G1->G2 coupled-subdivision placement controls. These
    # values are inside task36_growth.step's declared parameter domain. The
    # stronger variants change early child placement, not only the G3 field.
    upstream = {
        "overlap": [
            dict(face_gain=.85, edge_gain=.26, inherited_bias=.95, diagonal_tension=-.90, vertex_tension=-.95),
            dict(face_gain=.90, edge_gain=.12, inherited_bias=-.25, diagonal_tension=.25, vertex_tension=-1.0),
            dict(face_gain=.92, edge_gain=.30, inherited_bias=1.0, diagonal_tension=-.95, vertex_tension=-1.15)],
        "fan": [
            dict(face_gain=.50, edge_gain=.38, inherited_bias=.90, diagonal_tension=.60, vertex_tension=-.45),
            dict(face_gain=.75, edge_gain=.32, inherited_bias=-.45, diagonal_tension=-.85, vertex_tension=-.45),
            dict(face_gain=.90, edge_gain=.42, inherited_bias=.55, diagonal_tension=.30, vertex_tension=-.95)],
        "mirrored_twist": [
            dict(face_gain=.75, edge_gain=.24, inherited_bias=.35, diagonal_tension=-.95, vertex_tension=-.40),
            dict(face_gain=.55, edge_gain=.42, inherited_bias=-.55, diagonal_tension=.40, vertex_tension=-1.05),
            dict(face_gain=.88, edge_gain=.34, inherited_bias=.95, diagonal_tension=-.25, vertex_tension=-1.20)]}
    for family, rows in designs.items():
        for j, (nodes, length, phase, width, radial, axial) in enumerate(rows, 1):
            macro = dict(family=family, nodes=nodes, node_width=width,
                phase=phase, phase_advance=0.55+0.12*j, angular_order=1+(j % 3),
                radial_strength=radial, axial_strength=axial,
                tangent_strength=(0.22+0.035*j if family == "mirrored_twist" else 0.10+0.02*j),
                hierarchy=0.28+0.055*j, turns=0.35+0.18*j,
                return_bias=0.10+0.035*j, cap_fade=0.075,
                displacement_bound=0.72+0.025*j, length_scale=1.0,
                node_strengths=[float(v) for v in 0.85+0.25*np.cos(np.arange(nodes)*1.1+phase)])
            radial_profile = [1.0]+[float(1+0.10*np.cos(phase+k*1.2)) for k in range(6)]+[1.0]
            row = dict(id=f"{prefixes[family]}{j:02d}", family=family,
                label_ko=f"{labels[family]} {j} · {nodes}마디 · 길이 {length:.1f}배",
                length_scale=length, radius_scale_profile=radial_profile,
                material_axial_knots=_axial_knots(nodes, phase, family),
                macro_fields=macro, macro_injection_stage="G03_SIDEWALL_BEFORE_G04_NEUTRAL",
                global_XY_reflection=True, global_chiral_twist=False,
                experimental=True, fabrication_certified=False)
            if j >= 4:
                row["task36_recipe"] = upstream[family][j-4]
                row["upstream_child_placement_changed"] = True
            if j >= 2:
                # Keep the accepted search windows/three sidewall sectors;
                # alter the actual earlier returns and generated branch shape.
                direction = {"overlap": .30, "fan": .52, "mirrored_twist": .22}[family]
                row["overlap_events"] = [
                    dict(height=.32+.015*j, direction=direction+.025*j,
                         sweep=.18+.025*j, return_depth=.64+.025*j),
                    dict(height=.64+.01*j, direction=1.25-.035*j,
                         sweep=.34-.02*j, return_depth=.76-.02*j)]
                if family == "fan":
                    row["root_recipe"] = dict(root_heights=[.22,.65+.025*j,1.05+.06*j],
                        root_scales=[.98,.78,.52+.015*j], root_bend=.12+.025*j)
                    row["sidewall_recipe"] = dict(heights_root_radius=[.10,.34,.58+.045*j],
                        scales=[1.0,.72,.38], bend=.20+.025*j)
                elif family == "mirrored_twist":
                    row["root_recipe"] = dict(root_heights=[.28,.72,1.03+.035*j],
                        root_bend=.20+.03*j, twist=(-1)**j*.035*j)
                    row["sidewall_recipe"] = dict(heights_root_radius=[.12,.38,.62+.03*j],
                        bend=.26+.025*j, twist=-(-1)**j*.045*j)
                else:
                    row["root_recipe"] = dict(root_heights=[.27,.74,1.06+.045*j],
                        root_scales=[.92,.82,.65], root_bend=.22+.035*j)
                    row["sidewall_recipe"] = dict(heights_root_radius=[.12,.40,.66+.035*j],
                        bend=.28+.035*j)
            recipes.append(row)
    return deepcopy(recipes)


def catalogue():
    return dict(schema="CHESHIRE_EARLY_DYNAMIC_VARIATIONS_V1", recipes=variant_recipes(),
        baseline_id="B00", variation_count=18,
        meaning_ko="초기 부모의 길이·마디·겹침·부채·반사 비틀림을 바꾼 뒤 실제 후속 연산을 다시 계산하는 비교입니다.",
        length_scope="Top-level length_scale is applied once at G0. macro_fields.length_scale stays 1.",
        topology_scope="Macro coordinate fields retain topology; historical root/sidewall events still run.",
        symmetry_scope="All variants retain global X/Y reflections. Twist is counter-handed across mirror planes.",
        stronger_variants="O04..06/F04..06/T04..06 also change actual G1/G2 coupled subdivision face, edge, ancestry and tension controls.",
        units="Macro strengths and bound are fractions of actual parent median radius; node widths use inherited material t.",
        noise_used=False, aesthetic_success_claimed=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError("Preserve the previous catalogue: " + str(a.output))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(catalogue(), ensure_ascii=False, indent=2,
                                 allow_nan=False)+"\n", encoding="utf-8")
    print(a.output, flush=True)


if __name__ == "__main__":
    main()
