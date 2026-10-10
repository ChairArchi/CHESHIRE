import os,sys
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
REPO=Path(os.environ.get("CHESHIRE_ROOT",Path('C:\\Users\\USER\\CHESHIRE')))
DEPS=Path(os.environ.get("CHESHIRE_EXTERNAL_DEPS",Path('C:\\Users\\USER\\CHESHIRE\\scratch\\grotesque_gate_20261010\\deps')))
if DEPS.is_dir():sys.path.insert(0,str(DEPS))
if (PROJECT/"deps").is_dir():sys.path.insert(0,str(PROJECT/"deps"))
sys.path.insert(0,str(REPO/"src"))
ASTRA=Path(os.environ.get("CHESHIRE_ASTRA_ROOT",REPO.parent/"CHESHIRE_ASTRA"))
import cheshire
if (ASTRA/"src/cheshire").is_dir():cheshire.__path__.append(str(ASTRA/"src/cheshire"))

sys.path.insert(0,'C:\\Users\\USER\\CHESHIRE\\scratch\\generative_gate_20261010\\deps')
