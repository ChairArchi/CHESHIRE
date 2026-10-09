"""Identity and framing checks at the independent file boundary."""
import hashlib
import json
import pytest
from cheshire.gate_exchange import load_gate_input, ROTATION


def exchange(root):
    # One oriented triangle; importer does not require a fabricated closed solid.
    data = b"v 0 0 0\nv 2 0 0\nv 0 0 1\nf 1 2 3\n"
    (root / "mesh.obj").write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    record = dict(schema="alice-cheshire-gate/1", input_id=sha,
                  source=dict(file="gate.glb", sha256="a" * 64, revision="b" * 40),
                  mesh=dict(file="mesh.obj", sha256=sha, vertices=3, faces=1),
                  frame=dict(source_axes="X_RIGHT_Y_UP_Z_BACK", axes="X_RIGHT_Y_FRONT_Z_UP",
                             rotation=ROTATION, scale=2), unit="design_unit", parameters={},
                  semantics=dict(support_left=None, support_right=None, upper=None, openings=None))
    return record


def save(root, record):
    (root / "manifest.json").write_text(json.dumps(record), encoding="utf-8")


def test_preserves_geometry_winding_and_unknown_semantics(tmp_path):
    record = exchange(tmp_path); save(tmp_path, record)
    mesh, manifest = load_gate_input(tmp_path)
    assert mesh.vertex_coordinates(1) == [2, 0, 0]
    assert mesh.face_vertices(0) == [0, 1, 2]
    assert manifest["semantics"]["openings"] is None


def test_rejects_tampered_mesh(tmp_path):
    save(tmp_path, exchange(tmp_path))
    with (tmp_path / "mesh.obj").open("ab") as stream:
        stream.write(b"v 1 1 1\n")
    with pytest.raises(ValueError, match="hash"):
        load_gate_input(tmp_path)


@pytest.mark.parametrize("change", ["path", "axes", "scale", "unit", "region", "opening", "parameter", "revision", "missing", "count"])
def test_rejects_ambiguous_or_invalid_handoff(tmp_path, change):
    record = exchange(tmp_path)
    if change == "path": record["mesh"]["file"] = "../outside.obj"
    if change == "axes": record["frame"]["axes"] = "Y_UP"
    if change == "scale": record["frame"]["scale"] = -1
    if change == "unit": record["unit"] = "UNRESOLVED"
    if change == "region": record["semantics"]["upper"] = [1]
    if change == "opening": record["semantics"]["openings"] = [dict(bounds=[[0, 0, 0], [1, 0, 1]])]
    if change == "parameter": record["parameters"]["strength"] = float("nan")
    if change == "revision": record["source"]["revision"] = "unknown"
    if change == "missing": del record["semantics"]["upper"]
    if change == "count": record["mesh"]["faces"] = True
    save(tmp_path, record)
    with pytest.raises(ValueError): load_gate_input(tmp_path)
