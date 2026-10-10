"""Convert an existing normalized checkpoint to the shared tissue input contract."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
source=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]).resolve()
if output.exists():raise FileExistsError(output)
state=np.load(source)
output.write_text(json.dumps(dict(vertices=state['xyz'].tolist(),faces=[q[q>=0].tolist() for q in state['faces']])))
output.with_suffix('.source.json').write_text(json.dumps(dict(source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),axes='X right; Y front; Z up; normalized checkpoint coordinates',actual_ALICE=False),indent=2))
