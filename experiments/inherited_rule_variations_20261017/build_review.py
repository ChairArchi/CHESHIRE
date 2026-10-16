"""Package hash-bound inherited-rule G4 comparisons without changing inputs.

Requires seven exported/independently inspected replays and their completed
same-stage render receipt. Writes only a fresh --exports/REVIEW directory.
The source ZIP is an audit/reuse package, not a self-contained historical solver.
"""
from pathlib import Path
import argparse
import hashlib
import html
import json
import os
import re
import shutil
import time
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
IDS = tuple("I" + f"{i:02d}" for i in range(7))
THRESHOLDS = [.01, .05, .15, .35]
LEGEND = [
    dict(name="변화 없음 / 매우 작음", interval="0 이상 0.01 미만", rgb=[.32, .35, .39]),
    dict(name="작은 변화", interval="0.01 이상 0.05 미만", rgb=[.035, .39, .74]),
    dict(name="중간 변화", interval="0.05 이상 0.15 미만", rgb=[.025, .65, .51]),
    dict(name="큰 변화", interval="0.15 이상 0.35 미만", rgb=[.94, .43, .065]),
    dict(name="매우 큰 변화", interval="0.35 이상", rgb=[.71, .12, .25]),
]
ALGORITHM_FILES = ("replay_inherited.py", "regional_split_controls.py", "inherited_recipes.json",
                   "inspect_inherited.py", "prepare_comparison.py", "build_review.py")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def ah(array):
    return hashlib.sha256(np.ascontiguousarray(array).view(np.uint8)).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def record(path):
    return dict(path=str(Path(path).resolve()), sha256=sha(path))


def rel(path, root):
    return Path(os.path.relpath(path, root)).as_posix()


def checked(row):
    p = Path(row["path"])
    if sha(p) != row["sha256"]:
        raise ValueError("Bound artifact changed: " + str(p))
    return p


def normalized_direction(image):
    direction = np.asarray(image["camera_position"], float) - np.asarray(image["target"], float)
    length = float(np.linalg.norm(direction))
    if not np.isfinite(length) or length <= 0:
        raise ValueError("Actual camera direction is invalid")
    return direction / length


def bind_images(root, models, plan, render):
    if render.get("geometry_modifiers") is not False or render.get("LOD") is not False or render.get("normal_maps") is not False:
        raise ValueError("This comparison requires unmodified full native geometry")
    if render.get("smooth_normals_display_only") is not True:
        raise ValueError("Normal-interpolation display scope must be explicit")
    plans = {r["id"]: r for r in plan["items"]}
    items = {r["id"]: r for r in render["items"]}
    if len(items) != len(render["items"]) or len(plans) != len(plan["items"]):
        raise ValueError("Duplicate render/plan identifiers")
    expected = set(IDS) | {sid + "_G2" for sid in IDS if sid != "I00"}
    if set(items) != expected or set(plans) != expected:
        raise ValueError("Exactly seven G4 and six G2 comparison items are required")
    images, image_records = {}, []
    for sid in IDS:
        item = items[sid]
        source = checked(models[sid]["actual_geometry"])
        if item["source_sha256"] != models[sid]["actual_geometry"]["sha256"] or Path(item["geometry"]).resolve() != source.resolve():
            raise ValueError("G4 render does not bind the exported actual geometry: " + sid)
        if item["native"]["vertices"] != models[sid]["quality"]["vertices"] or item["native"]["triangles"] != models[sid]["quality"]["triangles"]:
            raise ValueError("G4 displayed full-native count differs")
        images[sid] = {}
        views = {v["view"]: v for v in item["images"]}
        if set(views) != {"whole", "upper_same"} or len(views) != len(item["images"]):
            raise ValueError("Actual whole and upper_same views are required for " + sid)
        for view, im in views.items():
            image = Path(im["path"])
            if not image.is_absolute():
                image = root / "COMPARISON_RENDER" / image
            checked(dict(path=str(image), sha256=im["sha256"]))
            with Image.open(image) as source_image:
                size = list(source_image.size)
            if size != [render["size"], render["size"]]:
                raise ValueError("Actual render size differs")
            images[sid][view] = dict(path=str(image), sha256=im["sha256"], size=size, actual_view=im)
            image_records.append(dict(id=sid, view=view, **record(image)))
    camera_checks = []
    for view in ("whole", "upper_same"):
        reference = images["I00"][view]["actual_view"]
        for sid in IDS:
            actual = images[sid][view]["actual_view"]
            if not np.allclose(actual["target"], reference["target"], atol=1e-6, rtol=0) or not np.isclose(actual["scale"], reference["scale"], atol=1e-6, rtol=0):
                raise ValueError("The comparison camera target/scale differs: " + sid + "/" + view)
            if not np.allclose(normalized_direction(actual), normalized_direction(reference), atol=1e-6, rtol=0):
                raise ValueError("The comparison camera direction differs")
            if view == "upper_same":
                custom = plans[sid]["custom_views"][view]
                if not np.allclose(actual["target"], custom["target"], atol=1e-6, rtol=0) or not np.isclose(actual["scale"], custom["scale"], atol=1e-6, rtol=0):
                    raise ValueError("Actual upper view differs from the saved plan")
        camera_checks.append(dict(view=view, same_target_scale_direction=True,
                                  orthographic_distance_not_used_as_shape_scale=True,
                                  reference_actual_view=reference))
    proof_path = root / "actual_G2_change_colors/COLOR_PROOF.json"
    proof = read(proof_path)
    proofs = {row["id"]: row for row in proof["variants"]}
    baseline_path = root / "variants/I00/states/G02_OVERLAP/control_quad.npz"
    with np.load(baseline_path, allow_pickle=False) as z:
        bx, bq, bc = z["xyz"], z["faces"], z["chart"]
    color_checks = []
    for sid in IDS[1:]:
        item, entry = items[sid + "_G2"], plans[sid + "_G2"]
        stage = root / "variants" / sid / "states/G02_OVERLAP"
        stage_meta = read(stage / "generation.json")
        geometry, control = stage / "geometry.npz", stage / "control_quad.npz"
        if sha(geometry) != stage_meta["geometry_file_sha256"] or item["source_sha256"] != stage_meta["geometry_file_sha256"]:
            raise ValueError("G2 image source geometry binding differs")
        if Path(item["geometry"]).resolve() != geometry.resolve() or Path(entry["geometry"]).resolve() != geometry.resolve():
            raise ValueError("G2 render/plan source path differs")
        with np.load(control, allow_pickle=False) as z:
            x, q, chart = z["xyz"], z["faces"], z["chart"]
        if not np.array_equal(q, bq) or not np.array_equal(chart, bc):
            raise ValueError("G2 color comparison lacks exact material correspondence")
        magnitude = np.linalg.norm(x - bx, axis=1)
        tags = np.repeat(np.digitize(magnitude[q].mean(axis=1), THRESHOLDS).astype(np.int32), 4)
        saved = Path(entry["face_colors"])
        if not np.array_equal(np.load(saved, allow_pickle=False), tags) or sha(saved) != proofs[sid]["tags_sha256"]:
            raise ValueError("Saved colors are not independently reproduced actual G2 differences")
        if proofs[sid]["source_control_sha256"] != sha(control) or proofs[sid]["baseline_control_sha256"] != sha(baseline_path) or proofs[sid]["thresholds"] != THRESHOLDS:
            raise ValueError("Actual color proof/source thresholds differ")
        if len(item["images"]) != 1 or item["images"][0]["view"] != "actual_change":
            raise ValueError("One actual_change G2 view is required")
        im = item["images"][0]
        if im["actual_tags_sha256"] != ah(tags):
            raise ValueError("Actual displayed color readback differs")
        if len(entry["palette"]) != len(LEGEND):
            raise ValueError("Actual change palette category count differs")
        for row, expected_row in zip(entry["palette"], LEGEND):
            if row["rgb"] != expected_row["rgb"]:
                raise ValueError("Color palette differs from the physical change legend")
        image = Path(im["path"])
        if not image.is_absolute():
            image = root / "COMPARISON_RENDER" / image
        checked(dict(path=str(image), sha256=im["sha256"]))
        with Image.open(image) as source_image:
            size = list(source_image.size)
        if size != [render["size"], render["size"]]:
            raise ValueError("G2 actual_change size differs")
        images[sid]["actual_change"] = dict(path=str(image), sha256=im["sha256"], size=size, actual_view=im)
        image_records.append(dict(id=sid, view="actual_change", **record(image)))
        color_checks.append(dict(id=sid, exact_material_topology=True, independently_recomputed_delta_colors=True,
                                 changed_G2_controls=int(np.count_nonzero(magnitude)),
                                 coordinate_delta_quantiles=np.quantile(magnitude, [0, .5, .9, .99, 1]).tolist(),
                                 native_color_counts=np.bincount(tags, minlength=5).tolist(), actual_tags_sha256=ah(tags)))
    if next(row for row in color_checks if row["id"] == "I05")["changed_G2_controls"] != 0:
        raise ValueError("I05 G2 must remain unchanged; its variation is the later G3 selection")
    return images, dict(rendered_image_count=len(image_records), images=image_records,
                        camera_checks=camera_checks, G2_actual_change_checks=color_checks,
                        color_proof=record(proof_path))


def recipe_text(recipe):
    pieces = []
    if recipe.get("overlap_events"):
        events = recipe["overlap_events"]
        positions = "/".join(format(e["height"], ".2f") for e in events)
        pieces.append("되접기 " + str(len(events)) + "곳 · 재료 높이 t=" + positions)
        if any(any(k in e for k in ("direction", "sweep", "span", "overlap_width")) for e in events):
            pieces.append("기존 방향·폭 조정")
    if recipe.get("split_regions"):
        pieces.append("G2 분할 배치 " + str(len(recipe["split_regions"])) + "구간 · w3/w4/w1")
    if recipe.get("root_recipe"):
        pieces.append("G3 뿌리 선택 위치 변경")
    if recipe.get("sidewall_recipe"):
        pieces.append("기존 측벽 선택 방향 변경")
    return " / ".join(pieces) if pieces else "원래 설정 그대로 재현"


def font(size):
    for name in ("C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/gulim.ttc"):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    raise RuntimeError("A Korean font is required to label the comparison board")


def wrapped(draw, text, box, fnt, fill, line_height):
    x, y, width = box
    line = ""
    for character in text:
        if character == "\n":
            draw.text((x, y), line, font=fnt, fill=fill)
            y += line_height; line = ""
            continue
        if line and draw.textlength(line + character, font=fnt) > width:
            draw.text((x, y), line, font=fnt, fill=fill)
            y += line_height; line = ""
        line += character
    if line:
        draw.text((x, y), line, font=fnt, fill=fill)


def board(models, images, path):
    tile_w, tile_h, top = 500, 620, 98
    im = Image.new("RGB", (4 * tile_w, top + 2 * tile_h), "#f4f1ea")
    draw = ImageDraw.Draw(im); title = font(32); label = font(24); small = font(19)
    draw.text((24, 14), "같은 SPAN 입력 · 기존 생성 규칙의 초기 G4 비교", font=title, fill="#242923")
    draw.text((25, 60), "I00 기준안과 I01–I06 · 전체 시점과 축척 동일 · 미세 장식 추가 없음", font=small, fill="#596159")
    sizes = set()
    for i, sid in enumerate(IDS):
        source = Path(images[sid]["whole"]["path"])
        with Image.open(source) as p:
            picture = p.convert("RGB"); sizes.add(picture.size)
        picture.thumbnail((tile_w - 16, tile_w - 16), Image.Resampling.LANCZOS)
        x, y = (i % 4) * tile_w, top + (i // 4) * tile_h
        im.paste(picture, (x + (tile_w - picture.width) // 2, y + 8))
        draw.text((x + 16, y + 505), sid + " · " + models[sid]["label"], font=label, fill="#252923")
        wrapped(draw, models[sid]["summary"], (x + 16, y + 546, tile_w - 32), small, "#596159", 27)
    if len(sizes) != 1:
        raise ValueError("Whole images need one source resolution for a common-scale board")
    x, y = 3 * tile_w + 20, top + tile_h + 120
    wrapped(draw, "고정: 원본 G0 / 기존 연산 / 반사 대칭\n변경: 지점·구간·방향·분할 배치", (x, y, tile_w - 40), label, "#3d4a40", 37)
    im.save(path)
    return dict(**record(path), size=list(im.size), grid=[4, 2], geometry_edited=False,
                image_crop=False, all_whole_images_resized_with_same_scale=True, Korean_font="Malgun Gothic or Gulim")


def code_bundle(out, models, root, qa_path, plan_path, render_path):
    entries, byte_entries, origins = {}, {}, {}
    def add(name, source):
        source = Path(source)
        if name in entries and sha(entries[name]) != sha(source):
            raise ValueError("Conflicting code archive paths")
        entries[name] = source
    source_digests = {}
    for sid, row in models.items():
        receipt_path = checked(row["source_receipt"])
        receipt = read(receipt_path)
        contract_path = receipt_path.parent / "RECIPE.json"
        checked(dict(path=str(contract_path), sha256=receipt["recipe_sha256"]))
        contract = read(contract_path)
        repo = Path(contract["source_repo"])
        for original, binding in receipt["source_snapshots"].items():
            source = Path(binding["snapshot"])
            checked(dict(path=str(source), sha256=binding["sha256"]))
            checked(dict(path=original, sha256=binding["sha256"]))
            if original in source_digests and source_digests[original] != binding["sha256"]:
                raise ValueError("Candidates executed different source versions")
            source_digests[original] = binding["sha256"]
            try:
                suffix = Path(original).relative_to(repo).as_posix()
            except ValueError:
                raise ValueError("An executed source is outside the declared source checkout")
            name = "historical_source/" + suffix
            add(name, source); origins[name] = dict(original=original, executed_snapshot=str(source), sha256=binding["sha256"])
        for name in ("RECEIPT.json", "RECIPE.json", "RECIPE_EARLY.json"):
            add("executed_cases/" + sid + "/" + name, receipt_path.parent / name)
        for stage in receipt["stages"]:
            add("executed_cases/" + sid + "/" + stage["id"] + "_generation.json",
                receipt_path.parent / "states" / stage["id"] / "generation.json")
        byte_entries["configuration/" + sid + "/design_recipe.json"] = (json.dumps(contract["recipe"], ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    for name in ALGORITHM_FILES:
        source = HERE / name
        if not source.is_file():
            raise FileNotFoundError(source)
        add("algorithms/" + name, source)
    add("algorithms/render_variations.py", HERE.parent / "early_dynamic_variations_20261016/render_variations.py")
    if sha(entries["algorithms/render_variations.py"]) != read(render_path)["renderer_sha256"]:
        raise ValueError("Archived renderer is not the executed source")
    add("evidence/INHERITED_EXPORT_AND_QA.json", qa_path)
    add("evidence/COMPARISON_RENDER_PLAN.json", plan_path)
    add("evidence/RENDER_RECEIPT.json", render_path)
    add("evidence/COLOR_PROOF.json", root / "actual_G2_change_colors/COLOR_PROOF.json")
    external = dict(original_SPAN_G0=read(qa_path)["original_input"],
                    original_stage_root=read(qa_path)["original_states"],
                    bindings_included_in_executed_case_recipes_and_generation_records=True,
                    excluded_assets="Original external SPAN/selected-recipe inputs, finite-field caches, native NPZ arrays and PLY models are not copied into this source ZIP.",
                    self_contained_full_replay=False)
    byte_entries["EXTERNAL_INPUTS.json"] = (json.dumps(external, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    text = (
        "기존 생성 규칙의 초기 G4 비교 — 알고리즘·실행 기록\n\n"
        "원본 SPAN G0와 기존 Task36 → 되접기 → WALL → ROOT/SIDEWALL → neutral CC 연산을 유지합니다. "
        "새 seed, CSG 형상, 외부 harmonic XYZ 변형 또는 후기 미세 장식을 추가하지 않습니다.\n\n"
        "재사용 코드: algorithms/regional_split_controls.py는 inherited material chart에서 기존 w3/w4/w1 계수만 고릅니다. "
        "replay_inherited.py는 Cheshire 원본 사슬용 실행 어댑터입니다. 전체 역사 소스는 historical_source/에 실행 당시 해시로 보존했습니다.\n\n"
        "이 ZIP은 알고리즘과 감사 기록 묶음입니다. 원래 SPAN 입력·선택 recipe 자산·Mandel finite-field cache는 외부 경로의 고정 자산이며, "
        "EXTERNAL_INPUTS.json 및 각 실행 RECIPE/generation 기록에 의존성이 있습니다. 독립 실행에 필요한 모든 자산을 포함했다고 주장하지 않습니다.\n\n"
        "환경: Python, NumPy, SciPy, Pillow. 렌더에는 Blender와 기존 실행 환경이 필요합니다.\n"
        "원본 자산이 준비된 환경에서의 명령 예:\n"
        "python -B algorithms/replay_inherited.py --recipe configuration/I01/design_recipe.json --output <새 폴더> --source-repo <원본 checkout>\n"
        "python -B algorithms/inspect_inherited.py --root <실험 variants> --output <새 models> --expected-count 7\n"
        "python -B algorithms/prepare_comparison.py --root <실험 root>\n"
        "blender --background --factory-startup --python algorithms/render_variations.py -- --plan <COMPARISON_RENDER_PLAN.json> --output <새 COMPARISON_RENDER>\n"
        "python -B algorithms/build_review.py --root <실험 root> --exports <models가 있는 exports>\n\n"
        "G4 회색은 실제 초기 형상입니다. G2 컬러는 I00와 동일한 재료 정점의 실제 좌표 차이를 각 quad 네 정점에서 평균해 표시합니다. "
        "전 안 공통 문턱은 0.01/0.05/0.15/0.35 모델 단위입니다. G4 변화 전체·곡률분류·최종 밀도를 뜻하지 않습니다. "
        "I05는 G3 뿌리 선택을 바꾸므로 G2가 회색인 것이 맞습니다.\n\n"
        "닫힘·방향·Euler2·반사·실제 계보·PLY 전체 재읽기를 검사했습니다. self-intersection, 제조 안정성 또는 미적 우승을 인증하지 않습니다. "
        "분할 face/edge coupling은 영역 밖 인접점에도 영향을 주므로 영역 밖 XYZ 불변을 주장하지 않습니다. "
        "원래 모델은 보존하며 사용자 채택 여부는 별도입니다.\n"
    )
    byte_entries["README_KO.txt"] = text.encode("utf-8")
    manifest = dict(kind="INHERITED_RULE_ALGORITHM_SOURCE_PACKAGE", files={}, executed_source_origins=origins,
                    historical_assets_included=False, standalone_full_replay_claimed=False,
                    no_native_NPZ_or_models_in_archive=True, user_adopted=False)
    for name, source in entries.items():
        if name.endswith((".npy", ".npz", ".ply")):
            raise ValueError("Large/native model asset cannot enter the source archive")
        manifest["files"][name] = dict(**record(source), bytes=source.stat().st_size)
    for name, content in byte_entries.items():
        manifest["files"][name] = dict(sha256=hashlib.sha256(content).hexdigest(), bytes=len(content), generated_package_text=True)
    target = out / "algorithm_source.zip"
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name, source in sorted(entries.items()):
            z.write(source, name)
        for name, content in sorted(byte_entries.items()):
            z.writestr(name, content)
        z.writestr("SOURCE_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:
            raise ValueError("Algorithm source archive CRC failed")
        for name, binding in manifest["files"].items():
            if hashlib.sha256(z.read(name)).hexdigest() != binding["sha256"]:
                raise ValueError("Algorithm archive member SHA differs")
        count = len(z.infolist())
    (out / "README_KO.txt").write_text(text, encoding="utf-8")
    write(out / "SOURCE_MANIFEST.json", manifest)
    return dict(**record(target), bytes=target.stat().st_size, archive_entries=count,
                CRC_passed=True, all_payload_member_SHA_passed=True, historical_external_assets_included=False)


HTML = r'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SPAN · 기존 규칙의 초기 형상 비교</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f4f1ea;color:#252c27;font:16px/1.65 "Malgun Gothic",sans-serif}main{max-width:1480px;margin:auto;padding:30px}h1{font-size:32px;line-height:1.3;margin:0 0 12px}h2{font-size:23px;margin:34px 0 12px}p{max-width:1080px}a{color:#27656a}button,select{font:inherit;border:1px solid #bbc2b9;background:#fff;padding:9px 13px;border-radius:8px}button{cursor:pointer}button.active{background:#31584d;color:#fff}.muted{font-size:14px;color:#616c63}.badge{display:inline-block;font-size:13px;background:#e2e8dd;padding:3px 8px;border-radius:6px}.tools{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:15px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:15px}.card,.compare article{background:#fff;border:1px solid #d8ded5;border-radius:13px;padding:13px}.card img{width:100%;height:320px;object-fit:contain;background:#eeede7}.card h3{margin:6px 0}.compare{display:grid;grid-template-columns:1fr 1fr;gap:16px}.compare img{width:100%;height:580px;object-fit:contain;background:#eeede7}.missing{padding:70px 15px;text-align:center;color:#6a7169}.legend{background:#e8e9df;padding:15px;border-radius:12px}.legend span{display:inline-block;margin:6px 15px 6px 0}.swatch{display:inline-block;width:16px;height:16px;border-radius:4px;vertical-align:middle;margin-right:7px}.board{width:100%;height:auto}.table{overflow-x:auto}table{border-collapse:collapse;width:100%;background:#fff}th,td{border-bottom:1px solid #dce1d8;text-align:left;padding:11px;vertical-align:top}th{white-space:nowrap;background:#e9ede4}summary{cursor:pointer;font-weight:bold}.links{display:flex;gap:15px;flex-wrap:wrap}.narrow{max-width:1080px}@media(max-width:700px){main{padding:18px}h1{font-size:27px}.compare{grid-template-columns:1fr}.compare img{height:440px}}</style></head><body><main>
<h1>같은 SPAN 입력, 기존 규칙 안에서 바꾼 초기 형상</h1><span class="badge">G4 초기 비교 · 사용자 채택 전</span>
<p>입력 형상과 생성 원리는 유지하고, 되접는 지점·구간·방향, 기존 분할의 배치, 뿌리와 측벽을 고르는 위치만 바꿨습니다. I00은 원래 설정을 그대로 다시 계산한 기준안입니다.</p>
<p class="muted">회색 이미지는 실제 G4 형상입니다. 같은 전체·상부 시점에서 비교하며, G5–G7이나 새 표면 장식은 추가하지 않았습니다.</p>
<div class="tools" id="viewButtons"><button class="active" data-view="whole">전체</button><button data-view="upper_same">같은 상부 시점</button></div><div class="grid" id="grid"></div>
<h2>기준안과 비교</h2><div class="tools"><label>왼쪽 <select id="left"></select></label><label>오른쪽 <select id="right"></select></label><select id="compareView"><option value="whole">G4 전체</option><option value="upper_same">G4 같은 상부 시점</option><option value="actual_change">G2 실제 좌표 변화</option></select></div><div class="compare" id="compare"></div>
<h2>어떤 설정을 바꿨나</h2><div class="table"><table><thead><tr><th>안</th><th>변경 내용</th><th>G2 최대 좌표 차이</th><th>실제 G4 삼각면</th><th>모델</th></tr></thead><tbody id="recipes"></tbody></table></div>
<h2>G2 색상 읽는 법</h2><p>같은 재료 정점에서 I00과의 실제 좌표 차이를 계산하고, 각 quad의 네 정점 평균을 색으로 표시했습니다. 모든 안에 같은 모델 단위 문턱을 씁니다. 곡률 분류나 최종 밀도, G4의 전체 변형량을 뜻하지 않습니다.</p>
<div class="legend" id="legend"></div><p class="muted">I05는 G3에서 뿌리·측벽 선택 위치를 바꿉니다. 그 이전 G2는 변하지 않아 색상 이미지가 회색인 것이 정상입니다.</p>
<details><summary>6개 안의 실제 G2 좌표 변화</summary><div class="grid" id="colors"></div></details>
<h2>한 장으로 비교</h2><a href="comparison_board.png"><img class="board" src="comparison_board.png" alt="I00부터 I06까지 같은 시점의 초기 G4 비교" loading="lazy"></a>
<h2>모델과 알고리즘</h2><div class="links"><a href="algorithm_source.zip">알고리즘·실행 기록 ZIP</a><a href="README_KO.txt">사용 안내</a><a href="../models/INHERITED_EXPORT_AND_QA.json">독립 형상 검사</a><a href="DELIVERY_MANIFEST.json">이미지·출력 기록</a></div>
<p class="muted narrow">닫힌 연결 구조, 양의 면적, 반사 대칭과 실제 부모·자식 계보를 검사한 비교 자료입니다. 교차·제조 안정성이나 미적 우승을 인증하지 않습니다. ZIP에는 코드와 실행 기록이 있으며 원본 입력·field cache 등 외부 자산이 별도로 필요합니다. 기존 결과는 변경하지 않았습니다.</p>
</main><script type="application/json" id="data">__DATA__</script><script>
const data=JSON.parse(document.querySelector('#data').textContent),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let view='whole';
const picture=(m,v)=>m.images[v]?`<a href="${esc(m.images[v].url)}"><img src="${esc(m.images[v].url)}" alt="${esc(m.id+' '+v)}" loading="lazy"></a>`:'<div class="missing">I00은 G2 좌표 차이를 계산하는 기준안입니다.</div>';
const title=m=>m.id+' · '+m.label;
function grid(){document.querySelector('#grid').innerHTML=data.models.map(m=>`<article class="card">${picture(m,view)}<h3>${esc(title(m))}</h3><p class="muted">${esc(m.summary)}</p><a href="${esc(m.ply)}">PLY 모델</a></article>`).join('')}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{view=b.dataset.view;document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x===b));grid()});
for(const id of ['left','right']){document.querySelector('#'+id).innerHTML=data.models.map(m=>`<option value="${esc(m.id)}">${esc(title(m))}</option>`).join('');document.querySelector('#'+id).value=data.default_comparison[id]}
function compare(){let v=document.querySelector('#compareView').value;document.querySelector('#compare').innerHTML=['left','right'].map(id=>{let m=data.models.find(m=>m.id===document.querySelector('#'+id).value);return `<article><h3>${esc(title(m))}</h3>${picture(m,v)}<p>${esc(m.summary)}</p><a href="${esc(m.ply)}">PLY 모델</a></article>`}).join('')}
for(const id of ['left','right','compareView'])document.querySelector('#'+id).onchange=compare;
document.querySelector('#recipes').innerHTML=data.models.map(m=>`<tr><td>${esc(title(m))}</td><td>${esc(m.summary)}</td><td>${m.G2_maximum_distance.toFixed(5)}</td><td>${m.triangles.toLocaleString()}</td><td><a href="${esc(m.ply)}">PLY</a></td></tr>`).join('');
document.querySelector('#legend').innerHTML=data.legend.map(r=>`<span><i class="swatch" style="background:rgb(${r.rgb.map(v=>Math.round(v*255)).join(',')})"></i>${esc(r.name)}<br><small>${esc(r.interval)}</small></span>`).join('');
document.querySelector('#colors').innerHTML=data.models.filter(m=>m.images.actual_change).map(m=>`<article class="card"><h3>${esc(title(m))}</h3>${picture(m,'actual_change')}</article>`).join('');grid();compare();
</script></body></html>'''


def main(a):
    started = time.perf_counter()
    qa_path = a.exports / "models/INHERITED_EXPORT_AND_QA.json"
    qa = read(qa_path)
    if qa.get("passed") is not True or qa.get("all_exported_geometry_full_readback_exact") is not True or qa.get("completed_count") != 7:
        raise ValueError("Seven actual independently inspected/readback-exported candidates are required")
    models = {r["id"]: r for r in qa["variants"]}
    if set(models) != set(IDS) or len(models) != len(qa["variants"]):
        raise ValueError("I00 through I06 must exist exactly once")
    plan_path, render_path = a.root / "COMPARISON_RENDER_PLAN.json", a.root / "COMPARISON_RENDER/RENDER_RECEIPT.json"
    plan, render = read(plan_path), read(render_path)
    if render["plan_sha256"] != sha(plan_path):
        raise ValueError("Render receipt does not bind the saved comparison plan")
    for sid, row in models.items():
        checked(row["model"])
        checked(row["source_receipt"])
        if not row["quality"]["passed"] or row["original_SPAN_G0_all_three_arrays_byte_exact"] is not True:
            raise ValueError("Required original-input/native inspection did not pass")
    images, render_checks = bind_images(a.root, models, plan, render)
    out = a.exports / "REVIEW"
    if out.exists():
        raise FileExistsError("Preserve existing review; choose a fresh export root")
    out.mkdir(parents=True); (out / "images").mkdir(); (out / "receipts").mkdir()
    presentation, copied = {}, []
    for sid, row in sorted(models.items()):
        recipe = row["allowed_settings"]["requested_settings"]
        views = {}
        for view, im in images[sid].items():
            if not re.fullmatch(r"[A-Za-z0-9_-]+", view):
                raise ValueError("Unsafe view identifier")
            target = out / "images" / (sid + "__" + view + ".png")
            shutil.copyfile(im["path"], target)
            checked(dict(path=str(target), sha256=im["sha256"]))
            views[view] = dict(url=rel(target, out), sha256=im["sha256"], size=im["size"])
            copied.append(dict(id=sid, view=view, source=im["path"], **record(target)))
        label = recipe.get("label_ko", sid)
        if "?" in label or "\ufffd" in label:
            raise ValueError("The actual recipe label has damaged Unicode")
        presentation[sid] = dict(id=sid, label=label, summary=recipe_text(recipe),
                                 triangles=row["quality"]["triangles"],
                                 G2_maximum_distance=row["G2_paired_material_displacement_quantiles"][-1],
                                 ply=rel(row["model"]["path"], out), images=views)
    board_record = board(presentation, images, out / "comparison_board.png")
    selection_path = a.root / "SELECTION.json"
    default_right = "I01"
    if selection_path.exists():
        selection = read(selection_path)
        candidates = selection.get("preferred_candidates", selection.get("ids", []))
        if any(sid not in models for sid in candidates):
            raise ValueError("Selection contains an unknown actual candidate")
        default_right = selection.get("default_compare", next((sid for sid in candidates if sid != "I00"), "I01"))
        if default_right not in models:
            raise ValueError("Default comparison must refer to an actual exported model")
    payload = dict(models=list(presentation.values()), legend=LEGEND,
                   default_comparison=dict(left="I00", right=default_right),
                   user_adopted=False, default_comparison_is_not_aesthetic_selection=True)
    write(out / "review_data.json", payload)
    page = out / "review.html"
    page.write_text(HTML.replace("__DATA__", json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")), encoding="utf-8")
    archive = code_bundle(out, models, a.root, qa_path, plan_path, render_path)
    for name, source in (("EXPORT_QA.json", qa_path), ("RENDER_RECEIPT.json", render_path),
                         ("COMPARISON_RENDER_PLAN.json", plan_path),
                         ("COLOR_PROOF.json", a.root / "actual_G2_change_colors/COLOR_PROOF.json")):
        shutil.copyfile(source, out / "receipts" / name)
    # Resolve every actual model/image link and the fixed product links locally.
    links = [row["ply"] for row in presentation.values()]
    links += [im["url"] for row in presentation.values() for im in row["images"].values()]
    links += ["comparison_board.png", "algorithm_source.zip", "README_KO.txt", "../models/INHERITED_EXPORT_AND_QA.json"]
    if not all((out / link).resolve().is_file() for link in links):
        raise ValueError("A gallery asset/model link does not resolve")
    manifest = dict(schema="CHESHIRE_INHERITED_RULE_REVIEW_DELIVERY_V1", passed=True,
                    model_count=7, rendered_image_count=len(copied), gallery=record(page),
                    comparison_board=board_record, algorithm_source_archive=archive,
                    export_QA=record(qa_path), render_receipt=record(render_path), render_plan=record(plan_path),
                    selection=record(selection_path) if selection_path.exists() else None,
                    independent_render_and_color_checks=render_checks,
                    models=[dict(id=sid, model=row["model"], source_receipt=row["source_receipt"]) for sid, row in sorted(models.items())],
                    copied_actual_images=copied, all_relative_asset_and_model_links_resolve=True,
                    source=record(__file__), user_adopted=False, aesthetic_success_claimed=False,
                    initial_G4_only=True, original_G0_fixed=True, same_existing_operators=True,
                    G2_colors_are_actual_coordinate_delta_not_segmentation_or_final_density=True,
                    original_inputs_or_models_modified=False, geometry_smoothing_applied=False,
                    smooth_normals_display_only=True, historical_external_assets_included=False,
                    self_intersection_or_manufacturing_certified=False,
                    elapsed_seconds=time.perf_counter() - started)
    write(out / "DELIVERY_MANIFEST.json", manifest)
    print("INHERITED_REVIEW_READY", page, sha(page), archive["sha256"], flush=True)
    return manifest


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--exports", type=Path, required=True)
    main(p.parse_args())
