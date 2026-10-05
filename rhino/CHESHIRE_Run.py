#! python 3
"""Rhino 8 entry point: select/display here, calculate in CHESHIRE's .venv."""

import json
from math import hypot, isfinite
from pathlib import Path
import queue
import subprocess
import sys
import threading
from time import monotonic
from uuid import uuid4

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import Eto.Forms as Forms
import Rhino
from System import Guid
from System.Drawing import Color
from exchange import (
    MAX_INPUT_FACES, MAX_INPUT_VERTICES, MOLA_MODE, MOLA_FIELD_MODE, MOLA_SURFACE_MODE, VISUAL_MODE, TIMEOUT_SECONDS, face_driver_display_data, read_json,
    validate_mesh_data, validate_request, validate_response, write_json_atomic,
)
from worker_process import worker_launch_options
from local_settings import remembered_mola_path, remember_mola_path


_RUNS = {}  # Keep this script's timer/callback alive after ScriptEditor returns.


def rhino_mesh_to_data(mesh):
    if not isinstance(mesh, Rhino.Geometry.Mesh):
        raise ValueError("Select an existing Rhino Mesh; Brep and SubD meshing is not supported.")
    if mesh.Ngons.Count:
        raise ValueError("Ngon groups are not supported by this triangle/quad demo; no automatic conversion is performed.")
    if mesh.Vertices.Count > MAX_INPUT_VERTICES or mesh.Faces.Count > MAX_INPUT_FACES:
        raise ValueError("Input exceeds the demo limit: 20,000 vertices / 5,000 faces.")
    # Raw vertex indices, never Rhino topology vertices (which can merge
    # coincident identities). Point3dAt reads existing double coordinates.
    vertices = []
    for index in range(mesh.Vertices.Count):
        point = mesh.Vertices.Point3dAt(index)
        vertices.append({"id": index, "xyz": [point.X, point.Y, point.Z]})
    faces = []
    for index in range(mesh.Faces.Count):
        face = mesh.Faces[index]
        corners = [face.A, face.B, face.C] if face.IsTriangle else [face.A, face.B, face.C, face.D]
        faces.append({"id": index, "vertices": corners})
    return validate_mesh_data({"vertices": vertices, "faces": faces}, MAX_INPUT_VERTICES, MAX_INPUT_FACES)


def data_to_rhino_mesh(data, x_offset=0.0, values=None):
    validate_mesh_data(data)
    mesh = Rhino.Geometry.Mesh()
    mesh.Vertices.UseDoublePrecisionVertices = True
    indices = {}
    for row in data["vertices"]:
        x, y, z = row["xyz"]
        if not isfinite(x + x_offset):
            raise ValueError("Display offset would produce non-finite geometry.")
        indices[row["id"]] = mesh.Vertices.Add(Rhino.Geometry.Point3d(x + x_offset, y, z))
    for row in data["faces"]:
        mesh.Faces.AddFace(*[indices[key] for key in row["vertices"]])
    if values is not None:
        for row in data["vertices"]:
            value = values[row["id"]]
            gray = int(round(value * 255)) if value is not None else None
            mesh.VertexColors.Add(Color.Magenta if gray is None else Color.FromArgb(gray, gray, gray))
    mesh.Normals.ComputeNormals()
    # Rhino uses dense list indices; explicit mappings retain calculation IDs.
    mesh.SetUserString("CHESHIRE vertex_ids", json.dumps([row["id"] for row in data["vertices"]]))
    mesh.SetUserString("CHESHIRE face_ids", json.dumps([row["id"] for row in data["faces"]]))
    return mesh


def source_fingerprint(doc, source):
    options = Rhino.FileIO.SerializationOptions()
    options.WriteUserData = True
    layer = doc.Layers[source.Attributes.LayerIndex]
    layers = []
    while layer is not None:
        layers.append(layer.ToJSON(options))
        layer = None if layer.ParentLayerId == Guid.Empty else doc.Layers.FindId(layer.ParentLayerId)
    return (source.RuntimeSerialNumber, source.Geometry.DataCRC(0), source.Attributes.ToJSON(options),
            source.IsHidden, source.IsLocked, tuple(layers), int(doc.ModelUnitSystem), doc.ModelAbsoluteTolerance)


def print_steps(response):
    if response.get("mode") == VISUAL_MODE:
        Rhino.RhinoApp.WriteLine("VISUAL_PROTOTYPE " + response["status"] + ": " + (response.get("reason") or "Three fixed spatial candidates completed."))
        for row in response["variants"]:
            Rhino.RhinoApp.WriteLine(f"{row['label']} {row['status']}: {row['vertex_count']} vertices / {row['face_count']} faces; "
                f"{row.get('elapsed_seconds', 0):.3f}s; semantic lineage {row['semantic_lineage']}.")
            Rhino.RhinoApp.WriteLine(row["recipe"]["layout"])
            if row.get("reason"):
                Rhino.RhinoApp.WriteLine(row["reason"])
            excluded = sum(len(step["excluded_selected_faces"]) for step in row["steps"])
            if excluded:
                Rhino.RhinoApp.WriteLine(f"{excluded} proposed faces excluded explicitly for unsupported geometry; reasons in response.json.")
        for row in response["attempts"]:
            if row["status"] == "FAILED":
                Rhino.RhinoApp.WriteLine(f"{row['id']} unavailable: {row['reason']}")
        Rhino.RhinoApp.WriteLine("Compare structure and detail in Shaded/Wireframe. Tests do not establish visual success or collision freedom.")
        return
    if response.get("mode") == MOLA_SURFACE_MODE:
        Rhino.RhinoApp.WriteLine("MOLA_SURFACE_STUDY " + response["status"] + ": " + (response.get("reason") or "G1/G3 raw and CC1 comparisons completed."))
        for row in response["derivatives"]:
            label = f"G{row['source_generation']} + CATMULL-CLARK 1"
            if row["status"] != "SUCCESS":
                Rhino.RhinoApp.WriteLine(label + " " + row["status"] + ": " + row["reason"])
                continue
            before, after = row["input"], row["output"]
            Rhino.RhinoApp.WriteLine(f"{label}: {before['vertex_count']}/{before['face_count']} -> "
                f"{after['vertex_count']}/{after['face_count']} vertices/faces; {row['elapsed_seconds']:.3f}s; budget {row['budget']['status']}.")
            Rhino.RhinoApp.WriteLine(f"BBox XYZ: {before['bounding_box']} -> {after['bounding_box']}; "
                f"retained vertex displacement {row['retained_vertex_displacement']} (model units).")
            Rhino.RhinoApp.WriteLine(f"Boundary {row['boundary_preservation']['status']}: fixed {row['fixed_vertex_count']} vertices, "
                f"creased {row['creased_edge_count']} edges at 2; components {row['components_before']} -> {row['components_after']}.")
        Rhino.RhinoApp.WriteLine("Terminal geometry comparisons; semantic lineage NOT IMPLEMENTED. Raw fields/roles/lineage retained in JSON.")
        return
    if response.get("mode") == MOLA_FIELD_MODE:
        reason = response.get("reason")
        if response["status"] == "PARTIAL":
            summary = f"Last completed generation: G{response['stages'][-1]['generation']} (PARTIAL)."
            if reason:
                summary += " " + reason
        elif response["status"] == "SUCCESS":
            summary = reason or "G1/G2/G3 cap recursion completed."
        else:
            summary = reason or "No completed generation."
        Rhino.RhinoApp.WriteLine("MOLA_FIELD_STUDY " + response["status"] + ": " + summary)
        Rhino.RhinoApp.WriteLine(f"Eligible original faces {len(response['eligible_faces'])}; excluded {len(response['excluded_faces'])}; height in input document units.")
        for warning in response["drivers"].get("warnings") or []:
            Rhino.RhinoApp.WriteLine(warning)
        for stage in response["stages"]:
            Rhino.RhinoApp.WriteLine("G{generation}: processed {processed_face_count} faces ({caps_processed} caps); "
                "{input_vertex_count}/{input_face_count} -> {vertex_count}/{face_count} vertices/faces; "
                "{elapsed_seconds:.3f}s".format(**stage))
            Rhino.RhinoApp.WriteLine(f"Height driver {stage['height_driver_range']}; taper driver {stage['taper_driver_range']}; "
                f"actual height {stage['height_range']}; fraction {stage['fraction_range']}; budget {stage['budget']['status']}.")
        top_five = response.get("top_five_g1") or []
        if top_five:
            Rhino.RhinoApp.WriteLine("Five original faces with greatest G1 height:")
        for row in top_five:
            Rhino.RhinoApp.WriteLine("Face {root_face}: height driver {height_driver:g}, taper driver {taper_driver:g}, "
                                    "height {height:g}, fraction {fraction:g}".format(**row))
        assessment = response.get("variation_assessment")
        if isinstance(assessment, str) and assessment:
            Rhino.RhinoApp.WriteLine(assessment)
        return
    if response.get("mode") == MOLA_MODE:
        Rhino.RhinoApp.WriteLine("MOLA_TAPER_STUDY " + response["status"] + ": " + (response.get("reason") or "A/B/C completed."))
        Rhino.RhinoApp.WriteLine(f"Selected {len(response['selected_faces'])}; excluded {len(response['excluded_faces'])}; height in input document coordinate units.")
        for variant in response["variants"]:
            heights = [row["height"] for row in variant["parameters"]]
            Rhino.RhinoApp.WriteLine("{name}: height ratio {height_ratio:g}, fraction {fraction:g}; {vertex_count} vertices / {face_count} faces; {elapsed_seconds:.3f}s".format(**variant))
            Rhino.RhinoApp.WriteLine("Actual height range: " + (f"{min(heights):g} .. {max(heights):g}" if heights else "none (empty selection)"))
        if response["variants"] and response["variants"][0]["backend"]:
            backend = response["variants"][0]["backend"]
            Rhino.RhinoApp.WriteLine("Mola: " + backend["assembly"] + "; CoreCLR " + backend["runtime"] + "; " + backend["dll_path"])
        Rhino.RhinoApp.WriteLine("Full parameters, exclusions, roles and lineage are in response.json. No global collision guarantee.")
        return
    Rhino.RhinoApp.WriteLine("CHESHIRE " + response["status"] + ": " + (response.get("reason") or "Four recipe applications completed."))
    for stage in response["stages"]:
        Rhino.RhinoApp.WriteLine(
            "G{generation}: {vertex_count} vertices / {face_count} faces; field [{field_min}, {field_max}]; "
            "unavailable {unavailable_count}; moved {moved_count}, selected skips {skipped_count}, "
            "not selected {not_selected_count}; strength {effective_strength:g}; max displacement {maximum_displacement:g}; "
            "{elapsed_seconds:.3f}s".format(**stage))
        if stage["notice"]:
            Rhino.RhinoApp.WriteLine(stage["notice"])
    Rhino.RhinoApp.WriteLine("Movement may be visually subtle. This is an experimental recipe, not finished ornament.")


def insert_results(doc, request, response):
    """UI-thread insertion with one undo record and run-local failure rollback."""
    if response.get("mode") == VISUAL_MODE:
        items = [("ORIGINAL REFERENCE", request["mesh"], None)]
        for row in response["variants"]:
            label = row["label"] + (" (last valid; PARTIAL)" if row["status"] != "SUCCESS" else "")
            items.append((label, row["mesh"], None))
    elif response.get("mode") == MOLA_SURFACE_MODE:
        items = [("ORIGINAL REFERENCE", request["mesh"], None)]
        stages = {stage["generation"]: stage for stage in response["stages"]}
        for row in response["derivatives"]:
            generation = row["source_generation"]
            if generation in stages:
                label = f"G{generation} RAW"
                if row["status"] != "SUCCESS":
                    label += f" (CC1 {row['status']})"
                items.append((label, stages[generation]["mesh"], None))
            if row["status"] == "SUCCESS":
                items.append((f"G{generation} + CATMULL-CLARK 1", row["mesh"], None))
    elif response.get("mode") == MOLA_FIELD_MODE:
        items = [("ORIGINAL REFERENCE", request["mesh"], None)]
        for name, label in (("height_driver", "HEIGHT DRIVER"), ("taper_driver", "TAPER DRIVER")):
            data, values, _ = face_driver_display_data(request["mesh"], response["drivers"]["faces"], name)
            items.append((label, data, values))
        for stage in response["stages"]:
            label = "G1 - heterogeneous taper extrusion" if stage["generation"] == 1 else f"G{stage['generation']} - cap recursion"
            if response["status"] == "PARTIAL" and stage is response["stages"][-1]:
                label += " (last valid; PARTIAL)"
            items.append((label, stage["mesh"], None))
    elif response.get("mode") == MOLA_MODE:
        selected = set(response["selected_faces"])
        preview = {"vertices": request["mesh"]["vertices"],
                   "faces": [row for row in request["mesh"]["faces"] if row["id"] in selected]}
        items = [("ORIGINAL REFERENCE", request["mesh"], None),
                 ("SELECTED FACE PREVIEW" if selected else "SELECTED FACE PREVIEW (none; original shown)",
                  preview if selected else request["mesh"], None)]
        for variant in response["variants"]:
            items.append(("{name} - height {height_ratio:g}, taper {fraction:g}".format(**variant), variant["mesh"], None))
    else:
        items = [("ORIGINAL REFERENCE", request["mesh"], None),
             (response["driver"]["label"], response["driver"]["mesh"],
              {row["id"]: row["value"] for row in response["driver"]["values"]})]
        stages = response["stages"]
        for stage in stages:
            generation = stage["generation"]
            if generation in (1, 2, 4) or stage is stages[-1]:
                items.append((f"G{generation}" + (" (last valid; PARTIAL)" if response["status"] == "PARTIAL" and stage is stages[-1] else ""), stage["mesh"], None))
    all_xyz = [row["xyz"] for _, data, _ in items for row in data["vertices"]]
    dimensions = [max(point[axis] for point in all_xyz) - min(point[axis] for point in all_xyz) for axis in range(3)]
    diagonal = hypot(*dimensions)
    spacing = dimensions[0] + diagonal * 0.35
    if not isfinite(spacing) or spacing <= 0:
        raise ValueError("Cannot represent a safe X-only comparison spacing.")
    root_name = "CHESHIRE_" + request["run_id"]
    created_objects, created_layers = [], []
    undo = doc.BeginUndoRecord("CHESHIRE " + request.get("mode", "mesh-grammar experiment"))
    if not undo:
        raise ValueError("Could not begin an undoable insertion; no results added.")
    try:
        parent = Rhino.DocObjects.Layer()
        parent.Name = root_name
        parent_index = doc.Layers.Add(parent)
        if parent_index < 0:
            raise ValueError("Could not create this run's layer.")
        created_layers.append(parent_index)
        for position, (label, data, values) in enumerate(items, 1):
            layer = Rhino.DocObjects.Layer()
            layer.Name = "G1 DRIVER FIELD" if values is not None and response.get("mode") != MOLA_FIELD_MODE else label
            layer.ParentLayerId = doc.Layers[parent_index].Id
            layer_index = doc.Layers.Add(layer)
            if layer_index < 0:
                raise ValueError("Could not create result layer.")
            created_layers.append(layer_index)
            attrs = Rhino.DocObjects.ObjectAttributes()
            attrs.LayerIndex, attrs.Name = layer_index, label
            attrs.SetUserString("CHESHIRE run_id", request["run_id"])
            attrs.SetUserString("CHESHIRE source_object", request["source"]["object_id"])
            task = {MOLA_MODE: "task09", MOLA_FIELD_MODE: "task10", MOLA_SURFACE_MODE: "task11", VISUAL_MODE: "task12"}.get(request.get("mode"), "task08")
            attrs.SetUserString("CHESHIRE results_file", str(ROOT / "output" / task / request["run_id"] / "response.json"))
            display = data_to_rhino_mesh(data, position * spacing, values)
            if response.get("mode") == MOLA_FIELD_MODE and values is not None:
                _, _, source_ids = face_driver_display_data(request["mesh"], response["drivers"]["faces"],
                    "height_driver" if label == "HEIGHT DRIVER" else "taper_driver")
                display.SetUserString("CHESHIRE original_vertex_ids", json.dumps(source_ids))
                display.SetUserString("CHESHIRE display_only", "Duplicated corners for exact per-face color; calculation topology unchanged.")
            object_id = doc.Objects.AddMesh(display, attrs)
            if object_id == Guid.Empty:
                raise ValueError("Rhino refused a result mesh.")
            created_objects.append(object_id)
            xyz = [row["xyz"] for row in data["vertices"]]
            dot = Rhino.Geometry.TextDot(label, Rhino.Geometry.Point3d(
                min(point[0] for point in xyz) + position * spacing,
                min(point[1] for point in xyz) - diagonal * 0.12, min(point[2] for point in xyz)))
            dot_id = doc.Objects.AddTextDot(dot, attrs)
            if dot_id == Guid.Empty:
                raise ValueError("Rhino refused a comparison label.")
            created_objects.append(dot_id)
    except Exception:
        for object_id in reversed(created_objects):
            doc.Objects.Delete(object_id, True)
        for layer_index in reversed(created_layers):
            doc.Layers.Delete(layer_index, True)
        raise
    finally:
        doc.EndUndoRecord(undo)
        doc.Views.Redraw()
    return created_objects


class Run:
    """One subprocess, one UI timer and one cancellation event; no host wait."""

    def __init__(self, doc, source, strength=None, mode="MESH_GRAMMAR", mola_dll=None):
        self.serial, self.object_id = doc.RuntimeSerialNumber, source.Id
        self.fingerprint = source_fingerprint(doc, source)
        payload = {"protocol": 1, "run_id": str(uuid4()),
                                        "source": {"document_serial": self.serial, "object_id": str(source.Id)},
                                        "mode": mode, "mesh": rhino_mesh_to_data(source.Geometry)}
        if mode in (MOLA_MODE, MOLA_FIELD_MODE, MOLA_SURFACE_MODE, VISUAL_MODE):
            payload.update(mola_dll=mola_dll, selected_faces="ALL_ELIGIBLE_PLANAR")
        else:
            payload["strength"] = strength
        self.request = validate_request(payload)
        self.directory = ROOT / "output" / {MOLA_MODE: "task09", MOLA_FIELD_MODE: "task10", MOLA_SURFACE_MODE: "task11", VISUAL_MODE: "task12"}.get(mode, "task08") / self.request["run_id"]
        self.directory.mkdir(parents=True, exist_ok=False)
        write_json_atomic(self.directory / "request.json", self.request)
        self.cancel = threading.Event()
        self.completion = queue.Queue()
        self.timer = Forms.UITimer()
        self.timer.Interval = 0.2
        self.timer.Elapsed += self.on_tick

    def start(self):
        executable = ROOT / ".venv/Scripts/python.exe"
        if not executable.is_file():
            raise ValueError("CHESHIRE .venv missing. Follow the repository setup instructions first.")
        _RUNS[self.request["run_id"]] = self
        Rhino.RhinoApp.EscapeKeyPressed += self.on_escape
        self.timer.Start()
        threading.Thread(target=self.calculate, daemon=True).start()
        Rhino.RhinoApp.WriteLine("CHESHIRE running; Rhino remains available. Press Esc to cancel this run.")

    def on_escape(self, sender, event):
        self.cancel.set()

    def calculate(self):
        process = None
        try:
            with (self.directory / "worker_stdout.txt").open("w", encoding="utf-8") as stdout, \
                 (self.directory / "worker_stderr.txt").open("w", encoding="utf-8") as stderr:
                start = monotonic()
                process = subprocess.Popen(
                    **worker_launch_options(ROOT, self.directory / "request.json", self.directory / "response.json"),
                    stdout=stdout, stderr=stderr)
                stopped = None
                while process.poll() is None:
                    if self.cancel.is_set() or monotonic() - start >= TIMEOUT_SECONDS:
                        stopped = "CANCELLED" if self.cancel.is_set() else "TIMEOUT"
                        process.kill()  # Only this explicitly launched worker; no process-tree/global kill.
                        process.wait()
                        break
                    try:
                        process.wait(timeout=0.1)
                    except subprocess.TimeoutExpired:
                        pass
            if stopped == "CANCELLED":
                self.completion.put((None, "Cancelled; no document results added. Completed checkpoints remain in this run's directory."))
                return
            path = self.directory / "response.json"
            if not path.is_file():
                tail = "\n".join((self.directory / "worker_stderr.txt").read_text(encoding="utf-8", errors="replace").splitlines()[-8:])
                raise ValueError(f"Worker returned no matching response (exit {process.returncode}, {stopped or 'no checkpoint'}).\n{tail}")
            response = validate_response(read_json(path), self.request)
            if stopped == "TIMEOUT" or process.returncode != 0:
                response["status"] = "PARTIAL" if response.get("variants", response.get("stages", [])) else "FAILED"
                response["reason"] = f"Worker {stopped or ('exited ' + str(process.returncode))}; retaining only validated completed stages."
                write_json_atomic(path, response)
            self.completion.put((response, None))
        except Exception as error:
            self.completion.put((None, str(error)))
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait()

    def on_tick(self, sender, event):
        try:
            # Eto UITimer's callback executes on the UI thread. Never read or
            # insert Rhino document objects on the subprocess-waiting thread.
            doc = Rhino.RhinoDoc.FromRuntimeSerialNumber(self.serial)
            active = Rhino.RhinoDoc.ActiveDoc
            if doc is None or active is None or active.RuntimeSerialNumber != self.serial:
                self.cancel.set()
            try:
                response, error = self.completion.get_nowait()
            except queue.Empty:
                return
            self.timer.Stop()
            Rhino.RhinoApp.EscapeKeyPressed -= self.on_escape
            _RUNS.pop(self.request["run_id"], None)
            if error:
                Rhino.RhinoApp.WriteLine("CHESHIRE: " + error)
                Rhino.RhinoApp.WriteLine("Run logs/checkpoints: " + str(self.directory))
                return
            if self.cancel.is_set():
                Rhino.RhinoApp.WriteLine("CHESHIRE cancelled or initiating document changed; results not inserted.")
                return
            source = doc.Objects.FindId(self.object_id)
            if source is None or source_fingerprint(doc, source) != self.fingerprint:
                Rhino.RhinoApp.WriteLine("CHESHIRE source object, attributes, layer, visibility or units changed; results not inserted.")
                return
            runtime = response["runtime_identity"]
            Rhino.RhinoApp.WriteLine("Worker Python: " + runtime["executable"] + " | " + runtime["version"].splitlines()[0])
            Rhino.RhinoApp.WriteLine("Worker stdlib: re=" + runtime["re_file"] + "; pathlib=" + runtime["pathlib_file"])
            Rhino.RhinoApp.WriteLine("CHESHIRE package: " + runtime["cheshire_file"])
            print_steps(response)
            if response.get("variants", response.get("stages", [])):
                insert_results(doc, self.request, response)
                Rhino.RhinoApp.WriteLine("Results translated along world X on a new CHESHIRE run layer; original preserved.")
                if response.get("mode") == MOLA_FIELD_MODE:
                    Rhino.RhinoApp.WriteLine("Height and taper drivers: black=low, white=high, magenta=excluded. Original face values; Shaded mode shows colors.")
                elif response.get("mode") in (MOLA_SURFACE_MODE, VISUAL_MODE):
                    Rhino.RhinoApp.WriteLine("Compare Shaded and Wireframe manually; no global display mode changed. CC1 outputs are terminal geometry only.")
                elif response.get("mode") != MOLA_MODE:
                    Rhino.RhinoApp.WriteLine("Driver: black=0, white=1, magenta=unavailable. Use Shaded mode to see mesh vertex colors; no display mode was changed.")
            Rhino.RhinoApp.WriteLine("Run files: " + str(self.directory))
        except Exception as error:
            self.cancel.set()
            self.timer.Stop()
            Rhino.RhinoApp.EscapeKeyPressed -= self.on_escape
            _RUNS.pop(self.request["run_id"], None)
            Rhino.RhinoApp.WriteLine("CHESHIRE insertion stopped: " + str(error))


def mola_dll_path(replace=False):
    saved = remembered_mola_path(ROOT)
    if saved and not replace:
        Rhino.RhinoApp.WriteLine("Using saved Mola DLL: " + saved)
        return saved
    path = Rhino.Input.Custom.GetString()
    path.SetCommandPrompt("Exact full path to official standalone HDMola.dll (saved locally, outside CHESHIRE)")
    if saved:
        path.SetDefaultString(saved)
    path.Get()
    if path.CommandResult() != Rhino.Commands.Result.Success:
        return None
    return remember_mola_path(ROOT, path.StringResult().strip().strip('"'))


def main():
    if Rhino.RhinoApp.InvokeRequired:
        raise ValueError("Run this entry point on Rhino's UI thread; do not enable async:true in ScriptEditor.")
    doc = Rhino.RhinoDoc.ActiveDoc
    if doc is None:
        Rhino.RhinoApp.WriteLine("Open a Rhino document containing an existing Mesh first.")
        return
    selection = Rhino.Input.Custom.GetObject()
    selection.SetCommandPrompt("Select one existing Mesh for CHESHIRE (no Brep/SubD conversion)")
    selection.SubObjectSelect = False
    selection.Get()
    if selection.CommandResult() != Rhino.Commands.Result.Success:
        return
    source = selection.Object(0).Object()
    try:
        rhino_mesh_to_data(source.Geometry)
        choice = Rhino.Input.Custom.GetOption()
        choice.SetCommandPrompt("CHESHIRE experiment mode")
        grammar = choice.AddOption("MeshGrammar")
        mola = choice.AddOption("MolaTaperStudy")
        field = choice.AddOption("MolaFieldStudy")
        surface = choice.AddOption("MolaSurfaceStudy")
        prototype = choice.AddOption("VisualPrototype")
        dll_option = choice.AddOption("SetMolaDllPath")
        choice.Get()
        if choice.CommandResult() != Rhino.Commands.Result.Success:
            return
        if choice.OptionIndex() == dll_option:
            if mola_dll_path(replace=True):
                Rhino.RhinoApp.WriteLine("Mola DLL preference updated; no study launched.")
            return
        if choice.OptionIndex() in (mola, field, surface, prototype):
            mode = {mola: MOLA_MODE, field: MOLA_FIELD_MODE, surface: MOLA_SURFACE_MODE, prototype: VISUAL_MODE}[choice.OptionIndex()]
            if mode == VISUAL_MODE:
                Rhino.RhinoApp.WriteLine("VisualPrototype: curved ribs, crown fans and diagonal terraces on this ORIGINAL mesh. Fixed reproducible recipes; existing limits apply.")
            else:
                Rhino.RhinoApp.WriteLine(mode + ": all eligible planar convex triangles/quads of this ORIGINAL mesh; excluded faces stay unchanged. Maximum 1000 selected faces.")
            dll = mola_dll_path()
            if dll is None:
                return
            Run(doc, source, mode=mode, mola_dll=dll).start()
            return
        Rhino.RhinoApp.WriteLine("Strength is a fraction of each pre-displacement bounding-box diagonal, not millimetres; allowed 0–0.03.")
        number = Rhino.Input.Custom.GetNumber()
        number.SetCommandPrompt("CHESHIRE strength (relative bbox diagonal)")
        number.SetDefaultNumber(0.01)
        number.SetLowerLimit(0.0, False)
        number.SetUpperLimit(0.03, False)
        number.Get()
        if number.CommandResult() != Rhino.Commands.Result.Success:
            return
        Run(doc, source, number.Number()).start()
    except Exception as error:
        Rhino.RhinoApp.WriteLine("CHESHIRE: " + str(error))


if __name__ == "__main__":
    main()
