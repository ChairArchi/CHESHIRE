"""Export normalized checkpoint geometry and render with the shared experiment camera."""
from pathlib import Path
import sys,subprocess,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
s=np.load(source);mesh=out/'checkpoint.obj'
with mesh.open('w') as f:
 for v in s['xyz']:f.write('v '+' '.join(format(x,'.17g') for x in v)+'\n')
 for q in s['faces']:f.write('f '+' '.join(str(int(x)+1) for x in q if x>=0)+'\n')
blender=ROOT.parent/'generative_gate_20261010/external/blender-4.5.4-windows-x64/blender.exe'
with (out/'render.log').open('w') as log:
 subprocess.run([str(blender),'-b','-t','4','--python',str(ROOT/'render_cycles.py'),'--',str(mesh),str(out),sys.argv[3] if len(sys.argv)>3 else 'front,oblique,micro',str(ROOT/'runs/patch_scale4/camera.json')],stdout=log,stderr=subprocess.STDOUT,check=True)
(out/'checkpoint_source.json').write_text(json.dumps({'source':str(source),'geometry':'Normalized pre-opening-guard checkpoint, same convention as the frozen Tissue TARGET'},indent=2))
