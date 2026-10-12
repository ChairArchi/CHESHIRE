"""Use the frozen broad comparison renderer for the fine-fold candidate only."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render as renderer

renderer.MODES = ('ROOTED_FANS',)
renderer.main()
# The original renderer's receipt already identifies native geometry and views.
# Retain this mode-list adapter as an additional execution-provenance record.
arguments = sys.argv[sys.argv.index('--')+1:]
root = Path(arguments[arguments.index('--root')+1])
for receipt_path in root.glob('ROOTED_FANS/*/G06/views/receipt.json'):
    receipt = json.loads(receipt_path.read_text(encoding='utf8'))
    receipt['render_adapter_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf8')
