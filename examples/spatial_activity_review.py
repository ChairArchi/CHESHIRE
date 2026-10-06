"""Matched real-geometry sheets and separate diagnostic tables; no beauty rank."""
import argparse
import csv
from html import escape
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spatial_activity_study import ROOT, STUDY, FROZEN, read, write, digest


def observations():
    rows = []; cases = []
    references = read(FROZEN/"uniform_reference_hashes.json")
    for directory in sorted((STUDY/"cases").iterdir()):
        if not (directory/"summary.json").is_file():
            cases.append(dict(id=directory.name, status="FAILED", reason=read(directory/"failure.json") if (directory/"failure.json").is_file() else "No checkpoint")); continue
        result = read(directory/"summary.json"); spec = result["spec"]
        audit = read(directory/"crossing_audit.json") if (directory/"crossing_audit.json").is_file() else None
        crossings = {int(r["id"][1:]): r["sampled_transverse_crossings"] for r in audit["candidates"]} if audit else {}
        stages = []
        for record in result["stages"]:
            g = record["generation"]; warning = record.get("diagnostics", {})
            topology = record["monitor"]["topology"]
            hierarchy = record.get("hierarchy", {}); dis = hierarchy.get("displacement", {})
            patch = hierarchy.get("active_patches", {}); normal = hierarchy.get("normal_variation", {})
            row = dict(id=directory.name, stage=spec["stage"], seed=spec["seed"], grammar=spec["grammar"], strategy=spec["strategy"], generation=g,
                vertex_count=record["statistics"]["vertex_count"], face_count=record["statistics"]["face_count"],
                source_coverage=record["source_coverage"], manifold=topology["is_manifold"], closed=topology["is_closed"], components=topology["components"],
                fan=len(warning.get("opposed_fan_normals", [])), degenerate=len(warning.get("degenerate_fan_faces", [])),
                bilinear=len(warning.get("bilinear_admissibility_warning_faces", [])), crossings=0 if g==0 else crossings.get(g),
                displacement_mean=dis.get("mean"), displacement_median=dis.get("median"), displacement_max=dis.get("max"), displacement_variance=dis.get("variance"),
                top_decile_mass=dis.get("top_decile_mass_fraction"), effective_fraction=hierarchy.get("spatial_concentration", {}).get("effective_fraction"),
                patches=patch.get("count"), largest_patch_fraction=patch.get("largest_patch_fraction"),
                normal_radius_1=normal.get("radius_1", {}).get("mean"), normal_radius_2=normal.get("radius_2", {}).get("mean"),
                opening_width_drift_percent=100*(record["monitor"]["opening_normalized"]["width"]-1),
                opening_height_drift_percent=100*(record["monitor"]["opening_normalized"]["height"]-1),
                outer_width_drift_percent=record["monitor"]["dimensions_drift_percent"]["width"],
                outer_height_drift_percent=record["monitor"]["dimensions_drift_percent"]["height"],
                base_z_displacement=record["monitor"]["support_base_displacement"]["mean"],
                geometry_hash=record["geometry_hash"], activity_scale=record.get("activity_scale", "SOURCE"))
            row["uniform_exact"] = spec["strategy"]=="U" and record["geometry_hash"]==references[spec["grammar"]][f"G{g}"]
            rows.append(row); stages.append(row)
        reasons = []
        if result["status"]!="SUCCESS": reasons.append("Incomplete requested generation")
        for row in stages[1:]:
            if row["source_coverage"]!=1: reasons.append(f"G{row['generation']} field coverage incomplete")
            if row["crossings"] is None: reasons.append(f"G{row['generation']} crossing audit unavailable")
            elif row["crossings"]: reasons.append(f"G{row['generation']} sampled transverse contacts: {row['crossings']}")
            if row["fan"] or row["degenerate"] or row["bilinear"]: reasons.append(f"G{row['generation']} fan/degenerate/bilinear warnings {row['fan']}/{row['degenerate']}/{row['bilinear']}")
            if not row["manifold"] or not row["closed"] or row["components"]!=1: reasons.append(f"G{row['generation']} topology issue")
        cases.append(dict(id=directory.name, spec=spec, status=result["status"], technical_clean=not reasons,
            technical_reasons=reasons, generations_reached=result["generations_reached"], elapsed_seconds=result.get("elapsed_seconds"),
            terminal=stages[-1], uniform_exact_all_generations=all(r["uniform_exact"] for r in stages) if spec["strategy"]=="U" else None))
    write(STUDY/"outcomes.json", cases)
    with (STUDY/"metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    write(STUDY/"metric_records.json", rows)
    print("cases", len(cases), "clean", sum(r.get("technical_clean", False) for r in cases),
          "uniform exact", all(r["uniform_exact_all_generations"] for r in cases if r.get("spec", {}).get("strategy")=="U"))
    for r in cases:
        if "terminal" not in r: continue
        last = r["terminal"]
        print(r["id"], "CLEAN" if r["technical_clean"] else "WARN", "G"+str(last["generation"]),
              "fan/cross", last["fan"], last["crossings"], "patch", last["patches"],
              "normal", round(last["normal_radius_1"] or 0, 4),
              "openingH%", round(last["opening_height_drift_percent"], 2))


def plan(stage):
    views = STUDY/"views"; views.mkdir(exist_ok=True)
    camera = FROZEN/"camera.json"
    if not camera.exists():
        prior = read(ROOT/"output/task17/study/views/selected_plan.json")
        write(camera, dict(bounds=prior["bounds"], provenance="Exact Task17 selected whole/front and C0-registered detail bounds; frozen before Task18 visual review"))
    bounds = read(camera)["bounds"]; w, h = 600, 630
    outcomes = [r for r in read(STUDY/"outcomes.json") if r.get("spec", {}).get("stage")==stage and r["status"]=="SUCCESS"]
    frames = []; sheets = []; images = {}
    for outcome in outcomes:
        name = outcome["id"]; spec = outcome["spec"]
        for g in range(outcome["generations_reached"]+1):
            for kind in ("whole", "front"):
                file = f"{name}_G{g}_{kind}.png"; images[name,g,kind] = file
                frames.append(dict(mesh=f"../cases/{name}/G{g}.json", file=file, camera="front" if kind=="front" else "oblique",
                    width=w, height=h, bounds=bounds["front" if kind=="front" else "oblique"], silhouette=kind=="front",
                    label=f"{spec['grammar']} / {spec['seed'][0]} / {spec['strategy']} / G{g}"+ (" / WARN" if not outcome["technical_clean"] else "")))
    if stage=="A":
        for seed in ("A_SHOULDER_PAIR", "B_FOUR_CORNER_FRAME", "C_UPPER_BIAS"):
            for grammar in ("CC", "DS", "HYBRID"):
                ordered = [r for strategy in ("U","S","M","R","P") for r in outcomes if r["spec"]["seed"]==seed and r["spec"]["grammar"]==grammar and r["spec"]["strategy"]==strategy]
                for kind in ("whole","front"):
                    sheets.append(dict(file=f"A_{seed}_{grammar}_{kind}_progression.png", title=f"{seed} {grammar}: rows U/S/M/R/P; columns G0/G1/G2/G3/G4",
                        images=[images[r["id"],g,kind] for r in ordered for g in range(5)], columns=5, width=w, height=h))
            for kind in ("whole","front"):
                ordered = [r for grammar in ("CC","DS","HYBRID") for strategy in ("U","S","M","R","P") for r in outcomes if r["spec"]["seed"]==seed and r["spec"]["grammar"]==grammar and r["spec"]["strategy"]==strategy]
                sheets.append(dict(file=f"A_{seed}_{kind}_grammars.png", title=f"{seed}: rows CC/DS/HYBRID; columns U/S/M/R/P at G4",
                    images=[images[r["id"],4,kind] for r in ordered], columns=5, width=w, height=h))
        for kind in ("whole","front"):
            ordered=[r for grammar in ("CC","DS","HYBRID") for strategy in ("U","S","M","D") for r in outcomes if r["spec"]["seed"]=="A_SHOULDER_PAIR" and r["spec"]["grammar"]==grammar and r["spec"]["strategy"]==strategy]
            sheets.append(dict(file=f"A_distance_{kind}.png", title="A seeds: rows CC/DS/HYBRID; columns U/S/M/distance-static at G4",
                images=[images[r["id"],4,kind] for r in ordered], columns=4, width=w, height=h))
    else:
        for r in outcomes:
            for kind in ("whole","front"):
                sheets.append(dict(file=f"{r['id']}_{kind}_progression.png", title=r["id"]+": all reached generations, same scale",
                    images=[images[r["id"],g,kind] for g in range(r["generations_reached"]+1)], columns=4, width=w, height=h))
        for kind, extra in (("detail", {}), ("wire", {"wireframe":True})):
            selected=[]
            for r in outcomes:
                for g in (3, r["generations_reached"]):
                    file=f"{r['id']}_G{g}_{kind}.png"; selected.append(file)
                    frames.append(dict(mesh=f"../cases/{r['id']}/G{g}.json", file=file,camera="oblique",width=w,height=h,
                        bounds=bounds["detail"] if kind=="detail" else bounds["oblique"],label=f"{r['spec']['grammar']} {r['spec']['seed'][0]} {r['spec']['strategy']} G{g} {kind}", **extra))
            sheets.append(dict(file=f"B_{kind}_comparison.png",title=f"Deep controls: paired G3 / terminal {kind}; fixed crop, no recentering",
                images=selected,columns=4,width=w,height=h))
        for kind in ("whole","front"):
            sheets.append(dict(file=f"B_{kind}_comparison.png",title="All declared deep controls / actual terminal generations",
                images=[images[r["id"],r["generations_reached"],kind] for r in outcomes],columns=4,width=w,height=h))
    write(views/f"{stage}_plan.json",dict(frames=frames,sheets=sheets,bounds=bounds,
        caveat="Fixed approximate polygon painter; nonplanar first-three-corner shade and polygon fill are not Rhino images or hidden-surface certification. Warning cases included and labeled, not disguised."))
    print(views/f"{stage}_plan.json",len(frames),"frames",len(sheets),"sheets")


def drift_plots():
    # Small self-contained SVG scatter plots, not a combined hierarchy score.
    rows = [r for r in read(STUDY/"metric_records.json") if r["generation"]>0]
    plots=STUDY/"plots"; plots.mkdir(exist_ok=True)
    colors={"U":"#222222","S":"#2774a6","M":"#b64330","R":"#398647","P":"#8154a3","D":"#bd822a"}
    for grammar in ("CC","DS","HYBRID"):
        for ykey in ("normal_radius_2","effective_fraction","largest_patch_fraction"):
            selected=[r for r in rows if r["grammar"]==grammar and r[ykey] is not None]
            xkey="opening_height_drift_percent"
            lo=min(r[xkey] for r in selected)-2; hi=max(r[xkey] for r in selected)+2
            ymin=min(r[ykey] for r in selected); ymax=max(r[ykey] for r in selected)
            pad=max((ymax-ymin)*.1,.01); ymin-=pad; ymax+=pad
            def xy(r): return (90+(r[xkey]-lo)/(hi-lo)*670,530-(r[ykey]-ymin)/(ymax-ymin)*420)
            svg=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="640" viewBox="0 0 900 640">',
                '<rect width="900" height="640" fill="white"/>',f'<text x="50" y="35" font-size="20">{grammar}: {ykey} versus opening-height drift</text>',
                '<text x="50" y="63" font-size="13">Each point is one actual case/generation; no gate rejection or combined score</text>',
                '<path d="M90 100 V530 H770" stroke="black" fill="none"/>']
            for t in range(6):
                x=90+t/5*670; y=530-t/5*420
                svg.extend([f'<text x="{x-15}" y="552" font-size="12">{lo+t/5*(hi-lo):.1f}</text>',
                    f'<text x="20" y="{y+4}" font-size="12">{ymin+t/5*(ymax-ymin):.3f}</text>'])
            for r in selected:
                x,y=xy(r); color=colors[r["strategy"]]
                title=escape(f"{r['id']} G{r['generation']}; x={r[xkey]:.5g}; y={r[ykey]:.5g}")
                svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{color}" fill-opacity=".65"><title>{title}</title></circle>')
            for i,(name,color) in enumerate(colors.items()):
                svg.append(f'<text x="800" y="{130+i*30}" fill="{color}" font-size="16">{name}</text>')
            svg.extend(['<text x="240" y="590" font-size="16">Opening-height drift (%) — approximate descendant landmarks</text>', '</svg>'])
            (plots/f"{grammar}_{ykey}_vs_drift.svg").write_text("\n".join(svg)+"\n",encoding="utf-8")


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--observations",action="store_true")
    parser.add_argument("--plan",choices=("A","B")); parser.add_argument("--plots",action="store_true")
    args=parser.parse_args()
    if args.observations: observations()
    if args.plan: plan(args.plan)
    if args.plots: drift_plots()
