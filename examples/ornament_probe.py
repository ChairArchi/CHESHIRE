"""Task 19: reflect the user's explicit standalone DLL before choosing operators."""
import json
import argparse
from pathlib import Path
from cheshire.mola import _load_backend

ROOT = Path(__file__).resolve().parents[1]
def main(dll):
    execute, metadata = _load_backend(str(dll))
    import clr
    assembly = clr.AddReference(str(dll))
    methods = [m for m in assembly.GetType("FaceSubdivision", True).GetMethods() if m.IsStatic and m.IsPublic]
    metadata["face_subdivision_api"] = [dict(name=str(m.Name), signature=str(m),
        parameters=[dict(name=str(p.Name), type=str(p.ParameterType.FullName)) for p in m.GetParameters()]) for m in methods]
    metadata["extrusion_probes"] = {}
    fixtures = {"unit_quad": [[0,0,0],[1,0,0],[1,1,0],[0,1,0]],
        "warped_quad": [[0,0,0],[1,0,.12],[1,1,0],[0,1,-.08]],
        "triangle": [[0,0,0],[1,0,0],[0,1,0]]}
    for name, xyz in fixtures.items():
        try:
            a = execute(xyz, .1, .25)
            metadata["extrusion_probes"][name] = dict(input=xyz, output=a, repeat_identical=a==execute(xyz,.1,.25))
        except Exception as error:
            metadata["extrusion_probes"][name] = dict(error=str(error))
    from System import Array, Object, Single
    vec = assembly.GetType("Mola.Vec3", True)
    ctor = next(c for c in vec.GetConstructors() if len(c.GetParameters())==3)
    metadata["frame_probes"] = {}
    for operator in ("Frame", "Offset"):
        method = next(m for m in methods if m.Name==operator and
            [str(p.ParameterType.FullName) for p in m.GetParameters()]==["Mola.Vec3[]", "System.Single"])
        for name, xyz in fixtures.items():
            vectors = Array.CreateInstance(vec,len(xyz))
            for i, p in enumerate(xyz):
                vectors.SetValue(ctor.Invoke(Array[Object]([Single(v) for v in p])), i)
            width=.1 if operator=="Frame" else -.1
            def call():
                return [[[float(vec.GetField(axis).GetValue(p)) for axis in ("x","y","z")]
                    for p in face] for face in method.Invoke(None,Array[Object]([vectors,Single(width)]))]
            try:
                a=call()
                metadata["frame_probes"][operator+"_"+name]=dict(input=xyz, parameter=width, output=a,repeat_identical=a==call())
            except Exception as error:
                metadata["frame_probes"][operator+"_"+name]=dict(error=str(error))
    path = ROOT / "output/task19/operator_api_evidence.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--dll",type=Path,required=True,help="Explicit user-supplied official standalone HDMola DLL")
    main(parser.parse_args().dll.resolve())
