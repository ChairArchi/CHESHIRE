"""Bitwise equality wrapper: preserved NaN payloads are equal source evidence."""
from pathlib import Path
import json
import sys

import numpy as np
import audit_coffer_foundation_cache as audit


def bitwise_equal(a, b):
    a, b = np.asarray(a), np.asarray(b)
    return a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes()


np.array_equal = bitwise_equal
audit.main()
output = Path(sys.argv[sys.argv.index('--output')+1])
report = json.loads(output.read_text(encoding='utf8'))
report['array_equality_method'] = 'Identical dtype, shape and all array bytes, including preserved NaN payloads. The initial audit helper stopped because ordinary np.array_equal treats matching NaNs as unequal.'
output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
