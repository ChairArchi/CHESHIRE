"""Optional, one-pass HDMola face adapter. CLR imports occur only on execution."""

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from math import fsum, hypot, isfinite, sqrt
import os
from pathlib import Path

from compas.datastructures import Mesh

from .execution import ExecutionBudget, check_execution_budget
from .lineage import LineageMap, ParentRef
from .normalization import _finite_number
from .validation import validate_lineage_coverage, validate_mesh

PLANAR_TOLERANCE = 1e-9
BACKEND_TOLERANCE = 2e-6  # Face-local, normalized coordinates; Mola uses float32.
MAX_SELECTED_FACES = 1000


@dataclass(frozen=True)
class TaperedExtrusionResult:
    mesh: Mesh
    lineage: LineageMap
    face_roles: dict
    parameters: dict
    backend: dict | None
    counts: dict
    warnings: list


def _cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def _dot(a, b):
    return fsum(x*y for x, y in zip(a, b))


def _subtract(a, b):
    return [x-y for x, y in zip(a, b)]


def _face_frame(mesh, key):
    """Validate an ordered planar convex polygon in scale-independent coordinates."""
    corners = list(mesh.face_vertices(key))
    if len(corners) not in (3, 4) or len(set(corners)) != len(corners):
        raise ValueError(f"Face {key}: distinct triangle/quad corners required.")
    xyz = [mesh.vertex_coordinates(v) for v in corners]
    center = [fsum(p[a]/len(xyz) for p in xyz) for a in range(3)]
    offsets = [_subtract(p, center) for p in xyz]
    scale = max(hypot(*p) for p in offsets)
    if not isfinite(scale) or scale <= 0:
        raise ValueError(f"Face {key}: degenerate or unrepresentable scale.")
    local = [[v/scale for v in p] for p in offsets]
    if not all(isfinite(v) for p in local for v in p):
        raise ValueError(f"Face {key}: unrepresentable coordinates.")
    crosses = [_cross(p, local[(i+1) % len(local)]) for i, p in enumerate(local)]
    area_vector = [fsum(p[a] for p in crosses) for a in range(3)]
    area2 = hypot(*area_vector)
    if area2 <= PLANAR_TOLERANCE:
        raise ValueError(f"Face {key}: degenerate area.")
    normal = [v/area2 for v in area_vector]
    if any(abs(_dot(_subtract(p, local[0]), normal)) > PLANAR_TOLERANCE for p in local):
        raise ValueError(f"Face {key}: nonplanar selected face.")
    for i, p in enumerate(local):
        turn = _cross(_subtract(p, local[i-1]), _subtract(local[(i+1) % len(local)], p))
        if _dot(turn, normal) <= PLANAR_TOLERANCE:
            raise ValueError(f"Face {key}: convex, nondegenerate corners required.")
    return corners, center, scale, local, normal, sqrt(area2/2)


def eligible_planar_faces(mesh):
    """Explicit eligibility preview; excluded faces remain untouched by the study."""
    selected, excluded = [], []
    for key in mesh.faces():
        try:
            _face_frame(mesh, key)
            selected.append(key)
        except (ValueError, ArithmeticError) as error:
            excluded.append({"id": key, "reason": str(error)})
    return selected, excluded


def _parameters(value, selected, name):
    if isinstance(value, Mapping):
        if set(value) != set(selected):
            raise ValueError(f"{name}: mapping must cover exactly the selected face keys.")
        values = value
    else:
        values = {key: value for key in selected}
        # Reject invalid scalars even for an empty selection.
        _parameter(value, name)
    return {key: _parameter(values[key], name) for key in selected}


def _parameter(value, name):
    result = _finite_number(value, name)
    if not (0 < result <= 0.5 if name == "height_ratio" else 0 < result < 0.9):
        raise ValueError(f"{name}: outside conservative demo range.")
    return result


def _check_mesh(mesh):
    problems = validate_mesh(mesh)
    # Check directed incidences independently before COMPAS can hide an
    # overwritten halfedge. No welding or changes to subdivision validation.
    directed = set()
    for key in mesh.faces():
        corners = mesh.face_vertices(key)
        if len(corners) < 3 or len(set(corners)) != len(corners):
            problems.append(f"Face {key}: invalid corner connectivity.")
        for a, b in zip(corners, corners[1:] + corners[:1]):
            if (a, b) in directed:
                problems.append(f"Repeated oriented edge {(a, b)}.")
            if hypot(*_subtract(mesh.vertex_coordinates(a), mesh.vertex_coordinates(b))) == 0:
                problems.append(f"Collapsed geometric edge {(a, b)}.")
            directed.add((a, b))
    if not mesh.is_valid() or not mesh.is_manifold():
        problems.append("COMPAS reports invalid/non-manifold connectivity.")
    if problems:
        raise ValueError("Invalid mesh: " + " ".join(problems))


@lru_cache(maxsize=1)
def _load_backend(dll_path):
    """Load only the explicitly provided standalone DLL, under .NET 8 CoreCLR."""
    dll = Path(dll_path).resolve()
    if not dll.is_file() or dll.suffix.lower() != ".dll":
        raise ValueError(f"Standalone HDMola DLL missing: {dll}")
    try:
        from pythonnet import load
    except ImportError as error:
        raise RuntimeError("Install CHESHIRE's optional mola extra in its .venv.") from error
    load("coreclr", runtime_config=str(Path(__file__).with_name("mola.runtimeconfig.json")),
         dotnet_root=str(Path(os.environ["ProgramFiles"]) / "dotnet"))
    import clr
    from System import Array, Object, Single, Boolean, Environment
    if Environment.Version.Major != 8:
        raise RuntimeError(f"Mola requires the selected .NET 8 runtime, got {Environment.Version}.")
    assembly = clr.AddReference(str(dll))
    if Path(str(assembly.Location)).resolve() != dll:
        raise RuntimeError("Loaded HDMola assembly does not match the configured DLL path.")
    vec = assembly.GetType("Mola.Vec3", True)
    constructor = next(c for c in vec.GetConstructors() if
                       [str(p.ParameterType.FullName) for p in c.GetParameters()] == ["System.Single"]*3)
    methods = [m for m in assembly.GetType("FaceSubdivision", True).GetMethods() if m.Name == "ExtrudeTapered"]
    method = next(m for m in methods if [str(p.ParameterType.FullName) for p in m.GetParameters()] ==
                  ["Mola.Vec3[]", "System.Single", "System.Single", "System.Boolean"])
    metadata = {"dll_path": str(dll), "sha256": sha256(dll.read_bytes()).hexdigest(),
                "assembly": str(assembly.FullName), "runtime": str(Environment.Version),
                "target_framework": next(str(a.FrameworkName) for a in assembly.GetCustomAttributes(False)
                                         if str(a.GetType().FullName) == "System.Runtime.Versioning.TargetFrameworkAttribute"),
                "references": [str(r.FullName) for r in assembly.GetReferencedAssemblies()],
                "public_types": [str(t.FullName) for t in assembly.GetExportedTypes()],
                "extrude_overloads": [str(m) for m in methods]}

    def execute(points, height, fraction):
        height32, fraction32 = Single(height), Single(fraction)
        if not isfinite(float(height32)) or float(height32) <= 0 or float(fraction32) <= 0:
            raise ValueError("Mola parameters cannot be represented as positive float32 values.")
        vectors = Array.CreateInstance(vec, len(points))
        for i, point in enumerate(points):
            vectors.SetValue(constructor.Invoke(Array[Object]([Single(v) for v in point])), i)
        faces = method.Invoke(None, Array[Object]([vectors, height32, fraction32, Boolean(True)]))
        return [[[float(vec.GetField(axis).GetValue(p)) for axis in ("x", "y", "z")]
                 for p in face] for face in faces]
    return execute, metadata


def extrude_tapered_once(mesh, *, selected_faces, height_ratio, fraction, dll_path,
                        budget=None, cap_top=True, source_is_result=False):
    """Mola-generated geometry, explicit face selection and immediate lineage.

    Fresh output carries XYZ/connectivity only, not arbitrary mesh attributes.
    Original boundary XYZ is exact. Top XYZ comes from Mola float32 in a local
    frame. Verification formulas check returned roles, never replace geometry.
    source_is_result applies the existing 50000 stage limits to a previously
    verified result; original-input limits stay 5000 faces / 20000 vertices.
    """
    if cap_top is not True:
        raise ValueError("Only cap_top=True is supported.")
    _check_mesh(mesh)
    selected = list(selected_faces)
    if len(set(selected)) != len(selected) or not set(selected) <= set(mesh.faces()):
        raise ValueError("Selected face keys must be distinct existing keys.")
    if type(source_is_result) is not bool:
        raise ValueError("source_is_result must be a boolean.")
    face_limit, vertex_limit = (50000, 50000) if source_is_result else (5000, 20000)
    if len(selected) > MAX_SELECTED_FACES or mesh.number_of_faces() > face_limit or mesh.number_of_vertices() > vertex_limit:
        raise ValueError(f"Demo input/selected-face limit exceeded ({face_limit} faces, {vertex_limit} vertices, 1000 selected).")
    ratios = _parameters(height_ratio, selected, "height_ratio")
    fractions = _parameters(fraction, selected, "fraction")
    frames = {key: _face_frame(mesh, key) for key in selected}
    extra = sum(len(frame[0]) for frame in frames.values())
    counts = {"input_faces": mesh.number_of_faces(), "input_vertices": mesh.number_of_vertices(),
              "output_faces": mesh.number_of_faces()+extra, "output_vertices": mesh.number_of_vertices()+extra}
    assessment = check_execution_budget(budget if budget is not None else ExecutionBudget(50000, 50000),
        input_faces=counts["input_faces"], input_vertices=counts["input_vertices"],
        estimated_output_faces=counts["output_faces"], estimated_output_vertices=counts["output_vertices"])
    if assessment["status"] != "SAFE":
        raise ValueError("Mola blocked by budget: " + " ".join(assessment["reasons"]))
    output = mesh.copy()
    vertices = {key: [ParentRef(key, 1)] for key in mesh.vertices()}
    faces = {key: [ParentRef(key, 1)] for key in mesh.faces() if key not in frames}
    roles = {key: "unchanged" for key in faces}
    parameters, backend = {}, None
    if not selected:
        return TaperedExtrusionResult(output, LineageMap(vertices, faces), roles, {}, None, counts, ["Empty selection: no-op."])
    # Rebuild geometry only; input custom attributes are never mutated/copied
    # as apparently current derived fields.
    output = Mesh()
    for key in mesh.vertices():
        x, y, z = mesh.vertex_coordinates(key)
        output.add_vertex(key=key, x=x, y=y, z=z)
    for key in faces:
        output.add_face(mesh.face_vertices(key), fkey=key)
    execute, backend = _load_backend(str(Path(dll_path).resolve()))
    next_vertex, next_face = max(mesh.vertices())+1, max(mesh.faces())+1
    for parent, (corners, center, scale, local, normal, sqrt_local_area) in frames.items():
        height_local = ratios[parent]*sqrt_local_area
        height = height_local*scale
        if not isfinite(height) or height <= 0:
            raise ValueError(f"Face {parent}: unrepresentable height.")
        returned = execute(local, height_local, fractions[parent])
        n = len(corners)
        if len(returned) != n+1 or [len(p) for p in returned] != [4]*n+[n]:
            raise ValueError("Mola returned unexpected side/cap counts or corner roles.")
        upper = returned[-1]
        # Formula is an independent role oracle. All actual upper coordinates
        # below are taken from the backend, not this expected-position check.
        local_center = [fsum(p[a]/n for p in local) for a in range(3)]
        expected = [[(1-fractions[parent])*p[a]+fractions[parent]*local_center[a]+height_local*normal[a]
                     for a in range(3)] for p in local]
        def matches(a, b):
            return all(isfinite(x) and abs(x-y) <= BACKEND_TOLERANCE for x, y in zip(a, b))
        if not all(matches(a, b) for a, b in zip(upper, expected)):
            raise ValueError("Mola cap corner order/center/normal offset differs from verified contract.")
        for i, point in enumerate(upper):
            in_plane = [(1-fractions[parent])*local[i][a]+fractions[parent]*local_center[a] for a in range(3)]
            if _dot(_subtract(point, in_plane), normal) <= 0:
                raise ValueError("Mola normal offset collapsed at the float32 boundary.")
        upper_keys = list(range(next_vertex, next_vertex+n))
        next_vertex += n
        for i, (key, point) in enumerate(zip(upper_keys, upper)):
            xyz = [center[a]+scale*point[a] for a in range(3)]
            if not all(isfinite(v) for v in xyz):
                raise ValueError("Mola restored coordinates are non-finite.")
            restored_offset = _subtract(xyz, mesh.vertex_coordinates(corners[i]))
            if _dot(restored_offset, normal) <= 0:
                raise ValueError("Mola normal offset collapsed when restoring world coordinates.")
            output.add_vertex(key=key, x=xyz[0], y=xyz[1], z=xyz[2])
            vertices[key] = [ParentRef(v, fractions[parent]/n+(1-fractions[parent] if j == i else 0))
                             for j, v in enumerate(corners)]
        for i, side in enumerate(returned[:-1]):
            j = (i+1) % n
            if not all(matches(a, b) for a, b in zip(side, [local[i], local[j], upper[j], upper[i]])):
                raise ValueError("Mola side roles differ from verified boundary/cap order.")
            output.add_face([corners[i], corners[j], upper_keys[j], upper_keys[i]], fkey=next_face)
            faces[next_face], roles[next_face] = [ParentRef(parent, 1)], "side"
            next_face += 1
        output.add_face(upper_keys, fkey=next_face)
        faces[next_face], roles[next_face] = [ParentRef(parent, 1)], "cap"
        next_face += 1
        parameters[parent] = {"height_ratio": ratios[parent], "height": height, "fraction": fractions[parent],
                              "cap_top": True, "normal_offset": [height*v for v in normal],
                              "upper_vertex_ids": upper_keys, "local_scale": scale}
    lineage = LineageMap(vertices, faces)
    _check_mesh(output)
    if validate_lineage_coverage(mesh, output, lineage):
        raise ValueError("Mola immediate-parent lineage coverage failed.")
    if output.number_of_faces() != counts["output_faces"] or output.number_of_vertices() != counts["output_vertices"]:
        raise ValueError("Actual Mola output counts differ from the budget estimate.")
    return TaperedExtrusionResult(output, lineage, roles, parameters, backend, counts,
        ["Float32 backend: role verification tolerance 2e-6 in normalized face coordinates; base XYZ retained exactly.",
         "In-face lineage weights exclude the separately recorded normal offset; no global collision guarantee."])
